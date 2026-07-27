"""T-0673 coverage: cross-file concept dedup in `docs/design/registry/`.

Verifies the 10 RECONCILIATION.md finding (b) concepts (plus the finding
(h) full pairwise-scan follow-on splits) carry non-empty, mutually
navigable `cross_refs` in the registry YAML, and that every backtick id
named in RECONCILIATION.md's finding (b) SPLIT section resolves to a real
registry id with a populated `cross_refs` list -- a standalone check of
the same invariant `src/frob/gates/_registry_exhaustiveness.py`'s REG004
enforces, kept independent so this ticket's evidence does not depend on
reaching into gate internals.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_DIR = REPO_ROOT / "docs" / "design" / "registry"

# The full mesh groups this ticket wired up: finding (b)'s 10 named
# concepts plus finding (h)'s pairwise-scan follow-on splits.
LINKED_GROUPS: tuple[tuple[str, ...], ...] = (
    (
        "ACC-5-2-CIRCUIT-BREAKER",
        "ACC-5-4-CIRCUIT-BREAKER",
        "MSIO-CIRCUIT-BREAKER",
        "RELEASEIT-PAT-CIRCUIT-BREAKER",
    ),
    ("ACC-5-2-BULKHEAD", "ACC-5-4-BULKHEAD", "RELEASEIT-PAT-BULKHEADS"),
    (
        "ACC-5-4-IDEMPOTENT-RECEIVER",
        "SDC-5-IDEMPOTENT-RECEIVER",
        "EIP-IDEMPOTENT-RECEIVER",
    ),
    ("ACC-5-4-ANTI-CORRUPTION-LAYER", "MSIO-ANTI-CORRUPTION-LAYER"),
    ("POEAA-VALUE-OBJECT", "DDD-II-VALUE-OBJECTS"),
    ("POEAA-REPOSITORY", "PAT-TRAP-21-LAW-OF-DEMETER-DI-CONTAINERS-ORM-REPOSITORY"),
    ("ACC-5-2-TIMEOUT-PATTERN-PRESENT", "SDC-5-TIMEOUT", "RELEASEIT-PAT-TIMEOUTS"),
    ("GOF-SINGLETON", "EFFJAVA-SINGLETON", "PAT-TRAP-11-SINGLETON-OVERUSE"),
    (
        "ACC-4-ANEMIC-DOMAIN-MODEL",
        "PAT-TRAP-20-ANEMIC-DOMAIN-GOD-OBJECT-LAVA-FLOW",
        "POEAA-DOMAIN-MODEL",
    ),
    ("ACC-5-4-SAGA", "MSIO-SAGA", "SDC-4-OUTBOX-SAGA-PATTERNS"),
    ("ACC-5-6-IDEMPOTENCY", "SDC-4-IDEMPOTENCY"),
    (
        "ACC-5-2-SHED-LOAD-GOVERNOR",
        "ACC-5-8-LOAD-SHEDDING",
        "SDC-5-LOAD-SHEDDING",
        "RELEASEIT-PAT-SHED-LOAD",
    ),
    ("ACC-5-7-STRIDE", "SEC-THREAT-FRAMEWORK-STRIDE"),
    ("ACC-1-5-COMPOSITION-OVER-INHERITANCE", "PAT-TRAP-10-INHERITANCE-VS-COMPOSITION"),
    ("ACC-1-5-FAIL-FAST", "ACC-5-2-FAIL-FAST", "RELEASEIT-PAT-FAIL-FAST"),
    ("ACC-2-1-SPECULATIVE-GENERALITY", "PAT-TRAP-09-YAGNI-SPECULATIVE-GENERALITY"),
    ("ACC-2-2-C5-COMMENTED-OUT-CODE", "CWE-1085"),
    ("ACC-3-6-CONTEXT-MANAGER-WITH", "PYIDIOM-CONTEXT-MANAGER"),
    ("ACC-4-LAVA-FLOW-DEAD-FROZEN-CODE-NOBODY-DARES-REMOVE", "CWE-561"),
    ("ACC-5-2-CASCADING-FAILURES", "RELEASEIT-ANTI-CASCADING-FAILURES"),
    ("ACC-5-2-INTEGRATION-POINTS", "RELEASEIT-ANTI-INTEGRATION-POINTS"),
    ("ACC-5-2-STEADY-STATE", "RELEASEIT-PAT-STEADY-STATE"),
    ("ACC-5-2-UNBOUNDED-RESULT-SETS", "RELEASEIT-ANTI-UNBOUNDED-RESULT-SETS"),
    ("ACC-5-4-ASYNCHRONOUS-REQUEST-REPLY", "EIP-REQUEST-REPLY"),
    ("ACC-5-4-COMPETING-CONSUMERS", "EIP-COMPETING-CONSUMERS"),
    (
        "ACC-5-4-EVENT-SOURCING",
        "MSIO-EVENT-SOURCING",
        "PAT-TRAP-18-PREMATURE-CQRS-EVENT-SOURCING",
    ),
    ("ACC-5-4-MESSAGING-BRIDGE", "EIP-MESSAGING-BRIDGE"),
    ("ACC-5-4-OUTBOX-TRANSACTIONAL-OUTBOX", "MSIO-TRANSACTIONAL-OUTBOX"),
    ("ACC-5-4-PIPES-AND-FILTERS", "EIP-PIPES-AND-FILTERS", "POSA1-PIPES-AND-FILTERS"),
    ("ACC-5-7-ATTACK-SURFACE", "CWE-1125"),
    ("ACC-5-7-LEAST-PRIVILEGE", "CWE-272"),
    ("ACC-5-8-CONNECTION-POOLING", "CWE-1072"),
    ("CWE-609", "POSA2-DOUBLE-CHECKED-LOCKING-OPTIMIZATION"),
    (
        "MSIO-DISTRIBUTED-TRACING",
        "SDC-11-DAPPER-A-LARGE-SCALE-DISTRIBUTED-SYSTEMS-TRACING-INFRASTRUCTURE",
        "SDC-7-DISTRIBUTED-TRACING-DAPPER",
    ),
)

# Reviewed-and-rejected pairwise-scan candidates (finding (h)): these
# MUST stay unlinked -- a regression that starts auto-linking generic
# token overlaps would silently reintroduce the failure mode finding (h)
# exists to reject.
REJECTED_PAIRS: tuple[tuple[str, str], ...] = (
    ("ACC-2-1-DATA-CLASS", "CWE-1042"),
    ("ACC-2-1-DATA-CLASS", "CWE-492"),
    ("ACC-2-1-DATA-CLASS", "CWE-499"),
    ("ACC-2-1-MUTABLE-DATA", "CWE-1283"),
    ("CWE-562", "EIP-RETURN-ADDRESS"),
    ("CWE-924", "EIP-MESSAGE-CHANNEL"),
)


def _cross_refs(entry: dict[str, Any]) -> set[str]:
    """Normalize an entry's `cross_refs` field (absent/None/list) to a
    plain string set for membership checks."""
    return {str(ref) for ref in (entry.get("cross_refs") or [])}


def _load_all_entries() -> dict[str, dict[str, Any]]:
    """Load every `id`-bearing entry across all registry YAML files, keyed
    by id -- the same flatten-and-index shape the registry gate's own
    `_index_entries_by_id` builds, kept independent of gate internals.
    """
    entries: dict[str, dict[str, Any]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                if isinstance(item, dict) and "id" in item:
                    entry = cast("dict[str, Any]", item)
                    entries[str(entry["id"])] = entry
                else:
                    walk(item)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)

    for path in sorted(REGISTRY_DIR.glob("*.yaml")):
        walk(yaml.safe_load(path.read_text(encoding="utf-8")))
    return entries


# frob:ticket T-0972
class TestLinkedGroupsResolveAndAreNavigable:
    """Every declared concept group is a real, non-empty, mutually
    reachable `cross_refs` mesh -- the graph-navigability property this
    ticket's cross-file dedup pass exists to establish."""

    # frob:tests \
    # tests/unit/strata/test_registry_cross_refs.py::TestLinkedGroupsResolveAndAreNavig\
    # able.test_every_group_id_exists
    def test_every_group_id_exists(self):
        entries = _load_all_entries()
        for group in LINKED_GROUPS:
            for entry_id in group:
                assert entry_id in entries, f"{entry_id} not found in any registry file"

    # frob:ticket T-0972
    # frob:tests \
    # tests/unit/strata/test_registry_cross_refs.py::TestLinkedGroupsResolveAndAreNavig\
    # able.test_every_member_cross_refs_every_other_member
    def test_every_member_cross_refs_every_other_member(self):
        entries = _load_all_entries()
        for group in LINKED_GROUPS:
            for entry_id in group:
                cross_refs = _cross_refs(entries[entry_id])
                others = set(group) - {entry_id}
                missing = others - cross_refs
                # frob:waive PERF004 reason="test-file assertion message; missing/cross_refs are this loop's own per-entry distinct sets, not hot-path re-sort"  # noqa: E501
                assert not missing, (
                    f"{entry_id} is missing cross_refs to {sorted(missing)} "
                    f"(has {sorted(cross_refs)})"
                )


