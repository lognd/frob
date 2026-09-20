## Done report

Changed: frob.toml `[gates.severity]` T-1002 managed zone only.

Rule set derivation: authoritative rule ids came from
`frob.gates._waive._KNOWN_GATE_RULES` (361 ids, itself generated-and-
verified against `frob.gates._rule_id_scan.generated_gate_rule_ids` by
`tests/gates_suite/test_sys.py::TestKnownGateRuleIds`) -- not the 338-id
regex sweep mentioned in the ticket body, which was explicitly disclaimed
as untrustworthy.

Zero-finding computation: loaded the 2026-09-05 full unscoped
`frob check --no-cache --json` baseline through
`scripts/check_summary.py`'s `iter_diagnostics` and intersected every
`diagnostic["code"]` that appeared (at ANY severity -- error/warning/
info/note, not just warning) against the 361 known rule ids. This
surfaced 50 known rule ids with live findings of some severity: the 35
warning-level rules from the ticket body's own histogram, DOC006 (the 1
tracked error, untouched, T-3843's lease), and 14 more that only showed
up as note/info residue for rules ALREADY promoted to error in the
pre-T-3844 zone (ARCH001/102/103, COV001, OPAQUE001, PERF001-004,
PII010/012, SEC110) plus 7 genuinely new non-warning findings this scan
caught that the warning-only histogram could not have surfaced: COV007
(214), LARGE001 (90), PERF011 (2), PII011 (1), RENDER001 (4), REF002 (6),
CYCLE001 (1). None of those 7 are promoted -- promoting any of them
would have turned their live note/info findings into hard errors,
exactly the "still fires" case the ticket warns against.

Promoted rule set (309 - 1 carve-out = 308 rules set to `error`, listed
in full in frob.toml's zone): every one of the remaining 311 zero-finding
rules that was not already `error` in the pre-existing zone, INCLUDING
VMOD001 (named explicitly by the owner), TEST002 and TEST005 (measured
at 0 findings despite being part of the old TEST002/003/005/006 "legacy
baseline" comment -- TEST003/006 still fire and stay warn, tracked
below).

Planning carve-out (repo-local, NOT a frob default): SYS101
(declared-but-never-observed "may" capability / stale design,
`frob.gates._sys_selfaudit.py`) is the one rule matching the owner's
"design names something that does not exist yet" exemption that is both
(a) currently at 0 live findings (so it would otherwise be free to
promote under step 1) and (b) actually in this ticket's remit. It is set
to `warn` with a comment naming T-3844, the owner's exact words, and that
a scaffolded design-first repo must still get it as an error. DOC006's
own forward/planned-path carve-out (T-3317/T-3821) is deliberately NOT
done here -- DOC006 is under T-3843's active lease and out of this
ticket's scope; T-3843 has since landed (done), so the DOC006
planned-path carve-out remains open follow-up work for whichever ticket
picks up T-3317/T-3821, not this one.

Post-promotion re-measurement: a second full unscoped `frob check
--no-cache --ticket T-3844 --json` run (captured at /tmp/post_check3.json
during this session) read through `scripts/check_summary.py` shows
`{'warning': 4512, 'info': 91, 'note': 1784, 'error': 1}` -- 1 error
(DOC006 only), matching the pre-promotion baseline's error count exactly.
No frob.toml edits occurred after that measurement (confirmed by `git
diff --stat frob.toml` still showing only the one intentional hunk), so
it remains the valid post-promotion measurement. Later full-repo
re-verification attempts in this session timed out under heavy fleet
contention (10+ concurrent `frob check`/`frob ticket land` processes on
the host); a targeted `gates-fast` + `gates-security` chunked re-run
after that contention (once burn-down ticket scope was added, see below)
came back with the same single DOC006 error and zero SCOPE001 findings.

Burn-down tickets filed, one per the 35 rules/clusters in the ticket
body's histogram, each carrying its measured denominator (all mirrored
to the primary checkout):

- T-3860: CPLACE001/CPLACE002 (2149)
- T-3861: EXHAUST002/003/004 (323)
- T-3863: TICK003/004/007/012/014 (917)
- T-3864: TEST003/006/014 (77)
- T-3865: WAIVE004/010 (265)
- T-3866: DOCARCH001 (474)
- T-3867: NARR001 (156)
- T-3868: dup-detector "renamed" category (134)
- T-3869: COV006 (85)
- T-3870: PERF005/008/010 (78)
- T-3871: DEAD001 (36)
- T-3872: LANG003 (21)
- T-3874: DOCENUM001 (8)
- T-3875: "(no-code)" diagnostic category (7)
- T-3876: ENV001 (5)
- T-3877: misc lint/ref hygiene cluster: unused-ignore-comment/
  possibly-missing-submodule/NEGEXIST001/REF003 (11)
