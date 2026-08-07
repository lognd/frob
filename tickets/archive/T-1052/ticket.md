---
id: T-1052
title: 'DEPR005: callgraph-resolved references + line-insensitive baseline keying
  (bare-name text match plus file:line keys red-main on nearly every land)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_deprecated_baseline.py
- src/frob/gates/__init__.py
- tests/unit/gates/test_deprecated_baseline.py
- docs/modules/gates.md
- frob-deprecated-baseline.lock.json
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: 'Ticket body explicitly requires restoring DEPR005 to error tier and

    removing the frob.toml [gates.severity] demotion block as part of this

    fix; frob.toml was omitted from the declared scope globs by oversight.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded
- tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_line_shift_leaves_baseline_byte_identical
- tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_shrinkage_keeps_lower_count_never_grows
- tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_never_absorbs_growth_inside_an_already_baselined_file
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_same_count_as_baseline_does_not_fire
- tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line
- tests/unit/gates/test_deprecated_baseline.py::TestFileReferenceCounts::test_buckets_by_file
- tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedBaselineEntry::test_file_counts_decodes_encoded_references
- tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_first_seen_symbol_is_seeded_whole
- tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_shrinkage_drops_stale_references
- tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_never_absorbs_a_new_reference
- tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_symbol_no_longer_deprecated_is_dropped
designated_repro_test: null
acceptance:
- text: given a repo where subprocess.run is called in a new file, when DEPR005 evaluates
    a deprecated symbol named run, then the new file is NOT reported as a caller unless
    the call graph resolves an edge to that exact symbol
  evidence:
  - tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded
- text: given a land that only shifts line numbers in a file already referencing a
    deprecated symbol, when DEPR005 re-evaluates, then no new-caller violation fires
    and the committed baseline is byte-identical
  evidence:
  - tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_line_shift_leaves_baseline_byte_identical
- text: given the redesigned lock format, when tighten_deprecated_baseline runs, then
    the shrink-only contract holds on the new (file, symbol) key shape
  evidence:
  - tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_shrinkage_keeps_lower_count_never_grows
  - tests/unit/gates/test_deprecated_baseline.py::TestTighten::test_never_absorbs_growth_inside_an_already_baselined_file
  - tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_same_count_as_baseline_does_not_fire
  - tests/unit/gates/test_deprecated_baseline.py::TestDepr005ViolationsGrowth::test_growth_beyond_baseline_fires_at_the_right_file_and_line
threat: null
component: null
---
## Description

DEPR005's new-caller ratchet red-mained three times in one session
(2026-07-27 night: re-baselines 54273735, 1ed269c1, plus a third hit
from T-0602's land) because BOTH of its axes are churn-hostile:

1. Reference DETECTION is a bare-short-name text match.
   `deprecated_current_references` matches the deprecated symbol's bare
   name, so for `src/frob/app/xref_runner.py::run` every
   `subprocess.run(`, gate-runner `.run(`, and any other textual `run`
   occurrence in the repo counts as a "caller" -- the committed baseline
   carries ~900 references per `run`-named symbol, nearly all junk
   (verified: the flagged "new callers" at
   tests/test_gates_tick009_tick010.py:86 and
   src/frob/app/ticket_runner.py:2206 are literally `subprocess.run`
   calls). Any land that ADDS a file containing `.run(` red-mains.

2. Baseline KEYING is file:line. Any land that edits lines ABOVE an
   existing reference shifts it, and the shifted line reads as a new
   caller (T-1023's test_gates.py edit produced 198 false errors at
   once; T-0714's land produced 6 more).

Fix both axes:
- Resolve references through the call graph / import resolution the way
  DEPR001-004 and the T-0639 caller-graph design doc already intend --
  a caller is an edge to THAT symbol, not a name coincidence.
  `frob.graph.callgraph.build_call_graph` is the shared substrate.
- Key the baseline line-insensitively: (referencing file, deprecated
  symbol) pairs, optionally with a per-file count for growth detection
  inside an already-referencing file. A pure line shift or an unrelated
  edit to a referencing file must NOT change the baseline identity.
- Regenerate the committed lock in the new format; drop the junk
  references that bare-name matching accumulated.
- Keep tighten_deprecated_baseline's shrink-only contract on the new
  key shape.

Until this lands, DEPR005 is demoted to warn in frob.toml
[gates.severity] (comment cites this ticket) -- three coordinator
re-stamps in 90 minutes is hand-maintenance of a broken signal, not
enforcement.