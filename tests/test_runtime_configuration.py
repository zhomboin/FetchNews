from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_docker_compose_reads_vite_api_base_from_env() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "VITE_API_BASE: ${VITE_API_BASE:-http://localhost:8000}" in compose
    assert "VITE_API_BASE: http://localhost:8000" not in compose


def test_docker_compose_uses_shared_service_anchors() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "x-app-python-service: &app-python-service" in compose
    assert "x-app-runtime-env: &app-runtime-env" in compose
    assert "x-app-service-env: &app-service-env" in compose
    assert "  <<: *app-python-service" in compose
    assert "      <<: *app-service-env" in compose
    assert compose.count("APP_AUTH_SECRET_KEY: ${APP_AUTH_SECRET_KEY:-fetchnews-dev-secret}") == 1
    assert compose.count('    - "host.docker.internal:host-gateway"') == 1


def test_frontend_api_clients_share_runtime_api_base_config() -> None:
    api_module = (REPO_ROOT / "web/src/lib/api.ts").read_text(encoding="utf-8")
    editorial_api_module = (REPO_ROOT / "web/src/lib/editorial-api.ts").read_text(encoding="utf-8")
    runtime_config_module = REPO_ROOT / "web/src/lib/runtime-config.ts"

    assert runtime_config_module.exists(), "runtime-config.ts should define the shared frontend runtime config"
    assert 'from "./runtime-config"' in api_module
    assert 'from "./runtime-config"' in editorial_api_module
    assert 'const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";' not in api_module
    assert 'const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";' not in editorial_api_module


def test_startup_docs_explain_browser_visible_addresses_and_cors() -> None:
    getting_started = (REPO_ROOT / "docs/getting-started.md").read_text(encoding="utf-8")
    ops_baseline = (REPO_ROOT / "docs/engineering-ops-baseline.md").read_text(encoding="utf-8")

    assert "浏览器可访问的后端地址" in getting_started
    assert "APP_CORS_ORIGINS" in getting_started
    assert "http://localhost:5173,http://192.168.175.201:5173" in getting_started
    assert "APP_CORS_ORIGINS" in ops_baseline
    assert "默认仅允许 `http://localhost:5173`" in ops_baseline
