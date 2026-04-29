from __future__ import annotations

from pathlib import Path


BUNDLE_ROOT = Path(__file__).resolve().parent.parent


def read_text(path: str) -> str:
    return (BUNDLE_ROOT / path).read_text(encoding="utf-8")


def test_documented_component_paths_exist():
    for path in [
        "zhuge-skill",
        "self-improving-loop",
        "taiji",
        "TaijiOS",
        "TaijiOS-Lite",
        "zhuge-crystals",
        "taijios-landing",
        "aios",
        "tools",
        "tests",
    ]:
        assert (BUNDLE_ROOT / path).exists(), f"documented component missing: {path}"


def test_documented_root_scripts_exist():
    for path in [
        "setup.py",
        "setup.bat",
        "taijios.py",
        "api_server.py",
        "doctor.py",
        "heartbeat.py",
        "heartbeat_daemon.py",
        "mcp_server.py",
        "brain.py",
        "install_scheduler.py",
        "uninstall.py",
    ]:
        assert (BUNDLE_ROOT / path).is_file(), f"documented root script missing: {path}"


def test_quickstart_docs_point_to_real_files():
    readme = read_text("README.md")
    for path in ["START_HERE.md", "MANIFEST.md", "SECURITY.md"]:
        assert f"]({path})" in readme
        assert (BUNDLE_ROOT / path).is_file()

    start_here = read_text("START_HERE.md")
    assert "python setup.py" in start_here
    assert "python taijios.py" in start_here
    assert "python doctor.py --dry" in start_here


def test_docs_do_not_overclaim_live_provider_health():
    combined = "\n".join(
        read_text(path)
        for path in ["README.md", "START_HERE.md", "MANIFEST.md"]
    )
    forbidden_claims = [
        "以上都**多轮 API 验证过**",
        "DeepSeek 真调稳定",
    ]
    for claim in forbidden_claims:
        assert claim not in combined
