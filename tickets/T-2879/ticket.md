---
id: T-2879
title: 'Red-tail sweep: COV001/DRIFT002/DOCENUM001/PERF004/DOC011/DOC006 (6 independent
  causes, CYCLE001/TICK004 verified correctly left alone)'
state: done
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- docs/modules/tickets-landing.md
- src/frob/strata/_selfconform_binding_rules.py
- src/frob/strata/_selfconform_surface_rules.py
- docs/investigations/T-2796-backlog-reproduction.md
- docs/guides/claude-hooks.md
evidence_scope:
- tests/unit/gates/test_doc011.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/gates.md
  reason: docs/modules/gates.md is under T-2874's live lease (Waive COV007's last
    finding); deferring DOCENUM001 fix to avoid a scope collision, will file/handle
    separately once T-2874 lands
  actor: logan
  at: '2026-08-22'
body_changes:
- mode: set
  reason: avoid literal DOC006-triggering path/symbol-pointer syntax for two illustrative
    citations (.claude/settings.local.json, frob.check._native_check_and_rebuild)
    -- both are prose narration, not real doc pointers
  actor: logan
  at: '2026-08-22'
  old_length: 7506
  new_length: 7541
- mode: append
  reason: 'BUG002 front door (T-2393): Doc/design-file annotation corrections (frob:doc/frob:describes/frob:waive
    additions, one backtick code-span fix) with no production code path changed; nothing
    for a designated repro test to exercise differently between commits.'
  actor: logan
  at: '2026-08-22'
  old_length: 7540
  new_length: 7803
evidence:
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_id_inside_inline_code_span_is_not_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Re-measured 2026-08-22 via unbudgeted `frob check --json` (gate-summary
present, ~350s): main carries 33 errors / 14 distinct (rule,file)
identities right now (down from the coordinator's 15-identity snapshot
minutes earlier -- tree moving under concurrent lands). This ticket
covers the assigned subset: PERF004 (5), COV001 (2), DRIFT002 (2),
DOC011 (1), DOC006 (1), DOCENUM001 (1) = 12 errors across 6 identities.
SELFAUDIT001/CLAUDE001 are explicitly owned elsewhere; TICK004/CYCLE001
are explicitly out of scope per the caveats below.

## Characterization: six independent root causes, not one

Investigated each before touching anything (git log/blame, git grep for
the actual symbol, read the citing ticket's own Done report where one
exists). None share a mechanism:

1. **COV001 x2 (design/frob.strata:1632,1635)** -- T-2801's own land
   (`f60eb5404`) added two new flows, `f_checker_stratamod` and
   `f_checker_natives`, documenting a real dependency it found
   (frob.check's _native_check_and_rebuild helper's lazy imports of
   `frob.strata`/`frob.natives._build`). It gave each a plain `// T-2801:
   ...` prose comment instead of the `frob:doc` directive every sibling
   flow in this file carries (`// frob:doc docs/strata/roadmap.md#self-
   hosting-commitments-decision-d7`, used by every other internal
   `checker -> X` flow). This is a follow-on omission from that land,
   not a new design decision -- fix is to add the same sibling anchor,
   reusing existing accurate doc content per this repo's convention, not
   inventing new prose.

2. **DRIFT002 x2 (docs/modules/tickets-landing.md, `#--check-repro-...`
   and `#bug003-the-positive-direction-...` sections)** -- exactly the
   playbook 4c pattern. `git grep` confirms `_BugReproOutcome` and
   `must_still_pass_violations` both now live in
   `src/frob/gates/_bug_repro.py` (T-2851's split out of
   `_mutation_evidence.py`); the two `frob:describes` edges still name
   the old file. Repoint only -- content already accurately describes
   both symbols post-split, no rewrite needed.

3. **DOCENUM001 (docs/modules/gates.md#rule-catalog)** -- same root
   cause CLASS as T-2801's own REG002 fix (DOC013, added under T-2843,
   never fully rolled into every enumeration site) but a DIFFERENT site:
   T-2801 fixed `docs/design/registry/check-coverage.yaml`; this
   ticket's finding is `docs/modules/gates.md`'s OWN separate
   `frob:enumerates ... members="..."` list, which independently omits
   DOC013. The table row for DOC013 already exists at line 76 -- only
   the enumerate directive's member list needs DOC013 inserted
   (alphabetically, between DOC012 and DOCBLOCKSSCHEMA001).

