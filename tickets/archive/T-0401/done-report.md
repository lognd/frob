## Done report

Resumed an orphaned T-0401 in-progress session. Re-audited docs/audits/strata.md
G1-G12 against the CURRENT tree (not the audit's original snapshot) and found
most of the ticket's mandate already landed by prior sessions on main:

- G3 (eval globally BenignCapability-excused): CLOSED. CWE-94 now joins the
  "eval" capability_kind (in addition to "exec"), eval is no longer in
  DEFAULT_BENIGN_CAPABILITIES; a `may "eval"` node with no mitigation now
  fires a real, dischargeable THREAT003 obligation. Verified via the three
  evidence tests already recorded on this ticket, re-run and confirmed green.
- G4 (FOREIGN file escapes all SYS rules): CLOSED (T-0500, merged). SYS102
  now fires per-FOREIGN-file within an already-owned directory, not just per
  fully-foreign top-level directory, and a loose top-level file is caught too.
- G5 (utility/krb_no_transit flow marker defeats confidentiality noflow):
  CLOSED (separate landed ticket, archived).
- G1 (boundary predicates never bound to code): PARTIALLY closed (T-0498,
  merged). `_matching_boundary_ids` now requires the boundary's `obligations`
  to resolve to a real in-model `Claim.id` (`_obligations_resolve`) -- a bare
  self-declared predicate string with no evidence ref no longer discharges.
  The STRONGER half of G1 -- binding the predicate to an OBSERVED sanitizer
  call site in code, not merely an in-model claim -- remains open. T-0498's
  Done report claimed this was filed as a follow-up ("a never-materialized draft (T-0595 is the real replacement)"), but
  that id was never resolved into a real ticket (confirmed absent from both
  tickets.md and tickets-archive.md -- a draft id minted off-default-branch
  that was never landed). Filed a real replacement ticket during this pass:
  T-0595 (ex-draft, id lost at land) (id resolves to a real T-#### at land), scoped to
  _threat.py/_selfconform.py/_code_binding.py/_effects.py, parent T-0401.
- G2/G7 (vacuous NoFlow discharge: foreign->sink flow un-modeled, or no
  foreign-trust node at all): NOT touched here. This is explicitly T-0501's
  scope (already filed, queued, from a prior T-0401 pass) -- per dispatch
  instructions, left untouched so as not to collide with that ticket. No
  flow-completeness work was done in this pass, so T-0501's finding is NOT
  subsumed; it remains the right home for G2/G7.
- G6/G9/G10/G12: already split into their own tickets by a prior session
  (T-0497's Done report: G8/G11 landed directly, G6/G9/G10/G12 split out
  because each needed a scope/budget too large for that ticket). Confirmed
  G12 (repo-declared benign-capability family scoping) is landed in
  _threat.py (`BenignCapability.family`, `_family_catalog_for`,
  `load_repo_benign_capabilities` validation).

No source changes were needed in this pass beyond re-verifying the prior
landed work and correcting the dangling follow-up-ticket reference -- the
ticket's own mandate items (1) boundary-binding, (3) eval obligation, and
(4) FOREIGN-file SYS coverage are closed (G1 partially, by design pending
the new follow-up ticket); item (2) flow-completeness is intentionally left
to T-0501 as instructed.

frob check --ticket T-0401: 0 errors (370 warnings, 187 waived), clean.
uv run pytest tests/unit/strata/test_threat.py: 116 passed.

### Changed
```
 tickets.md | 137 +++++++++++++++++++++++++++++++++----------------------------
 1 file changed, 74 insertions(+), 63 deletions(-)
```

### Evidence
- `tests/unit/strata/test_threat.py::TestEvalFiresCwe94::test_eval_capability_is_classified_not_benign_excused` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestEvalFiresCwe94::test_eval_capability_fires_a_real_cwe94_obligation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestEvalFiresCwe94::test_eval_capability_discharges_with_a_real_mitigation_claim` (pytest node id, verified passing when recorded)
