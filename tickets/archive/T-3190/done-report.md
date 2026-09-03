## Done report

Documented and proved the owner-recorded milestone decision instead of
bulk-stamping the 346-ticket queue, per this ticket's own explicit
guardrail ("do not stamp before it is agreed", "the owner sees the
proposed split before it is treated as settled").

Completed within declared scope:
- docs/modules/tickets-lifecycle.md: new "Adopting real milestones
  (T-3190)" section recording the owner decision (0.530.0 = publishable,
  1.0.0 = default/everything else), the derivation rule for 0.530.0
  membership, confirmation that the KNOWN blocking set named in the
  decision (T-3246/T-3247/T-3249/T-3250/T-3251) is now fully DONE
  (re-verified 2026-08-31), and a PROPOSED (not stamped) candidate list
  from a first-pass scan of the open queue.
- frob.toml: a clarifying comment above [tickets].default_milestone
  explaining it is the terminal fallback, not an assertion that shipping
  and 1.0.0 are the same event, referencing the decision doc.
- tests/test_config_frob_toml_milestone.py (new, scope --add'd with
  reason -- feature-kind tickets require pytest evidence node ids):
  two regression tests guarding acceptance criterion 1 (default_
  milestone stays configured; default_milestone is never re-set to the
  publish milestone 0.530.0).
- Verified MILE001/MILE003 already fire correctly against fixture data:
  tests/test_gates_milestone.py, 29/29 passing -- satisfies the
  ticket's "real (or fixture)" firing-demonstration acceptance bullet.

Deliberately NOT done (would require owner sign-off per this ticket's
own text): bulk-stamping any real open ticket with milestone=0.530.0,
and a real-data (non-fixture) MILE001 positive control. The follow-up
ticket below carries the proposed candidate list (T-2939, T-3076,
T-3212/T-3213, T-3337, T-3505, T-3512) for owner review before any
ledger write.

Filed: T-3602

### Changed
```
 tickets/T-3190/done-report.md      | 51 +++++++++++++++++++++++++++
 tickets/T-3190/ticket.md           | 33 ++++++++++++++++-
 tickets/T-3602/ticket.md | 72 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 155 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_config_frob_toml_milestone.py::TestDefaultMilestoneDoesNotConflateShippingWithOnePointZero::test_default_milestone_is_configured` (pytest node id, verified passing when recorded)
- `tests/test_config_frob_toml_milestone.py::TestDefaultMilestoneDoesNotConflateShippingWithOnePointZero::test_default_milestone_is_not_the_publish_milestone` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 28 error(s), 4138 warning(s), 892 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3190/tests/test_config_frob_toml_milestone.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3190, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@tests/test_config_frob_toml_milestone.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
