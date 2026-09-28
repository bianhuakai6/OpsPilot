from pathlib import Path


def test_release_compose_uses_a_versioned_api_image_and_dependency_checks() -> None:
    content = Path("docker-compose.release.yml").read_text(encoding="utf-8")

    assert "OPSPILOT_IMAGE" in content
    assert "pull_policy: never" in content
    assert "OPSPILOT_STORAGE: mysql" in content
    assert "OPSPILOT_REDIS_ENABLED: \"true\"" in content
    assert "condition: service_healthy" in content
    assert "/readyz" in content


def test_release_script_has_deploy_status_stop_and_port_protection() -> None:
    content = Path("scripts/release-local.ps1").read_text(encoding="utf-8")

    assert 'ValidateSet("deploy", "status", "stop")' in content
    assert "Get-NetTCPConnection -LocalPort 8000" in content
    assert "docker image inspect $image" in content
    assert "deployment was not started" in content
    assert "opspilot:local-placeholder" in content
    assert "docker stop opspilot-api" in content
    assert "Release succeeded" in content


def test_container_first_run_does_not_require_host_python() -> None:
    build_script = Path("scripts/build-image.ps1").read_text(encoding="utf-8")
    release_script = Path("scripts/release-local.ps1").read_text(encoding="utf-8")
    test_dockerfile = Path("Dockerfile.test").read_text(encoding="utf-8")
    entrypoint = Path("start-container.bat").read_text(encoding="utf-8")

    assert "C:\\Windows\\py.exe" not in build_script
    assert "C:\\Windows\\py.exe" not in release_script
    assert "RUN pytest -q" in test_dockerfile
    assert "container-start.ps1" in entrypoint
