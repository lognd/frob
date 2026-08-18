"""T-2358 regression: `frob.deploy._generate`/`_generate_windows` and
`frob.vet._capability`/`_capability_scan` used to import EACH OTHER
(`_generate_windows` needed manifest primitives back from `_generate`;
`_capability_scan` needed `language_for`/`scan_file_capabilities`/
`_resolved_candidates_for_language` back from `_capability`) -- both
genuine two-module import cycles, each previously worked around with a
function-local deferred import commented "avoid a circular import"
(`_generate.py`) or "T-1420: avoid a circular import" (`_capability_scan.
py`, 5 call sites). A deferred import hides a cycle from a NAIVE
top-level-only scanner, but this repo's own cycle gate (`frob check
--only cycle`, `frob.check._python._build_import_graph` +
`frob.cycle.graph.find_cycles`) walks into function bodies too, so it
kept reporting both cycles despite the workaround -- and because the
gate's finding carried no rule id or file (T-2345's own discovery), the
finding was unownable and neither cycle was ever fixed.

The real fix (T-2358) moved the shared pieces each side needed FROM the
other into a module BOTH already safely import: `deploy/_generate_
common.py` (new) for `DIGEST_HEADER_PREFIX`/`ManifestEntry`/
`manifest_digest`/`sorted_manifest_entries`; `vet/_capability_core.py`
(pre-existing) for `language_for`/`SCANNED_LANGUAGES`; and `vet/
_capability_scan.py` itself for `scan_file_capabilities`/
`_resolved_candidates_for_language` (moving the implementation to where
it was actually being called FROM, since `_capability.py` already acted
as a facade re-exporting most of `_capability_scan.py`'s surface via its
own `__all__` -- confirmed by reading it, not guessed).

This test runs the SAME real cycle detector this repo's own `frob check
--only cycle` gate uses against the actual `src/` tree and asserts the
SPECIFIC reverse edges T-2358 removed do not reappear -- NOT "this file
is absent from every cycle", which `_capability.py`/`_capability_scan.py`
cannot honestly claim: both remain members of a SEPARATE, much larger,
pre-existing cross-package cycle (`serve` -> `stats` -> `tickets` ->
`testing` -> `app` -> `serve`, ~175 nodes) that T-2358 measured, root-
caused down to its exact 5 cross-package edges, and explicitly did NOT
attempt to fix -- untangling which of five packages' dependency
DIRECTION is wrong needs a real architectural decision, not a guess made
implicitly inside a bug-fix ticket. Asserting "no cycle contains this
file" here would be dishonest (it would need the giant cycle fixed too,
which this ticket does not do) or would silently pass by accident should
someone later narrow `_build_import_graph`'s scope -- checking the exact
edges removed is what this ticket actually changed and is the only claim
this test can honestly make."""

from __future__ import annotations

from pathlib import Path

from frob.check._python import _build_import_graph
from frob.cycle.graph import DependencyGraph, find_cycles

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"


class TestDeployAndCapabilityCycleRegression:
    """T-2358: the two REVERSE edges each cycle depended on
    (`_generate_windows.py -> _generate.py`, `_capability_scan.py ->
    _capability.py`) must not reappear -- run against the actual repo
    tree, not a synthetic fixture, so a regression here is a REAL
    regression."""

    # frob:ticket T-2358
    # frob:tests tests/unit/test_capability_and_deploy_cycle_regression.py::TestDeployAndCapabilityCycleRegression.test_generate_windows_no_longer_imports_generate  # noqa: E501
    def test_generate_windows_no_longer_imports_generate(self) -> None:
        # frob:tests src/frob/check/_python.py::_build_import_graph kind="unit"
        graph = _build_import_graph(_SRC_ROOT)
        neighbors = set(graph.neighbors("frob/deploy/_generate_windows.py"))
        assert "frob/deploy/_generate.py" not in neighbors, (
            "deploy/_generate_windows.py must not import deploy/_generate.py "
            "(T-2358's own reverse edge -- both now depend on "
            "_generate_common.py instead)"
        )

    # frob:ticket T-2358
    # frob:tests tests/unit/test_capability_and_deploy_cycle_regression.py::TestDeployAndCapabilityCycleRegression.test_capability_scan_no_longer_imports_capability  # noqa: E501
    def test_capability_scan_no_longer_imports_capability(self) -> None:
        # frob:tests src/frob/check/_python.py::_build_import_graph kind="unit"
        graph = _build_import_graph(_SRC_ROOT)
        neighbors = set(graph.neighbors("frob/vet/_capability_scan.py"))
        assert "frob/vet/_capability.py" not in neighbors, (
            "vet/_capability_scan.py must not import vet/_capability.py "
            "(T-2358's own reverse edge -- language_for/scan_file_"
            "capabilities/_resolved_candidates_for_language now live in "
            "_capability_scan.py/_capability_core.py, imported the other "
            "direction only)"
        )


class TestPlantedCycleStillDetected:
    """T-2358's REQUIRED positive control, verbatim from the coordinator's
    brief: a deliberately planted 2-node cycle must STILL be detected
    after this fix, proving the fix broke the two real cycles without
    blinding the detector itself. This repo has already been burned once
    by a "clean" cycle verdict that came from a detector that could not
    see a planted case (docs/audits -- positive-control-or-it-proves-
    nothing) -- this is exactly that discipline applied here, using a
    synthetic `DependencyGraph` (not the real `src/` tree) so it can
    never accidentally pass just because the real tree happens to be
    clean."""

    # frob:ticket T-2358
    # frob:tests tests/unit/test_capability_and_deploy_cycle_regression.py::TestPlantedCycleStillDetected.test_planted_two_node_cycle_is_detected  # noqa: E501
    def test_planted_two_node_cycle_is_detected(self) -> None:
        # frob:tests src/frob/cycle/graph.py::find_cycles kind="unit"
        graph = DependencyGraph()
        graph.add_node("a.py")
        graph.add_node("b.py")
        graph.add_node("c.py")
        graph.add_edge("a.py", "b.py")
        graph.add_edge("b.py", "a.py")  # the planted 2-node cycle
        graph.add_edge("b.py", "c.py")  # an acyclic edge, must NOT show up
        cycles = find_cycles(graph)
        cycle_sets = [frozenset(c) for c in cycles]
        assert frozenset({"a.py", "b.py"}) in cycle_sets, (
            f"planted 2-node cycle a.py<->b.py was NOT detected -- the "
            f"detector itself may be blinded; got cycles: {cycles}"
        )
