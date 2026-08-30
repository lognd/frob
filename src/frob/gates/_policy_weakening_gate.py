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

from frob.excludes import is_excluded, iter_files, load_exclude_globs
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


def _strata_files(root: Path, design_dir: Path) -> list[Path]:
    """Every `.strata` file under `design_dir`, minus `[graph].exclude`
    matches -- duplicated from `frob.gates._vmodel._strata_files` /
    `frob.strata._design_load._strata_files` (same T-0135 "no cross-
    import just for a file walk" posture those two document) rather than
    imported, purely so `_policy_id_file_map` below can re-walk the SAME
    file set `load_design_ids` already loaded (T-3460: `DesignIds.
    policies` merges every file's `PolicyDecl`s into one flat tuple,
    discarding which file declared which -- see that dataclass's own
    docstring -- so this gate has no way to ask `load_design_ids`'s
    result for that provenance directly)."""
    if not design_dir.is_dir():
        return []
    exclude_globs = load_exclude_globs(root)
    found = []
    for path in sorted(iter_files(design_dir, suffix=".strata")):
        rel = path.relative_to(root).as_posix()
        if exclude_globs and is_excluded(rel, exclude_globs):
            continue
        found.append(path)
    return found


# frob:ticket T-3460
def _policy_id_file_map(root: Path, design_dir: str) -> dict[str, str]:
    """`{policy_id: rel_file}` for every `policy` declaration under
    `design_dir`, re-parsed PER FILE (T-3460) -- the same `node_file`-map
    pattern `frob.gates._vmodel._collect_vmodel_graph` already uses for
    VMOD001 (T-3264's own precedent, cited by this ticket's own body).
    `frob.strata` is already imported by every caller of this function
    (only reached after `load_design_ids` itself succeeded), so this
    duplicate per-file parse pays no NEW native-extension cost -- it is
    strictly a second, cheap syntactic pass over files already read once.
    A file that fails to re-parse here (should not happen -- the SAME
    files just parsed cleanly enough to reach this point) is skipped:
    its own policies simply have no entry and `INV051` findings that
    involve them fall back to the shared `design_dir` anchor unchanged,
    never a crash."""
    from frob.strata import parse_module

    mapping: dict[str, str] = {}
    for path in _strata_files(root, root / design_dir):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning(
                "policy_weakening_gate: could not re-read %s for its "
                "policy_id file map: %s",
                rel,
                exc,
            )
            continue
        parsed = parse_module(text)
        if parsed.is_err:
            _log.debug(
                "policy_weakening_gate: %s failed to re-parse for its "
                "policy_id file map (%s) -- its policies fall back to "
                "the shared design_dir anchor",
                rel,
                parsed.danger_err,
            )
            continue
        for policy in parsed.danger_ok.policies:
            mapping[policy.id] = rel
    return mapping


# frob:enforces CHK-GATE-INV051
# frob:doc docs/strata/policy.md#refinement-monotonicity-inv-051-t-1482
# frob:ticket T-1843
# frob:ticket T-1864
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
    cannot be compiled into policies at all.

    T-3460: each finding's `Violation.file` is the CHILD policy's own
    declaring `.strata` file (`_policy_id_file_map`) when resolvable,
    rather than the constant `design_dir` -- otherwise every INV051
    finding repo-wide collapsed onto one `(rule, file)` identity (the
    same anchor-collapse class T-3419 fixed generically at the sweep's
    identity-extraction layer for SELFAUDIT001; INV051's own message
    names policy ids, never a file path, so that generic fix could not
    recover a distinguishing file for it -- this is the gate-side,
    per-rule resolution T-3419's own Done report named as the necessary
    follow-up, the same `node_file`-map shape VMOD001 already uses,
    T-3264)."""
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

    merged_module = Module(
        name="__policy_weakening_gate__", policies=design_ids.policies
    )
    compiled = compile_policies(merged_module, design_ids.models[0])
    if compiled.is_err:
        _log.warning(
            "policy_weakening_gate: policy compilation failed: %s",
            compiled.danger_err,
        )
        return ()

    from frob.strata import find_policy_weakenings

    weakenings = find_policy_weakenings(compiled.danger_ok)
    if not weakenings:
        return ()
    # T-3460: policy_id -> declaring file, so each finding's identity is
    # the CHILD policy's own real file (the "subject" a reader would fix)
    # instead of the shared design_dir anchor every INV051 finding used
    # to collapse onto -- see this function's own docstring update and
    # `_policy_id_file_map`'s.
    policy_file = _policy_id_file_map(root, design_dir)
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
                file=policy_file.get(weakening.child_id, design_dir),
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
