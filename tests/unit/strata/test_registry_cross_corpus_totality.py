"""T-0678 (epic T-0346's cross-corpus totality close condition): extends
T-0343's per-domain drift-lock with a standing check spanning the WHOLE
registry (all 11 source docs / 1950+ entries), not one domain file at a
time -- RECONCILIATION.md findings (a) (prose-only docs) and (b)/(h)
(cross-file concept duplication) closed as one-time reconciliation passes
by T-0673 (dedup) and the prose-only id-minting pass; this module is the
STANDING evidence that those closures do not silently regress, mirroring
T-0658's "own scope/test tree, epic-owned closing evidence" relationship
to its own prerequisite reconciliation ticket (T-0392).

Two disclosed scope boundaries, stated here rather than silently assumed
closed:

1. Acceptance [0] ("every cross_refs-eligible concept has exactly one
   canonical id or a recorded justification for staying split") is
   locked GENERICALLY across the whole registry (every entry's
   `cross_refs` resolves to real ids and is mutually navigable), not by
   re-running T-0673's approximate name-token pairwise scan -- that scan
   is explicitly documented (RECONCILIATION.md finding (h) closing notes)
   as heuristic, over-inclusive, and requiring human reviewer judgment
   per candidate pair (`REJECTED_PAIRS` in `test_registry_cross_refs.py`
   exists exactly because auto-linking near-name-matches produces false
   positives); a literal re-scan-and-lock would need to re-litigate that
   judgment call on every future registry addition, which is not what
   "drift-lock the reconciliation that already happened" means. What CAN
   be mechanically locked forever, cheaply and without false positives,
   is that cross_refs stays internally consistent (no dangling id, no
   one-directional link) -- exactly what `TestCrossCorpusLinkageIntegrity`
   below checks, over every entry in the registry, not just the 35
   already-known groups.
2. Acceptance [1] ("a future corpus doc edit that adds a table row with
   no matching registry id... fails the build") is locked on the
   REGISTRY side of the prose-only retrofit (finding (a)'s 156 minted
   ids: `SLH-RULE-*`/`SLH-ARCH-EVA-*`/`SLH-SYS-EVA-*` = 23,
   `EVA-<LANG>-*` = 112, `PAT-TRAP-*` = 21, each still carrying the
   correct `source_doc` pointer) by `TestProseOnlyRetrofitIntegrity`
   below -- an id silently disappearing, or its `source_doc` drifting
   off the real file, both fail loudly. Parsing the 3 source docs'
   markdown TABLES themselves to detect a genuinely NEW row with no
   corresponding id is NOT implemented here (each of the 3 docs uses a
   different table shape -- named headings, per-language multi-column
   tables, a narrative coverage ledger -- and a robust parser for all
   three is a real, separate undertaking); disclosed as a follow-up gap
   the same way RECONCILIATION.md's own "Disposition assignment" /
   "semantic entity-resolution" items are disclosed rather than silently
   claimed closed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_DIR = REPO_ROOT / "docs" / "design" / "registry"


#: `cross_refs` carries TWO distinct id namespaces (discovered scanning the
#: real data for this module): most entries point at ANOTHER registry
#: entry's own `id` (the T-0673 dedup-linkage case this module locks), but
#: some point OUTSIDE the registry entirely -- a `FILE:SECTION` doc
#: pointer (e.g. `security-corpus:cwe-top25-2025`, finding (e)) or a
#: `FP-*` code-level fingerprint-pattern id (`src/frob/vet`'s pattern
#: catalog, e.g. `FP-TLS-VERIFY-001`, T-0188/T-0510) -- neither of which
#: is a registry `id` and neither of which this module's dangling-ref
#: check can or should resolve. A ref matching either shape is a
#: documented external pointer, not a dangling link.
def _is_external_pointer(ref: str) -> bool:
    """`True` for a `cross_refs` value that intentionally points OUTSIDE
    this registry's own id space (a `FILE:SECTION` doc pointer, or a
    `FP-*` code-level fingerprint-pattern id) -- see the module-level
    comment above for the two real shapes this codebase's data uses."""
    return ":" in ref or ref.startswith("FP-")


#: RECONCILIATION.md finding (a): the 3 previously prose-only docs' minted
#: id prefixes, their registry file, expected count (23/112/21 = 156
#: total), and the real source doc path each entry's `source_doc` field
#: must still point at.
_PROSE_ONLY_RETROFITS: tuple[tuple[str, str, str, int], ...] = (
    (
        "arch-checks.yaml",
        "SLH-",
        "docs/design/structural-linter-adversarial-hardening.md",
        23,
    ),
    ("evasion.yaml", "EVA-", "docs/design/capability-evasion-taxonomy.md", 112),
    ("patterns.yaml", "PAT-TRAP-", "docs/design/design-pattern-traps-corpus.md", 21),
)


