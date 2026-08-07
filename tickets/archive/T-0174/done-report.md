## Done report

Changed:
- strata-core/src/parse.rs -- `parse_node`'s clause loop gains `waive
  RULE_ID reason STRING [ticket STRING]`, a repeatable node property
  parsed alongside `may`/`code`/`carries`; `reason` is mandatory in the
  grammar itself (hard parse error without it), emitted onto each node's
  `waives` JSON array
- src/frob/strata/_ast.py -- `WaiverDecl` (rule/reason/ticket),
  `NodeDecl.waives: tuple[WaiverDecl, ...]`
- src/frob/strata/_models.py -- `Waiver` (rule/reason/ticket, frozen),
  `Node.waives: tuple[Waiver, ...]`
- src/frob/strata/_elaborate.py -- `_elaborate_node` maps
  `decl.waives` straight onto `Node.waives` (direct-mapping convention,
  same as `may`/`deploy`)
- src/frob/strata/_waive.py (new) -- the generic waiver evaluator:
  `apply_waivers` (matches findings against declared `Node.waives` by
  exact (node, rule), indexed by dict for O(1) lookup, computes STALE
  waivers), `WaiverMatch`, `WaivedFinding`, `WaiverApplication`,
  `STALE_WAIVER_RULE` ("SYSWAIVE002"), `stale_detail`. Generic over
  finding shape via `rule_of`/`target_of` callables plus a MANDATORY
  `in_scope` predicate per caller -- `Node.waives` is model-global but
  `check_self_conformance` and `evaluate_exhaustiveness` each only see
  their own slice of findings, so `in_scope` prevents a LINT004 waiver
  from being misreported STALE inside the SYS100-102-only pass (a real
  bug caught during self-testing against `design/frob.strata`'s own
  waivers, fixed before landing)
- src/frob/strata/_selfconform.py -- `check_self_conformance` applies
  `apply_waivers` (in_scope = the three SYS rule ids) to SYS100-102
  violations before returning; `SelfConformReport.waived` field added
- src/frob/strata/_audit.py -- `FamilyGap.target` field added (node id a
  gap fired against, populated by every `_xxx_gaps` adapter);
  `evaluate_exhaustiveness` applies `apply_waivers` (in_scope = every
  rule except the three SYS ids) to the full gap set before returning;
  `AuditReport.waived` field added
- src/frob/app/sys_runner.py -- `_print_audit_report`/
  `_print_selfconform_report` print a WAIVED line (family/rule/target/
  reason) for every waived finding, unconditionally, before the
  PROVED/GAP branch
- src/frob/strata/__init__.py -- exports `WaiverDecl`, `Waiver`,
  `WaivedFinding`, `WaiverApplication`, `WaiverMatch`,
  `STALE_WAIVER_RULE`, `apply_waivers`
- editors/vscode-strata/syntaxes/strata.tmLanguage.json --
  `clause-keywords` pattern gains `reason`, `ticket`, `waive`
  (drift-lock: `tests/unit/test_strata_tmlanguage.py`)
- docs/strata/waive.md (new) -- full mechanism doc: grammar, which rules
  are waivable, WAIVED reporting, stale-waiver drift lock, implementation
  map
- docs/strata/selfconform.md, docs/strata/threat.md, docs/strata/
  surface.md -- cross-links to the new doc; `surface.md`'s node grammar
  sketch extended with `waive_clause`; `threat.md`'s "self-model honesty
  note" rewritten to describe the now-waived (not merely left-firing)
  LINT004 gaps
- design/frob.strata -- `checker`/`stratamod`/`core`/`vet` nodes each
  gain a `waive "LINT004" reason "..." ticket "T-0200";` clause (T-0200
  checked `queued`, not landed, per the ledger at authoring time -- this
  is the honest-debt flow this ticket exists to provide); comments
  updated to describe the waiver instead of "left firing"
- tests/unit/strata/litmus/waive_lint.strata (new) -- litmus fixture:
  `node_waived` (real firing LINT004 + matching waiver) and `node_stale`
  (kill-switch already declared, so its waiver matches nothing -- STALE)
- tests/unit/strata/test_litmus_waive.py (new), tests/unit/strata/
  test_waive.py (new), tests/unit/strata/test_selfconform.py --
  `TestWaiverChannel` class added

`frob sys audit` on this repo's own `design/frob.strata` is PROVED (zero
gaps, zero SYS gaps) with the four LINT004 waivers printed as WAIVED with
their reasons -- verified by hand (`uv run frob sys audit`, exit 0) and by
`TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant`.

Filed: none -- everything needed stayed inside T-0174's declared scope;
T-0222/T-0223/T-0226 (the sibling-pilot P1 tickets whose bodies reference
this waiver channel) are pre-existing, not filed by this ticket, and were
read for context only per the dispatch instructions.

Gates: `frob check --stamp-baseline` then `--delta` clean (0/4 new
violations); `frob test --base main` both python/strata runners exit 0.

## REJECT round fixes (reviewer: 3 soundness holes)

Reviewer REJECTed the first landing for three real defects, all fixed:

1. **SPECIFICITY (blanket-waiver bug at node scope)**: `apply_waivers`
   keyed only on `(node, rule)`, but SYS100/SYS101/THREAT002/THREAT003
   can each fire MORE THAN ONCE per node (once per capability kind/CWE)
   -- a bare `waive "SYS100" ...` would suppress every current and future
   SYS100 finding on that node, the exact T-0148 bug reopened at node
   scope. Fixed:
   - `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` = `{SYS100, SYS101,
     THREAT002, THREAT003}` (SYS101 added beyond the reviewer's literal
     two-family list -- it shares SYS100's exact per-capability-kind
     shape, so the same bug would reopen on it alone if left bare-rule).
   - `_waive.py::split_waiver_rule` parses a `RULE:SUBTARGET` form on the
     SAME rule STRING (no grammar change: `"SYS100:fs-write"`,
     `"THREAT003:CWE-78"`) -- picked over a new grammar keyword since the
     sub-target is ordinary string data the parser never needs to
     understand.
   - `_waive.py::validate_waiver_fields` + `_elaborate.py::
     _validate_waivers` (wired into `elaborate()` before every other
     cross-declaration check) REJECT a multi-instance-family rule with no
     sub-target at elaborate time (`StrataError.MalformedWaiver`) --
     parse-time cannot know which rules are multi-instance (Python-side
     vocabulary fact), so this is elaborate-time by necessity, not choice.
   - `apply_waivers` gained a mandatory `sub_target_of` callable and now
     matches on the full `(node, family, sub_target)` triple.
     `SelfConformViolation.capability` (new field) and `FamilyGap.
     sub_target` (new field) carry each finding's instance-level
     identifier -- never parsed back out of `detail` text.
   - Single-instance families (LINT/PII/COMPLIANCE, SYS102) keep the
     bare-rule form -- verified explicit per-family in
     `TestValidateWaiverFields::test_every_multi_instance_family_
     requires_sub_target` (iterates the frozenset both ways).
   - Critical litmus: `waive_lint.strata`'s new `node_multi` node fires
     THREAT003 for CWE-78 (exec) AND CWE-89 (sql) on the SAME node,
     waives ONLY `THREAT003:CWE-78` -- CWE-89 is asserted to still fire
     unwaived (`test_sub_target_waiver_does_not_suppress_a_different_
     sub_target`), plus the same shape at the `check_self_conformance`
     layer (`test_sub_target_waiver_does_not_suppress_a_different_kind`,
     hand-built `KernelModel` with two undeclared capability kinds on one
     node).
2. **HONESTY (silent-looking PROVED with active waivers)**: `sys_runner`
   printed unqualified `"PROVED -- zero gaps"` even with waivers active
   (a `WARNING`-level WAIVED line is lost under grep/quiet filtering that
   the `INFO`-level PROVED summary survives -- reviewer confirmed this
   live). Fixed: `_print_audit_report`/`_print_selfconform_report` now
   print `"PROVED (N waived) -- zero UNWAIVED gaps..."` whenever
   `report.waived` is non-empty, unqualified `"PROVED"` only when it is
   empty. Verified by hand against `design/frob.strata`: `uv run frob sys
   audit` now prints `"sys audit: PROVED (4 waived) -- zero UNWAIVED gaps
   across every configured view"`.
