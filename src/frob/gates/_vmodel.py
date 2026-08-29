"""frob.gates._vmodel -- VMOD001, the V-model closure gate (T-3042).

T-3004/T-3005/T-3007 built a kernel (`strata-core::graph::vmodel`) that can
CHECK a requirement/spec/design/test graph for structural closure
(T-3043 fixed the closure semantics themselves), and T-3042 added the
`vmodel_node`/`vmodel_edge` authoring statements (docs/strata/vmodel.md)
so a human can actually WRITE one. Neither of those was reachable from
`frob check` before this module: `vmodel_check` (the PyO3 export) had
ZERO callers anywhere outside strata-core's own tests -- the exact
shipped-but-not-reachable failure class this repo has hit before at gate
scale (a gate written but never added to the gate dict). This module is
the missing wire: it aggregates every `vmodel_node`/`vmodel_edge`
declared across every `.strata` design file into ONE graph and runs
`vmodel_check` against it.

Opt-in the same way `frob.gates.sys_gate` is (T-0135's posture): a repo
with no design dir, or a design dir with zero vmodel declarations, sees
NOTHING from this gate -- frob has no V-model graph of its own yet, so a
loud gate here would just be noise nobody asked for. `strata_core` is
imported lazily, after that existence check, for the same reason
`sys_gate` defers its own `frob.strata` import.

SEVERITY: every VMOD001 finding is WARN, not ERROR (owner's explicit
instruction, T-3042's ticket body) -- promoting to ERROR belongs to a
later ticket, once a real V-model graph exists somewhere and burn-down is
plausible. Shipping this at ERROR against a repo with zero requirements
declared would just get waived en masse (the LARGE001-with-87-waivers
lesson this repo has already paid for).
"""

# frob:ticket T-3042

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from frob.excludes import is_excluded, iter_files, load_exclude_globs
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: Mirrors `frob.gates._sys._DEFAULT_DESIGN_DIR`/
#: `frob.strata._design_load.DEFAULT_DESIGN_DIR`. Duplicated as a bare
#: literal rather than imported, same T-0135 reasoning `_sys.py`'s own
#: copy documents: this gate must never import `frob.strata` (which
#: transitively needs the `strata_core` native extension) for a repo with
#: no design dir at all.
_DEFAULT_DESIGN_DIR = "design"


