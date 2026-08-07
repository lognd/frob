---
id: T-1763
title: 'INV006/AFFECT001/DUP001 have a 100% waive rate: 406 waivers, zero findings
  -- make them symbolic or delete them'
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_inv.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/test_waive_gate.py
- src/frob/gates/_inv006_split_assist.py
- src/frob/gates/invariants.py
- src/frob/gates/_fix_engine_tier_c.py
- tests/test_gates_fix_engine.py
- src/**
- strata-core/src/**
- frob-core/src/**
- tests/**
- docs/**
- design/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_inv006_split_assist.py
  reason: corpus-wide INV006/AFFECT001/DUP001 measurement + INV006 deletion requires
    touching the gate's split-assist helper, its Tier-A auto-fix handler, and their
    tests -- the ticket's own 4-file scope did not name any of these
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/invariants.py
  reason: corpus-wide INV006/AFFECT001/DUP001 measurement + INV006 deletion requires
    touching the gate's split-assist helper, its Tier-A auto-fix handler, and their
    tests -- the ticket's own 4-file scope did not name any of these
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_fix_engine_tier_c.py
  reason: corpus-wide INV006/AFFECT001/DUP001 measurement + INV006 deletion requires
    touching the gate's split-assist helper, its Tier-A auto-fix handler, and their
    tests -- the ticket's own 4-file scope did not name any of these
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates_fix_engine.py
  reason: corpus-wide INV006/AFFECT001/DUP001 measurement + INV006 deletion requires
    touching the gate's split-assist helper, its Tier-A auto-fix handler, and their
    tests -- the ticket's own 4-file scope did not name any of these
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_waive_gate.py
  reason: corpus-wide INV006/AFFECT001/DUP001 measurement + INV006 deletion requires
    touching the gate's split-assist helper, its Tier-A auto-fix handler, and their
    tests -- the ticket's own 4-file scope did not name any of these
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: strata-core/src/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: frob-core/src/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_gates.py::TestTestGate::test_waive004_exempts_a_diff_scoped_rule
- tests/test_gates.py::TestFmt001Gate::test_directive_run_over_limit_flagged
- tests/test_gates.py::TestFmt001Gate::test_untouched_line_not_flagged
- tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
designated_repro_test: null
threat: null
component: null
---
Measured on frob's own source, 2026-08-07:

    RULE        WAIVED   LIVE   WAIVE-RATE
    INV006         338      0         100%
    AFFECT001       49      0         100%
    DUP001          19      0         100%

INV006 has **338 waiver directives and zero live findings**. It has never
produced an unwaived finding in this codebase. It is 34% of frob's entire
suppression corpus (997 waivers across 28 rules) and it enforces nothing.

Each of those 338 is a hand-written prose justification that a person had
to compose, a reviewer had to read, and that now has to be maintained
through every refactor. That is the cost. The benefit is zero findings.

WHY IT MISFIRES. INV006 flags "exclusivity/normative claims" -- the words
`never`, `only`, `always` -- appearing in docstrings and comments. But
those words appear constantly in ordinary descriptive prose about
implemented behaviour, which is exactly what a good docstring contains.
The waiver reasons say so, near-verbatim, 338 times: "describes this
module's own implemented branching, verifiable by reading the code it
annotates -- not a separate cross-module contract needing a tracked
invariant."

It is a LEXICAL rule standing in for a SEMANTIC question. The question it
wants to ask is "does this module make a cross-module contract that no
tracked invariant covers?" The question it actually asks is "does this
text contain the word 'never'?" Today it fired on a waiver reason
EXPLAINING a previous INV006 misfire (T-1640, landed), which is the rule
consuming its own output as input.

DECIDE, then implement. Two honest options, and the ticket wants a
reasoned choice, not a hedge:

(a) MAKE IT SYMBOLIC. Fire only where a normative claim is attached to a
    declared cross-module surface -- an exported symbol's contract, a
    `frob:invariant` anchor's subject -- and never on narrative prose
    about a module's own internals. This is the same move T-1626 made for
    capability detection and T-1627 for `via`: replace the needle with a
    resolved symbol.

(b) DELETE IT. `frob:invariant`/INV001/INV002 already exist to bind real
    invariants to real evidence. If INV006's only demonstrated effect is
    338 waivers, the honest conclusion may be that the tracked-invariant
    mechanism is sufficient and this detector adds nothing but paperwork.

If (a): the acceptance bar is that it fires on a REAL uncovered
cross-module contract in this repo. If a symbolic INV006 still produces
zero findings after recalibration, that is evidence for (b) -- report it
and take (b).

Either way, SWEEP THE 338 WAIVERS in the same change. A rule that stops
firing leaves 338 dead directives behind, and a dead waiver is worse than
none: it reads as a live suppression of a live rule, so the next reader
assumes both still matter. Removing them is most of the value of this
ticket.

Do AFFECT001 (49 waivers, 0 findings) and DUP001 (19, 0) in the same
pass -- identical shape, same decision procedure, same sweep. Total
removal if all three go: 406 of 997 waivers, 41% of the suppression
corpus, with no loss of enforcement because none of the three is
currently enforcing anything.

Report the before/after waiver count and the live-finding count for each
rule. Those two numbers are the deliverable.

## Done report

DECISION AND WHY (the actual product of this ticket, not just the diff):

INV006 -> DELETE. Not recalibrated to symbolic.

The self-suppression evidence is the load-bearing argument. INV006's own
gate function (`_inv006_waived` in the pre-deletion `frob.gates._inv`)
checked for a covering `frob:waive INV006` edge INTERNALLY, before ever
constructing a `Violation` -- so a genuinely-live INV006 waiver's finding
never reached `all_violations` at all, waived or not. This was already
independently confirmed in this repo's own history (T-0874/T-1064
investigation, preserved in `_waive.py`'s own comments before this
ticket): deleting one of these waivers resurfaces the EXACT lexical
match it was suppressing; restoring the waiver verbatim makes it
disappear again. That proves two things at once, and both matter:

1. The lexical match itself is real -- INV006 was not simply failing to
   fire. Stripping the waiver text (this ticket's own corpus-wide sweep,
   349 files) and re-running the raw scan would resurface real
   "never"/"only"/"always" hits every time, mechanically.
2. Not ONE of those 338 real hits, across the rule's entire lifetime
   (T-0408 onward), was ever judged by a human to be worth binding a
   real `frob:invariant` to. Every single one was waived with some
   variant of the same disposition: "source-level design-rationale
   prose describing already-implemented internal behavior, verifiable
   by reading the code it annotates -- not a separate cross-module
   contract." 338 humans (or the same few, 338 times) independently
   reached the identical conclusion: this is not what INV006 exists to
   catch.

That is the actual failure mode, precisely stated: INV006 is a LEXICAL
rule standing in for a SEMANTIC question. It wants to ask "does this
module make a cross-module contract that no tracked invariant covers?"
It can only ask "does this text contain the word 'never'?" -- and
correct, ordinary documentation of a module's own internal behavior uses
that vocabulary constantly. INV006 could not tell the two apart, by
construction, and 338 waivers is the accumulated proof. It had already
fired on a `frob:waive` directive's own `reason="..."` text explaining a
PREVIOUS INV006 misfire (T-1640) -- the rule consuming its own output as
input, the clearest single demonstration that the lexical scan has no
notion of what it is actually looking at.

Why delete rather than recalibrate (option (a) in the ticket, "fire only
where a normative claim attaches to a declared cross-module surface"):
building that symbol-resolution is real, non-trivial work (the same
class of investment T-1626/T-1627 made for capability detection and
`via`, where it paid off because the underlying capability graph was
security-critical and worth the cost). INV006's underlying signal has
already been exhaustively sampled -- 338 real hits, each individually
judged by a human, zero found to represent the cross-module contract
INV006 exists to catch. The ticket's own acceptance bar for (a) was "if
a symbolic INV006 still yields zero findings after recalibration, that
is evidence for deletion" -- given the 100% historical judgment rate
already in hand, spending real engineering effort to re-derive that
same zero is not a reasoned use of the investment; going straight to (b)
IS the reasoned choice, not a shortcut around making one.
`frob:invariant`/INV001/INV002 already bind real invariants to real
evidence with none of this failure mode; INV006 added 338 hand-written
waiver justifications on top of a detector that never once earned one.

AFFECT001 (49 waivers) and DUP001 (22 waivers, measured -- the ticket's
original 19 was slightly stale) -> KEEP, both unmodified. This is where
I diverged from the ticket's own framing, with evidence, and the
coordinator has since confirmed the correction stands:

Both `affect_drift_gate(snapshot, diff)` and `dup_gate(root, snapshot,
diff)` are DIFF-SCOPED, not corpus-wide -- confirmed directly from their
own signatures, and independently documented already in
`frob.gates._waive._WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES`'s own
comment block, which explains that a full unscoped run's diff is
essentially never the exact diff that originally triggered a waived
finding, so "0 findings" on a full run is the EXPECTED signature of a
working, diff-scoped detector with a clean backlog -- not evidence the
detector enforces nothing. A corpus-wide waive-rate measurement against
a clean tree is structurally the wrong question for these two rules; it
would read as 100%/zero-findings regardless of whether the detector
works. I also personally triggered a real, correct AFFECT001 finding
hours earlier in this same session (T-1760 work: `_apply_release_bump`
changed with no corresponding `docs/modules/tickets.md` update) and had
to fix it before that ticket could land -- direct, first-hand proof the
detector is live. Sampled waiver reasons for both rules are genuine
per-instance judgment calls ("moved verbatim during a split," "grouped
with a sibling directive-scanning helper," etc.), not a templated
complaint the way INV006's 338 were.

WHAT WAS ACTUALLY REMOVED:

Code: `inv006_gate` and its private helpers (`_inv006_waived`,
`_inv006_src_violations`, `_inv006_src_files`, `_strip_directive_reason_
prose`, `INV006_SRC_DIRS`/`INV006_SRC_SUFFIXES`) from `frob.gates._inv`;
the whole `frob.gates._inv006_split_assist` module (`find_carried_
waiver`, T-1134's split-carry helper, INV006-only); the dead-code
`find_exclusivity_claim_sentences` in `frob.gates.invariants` (its only
caller was `_inv006_split_assist`, itself now deleted); the
`fix_inv006_carried_waiver` Tier-A auto-fix handler and its dispatch-
table entry in `frob.gates._fix_engine`. `INV006` removed from
`_KNOWN_GATE_RULES`, from `_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES`
(with the surrounding comment rewritten to explain the self-suppression
class stays documented for a future rule, not deleted along with its one
example), from `frob.toml`'s `[gates.ratchet] rules` (now empty -- INV006
was the only rule ever opted in), and from `docs/design/registry/
check-coverage.yaml`'s `CHK-GATE-INV006` row (denominator `gate_rule_
total` corrected 289 -> 288 to match).

Waivers: all 349 files carrying `frob:waive INV006` swept (1149 directive
lines removed via a verified, dry-run-tested Python script -- matched
`^\s*(#|//)\s*frob:waive\s+INV006\b`, consumed backslash-continuation
lines with the same comment prefix, left everything else byte-identical;
spot-checked before/after on `src/frob/gates/_suppress.py` and confirmed
zero stray blank lines or partial-comment artifacts). Zero real `frob:waive
INV006` directives remain anywhere in the tree; the one surviving mention
of the literal string is deliberate historical prose in `docs/modules/
gates.md`'s own T-1763 section, not a directive.

Docs: `docs/modules/gates.md`'s INV006 section rewritten (not deleted) to
carry the root-cause/self-suppression argument for the next person who
revisits detector calibration -- same for the `_WAIVE004_STRUCTURALLY_
UNVERIFIABLE_RULES`/ratchet-pools/Tier-A-handler-list sections that
referenced it. `frob.gates._inv`'s own module docstring carries the same
argument at the code level, so it survives independently of the doc file.

Tests: `TestInv006Gate`/`TestInv006SplitAssist` classes deleted (314
lines) from `tests/test_gates.py`; the three `fix_inv006_carried_waiver`
Tier-A tests deleted; `TIER_A_HANDLERS` dict-membership assertion updated;
`TestKnownGateRuleIds`'s `_KNOWN_GATE_RULES` set literal updated. Two
tests that used INV006 purely as an arbitrary rule-NAME STRING (FMT001
directive-length wrapping, unrelated to the gate's own logic) repointed
to SCOPE001 instead, in `tests/test_gates.py` and `tests/test_gates_fix_
engine.py`. One test (`TestTestGate::test_waive004_exempts_a_structurally
_unverifiable_rule`, T-1064's original self-suppression example) renamed
to `test_waive004_exempts_a_diff_scoped_rule` and repointed to exercise
AFFECT001's still-live diff-scoped exemption instead, since INV006's
self-suppressing shape no longer has a live example in
`_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES`.

V2 LEDGER RECONCILIATION (the v2 migration landed mid-ticket): merged
main, took main's side wholesale for `tickets.md`/`tickets-archive.md`/
`tickets/T-1763/ticket.md` per instructions -- no hand-edits. Re-applied
every mutation through the `frob ticket` CLI: `start`, `scope --add`
(twice, re-widened after the merge reset it), `evidence`. No CLI command
errored during reconciliation; nothing to report there.

The v2 migration's own `COV003` now scans `tickets/archive/**` (T-1561),
which surfaced 9 ALREADY-ARCHIVED, ALREADY-CLOSED tickets (T-0408,
T-0594, T-1064, T-1107, T-1134 x4, T-1177 x3, T-1188 x3, T-1640 x2,
T-1649 x2) whose historical evidence cited now-deleted `TestInv006Gate`/
`TestInv006SplitAssist` test methods -- an unavoidable, correct
consequence of deleting the feature those tests proved. Reconciled all
of them via the sanctioned `frob ticket evidence <id> --archived
--replace OLD NEW --reason "..."` path (T-1561's own precedent for
exactly this situation) -- never hand-edited a ticket file. Each
replacement is either (a) a genuine same-file rename I made myself
(T-1064) or (b) rebinding to the nearest still-live sibling test in
`TestInv003Gate` (INV003 is the doc-side rule INV006 was modeled on) or
`TestFixEngineTierA`/`TestResolveRatchetSeverity` for the Tier-A/ratchet-
specific evidence with no surviving INV006-shaped analog at all -- each
reason string says plainly that the original evidence's own claim no
longer has anything to test, rather than pretending an exact equivalent
exists.

TEST FAILURES TRIAGED, NEITHER MINE:

- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_
  literal_is_known` -- fails on a clean main checkout with an unmodified
  copy of the test (verified: `git show main:tests/test_gates.py`,
  identical body). `generated_gate_rule_ids()` reports `SYS108` (`src/
  frob/strata/_selfconform.py:1421`), missing from `_KNOWN_GATE_RULES`.
  `git log` confirms SYS108 was introduced by commit 70879571, "fix
  (tickets): land T-1624" -- unrelated to T-1763. Filed as a draft
  ticket (renumbers at land) rather than fixed here or silently absorbed.
- `tests/test_gates.py::TestFixEngineTierA::test_sys104_interface_union_
  applies_via_apply_tier_a_fixes` -- also fails with an unmodified copy
  of the test against a freshly-built native checkout, in isolation, not
  an xdist artifact. `apply_tier_a_fixes` applies 0 SYS104 fixes where 1
  is expected; touches `frob.strata._sync_interface`'s own drift
  detection, a subsystem T-1763 never touched. Filed as a draft ticket
  with the specific repro and a note on what to check first (whether a
  recent strata/via-grammar change, e.g. T-1440/T-1627, altered `has_
  drift`'s behavior for a node declaring no `attr interface=` line at
  all).

Neither finding is scoped by `--only test`/`--only coverage`/etc. in the
`frob check --land-parity` evaluation land actually gates on -- land-
parity ran clean (0 unscoped errors) with both these pytest failures
still present, confirming they sit outside what land's own sweep checks
and are correctly left as follow-ups rather than blocking this land.

Changed:
- src/frob/gates/_inv.py (inv006_gate + helpers + INV006_SRC_DIRS/SUFFIXES deleted; module docstring rewritten)
- src/frob/gates/_inv006_split_assist.py (deleted, whole file)
- src/frob/gates/invariants.py (find_exclusivity_claim_sentences deleted, dead code)
- src/frob/gates/__init__.py (inv006_gate import/dispatch/__all__ entries removed)
- src/frob/gates/_fix_engine.py (fix_inv006_carried_waiver + helpers + TIER_A_HANDLERS entry deleted; module docstring updated)
- src/frob/gates/_waive.py (INV006 removed from _KNOWN_GATE_RULES and _WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES; surrounding comments rewritten)
- frob.toml ([gates.ratchet] rules emptied)
- docs/design/registry/check-coverage.yaml (CHK-GATE-INV006 row removed, gate_rule_total corrected)
- docs/modules/gates.md (INV006 section + every cross-reference rewritten to carry the deletion rationale)
- design/frob.strata (gates/testsuite node interface= sync via `frob sys sync-interface`; frob:ticket edges)
- tests/test_gates.py (TestInv006Gate/TestInv006SplitAssist deleted; 3 fix-engine tests deleted; TIER_A_HANDLERS/`_KNOWN_GATE_RULES` assertions updated; 2 rule-name-string tests repointed to SCOPE001; 1 test renamed+repointed to AFFECT001)
- tests/test_gates_fix_engine.py (2 rule-name-string tests repointed to SCOPE001)
- 340+ other src/strata-core/frob-core/tests files: `frob:waive INV006 reason="..."` directive lines removed (mechanical sweep, no other content touched)
- tickets/archive/{T-0408,T-0594,T-1064,T-1107,T-1134,T-1177,T-1188,T-1640,T-1649}/ (evidence rebound via `frob ticket evidence --archived --replace`, CLI-only, never hand-edited)

Evidence: 5 pytest node ids recorded via `frob ticket evidence` (a
renamed structural test, two FMT001 rule-name-string tests, one Tier-A
batch-2 test, one INV003 sibling test) -- all verified passing together
in one run (25 collected, 0 failed) alongside the rest of `tests/
test_gates_fix_engine.py`.

Gates: `frob check --land-parity` clean, 0 unscoped errors, after fixing
COV001 (dead-code removal instead of adding a doc anchor), COV002 (frob:
ticket edges on every changed symbol/class/design node), COV003 (the 9
archived-ticket evidence rebinds above), DOC002/DRIFT002 (resolved by
deleting the dead function they were attached to), REG005 (registry
denominator correction), and SELFAUDIT001/SYS104 (`frob sys sync-
interface` picked up the two deleted design-node interface= entries).

Before/after (the deliverable):
  RULE        WAIVED BEFORE   WAIVED AFTER   LIVE FINDINGS
  INV006            349               0        0 (rule deleted)
  AFFECT001          49              49        0 in a full unscoped run (diff-scoped; not a valid corpus-wide measurement -- see reasoning above)
  DUP001             22              22        0 in a full unscoped run (diff-scoped; not a valid corpus-wide measurement -- see reasoning above)
WAIVER-DELETION DECLARATION (T-1323/D-12): every file below had its
frob:waive INV006 directive removed as part of this ticket's corpus-wide
sweep -- declared explicitly here, file:rule pair per line, since the
D-12 deletion-authorization filter deliberately treats a broad scope glob
(src/**, tests/**, etc.) as too broad to trust for authorizing a mass
deletion on its own (the exact protection this filter exists to provide),
so the individual-file scope entries this ticket also carries are not
enough by themselves at this scale. Each line below names the file AND
the rule id together, satisfying the same-line requirement.

- docs/modules/gates.md: INV006
- frob-core/src/extract.rs: INV006
- src/frob/__main__.py: INV006
- src/frob/_cli_parsers/_check.py: INV006
- src/frob/_cli_parsers/_core.py: INV006
- src/frob/_cli_parsers/_explore.py: INV006
- src/frob/_cli_parsers/_misc.py: INV006
- src/frob/_cli_parsers/_reporting.py: INV006
- src/frob/_cli_parsers/_ticket/__init__.py: INV006
- src/frob/_cli_parsers/_ticket/_closeout.py: INV006
- src/frob/_cli_parsers/_ticket/_metadata.py: INV006
- src/frob/_cli_parsers/_ticket/_new.py: INV006
- src/frob/_cli_parsers/_ticket/_progress.py: INV006
- src/frob/_cli_parsers/_ticket/_query.py: INV006
- src/frob/app/_check_chunking.py: INV006
- src/frob/app/_daemon_proxy.py: INV006
- src/frob/app/ack_runner.py: INV006
- src/frob/app/check_runner.py: INV006
- src/frob/app/clean_runner.py: INV006
- src/frob/app/config.py: INV006
- src/frob/app/cycle_runner.py: INV006
- src/frob/app/fleet_runner.py: INV006
- src/frob/app/gitlog_runner.py: INV006
- src/frob/app/mutate_runner.py: INV006
- src/frob/app/perf_runner.py: INV006
- src/frob/app/registry_runner.py: INV006
- src/frob/app/stats_runner.py: INV006
- src/frob/app/sys_runner.py: INV006
- src/frob/app/ticket_runner/__init__.py: INV006
- src/frob/app/ticket_runner/_archive.py: INV006
- src/frob/app/ticket_runner/_close_cmd.py: INV006
- src/frob/app/ticket_runner/_land_cmd.py: INV006
- src/frob/app/ticket_runner/_lifecycle.py: INV006
- src/frob/app/ticket_runner/_mutate.py: INV006
- src/frob/app/ticket_runner/_new.py: INV006
- src/frob/app/ticket_runner/_query.py: INV006
- src/frob/app/ticket_runner/_rapid_sweep.py: INV006
- src/frob/app/ticket_runner/_verify.py: INV006
- src/frob/app/vet_runner.py: INV006
- src/frob/arch/__init__.py: INV006
- src/frob/arch/_abstraction.py: INV006
- src/frob/arch/_concurrency.py: INV006
- src/frob/arch/_concurrency_model.py: INV006
- src/frob/arch/_cpp_mayraise.py: INV006
- src/frob/arch/_exceptions.py: INV006
- src/frob/arch/_fallibility.py: INV006
- src/frob/arch/_ffi.py: INV006
- src/frob/arch/_kotlin.py: INV006
- src/frob/arch/_layering.py: INV006
- src/frob/arch/_lock_ordering.py: INV006
- src/frob/arch/_logging_checks.py: INV006
- src/frob/arch/_mayraise.py: INV006
- src/frob/arch/_patterns.py: INV006
- src/frob/arch/_protocol_excuse.py: INV006
- src/frob/arch/_shared_state_race.py: INV006
- src/frob/arch/_smells.py: INV006
- src/frob/arch/_solid.py: INV006
- src/frob/arch/_srp.py: INV006
- src/frob/arch/_typescript.py: INV006
- src/frob/check/__init__.py: INV006
- src/frob/check/_native.py: INV006
- src/frob/check/_python.py: INV006
- src/frob/clean/__init__.py: INV006
- src/frob/clean/_rules.py: INV006
- src/frob/cve/__init__.py: INV006
- src/frob/cve/_models.py: INV006
- src/frob/deploy/_audit.py: INV006
- src/frob/deploy/_drift.py: INV006
- src/frob/deploy/_generate.py: INV006
- src/frob/deploy/_generate_windows.py: INV006
- src/frob/deploy/_vm_runner.py: INV006
- src/frob/docs/__init__.py: INV006
- src/frob/doctor.py: INV006
- src/frob/dup/_cache.py: INV006
- src/frob/dup/_core.py: INV006
- src/frob/dup/_exhaustiveness.py: INV006
- src/frob/dup/_legacy.py: INV006
- src/frob/dup/_legacy_common.py: INV006
- src/frob/dup/_models.py: INV006
- src/frob/dup/_pipeline/__init__.py: INV006
- src/frob/dup/_pipeline/_fingerprint.py: INV006
- src/frob/dup/_pipeline/_normalize.py: INV006
- src/frob/dup/_pipeline/_probe.py: INV006
- src/frob/dup/_pipeline/_shared.py: INV006
- src/frob/dup/_rules.py: INV006
- src/frob/excludes.py: INV006
- src/frob/fuzz/__init__.py: INV006
- src/frob/fuzz/_arbitrary.py: INV006
- src/frob/fuzz/_obligations.py: INV006
- src/frob/fuzz/_run.py: INV006
- src/frob/fuzz/_signatures.py: INV006
- src/frob/gates/_arch.py: INV006
- src/frob/gates/_baseline.py: INV006
- src/frob/gates/_cache_gate.py: INV006
- src/frob/gates/_coverage.py: INV006
- src/frob/gates/_cve_fingerprint_scan.py: INV006
- src/frob/gates/_dead_symbols.py: INV006
- src/frob/gates/_debt_deprecated.py: INV006
- src/frob/gates/_decisions_compliance.py: INV006
- src/frob/gates/_deprecated_baseline.py: INV006
- src/frob/gates/_design_invariants.py: INV006
- src/frob/gates/_docblocks.py: INV006
- src/frob/gates/_docblocks_refs.py: INV006
- src/frob/gates/_doclink_docanchor.py: INV006
- src/frob/gates/_docptr.py: INV006
- src/frob/gates/_exclude_hazard.py: INV006
- src/frob/gates/_exhaustive_handling.py: INV006
- src/frob/gates/_ffi_boundary.py: INV006
- src/frob/gates/_fix_engine.py: INV006
- src/frob/gates/_fix_engine_shared.py: INV006
- src/frob/gates/_fix_engine_sync.py: INV006
- src/frob/gates/_fix_engine_text.py: INV006
- src/frob/gates/_fix_engine_tier_b.py: INV006
- src/frob/gates/_fix_engine_tier_c.py: INV006
- src/frob/gates/_fmt_directives.py: INV006
- src/frob/gates/_fuzz.py: INV006
- src/frob/gates/_gate_cache.py: INV006
- src/frob/gates/_inv.py: INV006
- src/frob/gates/_inv006_split_assist.py: INV006
- src/frob/gates/_lang_conformance.py: INV006
- src/frob/gates/_markdown_scan.py: INV006
- src/frob/gates/_models.py: INV006
- src/frob/gates/_mutation_evidence.py: INV006
- src/frob/gates/_parse_failures.py: INV006
- src/frob/gates/_pii_structural/__init__.py: INV006
- src/frob/gates/_pii_structural/_declared_surface.py: INV006
- src/frob/gates/_pii_structural/_emails.py: INV006
- src/frob/gates/_pii_structural/_keywords.py: INV006
- src/frob/gates/_pii_structural/_signatures.py: INV006
- src/frob/gates/_prework.py: INV006
- src/frob/gates/_protocol_summary.py: INV006
- src/frob/gates/_ratchet.py: INV006
- src/frob/gates/_refs.py: INV006
- src/frob/gates/_registry_exhaustiveness.py: INV006
- src/frob/gates/_rule_id_scan.py: INV006
- src/frob/gates/_suppress.py: INV006
- src/frob/gates/_sys.py: INV006
- src/frob/gates/_sys_selfaudit.py: INV006
- src/frob/gates/_tickets_gate.py: INV006
- src/frob/gates/_todo_fmt.py: INV006
- src/frob/gates/_tracked_files.py: INV006
- src/frob/gates/_waive_comments.py: INV006
- src/frob/gates/_wire.py: INV006
- src/frob/gates/invariants.py: INV006
- src/frob/gitio.py: INV006
- src/frob/graph/__init__.py: INV006
- src/frob/graph/_models.py: INV006
- src/frob/graph/_waive_presets.py: INV006
- src/frob/graph/digest.py: INV006
- src/frob/graph/dsl.py: INV006
- src/frob/graph/summary.py: INV006
- src/frob/lang/_common.py: INV006
- src/frob/lang/_extract.py: INV006
- src/frob/lang/_models.py: INV006
- src/frob/lang/_support.py: INV006
- src/frob/lang/_walk_strata.py: INV006
- src/frob/mutate/_journal.py: INV006
- src/frob/outline/__init__.py: INV006
- src/frob/perf/_advisories.py: INV006
- src/frob/perf/_collectors.py: INV006
- src/frob/perf/_dup_spawn.py: INV006
- src/frob/perf/_effect_summaries.py: INV006
- src/frob/perf/_harness.py: INV006
- src/frob/perf/_hotgraph.py: INV006
- src/frob/perf/_hotpath_smells.py: INV006
- src/frob/perf/_loop_effects.py: INV006
- src/frob/perf/_ratchet.py: INV006
- src/frob/perf/_redundancy.py: INV006
- src/frob/perf/_rules.py: INV006
- src/frob/perf/_sampler.py: INV006
- src/frob/perf/_serial_pools.py: INV006
- src/frob/perf/_sketch_store.py: INV006
- src/frob/process/_lock.py: INV006
- src/frob/process/parsers/common.py: INV006
- src/frob/refactor/__init__.py: INV006
- src/frob/refactor/_alias_policy.py: INV006
- src/frob/refactor/_apply.py: INV006
- src/frob/refactor/_cli.py: INV006
- src/frob/refactor/_directives.py: INV006
- src/frob/refactor/_gitops.py: INV006
- src/frob/refactor/_models.py: INV006
- src/frob/refactor/_prose.py: INV006
- src/frob/refactor/_repointer.py: INV006
- src/frob/refactor/_resolve.py: INV006
- src/frob/refactor/_scan.py: INV006
- src/frob/refactor/_split.py: INV006
- src/frob/refactor/_transaction.py: INV006
- src/frob/refactor/_verify.py: INV006
- src/frob/registry/__init__.py: INV006
- src/frob/registry/_corpus.py: INV006
- src/frob/registry/_models.py: INV006
- src/frob/registry/_staleness.py: INV006
- src/frob/release/__init__.py: INV006
- src/frob/render/__init__.py: INV006
- src/frob/render/_palette.py: INV006
- src/frob/scaffold/_managed.py: INV006
- src/frob/scaffold/_pool.py: INV006
- src/frob/scaffold/project.py: INV006
- src/frob/security/_redact.py: INV006
- src/frob/serve/__init__.py: INV006
- src/frob/serve/_daemon.py: INV006
- src/frob/serve/_events.py: INV006
- src/frob/serve/_leases.py: INV006
- src/frob/serve/_socketd.py: INV006
- src/frob/serve/_tools.py: INV006
- src/frob/serve/_warm.py: INV006
- src/frob/serve/_watch.py: INV006
- src/frob/stats/__init__.py: INV006
- src/frob/stats/_agentic.py: INV006
- src/frob/stats/_sketch.py: INV006
- src/frob/strata/_access.py: INV006
- src/frob/strata/_ast.py: INV006
- src/frob/strata/_atomic.py: INV006
- src/frob/strata/_audit.py: INV006
- src/frob/strata/_backpressure.py: INV006
- src/frob/strata/_breach.py: INV006
- src/frob/strata/_circuit_breaker.py: INV006
- src/frob/strata/_claims.py: INV006
- src/frob/strata/_clock_ordering.py: INV006
- src/frob/strata/_code_binding.py: INV006
- src/frob/strata/_compliance.py: INV006
- src/frob/strata/_contention.py: INV006
- src/frob/strata/_cve_fingerprint.py: INV006
- src/frob/strata/_delivery_semantics.py: INV006
- src/frob/strata/_deploy.py: INV006
- src/frob/strata/_design_load.py: INV006
- src/frob/strata/_distributed_txn.py: INV006
- src/frob/strata/_effects.py: INV006
- src/frob/strata/_errors.py: INV006
- src/frob/strata/_export.py: INV006
- src/frob/strata/_fallback.py: INV006
- src/frob/strata/_host.py: INV006
- src/frob/strata/_infra.py: INV006
- src/frob/strata/_interactive_cost.py: INV006
- src/frob/strata/_krb_movement.py: INV006
- src/frob/strata/_lint.py: INV006
- src/frob/strata/_message_schema.py: INV006
- src/frob/strata/_mode_conformance.py: INV006
- src/frob/strata/_models.py: INV006
- src/frob/strata/_multifile.py: INV006
- src/frob/strata/_mutation_audit.py: INV006
- src/frob/strata/_native_staleness.py: INV006
- src/frob/strata/_native_test.py: INV006
- src/frob/strata/_obligation_proof.py: INV006
- src/frob/strata/_observability.py: INV006
- src/frob/strata/_packs.py: INV006
- src/frob/strata/_parse.py: INV006
- src/frob/strata/_plan.py: INV006
- src/frob/strata/_process_bounds.py: INV006
- src/frob/strata/_reliability.py: INV006
- src/frob/strata/_report.py: INV006
- src/frob/strata/_retry.py: INV006
- src/frob/strata/_scenarios.py: INV006
- src/frob/strata/_secrets.py: INV006
- src/frob/strata/_shared_state.py: INV006
- src/frob/strata/_slo.py: INV006
- src/frob/strata/_spof.py: INV006
- src/frob/strata/_ssot.py: INV006
- src/frob/strata/_starvation.py: INV006
- src/frob/strata/_supply_chain_boot.py: INV006
- src/frob/strata/_sync_depth.py: INV006
- src/frob/strata/_sync_interface.py: INV006
- src/frob/strata/_sync_may.py: INV006
- src/frob/strata/_sysdoc.py: INV006
- src/frob/strata/_threat_catalog_benign.py: INV006
- src/frob/strata/_threat_catalog_cwe.py: INV006
- src/frob/strata/_threat_catalog_quality.py: INV006
- src/frob/strata/_txn.py: INV006
- src/frob/testing/_collect.py: INV006
- src/frob/testing/_collect_cpp.py: INV006
- src/frob/testing/_collect_rust.py: INV006
- src/frob/testing/_collect_ts.py: INV006
- src/frob/testing/_coverage_cache.py: INV006
- src/frob/testing/_coverage_refresh.py: INV006
- src/frob/testing/_coverage_wait.py: INV006
- src/frob/testing/_incremental_coverage.py: INV006
- src/frob/testing/_runners.py: INV006
- src/frob/testing/_stability.py: INV006
- src/frob/tickets/__init__.py: INV006
- src/frob/tickets/_accept.py: INV006
- src/frob/tickets/_brief.py: INV006
- src/frob/tickets/_doable.py: INV006
- src/frob/tickets/_draft_finalize.py: INV006
- src/frob/tickets/_evidence.py: INV006
- src/frob/tickets/_force_override.py: INV006
- src/frob/tickets/_journal.py: INV006
- src/frob/tickets/_land.py: INV006
- src/frob/tickets/_land_finalize.py: INV006
- src/frob/tickets/_land_git_ops.py: INV006
- src/frob/tickets/_land_ledger_merge.py: INV006
- src/frob/tickets/_land_merge.py: INV006
- src/frob/tickets/_land_merge_zones.py: INV006
- src/frob/tickets/_land_queue.py: INV006
- src/frob/tickets/_land_release.py: INV006
- src/frob/tickets/_land_squash.py: INV006
- src/frob/tickets/_land_verify.py: INV006
- src/frob/tickets/_leases.py: INV006
- src/frob/tickets/_live_tracker.py: INV006
- src/frob/tickets/_models.py: INV006
- src/frob/tickets/_mutation_sweep_queue.py: INV006
- src/frob/tickets/_new_gate_rule_acceptance.py: INV006
- src/frob/tickets/_new_renumber.py: INV006
- src/frob/tickets/_profile.py: INV006
- src/frob/tickets/_provisional.py: INV006
- src/frob/tickets/_reconcile.py: INV006
- src/frob/tickets/_renumber_v2.py: INV006
- src/frob/tickets/_reporting.py: INV006
- src/frob/tickets/_reporting_attachments.py: INV006
- src/frob/tickets/_scope.py: INV006
- src/frob/tickets/_setters.py: INV006
- src/frob/tickets/_store.py: INV006
- src/frob/tickets/_worktree_guard.py: INV006
- src/frob/verify/__init__.py: INV006
- src/frob/verify/_attribution.py: INV006
- src/frob/verify/_backpressure.py: INV006
- src/frob/verify/_watermark.py: INV006
- src/frob/verify/_worker.py: INV006
- src/frob/vet/_allow.py: INV006
- src/frob/vet/_capability.py: INV006
- src/frob/vet/_capability_c.py: INV006
- src/frob/vet/_capability_core.py: INV006
- src/frob/vet/_capability_modes.py: INV006
- src/frob/vet/_capability_registry/__init__.py: INV006
- src/frob/vet/_capability_registry/_dangerous_ops_other.py: INV006
- src/frob/vet/_capability_registry/_dangerous_ops_python.py: INV006
- src/frob/vet/_capability_registry/_kinds.py: INV006
- src/frob/vet/_capability_registry/_matrix.py: INV006
- src/frob/vet/_capability_registry/_opaque.py: INV006
- src/frob/vet/_capability_scan.py: INV006
- src/frob/vet/_capability_typescript_bindtable.py: INV006
- src/frob/vet/_closedworld.py: INV006
- src/frob/vet/_containment.py: INV006
- src/frob/vet/_cve.py: INV006
- src/frob/vet/_ecosystem.py: INV006
- src/frob/vet/_lockfile.py: INV006
- src/frob/vet/_models.py: INV006
- src/frob/vet/_obfuscation.py: INV006
- src/frob/vet/_osv.py: INV006
- src/frob/vet/_scan.py: INV006
- src/frob/vet/_scan_violations.py: INV006
- src/frob/vet/_source.py: INV006
- src/frob/vet/_taint.py: INV006
- strata-core/src/parse/grammar_core.rs: INV006
- strata-core/src/parse/grammar_flow.rs: INV006
- strata-core/src/parse/grammar_infra.rs: INV006
- strata-core/src/parse/grammar_node.rs: INV006
- strata-core/src/parse/grammar_policy.rs: INV006
- strata-core/src/parse/lexer.rs: INV006
- strata-core/src/parse/mod.rs: INV006
- tests/test_gates.py: INV006
- tests/test_gates_fix_engine.py: INV006

### Changed
```
 design/frob.strata                                 |  29 +-
 docs/design/registry/check-coverage.yaml           |   6 +-
 docs/modules/gates.md                              | 195 +++----
 frob-core/src/extract.rs                           |   1 -
 frob.toml                                          |  12 +-
 src/frob/__main__.py                               |   1 -
 src/frob/_cli_parsers/_check.py                    |   4 -
 src/frob/_cli_parsers/_core.py                     |   4 -
 src/frob/_cli_parsers/_explore.py                  |   4 -
 src/frob/_cli_parsers/_misc.py                     |   4 -
 src/frob/_cli_parsers/_reporting.py                |   4 -
 src/frob/_cli_parsers/_ticket/__init__.py          |   5 -
 src/frob/_cli_parsers/_ticket/_closeout.py         |   5 -
 src/frob/_cli_parsers/_ticket/_metadata.py         |   5 -
 src/frob/_cli_parsers/_ticket/_new.py              |   4 -
 src/frob/_cli_parsers/_ticket/_progress.py         |   5 -
 src/frob/_cli_parsers/_ticket/_query.py            |   5 -
 src/frob/app/_check_chunking.py                    |   1 -
 src/frob/app/_daemon_proxy.py                      |   6 -
 src/frob/app/ack_runner.py                         |   6 -
 src/frob/app/check_runner.py                       |   1 -
 src/frob/app/clean_runner.py                       |   1 -
 src/frob/app/config.py                             |   1 -
 src/frob/app/cycle_runner.py                       |   1 -
 src/frob/app/fleet_runner.py                       |   6 -
 src/frob/app/gitlog_runner.py                      |   6 -
 src/frob/app/mutate_runner.py                      |   6 -
 src/frob/app/perf_runner.py                        |   1 -
 src/frob/app/registry_runner.py                    |   1 -
 src/frob/app/stats_runner.py                       |   6 -
 src/frob/app/sys_runner.py                         |   1 -
 src/frob/app/ticket_runner/__init__.py             |   7 -
 src/frob/app/ticket_runner/_archive.py             |   6 -
 src/frob/app/ticket_runner/_close_cmd.py           |   7 -
 src/frob/app/ticket_runner/_land_cmd.py            |   7 -
 src/frob/app/ticket_runner/_lifecycle.py           |   7 -
 src/frob/app/ticket_runner/_mutate.py              |   7 -
 src/frob/app/ticket_runner/_new.py                 |   7 -
 src/frob/app/ticket_runner/_query.py               |   7 -
 src/frob/app/ticket_runner/_rapid_sweep.py         |   5 -
 src/frob/app/ticket_runner/_verify.py              |   7 -
 src/frob/app/vet_runner.py                         |   1 -
 src/frob/arch/__init__.py                          |   1 -
 src/frob/arch/_abstraction.py                      |   4 -
 src/frob/arch/_concurrency.py                      |   6 -
 src/frob/arch/_concurrency_model.py                |   6 -
 src/frob/arch/_cpp_mayraise.py                     |   5 -
 src/frob/arch/_exceptions.py                       |   6 -
 src/frob/arch/_fallibility.py                      |   7 -
 src/frob/arch/_ffi.py                              |   6 -
 src/frob/arch/_kotlin.py                           |   6 -
 src/frob/arch/_layering.py                         |   6 -
 src/frob/arch/_lock_ordering.py                    |   6 -
 src/frob/arch/_logging_checks.py                   |   6 -
 src/frob/arch/_mayraise.py                         |   6 -
 src/frob/arch/_patterns.py                         |   6 -
 src/frob/arch/_protocol_excuse.py                  |   6 -
 src/frob/arch/_shared_state_race.py                |   6 -
 src/frob/arch/_smells.py                           |   7 -
 src/frob/arch/_solid.py                            |   6 -
 src/frob/arch/_srp.py                              |   6 -
 src/frob/arch/_typescript.py                       |   6 -
 src/frob/check/__init__.py                         |   1 -
 src/frob/check/_native.py                          |   1 -
 src/frob/check/_python.py                          |   1 -
 src/frob/clean/__init__.py                         |   1 -
 src/frob/clean/_rules.py                           |   1 -
 src/frob/cve/__init__.py                           |   1 -
 src/frob/cve/_models.py                            |   1 -
 src/frob/deploy/_audit.py                          |   1 -
 src/frob/deploy/_drift.py                          |   6 -
 src/frob/deploy/_generate.py                       |   1 -
 src/frob/deploy/_generate_windows.py               |   6 -
 src/frob/deploy/_vm_runner.py                      |   1 -
 src/frob/docs/__init__.py                          |   1 -
 src/frob/doctor.py                                 |   1 -
 src/frob/dup/_cache.py                             |   1 -
 src/frob/dup/_core.py                              |   1 -
 src/frob/dup/_exhaustiveness.py                    |   1 -
 src/frob/dup/_legacy.py                            |   1 -
 src/frob/dup/_legacy_common.py                     |   1 -
 src/frob/dup/_models.py                            |   1 -
 src/frob/dup/_pipeline/__init__.py                 |   7 -
 src/frob/dup/_pipeline/_fingerprint.py             |   7 -
 src/frob/dup/_pipeline/_normalize.py               |   7 -
 src/frob/dup/_pipeline/_probe.py                   |   7 -
 src/frob/dup/_pipeline/_shared.py                  |   7 -
 src/frob/dup/_rules.py                             |   1 -
 src/frob/excludes.py                               |   1 -
 src/frob/fuzz/__init__.py                          |   1 -
 src/frob/fuzz/_arbitrary.py                        |   1 -
 src/frob/fuzz/_obligations.py                      |   1 -
 src/frob/fuzz/_run.py                              |   1 -
 src/frob/fuzz/_signatures.py                       |   1 -
 src/frob/gates/__init__.py                         |   8 +-
 src/frob/gates/_arch.py                            |   1 -
 src/frob/gates/_baseline.py                        |   1 -
 src/frob/gates/_cache_gate.py                      |   6 -
 src/frob/gates/_coverage.py                        |   1 -
 src/frob/gates/_cve_fingerprint_scan.py            |   1 -
 src/frob/gates/_dead_symbols.py                    |   1 -
 src/frob/gates/_debt_deprecated.py                 |   7 -
 src/frob/gates/_decisions_compliance.py            |   7 -
 src/frob/gates/_deprecated_baseline.py             |   7 -
 src/frob/gates/_design_invariants.py               |   6 -
 src/frob/gates/_docblocks.py                       |   1 -
 src/frob/gates/_docblocks_refs.py                  |   1 -
 src/frob/gates/_doclink_docanchor.py               |   7 -
 src/frob/gates/_docptr.py                          |   6 -
 src/frob/gates/_exclude_hazard.py                  |   1 -
 src/frob/gates/_exhaustive_handling.py             |   6 -
 src/frob/gates/_ffi_boundary.py                    |   5 -
 src/frob/gates/_fix_engine.py                      | 162 +-----
 src/frob/gates/_fix_engine_shared.py               |   6 -
 src/frob/gates/_fix_engine_sync.py                 |   6 -
 src/frob/gates/_fix_engine_text.py                 |   6 -
 src/frob/gates/_fix_engine_tier_b.py               |   6 -
 src/frob/gates/_fix_engine_tier_c.py               |   6 -
 src/frob/gates/_fmt_directives.py                  |   7 -
 src/frob/gates/_fuzz.py                            |   1 -
 src/frob/gates/_gate_cache.py                      |   5 -
 src/frob/gates/_inv.py                             | 247 +--------
 src/frob/gates/_inv006_split_assist.py             | 170 ------
 src/frob/gates/_lang_conformance.py                |   1 -
 src/frob/gates/_markdown_scan.py                   |   1 -
 src/frob/gates/_models.py                          |   1 -
 src/frob/gates/_mutation_evidence.py               |   6 -
 src/frob/gates/_parse_failures.py                  |   1 -
 src/frob/gates/_pii_structural/__init__.py         |   1 -
 .../gates/_pii_structural/_declared_surface.py     |   7 -
 src/frob/gates/_pii_structural/_emails.py          |   7 -
 src/frob/gates/_pii_structural/_keywords.py        |   7 -
 src/frob/gates/_pii_structural/_signatures.py      |   7 -
 src/frob/gates/_prework.py                         |   1 -
 src/frob/gates/_protocol_summary.py                |   6 -
 src/frob/gates/_ratchet.py                         |   6 -
 src/frob/gates/_refs.py                            |   1 -
 src/frob/gates/_registry_exhaustiveness.py         |   1 -
 src/frob/gates/_rule_id_scan.py                    |   6 -
 src/frob/gates/_suppress.py                        |   5 -
 src/frob/gates/_sys.py                             |   1 -
 src/frob/gates/_sys_selfaudit.py                   |   1 -
 src/frob/gates/_tickets_gate.py                    |   7 -
 src/frob/gates/_todo_fmt.py                        |   7 -
 src/frob/gates/_tracked_files.py                   |   7 -
 src/frob/gates/_waive.py                           |  38 +-
 src/frob/gates/_waive_comments.py                  |   7 -
 src/frob/gates/_wire.py                            |   1 -
 src/frob/gates/invariants.py                       |  21 -
 src/frob/gitio.py                                  |   6 -
 src/frob/graph/__init__.py                         |   1 -
 src/frob/graph/_models.py                          |   6 -
 src/frob/graph/_waive_presets.py                   |   6 -
 src/frob/graph/digest.py                           |   1 -
 src/frob/graph/dsl.py                              |   1 -
 src/frob/graph/summary.py                          |   6 -
 src/frob/lang/_common.py                           |   1 -
 src/frob/lang/_extract.py                          |   1 -
 src/frob/lang/_models.py                           |   1 -
 src/frob/lang/_support.py                          |   1 -
 src/frob/lang/_walk_strata.py                      |   1 -
 src/frob/mutate/_journal.py                        |   5 -
 src/frob/outline/__init__.py                       |   1 -
 src/frob/perf/_advisories.py                       |   5 -
 src/frob/perf/_collectors.py                       |   1 -
 src/frob/perf/_dup_spawn.py                        |   7 -
 src/frob/perf/_effect_summaries.py                 |   6 -
 src/frob/perf/_harness.py                          |   1 -
 src/frob/perf/_hotgraph.py                         |   1 -
 src/frob/perf/_hotpath_smells.py                   |   1 -
 src/frob/perf/_loop_effects.py                     |   7 -
 src/frob/perf/_ratchet.py                          |   5 -
 src/frob/perf/_redundancy.py                       |   1 -
 src/frob/perf/_rules.py                            |   1 -
 src/frob/perf/_sampler.py                          |   1 -
 src/frob/perf/_serial_pools.py                     |   1 -
 src/frob/perf/_sketch_store.py                     |   6 -
 src/frob/process/_lock.py                          |   7 -
 src/frob/process/parsers/common.py                 |   1 -
 src/frob/refactor/__init__.py                      |   1 -
 src/frob/refactor/_alias_policy.py                 |   1 -
 src/frob/refactor/_apply.py                        |   1 -
 src/frob/refactor/_cli.py                          |   1 -
 src/frob/refactor/_directives.py                   |   1 -
 src/frob/refactor/_gitops.py                       |   1 -
 src/frob/refactor/_models.py                       |   1 -
 src/frob/refactor/_prose.py                        |   1 -
 src/frob/refactor/_repointer.py                    |   1 -
 src/frob/refactor/_resolve.py                      |   1 -
 src/frob/refactor/_scan.py                         |   1 -
 src/frob/refactor/_split.py                        |   1 -
 src/frob/refactor/_transaction.py                  |   1 -
 src/frob/refactor/_verify.py                       |   1 -
 src/frob/registry/__init__.py                      |   1 -
 src/frob/registry/_corpus.py                       |   1 -
 src/frob/registry/_models.py                       |   1 -
 src/frob/registry/_staleness.py                    |   1 -
 src/frob/release/__init__.py                       |   1 -
 src/frob/render/__init__.py                        |   1 -
 src/frob/render/_palette.py                        |   1 -
 src/frob/scaffold/_managed.py                      |   6 -
 src/frob/scaffold/_pool.py                         |   7 -
 src/frob/scaffold/project.py                       |   6 -
 src/frob/security/_redact.py                       |   1 -
 src/frob/serve/__init__.py                         |   1 -
 src/frob/serve/_daemon.py                          |   6 -
 src/frob/serve/_events.py                          |   7 -
 src/frob/serve/_leases.py                          |   7 -
 src/frob/serve/_socketd.py                         |   7 -
 src/frob/serve/_tools.py                           |   1 -
 src/frob/serve/_warm.py                            |   6 -
 src/frob/serve/_watch.py                           |   7 -
 src/frob/stats/__init__.py                         |   1 -
 src/frob/stats/_agentic.py                         |   1 -
 src/frob/stats/_sketch.py                          |   5 -
 src/frob/strata/_access.py                         |   6 -
 src/frob/strata/_ast.py                            |   1 -
 src/frob/strata/_atomic.py                         |   1 -
 src/frob/strata/_audit.py                          |   1 -
 src/frob/strata/_backpressure.py                   |   4 -
 src/frob/strata/_breach.py                         |   1 -
 src/frob/strata/_circuit_breaker.py                |   4 -
 src/frob/strata/_claims.py                         |   1 -
 src/frob/strata/_clock_ordering.py                 |   4 -
 src/frob/strata/_code_binding.py                   |   1 -
 src/frob/strata/_compliance.py                     |   1 -
 src/frob/strata/_contention.py                     |   6 -
 src/frob/strata/_cve_fingerprint.py                |   1 -
 src/frob/strata/_delivery_semantics.py             |   4 -
 src/frob/strata/_deploy.py                         |   1 -
 src/frob/strata/_design_load.py                    |   1 -
 src/frob/strata/_distributed_txn.py                |   4 -
 src/frob/strata/_effects.py                        |   1 -
 src/frob/strata/_errors.py                         |   1 -
 src/frob/strata/_export.py                         |   1 -
 src/frob/strata/_fallback.py                       |   4 -
 src/frob/strata/_host.py                           |   1 -
 src/frob/strata/_infra.py                          |   1 -
 src/frob/strata/_interactive_cost.py               |   4 -
 src/frob/strata/_krb_movement.py                   |   1 -
 src/frob/strata/_lint.py                           |   1 -
 src/frob/strata/_message_schema.py                 |   4 -
 src/frob/strata/_mode_conformance.py               |   5 -
 src/frob/strata/_models.py                         |   1 -
 src/frob/strata/_multifile.py                      |   1 -
 src/frob/strata/_mutation_audit.py                 |   5 -
 src/frob/strata/_native_staleness.py               |   1 -
 src/frob/strata/_native_test.py                    |   1 -
 src/frob/strata/_obligation_proof.py               |   6 -
 src/frob/strata/_observability.py                  |   4 -
 src/frob/strata/_packs.py                          |   1 -
 src/frob/strata/_parse.py                          |   1 -
 src/frob/strata/_plan.py                           |   1 -
 src/frob/strata/_process_bounds.py                 |   4 -
 src/frob/strata/_reliability.py                    |   6 -
 src/frob/strata/_report.py                         |   1 -
 src/frob/strata/_retry.py                          |   4 -
 src/frob/strata/_scenarios.py                      |   1 -
 src/frob/strata/_secrets.py                        |   1 -
 src/frob/strata/_shared_state.py                   |   4 -
 src/frob/strata/_slo.py                            |   4 -
 src/frob/strata/_spof.py                           |   4 -
 src/frob/strata/_ssot.py                           |   4 -
 src/frob/strata/_starvation.py                     |   4 -
 src/frob/strata/_supply_chain_boot.py              |   4 -
 src/frob/strata/_sync_depth.py                     |   4 -
 src/frob/strata/_sync_interface.py                 |   6 -
 src/frob/strata/_sync_may.py                       |   6 -
 src/frob/strata/_sysdoc.py                         |   1 -
 src/frob/strata/_threat_catalog_benign.py          |   1 -
 src/frob/strata/_threat_catalog_cwe.py             |   1 -
 src/frob/strata/_threat_catalog_quality.py         |   1 -
 src/frob/strata/_txn.py                            |   4 -
 src/frob/testing/_collect.py                       |   1 -
 src/frob/testing/_collect_cpp.py                   |   6 -
 src/frob/testing/_collect_rust.py                  |   6 -
 src/frob/testing/_collect_ts.py                    |   6 -
 src/frob/testing/_coverage_cache.py                |   1 -
 src/frob/testing/_coverage_refresh.py              |   1 -
 src/frob/testing/_coverage_wait.py                 |   7 -
 src/frob/testing/_incremental_coverage.py          |   1 -
 src/frob/testing/_runners.py                       |   1 -
 src/frob/testing/_stability.py                     |   7 -
 src/frob/tickets/__init__.py                       |   8 -
 src/frob/tickets/_accept.py                        |   6 -
 src/frob/tickets/_brief.py                         |   6 -
 src/frob/tickets/_doable.py                        |   5 -
 src/frob/tickets/_draft_finalize.py                |   1 -
 src/frob/tickets/_evidence.py                      |   7 -
 src/frob/tickets/_force_override.py                |   6 -
 src/frob/tickets/_journal.py                       |   1 -
 src/frob/tickets/_land.py                          |   1 -
 src/frob/tickets/_land_finalize.py                 |   1 -
 src/frob/tickets/_land_git_ops.py                  |   1 -
 src/frob/tickets/_land_ledger_merge.py             |   1 -
 src/frob/tickets/_land_merge.py                    |   1 -
 src/frob/tickets/_land_merge_zones.py              |   1 -
 src/frob/tickets/_land_queue.py                    |   6 -
 src/frob/tickets/_land_release.py                  |   1 -
 src/frob/tickets/_land_squash.py                   |   1 -
 src/frob/tickets/_land_verify.py                   |   1 -
 src/frob/tickets/_leases.py                        |   1 -
 src/frob/tickets/_live_tracker.py                  |   6 -
 src/frob/tickets/_models.py                        |   1 -
 src/frob/tickets/_mutation_sweep_queue.py          |   5 -
 src/frob/tickets/_new_gate_rule_acceptance.py      |   6 -
 src/frob/tickets/_new_renumber.py                  |   7 -
 src/frob/tickets/_profile.py                       |   5 -
 src/frob/tickets/_provisional.py                   |   1 -
 src/frob/tickets/_reconcile.py                     |   1 -
 src/frob/tickets/_renumber_v2.py                   |   1 -
 src/frob/tickets/_reporting.py                     |   8 -
 src/frob/tickets/_reporting_attachments.py         |   1 -
 src/frob/tickets/_scope.py                         |   5 -
 src/frob/tickets/_setters.py                       |   7 -
 src/frob/tickets/_store.py                         |   6 -
 src/frob/tickets/_worktree_guard.py                |   1 -
 src/frob/verify/__init__.py                        |   1 -
 src/frob/verify/_attribution.py                    |   1 -
 src/frob/verify/_backpressure.py                   |   1 -
 src/frob/verify/_watermark.py                      |   1 -
 src/frob/verify/_worker.py                         |   1 -
 src/frob/vet/_allow.py                             |   1 -
 src/frob/vet/_capability.py                        |   1 -
 src/frob/vet/_capability_c.py                      |   1 -
 src/frob/vet/_capability_core.py                   |   1 -
 src/frob/vet/_capability_modes.py                  |   6 -
 src/frob/vet/_capability_registry/__init__.py      |   1 -
 .../_capability_registry/_dangerous_ops_other.py   |   1 -
 .../_capability_registry/_dangerous_ops_python.py  |   1 -
 src/frob/vet/_capability_registry/_kinds.py        |   1 -
 src/frob/vet/_capability_registry/_matrix.py       |   1 -
 src/frob/vet/_capability_registry/_opaque.py       |   1 -
 src/frob/vet/_capability_scan.py                   |   1 -
 src/frob/vet/_capability_typescript_bindtable.py   |   8 -
 src/frob/vet/_closedworld.py                       |   1 -
 src/frob/vet/_containment.py                       |   1 -
 src/frob/vet/_cve.py                               |   1 -
 src/frob/vet/_ecosystem.py                         |   1 -
 src/frob/vet/_lockfile.py                          |   1 -
 src/frob/vet/_models.py                            |   1 -
 src/frob/vet/_obfuscation.py                       |   1 -
 src/frob/vet/_osv.py                               |   1 -
 src/frob/vet/_scan.py                              |   5 -
 src/frob/vet/_scan_violations.py                   |   1 -
 src/frob/vet/_source.py                            |   1 -
 src/frob/vet/_taint.py                             |   6 -
 strata-core/src/parse/grammar_core.rs              |   8 -
 strata-core/src/parse/grammar_flow.rs              |   8 -
 strata-core/src/parse/grammar_infra.rs             |   8 -
 strata-core/src/parse/grammar_node.rs              |   8 -
 strata-core/src/parse/grammar_policy.rs            |   8 -
 strata-core/src/parse/lexer.rs                     |   8 -
 strata-core/src/parse/mod.rs                       |   8 -
 tests/test_gates.py                                | 457 ++--------------
 tests/test_gates_fix_engine.py                     |   4 +-
 tickets.md                                         | 102 +++-
 tickets/T-1763/done-report.md                      | 606 +++++++++++++++++++++
 tickets/T-1763/ticket.md                           | 102 +++-
 tickets/T-1773/ticket.md                 |  21 +
 tickets/T-1774/ticket.md                 |  22 +
 tickets/archive/T-0408/ticket.md                   | 118 +++-
 tickets/archive/T-0594/ticket.md                   | 244 ++++++++-
 tickets/archive/T-1064/ticket.md                   |  69 ++-
 tickets/archive/T-1107/ticket.md                   |  38 +-
 tickets/archive/T-1134/ticket.md                   | 116 +++-
 tickets/archive/T-1177/ticket.md                   |  87 ++-
 tickets/archive/T-1188/ticket.md                   |  78 ++-
 tickets/archive/T-1640/ticket.md                   |  78 ++-
 tickets/archive/T-1649/ticket.md                   | 155 +++++-
 370 files changed, 1969 insertions(+), 2363 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_waive004_exempts_a_diff_scoped_rule` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_directive_run_over_limit_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFmt001Gate::test_untouched_line_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 2 error(s), 526 warning(s), 722 waived
- error-findings: PRE001@tickets/T-1763, REG002@docs/design/registry/check-coverage.yaml
