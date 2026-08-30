"""Python-level evidence for T-3042's authoring format: `vmodel_node`/
`vmodel_edge` statements parse through `strata_core.parse_source` the same
way every other strata construct does, and the additive-compatibility
guarantee (every existing `.strata` file keeps parsing unchanged) holds
through the real Python-facing boundary, not just the Rust unit level
(`strata-core/src/parse/mod.rs`'s own fixtures, already run via `cargo
test`, are the Rust-level evidence for the grammar itself).

T-3006 is the direct precedent this ticket follows (entity/architecture/
configuration): docs/strata/entity_architecture.md's own "Migration"
section and its `existing_bare_module_files_parse_unchanged_no_entity_
required` regression test are exactly the shape reused here for
`vmodel_node`/`vmodel_edge`.
"""

# frob:ticket T-3042
from __future__ import annotations

import json

import pytest

strata_core = pytest.importorskip(
    "strata_core",
    reason="strata_core native extension not built -- run `make core`",
)

# frob:tests strata-core/src/parse/mod.rs::parse_source_impl kind="unit"


def _parse(text: str) -> dict:
    return json.loads(strata_core.parse_source(text))


class TestVmodelAuthoringFormat:
    # frob:ticket T-3424
    def test_vmodel_node_and_edge_round_trip_through_python(self) -> None:
        """T-3424: this asserts the FULL node/edge payload shape crossing
        the Rust-to-Python boundary (`name`/`kind`/`level`/`attrs` for a
        node, `kind`/`src`/`dst`/`attrs` for an edge) -- not just a subset
        of fields -- against `strata_core.parse_source`'s real output, so
        a field this repo's own `frob.gates._vmodel._collect_nodes_edges`
        genuinely reads (T-3044 H3: `runnable`/`code_ref` on nodes,
        `reason` on `supersedes` edges) can never silently drift out of
        sync with what this test expects again.

        HISTORY (T-3424): this test previously asserted `vmodel_edges`
        with NO `attrs` key at all, and `vmodel_nodes` by NAME only (not
        full shape) -- both predate T-3044 H3, which added `attrs` to
        BOTH payloads (`strata-core/src/parse/grammar_core.rs`, the
        pre-T-3260 file, at the same `ast.vmodel_edges.push({..., "attrs":
        attrs})`/`ast.vmodel_nodes.push({..., "attrs": attrs})` call sites
        this test now covers). T-3260 (2026-08-29) later split that file
        into `strata-core/src/parse/grammar_vmodel.rs` verbatim -- `git
        show` of the pre-split file (commit 5ee140434^:strata-core/src/
        parse/grammar_core.rs) confirms the identical `attrs` field and
        the identical T-3044 H3 comment already present, unchanged by the
        split -- so T-3260 introduced NOTHING here; it only made this
        pre-existing, already-consumed field visible again by moving the
        code a test's stale expectation happened to be pointed at. This is
        answer (a) from the ticket's own decision tree: `attrs` is
        INTENDED and genuinely consumed (`frob.gates._vmodel`'s
        `_collect_nodes_edges` reads `n.get("attrs", {})`/`e.get("attrs",
        {})` for exactly this purpose), so the fix is updating this
        stale expectation to the real shape, exercising a non-empty
        `attrs` case on both node and edge (`runnable`/`reason`) so the
        consumed fields have real coverage, not just an empty-dict shape
        that would pass whether or not the grammar wired them at all.
        """
        payload = _parse(
            "module m\n"
            'vmodel_node req_1 kind "artifact" level "requirements";\n'
            'vmodel_node design_1 kind "artifact" level "component-design";\n'
            'vmodel_node ctest_1 kind "test" runnable "tests/test_x.py::test_y";\n'
            'vmodel_edge kind "satisfies" src design_1 dst req_1;\n'
            'vmodel_edge kind "supersedes" src req_1 dst design_1 reason "revised scope";\n'
        )
        ast = payload["ok"]
        assert ast["vmodel_nodes"] == [
            {"name": "req_1", "kind": "artifact", "level": "requirements", "attrs": {}},
            {
                "name": "design_1",
                "kind": "artifact",
                "level": "component-design",
                "attrs": {},
            },
            {
                "name": "ctest_1",
                "kind": "test",
                "level": None,
                "attrs": {"runnable": "tests/test_x.py::test_y"},
            },
        ]
        assert ast["vmodel_edges"] == [
            {"kind": "satisfies", "src": "design_1", "dst": "req_1", "attrs": {}},
            {
                "kind": "supersedes",
                "src": "req_1",
                "dst": "design_1",
                "attrs": {"reason": "revised scope"},
            },
        ]

    def test_duplicate_vmodel_node_name_is_a_parse_error(self) -> None:
        payload = _parse(
            "module m\n"
            'vmodel_node req_1 kind "artifact" level "requirements";\n'
            'vmodel_node req_1 kind "artifact" level "requirements";\n'
        )
        assert "err" in payload
        assert "duplicate vmodel_node" in payload["err"]["message"]

    def test_existing_bare_module_files_parse_unchanged(self) -> None:
        """T-3042's own additive-parse regression, through the Python
        boundary: a file with zero vmodel statements (every one of this
        repo's 8+ existing .strata files, including design/frob.strata
        itself) must parse to exactly empty vmodel_nodes/vmodel_edges
        arrays -- the same guarantee T-3006 proved for entity/
        architecture/configuration."""
        payload = _parse("module legacy\nnode n : trusted { }\n")
        ast = payload["ok"]
        assert ast["vmodel_nodes"] == []
        assert ast["vmodel_edges"] == []

    def test_designs_own_frob_strata_still_parses(self) -> None:
        """The literal self-model file this repo's own `frob check` reads
        every run -- must still parse cleanly after this ticket's grammar
        addition, with empty vmodel arrays (it declares no vmodel
        statements)."""
        from pathlib import Path

        text = Path("design/frob.strata").read_text(encoding="utf-8")
        payload = _parse(text)
        assert "ok" in payload, payload.get("err")
        assert payload["ok"]["vmodel_nodes"] == []
        assert payload["ok"]["vmodel_edges"] == []