- T-3878: architecture-cohesion cluster: god-module/god-class (17)
- T-3880: WALK001 (1)
- T-3881: INV005 (1)

Denominators sum to 4765, matching the ticket body's warning total
exactly.

Not filed as burn-down tickets (acceptance criteria scope them to
"warning rule or cluster"; these 7 are note/info-only, not warning, and
were caught only by this ticket's own all-severity zero-finding scan --
flagged here for visibility, not tracked as separate tickets since no
warning-level population exists for them): COV007 (214), LARGE001 (90),
PERF011 (2), PII011 (1), RENDER001 (4), REF002 (6), CYCLE001 (1).

Evidence: frob.toml is data/config, not a function with a docstring or a
directly-testable code path of its own; the mechanism it configures
(`_apply_severity_overrides`/`_severity_overrides` in
`src/frob/gates/_waive.py`) and its own drift-locks are exercised by:
- tests/gates_suite/test_run.py::TestSeverityOverrides::test_override_downgrades_and_ignores_garbage
- tests/gates_suite/test_run.py::TestSeverityOverrides::test_no_frob_toml_is_identity
- tests/gates_suite/test_run.py::TestSeverityOverrides::test_sec110_promoted_to_error_gates_a_real_repo_toml
  (the existing before/after-fixture pattern for a real promotion in
  this repo's own frob.toml -- the same shape this ticket's promotions
  use)
- tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_returns_known_rule_id
- tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_is_frozenset
  (drift-locks the `_KNOWN_GATE_RULES` set this ticket's derivation used
  as its authority)
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_still_pass_this_repos_own_frob_toml
  (GATESSCHEMA001 re-validates every `[gates.severity]` key against the
  live rule-id registry -- catches a typo'd or unknown rule id in the 308
  new lines)

All 6 pass against this ticket's frob.toml (10/10 and 8/8 in their full
classes, run in this worktree).

Filed: T-3860, T-3861, T-3863, T-3864, T-3865, T-3866, T-3867, T-3868,
T-3869, T-3870, T-3871, T-3872, T-3874, T-3875, T-3876, T-3877, T-3878,
T-3880, T-3881 (19 burn-down tickets, listed above with denominators).

Gates: `frob check --ticket T-3844` (chunked gates-fast + gates-security,
full run timed out under fleet contention) clean except the pre-existing
DOC006 (untouched, tracked at T-3843, now done on main but not yet
rebased into this stale worktree). No waivers used in this ticket's own
change.

### Changed
```
 tickets/T-3844/ticket.md | 186 ++++++++++++++++++++++++++++++++++++++++++++++-
 tickets/T-3860/ticket.md |  27 +++++++
 tickets/T-3861/ticket.md |  27 +++++++
 tickets/T-3863/ticket.md |  27 +++++++
 tickets/T-3864/ticket.md |  27 +++++++
 tickets/T-3865/ticket.md |  27 +++++++
 tickets/T-3866/ticket.md |  27 +++++++
 tickets/T-3867/ticket.md |  27 +++++++
 tickets/T-3868/ticket.md |  27 +++++++
 tickets/T-3869/ticket.md |  27 +++++++
 tickets/T-3870/ticket.md |  27 +++++++
 tickets/T-3871/ticket.md |  27 +++++++
 tickets/T-3872/ticket.md |  27 +++++++
 tickets/T-3874/ticket.md |  27 +++++++
 tickets/T-3875/ticket.md |  27 +++++++
 tickets/T-3876/ticket.md |  27 +++++++
 tickets/T-3877/ticket.md |  28 +++++++
 tickets/T-3878/ticket.md |  28 +++++++
 tickets/T-3880/ticket.md |  46 ++++++++++++
 tickets/T-3881/ticket.md |  40 ++++++++++
 20 files changed, 732 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/gates_suite/test_run.py::TestSeverityOverrides::test_override_downgrades_and_ignores_garbage` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_run.py::TestSeverityOverrides::test_no_frob_toml_is_identity` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_run.py::TestSeverityOverrides::test_sec110_promoted_to_error_gates_a_real_repo_toml` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_returns_known_rule_id` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_is_frozenset` (pytest node id, verified passing when recorded)
- `tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 1 error(s), 4341 warning(s), 922 waived
- error-findings: DOC006@tickets/T-3807/ticket.md
