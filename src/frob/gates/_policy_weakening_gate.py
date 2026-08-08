"""INV051 gate (T-1843): wires `frob.strata.find_policy_weakenings` (INV-051,
T-1482) into a real `frob check` finding over this repo's actual `design/`
policies, instead of leaving it a tested-but-uncalled TIER-1 diff pass
(the WIRE001 waiver `find_policy_weakenings` carried named this ticket as
the follow-up).

Loads+elaborates every `.strata` file the way `frob.gates._sys.sys_gate`
already does (`load_design_ids`, opt-in behind a `design/` directory
existing), then compiles the merged `PolicyDecl`s `DesignIds.policies`
now carries (T-1843's own `_design_load.py` addition) against the single
merged `KernelModel` `DesignIds.models` holds, and hands the result to
`find_policy_weakenings` unchanged -- no new diff logic here, this module
is wiring only.

Deliberately excludes `forbid_call`/`forbid_import` from consideration --
not this module's decision, `find_policy_weakenings` itself already never
flags them (`_policy.py`'s `test_forbid_call_never_flagged_even_when_
child_narrows`, T-1482 finding: both rule forms are purely additive under
TIER-2's union enforcement, so a child can never "weaken" one by omission
or restatement). This module surfaces whatever `find_policy_weakenings`
returns; it does not filter rule kinds itself.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: Mirrors `frob.gates._DEFAULT_DESIGN_DIR` / `frob.strata._design_load.
#: DEFAULT_DESIGN_DIR` as a bare literal so a repo with no design dir at
#: all never pays the `frob.strata` native-extension import cost (same
#: T-0135 posture `_sys.py`'s own default mirror documents).
_DEFAULT_DESIGN_DIR = "design"


def _design_dir(root: Path) -> str:
    """`[strata].design_dir` from frob.toml, defaulting to `_DEFAULT_DESIGN_DIR`
    -- duplicated from `frob.gates._sys._design_dir` rather than imported,
    same T-0135 reasoning: this module must not import `frob.gates._sys`
    (which itself defers `frob.strata`) just to read one toml key."""
    import tomllib

    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return _DEFAULT_DESIGN_DIR
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("policy_weakening_gate: frob.toml unreadable: %s", exc)
        return _DEFAULT_DESIGN_DIR
    strata_table = doc.get("strata", {})
    if not isinstance(strata_table, dict):
        return _DEFAULT_DESIGN_DIR
    value = strata_table.get("design_dir", _DEFAULT_DESIGN_DIR)
    return value if isinstance(value, str) else _DEFAULT_DESIGN_DIR


# frob:doc docs/strata/policy.md#refinement-monotonicity-inv-051-t-1482
# frob:ticket T-1843
# frob:tests tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate.test_no_design_dir_noop  # noqa: E501
# frob:tests tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate.test_weakening_detected  # noqa: E501
# frob:tests tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate.test_clean_policies_no_finding  # noqa: E501
# frob:tests tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate.test_load_failure_skips_silently  # noqa: E501
def policy_weakening_gate(root: Path) -> tuple[Violation, ...]:
    """INV051: a `design/` policy whose scope is a strict subset of a
    containing policy's, but which re-declares `confine_use`/
    `at_call_require_arg`/`mediate` less restrictively than the parent
    already required for the same target -- `find_policy_weakenings`
    (T-1482) run for real, over this repo's actual design, rather than
    only over test fixtures. Opt-in behind a `design/` (or
    `[strata].design_dir`) directory existing, same posture as
    `frob.gates.sys_gate` (T-0135: no directory means no `frob.strata`
    import at all). A design load failure is left to SYS004 to report --
    this gate silently contributes nothing rather than double-reporting a
    load failure under a second rule id, since a malformed `.strata` file
    cannot be compiled into policies at all."""
    design_dir = _design_dir(root)
    if not (root / design_dir).is_dir():
        _log.debug("policy_weakening_gate: no %s/ directory, skipping", design_dir)
        return ()

    from frob.strata import Module, compile_policies, load_design_ids

    design_ids = load_design_ids(root, design_dir)
    if design_ids.errors or not design_ids.models:
        _log.debug(
            "policy_weakening_gate: %d design load error(s), skipping "
            "(SYS004 reports the load failure itself)",
            len(design_ids.errors),
        )
        return ()
    if not design_ids.policies:
        _log.debug("policy_weakening_gate: no policy declarations, skipping")
        return ()

    merged_module = Module(name="__policy_weakening_gate__", policies=design_ids.policies)
    compiled = compile_policies(merged_module, design_ids.models[0])
    if compiled.is_err:
        _log.warning(
            "policy_weakening_gate: policy compilation failed: %s",
            compiled.danger_err,
        )
        return ()

    from frob.strata import find_policy_weakenings

    weakenings = find_policy_weakenings(compiled.danger_ok)
    violations: list[Violation] = []
    for weakening in weakenings:
        _log.warning(
            "INV051: policy %s weakens %s's %s rule (%s)",
            weakening.child_id,
            weakening.parent_id,
            weakening.rule_kind,
            weakening.detail,
        )
        violations.append(
            Violation(
                rule="INV051",
                severity=Severity.ERROR,
                file=design_dir,
                line=0,
                message=(
                    f"INV051: policy {weakening.child_id!r} weakens parent "
                    f"policy {weakening.parent_id!r}'s {weakening.rule_kind} "
                    f"rule -- {weakening.detail}; a narrower-scope policy may "
                    f"only strengthen an inherited rule, never weaken it "
                    f"(docs/strata/policy.md#refinement-monotonicity-inv-051-"
                    f"t-1482)"
                ),
            )
        )
    return tuple(violations)


__all__ = ["policy_weakening_gate"]
