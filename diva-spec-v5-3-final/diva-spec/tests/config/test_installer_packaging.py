"""Static contracts for the offline Windows installer (PROD-05, DEC-109).

The installer cannot be executed in CI (it needs Windows and WSL2), so these
checks lock the parts that broke during development: the image must contain the
config script, the one-shot jobs must be real scripts instead of folded YAML,
and the SFX must bundle every image the compose file references.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra" / "compose" / "store.prod.yml"
STORE_DOCKERFILE = ROOT / "infra" / "images" / "store" / "Dockerfile"
WSL_DOCKERFILE = ROOT / "infra" / "images" / "wsl" / "Dockerfile"
BUILD = ROOT / "scripts" / "build-installer.sh"
INSTALL_PS1 = ROOT / "scripts" / "install.ps1"
SETUP_CMD = ROOT / "scripts" / "setup.cmd"
SFX = ROOT / "infra" / "sfx" / "7zSD.sfx"


def compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def test_production_compose_targets_one_site() -> None:
    services = compose()["services"]
    assert "create-site" in services
    assert "configurator" in services
    frontend = services["frontend"]
    assert frontend["environment"]["FRAPPE_SITE_NAME_HEADER"] == "diva.local"


def test_one_shot_jobs_are_scripts_not_folded_yaml() -> None:
    """A folded scalar keeps newlines and broke `bench new-site` options."""
    services = compose()["services"]
    for name in ("configurator", "create-site"):
        command = services[name]["command"]
        script = "/opt/diva/configure.sh" if name == "configurator" else "/opt/diva/create-site.sh"
        assert command == [script], name


def test_store_image_contains_the_config_and_one_shot_scripts() -> None:
    text = STORE_DOCKERFILE.read_text(encoding="utf-8")
    assert "COPY --chown=frappe:frappe infra/erpnext-config infra/erpnext-config" in text
    assert "scripts/docker/configure.sh /opt/diva/configure.sh" in text
    assert "scripts/docker/create-site.sh /opt/diva/create-site.sh" in text


def test_apps_install_into_the_bench_virtualenv() -> None:
    """`pip` on PATH is the system interpreter; bench uses frappe-bench/env.

    Installing with the wrong pip makes `python -c "import diva_guard"` pass
    while `bench install-app diva_guard` fails with "No module named" because
    the venv has no editable path for the app.
    """
    text = STORE_DOCKERFILE.read_text(encoding="utf-8")
    assert "env/bin/python -m pip install" in text
    assert "\nRUN pip install" not in text


def test_pos_next_build_has_the_config_it_imports_and_keeps_assets() -> None:
    """`src/socket.js` imports socketio_port; the entrypoint replaces sites/assets.

    Without seeding common_site_config.json the Vite build fails; without moving
    the build to frappe-bench/assets the runtime symlink hides it.
    """
    text = STORE_DOCKERFILE.read_text(encoding="utf-8")
    assert '{"socketio_port": 9000}' in text
    assert "bench build --app frappe --app erpnext --app pos_next" in text
    assert "rm -rf assets" in text
    assert "mv sites/assets assets" in text


def test_create_site_restores_apps_txt_before_installing_apps() -> None:
    """`bench new-site` rewrites apps.txt; bench resolves imports from it."""
    text = (ROOT / "scripts" / "docker" / "create-site.sh").read_text(encoding="utf-8")
    new_site = text.index("bench new-site")
    rewrite = text.index("write_apps_txt > sites/apps.txt")
    install = text.index('install-app "$app"')
    assert new_site < rewrite < install
    assert 'echo "frappe"' in text
    assert "hooks.py" in text
    # `set -e` would abort when the last directory is not a bench app (the
    # rules-engine library), so the helper must end successfully.
    start = text.index("write_apps_txt() {")
    helper = text[start : text.index("\n}\n", start)]
    assert "if [" in helper
    assert "return 0" in helper
    assert "&& echo" not in helper


def test_create_site_is_resumable() -> None:
    text = (ROOT / "scripts" / "docker" / "create-site.sh").read_text(encoding="utf-8")
    assert 'if [ ! -d "sites/$SITE" ]' in text
    assert "list-apps | grep -qx" in text
    assert "ensure_api_credentials" in text
    assert "prepare_first_run" in text


def test_wsl_rootfs_runs_docker_engine_with_systemd() -> None:
    text = WSL_DOCKERFILE.read_text(encoding="utf-8")
    assert "docker-ce" in text
    assert "docker-compose-plugin" in text
    assert "systemd=true" in text
    assert "diva-store.service" in text


def test_sfx_payload_contains_every_compose_image() -> None:
    text = BUILD.read_text(encoding="utf-8")
    assert "diva-store:latest" in text
    assert "mariadb:11.8" in text
    assert "redis:6.2-alpine" in text
    assert 'cat "$SFX"' in text
    assert "DivaStore-Setup-$VERSION.exe" in text
    assert SFX.is_file()


def test_windows_installer_is_resumable_and_offline() -> None:
    text = INSTALL_PS1.read_text(encoding="utf-8")
    assert "wsl.exe --import" in text
    assert "docker load -i" in text
    assert "docker compose --env-file .env -f store.prod.yml up -d" in text
    assert "if (Test-Path $script:EnvFile)" in text
    assert "ADMIN_PASSWORD.txt" in text
    assert "https://" not in text.replace("https://localhost", "")
    # wsl --import needs its target directory, and the systemd unit documents
    # /opt/diva/README.txt.
    assert '(Join-Path $InstallDir "wsl")' in text
    assert "/opt/diva/README.txt" in text


def test_setup_cmd_runs_the_powershell_installer() -> None:
    text = SETUP_CMD.read_text(encoding="utf-8")
    assert "install.ps1" in text
    assert "ExecutionPolicy Bypass" in text
    # WSL2 needs Administrator; the elevated copy must finish before the SFX
    # deletes the temporary payload directory.
    assert "net session" in text
    assert "-Verb RunAs -Wait" in text
