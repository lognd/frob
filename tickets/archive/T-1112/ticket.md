---
id: T-1112
title: 'arch: abstraction-opportunity check-registry-protocol detector exclusion'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestCheckRegistryExclusion::test_check_and_run_checks_names_not_flagged
- tests/unit/test_arch.py::TestCheckRegistryExclusion::test_non_registry_named_group_still_flagged
- tests/unit/test_arch.py::TestCheckRegistryExclusion::test_check_registry_regex_matches_both_shapes
designated_repro_test: null
threat: null
component: null
---
Filed from T-1084 (triage of the 27 arch-package abstraction-opportunity
findings T-1067 handed off). After reading every one of the 27 groups'
member bodies (not just names), none warrant a manual extraction inside
`src/frob/arch/` -- they split into recognizable, already-reviewed shapes
the detector cannot yet tell apart from a real missing abstraction:

1. The check-function registry protocol itself: `_exceptions.py`'s 27-
   member `(NormalizedModule) -> list[ArchSuggestion]` group is not a
   coincidence -- it is literally every `check_*` detector across the
   whole `frob.arch` package (33 functions match `^def check_` under
   `src/frob/arch/*.py`; ~27 of them share the exact bare signature, the
   handful of others take an extra param). This is the package's own
   intentional common interface (every detector module registers this
   way), not duplicate logic to extract -- the exact same "protocol
   family" shape as T-0360's `_is_dispatch_family`/T-1068's language-tag
   exclusion already carve out for other signature-collision classes,
   just not yet generalized to "every function whose name matches
   `^check_` (or another package-wide naming convention) is exempt from
   this category, regardless of arity."
2. Per-construct mirrored builders: `_typescript.py`'s
   `_ts_build_class`/`_ts_build_interface`/`_ts_build_enum` (and the
   `_kotlin.py`-anchored cross-language equivalents T-1068 already
   partially covers) build genuinely DIFFERENT tree-sitter node types
   (`class_declaration` vs `interface_declaration` vs `enum_declaration`)
   into the same `NormalizedClass` return type -- distinct concerns that
   happen to share a return type, not one duplicated function.
3. Deliberately-kept-separate trivial one-liners: `_mayraise.py`,
   `_fallibility.py`, and `_exceptions.py` each define their own
   byte-identical `_bare_callee_name(callee: str) -> str`, and each
   docstring explicitly cross-references the sibling copy ("same
   convention as `frob.arch._fallibility._bare_callee_name`") -- a prior
   ticket (T-0686) already reviewed this exact tradeoff for the sibling
   `_qualname` duplicate and chose to keep the modules independent rather
   than share a one-line private helper across otherwise-unrelated check
   families. Re-deduplicating now would reverse that reviewed decision
   without a new instruction to do so.
4. Large mixed-concern groups (`_async_hazards.py`'s 32-member
   `(Node) -> bool` group, `_concurrency_model.py`'s 27-member
   `(Node) -> str | None` group, etc.): genuinely unrelated tree-walk
   predicates/extractors that only coincide on a common, very generic
   tree-sitter-node signature shape -- the class-1 "coincidental
   collision" case the parent ticket's own body already anticipated.

Add a `_is_check_registry_family` (or similarly named) exclusion to
`frob.arch._python._check_abstraction_opportunities` alongside
`_is_dispatch_family`/`_is_language_parity_family`: a same-signature group
is exempt when every member's bare name matches the package's own
detector-naming convention (`^check_[a-z_]+$`, mirroring how
`_is_dispatch_family`/`_is_language_parity_family` are both purely
name/structure-based, never raw text proximity). Re-measure
`abstraction-opportunity` count after landing and confirm the drop is
exactly the check-registry groups, mirroring T-1068's own before/after
methodology.