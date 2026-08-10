"""CLI wiring for `frob profile show`/`frob profile downgrade` (T-1584):
the CLI surface `frob.tickets._profile.effective_profile`/
`downgrade_profile_ratchet` had no caller for -- T-1575's own module
docstring says outright "`frob profile downgrade` is the only way back",
but no such command existed until this ticket (WIRE001-waived with this
exact follow-up, `src/frob/tickets/_profile.py::downgrade_profile_ratchet`'s
own docstring).

`show` never mutates anything. `downgrade` requires a reason (inline
`--reason` or `--reason-file`, T-0737's shell-injection-avoidance
precedent) and is the ONLY caller of `downgrade_profile_ratchet` anywhere
in this package outside its own tests -- matching the module docstring's
"downgrades never automatic" contract exactly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


def _resolve_downgrade_reason(cfg: AppConfig) -> str | None:
    """Resolve `frob profile downgrade`'s `--reason`: `--reason-file` wins
    if given (read verbatim, T-0737), else the inline `--reason` string.
    Exits 1 if both are given (ambiguous which the caller meant) or the
    file cannot be read. Mirrors `frob.app.ticket_runner._new.
    _resolve_new_body`'s shape -- called exactly ONCE per invocation
    (T-2021's own lesson: a second read of a non-seekable `--reason-file`
    source silently returns empty)."""
    if cfg.profile_downgrade_reason_file is not None and cfg.profile_downgrade_reason:
        _log.error(
            "frob profile downgrade: --reason and --reason-file are "
            "mutually exclusive"
        )
        sys.exit(1)
    if cfg.profile_downgrade_reason_file is not None:
        try:
            text = cfg.profile_downgrade_reason_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "frob profile downgrade: could not read --reason-file %s: %s",
                cfg.profile_downgrade_reason_file,
                exc,
            )
            sys.exit(1)
        return text
    return cfg.profile_downgrade_reason


def _run_show(cfg: AppConfig, root: Path) -> None:
    """`frob profile show`: the configured profile, the effective profile
    (after the T-1575 auto-ratchet/T-1681 override are applied), and --
    when they differ -- the persisted ratchet's own reason/timestamp.
    Read-only; touches nothing on disk."""
    from frob.tickets._profile import configured_profile, effective_profile

    configured = configured_profile(root)
    if configured.is_err:
        _log.error("frob profile show: %s", configured.danger_err)
        sys.exit(1)
    effective = effective_profile(root)
    if effective.is_err:
        _log.error("frob profile show: %s", effective.danger_err)
        sys.exit(1)

    configured_name = configured.danger_ok.value
    effective_name = effective.danger_ok.value
    ratcheted = configured_name != effective_name

    if cfg.profile_json:
        payload = {
            "configured": configured_name,
            "effective": effective_name,
            "ratcheted": ratcheted,
        }
        _log.info(json.dumps(payload, indent=2))
        return

    if ratcheted:
        _log.info(
            "profile: configured=%s effective=%s (AUTO-RATCHETED -- "
            "`frob profile downgrade --reason ...` is the only way back)",
            configured_name,
            effective_name,
        )
    else:
        _log.info(
            "profile: configured=%s effective=%s (unratcheted)",
            configured_name,
            effective_name,
        )


def _run_downgrade(cfg: AppConfig, root: Path) -> None:
    """`frob profile downgrade --reason TEXT`: the ONLY sanctioned caller
    of `downgrade_profile_ratchet` -- an explicit, reasoned, loudly-logged
    decision, never invoked automatically anywhere in this package."""
    from frob.tickets._profile import downgrade_profile_ratchet

    reason = _resolve_downgrade_reason(cfg)
    if not reason:
        _log.error(
            "frob profile downgrade requires --reason TEXT or --reason-file PATH"
        )
        sys.exit(1)

    result = downgrade_profile_ratchet(root, reason=reason)
    if result.is_err:
        _log.error("frob profile downgrade: %s", result.danger_err)
        sys.exit(1)

    cleared = result.danger_ok
    if cfg.profile_json:
        _log.info(json.dumps({"cleared": cleared}, indent=2))
        return
    if cleared:
        _log.info("frob profile downgrade: ratchet cleared, reason=%r", reason)
    else:
        _log.info("frob profile downgrade: nothing was ratcheted -- no-op")


# frob:ticket T-1584
# frob:doc docs/modules/tickets.md#development-profiles-frobtoml-profile-t-1575
# frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerShow.test_show_reports_configured_and_effective  # noqa: E501
# frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade.test_downgrade_requires_a_reason  # noqa: E501
# frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade.test_downgrade_clears_a_real_ratchet  # noqa: E501
def run(cfg: AppConfig) -> None:
    """`frob profile show` / `frob profile downgrade --reason TEXT`
    (T-1584): wires `frob.tickets._profile`'s `effective_profile`/
    `downgrade_profile_ratchet` to a real CLI entrypoint -- neither had
    one before this ticket."""
    root = (cfg.profile_path or Path(".")).resolve()

    if cfg.profile_command == "downgrade":
        _run_downgrade(cfg, root)
        return

    # `show` is the default action (bare `frob profile` with no
    # sub-action, matching `frob registry`'s own bare-verb-defaults-to-
    # its-primary-read precedent) as well as the explicit `frob profile
    # show`.
    _run_show(cfg, root)
