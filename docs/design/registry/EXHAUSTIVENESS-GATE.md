# Registry exhaustiveness drift-lock (T-0343)

The unified design-knowledge registry (`docs/design/registry/*.yaml`,
README.md's "Unified design-knowledge registry") was built and documented
as a machine-readable, enforced catalog, but was in fact read by ZERO
code -- catalogued, not enforced, with no gate watching the gap. This is
the fix: `frob.gates._registry_exhaustiveness.registry_gate`, wired into
`frob check` at ERROR severity as the `registry` gate, family `REG001`-
`REG005`.

## Unified model (T-0407)

Parsing (YAML loading, entry shape, the disposition grammar) lives in
exactly one place: `frob.registry._models` (`RegistryEntry`, `Disposition`,
`DispositionKind`, `load_registry_dir`, `audit_registry_file`). Before
T-0407 this parsing was duplicated inline inside
`frob.gates._registry_exhaustiveness` -- correct, but a second registry
consumer (T-0424's reflexive check-coverage registry) would either
duplicate that parser again or reach into a gate-internal module as if it
were a library. `registry_gate` now calls into `frob.registry` and is
purely the POLICY layer: which `DispositionKind` earns which `Violation`,
verified against live state.

T-0407 also closes two early-exit/partial-coverage holes the
pre-unification gate silently allowed:

- **REG006** -- a list item under `entries:`/`*_entries:` that is not a
  mapping, or has no string `id`, is now a loud violation instead of a
  silent `continue`. Pre-T-0407 such an item vanished from every count
  with no trace -- exactly the "enumerate a universe, then drop part of
  it silently" shape T-0407 exists to close.
- **REG007** -- the same `id` string defined by two or more entries
  anywhere in the loaded registry (a real collision, distinct from an
  intentional `duplicate_of:` reference, which REG004 already governs).
  Pre-T-0407 the cross-file id index silently kept only the last-seen
  entry for a collided id.

`frob registry audit` (also T-0407) reports the per-file `RegistryAudit`
accounting -- `handled`/`deferred`/`duplicate`/`out_of_scope`/
`unaccounted`/`malformed` counts against `total` -- so "is this registry
exhausted" is a one-line honest read, not a re-derivation from the raw
violation list.

## Disposition grammar

Every entry's `disposition:` string is parsed and VERIFIED, never taken
at face value:

- `handled_by:<rule-id>` -- `<rule-id>` must name a rule this build's own
  gate/policy rule registry actually knows about (checked against the
  live `frob.gates._KNOWN_GATE_RULES | policy rule ids` union at call
  time, never a hardcoded snapshot). A dangling reference is `REG002`.
- `deferred:<ticket-id>` -- `<ticket-id>` must resolve to a ticket that
  is not `done`/`dropped`. A deferral to a closed or nonexistent ticket
  is `REG003`.
- `duplicate_of:<id>` / `duplicate-of:<id>` -- `<id>` must resolve to a
  real entry id somewhere in the registry. A dangling duplicate
  reference is `REG004`.
- `out_of_scope:<reason>` / `out-of-scope:<reason>` /
  `out-of-scope(<reason>)` -- `REG001` (ERROR) if `<reason>` is empty.
  `<reason>` is additionally routed through `REG011` (WARN, T-0680, see
  below) -- the same `caught_by` verification T-0382 built for `strata`'s
  `OutOfScopeEntry`/`BenignCapability`/`OutOfScopeRegulation` models.
- anything else -- missing, `pending`, or a bare `addressed` with no
  `handled_by` attached -- is `REG001`, undispositioned. A bare
  `addressed` claim with nothing backing it is deliberately treated as
  undispositioned, not accepted at face value.

## REG004 (also): documented splits

`RECONCILIATION.md` finding (b) names real-world concepts split across
multiple, currently-unlinked registry ids. Any backtick-quoted registry
id that table names is required to carry a non-empty `cross_refs` list;
an id still showing `cross_refs: []` despite being a documented split
fails `REG004`.

## REG005: declared-total drift

A registry file may declare a `total:` (or, for a split entry-list key
like `weaknesses.yaml`'s `cwe_entries`, a `<prefix>_total:`) alongside its
`entries:` list. If declared, it must equal the actual entry count -- a
silent future add/drop without updating the denominator fails `REG005`.
Files/lists with no declared total are not checked.

## REG010 (gate rule staleness, T-0560)

T-0424 built `check-coverage.yaml` (the reflexive registry: one
`CHK-GATE-<rule>` entry per rule `known_gate_rule_ids()` reports live) but
only as a one-time seed -- nothing kept it in sync as new rules landed.
T-0560 is the CONTINUOUS half: `REG010` (WARN) fires the moment a live
rule has no corresponding `CHK-GATE-<rule>` entry in `check-coverage.yaml`,
caught by the very next `frob check` rather than depending on someone
remembering to re-audit.

A genuinely SCHEDULED daemon was considered for this and rejected as
dishonest scope: this repo has no always-on process host, and a cron-style
runner needs its own supervision/alerting this pass does not build. The
gate above is the honest substitute -- it fires on every single `frob
check` invocation, which happens far more often than any schedule this
project could actually operate, so "found before the user notices" is
satisfied without inventing infrastructure. `frob registry audit
--sync-gate-rules` (`frob.registry._staleness.sync_gate_rule_entries`) is
the auto-file mechanism: it appends one `handled_by:<rule>` entry per
missing rule (self-referentially dispositioned -- "this rule is live" IS
the verification, not a claim needing later review) and keeps
`gate_rule_total` in lockstep, so a human or a CI step can clear REG010's
finding with one command whenever it fires.

`sync_gate_rule_entries`'s own `check-coverage.yaml` rewrite is crash-safe
(T-1359): it now writes via `frob.tickets._store.atomic_write` (temp file
+ `fsync` + `os.replace`) instead of a bare `Path.write_text`, so a land
killed mid-REG010-autofix leaves the previous `check-coverage.yaml`
intact rather than half-written -- the same hazard class T-1348 already
closed for `frob.gates._fix_engine`'s direct writes.

<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_sync_gate_rules_for_land -->

T-1011: `frob ticket land` now runs this same sync AUTOMATICALLY, not just
on request -- `_sync_gate_rules_for_land` (`ticket_runner.py`, wired as
`land()`'s `sync_gate_rules` callback, `src/frob/tickets/_land.py`) diffs
the landing worktree's own `_KNOWN_GATE_RULES` change against the squash-
applied tree right after the REL001 bump is staged; if the diff touched
`_KNOWN_GATE_RULES` (unaffected by T-1069's unrelated `tier` dispatch-table
addition to `ticket_runner.run`, which merely added a new `frob ticket
tier` verb alongside the existing `priority`/`kind`/`component`/`sprint`
mutators), it scans root's on-disk tree (never a live import --
`frob.gates._rule_id_scan.generated_gate_rule_ids`, the T-0964 scanner) and
stages any newly-missing `check-coverage.yaml` rows into the SAME land
commit. This ends the manual re-sync docs/audits/coordination-churn.md
disclosed drifting twice in one drive -- a landed gate-rule change can no
longer outrun `check-coverage.yaml` at all, closing REG010's remaining gap
between "caught at the next `frob check`" and "never drifts to begin
with".

## REG011 out-of-scope caught_by (T-0680)

T-0343's original gate left one named gap: an `out_of_scope:<reason>`
disposition was accepted the moment `<reason>` was non-empty, with no
check that the excuse actually named anything real. T-0382 built exactly
that verification (`strata._threat._check_caught_by_integrity` /
`strata._compliance._check_regulation_caught_by_integrity`, THREAT006 /
COMPLIANCE004) for `strata`'s own `OutOfScopeEntry`/`BenignCapability`/
`OutOfScopeRegulation` model objects -- but the registry-YAML
`out_of_scope:<reason>` surface is a separate string, parsed by
`frob.registry._models`, that never passed through it. `REG011` closes
that gap by reusing the SAME token-resolution helper T-0382 built
(`frob.strata._threat._caught_by_unresolved_tokens`, no duplicated
regex/logic):

- `<reason>` must either (a) name a real, live catching control -- a
  rule-id-shaped token (e.g. `PII010`) or a CWE-id-shaped token (e.g.
  `CWE-78`) that resolves against this run's live gate-rule-id set /
  `strata`'s CWE catalog -- or (b) be a SUBSTANTIVE
  `"none -- <explanation>"` reasoned-none disclosure (the bare word
  `"none"` alone, with no explanation after it, does not count).
- A reason naming no catching control at all, and not a substantive
  reasoned-none, is `REG011` ("unaccountable excuse").
- A reason naming a control that does not actually resolve (a typo'd or
  fabricated rule/CWE id) is also `REG011` ("references unknown
  control(s)").

`REG011` is WARN, not ERROR, matching `REG008`/`REG009`'s first-turn-on
precedent: this repo's registry carries hundreds of pre-existing
`out_of_scope` entries (`patterns.yaml`'s `advisory-design-pattern-
recommendation` entries, `compliance.yaml`'s `organizational/process
control` entries, and others) written before this check existed --
promoting to ERROR immediately would red the build on old debt, not catch
future drift. Driving it green is a future reconciliation pass, same
posture as REG001-007's own `T-0384..T-0392` lineage, not this ticket's
job.

## REG012: adopted-then-deleted registry (T-0894)

T-0343's original missing-directory posture ("no `docs/design/registry/`
at all means no claim, not a violation") could not tell a repo that never
adopted the registry from one that adopted it and then LOST it -- whether
by accident or by a compliance/security-load-bearing-artifact removal
attack. Both silently returned an empty violation tuple, clearing every
finding the registry existing would have produced, with no other gate in
the catalog watching for the deletion itself.

`registry_gate` now checks `frob.gates._registry_exhaustiveness.
path_ever_tracked(repo_root, rel_path)` before returning empty on a
missing directory: `git log -1 -- <rel_path>` against `HEAD` tells whether
the path was ever committed on this branch's history, independent of its
current working-tree state. A directory with no such history is the
ordinary never-adopted case (still silent). A directory that WAS committed
and is now gone fires `REG012` at `Severity.ERROR`, and `REG012` is in
`_UNWAIVABLE_RULES` -- deleting the whole registry is a higher-stakes
claim than any individual undispositioned entry, so it gets no waiver
escape hatch.

The same `path_ever_tracked` signal backs the two sibling instances of
this exact posture T-0894 also closed: `compliance_gate`'s `COMPLIANCE006`
(a deleted `compliance.yaml`) and `decisions_gate`'s `DEC003` (a deleted
`decisions/` directory) -- see `docs/modules/gates.md#compliance005-t-0788`
and `docs/modules/decisions.md#the-dec-gates` respectively. T-1159: both
gates now live in `src/frob/gates/_decisions_compliance.py` (split out of
`frob.gates.__init__` verbatim, re-exported from `frob.gates` unchanged),
not `frob.gates.__init__` directly.

## COMPLIANCE005/COMPLIANCE007: compliance registry vs. model checking (T-1244)

`compliance_gate` (`frob.gates._decisions_compliance`) has two rules, and
it is important to be precise about what each one does and does NOT
prove, because they are easy to conflate:

- **COMPLIANCE005** verifies that every `CMPL_REGISTRY_UNIT_IDS` member
  present in `docs/design/registry/compliance.yaml` carries a NON-
  deferred, non-undispositioned `handled_by:<rule>`/`out_of_scope:<reason>`
  disposition STRING. This is purely a registry-hygiene check -- it says
  nothing about whether the named rule actually enforces anything for
  that specific framework. In particular, 16 of the 17 units carry the
  self-referential `handled_by:COMPLIANCE005` -- i.e. "this framework's
  disposition is handled by the check that verifies a disposition string
  exists", which is circular and proves nothing about real per-framework
  coverage.
- **COMPLIANCE007** (T-1244) closes that gap for the specific vacuous
  shape: it flags any `_CMPL_UNIT_TRIAGE_TICKET` member whose disposition
  is still the self-referential `handled_by:COMPLIANCE005`, naming the
  open triage ticket (T-1245-T-1249) that owns re-dispositioning it
  against a real `RegulationEntry`/mitigation/attestation. `CMPL-FROB-
  CATALOG-ENTRIES` is the one exception -- it is a meta-row counting
  `COMPLIANCE_CATALOG`'s own real entries, so its self-reference is
  genuine, not vacuous (T-1250 confirms this explicitly). COMPLIANCE007
  is deliberately WARN-tier, not ERROR: re-dispositioning each of the 16
  flagged rows is a per-framework classification decision the sibling
  triage tickets own, not a code bug this check fixes -- as of this
  writing it fires on all 16, an honest, currently-open finding, not a
  regression to silence.

Neither COMPLIANCE005 nor COMPLIANCE007 verifies against a real strata
MODEL at all -- both are pure `compliance.yaml` registry-string checks,
running in a few milliseconds regardless of whether the target repo has
any `.strata` design file. The actual model-driven check --
`frob.strata._compliance.evaluate_compliance(model, view, ...)`, which
proves a specific `KernelModel` instance discharges each fired regulatory
obligation (COPPA/GDPR/HIPAA/PRIVACY-NOTICE/etc, T-1242) -- was, until
T-1314, invoked only through the separate, explicit `frob sys audit
<design-file>` command (`frob.strata._audit.evaluate_exhaustiveness`,
`_compliance_pii_lint_fingerprint_gaps`), never wired into `frob check`'s
automatic gate pipeline (T-1244's own investigation confirmed no code
path called `evaluate_compliance` from `frob check` at the time). That
was exactly the "catalogued but check-invisible" divergence class this
whole gate exists to refuse -- a green `frob check` making no claim at
all about whether the repo's own strata model actually discharges its
regulatory obligations, with nothing structurally blocking a land that
reddened that model undisclosed.

T-1314 closes this: `frob.gates.sys_gate` now also runs `evaluate_
compliance` per discovered `.strata` model (opt-in behind the SAME
`design/` directory precondition every other `sys_gate` sub-check
already requires -- a repo with no `.strata` corpus pays nothing new),
folded into SELFAUDIT001 (docs/modules/gates.md#self-audit-at-land-selfaudit001-t-0756)
alongside self-conformance/resource-contention/mode-conformance/
reliability, at WARN tier (see that section for the tier rationale). A
green `frob check` now DOES make a claim about the repo's own strata
model's compliance posture -- WARN, not silence -- closing the green-
check-red-audit divergence for this family the same way T-0756 already
closed it for the other five; `frob sys audit` remains the tool for a
deliberate, human-driven deep-dive, but its own findings are no longer
invisible to `frob check`.

## Honest first-turn-on state

On first turn-on this gate is RED for the ~1950 entries the registry
carries today (the great majority `pending`, `addressed` with nothing
backing it, or a legacy CWE `duplicate-of`/`out-of-scope` disposition
that predates and does not yet match this grammar). That red is the
honest current state of the corpus, not a bug in the gate -- it is
driven green only by the per-registry reconciliation tickets
(T-0384..T-0392 doing the real per-entry disposition work), never by
suppressing or bulk-waiving this gate.
