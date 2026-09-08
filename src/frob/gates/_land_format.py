"""frob.gates._land_format -- LANDFMT001 (T-4298).

T-4298's own measurement: `frob format`'s existing land-path absorption
(`_fmt_pre_land_step` in `frob.app.ticket_runner._land_cmd`) only ever
canonicalized `frob:` directive comment line-wrapping -- never `ruff
format` drift in actual Python source. The land-path formatting gate this
project runs (FMT001, `frob.gates._todo_fmt`) is diff-scoped to over-long
`frob:` directive lines by design and says so plainly in its own
docstring: it never scans a file's general code layout and a clean result
from it is not a claim the repository is formatter-clean. Nothing else on
the land path covered what that gate deliberately excludes, so ordinary
`ruff format` drift in a land's own changed files reached the integration
branch unnoticed, accumulating faster than the release-day tickets filed
to clear it could keep up (measured twice in one day: four files, then
six, after the four were cleared and several more lands landed new
drift).

THIS MODULE closes that gap the same way T-3456/T-3467's
`frob.gates._land_parity` closed its own: a pure `(root, touched_paths)`
function `run_gates` can dispatch, mirroring `_land_parity_diff`'s
`working_diff(root, "main")` posture exactly, so `frob check --ticket
<id>` in a ticket's own worktree sees the identical finding `frob ticket
land`'s own unscoped `frob check --json` spawn would refuse the land on
(`_land_cmd.py`'s pre-mutation gate pass, `_spawn_full_check_json`/
`_check_gate_findings_fn`) -- no change to `_land_cmd.py`/`_land.py`
themselves needed for the REFUSE half of this ticket's acceptance
criteria, and none made here: both files carry an in-progress lease held
by a sibling ticket (T-4281) at the time this ticket was scoped, so the
APPLY half (having the land absorb-fix the drift the way `_fmt_pre_land_
step` already does for directives, rather than only refuse on it) is
deliberately left as a `frob:todo`, not built in this change -- see that
directive below for the reasoning on the REFUSE-vs-APPLY design question
T-4298 raised.

DESIGN DECISION, RECORDED HERE PER T-4298's OWN ACCEPTANCE CRITERION 3:
REFUSE, not auto-apply, for now. `ruff format` is deterministic and this
project already auto-fixes other rule families (Tier-A) on the land path,
so an auto-apply absorption step (extending `_fmt_pre_land_step`'s
existing pattern to also run `ruff format` on the touched set, not just
`frob fmt`) is very likely still the right end state and is recorded as a
`frob:todo` immediately below. Refuse-first ships today, inside this
ticket's own scope, without touching the two files a live sibling ticket
holds a lease on; whoever picks up the auto-apply follow-up gets a
refusing gate already proving the touched-set detection is correct before
they wire a write path on top of it. See the `frob:todo` directive below
for the tracked follow-up."""

# frob:ticket T-4298
# Deferred: auto-apply LANDFMT001's drift the same way `_fmt_pre_land_step`
# already absorbs `frob:` directive drift, once `_land_cmd.py`'s scope
# lease is free -- extend `_absorb_pre_land_fixes` with a `ruff format`-
# on-touched-set step next to its existing `frob fmt` one, so a land
# REWRITES this drift instead of refusing on it, matching this project's
# existing Tier-A auto-fix posture.
# frob:todo T-4298

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import working_diff
from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.process._project_tool import project_tool_argv

_log = get_logger(__name__)


def _land_format_touched_py_files(root: Path) -> frozenset[str] | None:
    """The `.py` subset of `working_diff(root, "main")`'s touched files --
    the SAME diff source `_land_parity_diff` (`frob.gates._land_parity`)
    and `frob.app.ticket_runner._land_cmd._land_touched_paths` both use,
    so a `frob check` run in a ticket's own worktree sees the identical
    touched-file set the eventual land would diff against. `None` when
    the diff cannot be computed at all (no merge-base, detached HEAD, a
    `git` spawn failure) OR when it computes cleanly to an empty/all-non-
    Python touched set -- `land_format_gate` treats both the same way
    (`()`, no finding), matching every diff-scoped land-time check's own
    fail-open posture in this package."""
    diff_result = working_diff(root, "main")
    if diff_result.is_err:
        _log.debug(
            "land_format: could not compute the working diff (%s) -- "
            "skipping (unmeasured, not zero)",
            diff_result.danger_err,
        )
        return None
    touched = frozenset(
        hunk.file for hunk in diff_result.danger_ok.hunks if hunk.file.endswith(".py")
    )
    return touched or None


