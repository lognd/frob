---
id: T-1068
title: 'arch: abstraction-opportunity language-parity exclusion (detector precision)'
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
scope_changes:
- op: add
  glob: tests/unit/test_arch.py
  reason: language-parity exclusion needs its detector tests updated in the same file
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_arch.py::TestLanguageParityExclusion::test_one_member_per_language_not_flagged
- tests/unit/test_arch.py::TestLanguageParityExclusion::test_non_parity_group_still_flagged[duplicate_rust_tag]
- tests/unit/test_arch.py::TestLanguageParityExclusion::test_non_parity_group_still_flagged[untagged_member]
- tests/unit/test_arch.py::TestLanguageParityExclusion::test_tag_requires_underscore_boundary
designated_repro_test: null
threat: null
component: null
---
Filed from T-0393 (failed as too large for one pass). arch/_kotlin.py,
arch/_async_hazards.py, arch/_concurrency_model.py, arch/_cpp.py contain
~10 abstraction-opportunity groups that are parallel per-language
tree-sitter walkers (python/kotlin/rust/typescript/cpp implementing the
same structural operation) -- not the T-0360 dispatch-table shape the
detector already excludes, but the same class of false positive
(intentional per-language parity). Add a new exclusion family to
frob.arch._python._check_abstraction_opportunities (or a sibling helper)
recognizing a same-signature group where every member's name carries a
distinct language-tag prefix/infix (_py_/_kt_/_rust_/_ts_/_cpp_) matched
across a fixed small set of language modules, mirroring T-0360's
structural-detection rigor (no raw text proximity). Re-measure
abstraction-opportunity count after landing; the remaining non-language-
family findings become the scope of a further per-file ticket.