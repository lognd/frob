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
    def test_vmodel_node_and_edge_round_trip_through_python(self) -> None:
        payload = _parse(
            'module m\n'
            'vmodel_node req_1 kind "artifact" level "requirements";\n'
            'vmodel_node design_1 kind "artifact" level "component-design";\n'
            'vmodel_edge kind "satisfies" src design_1 dst req_1;\n'
        )
        ast = payload["ok"]
        assert [n["name"] for n in ast["vmodel_nodes"]] == ["req_1", "design_1"]
        assert ast["vmodel_edges"] == [{"kind": "satisfies", "src": "design_1", "dst": "req_1"}]

    def test_duplicate_vmodel_node_name_is_a_parse_error(self) -> None:
        payload = _parse(
            'module m\n'
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