def _design_dir(root: Path) -> str:
    """`[strata].design_dir` from frob.toml, defaulting to `_DEFAULT_DESIGN_DIR`."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return _DEFAULT_DESIGN_DIR
    try:
        with toml_path.open("rb") as fh:
            return (
                tomllib.load(fh)
                .get("strata", {})
                .get("design_dir", _DEFAULT_DESIGN_DIR)
            )
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("vmodel_gate: frob.toml unreadable: %s", exc)
        return _DEFAULT_DESIGN_DIR


def _strata_files(root: Path, design_dir: Path) -> list[Path]:
    """Every `.strata` file under `design_dir`, minus `[graph].exclude`
    matches, in deterministic order -- same walk `frob.strata._design_load
    ._strata_files` does for SYS00x, duplicated here (rather than
    imported) so this gate never has to import `frob.strata` for a repo
    with no vmodel declarations at all (T-0135 posture, same as
    `_design_dir` above)."""
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


# frob:ticket T-3264
# frob:tests tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud.test_check_fails_loud_with_sys004_when_strata_present  # noqa: E501
def _collect_vmodel_graph(
    paths: list[Path],
) -> tuple[
    list[tuple[str, str, str | None, dict[str, str]]],
    list[tuple[str, str, str, dict[str, str]]],
    dict[str, str],
]:
    """Parse every file in `paths` and merge their `vmodel_node`/
    `vmodel_edge` statements into one flattened (nodes, edges) pair, the
    shape `strata_core.vmodel_check` takes. Also returns a `node -> file`
    map (last file to declare a given node id wins -- duplicate node ids
    across files is a real construction-time `GraphError` `vmodel_check`
    itself will report, this map only exists so THIS gate can cite a
    real file for a violation instead of a repo-wide `file="design"`).

    A file that fails to parse is logged and skipped -- `sys_gate`'s
    SYS004 already reports a malformed `.strata` file as its own finding;
    duplicating that here would double-report the same root cause under
    two rule ids.

    T-3044 H3: every node/edge now carries an `attrs` dict (the kernel's
    typed payload -- `runnable` on a test node, `code_ref` on an
    artifact, `reason` on a `supersedes` edge). The grammar's
    `vmodel_node`/`vmodel_edge` statements carry a matching optional
    `runnable`/`code_ref`/`reason` clause (docs/strata/vmodel.md); a
    declaration that omits the one its kind requires parses fine (the
    grammar does not enforce this -- the kernel does) but will correctly
    surface here as a VMOD001 construction-error finding once
    `vmodel_check` refuses it, exactly the H3 behavior this ticket exists
    to guarantee.

    T-3264: `strata_core` may be genuinely absent (a standalone
    `uv tool install frob` with no natives, T-0134) -- an unguarded
    `import strata_core` here previously crashed the whole `frob check`
    dispatch with a raw `ImportError` instead of degrading, even though
    `sys_gate`'s SYS004 already reports the exact same native-missing
    condition as a proper typed finding for every file in `paths`
    (this docstring's own "SYS004 covers this" note, just not yet true
    for the native-missing case specifically). Return empty rather than
    raise: a VMOD001 finding would be redundant with SYS004 here too,
    same as the per-file parse-failure skip below."""
    try:
        import strata_core
    except ImportError as exc:
        _log.warning(
            "vmodel_gate: strata_core native extension unavailable (%s) -- "
            "skipping (SYS004 covers this)",
            exc,
        )
        return [], [], {}

    nodes: list[tuple[str, str, str | None, dict[str, str]]] = []
    edges: list[tuple[str, str, str, dict[str, str]]] = []
    node_file: dict[str, str] = {}
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning("vmodel_gate: could not read %s: %s", path, exc)
            continue
        payload = json.loads(strata_core.parse_source(text))
        if "err" in payload:
            _log.debug(
                "vmodel_gate: %s failed to parse, skipping (SYS004 covers this)", path
            )
            continue
        ast = payload["ok"]
        for n in ast.get("vmodel_nodes", []):
            nodes.append((n["name"], n["kind"], n.get("level"), n.get("attrs", {})))
            node_file[n["name"]] = str(path)
        for e in ast.get("vmodel_edges", []):
            edges.append((e["kind"], e["src"], e["dst"], e.get("attrs", {})))
    return nodes, edges, node_file


# frob:ticket T-3042
# frob:doc docs/strata/vmodel.md#wired-into-frob-check-vmod001-t-3042
# frob:tests tests/test_gates_vmodel.py::TestVmodelGate.test_noop_no_design_dir
# frob:tests tests/test_gates_vmodel.py::TestVmodelGate.test_noop_no_vmodel_declarations
# frob:tests \
# tests/test_gates_vmodel.py::TestVmodelGate.test_fires_vmod001_on_construction_error
# frob:tests \
# tests/test_gates_vmodel.py::TestVmodelGate.test_fires_vmod001_on_closure_violation
# frob:tests \
# tests/test_gates_vmodel.py::TestVmodelGate.test_quiet_on_a_genuinely_closed_graph
# frob:enforces CHK-GATE-VMOD001
def vmodel_gate(root: Path) -> tuple[Violation, ...]:
    """VMOD001 (WARN): every `strata_core.vmodel_check` construction error
    or closure-rule violation over the ONE V-model graph assembled from
    every `vmodel_node`/`vmodel_edge` statement in every `.strata` file
    under the repo's design dir.

    Opt-in on TWO levels, both silent (not a finding of their own): no
    design dir at all (same posture as `sys_gate`), or a design dir with
    zero vmodel declarations anywhere (frob has no V-model graph of its
    own yet -- T-3042's ticket body is explicit that shipping loud here
    before a real graph exists would just get waived away, the LARGE001
    lesson). `strata_core` is imported only once nodes are known to
    exist, so a repo with a design dir but no vmodel statements never
    pays the native-extension import cost either."""
    design_dir = root / _design_dir(root)
    paths = _strata_files(root, design_dir)
    if not paths:
        _log.debug("vmodel_gate: no .strata files under %s, skipping", design_dir)
        return ()

    nodes, edges, node_file = _collect_vmodel_graph(paths)
    if not nodes:
        _log.debug("vmodel_gate: no vmodel_node declarations found, skipping")
        return ()

    import strata_core

    errors, rule_violations = strata_core.vmodel_check(nodes, edges)
    _log.info(
        "vmodel_gate: checked %d node(s), %d edge(s) -- %d construction error(s), "
        "%d closure violation(s)",
        len(nodes),
        len(edges),
        len(errors),
        len(rule_violations),
    )

    violations: list[Violation] = []
    for detail in errors:
        violations.append(
            Violation(
                rule="VMOD001",
                severity=Severity.WARN,
                file=str(design_dir),
                line=0,
                message=(
                    f"VMOD001: V-model graph construction error: {detail} -- "
                    f"fix the offending vmodel_node/vmodel_edge statement"
                ),
            )
        )
    for rule_name, node_id in rule_violations:
        violations.append(
            Violation(
                rule="VMOD001",
                severity=Severity.WARN,
                file=node_file.get(node_id, str(design_dir)),
                line=0,
                message=(
                    f"VMOD001: V-model closure rule {rule_name!r} violated at "
                    f"node {node_id!r} -- see docs/strata/vmodel.md#the-closure-rules"
                ),
            )
        )
    return tuple(violations)


__all__ = ["vmodel_gate"]