def _ruff_format_would_rewrite(
    root: Path, touched_py_files: frozenset[str]
) -> tuple[str, ...]:
    """Which of `touched_py_files` (repo-root-relative) `ruff format
    --check` would rewrite, as a sorted tuple -- `()` if none, if the
    files no longer exist on disk (a diff can name a since-deleted file),
    or if `ruff` itself is unavailable/disabled (T-0142/EXEC_KILL_SWITCH:
    an unmeasured tool is not a measured zero, but this gate's own
    fail-open posture already treats "could not measure" as "no finding"
    everywhere else in this module, so a missing/disabled `ruff` degrades
    the same way rather than refusing a land over a checker it cannot
    run).

    Scoped to `touched_py_files` explicitly, one `ruff format --check`
    invocation over exactly that list -- never a whole-tree scan -- per
    T-4298's own stated cost/attribution reasoning: proportional cost,
    and the person who introduced the drift is the one told, while it is
    still cheap to fix. `project_tool_argv` (T-3887/T-4125) resolves
    `ruff` through this project's own pinned venv, never a bare PATH
    lookup."""
    existing = sorted(rel for rel in touched_py_files if (root / rel).is_file())
    if not existing:
        return ()
    try:
        run_result = guarded_subprocess_run(
            project_tool_argv(root, "ruff", "format", "--check", *existing),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        _log.debug("land_format: ruff binary not found -- skipping (unmeasured)")
        return ()
    if run_result.is_err:
        _log.debug(
            "land_format: ruff format --check failed to run (%s) -- skipping "
            "(unmeasured)",
            run_result.danger_err,
        )
        return ()
    proc = run_result.danger_ok
    if not proc.returncode:
        return ()
    msg = (proc.stdout + proc.stderr).strip()
    return tuple(
        sorted(
            ln.replace("Would reformat ", "").strip()
            for ln in msg.splitlines()
            if "Would reformat" in ln
        )
    )


# frob:ticket T-4298
# frob:doc docs/modules/gates.md#land-format-landfmt001-t-4298
# frob:enforces CHK-GATE-LANDFMT001
# frob:tests \
# tests/unit/test_land_format_gate.py::test_diff_touched_unformatted_file_fires
# frob:tests \
# tests/unit/test_land_format_gate.py::test_already_formatted_touched_file_is_quiet
# frob:tests tests/unit/test_land_format_gate.py::test_no_diff_is_quiet
def land_format_gate(root: Path) -> tuple[Violation, ...]:
    """LANDFMT001 (T-4298): `ruff format --check`, scoped to this diff's
    OWN touched `.py` files (`_land_format_touched_py_files`) rather than
    a whole-tree scan -- closes the gap left by FMT001 (`frob.gates.
    _todo_fmt`), which by design only ever covers over-length `frob:`
    directive comment lines and never general code-layout drift, so a
    land could introduce a file `ruff format` would rewrite with nothing
    on the land path ever catching it before the next whole-tree
    integration run did. `()` when the touched set cannot be computed or
    is empty (`_land_format_touched_py_files` returned `None`), matching
    `land_parity_doc_test_gate`'s/`land_parity_long_function_gate`'s own
    fail-open posture for the identical "no diff to measure" case."""
    touched_py_files = _land_format_touched_py_files(root)
    if touched_py_files is None:
        return ()
    unformatted = _ruff_format_would_rewrite(root, touched_py_files)
    if not unformatted:
        return ()
    return tuple(
        Violation(
            rule="LANDFMT001",
            severity=Severity.ERROR,
            file=rel_path,
            line=1,
            message=(
                f"LANDFMT001: {rel_path} needs `ruff format` (T-4298) -- "
                f"this diff touches a file `ruff format` would rewrite; run "
                f"`frob format --code` and commit the result"
            ),
        )
        for rel_path in unformatted
    )


__all__ = ["land_format_gate"]
