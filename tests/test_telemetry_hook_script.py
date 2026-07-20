"""scripts/frob-telemetry-hook: PostToolUse telemetry hook (T-0178)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_HOOK = Path(__file__).resolve().parents[1] / "scripts" / "frob-telemetry-hook"


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)


def _run_hook(root: Path, stdin_text: str, extra_args: list[str] | None = None):
    return subprocess.run(
        [sys.executable, str(_HOOK), *(extra_args or [])],
        cwd=root,
        input=stdin_text,
        capture_output=True,
        text=True,
        check=False,
    )


def test_hook_emits_valid_jsonl_from_stdin_payload(tmp_path: Path):
    # frob:tests scripts/frob-telemetry-hook kind="integration"
    _init_repo(tmp_path)
    payload = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
            "tool_response": "hi\n",
            "duration_ms": 12.0,
        }
    )
    result = _run_hook(tmp_path, payload)
    assert result.returncode == 0
    telemetry = tmp_path / ".frob" / "telemetry.jsonl"
    record = json.loads(telemetry.read_text(encoding="utf-8").strip())
    assert record["kind"] == "tool"
    assert record["tool"] == "Bash"
    assert record["output_tokens_est"] == len("hi\n") // 4


def test_hook_exits_zero_on_empty_stdin(tmp_path: Path):
    # frob:tests scripts/frob-telemetry-hook kind="integration"
    _init_repo(tmp_path)
    result = _run_hook(tmp_path, "")
    assert result.returncode == 0
    assert not (tmp_path / ".frob" / "telemetry.jsonl").exists()


def test_hook_exits_zero_on_malformed_json(tmp_path: Path):
    # frob:tests scripts/frob-telemetry-hook kind="integration"
    _init_repo(tmp_path)
    result = _run_hook(tmp_path, "not json at all")
    assert result.returncode == 0
    assert not (tmp_path / ".frob" / "telemetry.jsonl").exists()


def test_hook_respects_no_telemetry_env(tmp_path: Path, monkeypatch):
    # frob:tests scripts/frob-telemetry-hook kind="integration"
    _init_repo(tmp_path)
    monkeypatch.setenv("FROB_NO_TELEMETRY", "1")
    payload = json.dumps({"tool_name": "Bash", "tool_input": {}, "tool_response": ""})
    result = subprocess.run(
        [sys.executable, str(_HOOK)],
        cwd=tmp_path,
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        env={**__import__("os").environ, "FROB_NO_TELEMETRY": "1"},
    )
    assert result.returncode == 0
    assert not (tmp_path / ".frob" / "telemetry.jsonl").exists()


def test_hook_shim_mode_appends_from_flags(tmp_path: Path):
    # frob:tests scripts/frob-telemetry-hook kind="integration"
    _init_repo(tmp_path)
    result = _run_hook(
        tmp_path,
        "",
        extra_args=[
            "--tool",
            "pytest",
            "--duration-ms",
            "4200",
            "--input",
            "pytest -q",
            "--output",
            "1 passed",
        ],
    )
    assert result.returncode == 0
    telemetry = tmp_path / ".frob" / "telemetry.jsonl"
    record = json.loads(telemetry.read_text(encoding="utf-8").strip())
    assert record["tool"] == "pytest"
    assert record["duration_ms"] == 4200.0


def test_hook_exits_zero_on_valid_non_dict_json_array(tmp_path: Path):
    # frob:tests scripts/frob-telemetry-hook kind="integration"
    _init_repo(tmp_path)
    result = _run_hook(tmp_path, "[1, 2, 3]")
    assert result.returncode == 0
    assert result.stderr == ""
    assert not (tmp_path / ".frob" / "telemetry.jsonl").exists()


def test_hook_exits_zero_on_valid_non_dict_json_string(tmp_path: Path):
    # frob:tests scripts/frob-telemetry-hook kind="integration"
    _init_repo(tmp_path)
    result = _run_hook(tmp_path, '"hi"')
    assert result.returncode == 0
    assert result.stderr == ""
    assert not (tmp_path / ".frob" / "telemetry.jsonl").exists()


def test_hook_exits_zero_on_valid_non_dict_json_number(tmp_path: Path):
    # frob:tests scripts/frob-telemetry-hook kind="integration"
    _init_repo(tmp_path)
    result = _run_hook(tmp_path, "5")
    assert result.returncode == 0
    assert result.stderr == ""
    assert not (tmp_path / ".frob" / "telemetry.jsonl").exists()


def test_hook_redacts_secret_looking_input(tmp_path: Path):
    # frob:tests scripts/frob-telemetry-hook kind="integration"
    _init_repo(tmp_path)
    fake_key = "sk-ant-api03-" + ("a" * 95)
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": fake_key}, "tool_response": ""}
    )
    result = _run_hook(tmp_path, payload)
    assert result.returncode == 0
    telemetry = tmp_path / ".frob" / "telemetry.jsonl"
    text = telemetry.read_text(encoding="utf-8")
    assert fake_key not in text
