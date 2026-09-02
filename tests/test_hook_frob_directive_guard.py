""".claude/hooks/frob-directive-guard.py: PreToolUse Write/Edit/NotebookEdit/
Bash hook that blocks a `frob:tests` directive using pytest's `Class::
method` collect-only separator instead of this graph's own `<file>::
<dotted qualname>` convention.

Subprocess-only, matching every other standalone-hook test file in this
directory (`tests/test_hook_root_write_guard.py`, `tests/test_hook_
frob_timeout_guard.py`) -- the hook is a standalone script outside the
`frob` package (a hyphenated filename is not even a valid Python module
name), so it is exercised through its real stdin/stdout/exit-code
contract, never imported directly.

T-3697: the `frob:tests Class::method` mistake (should be `Class.method`)
broke four different agents' lands this drive, each time surfacing only
post-land as a DOC007/DRIFT002 gate failure. This hook reuses DOC007's own
grammar (`src/frob/gates/_docptr.py::_DOUBLE_SEP_TESTS_TARGET_RE`: a
SECOND `::` anywhere in a `frob:tests` target is the recognized-wrong
shape) so the two never disagree about what counts as broken."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# frob:ticket T-3697
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-3697
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "frob-directive-guard.py"


# frob:waive DUP001 reason="each standalone-hook test file exercises a DIFFERENT \
# hook's real stdin/stdout subprocess contract independently (the same precedent \
# tests/ test_hook_root_write_guard.py's own _run_hook/_run_bash_hook and tests/ \
# test_hook_frob_timeout_guard.py's own _run_hook already carry, and each names as its \
# own reason); extracting a shared helper would couple three independently-evolving \
# hook test files to one shared module for a few lines of subprocess plumbing, not a \
# real behavioral duplication worth centralizing"
# frob:ticket T-3697
def _run_hook(tool_name: str, tool_input: dict):
    """Invoke the hook's real PreToolUse stdin/stdout contract for a
    `tool_name` call carrying `tool_input`."""
    payload = {"tool_name": tool_name, "tool_input": tool_input}
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


# frob:waive DUP001 reason="same precedent as _run_hook above -- \
# tests/test_hook_root_write_guard.py and tests/test_hook_frob_timeout_guard.py each \
# carry their own near-identical _denial_reason for the same reason: independent \
# standalone-hook subprocess contracts, not one shared behavior to centralize"
# frob:ticket T-3697
def _denial_reason(result) -> str | None:
    """The `permissionDecisionReason` string when the hook denied, else
    `None`."""
    out = result.stdout.strip()
    if not out:
        return None
    payload = json.loads(out)
    return payload.get("hookSpecificOutput", {}).get("permissionDecisionReason")


# frob:tests .claude/hooks/frob-directive-guard.py::main kind="integration"
# frob:ticket T-3697
def test_write_double_colon_in_symbol_is_blocked():
    """MUST-FIRE: `Write`ing a `frob:tests` directive with the pytest
    `Class::method` separator (`tests/x.py::TestA::test_b`) is blocked,
    and the denial names the corrected `tests/x.py::TestA.test_b` form."""
    result = _run_hook(
        "Write",
        {
            "file_path": "src/foo.py",
            "content": '# frob:tests tests/x.py::TestA::test_b kind="unit"\ndef f():\n    pass\n',
        },
    )
    reason = _denial_reason(result)
    assert reason is not None
    assert "tests/x.py::TestA.test_b" in reason


# frob:tests .claude/hooks/frob-directive-guard.py::main kind="integration"
# frob:ticket T-3697
def test_write_correct_dotted_form_is_allowed():
    """MUST-STAY-QUIET: the CORRECT form -- a single `::` splitting FILE
    from SYMBOL, then a dotted `Class.method` qualname -- is never
    blocked."""
    result = _run_hook(
        "Write",
        {
            "file_path": "src/foo.py",
            "content": '# frob:tests tests/x.py::TestA.test_b kind="unit"\ndef f():\n    pass\n',
        },
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-directive-guard.py::main kind="integration"
# frob:ticket T-3697
def test_write_with_no_directive_is_allowed():
    """MUST-STAY-QUIET: an ordinary edit carrying no `frob:tests`
    directive at all passes untouched."""
    result = _run_hook(
        "Write",
        {"file_path": "src/foo.py", "content": "def f():\n    return 1\n"},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-directive-guard.py::main kind="integration"
# frob:ticket T-3697
def test_edit_new_string_double_colon_is_blocked():
    """MUST-FIRE: the same mistake introduced via `Edit`'s `new_string`
    (not `old_string` -- the OLD text is not what is being introduced) is
    blocked."""
    result = _run_hook(
        "Edit",
        {
            "file_path": "src/foo.py",
            "old_string": "x = 1",
            "new_string": "# frob:tests tests/x.py::TestA::test_b\nx = 1",
        },
    )
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/frob-directive-guard.py::main kind="integration"
# frob:ticket T-3697
def test_edit_old_string_double_colon_is_not_blocked():
    """MUST-STAY-QUIET: the mistake sitting only in `old_string` (text
    being REMOVED, not introduced) never blocks -- only `new_string` is
    scanned."""
    result = _run_hook(
        "Edit",
        {
            "file_path": "src/foo.py",
            "old_string": "# frob:tests tests/x.py::TestA::test_b\nx = 1",
            "new_string": "x = 1",
        },
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-directive-guard.py::main kind="integration"
# frob:ticket T-3697
def test_bash_heredoc_writing_double_colon_directive_is_blocked():
    """MUST-FIRE: a `Bash` heredoc that would write the wrong-separator
    directive to a source file is blocked the same way -- this is the
    real shape a ticket-body or source edit reaches disk in this
    harness's tool surface."""
    command = "cat >> foo.py << 'EOF'\n# frob:tests tests/x.py::TestA::test_b\nEOF\n"
    result = _run_hook("Bash", {"command": command})
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/frob-directive-guard.py::main kind="integration"
# frob:ticket T-3697
def test_bash_unrelated_command_is_allowed():
    """MUST-STAY-QUIET: an ordinary command with no `frob:tests` directive
    text at all passes untouched."""
    result = _run_hook("Bash", {"command": "git status"})
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-directive-guard.py::main kind="integration"
# frob:ticket T-3697
def test_file_boundary_double_colon_alone_is_not_the_violation():
    """MUST-STAY-QUIET: a target with exactly ONE `::` (the FILE::SYMBOL
    boundary) and no further `::` in the symbol half -- even one naming a
    bare function with no class at all -- is never blocked. Proves the
    guard flags a SECOND `::`, not the presence of `::` itself."""
    result = _run_hook(
        "Write",
        {
            "file_path": "src/foo.py",
            "content": "# frob:tests tests/x.py::test_bare_function\ndef f():\n    pass\n",
        },
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/frob-directive-guard.py::main kind="integration"
# frob:ticket T-3697
def test_multiple_violations_all_named_in_denial():
    """MUST-FIRE: two separate wrong-separator directives in the same
    write are BOTH named in the denial with their corrected forms, not
    just the first."""
    content = (
        "# frob:tests tests/x.py::TestA::test_one\n"
        "def f():\n    pass\n\n\n"
        "# frob:tests tests/y.py::TestB::test_two\n"
        "def g():\n    pass\n"
    )
    result = _run_hook("Write", {"file_path": "src/foo.py", "content": content})
    reason = _denial_reason(result)
    assert reason is not None
    assert "tests/x.py::TestA.test_one" in reason
    assert "tests/y.py::TestB.test_two" in reason


# frob:tests .claude/hooks/frob-directive-guard.py::main kind="integration"
# frob:ticket T-3697
def test_unrecognized_tool_name_is_allowed():
    """MUST-STAY-QUIET: a tool this hook does not scan at all (e.g. a
    plain `Read`) is a silent no-op regardless of `tool_input` shape."""
    result = _run_hook("Read", {"file_path": "src/foo.py"})
    assert result.stdout.strip() == ""