# frob:ticket T-0678
def _load_all_entries() -> dict[str, dict[str, Any]]:
    """Every `id`-bearing entry across all registry YAML files, keyed by
    id -- raw YAML (not the typed `RegistryEntry` model, which has no
    `name`/`source_doc` field) so this module can read those two fields
    directly, the same load shape `test_registry_cross_refs.py`'s own
    `_load_all_entries` uses (kept independent, not imported, to match
    that module's own "standalone check, no gate-internals dependency"
    precedent)."""
    entries: dict[str, dict[str, Any]] = {}

    def walk(node: Any, source_file: str) -> None:
        if isinstance(node, list):
            for item in node:
                if isinstance(item, dict) and "id" in item:
                    entry = cast("dict[str, Any]", dict(item))
                    entry["_source_file"] = source_file
                    entries[str(entry["id"])] = entry
                else:
                    walk(item, source_file)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value, source_file)

    for path in sorted(REGISTRY_DIR.glob("*.yaml")):
        walk(yaml.safe_load(path.read_text(encoding="utf-8")), path.name)
    return entries


# frob:ticket T-0678
# frob:tests tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity.test_every_cross_ref_resolves_to_a_real_id  # noqa: E501
# frob:tests tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity.test_every_cross_ref_is_mutually_navigable  # noqa: E501
class TestCrossCorpusLinkageIntegrity:
    """Acceptance [0], the mechanically-lockable half: every declared
    `cross_refs` link in the WHOLE registry (all files, not just the 35
    known groups) resolves to a real id and is reciprocated -- so a
    future edit that adds a one-directional or dangling cross-reference
    (breaking the "exactly one canonical id or a recorded, navigable
    split" property T-0673 established) fails the build immediately,
    without re-running the heuristic name-similarity scan."""

    # frob:ticket T-0678
    def test_every_cross_ref_resolves_to_a_real_id(self) -> None:
        entries = _load_all_entries()
        dangling = [
            (entry_id, ref)
            for entry_id, entry in entries.items()
            for ref in (str(r) for r in (entry.get("cross_refs") or []))
            if not _is_external_pointer(ref) and ref not in entries
        ]
        assert dangling == [], f"dangling cross_refs (id, missing target): {dangling}"

    # frob:ticket T-0678
    def test_every_cross_ref_is_mutually_navigable(self) -> None:
        entries = _load_all_entries()
        one_directional = [
            (entry_id, ref)
            for entry_id, entry in entries.items()
            for ref in (str(r) for r in (entry.get("cross_refs") or []))
            if not _is_external_pointer(ref)
            and ref in entries
            and entry_id not in (entries[ref].get("cross_refs") or [])
        ]
        assert one_directional == [], (
            f"one-directional cross_refs (id, target that doesn't link back): "
            f"{one_directional}"
        )


# frob:ticket T-0678
# frob:tests tests/unit/strata/test_registry_cross_corpus_totality.py::TestProseOnlyRetrofitIntegrity.test_retrofit_counts_and_source_doc_pointers_hold  # noqa: E501
class TestProseOnlyRetrofitIntegrity:
    """Acceptance [1], the registry-side half (module docstring's
    disclosed scope boundary: the doc-table-row-parsing half is NOT
    implemented here): the 156 ids RECONCILIATION.md finding (a) minted
    for the 3 previously prose-only docs still exist, in the expected
    count per prefix, each still pointing its `source_doc` at the real
    source file -- an id quietly disappearing, or its source pointer
    rotting, both fail loudly."""

    # frob:ticket T-0678
    def test_retrofit_counts_and_source_doc_pointers_hold(self) -> None:
        entries = _load_all_entries()
        for registry_file, prefix, source_doc, expected_count in _PROSE_ONLY_RETROFITS:
            matching = {
                entry_id: entry
                for entry_id, entry in entries.items()
                if entry_id.startswith(prefix)
                and entry["_source_file"] == registry_file
            }
            matching_ids = sorted(matching)
            assert len(matching) == expected_count, (
                f"{registry_file}::{prefix}*: expected {expected_count} entries, "
                f"found {len(matching)}: {matching_ids}"
            )
            wrong_source = {
                entry_id: entry.get("source_doc")
                for entry_id, entry in matching.items()
                if entry.get("source_doc") != source_doc
            }
            assert wrong_source == {}, (
                f"{registry_file}::{prefix}*: entries with a source_doc other than "
                f"{source_doc!r}: {wrong_source}"
            )
