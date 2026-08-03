"""Per-test stability tracking and quarantine-with-ticket (docs/modules/testing.md's
Flake quarantine section, T-0575).

A flaky test blocks every parallel agent working through `frob test`: a
single intermittent failure looks the same as a real regression, so an
agent either wrongly reverts good work chasing it, or starts ignoring red
runs altogether (worse). This module gives `frob test` a per-test pass/fail
history (`.frob/test-stability.json`), a static flake-detection rule over
that history, and a quarantine mechanism that always carries a real ticket
id -- never a silent skip-list -- so a quarantined test still runs (and
still reports) but does not fail the gate, and an alarm fires if its ticket
closes while the test is still flaky.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/testing/_stability.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring describing already-implemented \
# internal behavior, verifiable by reading the code it annotates -- 'never a silent \
# skip-list' describes quarantine's ticket-required design, already enforced by \
# quarantine()'s own TicketUnresolvable/auto-file logic) rather than a separate \
# cross-module contract needing its own tracked invariant"

from __future__ import annotations

import json
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, ErrorSet, Ok
from typani.result import Result
from typani.unit import Unit

from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

_CAPTURE_TIMEOUT_S = 900.0

_STABILITY_REL = Path(".frob") / "test-stability.json"

# frob:doc docs/modules/testing.md#flake-quarantine-t-0575
#: bounded per-test outcome window: only the last N recorded runs count
#: toward flake detection or get persisted -- an old flake that has since
#: gone stable for N runs straight must not haunt the record forever, and
#: an unbounded history would grow `.frob/test-stability.json` without limit.
HISTORY_WINDOW = 20

#: a test needs at least this many recorded runs before flake detection
#: applies at all -- a single failure (possibly the test's very first run)
#: is not yet evidence of intermittency, just evidence of a failure.
_MIN_HISTORY_FOR_FLAKE = 2

#: a quarantined test needs at least this many recorded runs, ALL failing,
#: before it is treated as a hard regression rather than a flake still
#: settling right after quarantine (T-0636). One point higher than
#: `_MIN_HISTORY_FOR_FLAKE` on purpose: quarantining a test resets nothing
#: in its history, so the run or two immediately following quarantine can
#: still legitimately read as "all fail so far" without yet being proof the
#: flake has become a permanent regression -- this threshold is what keeps
#: that distinction from being a coin flip on the very next run.
_MIN_HISTORY_FOR_REGRESSION = 3

# frob:doc docs/modules/testing.md#flake-quarantine-t-0575
#: default width of the recent-tail-window hard-regression check (T-0679):
#: the last this-many recorded runs, all-fail, is enough to flag a hard
#: regression even when an older, now-irrelevant pass sits earlier in the
#: bounded `HISTORY_WINDOW` history and would otherwise defeat the
#: whole-window all-fail rule for up to `HISTORY_WINDOW - 1` further runs.
DEFAULT_REGRESSION_TAIL_K = 5

_PASS = "P"
_FAIL = "F"


# frob:doc docs/modules/testing.md#error-types
# frob:ticket T-1477
class FlakeError(ErrorSet):
    """Failure values this module's stability/quarantine functions can return."""

    __test__: bool = False

    WriteFailed = "Could not persist .frob/test-stability.json"
    ReadFailed = "Could not read/parse .frob/test-stability.json"
    UnknownTest = "The node id has no recorded stability history"
    TicketUnresolvable = "The named ticket id is absent from the queue"
    TicketCreateFailed = "Auto-filing a quarantine ticket via frob.tickets failed"
    CaptureSpawnFailed = "pytest could not be spawned for per-test stability capture"
    CaptureReadFailed = (
        "The junit-xml report from a stability capture run was unreadable"
    )


