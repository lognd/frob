""".claude/hooks/root-write-guard.py: PreToolUse Write/Edit/NotebookEdit/Bash
hook that refuses a write into the shared root at edit time.

Subprocess-only, matching `tests/test_hook_frob_timeout_guard.py`'s own
pattern -- the hook is a standalone script outside the `frob` package (a
hyphenated filename is not even a valid Python module name), so it is
exercised through its real stdin/stdout/exit-code contract, never imported
directly.

T-2850: the discriminator inverted. Before, a write into the primary
checkout was ALLOWED unless `FROB_AGENT`/`FROB_WORKTREE` (agent context)
was detected. Now it is DENIED unless one of a short, explicit allowlist
holds: `FROB_COORDINATOR=1` (the new opt-in marker), a ledger path,
`FROB_LAND_INTERNAL=1`, or the target resolving inside a REAL registered
linked worktree. Every fixture here builds a REAL throwaway git repo with
a REAL linked worktree (`git worktree add`), because the worktree-based
exemption validates against actual `git worktree list` output, not a
path-shape guess. The two must-fail positive controls this ticket cares
about most: a plain shell with NO markers at all writing to the root is
now REFUSED (the exact pre-worktree-agent gap T-2850 closes), and a
shell carrying the explicit `FROB_COORDINATOR=1` marker writing the
identical target is still ALLOWED."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# frob:ticket T-2850
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-2850
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "root-write-guard.py"


# frob:ticket T-2850
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


# frob:ticket T-2850
def _make_repo_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """Build a real throwaway git repo at `tmp_path/primary` with one real
    linked worktree SITED AS A SIBLING at `tmp_path/agent-wt`, and return
    both paths."""
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


# frob:ticket T-2850
def _make_repo_with_nested_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """Build a real throwaway git repo at `tmp_path/primary` with one real
    linked worktree NESTED INSIDE the primary checkout, at
    `primary/.claude/worktrees/agent-wt` -- this repo's actual deployment
    topology (see this repo's own `.claude/worktrees/` layout)."""
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
# frob:ticket T-2850
def _run_hook(
    *,
    cwd: Path,
    file_path: Path,
    env: dict[str, str],
    tool_name: str = "Write",
):
    """Invoke the hook's real PreToolUse stdin/stdout contract for a
    `tool_name` write to `file_path`, from `cwd`, under `env` (REPLACES the
    subprocess environment so markers are controlled deterministically)."""
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
# frob:ticket T-2850
def _denial_reason(result) -> str | None:
    """The `permissionDecisionReason` string when the hook denied, else
    `None`."""
    out = result.stdout.strip()
    if not out:
        return None
    payload = json.loads(out)
    return payload.get("hookSpecificOutput", {}).get("permissionDecisionReason")


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_no_marker_write_to_root_is_refused(tmp_path):
    """T-2850 acceptance criterion (must-fail positive control, the whole
    point of this ticket): a plain shell with NO markers set at all --
    the exact environment a dispatched agent carries BEFORE it ever runs
    `frob ticket work` -- writing into the PRIMARY checkout is denied. This
    is the case the pre-T-2850 discriminator could never see, because it
    is environmentally identical to a human/coordinator shell."""
    primary, _worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(cwd=primary, file_path=primary / "src.py", env={})
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_stale_agent_env_vars_do_not_exempt_a_root_write(tmp_path):
    """`FROB_AGENT`/`FROB_WORKTREE` (even a real, registered worktree) no
    longer exempt a ROOT write on their own -- T-2850 removed them from the
    decision entirely. Only `FROB_COORDINATOR`, a ledger path,
    `FROB_LAND_INTERNAL`, or the target itself being inside a worktree
    still allow."""
    primary, worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "src.py",
        env={"FROB_AGENT": "1", "FROB_WORKTREE": str(worktree)},
    )
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_coordinator_marker_allows_a_root_write(tmp_path):
    """T-2850's other must-pass positive control: the SAME write, from a
    shell carrying the explicit opt-in `FROB_COORDINATOR=1` marker, is
    never refused."""
    primary, _worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "src.py",
        env={"FROB_COORDINATOR": "1"},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_write_inside_a_real_worktree_is_allowed_with_no_markers(tmp_path):
    """The normal, correct case, with NO markers set at all: a write
    targeting a path INSIDE a real registered linked worktree (not the
    primary checkout) is never refused -- being inside your own worktree is
    itself sufficient, independent of any env var."""
    primary, worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=worktree,
        file_path=worktree / "src.py",
        env={},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_write_inside_a_nested_worktree_is_allowed(tmp_path):
    """The real deployment topology (worktree nested INSIDE the primary
    checkout) -- a write inside it is allowed with no markers set, same as
    the sibling-sited case above."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_hook(cwd=worktree, file_path=worktree / "src.py", env={})
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_fake_worktree_looking_path_does_not_exempt_a_root_write(tmp_path):
    """A `file_path` that merely LOOKS like it could be a worktree path but
    is not one of the repo's actually registered linked worktrees does not
    exempt a write -- proves the exemption is a real `git worktree list`
    fact, not a path-shape guess."""
    primary, _worktree = _make_repo_with_worktree(tmp_path)
    not_a_worktree = tmp_path / "not-a-real-worktree"
    not_a_worktree.mkdir()
    result = _run_hook(
        cwd=primary,
        file_path=not_a_worktree / "src.py",
        env={},
    )
    # Not under the primary checkout at all -- never refused, but also
    # never because it was treated as a worktree.
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_ledger_paths_are_exempt_with_no_markers(tmp_path):
    """`tickets.md`/`tickets/**` writes into the primary checkout are
    exempt even with no markers at all -- the `frob ticket` CLI's own
    ledger bookkeeping legitimately does this from a worktree context."""
    primary, _worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "tickets.md",
        env={},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_frob_land_internal_exempts_a_root_write_with_no_other_markers(tmp_path):
    """`FROB_LAND_INTERNAL=1` (land's own internal escape hatch) exempts
    everything, matching every other land-owned-file guard (playbook
    section 4b) -- unaffected by T-2850's default inversion."""
    primary, _worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "src.py",
        env={"FROB_LAND_INTERNAL": "1"},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_non_guarded_tool_is_ignored(tmp_path):
    """A tool name outside `_GUARDED_TOOLS` (e.g. `Grep`) is never
    evaluated at all, even with no markers set."""
    primary, _worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "src.py",
        env={},
        tool_name="Grep",
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_notebook_edit_to_root_is_refused_with_no_markers(tmp_path):
    """`NotebookEdit`'s `notebook_path` key is resolved the same way
    `Write`/`Edit`'s `file_path` is, and is refused by default same as
    them."""
    primary, _worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "nb.ipynb",
        env={},
        tool_name="NotebookEdit",
    )
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_refusal_names_the_recovery_recipe(tmp_path):
    """The refusal text itself carries the exact recovery recipe measured
    to work on the two incidents that motivated T-2850 -- git diff/apply
    --3way/bare checkout -- not just a pointer to `frob ticket work`."""
    primary, _worktree = _make_repo_with_worktree(tmp_path)
    result = _run_hook(cwd=primary, file_path=primary / "src.py", env={})
    reason = _denial_reason(result)
    assert reason is not None
    assert "git apply --3way" in reason
    assert "git checkout -- <paths>" in reason
    assert "FROB_COORDINATOR=1" in reason


