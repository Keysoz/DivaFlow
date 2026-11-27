#!/usr/bin/env bash
# Build the single-file Diva Store installer (PROD-05, DEC-109).
#
# Produces:
#   dist/installer/DivaStore-Setup-<version>.exe
#   dist/installer/DivaStore-Setup-<version>.exe.sha256
#
# The .exe is a 7-Zip self-extractor containing the Windows scripts, the
# Debian+Docker WSL2 rootfs and every container image. It needs no network.
#
# Usage:
#   bash scripts/build-installer.sh              # reuse existing images
#   bash scripts/build-installer.sh --rebuild    # rebuild both images first
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist/installer"
PAYLOAD="$DIST/payload"
# Set DIVA_VERSION to name a release explicitly (for example 0.1.0); otherwise
# use the nearest tag plus the commit, so an installer is always traceable.
VERSION="${DIVA_VERSION:-$(git -C "$ROOT" describe --tags --always --dirty 2>/dev/null || echo 0.0.0)}"
REBUILD=0
[[ "${1:-}" == "--rebuild" ]] && REBUILD=1

for tool in docker 7z sha256sum; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done

SFX="$ROOT/infra/sfx/7zSD.sfx"
[[ -f "$SFX" ]] || { echo "Missing SFX module: $SFX" >&2; exit 1; }

echo "==> Diva Store installer $VERSION"

if [[ "$REBUILD" == "1" ]] || ! docker image inspect diva-store:latest >/dev/null 2>&1; then
    echo "==> Building diva-store:latest"
    docker build -f "$ROOT/infra/images/store/Dockerfile" -t diva-store:latest "$ROOT"
fi

if [[ "$REBUILD" == "1" ]] || ! docker image inspect diva-wsl-rootfs:latest >/dev/null 2>&1; then
    echo "==> Building diva-wsl-rootfs:latest"
    docker build -f "$ROOT/infra/images/wsl/Dockerfile" -t diva-wsl-rootfs:latest "$ROOT"
fi

for image in mariadb:11.8 redis:6.2-alpine; do
    docker image inspect "$image" >/dev/null 2>&1 || {
        echo "Missing base image $image. Pull it before building the installer." >&2
        exit 1
    }
done

rm -rf "$DIST"
mkdir -p "$PAYLOAD"

echo "==> Exporting the WSL2 rootfs"
docker rm -f diva-rootfs-export >/dev/null 2>&1 || true
docker create --name diva-rootfs-export diva-wsl-rootfs:latest /bin/true >/dev/null
docker export diva-rootfs-export -o "$PAYLOAD/rootfs.tar"
docker rm diva-rootfs-export >/dev/null

echo "==> Saving container images"
docker save -o "$PAYLOAD/images.tar" \
    diva-store:latest \
    mariadb:11.8 \
    redis:6.2-alpine

echo "==> Assembling the payload"
cp "$ROOT/scripts/install.ps1" "$PAYLOAD/install.ps1"
cp "$ROOT/scripts/setup.cmd" "$PAYLOAD/setup.cmd"
cp "$ROOT/scripts/README-installer.txt" "$PAYLOAD/README.txt"
cp "$ROOT/infra/compose/store.prod.yml" "$PAYLOAD/store.prod.yml"
cp "$ROOT/infra/compose/.env.prod.example" "$PAYLOAD/env.prod.example"

(
    cd "$PAYLOAD"
    sha256sum install.ps1 setup.cmd README.txt store.prod.yml env.prod.example \
        rootfs.tar images.tar > SHA256SUMS
)

echo "==> Compressing the payload (this is the long step)"
rm -f "$DIST/payload.7z"
(cd "$PAYLOAD" && 7z a -t7z -mx=5 -ms=on -bd "$DIST/payload.7z" ./* >/dev/null)

EXE="$DIST/DivaStore-Setup-$VERSION.exe"
cat "$SFX" "$ROOT/infra/sfx/config.txt" "$DIST/payload.7z" > "$EXE"
rm -f "$DIST/payload.7z"

(
    cd "$DIST"
    sha256sum "$(basename "$EXE")" > "$(basename "$EXE").sha256"
)

echo
echo "==> Done"
ls -lh "$EXE" "$EXE.sha256"
cat "$EXE.sha256"