# frob:doc docs/modules/testing.md#data-models
class StabilityEntry(BaseModel):
    """One test's recent pass/fail history plus its quarantine state, if any."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    #: most-recent-last, each element "P" or "F", bounded to `HISTORY_WINDOW`.
    history: tuple[str, ...] = ()
    quarantine_ticket: str | None = None
    quarantined_at: str | None = None


def _entry_key(node_id: str) -> str:
    """The stable dict key for `node_id` (identity function today; named so
    every read/write site goes through one place if the key ever needs
    normalizing)."""
    return node_id


# frob:tests tests/unit/testing/test_stability.py::TestRecord.test_persists
# frob:doc docs/modules/testing.md#public-api
def load_stability(root: Path) -> dict[str, StabilityEntry]:
    """Every recorded `StabilityEntry`, keyed by node id; an absent or
    unreadable `.frob/test-stability.json` degrades to `{}` (no history yet
    is not an error -- every test starts with an empty record)."""
    path = root / _STABILITY_REL
    if not path.exists():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("load_stability: %s unreadable: %s", path, exc)
        return {}
    entries: dict[str, StabilityEntry] = {}
    for node_id, raw in doc.get("tests", {}).items():
        try:
            entries[node_id] = StabilityEntry.model_validate(raw)
        except ValueError as exc:
            _log.warning(
                "load_stability: dropping malformed entry %r: %s", node_id, exc
            )
    return entries


def _save_stability(
    root: Path, entries: Mapping[str, StabilityEntry]
) -> Result[Unit, FlakeError]:
    """The only writer of `.frob/test-stability.json`."""
    path = root / _STABILITY_REL
    doc = {"tests": {k: json.loads(v.model_dump_json()) for k, v in entries.items()}}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        _log.error("_save_stability: could not write %s: %s", path, exc)
        return Err(FlakeError.WriteFailed)
    return Ok(Unit())


# frob:tests tests/unit/testing/test_stability.py::TestRecord.test_persists
# frob:tests tests/unit/testing/test_stability.py::TestRecord.test_window_bounded
# frob:tests tests/unit/testing/test_stability.py::TestRecord.test_carries_quarantine
# frob:doc docs/modules/testing.md#public-api
def record_outcomes(
    root: Path, outcomes: Mapping[str, bool]
) -> Result[dict[str, StabilityEntry], FlakeError]:
    """Append one pass(`True`)/fail(`False`) observation per node id in
    `outcomes` onto its history (window-bounded to `HISTORY_WINDOW`),
    persist, and return the full updated map. A node id with no prior entry
    starts a fresh one. Quarantine fields are carried forward untouched --
    recording a run never lifts or grants quarantine, only `quarantine`/
    `lift_quarantine` do."""
    entries = load_stability(root)
    for node_id, passed in outcomes.items():
        key = _entry_key(node_id)
        prior = entries.get(key)
        mark = _PASS if passed else _FAIL
        history = ((prior.history if prior else ()) + (mark,))[-HISTORY_WINDOW:]
        entries[key] = StabilityEntry(
            node_id=node_id,
            history=history,
            quarantine_ticket=prior.quarantine_ticket if prior else None,
            quarantined_at=prior.quarantined_at if prior else None,
        )
    saved = _save_stability(root, entries)
    if saved.is_err:
        return Err(saved.danger_err)
    _log.info("record_outcomes: recorded %d test outcome(s)", len(outcomes))
    return Ok(entries)


# frob:tests tests/unit/testing/test_stability.py::TestIsFlaky.test_all_pass_ok
# frob:tests tests/unit/testing/test_stability.py::TestIsFlaky.test_all_fail_ok
# frob:tests tests/unit/testing/test_stability.py::TestIsFlaky.test_mixed_is_flaky
# frob:tests tests/unit/testing/test_stability.py::TestIsFlaky.test_single_run_ok
# frob:doc docs/modules/testing.md#public-api
def is_flaky(entry: StabilityEntry) -> bool:
    """The flake-detection rule: `entry`'s bounded history contains BOTH a
    pass and a fail (a fail-then-pass-on-retry, or any other intermittent
    mix across runs) -- a test that is consistently all-pass or all-fail is
    NOT flaky by this rule (an all-fail test is a real regression, not a
    flake, and must not be quarantine-eligible just by having enough
    history). Fewer than `_MIN_HISTORY_FOR_FLAKE` recorded runs is never
    flaky -- a single observation, pass or fail, is not yet evidence of
    intermittency."""
    if len(entry.history) < _MIN_HISTORY_FOR_FLAKE:
        return False
    seen = set(entry.history)
    return _PASS in seen and _FAIL in seen


# frob:tests tests/unit/testing/test_stability.py::TestIsFlaky.test_filters_map
# frob:doc docs/modules/testing.md#public-api
def flaky_node_ids(entries: Mapping[str, StabilityEntry]) -> frozenset[str]:
    """Every node id in `entries` whose history currently reads as flaky
    (`is_flaky`), quarantined or not."""
    return frozenset(node_id for node_id, entry in entries.items() if is_flaky(entry))


# frob:tests tests/unit/testing/test_stability.py::TestHardRegression.test_past_thresh
# frob:tests tests/unit/testing/test_stability.py::TestHardRegression.test_under_thresh
# frob:tests tests/unit/testing/test_stability.py::TestHardRegression.test_mixed
# frob:tests tests/unit/testing/test_stability.py::TestHardRegression.test_tail_stale
# frob:tests tests/unit/testing/test_stability.py::TestHardRegression.test_tail_short
# frob:tests tests/unit/testing/test_stability.py::TestHardRegression.test_tail_cfg
# frob:doc docs/modules/testing.md#flake-quarantine-t-0575
def is_hard_regression(
    entry: StabilityEntry, *, tail_k: int = DEFAULT_REGRESSION_TAIL_K
) -> bool:
    """The hard-regression rule (T-0636, widened by T-0679): true when
    EITHER `entry`'s entire bounded history (at least
    `_MIN_HISTORY_FOR_REGRESSION` runs) is all-fail, OR its most recent
    `tail_k` runs are all-fail (also gated by `_MIN_HISTORY_FOR_REGRESSION`
    as a floor, so a tiny `tail_k` cannot bypass the same settling-in
    protection the whole-window rule gets). The whole-window rule alone
    missed a real case: a single stale pass ANYWHERE in the bounded
    `HISTORY_WINDOW` (e.g. from before quarantine, or a one-off flake that
    never repeated) defeats all-fail detection for up to `HISTORY_WINDOW -
    1` subsequent all-fail runs even though the test has clearly gone
    permanently red since -- the recent-tail-window check catches that by
    looking only at the tail. `is_flaky` deliberately excludes an all-fail
    history from being a flake ("a real regression, not a flake"), but that
    exclusion by itself is silent -- nothing separately said a quarantined
    test in this state needs attention. This is that separate signal: a
    test can be quarantined for genuine intermittency, then regress to
    permanently failing, and by definition stop being flaky without the
    quarantine ever being lifted -- `is_hard_regression` is how callers
    (the gate, `hard_regression_alarms`) detect that and refuse to keep it
    green."""
    if len(entry.history) < _MIN_HISTORY_FOR_REGRESSION:
        return False
    if all(mark == _FAIL for mark in entry.history):
        return True
    effective_k = max(tail_k, _MIN_HISTORY_FOR_REGRESSION)
    if len(entry.history) < effective_k:
        return False
    tail = entry.history[-effective_k:]
    return all(mark == _FAIL for mark in tail)


# frob:tests tests/unit/testing/test_stability.py::TestQuarantine.test_explicit_ticket
# frob:doc docs/modules/testing.md#public-api
def quarantined_node_ids(entries: Mapping[str, StabilityEntry]) -> frozenset[str]:
    """Every node id in `entries` currently under quarantine (has a
    `quarantine_ticket`), regardless of its current flakiness -- lifting
    quarantine is a separate, explicit action (`lift_quarantine`), not an
    automatic consequence of the test going stable again."""
    return frozenset(
        node_id for node_id, entry in entries.items() if entry.quarantine_ticket
    )


def _ticket_is_open(root: Path, ticket_id: str) -> bool | None:
    """Whether `ticket_id` resolves in the queue and is not yet closed/dropped
    (any state before the terminal ones); `None` if the queue itself could
    not be loaded (caller must treat that as "cannot verify", not "open")."""
    from frob.tickets import TicketState, load_queue

    loaded = load_queue(root)
    if loaded.is_err:
        _log.warning(
            "_ticket_is_open: could not load ticket queue: %s", loaded.danger_err
        )
        return None
    ticket = loaded.danger_ok.tickets.get(ticket_id)
    if ticket is None:
        return None
    return ticket.state not in (TicketState.DONE, TicketState.DROPPED)


# frob:tests tests/unit/testing/test_stability.py::TestQuarantine.test_explicit_ticket
# frob:tests tests/unit/testing/test_stability.py::TestQuarantine.test_rejects_bad
# frob:tests tests/unit/testing/test_stability.py::TestQuarantine.test_auto_files
# frob:doc docs/modules/testing.md#public-api
def quarantine(
    root: Path, node_id: str, *, ticket_id: str | None = None
) -> Result[str, FlakeError]:
    """Quarantine `node_id`: excluded from failing the gate, but still run
    and still reported. NEVER a silent skip-list entry -- `ticket_id` must
    name a real, resolvable, still-open ticket; if `ticket_id` is omitted, a
    new bug ticket is auto-filed (via `frob.tickets.new_ticket`, the public
    ticket-creation surface, T-0575's mandate to route through the CLI/API
    surface rather than hand-writing `tickets.md`) recording the flaky node
    id so the flake is tracked, not just hidden. Returns the ticket id that
    now owns the quarantine."""
    resolved_ticket = ticket_id
    if resolved_ticket is None:
        filed = _file_quarantine_ticket(root, node_id)
        if filed.is_err:
            return Err(filed.danger_err)
        resolved_ticket = filed.danger_ok
    else:
        is_open = _ticket_is_open(root, resolved_ticket)
        if is_open is None:
            _log.error(
                "quarantine: ticket %r does not resolve in the queue", resolved_ticket
            )
            return Err(FlakeError.TicketUnresolvable)

    entries = load_stability(root)
    prior = entries.get(node_id)
    stamp = datetime.now(UTC).isoformat()
    entries[node_id] = StabilityEntry(
        node_id=node_id,
        history=prior.history if prior else (),
        quarantine_ticket=resolved_ticket,
        quarantined_at=stamp,
    )
    saved = _save_stability(root, entries)
    if saved.is_err:
        return Err(saved.danger_err)
    _log.info("quarantine: %s quarantined under %s", node_id, resolved_ticket)
    return Ok(resolved_ticket)


def _file_quarantine_ticket(root: Path, node_id: str) -> Result[str, FlakeError]:
    """Auto-file a bug ticket recording `node_id`'s flake, via the public
    `frob.tickets.new_ticket` API (never a hand-edit of `tickets.md`, and
    never touching `src/frob/tickets/**` internals -- T-0575's scope note)."""
    from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket

    spec = TicketSpec(
        title=f"flake quarantine: stabilize {node_id}",
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        body=(
            f"Auto-filed by `frob test`'s flake quarantine (T-0575): "
            f"`{node_id}` was observed both passing and failing across "
            f"recent runs with no related code change, and has been "
            f"quarantined (still runs, does not fail the gate) pending a fix."
        ),
    )
    created = new_ticket(root, spec)
    if created.is_err:
        _log.error(
            "quarantine: auto-file failed for %s: %s", node_id, created.danger_err
        )
        return Err(FlakeError.TicketCreateFailed)
    ticket_id = created.danger_ok.id
    _log.info("quarantine: auto-filed %s for flaky %s", ticket_id, node_id)
    return Ok(ticket_id)


# frob:tests tests/unit/testing/test_stability.py::TestQuarantine.test_lift_clears
# frob:tests tests/unit/testing/test_stability.py::TestQuarantine.test_lift_unknown_errs
# frob:doc docs/modules/testing.md#public-api
def lift_quarantine(root: Path, node_id: str) -> Result[Unit, FlakeError]:
    """Remove `node_id`'s quarantine (its history is kept -- only the
    quarantine fields are cleared). `Err(UnknownTest)` if `node_id` has no
    recorded entry at all."""
    entries = load_stability(root)
    prior = entries.get(node_id)
    if prior is None:
        _log.error("lift_quarantine: %s has no recorded history", node_id)
        return Err(FlakeError.UnknownTest)
    entries[node_id] = StabilityEntry(
        node_id=node_id,
        history=prior.history,
        quarantine_ticket=None,
        quarantined_at=None,
    )
    saved = _save_stability(root, entries)
    if saved.is_err:
        return Err(saved.danger_err)
    _log.info("lift_quarantine: %s un-quarantined", node_id)
    return Ok(Unit())


# frob:tests tests/unit/testing/test_stability.py::TestAlarms.test_closed_still_flaky
# frob:tests tests/unit/testing/test_stability.py::TestAlarms.test_no_alarm_open
# frob:tests tests/unit/testing/test_stability.py::TestAlarms.test_no_alarm_stable
# frob:doc docs/modules/testing.md#public-api
def quarantine_alarms(
    root: Path, entries: Mapping[str, StabilityEntry]
) -> tuple[str, ...]:
    """Node ids whose quarantine ticket has since closed (DONE or DROPPED)
    while the test is STILL flaky (`is_flaky`) -- this is the expiry alarm:
    the flake was never actually fixed, so the quarantine must not simply
    lapse into silent permanent cover. Ticket ids that fail to resolve (a
    typo, a renumbered ticket) are also alarmed -- an unresolvable ticket
    behind a quarantine is exactly the "silent skip-list" this module
    exists to prevent. Sorted for deterministic reporting. This is the
    EXPIRY alarm only -- a quarantined test that has regressed to all-fail
    (no longer flaky by `is_flaky`'s own rule, so it would never trip this
    alarm) is a DIFFERENT condition surfaced separately by
    `hard_regression_alarms` (T-0636); the two are not merged into one
    signal because they call for different responses (re-triage the ticket
    vs. the fix never landed at all)."""
    alarmed: list[str] = []
    for node_id, entry in entries.items():
        if entry.quarantine_ticket is None:
            continue
        if not is_flaky(entry):
            continue
        is_open = _ticket_is_open(root, entry.quarantine_ticket)
        if is_open is not True:
            alarmed.append(node_id)
    return tuple(sorted(alarmed))


# frob:tests tests/unit/testing/test_stability.py::TestAlarms.test_hard_alarm
# frob:tests tests/unit/testing/test_stability.py::TestAlarms.test_hard_no_alarm_flaky
# frob:tests tests/unit/testing/test_stability.py::TestAlarms.test_hard_alarm_tail
# frob:doc docs/modules/testing.md#flake-quarantine-t-0575
def hard_regression_alarms(
    entries: Mapping[str, StabilityEntry], *, tail_k: int = DEFAULT_REGRESSION_TAIL_K
) -> tuple[str, ...]:
    """Node ids currently quarantined whose history has regressed to a hard
    failure (`is_hard_regression`, `tail_k` forwarded so a caller can widen
    or narrow the recent-tail-window rule) -- T-0636's fix for the gap
    `quarantine_alarms` cannot cover: an all-fail history is BY DEFINITION
    not flaky, so it never enters `quarantine_alarms`'s `is_flaky` filter
    and would otherwise stay quarantined (and gate-green, see
    `evaluate_gate`) forever with no alarm at all -- a silent skip-list.
    Pure and root-independent (unlike `quarantine_alarms`, this needs no
    ticket-queue lookup: the regression is visible from the history alone).
    Sorted for deterministic reporting."""
    alarmed = [
        node_id
        for node_id, entry in entries.items()
        if entry.quarantine_ticket is not None
        and is_hard_regression(entry, tail_k=tail_k)
    ]
    return tuple(sorted(alarmed))


# frob:tests tests/unit/testing/test_stability.py::TestGate.test_already_ok_stays_ok
# frob:tests tests/unit/testing/test_stability.py::TestGate.test_all_quarantined_ok
# frob:tests tests/unit/testing/test_stability.py::TestGate.test_one_bad_stays_failed
# frob:tests tests/unit/testing/test_stability.py::TestGate.test_hard_regress_fails
# frob:tests tests/unit/testing/test_stability.py::TestGate.test_hard_regress_tail_fails
# frob:doc docs/modules/testing.md#public-api
def evaluate_gate(
    ok: bool,
    failing_node_ids: frozenset[str],
    entries: Mapping[str, StabilityEntry],
    *,
    tail_k: int = DEFAULT_REGRESSION_TAIL_K,
) -> bool:
    """Whether a test run's overall pass/fail (`ok`) should stand, once
    quarantine is accounted for: if `ok` is already `True`, unchanged; if
    `False`, it is promoted back to `True` only when EVERY failing node id
    is currently quarantined (`quarantined_node_ids`) AND not a hard
    regression (`is_hard_regression`, `tail_k` forwarded, T-0636/T-0679) --
    a quarantined test whose history has gone all-fail (whole-window or
    recent-tail-window) beyond the threshold is by definition no longer
    flaky, so quarantine status alone must not promote it back to green:
    that was the exact silent-skip-list gap this check closes. A single
    non-quarantined (or hard-regressed) failure among the losers keeps the
    run failed. Pure, no IO: callers gather `failing_node_ids` from their
    own per-test result capture and pass the already-loaded `entries` map
    in."""
    if ok:
        return True
    if not failing_node_ids:
        return ok
    quarantined = quarantined_node_ids(entries)
    hard_regressed = frozenset(
        node_id
        for node_id in quarantined
        if node_id in entries and is_hard_regression(entries[node_id], tail_k=tail_k)
    )
    excused = quarantined - hard_regressed
    return failing_node_ids <= excused


def _parse_junit_outcomes(
    report_path: Path, node_ids: tuple[str, ...]
) -> dict[str, bool]:
    """Per-test pass/fail from a `--junit-xml` report, keyed back onto the
    original `node_ids` by run order. KNOWN APPROXIMATION: junit's own
    `classname`/`name` attributes are pytest's dotted module path, not the
    `path::Class::method` node id this codebase's graph uses, so this zips
    `node_ids` against the report's `<testcase>` elements positionally
    (pytest preserves argv order in its junit output) rather than
    re-deriving each node id from junit's own naming -- a skipped testcase
    (e.g. `importorskip`) is dropped from the result entirely (neither pass
    nor fail is recorded for it, matching how a native-gated test that
    never ran should not count as flake evidence either way)."""
    try:
        tree = ET.parse(report_path)
    except (OSError, ET.ParseError) as exc:
        _log.warning("_parse_junit_outcomes: could not parse %s: %s", report_path, exc)
        return {}
    cases = tree.getroot().iter("testcase")
    outcomes: dict[str, bool] = {}
    for node_id, case in zip(node_ids, cases, strict=False):
        skipped = case.find("skipped") is not None
        if skipped:
            continue
        failed = case.find("failure") is not None or case.find("error") is not None
        outcomes[node_id] = not failed
    return outcomes


# frob:tests tests/unit/testing/test_stability.py::TestCapture.test_empty_ok
# frob:tests tests/unit/testing/test_stability.py::TestCapture.test_spawn_err
# frob:tests tests/unit/testing/test_stability.py::TestCapture.test_parses_junit
# frob:doc docs/modules/testing.md#public-api
def capture_python_outcomes(
    root: Path, node_ids: tuple[str, ...], *, cwd: str = "."
) -> Result[dict[str, bool], FlakeError]:
    """Run `node_ids` directly through `uv run pytest --junit-xml` (bypassing
    any configured `[[test.runner]]` template, which has no placeholder for
    a report path) and return each one's pass/fail, for stability tracking.
    A pytest failure exit code is expected data, not a spawn error -- only
    an actual spawn/timeout failure or an unparseable report is `Err`."""
    if not node_ids:
        return Ok({})
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "junit.xml"
        argv = [
            "uv",
            "run",
            "pytest",
            "-q",
            "--junit-xml",
            str(report_path),
            *node_ids,
        ]
        spawned = run_argv(argv, cwd=root / cwd, timeout_s=_CAPTURE_TIMEOUT_S)
        if spawned.is_err:
            _log.error("capture_python_outcomes: pytest failed to spawn in %s", root)
            return Err(FlakeError.CaptureSpawnFailed)
        if not report_path.exists():
            _log.error(
                "capture_python_outcomes: no junit report produced at %s", report_path
            )
            return Err(FlakeError.CaptureReadFailed)
        outcomes = _parse_junit_outcomes(report_path, node_ids)
    _log.info("capture_python_outcomes: captured %d outcome(s)", len(outcomes))
    return Ok(outcomes)


# frob:tests tests/unit/testing/test_stability.py::TestTrack.test_captures_then_records
# frob:doc docs/modules/testing.md#public-api
def track_python_stability(
    root: Path, node_ids: tuple[str, ...], *, cwd: str = "."
) -> Result[dict[str, StabilityEntry], FlakeError]:
    """Capture (`capture_python_outcomes`) and record (`record_outcomes`)
    `node_ids`' pass/fail in one call -- the single entry point a `frob
    test` invocation (or a scheduled stability sweep) needs to keep
    `.frob/test-stability.json` current."""
    captured = capture_python_outcomes(root, node_ids, cwd=cwd)
    if captured.is_err:
        return Err(captured.danger_err)
    return record_outcomes(root, captured.danger_ok)


__all__ = [
    "DEFAULT_REGRESSION_TAIL_K",
    "FlakeError",
    "HISTORY_WINDOW",
    "StabilityEntry",
    "capture_python_outcomes",
    "evaluate_gate",
    "flaky_node_ids",
    "hard_regression_alarms",
    "is_flaky",
    "is_hard_regression",
    "lift_quarantine",
    "load_stability",
    "quarantine",
    "quarantine_alarms",
    "quarantined_node_ids",
    "record_outcomes",
    "track_python_stability",
]
