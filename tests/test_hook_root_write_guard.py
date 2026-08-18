""".claude/hooks/root-write-guard.py: PreToolUse Write/Edit/NotebookEdit
hook that refuses a dispatched agent's write into the shared root at edit
time.

Subprocess-only, matching `tests/test_hook_frob_timeout_guard.py`'s own
pattern -- the hook is a standalone script outside the `frob` package (a
hyphenated filename is not even a valid Python module name), so it is
exercised through its real stdin/stdout/exit-code contract, never imported
directly.

Every fixture here builds a REAL throwaway git repo with a REAL linked
worktree (`git worktree add`), because the hook's discriminator
(`_worktree_fact`) validates `FROB_WORKTREE` against actual
`git worktree list` output, not just the env var's presence -- a fake path
must NOT satisfy it. T-2396 acceptance criteria 1 and 2 are both must-fail
positive controls: the discriminator must fire for a simulated agent shell
and must NOT fire for a plain coordinator/human shell, against the exact
same write."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# frob:ticket T-2396
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-2396
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "root-write-guard.py"


# frob:ticket T-2396
def _git(args: list[str], cwd: Path) -> None:
    """Run a `git` command in `cwd`, raising on any non-zero exit -- test
    fixture plumbing only, not the hook's own logic."""
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


# frob:ticket T-2396
def _make_repo_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """Build a real throwaway git repo at `tmp_path/primary` with one real
    linked worktree SITED AS A SIBLING at `tmp_path/agent-wt`, and return
    both paths. T-2442: this topology alone is NOT this repo's real
    deployment shape (worktrees here nest under `.claude/worktrees/`
    INSIDE the primary checkout) -- keep this fixture for sibling-topology
    coverage, but see `_make_repo_with_nested_worktree` below for the
    shape that actually matters."""
    primary = tmp_path / "primary"
    primary.mkdir()
    _git(["init"], primary)
    _git(["config", "user.email", "t@example.com"], primary)
    _git(["config", "user.name", "T"], primary)
    (primary / "README.md").write_text("x\n", encoding="utf-8")
    _git(["add", "README.md"], primary)
    _git(["commit", "-m", "init"], primary)
    worktree = tmp_path / "agent-wt"
    _git(["worktree", "add", "-b", "agent-branch", str(worktree)], primary)
    return primary, worktree


# frob:ticket T-2442
def _make_repo_with_nested_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """Build a real throwaway git repo at `tmp_path/primary` with one real
    linked worktree NESTED INSIDE the primary checkout, at
    `primary/.claude/worktrees/agent-wt` -- this repo's actual deployment
    topology (see this repo's own `.claude/worktrees/` layout). T-2396's
    original fixture (`_make_repo_with_worktree`) only ever built the
    SIBLING shape, so its positive control passed against the pre-fix
    hook for the wrong reason: the pre-fix `..`-relpath-shape check
    happens to also classify a sibling-sited worktree as non-primary even
    with the bug present, and the bug (every write inside a NESTED
    worktree misclassified as a root write) never got exercised. This
    fixture reproduces the real topology instead of the abstract shape."""
    primary = tmp_path / "primary"
    primary.mkdir()
    _git(["init"], primary)
    _git(["config", "user.email", "t@example.com"], primary)
    _git(["config", "user.name", "T"], primary)
    (primary / "README.md").write_text("x\n", encoding="utf-8")
    _git(["add", "README.md"], primary)
    _git(["commit", "-m", "init"], primary)
    worktree = primary / ".claude" / "worktrees" / "agent-wt"
    worktree.parent.mkdir(parents=True)
    _git(["worktree", "add", "-b", "agent-branch", str(worktree)], primary)
    return primary, worktree


# frob:waive DUP001 reason="each standalone-hook test file exercises a DIFFERENT \
# hook's real stdin/stdout subprocess contract independently (this module's own \
# docstring names the precedent: tests/test_hook_frob_timeout_guard.py, \
# tests/test_hook_frob_suggest.py both carry their own near-identical _run_hook); \
# extracting a shared helper would couple three independently-evolving hook test files \
# to one shared module for a few lines of subprocess plumbing, not a real behavioral \
# duplication worth centralizing"
# frob:ticket T-2396
def _run_hook(
    *,
    cwd: Path,
    file_path: Path,
    env: dict[str, str],
    tool_name: str = "Write",
):
    """Invoke the hook's real PreToolUse stdin/stdout contract for a
    `tool_name` write to `file_path`, from `cwd`, under `env` (REPLACES the
    subprocess environment so `FROB_AGENT`/`FROB_WORKTREE` are controlled
    deterministically)."""
    key = "notebook_path" if tool_name == "NotebookEdit" else "file_path"
    payload = {
        "tool_name": tool_name,
        "tool_input": {key: str(file_path), "content": "x"},
        "cwd": str(cwd),
    }
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
        env=env,
    )


