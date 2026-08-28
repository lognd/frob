## Done report

Changed:
  src/frob/gates/_comment_placement.py (new)
  tests/gates/test_comment_placement.py (new)
  docs/guides/agent-playbook.md (new sec 7b)
  docs/modules/gates.md (rule-catalog rows + enumerates member list)
  src/frob/gates/__init__.py (wiring: import, _ALL_GATES, GATE_RUNNERS, __all__)
  src/frob/gates/_waive.py (_KNOWN_GATE_RULES: CPLACE001, CPLACE002)

GATE DESIGN: two new rules, CPLACE001 (src/**/*.py: a frob:waive
directive's reason prose over 2 physical lines -- T-2987's own proposed
cap, adopted verbatim) and CPLACE002 (docs/modules/**/*.md: a ticket-id
prose paragraph outside a markdown table row, over 15 words). Both WARN,
not ERROR (T-2372/TICK011 ladder), both provenance-exempt on
changelog.d/, CHANGELOG.md, docs/decisions/, tickets/**.

NARR001 (T-2993/T-3014) ALREADY EXISTS and already covers the
"# T-####:"-led comment-block-length half of T-3218's BUILD item 1 -- it
is NOT duplicated here. What NARR001 does not cover, and what T-2987's
own finding (the blanket frob:-exemption is too broad for frob:waive)
plus the docs/modules placement rule (BUILD item 2) both required, is
what CPLACE001/CPLACE002 add. CPLACE001 does not match a
"# T-####:"-led block at all; it matches only a `frob:waive` directive
start on the FOLDED logical line (via frob.graph.dsl.fold_comment_runs,
the same physical-line-count primitive frob fmt/T-0441 canonicalizes
with) -- never a raw substring search, per the house-rule regression this
module's docstring and
test_does_not_fire_on_prose_mentioning_frobwaive_by_name both guard
against.

EXEMPTION FIXTURES (tests/gates/test_comment_placement.py):
  - test_must_stay_quiet_exempt_path (x2, one per rule) -- changelog/
    decisions/tickets paths never fire.
  - test_must_stay_quiet_frob_ticket_directive_any_length -- frob:ticket
    stays exempt at any length; CPLACE001 only matches frob:waive.
  - test_must_stay_quiet_ordinary_one_line_waive -- the specific
    must-stay-quiet fixture the ticket named: a compliant one-line
    frob:waive reason="..." never fires.
  - test_must_stay_quiet_short_attribution -- a short "See T-1234 for
    why" attribution stays under CPLACE002's word limit.
  - test_must_stay_quiet_table_row_citation -- a bare (T-1234) citation
    inside a markdown table row (provenance) never fires.
  - test_must_fire_long_waive_reason / test_must_fire_long_narrative_paragraph
    -- one must-fire per rule.
  - test_does_not_fire_on_prose_mentioning_frobwaive_by_name -- the
    house-rule regression (raw substring vs structured-directive match).
  - test_threshold_boundary_is_inclusive / test_word_limit_boundary --
    boundary fixtures for both thresholds.
12 tests total, all green.

MIGRATION: per T-3218's own explicit text ("MIGRATION IS NOT THIS
TICKET'S JOB... T-2987/T-2988/T-3022 already own the respective
migrations"), NO migration was performed under this ticket -- this
overrides the dispatch brief's general "migration is part of the work"
guidance, since the ticket's own reconciled text is the more specific
and more recently written instruction and explicitly forbids it here.

BEFORE/AFTER, measured via comment_placement_gate(Path('.')) at land
time: CPLACE001 863 findings, CPLACE002 1163 findings, 2026 total --
this IS the "before" count since no migration ran under this ticket
(matches T-3218's own explicit "no migration" instruction; T-2987/T-3022
own draining it). This confirms gate-build found the migration tickets
have NOT landed enough to avoid a noisy WARN flood: 2026 day-one
findings, comparable magnitude to NARR001's own 1728-block baseline.
Per BUILD item 1's own ladder guidance ("start at WARN if burn-down is
not immediately achievable... state which was chosen and why"), both
rules ship at WARN. SAFE TO SHIP AHEAD of T-2987/T-2988/T-3022: WARN
findings do not fail `frob check` (confirmed: `gate:CPLACE` reports
"pass ... 2026 warnings" in the full-repo run), so shipping the gate now
does not block anything; promoting to ERROR must wait behind those three
migrations landing enough to burn the count down, same as NARR001's own
stated ladder.

Filed: none -- no new out-of-scope tickets needed; T-2987/T-2988/T-3022
already own the migration this gate's findings feed.

Evidence: 12 pytest node ids recorded (tests/gates/test_comment_placement.py,
all classes), plus tests/test_narrative_blocks.py (17 total) confirmed
still green.

Gates: `frob check --ticket T-3218 --only scope` clean (0 errors after
extending scope to docs/modules/gates.md and src/frob/gates/__init__.py,
the two wiring/catalog files this ticket's own gate-registration
required). `frob check --ticket T-3218 --only prework` clean (0 errors
for gate:PRE/gate:SCOPE after `frob ticket sweep T-3218`; the remaining
gate:DRIFT (53) and gate:WAIVE (1) failures in that run are repo-wide
pre-existing baseline, unrelated to this diff -- confirmed absent from
main before this change and containing zero references to
_comment_placement.py or test_comment_placement.py). `frob test --base
main` touched-set run surfaced one unrelated pre-existing failure
(TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known, missing
TDD001/VMOD001/VERSION001 -- confirmed absent from CPLACE001/CPLACE002,
and confirmed the same three ids are already missing on main before this
change).
