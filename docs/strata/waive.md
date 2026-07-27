# Waiving `frob sys audit` findings (T-0174)

`frob check` gate violations have had `frob:waive REASON="..."` since
early on (`docs/modules/gates.md#waive-boundary-t-0101`): a repo can
record honest debt instead of either fixing a finding immediately or
faking it green. `frob sys audit` findings (SYS100-102, THREAT002/003,
LINT004, ...) had no equivalent channel -- a piloting repo had to fix
every finding immediately or live with permanent red, which pushes toward
gaming the model (deleting a `may` declaration, weakening a claim) rather
than recording the debt where it belongs. This is that channel.

## Surface syntax

A `waive` clause lives ON THE NODE it excuses, inside the `node { ... }`
block, alongside `may`/`code`/`carries` (`strata-core/src/parse.rs`'s
`parse_node`):

```
node checker : trusted {
    code "src/frob/check/**";
    may "exec";
    waive "LINT004" reason "no real kill switch around subprocess spawning yet -- T-0200 is the follow-on ticket to build one" ticket "T-0200";
}
```

Grammar: `waive RULE_ID reason "..." [ticket "..."]`. `RULE_ID` and
`reason` are STRING literals (not IDENT), the same choice `may`/`carries`
made -- rule ids and free-text reasons are not valid identifiers. `ticket`
is optional and, when present, should name the ticket tracking the real
fix (`design/frob.strata`'s own T-0200 waivers are the worked example: see
the `checker`/`stratamod`/`core`/`vet` nodes).

`reason` is mandatory -- both IN THE GRAMMAR (`waive "RULE";` with no
`reason` clause at all is a hard parse error, like `frob:waive`'s
`reason="..."` requirement but enforced earlier) AND at elaborate time
(`reason ""` or `reason "   "` parses cleanly as an empty/whitespace-only
STRING but is REJECTED by `_elaborate.py::_validate_waivers` with
`StrataError.MalformedWaiver` -- an empty reason is a functional bypass,
not a written debt record, and the grammar alone cannot see that a string
is blank). There is no way to elaborate a module with a blank-reason
waiver: no blanket waivers, ever.

A node may declare more than one `waive` clause (one per rule/sub-target
pair it excuses).

## Which rules are waivable

Any rule whose finding names the node it fired against: SYS100
(undeclared interface), SYS101 (stale design), SYS102 (unmodeled code,
`_selfconform.py`), THREAT002/THREAT003 (`_threat.py`), LINT001-005
(`_lint.py`), PII001-004 (`_pii.py`), COMPLIANCE001/002 (`_compliance.py`).

Findings with no single owning node (a catalog-completeness gap, a
CVE-fingerprint catalog drift check) cannot be targeted by a `waive`
clause -- there is no node to attach it to.

<a id="sub-targets"></a>

## Sub-targets: required for multi-instance-per-node rule families

`RULE_ID` alone is not always a fine enough key. **SYS100, SYS101,
THREAT002, and THREAT003 can each fire MORE THAN ONCE on the same node**
-- once per capability kind observed/declared, once per CWE implicated.
A bare `waive "SYS100" reason "...";` would suppress EVERY current AND
FUTURE SYS100 finding on that node under one stale reason -- exactly the
T-0148 blanket-waiver bug the file-scoped -> symbol-scoped `frob:waive`
fix closed for gate violations, reopened here at node scope (this is a
real defect a review round caught in T-0174's first landing; it is fixed,
not theoretical).

The fix is a `RULE:SUBTARGET` form on the SAME `RULE_ID` string -- no new
grammar keyword, just a documented convention `_waive.py::
split_waiver_rule` parses:

```
node checker : trusted {
    may "exec";
    waive "SYS100:exec" reason "capability is intentional, tracked in T-0201";
}
node payments : trusted {
    may "sql";
    waive "THREAT003:CWE-89" reason "parameterized at the ORM layer, discharge claim pending" ticket "T-0301";
}
```

