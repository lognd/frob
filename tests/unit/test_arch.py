"""
Unit tests for frob.arch.analyze_project.

The frob.arch module may not exist yet; these tests are written against its
expected public API and will be skipped if the module is unavailable.

The ArchResult model has a `suggestions` list of ArchSuggestion objects.
Each ArchSuggestion has: file, line, category, severity, message, detail.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"

try:
    from frob.arch import analyze_project

    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")


# ---------------------------------------------------------------------------
# god-class detection
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# long-function detection
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# deep-nesting detection
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# T-1066: deep-nesting's detector-owned arch-exempt directive -- a reasoned
# per-function override for a genuinely irreducible algorithm (mirrors the
# ARCH001 reasoned-waiver precedent, but stays off the generic waiver/
# Violation channel deep-nesting is deliberately excluded from).
# ---------------------------------------------------------------------------


# frob:ticket T-1066
_DEEP_NEST_SRC = (FIXTURES / "arch_python" / "src" / "deep_nest.py").read_text()




# ---------------------------------------------------------------------------
# analyze_project
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# output format
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# interface-level integration
# ---------------------------------------------------------------------------


def test_arch_end_to_end_analyze_then_render():
    # frob:tests src/frob/arch kind="integration"
    # Drive the whole arch boundary: walk a real fixture tree, produce an
    # ArchResult, and round-trip it through both public renderers.
    result = analyze_project(FIXTURES / "arch_python" / "src")
    categories = {s.category for s in result.suggestions}
    assert {"god-class", "long-function", "deep-nesting"} <= categories
    data = json.loads(result.as_json())
    assert len(data["suggestions"]) == len(result.suggestions)
    assert isinstance(result.as_text(), str)


# ---------------------------------------------------------------------------
# T-0359: advisory categories exempt test files
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# T-0360: dispatch/validator families are not abstraction-opportunities
# ---------------------------------------------------------------------------






# ---------------------------------------------------------------------------
# T-0368: test files and fixtures/ data are exempt from large-file and
# deep-nesting too (extends the T-0359 advisory-category exemption)
# ---------------------------------------------------------------------------








# ---------------------------------------------------------------------------
# T-0370: abstraction-opportunity requires signature-specificity or
# body-similarity, not a bare shared signature
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# T-1068: language-parity groups (filed from T-0393) are not
# abstraction-opportunities -- the same false-positive class T-0360's
# dispatch-family exclusion covers, but for parallel per-language
# tree-sitter walkers (_py_/_rust_/_kt_/_ts_/_cpp_) instead of a shared
# call/registry site.
# ---------------------------------------------------------------------------












# ---------------------------------------------------------------------------
# design-pattern recommender (T-0332): HALLMARK->PATTERN and
# ANTI-PATTERN->ESCAPE advisory suggestions.
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# T-0609: normalized code model + adapter protocol
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# T-0610: PythonAdapter -- maps a real parsed python file onto NormalizedModule
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# T-0611: TypeScriptAdapter -- maps a real parsed TypeScript file onto
# NormalizedModule, mirroring TestPythonAdapter's structure. Hand-built
# inline TS fixtures (written to tmp_path) rather than a shared fixtures/
# directory, since none exists for TypeScript yet.
# ---------------------------------------------------------------------------






# ---------------------------------------------------------------------------
# T-0612: RustAdapter -- maps a real parsed rust file onto NormalizedModule,
# mirroring TestTypeScriptAdapter's structure. Hand-built inline .rs
# fixtures (written to tmp_path), same as TypeScript's approach.
# ---------------------------------------------------------------------------






# ---------------------------------------------------------------------------
# T-0614: KotlinAdapter -- maps a real parsed kotlin file onto
# NormalizedModule, mirroring TestRustAdapter's structure. `tree-sitter-
# kotlin` (via `tree-sitter-language-pack`) exposes almost no named fields
# (see `frob.arch._kotlin`'s module docstring), so fixtures are built and
# parsed directly through `frob.lang._walk_kotlin.parse_kotlin` (source
# bytes -> Tree) rather than `frob.lang.raw_tree` -- `.kt`/`.kts` are not
# wired into `frob.lang`'s `_EXTENSION_TABLE`/`_extract.py` central
# dispatch (that is a separate follow-up ticket, T-draft-a78fa200: wiring
# them there needs a real `_walk_kotlin` RawSymbol walker too, or
# `parse_file`/`frob check` would KeyError on any real `.kt` file).
# ---------------------------------------------------------------------------






# ---------------------------------------------------------------------------
# T-0615: the N:1 cross-language equivalence meta-test -- EPIC T-0329's own
# closing acceptance criterion ("an arch check written once fires correctly
# across python+ts+rust+kotlin on equivalent code"). T-0610/T-0611/T-0612/
# T-0614 each proved this PAIRWISE (python vs one other language); this is
# the four-way superset: one equivalent fixture per language under
# `tests/fixtures/arch/<language>/equiv.<ext>` (same base/derived class +
# field + overriding method shape, same nested if/for/while long function,
# same three-way dispatch function), adapted through all four
# `LanguageAdapter`s, asserting:
#
#   1. every `NormalizedModule` expresses the SAME entity counts/kinds for
#      the equivalent constructs, with per-language WAIVERS documented
#      (not silently skipped) where a language genuinely lacks a construct
#      -- python has no static "override" keyword, so its
#      `NormalizedFunction.overrides` stays `None` even for a genuine
#      override, unlike TS/kotlin's explicit `override` modifier and
#      rust's trait-impl inference;
#   2. the SHARED check (`_iter_normalized_functions`/`_normalized_is_complex`,
#      migrated once in T-0610 and reused unmodified by every adapter's
#      pairwise test) fires IDENTICALLY across all four on the equivalent
#      long/complex function;
#   3. the per-language branch-counting divergence on the SAME three-way
#      dispatch construct (python's if/elif chain folds to ONE branch;
#      TS's `switch` produces ZERO branches; rust's `match` and kotlin's
#      `when` each produce THREE, one per arm/entry) is pinned as an
#      EXPECTED difference with the rationale here, so future drift in
#      either direction (an adapter starting -- or stopping -- to count
#      arms) fails this test loudly instead of silently.
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# T-0695: structural fork/pool hazard family
# ---------------------------------------------------------------------------








# ---------------------------------------------------------------------------
# T-0618: LSP checks -- override contract violations (docs/modules/arch.md#lsp-checks)
# ---------------------------------------------------------------------------
















# ---------------------------------------------------------------------------
# T-0619: ISP checks -- fat interface, narrow-client usage (docs/modules/arch.md#isp-checks)
# ---------------------------------------------------------------------------














# ---------------------------------------------------------------------------
# T-0620: DIP layering contract + no-DI construction smell (docs/modules/arch.md#dip-layering-contract)
# ---------------------------------------------------------------------------










# ---------------------------------------------------------------------------
# T-0621: type-driven design checks (docs/modules/arch.md#type-driven-design-checks)
# ---------------------------------------------------------------------------












# ---------------------------------------------------------------------------
# T-0622: logging discipline checks -- unlogged error path, unlogged
# boundary, print-as-diagnostic
# ---------------------------------------------------------------------------










# ---------------------------------------------------------------------------
# T-0623: fallibility checks -- unhandled Result, swallowed exception,
# recoverable-error-wrong-signature, over-broad except
# ---------------------------------------------------------------------------




























# ---------------------------------------------------------------------------
# T-0624: misc design smells -- mutable default arg, feature envy, data
# clumps, magic literals, dead private code, deep inheritance, temporal
# coupling
# ---------------------------------------------------------------------------


















# ---------------------------------------------------------------------------
# T-0625: module dependency cycle detection
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# T-0745: protocol summary engine -- per-function fixpoint over the call graph
# ---------------------------------------------------------------------------

