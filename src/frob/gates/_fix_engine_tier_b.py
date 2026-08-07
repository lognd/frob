"""frob.gates._fix_engine_tier_b -- Tier-B transactional fix engine (T-1262).

Second tier of the T-1137 `--fix` epic, per docs/design/check-fix-engine.md's
"Transaction / rollback model" section: a Tier-B remedy is mechanical but
only SAFE conditionally on the rest of the tree, so it must be proven
correct by re-running its own declared `affected_gates`/`bound_tests`
before being kept -- apply, then PROVE, then keep or revert, never
apply-and-hope. This module owns the apply-verify-commit-or-rollback
engine itself (`apply_tier_b_fixes`) plus `TIER_B_HANDLERS`, the Tier-B
sibling of `_fix_engine.TIER_A_HANDLERS`; wiring a real `--fix` CLI entry
point to call this is a later batch of the same epic (this ticket's scope
is `src/frob/gates/_fix_engine_tier_b.py`/`tests/test_gates.py`, not
`src/frob/app/**`/`src/frob/_cli_parsers/**` -- the same split T-1138 drew
for Tier A).

Reference handler (T-1262's own acceptance note: "no concrete Tier-B
handler is required to exist yet beyond one minimal reference handler
proving the rollback path end-to-end -- a synthetic/test-fixture rule is
acceptable"): `fix_tierbdemo001_marker_rewrite` is that synthetic handler.
It scans for a `# frob:tierbdemo <replacement>` marker comment and
rewrites the marker's OWN line to `replacement`, verbatim -- deliberately
trivial, so this module's own tests can exercise the full commit and
rollback paths deterministically without depending on any real gate
rule's shape. A real Tier-B handler (release-sync-shaped, or any other
remedy whose safety depends on tree state) is a follow-up, out of this
ticket's own scope per its Plan section.

`apply_tier_b_fixes`'s `gate_runner`/`test_runner` keyword params default
to the real `run_gates`/subprocess-`pytest` implementations but accept an
injected fake for tests -- the same "default preserves real behavior,
override is test-only" shape `fix_fmt001_directive_wrap`'s `only_paths`
already established in `_fix_engine.py`. This lets this module's own
tests prove the commit/rollback DECISION LOGIC deterministically and
fast, without spawning a real `run_gates()`/pytest subprocess per test
(which would make the tier-B suite itself slow and gate-composition-
fragile) while the default arguments are exactly what a real `--fix`
caller gets.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from frob.gates._fix_engine import FixApplied
from frob.gates._models import GateConfig, Severity
from frob.graph import GraphSnapshot
from frob.process._guard import guarded_subprocess_run
from frob.tickets import TicketQueue

if TYPE_CHECKING:
    from frob.gates._models import GateReport

_log = logging.getLogger(__name__)


# frob:doc docs/design/check-fix-engine.md#transaction--rollback-model-tier-b
class TierBFix(BaseModel):
    """One Tier-B fix a handler has ALREADY applied to disk, plus the
    receipt the transaction engine needs to prove it safe: the pre-fix
    byte snapshot (`backup`, for a byte-for-byte revert) and the fixed,
    per-handler-declared `affected_gates`/`bound_tests` to re-run in
    order to decide commit vs. rollback (never recomputed at fix time --
    see `docs/design/check-fix-engine.md`'s own "a fixed, per-handler-
    declared list, never a guess computed at fix time" note)."""

    model_config = {}

    rule: str
    file: str
    line: int
    detail: str
    backup: bytes
    affected_gates: tuple[str, ...]
    bound_tests: tuple[str, ...]


# frob:doc docs/design/check-fix-engine.md#transaction--rollback-model-tier-b
class FixRolledBack(BaseModel):
    """The disclosed record of a Tier-B fix that regressed and was
    reverted byte-for-byte: which rule/site it was, and (`regression_
    detail`) WHICH gate or test newly failed and its own message -- never
    a silent revert."""

    model_config = {}

    rule: str
    file: str
    line: int
    regression_detail: str


#: One rule id -> one Tier-B handler, mirroring `_fix_engine.TIER_A_
#: HANDLERS`'s uniform `(root, snapshot, queue) -> list[...]` call shape
#: exactly (docs/design/check-fix-engine.md's "Fix-handler protocol"
#: section) so the fixability-registry-field ticket (T-1264) can
#: introspect this table by name the same way it introspects Tier A's.
TierBHandler = Callable[[Path, GraphSnapshot, TicketQueue], list[TierBFix]]


# ---------------------------------------------------------------------------
# TIERBDEMO001: synthetic reference handler proving the rollback path
# end-to-end (T-1262's own acceptance note quoted in the module docstring).
# Never registered against a real gate rule id -- "tierbdemo" is not, and
# must never become, a real `frob check` rule.
# ---------------------------------------------------------------------------

#: `# frob:tierbdemo <replacement text>` -- a single-line marker comment
#: this handler rewrites to `<replacement text>` verbatim. Deliberately
#: the simplest possible mechanical rewrite (a whole-line replace) so this
#: module's tests can construct both a "fix applies cleanly" and a "fix
#: regresses" fixture by controlling only what the INJECTED `gate_runner`/
#: `test_runner` report afterward, never by needing the rewrite itself to
#: be semantically risky.
_TIERBDEMO_MARKER_PREFIX = "# frob:tierbdemo "


# frob:doc docs/design/check-fix-engine.md#transaction--rollback-model-tier-b
# frob:tests \
# tests/test_gates.py::TestFixEngineTierB.test_clean_fix_commits_and_is_reported_fixed \
# kind="unit"
# frob:waive WIRE001 reason="synthetic reference handler, T-1262's own acceptance note \
# explicitly permits a synthetic/test-fixture rule to prove the Tier-B rollback path \
# end-to-end; 'TIERBDEMO001' is deliberately never a real frob check rule id (module \
# docstring), so it is intentionally absent from _KNOWN_GATE_RULES -- adding it there \
# would misrepresent it as something frob check itself can report" follow_up="T-1481"
# frob:waive EXHAUST003 reason="T-1262: leaked Unknown traces to \
# path.relative_to/iter_files, cross-module calls the resolver cannot see through; the \
# one documented raise path (OSError on read_text/write_text) is caught above"
# frob:waive EXHAUST002 reason="T-1262: KeyError is the resolver's conservative \
# over-approximation for plain list/index indexing (new_lines[idx]) inside this \
# function's own loop -- idx is always a valid enumerate() index into the same list, \
# never out of range"
def fix_tierbdemo001_marker_rewrite(
    root: Path, snapshot: GraphSnapshot, queue: TicketQueue
) -> list[TierBFix]:
    """Synthetic Tier-B reference handler (T-1262): for every file under
    `root` carrying a `# frob:tierbdemo <replacement>` marker line,
    snapshot the file's pre-fix bytes, rewrite that ONE line to
    `<replacement>`, and return a `TierBFix` declaring `affected_gates=
    ("tierbdemo",)` and `bound_tests=()` -- a placeholder gate id no real
    gate ever reports, matched only by whatever `gate_runner` a caller
    supplies (production callers get the real `run_gates`, which reports
    nothing for an unknown gate id and so never blocks a genuine commit;
    this module's own tests inject a fake to exercise both the commit and
    rollback paths deterministically). Proves the full snapshot-apply-
    verify-commit-or-rollback path end-to-end without depending on any
    real gate rule's shape, per this ticket's own acceptance note."""
    del snapshot, queue  # signature uniformity only; this demo scans root itself
    from frob.excludes import iter_files

    applied: list[TierBFix] = []
    for path in sorted(iter_files(root, suffix=".py")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _TIERBDEMO_MARKER_PREFIX not in text:
            continue
        lines = text.splitlines(keepends=True)
        for idx, line in enumerate(lines):
            stripped = line.rstrip("\n")
            if not stripped.startswith(_TIERBDEMO_MARKER_PREFIX):
                continue
            replacement = stripped[len(_TIERBDEMO_MARKER_PREFIX) :]
            newline = "\n" if line.endswith("\n") else ""
            new_line = replacement + newline
            if new_line == line:
                continue
            backup = text.encode("utf-8")
            new_lines = list(lines)
            new_lines[idx] = new_line
            new_text = "".join(new_lines)
            try:
                path.write_text(new_text, encoding="utf-8")
            except OSError:
                continue
            rel = path.relative_to(root).as_posix()
            # frob:waive WIRE001 reason="'TIERBDEMO001' is a deliberately synthetic \
            # reference-handler rule id (see this function's own docstring), never a \
            # real frob check rule -- it must stay OUT of _KNOWN_GATE_RULES on \
            # purpose, not be registered there" follow_up="T-1481"
            applied.append(
                TierBFix(
                    rule="TIERBDEMO001",
                    file=rel,
                    line=idx + 1,
                    detail=f"{stripped!r} -> {replacement!r}",
                    backup=backup,
                    affected_gates=("tierbdemo",),
                    bound_tests=(),
                )
            )
    return applied


#: The Tier-B sibling of `_fix_engine.TIER_A_HANDLERS` -- a rule id present
#: here must NEVER also appear in `TIER_A_HANDLERS`/`TIER_C_EMITTERS`
#: (T-1264's `FixabilityConflict` enforces this mechanically once it
#: lands). "tierbdemo" is a synthetic placeholder id, not a real gate
#: rule, and is deliberately excluded from `frob.gates._waive.
#: known_gate_rule_ids()` for exactly that reason -- it must never be
#: mistaken for something `frob check` itself can report.
# frob:doc docs/design/check-fix-engine.md#transaction--rollback-model-tier-b
TIER_B_HANDLERS: dict[str, TierBHandler] = {
    "TIERBDEMO001": fix_tierbdemo001_marker_rewrite,
}


# ---------------------------------------------------------------------------
# The transaction engine itself.
# ---------------------------------------------------------------------------


# frob:waive WIRE001 reason="apply_tier_b_fixes's own default gate_runner argument -- \
# only reachable once T-1481 wires a real --fix caller (or a test) that invokes \
# apply_tier_b_fixes without overriding gate_runner; the whole engine is deliberately \
# CLI-uncalled in this ticket's own scope" follow_up="T-1481"
def _real_gate_runner(root: Path, gates: frozenset[str]) -> "GateReport | None":
    """The production `gate_runner`: `run_gates` restricted to `gates`,
    or `None` if the run itself errored (a Tier-B commit can never trust
    a verification it could not even perform -- treated as a regression
    by the caller, same "prove-fresh-or-do-nothing" posture `_fix_engine.
    fix_waive004_stale_waiver` already established for its own self-
    manufactured run)."""
    from frob.gates import run_gates

    result = run_gates(GateConfig(root=str(root), gates=gates))
    if result.is_err:
        _log.error(
            "tier-b fixes: gate re-run for %s errored: %s",
            sorted(gates),
            result.danger_err,
        )
        return None
    return result.danger_ok


# frob:waive WIRE001 reason="apply_tier_b_fixes's own default test_runner argument -- \
# same CLI-uncalled-until-T-1481 disposition as _real_gate_runner above" \
# follow_up="T-1481"
def _real_test_runner(root: Path, bound_tests: tuple[str, ...]) -> tuple[bool, str]:
    """The production `test_runner`: a subprocess `pytest` invocation
    over exactly `bound_tests`' node ids -- `(True, "")` on an empty
    tuple (nothing bound, vacuously clean) or an all-pass run; `(False,
    <detail>)` otherwise, where `<detail>` is the tail of pytest's own
    stdout/stderr (no separate message-parsing layer; pytest's own
    failure summary IS the regression detail an agent needs)."""
    if not bound_tests:
        return True, ""
    argv = [
        sys.executable,
        "-m",
        "pytest",
        *bound_tests,
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    result = guarded_subprocess_run(
        argv, cwd=root, capture_output=True, text=True, timeout=540
    )
    if result.is_err:
        return False, f"pytest invocation refused: {result.danger_err}"
    proc = result.danger_ok
    if proc.returncode == 0:
        return True, ""
    tail = "\n".join((proc.stdout or "").splitlines()[-40:])
    return False, tail or f"pytest exited {proc.returncode}"


def _error_keys(report: "GateReport | None") -> frozenset[tuple[str, str, int]]:
    """`report`'s ERROR-severity violations, keyed `(rule, file, line)` --
    the comparison unit `_new_error_violations` diffs a before/after pair
    against. `None` (the re-run itself errored) yields an empty set,
    since `_new_error_violations`'s own `report is None` branch already
    treats a broken AFTER re-run as "everything is new"; a broken BEFORE
    re-run instead falls out of this empty set naturally -- every after-
    violation reads as new, which is the conservative (never falsely
    clean) direction to fail in either case."""
    if report is None:
        return frozenset()
    return frozenset(
        (v.rule, v.file, v.line)
        for v in report.violations
        if v.severity == Severity.ERROR
    )


def _new_error_violations(
    before: frozenset[tuple[str, str, int]], report: "GateReport | None"
) -> list[str]:
    """Every ERROR-severity violation in `report` keyed `(rule, file,
    line)` that was NOT already present in `before` -- `None` `report`
    (the re-run itself errored, `_real_gate_runner`'s own contract) is
    treated as "everything is new" (a single sentinel entry), since a
    re-run that could not even complete proves nothing and must never be
    read as clean."""
    if report is None:
        return ["gate re-run did not complete"]
    new: list[str] = []
    for violation in report.violations:
        if violation.severity != Severity.ERROR:
            continue
        key = (violation.rule, violation.file, violation.line)
        if key in before:
            continue
        new.append(
            f"{violation.rule} at {violation.file}:{violation.line}: "
            f"{violation.message}"
        )
    return new


# frob:waive EXHAUST003 reason="T-1262: leaked Unknown traces to Path.__truediv__ \
# (root / fix.file), a stdlib operator the resolver cannot see through; the one real \
# raise path (OSError on write_bytes) is caught below"
def _restore_backup(root: Path, fix: TierBFix) -> None:
    """Byte-for-byte revert of `fix`'s one touched file from its own
    pre-fix snapshot -- the ONLY write `apply_tier_b_fixes` performs on
    the rollback path, never a partial/best-effort rewrite."""
    path = root / fix.file
    try:
        path.write_bytes(fix.backup)
    except OSError:
        _log.error(
            "tier-b fixes: FAILED to restore %s from backup after a rollback "
            "decision -- the file may be left in its post-fix (unverified) state",
            path,
        )


# frob:waive EXHAUST003 reason="T-1262: leaked Unknown traces to Path.__truediv__ \
# (root / fix.file) plus the caller-supplied gate_runner, an injected callable the \
# resolver cannot see through; every real raise path (OSError on \
# read_bytes/write_bytes) is caught above"
def _pre_fix_baseline(
    root: Path,
    fix: TierBFix,
    gates: frozenset[str],
    gate_runner: Callable[[Path, frozenset[str]], "GateReport | None"],
) -> frozenset[tuple[str, str, int]]:
    """The TRUE pre-fix error-violation baseline for `fix`'s own
    `affected_gates`, split out of `_verify_and_decide_one_fix` to keep it
    under ARCH001's ceiling: a temporary revert-measure-restore around
    `fix.backup` -- write the pre-fix bytes back, run `gate_runner`, then
    restore the post-fix bytes this function itself read, never leaving
    the file in the reverted state past this one measurement (the
    handler already applied `fix`, per this module's own apply-then-
    report contract, so there is no OTHER way to see the tree as it stood
    immediately before this one fix)."""
    if not gates:
        return frozenset()
    target = root / fix.file
    try:
        post_bytes: bytes | None = target.read_bytes()
    except OSError:
        post_bytes = None
    if post_bytes is not None:
        try:
            target.write_bytes(fix.backup)
        except OSError:
            post_bytes = None
    before_keys = _error_keys(gate_runner(root, gates))
    if post_bytes is not None:
        try:
            target.write_bytes(post_bytes)
        except OSError:
            _log.error(
                "tier-b fixes: FAILED to restore %s to its post-fix bytes "
                "after measuring the pre-fix baseline -- left reverted",
                target,
            )
    return before_keys


def _verify_and_decide_one_fix(
    root: Path,
    fix: TierBFix,
    gate_runner: Callable[[Path, frozenset[str]], "GateReport | None"],
    test_runner: Callable[[Path, tuple[str, ...]], tuple[bool, str]],
) -> FixApplied | FixRolledBack:
    """`apply_tier_b_fixes`'s per-fix body, split out to keep the caller
    under ARCH001's function-length ceiling: verifies ONE already-applied
    `fix` (re-running its `affected_gates` before-and-after via
    `_pre_fix_baseline`, plus its `bound_tests`) and returns either a
    committed `FixApplied` or a `FixRolledBack` -- restoring `fix`'s file
    byte-for-byte on the rollback path as a side effect, per this
    module's own transaction contract."""
    gates = frozenset(fix.affected_gates)
    before_keys = _pre_fix_baseline(root, fix, gates, gate_runner)
    tests_ok, test_detail = test_runner(root, fix.bound_tests)
    after_report = gate_runner(root, gates) if gates else None
    new_errors = _new_error_violations(before_keys, after_report)
    if not tests_ok or new_errors:
        _restore_backup(root, fix)
        detail = "; ".join(
            part
            for part in (
                f"test(s) failed: {test_detail}" if not tests_ok else "",
                f"new error violation(s): {'; '.join(new_errors)}"
                if new_errors
                else "",
            )
            if part
        )
        _log.warning(
            "tier-b fixes: rolled back %s at %s:%s -- %s",
            fix.rule,
            fix.file,
            fix.line,
            detail,
        )
        return FixRolledBack(
            rule=fix.rule,
            file=fix.file,
            line=fix.line,
            regression_detail=detail or "unspecified regression",
        )
    return FixApplied(rule=fix.rule, file=fix.file, line=fix.line, detail=fix.detail)


# frob:doc docs/design/check-fix-engine.md#transaction--rollback-model-tier-b
# frob:waive WIRE001 reason="the Tier-B transaction engine's own public entry point -- \
# T-1262's scope is the engine itself (src/frob/gates/_fix_engine_tier_b.py, \
# tests/test_gates.py only), not the CLI wiring; T-1481 is the open follow-up ticket \
# that wires a real --fix caller to invoke this, mirroring apply_tier_a_fixes's own \
# T-1138/T-1260 split" follow_up="T-1481"
def apply_tier_b_fixes(
    root: Path,
    snapshot: GraphSnapshot,
    queue: TicketQueue,
    *,
    gate_runner: Callable[
        [Path, frozenset[str]], "GateReport | None"
    ] = _real_gate_runner,
    test_runner: Callable[
        [Path, tuple[str, ...]], tuple[bool, str]
    ] = _real_test_runner,
) -> tuple[list[FixApplied], list[FixRolledBack]]:
    """Apply every Tier-B fix `TIER_B_HANDLERS` ships, one handler at a
    time, verifying and committing-or-rolling-back EACH `TierBFix` before
    moving to the next -- never batched, per docs/design/check-fix-
    engine.md's own "a rollback never has to bisect more than one fix"
    rule.

    Per fix: `gate_runner` re-runs exactly the fix's own declared
    `affected_gates` TWICE -- once against the tree as it stood
    immediately before this fix was committed-or-rolled-back (the
    `before` baseline, so a PRE-EXISTING error the fix did not cause is
    never mistaken for a regression it introduced) and once after -- and
    `test_runner` runs its `bound_tests`. "Clean" means: no gate in
    `affected_gates` reports a NEW error-severity violation (`(rule, file,
    line)` not present in the `before` baseline) and every bound test
    passes. Clean -> the fix is kept, reported as a `FixApplied` (T-1137's
    "committed Tier-B is reported identically to Tier A" contract -- a
    caller never needs to branch on tier to read the output). NOT clean
    -> `fix.backup` is restored byte-for-byte and a `FixRolledBack` is
    recorded naming which gate/test regressed and its own message --
    disclosed, never silent. A rolled-back fix is NOT retried in the same
    invocation.

    Returns `(committed, rolled_back)`. Each handler's OWN returned list
    may already contain more than one already-applied `TierBFix` (mirrors
    `_fix_engine.TIER_A_HANDLERS`'s call shape); this engine still
    verifies and decides commit-vs-rollback for each one INDIVIDUALLY, in
    the order the handler returned them, before considering the next --
    so two fixes touching the SAME file within one handler call are still
    verified sequentially, one commit/rollback decision at a time, never
    as a merged batch."""
    committed: list[FixApplied] = []
    rolled_back: list[FixRolledBack] = []
    for handler in TIER_B_HANDLERS.values():
        fixes = handler(root, snapshot, queue)
        for fix in fixes:
            outcome = _verify_and_decide_one_fix(root, fix, gate_runner, test_runner)
            if isinstance(outcome, FixRolledBack):
                rolled_back.append(outcome)
            else:
                committed.append(outcome)
    return committed, rolled_back
