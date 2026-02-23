from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSTALL_TOOLS_PATH = PROJECT_ROOT / ".claude" / "scripts" / "orchestration" / "install_tools.sh"


def test_install_tools_requires_ralphex_not_optional():
    content = INSTALL_TOOLS_PATH.read_text()
    assert "check_ralphex || all_ok=false" in content
    assert "check_ralphex || install_ralphex" in content
    assert "ralphex not installed (optional)" not in content
    assert "ralphex not available (this is okay, it's optional)" not in content


def test_install_tools_uses_brew_for_ralphex():
    content = INSTALL_TOOLS_PATH.read_text()
    assert "brew install ralphex" in content
    assert "brew upgrade ralphex" in content
    assert "npm install -g ralphex" not in content


def test_install_tools_requires_omx():
    content = INSTALL_TOOLS_PATH.read_text()
    assert "check_omx" in content
    assert "install_omx" in content
