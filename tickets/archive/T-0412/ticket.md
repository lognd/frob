---
id: T-0412
title: frob:debt vs frob:waive -- expiring debt that is collected + re-raised as error
  before release (143 debt-waivers hide today)
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/graph/
- src/frob/gates/
- frob.toml
- src/frob/app/app.py
- src/frob/app/debt_runner.py
- tests/test_gates.py
- docs/guides/extending/comment-dsl-directives.md
- tests/test_debt_runner.py
- docs/modules/gates.md
- src/frob/app/ack_runner.py
- src/frob/release/__init__.py
- tests/test_ack_worktree_lease.py
- tests/test_release_worktree_lease.py
- tickets-archive.md
- pyproject.toml
- .frob-release.json
- CHANGELOG.md
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/app.py
  reason: frob debt CLI subcommand wiring (app.py dispatch table + new debt_runner.py)
    and its test/doc surface; __main__.py/config.py already implicit via T-0446 feature-kind
    CLI-wiring-files rule
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/app/debt_runner.py
  reason: frob debt CLI subcommand wiring (app.py dispatch table + new debt_runner.py)
    and its test/doc surface; __main__.py/config.py already implicit via T-0446 feature-kind
    CLI-wiring-files rule
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_gates.py
  reason: frob debt CLI subcommand wiring (app.py dispatch table + new debt_runner.py)
    and its test/doc surface; __main__.py/config.py already implicit via T-0446 feature-kind
    CLI-wiring-files rule
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/guides/extending/comment-dsl-directives.md
  reason: frob debt CLI subcommand wiring (app.py dispatch table + new debt_runner.py)
    and its test/doc surface; __main__.py/config.py already implicit via T-0446 feature-kind
    CLI-wiring-files rule
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_debt_runner.py
  reason: new CLI test file for frob debt (src/frob/app/debt_runner.py)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/gates.md
  reason: DEBT001-003 + debt_gate/list_debt frob:doc anchors
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/app/ack_runner.py
  reason: 'sequential single-worktree dispatch: T-0507/T-0456''s committed files still
    show in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0412''s own REL001 bump (new public frob:debt gate API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/release/__init__.py
  reason: 'sequential single-worktree dispatch: T-0507/T-0456''s committed files still
    show in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0412''s own REL001 bump (new public frob:debt gate API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_ack_worktree_lease.py
  reason: 'sequential single-worktree dispatch: T-0507/T-0456''s committed files still
    show in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0412''s own REL001 bump (new public frob:debt gate API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_release_worktree_lease.py
  reason: 'sequential single-worktree dispatch: T-0507/T-0456''s committed files still
    show in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0412''s own REL001 bump (new public frob:debt gate API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tickets-archive.md
  reason: 'sequential single-worktree dispatch: T-0507/T-0456''s committed files still
    show in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0412''s own REL001 bump (new public frob:debt gate API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: 'sequential single-worktree dispatch: T-0507/T-0456''s committed files still
    show in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0412''s own REL001 bump (new public frob:debt gate API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: 'sequential single-worktree dispatch: T-0507/T-0456''s committed files still
    show in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0412''s own REL001 bump (new public frob:debt gate API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: 'sequential single-worktree dispatch: T-0507/T-0456''s committed files still
    show in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0412''s own REL001 bump (new public frob:debt gate API)'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: 'sequential single-worktree dispatch: T-0507/T-0456''s committed files still
    show in the diff-vs-main SCOPE001 check (T-0431 precedent); pyproject/.frob-release.json/CHANGELOG.md/uv.lock
    for T-0412''s own REL001 bump (new public frob:debt gate API)'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestDebtGate::test_debt001_malformed_directive_is_reported
- tests/test_gates.py::TestDebtGate::test_debt002_closed_ticket_is_reported
- tests/test_gates.py::TestDebtGate::test_debt002_open_ticket_is_silent
- tests/test_gates.py::TestDebtGate::test_debt003_expired_by_date_is_reported
- tests/test_gates.py::TestDebtGate::test_debt003_not_yet_expired_is_silent
- tests/test_gates.py::TestDebtGate::test_debt003_expired_by_version_is_reported
- tests/test_gates.py::TestDebtGate::test_clean_debt_produces_no_violations
- tests/test_gates.py::TestDebtGate::test_lists_every_debt_entry
- tests/test_gates.py::TestDebtGate::test_release_gate_fails_while_debt_is_open
- tests/test_debt_runner.py::TestDebtRunner::test_json_mode_lists_debt_entries
- tests/test_debt_runner.py::TestDebtRunner::test_no_debt_logs_clean_message
- tests/test_debt_runner.py::TestDebtRunner::test_human_mode_reports_expired_flag
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
User directive (2026-07-20): distinguish PERMANENT waivers from EXPIRING debt. Today frob:waive is the only mechanism and 143 of 569 waivers (25%) are debt-shaped -- their reason literally says "debt T-0160" (e.g. frob:waive TEST005 reason="visit_Constant 75.0% branch cover, debt T-0160"). Debt is masquerading as a permanent, forever-acceptable exception, so it will NEVER be collected. There is no frob:debt directive, no debt tracking, and the release gate does not check for outstanding debt.

DESIGN: two distinct directives with distinct semantics. (1) frob:waive <RULE> reason="..." = PERMANENT, genuine forever-exception (the sort runs once not in a loop; this env-read is scan-pattern data). Stays. (2) frob:debt <RULE> reason="..." ticket=T-#### [until=<version|date|"next-release">] = TEMPORARY accepted gap, TRACKED as owed, BOUND to a ticket (required -- the debt must have a home), with an optional expiry. Semantics: a debt suppresses the finding NOW (like a waive) BUT is recorded as outstanding debt; it ESCALATES to an ERROR when its until boundary passes (a date/version), and -- the key requirement -- the RELEASE GATE (REL) BLOCKS a release while ANY debt is open (or any debt whose until <= the release being cut), so all debt is collected + re-raised + resolved before shipping. A debt with no ticket, or a ticket that is closed/nonexistent, is itself an error (anti-lie: a debt must point at real, open, owed work).

TOOLING: frob debt (list all outstanding debt: rule, site, ticket, until, age); a DEBT gate that escalates expired debt to error; the release stamp/check path fails on open debt. MIGRATE: the 143 debt-shaped frob:waive directives become frob:debt <RULE> ... ticket=T-0160 (or their real owner ticket), so the T-0160 coverage debt is properly tracked as owed and collected before the 1.0.0 release, not silently permanent. Ships per-project (T-0406). Acceptance: a frob:debt with a closed/missing ticket errors; an expired frob:debt errors; frob release check FAILS while debt is open; frob debt reports the full outstanding set honestly; the 143 existing debt-waivers are migrated and now show as tracked debt, not permanent waivers. This is the waive-vs-debt distinction: a permanent exception is fine; owed work must never look resolved (same class as the whole audit).

DEBT<->TODO COHERENCE (user, 2026-07-20): frob:debt and frob:todo must work together, not as two parallel systems. A frob:debt suppresses a GATE FINDING (the symptom); a frob:todo tracks DEFERRED WORK (already open-ticket-enforced today via TODO001 _todo001_edges, which fires on a frob:todo bound to a non-open/missing ticket). A debt without visible payoff-work is a silent suppression. REQUIREMENTS: (1) a frob:debt at a site must be accompanied by a frob:todo for the SAME ticket -- either require the paired frob:todo directive, OR have frob:debt implicitly REGISTER a todo so the debt payoff appears in the deferred-work queue (frob todo / doable); pick the cleaner of the two but the debt work MUST be visible as a todo, not only as a gate suppression. (2) BOTH frob:debt and frob:todo require an OPEN ticket -- reuse TODO001s existing open-ticket check for debt too (a debt or todo pointing at a closed/nonexistent ticket errors). (3) CONSISTENCY: a frob:debt and its co-located frob:todo must name the SAME ticket -- if they disagree, error (no debt tracked under one ticket while its todo points at another). (4) SYMMETRY at resolution: closing the ticket should surface BOTH the debt (a gate finding to unsuppress + re-verify) and the todo (work to confirm done) so neither is silently orphaned when the other resolves. Acceptance: a frob:debt with no accompanying/implied frob:todo fails (or auto-registers one, per the chosen design); a frob:debt + frob:todo naming different tickets fails; a debt/todo on a closed ticket fails; frob todo and frob debt cross-reference the same open ticket.