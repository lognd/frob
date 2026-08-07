---
id: T-0435
title: 'README/prose-claim drift-lock: bind README''s command table (+ checkable counts)
  to the real subcommand registry -- frob was blind to README drift'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0424
tier: ticket
sprint: null
scope:
- src/frob/gates/
- README.md
- docs/
- tests/test_docblocks_gate.py
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_docblocks_gate.py
  reason: DOC005 unit tests live here
  actor: logan
  at: '2026-07-22'
- op: add
  glob: pyproject.toml
  reason: REL001 version bump for new public gate symbols (doc005_gate)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: CHANGELOG.md
  reason: REL001 version bump for new public gate symbols (doc005_gate)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: REL001 release-stamp artifacts updated for version bump
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: REL001 release-stamp artifacts updated for version bump
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_missing_row_for_real_command_fails
- tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_stale_row_for_removed_command_fails
- tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_fully_covered_table_passes
- tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_count_claim_mismatch_fails
- tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_count_claim_matching_passes
- tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_no_config_means_no_readme_checking
designated_repro_test: null
threat: null
component: null
---
User (2026-07-20): noticed doc drift in the base README.md -- why was it allowed? frob should have flagged it. ROOT CAUSE (the meta-principle: a gap in our compliance is a gap in frobs enforcement): README carries ~0 frob:describes anchors (grep finds 1 in the whole file), so it is UNANCHORED prose. DRIFT001/002 detect code<->doc drift THROUGH anchors; the README command table is not bound to the actual argparse subcommand registry, so adding frob vet/sys/deploy/serve/perf/mutate/stats/release during the rework never flagged the README table as stale -- it was missing 8 of 25 real commands (a third, incl. major subsystems). Same existence-not-verified class: README claims a command set unbound to the truth (the real commands), so it drifts silently. FIXED the immediate drift (added the 8 rows). ENFORCEMENT (this ticket): a drift-lock that binds README (and other top-level prose making CHECKABLE factual claims) to reality -- (1) the README command table is DERIVED-from / checked-against the live subcommand registry (frob --help / the argparse commands): a table row for a command that does not exist FAILS, a real command absent from the table FAILS. (2) Extend to other checkable claims where cheap: a claimed COUNT ("N commands", "N gates", "N tickets") bound to the real count; install/quickstart command snippets that name a subcommand verified to exist. This is an instance of reflexive completeness (T-0424) + the derived-check model (T-0428): dont hand-maintain a prose list that drifts -- check it against the code registry. Acceptance: adding a new subcommand with no README row FAILS the drift-lock; removing a command leaves its README row FAILING; a claimed count that no longer matches FAILS. frobs own README can never again silently omit a third of its commands.