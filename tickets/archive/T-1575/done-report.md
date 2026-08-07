## Done report

T-1575: Development profiles (frob.toml [profile]).

Changed:
- src/frob/tickets/_profile.py (new): ProfileName (rapid/standard/
  fortress), ProfileError, configured_profile (raw frob.toml read,
  standard default), effective_profile (the one-way auto-ratchet: three
  live thresholds -- repo file count 300, ticket count 200, concurrent
  lease count 5, any one trips -- persisted to
  .frob/profile-ratchet.json), downgrade_profile_ratchet (explicit,
  loudly-logged clear).
- src/frob/tickets/_land.py::_check_mutation_evidence: rapid profile
  skips TEST016 entirely (both the T-1518 synchronous security-kind
  mutation subprocess and the deferred batch-sweep enqueue); BUG002
  unaffected, still runs/blocks for bug/security kind under every
  profile.
- src/frob/app/ticket_runner/_land_cmd.py::_land: passes
  pre_commit_sweep=None to land() when the effective profile is rapid --
  only the existing single post-land revert-on-red sweep runs.
- docs/modules/tickets.md: new "Development profiles" section.
- tests/unit/test_profile.py (new): 9 unit tests covering
  configured_profile, effective_profile's ratchet trip/persist/no-
  re-trip-downward behavior, and downgrade_profile_ratchet.

Evidence: 9 pytest node ids bound via the ticket evidence CLI, all
observed passing (9 passed) under a targeted pytest run of the new test
module; also re-ran tests/unit/test_ticket_close_bug002_t1427.py (2
passed) to confirm the BUG002/mutation-evidence land path this ticket
touches is unaffected for the non-rapid (standard) case.

Gates: a repo-wide (not --ticket-scoped) run of invariant/prework/wire/
test/coverage stage groups shows zero unwaived findings against any file
this ticket touched -- the two new findings (INV006 module-docstring
exclusivity language, WIRE001 downgrade_profile_ratchet having no
caller) are both waived with stated reasons, the WIRE001 waiver's
follow_up bound to a real filed draft ticket. Remaining unwaived findings
in that run are pre-existing COV006/COV007 on files this ticket did not
change.

Disclosed cuts (both filed as draft follow-up tickets, real ids after
<!-- frob:waive DOC006 reason="historical Done report: this discloses 'frob profile' as a not-yet-built follow-up CLI surface, matching the doc's own 'not implemented here' language" -->
land):
1. No CLI surface for `downgrade_profile_ratchet` yet (no `frob profile`
   subcommand) -- T-1575's own scope did not include
   src/frob/_cli_parsers/**/src/frob/app/app.py's dispatch wiring, and
   adding a new top-level command group safely (registration, help text,
   a matching runner module) was judged too much for this same pass.
   Follow-up: the draft ticket filed above for "Wire frob profile CLI
   (show/downgrade)".
2. Three remaining rapid semantics from the ticket body are NOT wired:
   evidence/done-report leniency for kind=docs/chore, REL001 off under
   rapid, and a fully baseline-thread-free rapid land (today rapid still
   runs the T-1463 baseline-capture thread, since _land_cmd.py's
   post-land sweep reads the SAME thread/result the pre-commit sweep
   used to -- disentangling them safely needs its own dedicated
   regression coverage I judged out of scope for this pass, rather than
   risk a land-pipeline regression). Follow-up: the second draft ticket
   filed above ("rapid profile: evidence/done-report leniency for
   docs/chore, REL001 off, baseline-thread-free land").
3. `fortress` ships as an enum member only, per the ticket's own
   "placeholder wiring only" instruction -- no behavioral wiring, by
   design, not a cut.

Filed: two draft tickets (real ids assigned at land) -- CLI wiring for
frob profile show/downgrade; remaining rapid semantics (evidence
leniency, REL001, baseline-thread-free).

### Changed
```
 docs/modules/tickets.md                    | 136 +++++++++-
 src/frob/_cli_parsers/_ticket/_progress.py |  18 ++
 src/frob/app/_config_external.py           |   2 +
 src/frob/app/config.py                     |   6 +
 src/frob/app/ticket_runner/_land_cmd.py    |  78 +++++-
 src/frob/tickets/_land.py                  | 101 ++++++--
 src/frob/tickets/_mutation_sweep_queue.py  | 399 +++++++++++++++++++++++++++++
 src/frob/tickets/_profile.py               | 354 +++++++++++++++++++++++++
 tests/unit/test_mutation_sweep_queue.py    | 179 +++++++++++++
 tests/unit/test_profile.py                 | 123 +++++++++
 tickets.md                                 | 232 ++++++++++++++++-
 11 files changed, 1590 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/unit/test_profile.py::TestConfiguredProfile::test_absent_frob_toml_is_standard` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile.py::TestConfiguredProfile::test_explicit_rapid_parses` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile.py::TestConfiguredProfile::test_unknown_value_errors` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile.py::TestEffectiveProfile::test_standard_is_unaffected_by_ratchet` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile.py::TestEffectiveProfile::test_rapid_below_threshold_stays_rapid` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile.py::TestEffectiveProfile::test_rapid_above_threshold_ratchets_to_standard` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile.py::TestEffectiveProfile::test_persisted_ratchet_wins_even_if_thresholds_no_longer_trip` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile.py::TestDowngrade::test_downgrade_clears_persisted_ratchet` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile.py::TestDowngrade::test_downgrade_is_noop_when_nothing_ratcheted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 0 error(s), 6998 warning(s), 787 waived
- error-findings: none (measured, zero errors)
