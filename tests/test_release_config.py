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
    assert "Release succeeded" in content
