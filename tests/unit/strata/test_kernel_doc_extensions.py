"""Docs check for docs/strata/kernel.md (T-4952/T-4681, SF-21).

Asserts kernel.md no longer claims conditional flows are the only kernel
extension, and that every one of the eight measured non-sugar keyword
domains (scratchpad/STRATA-KEYWORDS.md) is named as a deliberate,
recorded extension rather than drift.
"""

from __future__ import annotations

import re
from pathlib import Path

KERNEL_DOC = Path(__file__).resolve().parents[3] / "docs" / "strata" / "kernel.md"

# Substrings that must each appear somewhere in the doc, one per domain
# (case-insensitive), proving the domain is named.
DOMAIN_MARKERS = [
    "code binding",
    "capability via-lists",
    "waivers",
    "entity/architecture",
    "vmodel",
    "policy",
    "host/acl",
    "kerberos",
]

# The false claim this ticket removes -- any sentence asserting no other
# kernel extension exists or is planned must be gone.
FALSE_CLAIM_RE = re.compile(
    r"no other kernel extension exists or is planned", re.IGNORECASE
)


def _read_kernel_doc() -> str:
    """Load docs/strata/kernel.md's text once for the assertions below."""
    return KERNEL_DOC.read_text(encoding="utf-8")


def test_false_no_other_extension_claim_is_gone() -> None:
    """kernel.md must not claim no other kernel extension exists or is planned."""
    text = _read_kernel_doc()
    assert not FALSE_CLAIM_RE.search(text), (
        "docs/strata/kernel.md still asserts no other kernel extension "
        "exists or is planned; ~79 of 139 keywords are non-sugar across "
        "eight domains (T-4681/SF-21)."
    )


def test_all_eight_extension_domains_are_named() -> None:
    """kernel.md must name each of the eight measured extension domains."""
    text = _read_kernel_doc().lower()
    missing = [marker for marker in DOMAIN_MARKERS if marker not in text]
    assert not missing, (
        f"docs/strata/kernel.md is missing these extension domains: {missing}"
    )


def test_law_one_record_present_for_each_domain() -> None:
    """Each domain section must state its law-1 record (prover vs Python-side)."""
    text = _read_kernel_doc()
    law_one_mentions = len(re.findall(r"Law-1\s+record", text))
    assert law_one_mentions >= len(DOMAIN_MARKERS), (
        "docs/strata/kernel.md must carry a 'Law-1 record' for each of the "
        f"eight domains; found {law_one_mentions}, need >= {len(DOMAIN_MARKERS)}."
    )