3. **Empty-reason bypass**: `reason ""` / `reason "   "` parsed
   successfully (a functional blanket bypass -- the grammar cannot see a
   string is blank). Fixed: `validate_waiver_fields` rejects
   empty/whitespace-only reasons with the same `MalformedWaiver` error,
   enforced by the same `_validate_waivers` elaborate-time pass. Verified
   by `TestElaborateWaivers::test_empty_reason_fails_closed`/
   `test_whitespace_only_reason_fails_closed` and
   `TestValidateWaiverFields::test_empty_reason_rejected`/
   `test_whitespace_reason_rejected`.

Also fixed as part of getting these three right: the WAIVED output
detail now embeds the RAW declared rule string (`WAIVED[RULE]` /
`WAIVED[RULE:SUBTARGET]`), not just the bare finding family, so a reader
can always see the EXACT sub-target a printed reason was written against
(`_audit.py`/`_selfconform.py`'s `waived_gaps`/`waived_violations`
construction).

`design/frob.strata`'s four existing `LINT004` waivers (checker/core/
stratamod/vet) are UNCHANGED (still bare-rule) -- LINT004 is genuinely
single-instance-per-node (`_lint.py::check_lint_kill_switch` folds every
risky kind a node holds into ONE finding), so a sub-target would name
nothing; this is a deliberate, documented choice
(`docs/strata/waive.md#sub-targets-required-for-multi-instance-families`),
not an oversight the reviewer's instruction was mechanically applied
against.

Merge note: `main` moved twice during this round (T-0161 PERF gate
rework, then T-0166 store `code`/`may` grammar). T-0166 gave
`design/frob.strata`'s `tickets_ledger` store real `may "exec"` with no
kill switch, which now fires a genuine NEW LINT004 finding `frob sys
audit` cannot waive -- the `waive` clause was only ever added to
`strata-core/src/parse/mod.rs::parse_node`, not `parse_store` (T-0166 landed
concurrently with, not before, this ticket's original round, so store
support was never in scope). This is real, unrelated debt from a
different ticket's concurrent landing, not something T-0174 introduced or
should silently paper over by scope-creeping grammar work into this
round. Not Filed T-draft-41982e4b (never refiled) ("extend waive clause grammar to store
nodes (tickets_ledger LINT004 gap from T-0166)") rather than fixed here.
`frob sys audit` therefore now exits 1 with exactly ONE honestly-named,
tracked gap (`tickets_ledger` LINT004) -- this is the correct, intended
behavior of an honest-debt system, not a regression: an unwaived gap with
a filed ticket is exactly what "declare real facts or waive with
reasons" means when a waiver genuinely cannot be written yet.

Gates (REJECT-round re-verification): `frob check --stamp-baseline` then
`--delta` clean (0/7 new violations); `frob test --base main` both
python/strata runners exit 0 (post-merge, natives rebuilt via `make
core`); `git diff main --diff-filter=D --stat` empty (deletion-filter
clean, post-merge).