# frob:ticket T-2850
def _run_bash_hook(*, cwd: Path, command: str, env: dict[str, str]):
    """Invoke the hook's real PreToolUse stdin/stdout contract for a `Bash`
    call running `command` from `cwd`, under `env`."""
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}
    return subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
        env=env,
    )


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_bash_ticket_verb_with_no_cd_no_path_no_marker_is_refused(tmp_path):
    """The exact incident shape -- `frob ticket land` (the one verb that
    genuinely writes non-ledger root content) run from the primary
    checkout, with neither a `cd` into a worktree, a `--path`, nor a
    resolvable `--worktree` flag, and NO markers set -- is refused.
    Fixture uses the REAL nested-worktree topology. T-2895 narrowed the
    Bash ticket-verb shape to `land` alone (every OTHER mutating verb is
    ledger-only and exempt -- see `test_bash_ledger_only_ticket_verb_
    is_allowed_with_no_markers_or_cd` below), so this is now the one
    must-still-refuse case for this shape."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command="timeout 540 uv run frob ticket land T-0001",
        env={},
    )
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_bash_ticket_verb_with_coordinator_marker_is_allowed(tmp_path):
    """The identical must-refuse `land` command from the previous test, run
    with `FROB_COORDINATOR=1` set, is never refused."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command="timeout 540 uv run frob ticket land T-0001",
        env={"FROB_COORDINATOR": "1"},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2895
