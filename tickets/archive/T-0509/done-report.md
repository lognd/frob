## Done report

Calibrated INV003/INV004 per the ticket's plan:

1. Claim-shape scanning (frob.gates.invariants): _strip_markdown_noise
   drops fenced code, inline code, markdown link targets, and table rows
   before scanning; _is_claim_shaped/_CLAIM_VERB_RE require a claim-verb
   in the same sentence as the trigger word (a heading or bare noun
   phrase asserts nothing regardless of vocabulary). Both
   find_exclusivity_claims (INV003) and find_normative_claims (INV004)
   go through this shared preprocessing.
2. INV003 directory scoping: INV003_SPEC_DIRS = ("docs/modules",
   "docs/strata") -- INV003 now only runs over these two spec-normative
   trees, not all of docs/**.md. INV004 (the coarser advisory signal)
   still runs over all of docs/, unscoped, per the ticket's own framing
   ("consider scoping INV003").
3. Markdown-side frob:waive support: `<!-- frob:waive INV003|INV004
   reason="..." -->` dispositions a genuine-but-unprovable claim (file-
   level for INV003, section-level for INV004 via
   _inv004_waived_headings/_inv004_message_heading), same honesty
   requirement as the code-side frob:waive's WAIVE001 -- a marker with
   no reason= is not honored (tested).

Deliberately NOT folded into the existing _inv003_doc_violations/
_inv004_doc_violations function bodies: doing so at first triggered a
real COV005 false positive -- those private helpers' "frob:ticket
T-0462"/"T-0452" directive targets are reused by public siblings
elsewhere in the same file (inv003_gate, inv004_gate), and COV005
matches old/new directive bindings by (kind, target) alone, so editing
inside the tagged private helper read as "this directive rode onto a
new private symbol" even though nothing rebound. Applying the waiver
filter from the (public, T-0509-tagged) gate functions instead avoids
the collision entirely -- documented in
_file_has_reasoned_doc_waiver's docstring.

Before/after (measured via `uv run frob check --only invariant` on this
worktree, before by reverting the edit and re-running):
INV003 88 -> 31. INV004 677 -> 573 (a further doc-rewording pass in
docs/modules/gates.md itself brought the final combined total in a
full `frob check` run to 601). Combined 765 -> 601/604 depending on
whether the doc-rewording commit is included.

604 (the calibration-only figure) is above the <30 in-ticket-burndown
threshold this ticket's plan set, so the residual was NOT hand-burned
down here. Filed as a follow-up ticket with the exact counts and next
steps (bind real invariants, add reasoned waivers, reword loose
prose, and reconsider INV004's own directory scope since it carries
the larger remaining share).

REL001: bumped 0.49.0 -> 0.50.0 (new public INV003_SPEC_DIRS constant),
CHANGELOG updated, uv.lock refreshed, `frob release stamp` run.

### Changed
```
 .frob-release.json           |   3 +-
 CHANGELOG.md                 |  18 ++++
 docs/modules/gates.md        |  67 +++++++++---
 pyproject.toml               |   2 +-
 src/frob/gates/__init__.py   | 245 +++++++++++++++++++++++++++++++++++++------
 src/frob/gates/invariants.py |  67 +++++++++++-
 tests/test_gates.py          | 141 ++++++++++++++++++++++++-
 tickets.md                   |  68 +++++++++++-
 uv.lock                      |   2 +-
 9 files changed, 554 insertions(+), 59 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_marker_naming_unknown_invariant_still_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_no_exclusivity_language_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_missing_docs_dir_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_claim_without_verb_in_sentence_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_claim_in_code_fence_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_outside_spec_dirs_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_markdown_waive_marker_with_reason_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_markdown_waive_marker_without_reason_still_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv004Gate::test_section_with_normative_language_and_no_invariant_is_advisory` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv004Gate::test_section_with_any_invariant_marker_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv004Gate::test_section_with_no_normative_language_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv004Gate::test_two_sections_only_flags_the_underspecified_one` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv004Gate::test_missing_docs_dir_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv004Gate::test_markdown_waive_marker_with_reason_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv004Gate::test_claim_without_verb_in_sentence_is_silent` (pytest node id, verified passing when recorded)
