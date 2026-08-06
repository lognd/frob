"""Drift-lock the registry-of-registries against the extending guide series.

WHY: docs/guides/extending/registry_of_registries.json is the machine-readable
inventory of every registry/extension point in frob (T-0159). Each entry
promises (a) a guide file under docs/guides/extending/, (b) a live frob:doc
anchor in the entry's anchor_file pointing at that guide, and (c) an H1 whose
slug the anchor's #fragment resolves to. This test asserts all three, plus
the reverse direction: no orphan guide .md files absent from the inventory,
and -- the completeness half -- every KNOWN registry marker in the codebase
appears as an inventory row, so ADDING A NEW REGISTRY without a guide fails
the build here instead of rotting silently.

frob:tests docs/guides/extending/registry_of_registries.json kind="unit"
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from frob.graph.dsl import slugify

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTENDING = REPO_ROOT / "docs" / "guides" / "extending"
INVENTORY = EXTENDING / "registry_of_registries.json"

#: Codebase markers that indicate a registry-like extension point exists.
#: Each maps a (file, regex) probe to the inventory id that must cover it.
#: Adding a new registry means adding its probe here AND an inventory row
#: AND a guide -- this table is deliberately the third leg of the lock so
#: the test itself cannot silently under-count the universe.
_REGISTRY_PROBES: dict[str, tuple[str, str]] = {
    "gate-rule-families": ("src/frob/gates/_models.py", r"class GateConfig"),
    "comment-dsl-directives": ("src/frob/graph/dsl.py", r"_VERB_TABLE"),
    "threat-catalog": ("src/frob/strata/_threat_models.py", r"class WeaknessEntry"),
    "compliance-registry": ("src/frob/strata/_compliance.py", r"class RegulationEntry"),
    "capability-registry": (
        "src/frob/vet/_capability_registry/_matrix.py",
        r"DANGEROUS_OPERATIONS",
    ),
    "cve-fingerprints": (
        "src/frob/strata/_cve_fingerprint.py",
        r"class CveFingerprint",
    ),
    "pii-categories": ("src/frob/strata/_pii.py", r"PII_CATEGORIES"),
    "design-lint-rules": ("src/frob/strata/_lint.py", r"class LintViolation"),
    "secrets-scan-providers": ("src/frob/security/_redact.py", r"class _SecretPattern"),
    "prover-claim-kinds": ("src/frob/strata/_claims.py", r"_SKEW_PREFIX"),
    "scenario-kinds": ("src/frob/strata/_scenarios.py", r"class ScenarioResult"),
    "strata-surface-grammar": (
        "tests/unit/test_strata_tmlanguage.py",
        r"def test_construct_keywords_match_parser_bidirectionally",
    ),
    "test-runner-entries": ("src/frob/testing/_models.py", r"class RunnerSpec"),
    "language-grammar-handlers": ("src/frob/lang/_extract.py", r"_WALKERS"),
    "sys-export-formats": ("src/frob/strata/_export.py", r"def export_"),
    "litmus-fixtures": (
        "tests/unit/strata/test_litmus_surface.py",
        r"class TestNaiveSurfaceGoldens",
    ),
    "benign-capabilities": (
        "src/frob/strata/_threat_models.py",
        r"class BenignCapability",
    ),
    "ticket-kinds-states": ("src/frob/tickets/_models.py", r"class TicketState"),
    "dup-detector-registry": ("src/frob/dup/_rules.py", r"def DUP001"),
}

_ANCHOR_RE = re.compile(r"frob:doc\s+(docs/guides/extending/\S+?\.md)#(\S+)")
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_A_ID_RE = re.compile(r'<a id="([^"]+)"></a>')

#: A `frob:doc <path>#<fragment>` anchor's value is always one unbreakable
#: run of non-space characters, so `frob fmt`'s canonicalizer only ever
#: wraps it right after the `frob:doc` keyword itself -- a real word
#: boundary that had a space before the continuation backslash (T-0991's
#: fixed round trip preserves it). Folding that one join shape back to a
#: single space before `_ANCHOR_RE` runs keeps this scan working across
#: both the pre- and post-recompaction single-line/wrapped forms (T-0988).
_CONTINUATION_FOLD_RE = re.compile(r"\\\n#[ \t]?")


def _fold_directive_continuations(text: str) -> str:
    """`text` with any `frob:` directive's wrapped continuation lines
    (a trailing `\\` then a `#`-prefixed physical line) rejoined with a
    single space, so a regex written against the unwrapped single-line
    form still matches the wrapped form."""
    return _CONTINUATION_FOLD_RE.sub(" ", text)


def _load_inventory() -> list[dict[str, str]]:
    """The parsed registry rows, failing loudly on a malformed file."""
    data = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert data["registries"], "registry_of_registries.json has no rows"
    return data["registries"]


class TestExtendingGuidesComplete:
    """Every registry has a guide, a live anchor, and a resolvable slug."""

    def test_every_row_has_a_guide_file(self) -> None:
        for row in _load_inventory():
            guide = REPO_ROOT / row["guide"]
            assert guide.is_file(), (
                f"inventory row {row['id']!r} promises guide {row['guide']} "
                "which does not exist -- write the guide or drop the row"
            )

    def test_every_row_anchor_file_exists_and_mentions_guide(self) -> None:
        for row in _load_inventory():
            anchor_file = REPO_ROOT / row["anchor_file"]
            assert anchor_file.is_file(), (
                f"inventory row {row['id']!r} names anchor_file "
                f"{row['anchor_file']} which does not exist"
            )
            text = anchor_file.read_text(encoding="utf-8")
            guide_rel = row["guide"]
            assert guide_rel in text, (
                f"{row['anchor_file']} has no frob:doc anchor pointing at "
                f"{guide_rel} -- add the anchor next to {row['anchor_symbol']}"
            )
            assert row["anchor_symbol"] in text, (
                f"{row['anchor_file']} no longer defines "
                f"{row['anchor_symbol']} -- update the inventory row"
            )

    # frob:waive PERF004 reason="sorted() only formats tiny sets for assert messages, \
    # not hot-path work"
    def test_every_anchor_fragment_resolves_to_guide_h1(self) -> None:
        for row in _load_inventory():
            anchor_file = REPO_ROOT / row["anchor_file"]
            text = anchor_file.read_text(encoding="utf-8")
            fragments = [
                frag
                for path, frag in _ANCHOR_RE.findall(
                    _fold_directive_continuations(text)
                )
                if path == row["guide"]
            ]
            assert fragments, (
                f"{row['anchor_file']} anchor for {row['guide']} carries no #fragment"
            )
            guide_text = (REPO_ROOT / row["guide"]).read_text(encoding="utf-8")
            # DOC002 semantics: a fragment resolves via a heading slug OR an
            # explicit <a id="..."> anchor in the guide.
            slugs = {slugify(h) for h in _H1_RE.findall(guide_text)}
            slugs |= set(_A_ID_RE.findall(guide_text))
            have = sorted(slugs)
            for frag in fragments:
                assert frag in slugs, (
                    f"anchor #{frag} in {row['anchor_file']} matches no "
                    f"heading slug or <a id> in {row['guide']} (have: {have})"
                )

    # frob:waive PERF004 reason="sorted() only formats tiny sets for assert messages, \
    # not hot-path work"
    def test_no_orphan_guides(self) -> None:
        known = {Path(row["guide"]).name for row in _load_inventory()}
        on_disk = {p.name for p in EXTENDING.glob("*.md") if p.name != "README.md"}
        orphans = on_disk - known
        assert not orphans, (
            f"guide files with no inventory row: {sorted(orphans)} -- add "
            "rows to registry_of_registries.json"
        )

    # frob:waive PERF004 reason="sorted() only formats tiny sets for assert messages, \
    # not hot-path work"
    def test_probe_table_and_inventory_agree(self) -> None:
        inventory_ids = {row["id"] for row in _load_inventory()}
        probe_ids = set(_REGISTRY_PROBES)
        assert inventory_ids == probe_ids, (
            "registry_of_registries.json rows and _REGISTRY_PROBES disagree: "
            f"only-in-inventory={sorted(inventory_ids - probe_ids)} "
            f"only-in-probes={sorted(probe_ids - inventory_ids)}"
        )

    def test_every_probe_still_matches_source(self) -> None:
        for reg_id, (rel_path, pattern) in _REGISTRY_PROBES.items():
            path = REPO_ROOT / rel_path
            assert path.is_file(), f"probe file for {reg_id!r} missing: {rel_path}"
            text = path.read_text(encoding="utf-8")
            assert re.search(pattern, text), (
                f"probe {pattern!r} for {reg_id!r} no longer matches "
                f"{rel_path} -- registry moved or renamed; update the "
                "inventory row, the guide, and this probe together"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
