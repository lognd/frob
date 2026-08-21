"""Post-command footgun-tip advisories (T-1360), split out of the former
monolithic `telemetry.py` by T-2694 (T-1656 LARGE001 successor): a
distinct read-then-render concern with its own opt-out env var
(`FROB_NO_FOOTGUN_TIPS` vs `FROB_NO_TELEMETRY`), reading the SAME
event corpus `frob.app.telemetry` (event recording, this package's
`__init__.py`) writes rather than owning its own storage. Re-exported
from `frob.app.telemetry` unchanged (see that module's own docstring)
so no pre-existing caller needs editing."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from frob.logging import get_logger

from . import (
    _external_path_arg_hash,
    _home_config_state_hash,
    _telemetry_path,
    is_disabled,
)

_log = get_logger(__name__)

# frob:ticket T-1360
_NO_FOOTGUN_TIPS_ENV = "FROB_NO_FOOTGUN_TIPS"
"""Opt-out env var for footgun tips specifically -- distinct from
`FROB_NO_TELEMETRY`, which also stops recording. A caller may want the
corpus recorded but not the post-command nag."""

# frob:ticket T-1360
_SUPPRESS_TIPS_ENV = "FROB_SUPPRESS_TIPS"
"""Comma-separated rule ids (e.g. `FAST_EXIT1,REDUNDANT_RERUN`) individually
suppressed -- a tip that nags gets ignored, which is worse than no tip
(T-1360's own delivery requirement)."""

# frob:ticket T-1360
_FAST_EXIT_MS = 2000.0
"""Duration threshold under which a nonzero exit is flagged as `FAST_EXIT1`
-- short enough that the command plausibly failed before doing real work,
per T-1360's corpus mining (756 such runs)."""

# frob:ticket T-1360
_REDUNDANT_LOOKBACK = 200
"""How many trailing telemetry records `detect_footguns` scans for a prior
identical (subcommand, args_head, tree_hash) or repeated-failure match --
bounded so detection stays O(1)-ish relative to a large corpus rather than
re-reading the whole file every invocation."""

# frob:ticket T-1360
_REPEATED_FAILURE_STREAK = 3
"""Consecutive identical failing invocations (same subcommand + args_head,
each nonzero exit, no successful run of the same command in between)
required before `REPEATED_FAILURE` fires -- one or two retries is normal
iteration, three in a row with no change is stuck."""


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_render_tips_human_readable_names_the_rule  # noqa: E501
class Tip(BaseModel):
    """One footgun-detector finding (T-1360): a command that completed but
    looked like a different result than what actually happened (silently
    redundant, silently erroring fast, silently under-verified, silently
    stuck). Printed AFTER the command it concerns, never blocking it;
    `--json`-serializable so an agent -- the primary consumer per the
    ticket -- can parse and self-correct rather than relying on a
    human-styled hint."""

    model_config = {}

    rule_id: str
    message: str
    suggested_command: str | None = None


# frob:ticket T-1360
def _suppressed_rule_ids() -> frozenset[str]:
    """Rule ids named in `FROB_SUPPRESS_TIPS` (comma-separated), normalized
    to upper case -- an empty/unset env yields an empty set, suppressing
    nothing."""
    raw = os.environ.get(_SUPPRESS_TIPS_ENV, "")
    return frozenset(part.strip().upper() for part in raw.split(",") if part.strip())


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_detect_footguns_returns_empty_when_tips_disabled  # noqa: E501
def tips_disabled() -> bool:
    """True when tips are opted out entirely via `FROB_NO_FOOTGUN_TIPS`
    (any non-empty, non-`0`/`false` value) or telemetry itself is disabled
    (`is_disabled()`) -- no corpus, no detection."""
    if is_disabled():
        return True
    value = os.environ.get(
        _NO_FOOTGUN_TIPS_ENV, ""
    )  # frob:waive SEC110 reason="opt-out flag, not a secret"
    return value.strip().lower() not in ("", "0", "false")


# frob:ticket T-1360
def _read_recent_cli_events(root: Path, limit: int) -> list[dict[str, Any]]:
    """Up to `limit` most recent `kind=\"cli\"` records from `root`'s
    telemetry stream, oldest first. Missing/unreadable file yields an empty
    list -- detection is best-effort, same as recording itself."""
    path = _telemetry_path(root)
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _log.debug("telemetry: read failed (ignored): %s", exc)
        return []
    events: list[dict[str, Any]] = []
    for line in lines[-limit * 4 :]:  # cli + ticket records interleaved; overscan
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("kind") == "cli":
            events.append(record)
    return events[-limit:]


# frob:ticket T-1360
def _tip_redundant_rerun(
    history: list[dict[str, Any]],
    *,
    root: Path,
    subcommand: str,
    args_head: str,
    tree_hash_value: str,
) -> Tip | None:
    """`REDUNDANT_RERUN`: an EARLIER `history` record shares this run's
    `(subcommand, args_head, tree_hash, home_config_hash,
    external_path_hash)` exactly -- ONLY the state this repo knows a verb
    can read (the repo tree, `~/.claude` via T-2191's `_home_config_state_
    hash`, AND any external PATH argument the command line itself names,
    T-2204's `_external_path_arg_hash`) is unchanged, so this run's result
    could not have differed. Still not omniscient: a verb with a real
    out-of-repo input this cannot see at all (a different env var, a
    different external service, a positional argument that is not
    PATH-shaped) is not covered by any of the three digests -- this is a
    strictly TIGHTER key than pre-T-2204's pair, not a complete one; it
    removes the two measured false-positive classes (`frob claude sync
    --check`, and T-2204's `frob cycle <external-fixture>`) without
    claiming to remove every possible one."""
    home_config_hash_value = _home_config_state_hash()
    external_path_hash_value = _external_path_arg_hash(root, args_head)
    for prior in reversed(history):
        if (
            prior.get("subcommand") == subcommand
            and prior.get("args_head") == args_head
            and prior.get("tree_hash") == tree_hash_value
            and prior.get("home_config_hash") == home_config_hash_value
            and prior.get("external_path_hash") == external_path_hash_value
        ):
            return Tip(
                rule_id="REDUNDANT_RERUN",
                message=(
                    f"you ran 'frob {args_head}' at this exact "
                    f"tree state (tree_hash={tree_hash_value}) before, at "
                    f"{prior.get('iso_ts', 'an earlier time')}; nothing has "
                    "changed since -- this run could not have produced a "
                    "different result."
                ),
                suggested_command=None,
            )
    return None


# frob:ticket T-1360
def _tip_fast_exit1(
    *, args_head: str, duration_ms: float, exit_code: int
) -> Tip | None:
    """`FAST_EXIT1`: this run itself exited nonzero in under `_FAST_EXIT_MS`
    -- the trap T-1360's own coordinator incident hit (a 0.77s error read
    as a 180x speedup)."""
    if exit_code == 0 or duration_ms >= _FAST_EXIT_MS:
        return None
    return Tip(
        rule_id="FAST_EXIT1",
        message=(
            f"'frob {args_head}' exited with an ERROR "
            f"(exit={exit_code}) in {duration_ms:.0f}ms; it did NOT do the "
            "work you may think it did -- a fast failure is not a fast "
            "success."
        ),
        suggested_command=None,
    )


# frob:ticket T-1360
def _tip_repeated_failure(
    history: list[dict[str, Any]],
    *,
    subcommand: str,
    args_head: str,
    exit_code: int,
) -> Tip | None:
    """`REPEATED_FAILURE`: this run is the Nth (>= `_REPEATED_FAILURE_STREAK`)
    consecutive failure of the identical `(subcommand, args_head)` in
    `history` with no intervening success -- stuck, not progressing."""
    if exit_code == 0:
        return None
    streak = 1
    for prior in reversed(history):
        if prior.get("subcommand") != subcommand or prior.get("args_head") != args_head:
            continue
        if prior.get("exit") == 0:
            break
        streak += 1
        if streak >= _REPEATED_FAILURE_STREAK:
            break
    if streak < _REPEATED_FAILURE_STREAK:
        return None
    return Tip(
        rule_id="REPEATED_FAILURE",
        message=(
            f"'frob {args_head}' has now failed "
            f"{streak} times in a row with no successful run in "
            "between -- this looks stuck, not progressing; "
            "re-running the identical command is unlikely to help."
        ),
        suggested_command=None,
    )


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_detect_footguns_flags_redundant_rerun
# frob:tests tests/test_telemetry.py::test_detect_footguns_respects_suppress_env
def detect_footguns(
    root: Path,
    *,
    subcommand: str,
    args_head: str,
    duration_ms: float,
    exit_code: int,
    tree_hash_value: str,
) -> list[Tip]:
    """Footgun tips for the CLI invocation just completed (T-1360),
    evaluated against the trailing telemetry corpus. Three of the ticket's
    named rules are implemented here, one per `_tip_*` helper (the fourth,
    coverage-number misuse, ties to T-1335 and is out of this ticket's
    scope per its own Description): `REDUNDANT_RERUN`, `FAST_EXIT1`,
    `REPEATED_FAILURE` -- see each helper's own docstring.

    Suppressed rule ids (`FROB_SUPPRESS_TIPS`) are filtered out before
    returning. Returns `[]` when tips are disabled (`tips_disabled()`) --
    callers should check that first to skip the read entirely, but this
    function re-derives nothing unsafe if called anyway."""
    if tips_disabled():
        return []
    suppressed = _suppressed_rule_ids()
    history = _read_recent_cli_events(root, _REDUNDANT_LOOKBACK)

    candidates = (
        _tip_redundant_rerun(
            history,
            root=root,
            subcommand=subcommand,
            args_head=args_head,
            tree_hash_value=tree_hash_value,
        ),
        _tip_fast_exit1(
            args_head=args_head, duration_ms=duration_ms, exit_code=exit_code
        ),
        _tip_repeated_failure(
            history, subcommand=subcommand, args_head=args_head, exit_code=exit_code
        ),
    )
    return [
        tip for tip in candidates if tip is not None and tip.rule_id not in suppressed
    ]


# frob:ticket T-1360
# frob:doc docs/guides/agentic-time-profiling.md#public-api
# frob:tests tests/test_telemetry.py::test_render_tips_json_is_parseable
# frob:tests tests/test_telemetry.py::test_render_tips_empty_list_is_empty_string
def render_tips(tips: list[Tip], *, as_json: bool) -> str:
    """`tips` formatted for post-command display: one `model_dump_json`
    array when `as_json` (the machine-readable form T-1360 requires so an
    agent can self-correct), else one human-readable `[RULE_ID] message`
    line per tip. Returns `\"\"` for an empty list either way -- callers
    should skip printing entirely rather than print an empty JSON array,
    to avoid corrupting a `--json` command's own stdout (same discipline
    as `record_cli_event`'s `quiet_stdout_logs` requirement)."""
    if not tips:
        return ""
    if as_json:
        return json.dumps([t.model_dump() for t in tips])
    return "\n".join(f"[{t.rule_id}] {t.message}" for t in tips)