# frob:waive DUP001 reason="same precedent as _run_hook above -- \
# tests/test_hook_frob_suggest.py and tests/test_hook_frob_timeout_guard.py each carry \
# their own near-identical _denial_reason for the same reason: independent \
# standalone-hook subprocess contracts, not one shared behavior to centralize"
# frob:ticket T-2396
def _denial_reason(result) -> str | None:
    """The `permissionDecisionReason` string when the hook denied, else
    `None`."""
    out = result.stdout.strip()
    if not out:
        return None
    payload = json.loads(out)
    return payload.get("hookSpecificOutput", {}).get("permissionDecisionReason")


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2396
def test_agent_context_write_to_root_is_refused(tmp_path):
    """T-2396 acceptance criterion 1 (must-fail positive control): a
    simulated agent shell (real FROB_AGENT + real FROB_WORKTREE pointing at
    a REAL linked worktree) writing into the PRIMARY checkout is denied."""
    primary, worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "src.py",
        env={"FROB_AGENT": "1", "FROB_WORKTREE": str(worktree)},
    )
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2396
def test_worktree_fact_alone_is_sufficient_without_frob_agent(tmp_path):
    """The FACT-based half of the discriminator alone (FROB_WORKTREE
    resolving to a real linked worktree, FROB_AGENT unset) still fires --
    the exact gap T-2071 measured (FROB_AGENT unset in a real agent
    shell)."""
    primary, worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "src.py",
        env={"FROB_WORKTREE": str(worktree)},
    )
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2396
def test_coordinator_or_human_write_to_root_is_allowed(tmp_path):
    """T-2396 acceptance criterion 2 (must-fail positive control, other
    direction): the SAME write, with no FROB_AGENT/FROB_WORKTREE set at
    all (plain coordinator/human shell), is never refused."""
    primary, _worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(cwd=primary, file_path=primary / "src.py", env={})
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2396
def test_fake_frob_worktree_value_does_not_satisfy_the_fact_check(tmp_path):
    """A `FROB_WORKTREE` value that does NOT correspond to a real registered
    linked worktree (spoofed/stale) does not satisfy `_worktree_fact` on its
    own -- proves the check is a real FACT lookup, not a bare string
    presence check."""
    primary, _worktree = _make_repo_with_worktree(tmp_path)
    fake = tmp_path / "not-a-real-worktree"
    fake.mkdir()
    result = _run_hook(
        cwd=primary,
        file_path=primary / "src.py",
        env={"FROB_WORKTREE": str(fake)},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2396
def test_agent_write_inside_its_own_worktree_is_allowed(tmp_path):
    """The normal, correct case: an agent context writing INSIDE its own
    leased worktree (not the primary checkout) is never refused."""
    primary, worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=worktree,
        file_path=worktree / "src.py",
        env={"FROB_AGENT": "1", "FROB_WORKTREE": str(worktree)},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2442
def test_agent_write_inside_a_nested_worktree_is_allowed(tmp_path):
    """T-2442: the real deployment topology (worktree nested INSIDE the
    primary checkout, per T-2412's fix commit 39039b5f3) -- an agent
    write inside its own leased worktree there must be allowed, same as
    the sibling-sited case above. This is the exact fixture gap that let
    T-2396's original 9/9-green suite ship a hook denying every agent
    write in the fleet's real worktree layout: this must FAIL against the
    pre-fix hook (`git show 39039b5f3^:.claude/hooks/root-write-guard.py`)
    and PASS against current."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_hook(
        cwd=worktree,
        file_path=worktree / "src.py",
        env={"FROB_AGENT": "1", "FROB_WORKTREE": str(worktree)},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2396
def test_ledger_paths_are_exempt_even_for_an_agent(tmp_path):
    """`tickets.md`/`tickets/**` writes from an agent context into the
    primary checkout are exempt -- the `frob ticket` CLI's own ledger
    bookkeeping legitimately does this."""
    primary, worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "tickets.md",
        env={"FROB_AGENT": "1", "FROB_WORKTREE": str(worktree)},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2396
def test_frob_land_internal_exempts_an_agent_write(tmp_path):
    """`FROB_LAND_INTERNAL=1` (land's own internal escape hatch) exempts
    everything, matching every other land-owned-file guard (playbook
    section 4b)."""
    primary, worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "src.py",
        env={
            "FROB_AGENT": "1",
            "FROB_WORKTREE": str(worktree),
            "FROB_LAND_INTERNAL": "1",
        },
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2396
def test_non_guarded_tool_is_ignored(tmp_path):
    """A tool name outside {Write, Edit, NotebookEdit} (e.g. `Bash`) is
    never evaluated at all, even under a full agent context."""
    primary, worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "src.py",
        env={"FROB_AGENT": "1", "FROB_WORKTREE": str(worktree)},
        tool_name="Bash",
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2396
def test_notebook_edit_to_root_is_refused_for_an_agent(tmp_path):
    """`NotebookEdit`'s `notebook_path` key is resolved the same way
    `Write`/`Edit`'s `file_path` is."""
    primary, worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "nb.ipynb",
        env={"FROB_AGENT": "1", "FROB_WORKTREE": str(worktree)},
        tool_name="NotebookEdit",
    )
    assert _denial_reason(result) is not None