def test_bash_ledger_only_ticket_verb_is_allowed_with_no_markers_or_cd(tmp_path):
    """T-2895 defect 3, must-now-pass: `frob ticket done-report` (a
    ledger-only mutating verb, never `land`) run from the primary checkout
    with no `cd`, no `--path`, and NO markers set is now ALLOWED -- matching
    the module docstring's and `REASON`'s standing claim that
    `tickets.md`/`tickets/**` writes are exempt, which previously held only
    for the `Write`/`Edit` tool path and never for this `Bash`-invoked CLI
    shape."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command="frob ticket done-report T-0001 --why done",
        env={},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_bash_ticket_verb_with_cd_into_worktree_is_allowed(tmp_path):
    """The identical command, prefixed with `cd <worktree> &&` in the SAME
    call, is never refused -- no markers needed, since the effective cwd
    itself resolves inside a real registered worktree."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command=f"cd {worktree} && frob ticket done-report T-0001 --why done",
        env={},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_bash_ticket_verb_with_explicit_path_flag_is_allowed(tmp_path):
    """An explicit `--path <worktree>` in the same call is never refused,
    even with no `cd`, no markers, and cwd still at the primary checkout
    (the same escape T-2481 established, unaffected by the inversion)."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command=f"frob ticket done-report T-0001 --why done --path {worktree}",
        env={},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_bash_redirect_into_primary_with_no_marker_is_refused(tmp_path):
    """A `>` redirect whose target resolves under the primary checkout,
    with no `cd` and no markers, is refused -- the second narrow shape
    T-2481 measured, still detected the same way post-inversion."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command="echo hi > notes.txt",
        env={},
    )
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_bash_redirect_inside_worktree_is_allowed_with_no_markers(tmp_path):
    """The identical redirect shape, `cd`'d into a real worktree first in
    the same call, is never refused -- no markers required."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command=f"cd {worktree} && echo hi > notes.txt",
        env={},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_bash_ambiguous_redirect_target_is_allowed(tmp_path):
    """A redirect whose target is a shell variable this hook cannot
    statically resolve is ALLOWED, not refused -- 'when in doubt, allow' as
    code, unaffected by the default inversion (this governs whether a
    target is IDENTIFIED at all, not what happens once it is)."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command='echo hi > "$OUTFILE"',
        env={},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_bash_read_only_ticket_verb_is_never_refused(tmp_path):
    """A read-only `frob ticket show` (not in `_MUTATING_TICKET_VERBS`) is
    never mistaken for a write, even from the primary checkout with no
    markers set."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command="frob ticket show T-0001",
        env={},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2850
def test_bash_unrelated_command_is_never_refused(tmp_path):
    """An ordinary read command with no ticket verb and no redirect at all
    is never evaluated as a write, from the primary checkout, no markers
    set."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command="git status",
        env={},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2860
