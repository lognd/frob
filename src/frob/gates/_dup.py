"""frob.gates._dup -- DUP001/DUP002/DUP003 clone-detection gate (T-1174).

Split out of `frob.gates.__init__` (T-1072/T-1140/T-1159/T-1170/T-1174
one-family-per-land discipline) so the parent module can keep dropping
toward the large-file threshold without changing any public behavior.
`dup_gate` is re-exported from `frob.gates` unchanged -- it is the only
name this family is externally imported by (`tests/test_gates.py`, prose
references in `frob.dup._models`/`frob.app.config`), verified by a
repo-wide grep before the move; `_dup_config`/`_dup_gate_violations` stay
private to this module, never imported elsewhere.

One cohesive family: `_dup_config` reads `[dup]` frob.toml knobs,
`dup_gate` applies the opt-in/fail-closed policy (T-0399, INV-011) around
them, and `_dup_gate_violations` does the actual `find_clones` call and
DUP001/DUP002 translation -- all three exist only to serve `dup_gate`,
with no shared runtime state beyond that.
"""
# frob:ticket T-1174

from __future__ import annotations

import tomllib
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.graph import GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)


def _dup_config(root: Path) -> tuple[bool, float, bool, bool]:
    """`([dup].enforce, [dup].threshold, [dup].region_kernel,
    [dup].native_rungs)` from frob.toml, defaulting to off/0.85/off/off.

    `region_kernel` gates the R1.5 exact-region kernel (`frob.dup.
    DupConfig.region_kernel_enabled`) independently of `enforce` -- turning
    on the whole-symbol rung ladder does not by itself pay for the extra
    suffix-array pass; both knobs must be true for R1.5 to run in the gate
    path. `native_rungs` (T-0974) gates the R3/R4/R5 native fingerprint
    rungs (`frob.dup.DupConfig.native_rungs_enabled`) the same way --
    measured cold-cache cost of those rungs at whole-snapshot scale is
    what kept `[dup].enforce` off by default (T-0399/T-0974); R1/R2 alone
    are cheap enough to enforce by default.
    """
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return False, 0.85, False, False
    try:
        with toml_path.open("rb") as fh:
            dup_cfg = tomllib.load(fh).get("dup", {})
        return (
            bool(dup_cfg.get("enforce", False)),
            float(dup_cfg.get("threshold", 0.85)),
            bool(dup_cfg.get("region_kernel", False)),
            bool(dup_cfg.get("native_rungs", False)),
        )
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        _log.warning("dup_gate: frob.toml unreadable: %s", exc)
        return False, 0.85, False, False


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0001
# frob:invariant INV-011
# frob:ticket T-0399
# invariant spec: [INV-011](invariants/INV-011.md)
# frob:enforces CHK-GATE-DUP003
def dup_gate(root: Path, snapshot: GraphSnapshot, diff) -> tuple[Violation, ...]:  # noqa: ANN001
    """DUP001/DUP002: the diff introduces a clone of an existing symbol.

    Opt-in via `[dup].enforce = true` in frob.toml (default off): smart
    clone detection needs the frob-core native extension, so it stays
    silent until a repo turns it on. T-0399 (gates-quality audit finding 2):
    a requested-but-unavailable control must fail CLOSED, not open -- when
    `enforce` is true and frob-core is missing, this now emits a blocking
    DUP003 ERROR ("clone detection requested but unavailable") instead of
    silently skipping with only a log line, so a repo that opted in cannot
    silently lose clone coverage the moment a worktree's native build goes
    stale.
    """
    from frob.dup import core_available

    root = Path(root)
    enforce, threshold, region_kernel, native_rungs = _dup_config(root)
    if not enforce:
        _log.debug("dup_gate: [dup].enforce off, skipping")
        return ()
    if not core_available():
        _log.warning(
            "dup_gate: [dup].enforce=true but frob-core is not installed; "
            "failing closed (DUP003)"
        )
        return (
            Violation(
                rule="DUP003",
                severity=Severity.ERROR,
                file="frob.toml",
                line=1,
                message=(
                    "DUP003: [dup].enforce=true requests clone detection but "
                    "the frob-core native extension is not installed/built in "
                    "this environment -- run `make core` (or the repo's "
                    "native-build target) so DUP001/DUP002 actually run, or "
                    "set [dup].enforce=false if this environment deliberately "
                    "does not ship natives"
                ),
            ),
        )

    violations = _dup_gate_violations(
        snapshot, diff, threshold, region_kernel, native_rungs
    )
    _log.info("dup_gate: %d clone violation(s)", len(violations))
    return violations


def _dup_gate_violations(
    snapshot: GraphSnapshot,
    diff,
    threshold: float,
    region_kernel: bool,  # noqa: ANN001
    native_rungs: bool = False,  # noqa: ANN001
) -> tuple[Violation, ...]:
    """Run `find_clones` and return the DUP001/DUP002 violations against
    the diff's touched refs, or empty (already logged) if clone-finding
    itself fails."""
    from frob.dup import DUP001, DUP002, DupConfig, find_clones
    from frob.dup import touched_refs as _touched

    report_result = find_clones(
        snapshot,
        DupConfig(
            threshold=threshold,
            region_kernel_enabled=region_kernel,
            native_rungs_enabled=native_rungs,
        ),
        diff=diff,
    )
    if report_result.is_err:
        _log.warning("dup_gate: find_clones failed: %s", report_result.danger_err)
        return ()
    report = report_result.danger_ok
    touched = _touched(snapshot, diff)
    return (
        *DUP001(report, touched, threshold),
        *DUP002(report, touched, threshold),
    )