`MULTI_INSTANCE_WAIVER_FAMILIES` (`_waive.py`) names the families that
REQUIRE a sub-target: `SYS100`, `SYS101`, `THREAT002`, `THREAT003`, and
(the same per-flow reasoning, one node can originate several flows)
`REL200`/`REL201`, `REL220`/`REL221`/`REL222`, `REL270`/`REL271`/
`REL272`, and `REL370`/`REL371`/`REL372` (T-0657's CLOCK/ORDERING-
ASSUMPTIONS family, `_clock_ordering.py`). A `waive` clause on one of
these with no `:SUBTARGET` is an ELABORATE-TIME error
(`StrataError.MalformedWaiver`) -- the grammar accepts the bare string
(it does not know which rules are multi-instance; that is a Python-side
vocabulary fact), but `_elaborate.py::_validate_waivers` rejects it
before a `KernelModel` can exist. There is no silent "assume it means
every instance" fallback.

Single-instance-per-node families keep the bare-rule form -- `LINT001-005`
(one finding per node per rule; `_lint.py::check_lint_kill_switch` folds
every risky kind a node holds into ONE `LINT004` finding, not one per
kind), `PII001-004`, `COMPLIANCE001/002`, and `SYS102` (one finding per
UNMODELED DIRECTORY, not per node-multiplicity) -- `design/frob.strata`'s
four `LINT004` waivers stay bare-rule deliberately, not because they were
missed in this fix.

A `waive` clause matches a finding iff `(node id, rule family, sub-target)`
is an EXACT triple match -- never a substring/prefix, never "waive
everything on this node," and (the point of this section) never "waive
every instance of this rule on this node." `sub_target=None` (bare rule)
only ever matches a finding whose own sub-target is also `None`.

<!-- frob:invariant INV-036 -->

## Reported output: WAIVED, never silent

`frob sys audit` prints a `WAIVED` line for every suppressed finding, WITH
the reason, whether or not the run is otherwise clean -- a waiver can
never make a run look silently empty. The detail text carries the
`waive` clause's RAW declared rule string (`WAIVED[RULE]` /
`WAIVED[RULE:SUBTARGET]`), never just the finding's bare family, so a
reader can always see the EXACT sub-target a waiver named -- a reason must
never appear to justify a finding it did not:

```
sys audit: WAIVED family=lint view=model rule=LINT004 target=checker detail=... -- WAIVED[LINT004]: 'no real kill switch around subprocess spawning yet -- T-0200 is the follow-on ticket to build one' (ticket T-0200)
sys audit: WAIVED family=security view=owasp-top-10 rule=THREAT003 target=payments detail=... -- WAIVED[THREAT003:CWE-89]: 'parameterized at the ORM layer, discharge claim pending' (ticket T-0301)
```

`AuditReport.waived` / `SelfConformReport.waived` carry these
programmatically; `AuditReport.proved` / a non-empty `SelfConformReport.
violations` are computed AFTER waiving, so a waived finding never counts
against either gate.

**The summary line itself carries the waived count, not just a separate
WARNING** -- a `WARNING`-level `WAIVED` line can be lost under `grep`/
quiet-mode filtering while the `INFO`-level "PROVED" summary survives, so
"PROVED" alone (with active waivers silently propping it up) would read
as a genuinely clean run. `frob sys audit` instead prints `PROVED (N
waived)` whenever any waiver is active, and unqualified `PROVED` only when
none are:

```
sys audit: PROVED (4 waived) -- zero UNWAIVED gaps across every configured view
sys audit: self-conformance PROVED -- zero SYS gaps
```

## Drift lock: stale waivers fail