class TestRejectedPairsStayUnlinked:
    """The finding (h) false-positive pairs (generic-token overlap, not
    the same real-world concept) must never silently gain a cross_ref --
    that would reintroduce the exact failure mode finding (h) rejected
    them for."""

    # frob:tests \
    # tests/unit/strata/test_registry_cross_refs.py::TestRejectedPairsStayUnlinked.test\
    # _rejected_pairs_not_cross_linked
    def test_rejected_pairs_not_cross_linked(self):
        entries = _load_all_entries()
        for left, right in REJECTED_PAIRS:
            assert left in entries and right in entries
            left_refs = _cross_refs(entries[left])
            right_refs = _cross_refs(entries[right])
            assert right not in left_refs, (
                f"{left} unexpectedly cross_refs rejected pair {right}"
            )
            assert left not in right_refs, (
                f"{right} unexpectedly cross_refs rejected pair {left}"
            )


class TestReconciliationSplitSectionFullyLinked:
    """Every backtick-quoted id RECONCILIATION.md's finding (b) SPLIT
    section names resolves to a registry entry with a non-empty
    `cross_refs` -- mirrors the invariant REG004
    (`src/frob/gates/_registry_exhaustiveness.py`) enforces, checked here
    independently of gate internals."""

    # frob:tests \
    # tests/unit/strata/test_registry_cross_refs.py::TestReconciliationSplitSectionFull\
    # yLinked.test_finding_b_ids_all_linked
    def test_finding_b_ids_all_linked(self):
        text = (REGISTRY_DIR / "RECONCILIATION.md").read_text(encoding="utf-8")
        start = text.find("### (b) SPLIT entries")
        assert start != -1, "finding (b) section missing from RECONCILIATION.md"
        end = text.find("\n### (c)", start)
        section = text[start : end if end != -1 else len(text)]

        split_ids = frozenset(re.findall(r"`([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)`", section))
        assert split_ids, "expected at least one backtick-quoted id in finding (b)"

        entries = _load_all_entries()
        for entry_id in split_ids:
            assert entry_id in entries, (
                f"{entry_id} named in finding (b) but not in the registry"
            )
            cross_refs = entries[entry_id].get("cross_refs") or []
            assert cross_refs, (
                f"{entry_id} named in finding (b) still has empty cross_refs"
            )
