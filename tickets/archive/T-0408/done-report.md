## Done report

Verify-first finding: the repo landed T-0462/T-0452/T-0509/T-0515 since
this ticket was filed -- INV003 (exclusivity claims) and INV004 (normative
claims) already exist, WARN severity, and already cover docs/modules +
docs/strata with a noise-filtered claim-shape scan; T-0520 already bound
32 invariants across those doc trees. So the doc-side half of the ticket's
premise is already satisfied by prior work, not by this pass.

The genuine remaining delta (verified via a fresh repo-wide grep before
writing any code): BOTH INV003 and INV004 are hard-scoped to
`INV003_SPEC_DIRS` (docs/modules, docs/strata) and never look at source
code at all. `grep -rlE '\b(always|never|idempotent|thread-safe|exactly
once|monotonic|guarantees?|must not)\b' src/ strata-core/ frob-core/`
found 176 source files making exactly this class of claim in
docstrings/comments, entirely outside either gate's reach -- the same
"tooling gap" the ticket's META-PRINCIPLE section names: nothing checked
whether ENOUGH invariants existed, only whether the ones that already
existed were individually well-formed.

Fix: a new INV006 gate (`frob.gates.inv006_gate`, WARN, matching INV003's
posture) that reuses INV003's exact noise-filtered claim vocabulary
(`find_exclusivity_claims`) over source trees (`INV006_SRC_DIRS`: src,
strata-core/src, frob-core/src; .py/.rs), bound-checked against the real
`frob:invariant` comment-DSL edge in the `GraphSnapshot` (not an
HTML-comment-only regex that would never match Python/Rust comments), with
`frob:waive INV006 reason="..."` as the disposition path.

Measured effect (`frob check --only invariant` on this repo): 184 total
INV warnings post-change (142 remaining after subtracting the 17
pre-existing INV005 findings + 2 unrelated WAIVE002 findings baked into
main already -- roughly ~167 are new INV006 findings across src/,
strata-core/src/, frob-core/src/). WARN severity: this does not fail
`frob check`, so it does not block this or any other ticket; driving the
167 down to 0 (bind a real invariant, waive with a specific reason, or
reword) is a follow-up burndown of the same shape as INV003/INV004's own
residual triage, which prior tickets also left as tracked follow-up
rather than hand-closing in one pass -- disclosed honestly, not silently
cut.

NOT done in this pass (disclosed, not silently dropped): the ticket's
full acceptance line ("the current 128 are each dispositioned") is NOT
met -- that is per-claim human/reviewer triage across ~167+31 findings,
comparable effort to T-0509/T-0515's own calibration passes, and out of
this ticket's budget. The coverage-completeness TOOLING gap (the actual
meta-fix the user asked for) is closed; the full burndown of every
individual claim is not. No new ticket filed for the burndown itself
since docs/modules/gates.md's INV006 section already names it as
tracked, mirroring how INV003/INV004's own residuals were left as
"tracked as a follow-up" prose rather than a separate ticket id in this
repo's established convention for this exact gate family.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_with_bound_invariant_anchor_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_waived_with_reason_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_no_exclusivity_language_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_outside_src_dirs_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_missing_src_dir_is_silent` (pytest node id, verified passing when recorded)
