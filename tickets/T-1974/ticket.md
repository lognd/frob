---
id: T-1974
title: 'Adding one gate rule id needs three hand edits and none is checked before
  the land: DOCENUM001+REG010 regressed the floor twice'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new_gate_rule_acceptance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
REPEATED-MISTAKE AUDIT (2026-08-10). Adding ONE gate rule id requires
hand-updating at least THREE places. None of them is checked before the
land that adds the rule; each is caught afterwards by a different gate,
as a floor regression on main that then needs its own ticket.

The three places:
  1. `_KNOWN_GATE_RULES` (src/frob/gates/_waive.py) -- the registry
     literal.
  2. `docs/modules/gates.md#rule-catalog` -- the `frob:enumerates`
     member list, enforced by DOCENUM001.
  3. `docs/design/registry/check-coverage.yaml` -- a CHK-GATE-<rule>
     entry, enforced by REG010.

MEASURED, twice in one session, same shape both times:
  - T-1937 registered 8 new ids (BUDGET001, CHECK001, CVEFP001,
    DEPLOY001-003, DERIVED001, SYS109). Its land immediately produced
    DOCENUM001 on docs/modules/gates.md (filed as T-1958) AND REG010 on
    check-coverage.yaml. Both had to be fixed by follow-up tickets.
  - T-1629 registered SYS110. Its land produced the IDENTICAL
    DOCENUM001 (`docs/modules/gates.md:13 -- frob:enumerates ... claims a
    stale member list for 'src/frob/gates/_waive.py::_KNOWN_GATE_RULES'`)
    AND REG010 (filed as T-1972). T-1958 had fixed this exact error
    hours earlier; it recurred on the very next rule addition.

So the floor went 0 -> 1 purely as bookkeeping debt from a land that was
otherwise correct. The author of the rule is not doing anything wrong;
the tool simply does not tell them the other two edits exist until after
they have landed.

THE RULE IS ALREADY WRITTEN DOWN AND DID NOT HELP. Dispatch briefs this
session explicitly told agents "a new gate rule id must be added to
`_KNOWN_GATE_RULES` or the acceptance preflight will not see it", and
that warning was followed -- step 1 was done both times. Steps 2 and 3
were still missed, because nothing names them at the moment of the edit.
Per the standing audit rule: when a written rule is followed and the
failure still happens, the rule was not the fix.

DO NOT FIX IT THIS WAY:
- Do NOT make `_KNOWN_GATE_RULES` a computed expression to keep the doc
  in sync. `frob.tickets._new_gate_rule_acceptance` scrapes that
  literal's SOURCE TEXT (via `git show <rev>:...` plus a regex, not via
  import) for the T-0756 acceptance preflight; a computed expression has
  no literal to scrape and would silently blind that consumer -- the
  exact consumer T-1937 existed to protect.
- Do NOT relax DOCENUM001 or REG010. They are correctly catching real
  staleness; the defect is that they catch it too late.
- Do NOT solve it with a `frob rules sync` verb an author must remember
  to run. Per standing directive, a command requires knowledge of the
  command, and this failure is specifically about not knowing.

FIX DIRECTION, preferred order:
(a) At the moment a new rule id is registered, update all three places
    automatically (the registry entry and the enumerates list are both
    mechanically derivable from the id set).
(b) Failing that, make the ticket-close/land preflight that ALREADY
    detects newly-added rule ids -- `unregistered_rule_ids_in_scope`,
    wired into `_evidence.py`'s done-transition guard by T-1956 --
    also refuse when places 2 and 3 are stale for that id. That hook
    already exists and already fires at the right moment; it currently
    checks only place 1.

(b) is likely the cheap correct answer: the detection point is built,
tested and live, and only its coverage is narrow.

ACCEPTANCE: first test must FAIL before the fix -- register a new rule id
without touching docs/modules/gates.md or check-coverage.yaml, and assert
the close/land refuses naming BOTH stale locations. Then assert a rule id
whose three places are all consistent closes cleanly, and that removing a
rule id is handled symmetrically (no false refusal).
