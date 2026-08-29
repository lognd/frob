"""Tests for the entity/architecture/configuration surface (T-3006,
T-3004 section 5) at the Python native boundary.

The grammar and its SYS300-303 refusals are exercised exhaustively, both
directions, in `strata-core/src/parse/mod.rs`'s `#[cfg(test)] mod tests`
(Rust is where this parser lives, per docs/strata/surface.md#parser).
This file's job is narrower: prove the two worked-example fixtures
(`tests/unit/strata/entity_arch/storage_fast.strata` and
`storage_cheap.strata` -- "one entity, many architectures satisfying it",
T-3004 section 5) parse cleanly through the REAL `strata_core.parse_source`
Python binding, and that the additive-migration guarantee
(docs/strata/entity_architecture.md#migration) holds for a plain existing
`.strata` file with no entity/architecture blocks at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

strata_core = pytest.importorskip("strata_core")

FIXTURE_DIR = Path(__file__).parent / "strata" / "entity_arch"


def _parse(path: Path) -> dict:
    """Parse one `.strata` fixture and return its `ok` AST dict, failing the test with the raw diagnostic on a parse error."""
    result = json.loads(strata_core.parse_source(path.read_text()))
    assert "ok" in result, f"expected ok, got {result}"
    return result["ok"]


class TestEntityArchitectureFixtures:
    """One entity (`storage_component`), two architectures satisfying it."""

    def test_fast_architecture_binds_its_own_module_within_ceiling(self) -> None:
        """`storage_fast.strata`'s architecture stays inside the entity's may ceiling and binds its own module."""
        ast = _parse(FIXTURE_DIR / "storage_fast.strata")
        assert ast["name"] == "storage_fast"
        assert [e["name"] for e in ast["entities"]] == ["storage_component"]
        arch = ast["architectures"][0]
        assert arch["name"] == "fast"
        assert arch["of_entity"] == "storage_component"
        assert arch["binds"] == "storage_fast"

    def test_cheap_architecture_is_a_second_realization_of_the_same_entity(
        self,
    ) -> None:
        """`storage_cheap.strata` re-declares the same entity and offers a second, narrower architecture plus a configuration selecting it."""
        ast = _parse(FIXTURE_DIR / "storage_cheap.strata")
        assert [e["name"] for e in ast["entities"]] == ["storage_component"]
        arch = ast["architectures"][0]
        assert arch["name"] == "cheap"
        assert arch["of_entity"] == "storage_component"
        config = ast["configurations"][0]
        assert config == {
            "name": "default",
            "entity": "storage_component",
            "architecture": "cheap",
        }

    def test_existing_bare_module_source_parses_unchanged(self) -> None:
        """Migration guarantee: a file with no entity/architecture/configuration blocks (every existing `.strata` file) yields empty arrays for the three new fields, never a parse error."""
        ast = _parse_text("module legacy\nnode n : trusted { }\n")
        assert ast["entities"] == []
        assert ast["architectures"] == []
        assert ast["configurations"] == []

    def test_architecture_referencing_undeclared_entity_is_refused(self) -> None:
        """SYS300 must-fire, at the Python boundary: an undeclared `of ENTITY` name is a parse error, not a silently-accepted architecture."""
        result = json.loads(
            strata_core.parse_source(
                "module m\nnode n : trusted { }\n"
                "architecture a of ghost_entity {\n    binds m;\n}\n"
            )
        )
        assert "err" in result
        assert "undeclared entity" in result["err"]["message"]


def _parse_text(text: str) -> dict:
    """Parse an inline `.strata` source string and return its `ok` AST dict, failing the test with the raw diagnostic on a parse error."""
    result = json.loads(strata_core.parse_source(text))
    assert "ok" in result, f"expected ok, got {result}"
    return result["ok"]