def test_land_with_real_registered_worktree_is_allowed_with_no_markers(tmp_path):
    """The fleet-stopper this ticket fixes: `frob ticket land <id>
    --worktree <real registered worktree>`, run from the primary checkout
    with NO markers at all, is allowed -- landing IS a root write by
    design, and this is the exact shape T-2850 accidentally refused."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command=f"timeout 540 uv run frob ticket land T-0001 --worktree {worktree} --finish",
        env={},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2860
def test_land_with_unregistered_worktree_path_is_still_refused(tmp_path):
    """A `--worktree` naming a directory that is NOT an actual registered
    linked worktree gets no exemption -- the discriminator re-validates
    the real structural fact, it does not trust the flag's text alone."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    fake = primary / ".claude" / "worktrees" / "not-a-real-worktree"
    result = _run_bash_hook(
        cwd=primary,
        command=f"timeout 540 uv run frob ticket land T-0001 --worktree {fake} --finish",
        env={},
    )
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2860
def test_land_with_no_worktree_flag_is_still_refused(tmp_path):
    """`frob ticket land` with no `--worktree` at all is still refused --
    the exemption requires the flag to be present and to resolve."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command="timeout 540 uv run frob ticket land T-0001",
        env={},
    )
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2860
def test_non_land_mutating_verb_with_worktree_flag_is_still_refused(tmp_path):
    """`_is_legitimate_land`'s structural `--worktree` check is scoped to
    `land` alone -- a different mutating verb carrying a `--worktree`-
    shaped flag (not a real flag any other verb accepts) never goes
    through that check at all. Since T-2895 that verb is allowed anyway
    (it is ledger-only, exempt independent of any flag) -- covered by
    `test_bash_ledger_only_ticket_verb_is_allowed_with_no_markers_or_cd`
    above. `land`'s own structural requirement (a flag that must resolve
    to a REAL registered worktree, never trusted by text alone) is what
    stays refused without it -- see `test_land_with_no_worktree_flag_is_
    still_refused` and `test_land_with_unregistered_worktree_path_is_
    still_refused` below."""
    primary, worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_bash_hook(
        cwd=primary,
        command=f"frob ticket done-report T-0001 --why done --worktree {worktree}",
        env={},
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2895
def test_bash_redirect_target_outside_repo_via_home_relative_path_is_allowed(tmp_path):
    """T-2895 defect 1, must-now-pass: a Bash write whose real target is
    OUTSIDE the repo entirely, expressed as a home-relative (`~/...`)
    path, issued with cwd AT the primary checkout root, is ALLOWED. Before
    the fix, `os.path.isabs("~/x")` is `False`, so the target was joined
    onto the primary checkout instead of expanded, falsely resolving
    under it -- the exact "refused solely because cwd is the repo root"
    defect measured against a real coordinator/agent session."""
    monkeypatch_home = tmp_path / "fakehome"
    monkeypatch_home.mkdir()
    outside_dir = monkeypatch_home / "notes"
    outside_dir.mkdir()
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    env = {"HOME": str(monkeypatch_home)}
    result = _run_bash_hook(
        cwd=primary,
        command="cat > ~/notes/scratch.md <<'EOF'\nx\nEOF",
        env=env,
    )
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2895
def test_bash_redirect_target_inside_primary_via_home_relative_path_is_still_refused(
    tmp_path,
):
    """T-2895 must-still-fire control (the narrowing proof this ticket
    requires alongside the must-now-pass case above): a `~`-expressed
    target that genuinely resolves INSIDE the primary checkout (HOME
    pointed at the primary checkout's own parent, target under the
    checkout itself) is still refused -- `~`-expansion narrows false
    refusals, it does not create a new blind spot for a real root
    write expressed with a leading `~`."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    env = {"HOME": str(primary.parent)}
    result = _run_bash_hook(
        cwd=primary,
        command=f"cat > ~/{primary.name}/notes.txt <<'EOF'\nx\nEOF",
        env=env,
    )
    assert _denial_reason(result) is not None


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2895
def test_coordinator_marker_file_allows_a_root_write_with_no_env_var(tmp_path):
    """T-2895 defect 2, must-now-pass: `.frob/coordinator-mode` present on
    disk under the PRIMARY checkout, with `FROB_COORDINATOR` absent from
    the environment entirely, allows a root write -- the mechanism that
    actually works when the hook runs as a separately-spawned process that
    never inherits a Bash tool call's own `export`."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    (primary / ".frob").mkdir(exist_ok=True)
    (primary / ".frob" / "coordinator-mode").touch()
    result = _run_hook(cwd=primary, file_path=primary / "src.py", env={})
    assert result.stdout.strip() == ""


# frob:tests .claude/hooks/root-write-guard.py::main kind="integration"
# frob:ticket T-2895
def test_env_var_alone_still_works_when_genuinely_inherited(tmp_path):
    """The env-var marker is kept, not removed, for the case where
    inheritance genuinely does hold (a direct child process, or a test
    harness like this one) -- `FROB_COORDINATOR=1` with no marker file
    still allows a root write."""
    primary, _worktree = _make_repo_with_nested_worktree(tmp_path)
    result = _run_hook(
        cwd=primary,
        file_path=primary / "src.py",
        env={"FROB_COORDINATOR": "1"},
    )
    assert result.stdout.strip() == ""
