# frob:waive INV006 preset="split-carried-prose"
"""frob.gates._fuzz -- FUZZ001/FUZZ002/FUZZ003 fuzz-obligation gate (T-1183).

Split out of `frob.gates.__init__` (T-1072/T-1140/T-1159/T-1170/T-1174/
T-1183 one-family-per-land discipline, T-1174's `_dup.py` precedent) so
the parent module can keep dropping toward the large-file threshold
without changing any public behavior. `fuzz_gate` is re-exported from
`frob.gates` unchanged -- the name this family is externally imported by
(`tests/test_gates.py`, `_ALL_GATES`'s process-job table);
`_fuzz_enforce`/`_fuzz_gate_violations` stay private to this module, not
imported elsewhere.

One cohesive family: `_fuzz_enforce` reads the `[fuzz].enforce` frob.toml
knob, `fuzz_gate` applies the opt-in/default-OFF policy around it, and
`_fuzz_gate_violations` does the actual `frob.fuzz` obligation resolution
and FUZZ001/002/003 translation -- all three exist solely to serve
`fuzz_gate`, with no shared runtime state beyond that.
"""
# frob:ticket T-1183

from __future__ import annotations

import tomllib
from pathlib import Path

from frob.gates._models import Violation
from frob.graph import GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)


def _fuzz_enforce(root: Path):  # noqa: ANN202
    """The `[fuzz].enforce` value from frob.toml as a `FuzzEnforce`, default OFF."""
    from frob.fuzz import FuzzEnforce

    enforce = FuzzEnforce.OFF
    toml_path = root / "frob.toml"
    if toml_path.exists():
        try:
            with toml_path.open("rb") as fh:
                raw = tomllib.load(fh).get("fuzz", {}).get("enforce")
            if raw in tuple(FuzzEnforce):
                enforce = FuzzEnforce(raw)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            _log.warning("fuzz_gate: frob.toml unreadable: %s", exc)
    return enforce


# frob:doc docs/modules/gates.md#public-api
# frob:ticket T-0002
def fuzz_gate(root: Path, snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """FUZZ001/002/003 over the [fuzz] policy in frob.toml.

    Default enforce is OFF (a repo opts in): fuzzing is a strong mandate, so
    it stays silent until [fuzz].enforce is set -- the warn-first adoption
    posture.
    """
    from frob.fuzz import FuzzEnforce, FuzzPolicy, obligations

    root = Path(root)
    enforce = _fuzz_enforce(root)
    if enforce == FuzzEnforce.OFF:
        _log.debug("fuzz_gate: [fuzz].enforce=off, skipping")
        return ()

    obs = obligations(snapshot, FuzzPolicy(enforce=enforce))
    violations = _fuzz_gate_violations(root, snapshot, obs)
    _log.info("fuzz_gate: %d obligation(s), %d violation(s)", len(obs), len(violations))
    return violations


def _fuzz_gate_violations(
    root: Path, snapshot: GraphSnapshot, obs
) -> tuple[Violation, ...]:  # noqa: ANN001
    """FUZZ001/002/003 for the resolved fuzz `obs` obligations."""
    from frob.fuzz import (
        FUZZ001,
        FUZZ002,
        FUZZ003,
        load_fuzz_stamp,
        resolve_param_types,
    )

    param_types = {ob.ref: resolve_param_types(root, ob.ref) for ob in obs}
    stamp = load_fuzz_stamp(root)
    return (
        *FUZZ001(snapshot, obs),
        *FUZZ002(obs, param_types),
        *FUZZ003(snapshot, obs, stamp),
    )
