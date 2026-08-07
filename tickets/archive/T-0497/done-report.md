## Done report

Worked the 5 findings one at a time, counterexample-first, per the ticket's own
instruction. Two landed as real fixes (own commits each); three were split out
to individual tickets rather than rushed, an honest outcome the ticket itself
sanctions over a half-verified engine change.

LANDED:

- G8 (THREAT005 KeyError risk): check_effect_completeness trusted
  binding.owner[effect.file] to always resolve, relying on an IMPLICIT
  cross-module invariant (extract_effects only walking non-FOREIGN owned
  files). Hardened to binding.owner.get(effect.file, FOREIGN), reusing the
  existing FOREIGN sentinel. Counterexample: monkeypatched extract_effects to
  yield an off-binding file and proved the join now returns a Violation
  instead of raising KeyError
  (tests/unit/strata/test_threat.py::TestCheckEffectCompleteness::test_effect_on_a_file_absent_from_owner_does_not_crash).

- G11 (LATENCY dead metric): _eval_bound_latency_or_size read flow.size even
  for a LATENCY claim -- Flow has no latency field at all, so a LATENCY bound
  could never do anything but REFUTE-as-missing, forever, indistinguishable
  from an ordinary failing check. Added StrataError.UnsupportedMetric and
  refuse LATENCY outright with it instead. Counterexample: a LATENCY bound
  against a REAL flow (not just an unknown target, which already failed
  closed) now returns the typed error instead of a masquerading REFUTED
  verdict
  (tests/unit/test_claims_and_store_batch6.py::TestBoundClaimEdgeCases::test_latency_on_a_real_flow_is_refused_not_silently_refuted).

SPLIT OUT (own tickets, finding text carried over verbatim plus what was
learned trying/scoping each):

- G6 (default view coverage) -> T-draft-f75e805c: architecturally entangled
  with _audit.py's default-view plumbing and sys_runner's caller; needs a
  real design decision (fold cwe-top-25 into a genuine default multi-view
  run vs. loudly disclose the narrower scope), not a quick patch.

- G9 (native-staleness mtime-only) -> T-draft-035b0ea9: needs a real content-
  digest scheme designed (what gets hashed, where the build-time digest is
  recorded) plus its own touch-defeats-mtime litmus counterexample; not
  something to rush.

- G10 (untested Rust kernels) -> T-draft-9adddf64: needs a pure-Python
  reference implementation of the native kernels designed and a property/
  differential test harness built around it; a real piece of new test
  infrastructure, not a quick patch.

- G12 (BenignCapability allowlist) -> T-draft-0088bcd5: ATTEMPTED and
  REVERTED inside this ticket. The obvious fix (reject any kind already
  catalogued in CWE_CATALOG union QUALITY_CATALOG) breaks a real, tested,
  load-bearing use case: client_storage IS catalogued under CWE_CATALOG but
  has NO QUALITY_CATALOG entry, so excusing it for the quality loop
  specifically is legitimate and already covered by
  test_repo_declared_excuse_resolves_threat002. A correct fix needs to reason
  per-family (which catalog an excuse is meant to apply against), not a flat
  allowlist -- caught this via the existing test suite (ran it against my
  first attempt, it broke a real passing test) rather than shipping it.
  Reverted via `git checkout -- src/frob/strata/_threat.py` before
  committing anything for G12.

Caveats:

- `frob check --ticket T-0497` shows 2 pre-existing FAILs unrelated to this
  ticket's own changes: gate:DOC (DOC003 on docs/commands/sys.md, an
  owasp-top-10 exhaustiveness claim -- actually the SAME underlying gap G6
  names, now tracked as T-draft-f75e805c) and gate:SCOPE (SCOPE001 flagging
  docs/design/registry/weaknesses.yaml as outside T-0497's scope -- that file
  belongs to T-0508, closed earlier in this same worktree/branch; the SCOPE
  gate diffs the whole branch against main, so a prior ticket's already-
  landed, already-verified change on the same branch shows up here too. Not
  a T-0497 regression.
- Full targeted suite: `uv run pytest tests/unit/strata -q` (all ~815) green
  after both landed fixes; `uv run pytest tests/unit/strata tests/unit/test_claims_and_store_batch6.py
  tests/test_registry_exhaustiveness.py -q` green.
- Mid-session, main advanced (T-0411 ticket-priority schema + a 63-ticket
  archive) and tickets.md conflicted on merge; resolved per
  agent-playbook.md#10b (restore main's ledger verbatim, re-apply this
  session's own ticket-CLI operations against the fresh ledger) rather than
  hand-splicing -- both T-0508 and T-0497's states were rebuilt through the
  CLI after the merge, not hand-edited.

### Changed
```
 docs/design/registry/weaknesses.yaml       |  40 +++++-----
 src/frob/strata/_claims.py                 |  11 ++-
 src/frob/strata/_errors.py                 |  10 +++
 src/frob/strata/_threat.py                 |  16 +++-
 tests/unit/strata/test_threat.py           |  31 ++++++++
 tests/unit/test_claims_and_store_batch6.py |  26 ++++++
 tickets.md                                 | 124 +++++++++++++++++++++++++++--
 7 files changed, 231 insertions(+), 27 deletions(-)
```

### Evidence
(no evidence recorded)