4. **PERF004 x5 (`_selfconform_binding_rules.py:92,202`,
   `_selfconform_surface_rules.py:314,372,429`)** -- all five are the
   identical shape: `sorted(<per-iteration-distinct-set>)` called for a
   `_log.warning` inside an outer `for node in model.nodes:` (or
   equivalent) loop, where the sorted collection is a DIFFERENT set on
   every iteration (`via_less_atoms`, `dupes`, `real - declared`,
   `observed - allowed`, each computed fresh per node). This is the
   exact syntactic-detector false-positive shape T-2801 already found
   and waived once this session (`_evidence.py:251`, "each loop
   iteration's own distinct per-other-ticket intersection set, sorted
   only for a log message, not a repeated re-sort of identical data").
   PERF004 is a lexical/syntactic check (any `sorted()` textually inside
   a `for`) with no data-flow analysis to tell "same set every
   iteration" (genuinely hoistable) from "new set every iteration"
   (not) -- confirmed by reading all 5 call sites directly, not
   assumed from the rule name. All 5: waive, matching the established
   precedent's reasoning and wording convention.

5. **DOC011 (docs/investigations/T-2796-backlog-reproduction.md:116)**
   -- the doc mentions `T-draft-be1e79b5` while discussing "T-2693
   (TICK006 phantom-refile of T-draft-be1e79b5 collides with T-2689's
   identical title/scope)". This is not a typo or dead citation to fix:
   the paragraph's whole subject IS that this draft id was never
   finalized/collided historically -- a point-in-time investigation
   record documenting an anomaly, not a live reference that should
   resolve. The same file already carries a top-of-file `frob:waive
   REF002` for the identical "point-in-time investigation doc" reason
   (T-2369). Waive DOC011 the same way, same file, same justification
   shape -- do not alter the investigation's own historical prose.

6. **DOC006 (docs/guides/claude-hooks.md:208)** -- cites
   the local, gitignored settings.local.json file (under .claude/) while narrating a real, historically
   observed incident (an agent setting FROB_COORDINATOR=1 in that
   file). That local settings file is a real, intentionally
   untracked (gitignored) per-session local file -- it will never
   resolve as a tracked path, by design. This repo has an established
   inline-comment waiver convention for exactly this shape (checked:
   `docs/audits/check-performance.md`, `docs/audits/graph.md`,
   `docs/audits/gates-quality.md` all carry inline `frob:waive DOC006`
   comments for ephemeral/illustrative/untracked-by-design paths).
   Waive inline, same convention.

## Explicitly OUT of scope (verified, not assumed)

- **CYCLE001 (src/frob/__init__.py)**: read T-2801's Done report --
  this exact identity was found there too and explicitly left
  undischarged: "the file's own header comment documents this as a live
  160-node cycle already tracked by T-2583 (untangle, an explicit
  owner-decision hold) and T-2584 (the fact that `frob:waive CYCLE001`
  does nothing -- `frob-cycle` never consults the waiver pipeline)."
  Re-verified the header comment is still present and unchanged, and
  the cycle's member list in this run is the same shape (160+ files
  rooted at `src/frob/tickets/_worktree_sweep.py`). Same finding,
  correctly left alone -- not touched here.
- **TICK004 (tickets.md, 3 epics: T-0969, T-1273, T-1382)**: same three
  epic ids as T-2801's own explicit non-fix: "administrative
  epic-staleness state, not something a single bug ticket should
  force-close or re-triage; each is noted in the gate's own message as
  'already decomposed and being worked (a no-op likely)'." Re-verified
  against the current gate message text (unchanged: "already decomposed
  and being worked ... the recommended action is checking the
  children's own progress instead"). Correctly left alone.

## Noted but NOT filed (flag for coordinator)

- **LANG004 (src/frob/lang/_support.py)** appeared in this run's
  unbudgeted measurement but was NOT in the coordinator's assigned
  bucket list, and T-2801's own re-measurement of the SAME identity
  explicitly found it "not present" (a stale-sweep false positive) at
  T-2801's measurement time. It has since reappeared. Not investigated
  further or fixed here -- outside this ticket's assigned scope, and
  its history (present -> absent -> present) suggests either flake or a
  genuine regression from a land between T-2801 and now; flagging by
  name rather than silently fixing or silently ignoring it.

frob:no-behavior-change reason="All six fixes are doc/design-file annotation corrections (frob:doc/frob:describes/frob:enumerates/frob:waive additions) plus PERF004 waivers with no runtime-behavior-affecting code edits -- there is no production code path change for a designated repro test to exercise differently between the parent commit and this fix."

frob:no-behavior-change reason="Doc/design-file annotation corrections (frob:doc/frob:describes/frob:waive additions, one backtick code-span fix) with no production code path changed; nothing for a designated repro test to exercise differently between commits."