A `waive` clause names a `(node, rule family, sub-target)` triple that
must actually be firing right now. If the underlying finding stops firing
-- the capability is removed, the kill switch gets added, the claim gets
discharged -- the waiver has nothing left to waive and is itself reported
as a NEW finding, `SYSWAIVE002` (`_waive.py::STALE_WAIVER_RULE`), under
the `waiver` family (`AuditReport`) or as a `SelfConformViolation`
(`SelfConformReport`). This mirrors the gate system's WAIVE002
(`docs/modules/gates.md#waive-boundary-t-0101`: a waiver that can never
match is loud, not a silent no-op) -- except here it is drift in the
OTHER direction: the waiver used to be effective and stopped being
needed, which is good news, but a `waive` clause left behind after the
debt is paid is itself now misleading text and must be deleted.
`SYSWAIVE002` fails the run (`AuditReport.proved` is `False`,
`SelfConformReport.violations` is non-empty) until the stale `waive`
clause is removed.

A waiver's sub-target being wrong (e.g. `SYS100:net` on a node that only
ever fires `SYS100:exec`) is ALSO caught by this same mechanism -- the
declared triple simply never matches any finding, so it goes STALE like
any other ineffective waiver. There is no separate "sub-target mismatch"
error class; staleness already covers it.

## Implementation

- Grammar: `strata-core/src/parse.rs`'s `waive` node property (the
  `RULE:SUBTARGET` convention is NOT a grammar feature -- it is an
  ordinary STRING value the parser never inspects).
- Errors: `_errors.py::StrataError.MalformedWaiver` -- blank reason or a
  multi-instance family with no sub-target.
- AST/kernel: `_ast.py::WaiverDecl` -> `_elaborate.py::_elaborate_node` ->
  `_models.py::Node.waives: tuple[Waiver, ...]`; `_elaborate.py::
  _validate_waivers` (called from `elaborate()` before any other
  cross-declaration check) rejects a malformed waiver before a
  `KernelModel` can exist.
- Sub-target parsing: `_waive.py::split_waiver_rule` (`"SYS100:exec"` ->
  `("SYS100", "exec")`), `MULTI_INSTANCE_WAIVER_FAMILIES`,
  `validate_waiver_fields` (the actual check `_validate_waivers` calls).
- Matching/staleness: `_waive.py::apply_waivers` -- one generic algorithm
  shared by `check_self_conformance` (SYS100-102) and
  `evaluate_exhaustiveness` (everything else), matching on `(node, rule,
  sub_target)` via caller-supplied `rule_of`/`target_of`/`sub_target_of`
  callables, partitioned by an `in_scope` predicate per caller so a
  LINT004 waiver is never judged stale by the SYS100-102 pass (which
  never sees LINT findings at all) and vice versa. `SelfConformViolation.
  capability` and `FamilyGap.sub_target` are the structured fields that
  carry each finding's instance-level identifier -- never parsed back out
  of `detail`'s free text.
- Reporting: `_audit.py::AuditReport.waived` / `_selfconform.py::
  SelfConformReport.waived`; printed by `src/frob/app/sys_runner.py::
  _print_audit_report` / `_print_selfconform_report`, including the
  `PROVED (N waived)` summary-line honesty fix.
- tmLanguage: `editors/vscode-strata/syntaxes/strata.tmLanguage.json`'s
  `clause-keywords` pattern includes `waive`/`reason`/`ticket`
  (drift-locked against the parser by `tests/unit/test_strata_tmlanguage.py`).
  No new entry needed for `RULE:SUBTARGET` -- it is a plain STRING value,
  not a grammar construct.
- Litmus fixture: `tests/unit/strata/litmus/waive_lint.strata` +
  `tests/unit/strata/test_litmus_waive.py` -- a real matched waiver, a
  real stale waiver, AND (the critical fixture) a node firing THREAT003
  for two different CWEs where only one is waived, proving a sub-target A
  waiver never suppresses a sub-target B finding on the same node/rule.
- Negative-path unit coverage: `tests/unit/strata/test_elaborate.py::
  TestElaborateWaivers`, `tests/unit/strata/test_waive.py::
  TestSplitWaiverRule`/`TestValidateWaiverFields`.
