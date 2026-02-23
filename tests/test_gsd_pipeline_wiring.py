import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = PROJECT_ROOT / ".claude" / "settings.json"
GSD_PIPELINE_PATH = PROJECT_ROOT / ".claude" / "hooks" / "gsd-pipeline.sh"


def _first_hook_command(settings: dict, event_key: str) -> str:
    return settings["hooks"][event_key][0]["hooks"][0]["command"]


def test_settings_routes_session_start_to_gsd_pipeline():
    settings = json.loads(SETTINGS_PATH.read_text())
    command = _first_hook_command(settings, "SessionStart")
    assert "gsd-pipeline.sh session_start" in command


def test_settings_routes_user_prompt_submit_to_gsd_pipeline():
    settings = json.loads(SETTINGS_PATH.read_text())
    command = _first_hook_command(settings, "UserPromptSubmit")
    assert "gsd-pipeline.sh user_prompt_submit" in command


def test_settings_routes_pre_tool_use_to_gsd_pipeline():
    settings = json.loads(SETTINGS_PATH.read_text())
    command = _first_hook_command(settings, "PreToolUse")
    assert "gsd-pipeline.sh pre_tool_use" in command


def test_gsd_pipeline_script_exists_and_is_valid_bash():
    assert GSD_PIPELINE_PATH.exists()
    result = subprocess.run(
        ["bash", "-n", str(GSD_PIPELINE_PATH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
