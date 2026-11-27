#!/usr/bin/env bash
# Build the Diva Store distribution payload (PROD-05).
#
# Usage:
#   bash scripts/build-package.sh             # sources, config and scripts
#   bash scripts/build-package.sh --with-image  # also export diva-store:latest
#
# The output is a single directory, `dist/`, whose *contents* are the payload.
# `cd dist && ./verify-package.sh` therefore works exactly as an installer sees
# it. Every checksum is recorded relative to that directory and cache folders
# are excluded, so the manifest is reproducible and verifies on the next run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
# No release tags yet, so the payload is identified by its commit. Once PROD-05
# tags a release this becomes the tag name without any other change.
VERSION="$(git -C "$ROOT" describe --tags --always --dirty 2>/dev/null || echo 0.0.0-unknown)"
ARCHIVE="diva-store-$VERSION.tar.gz"
WITH_IMAGE=0
[[ "${1:-}" == "--with-image" ]] && WITH_IMAGE=1

cd "$ROOT"

rm -rf "$DIST"
mkdir -p "$DIST"

# Payload: the sources the installer needs, minus caches and build output.
tar -cf - \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.ruff_cache' \
    --exclude='.mypy_cache' \
    --exclude='.pytest_cache' \
    --exclude='node_modules' \
    --exclude='.venv' \
    apps packages infra scripts CHANGELOG.md README.md \
    | tar -C "$DIST" -xf -

printf '%s\n' "$VERSION" > "$DIST/VERSION"

if [[ "$WITH_IMAGE" == "1" ]]; then
    if ! docker image inspect diva-store:latest >/dev/null 2>&1; then
        echo "diva-store:latest is not built; run docker build first." >&2
        exit 1
    fi
    mkdir -p "$DIST/images"
    docker save diva-store:latest | gzip -9n > "$DIST/images/diva-store-$VERSION.tar.gz"
fi

cat > "$DIST/MANIFEST.txt" <<EOF
Diva Store distribution payload
===============================

Version: $VERSION
Built:   $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Payload: source packages, ERPNext configuration and scripts
Image:   $( [[ "$WITH_IMAGE" == "1" ]] && echo "images/diva-store-$VERSION.tar.gz" || echo "not included (build with --with-image)" )

This payload is not yet the single-file installer: the 7-Zip SFX assembly and
the WSL2 distro belong to PROD-04/PROD-05 and land with that task.

Verify with:  cd dist && ./verify-package.sh
EOF

cat > "$DIST/verify-package.sh" <<'EOF'
#!/usr/bin/env bash
# Verify the payload against SHA256SUMS. Paths are relative to this directory.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

for required in VERSION MANIFEST.txt SHA256SUMS apps/diva_guard packages/rules-engine; do
    if [[ ! -e "$required" ]]; then
        echo "Missing: $required" >&2
        exit 1
    fi
done

sha256sum --check --quiet SHA256SUMS
echo "OK: $(grep -c . SHA256SUMS) files verified"
EOF
chmod +x "$DIST/verify-package.sh"

# Manifest last: it must cover every payload file except itself.
(
    cd "$DIST"
    find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)

# Reproducible archive: sorted names, fixed mtime, no gzip timestamp. The
# archive is written outside the payload first so tar never reads its own
# output, then moved in with its own checksum.
TMPDIR_BUILD="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_BUILD"' EXIT
(
    cd "$DIST"
    tar --sort=name --mtime='UTC 2026-01-01' --owner=0 --group=0 --numeric-owner \
        -cf "$TMPDIR_BUILD/payload.tar" .
)
gzip -9n -c "$TMPDIR_BUILD/payload.tar" > "$DIST/$ARCHIVE"
sha256sum "$DIST/$ARCHIVE" | sed "s|$DIST/||" > "$DIST/$ARCHIVE.sha256"

"$DIST/verify-package.sh"
echo "payload: $DIST"
echo "archive: $DIST/$ARCHIVE ($(du -h "$DIST/$ARCHIVE" | cut -f1))"
