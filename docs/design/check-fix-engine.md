# `frob check --fix`: tiered auto-fix engine (T-1137)

One sentence: a single `--fix` flag on `frob check` that mechanically
discharges findings whose remedy is unambiguous (Tier A), verifiably
discharges findings whose remedy needs a re-run to confirm (Tier B), and
for everything else emits a structured, agent-consumable fix-it instead of
touching anything (Tier C) -- never inventing a waiver, never loosening a
threshold.

## Status quo (what already exists)

- `src/frob/gates/_fix_engine.py` (T-1138, done) ships `apply_tier_a_fixes`
  with three handlers: `fix_doc007_dotted_form` (DOC007 directive-form
  rewrite), `fix_doc002_unique_slug` (DOC002 unique-anchor-slug
  correction), `fix_tick002_renumber` (TICK002 draft renumber), plus a
  fourth added later by T-1177, `fix_inv006_carried_waiver` (INV006
  verbatim-split waiver carry -- NOT a new waiver, see anti-goal
  enforcement below). All four are pure Tier-A: each either performs the
  ONE correct rewrite or is a no-op.
- **`apply_tier_a_fixes` has no CLI entry point.** T-1138's own scope note
  says so explicitly: `src/frob/app/check_runner.py` and
  `src/frob/_cli_parsers/_check.py` were out of that ticket's scope.
  Confirmed by grep: no `--fix`/`Fix` reference exists in either file
  today. `frob check --fix` does not exist as a runnable command yet --
  this design (and its child tickets) is what wires it in.
- `frob doctor` (`src/frob/doctor.py`) diagnoses and reports; it does not
  repair anything. Its two surfaces are native-extension importability
  (`NativeExtensionStatus`) and derived-artifact integrity
  (`DERIVED_ARTIFACTS`, drift, stale mutate journals). Every finding it
  produces is read-only and points at a remediation COMMAND
  (`REMEDIATION_HINT`, "re-run `frob mutate`") -- it never edits a file
  itself. See "doctor fold-vs-delegate" below for the resulting scope
  boundary.
- The generated-rule-registry precedent (T-1008/T-1010,
  `src/frob/gates/_rule_id_scan.py`) is the shape this design's fixability
  field reuses: a scanner is the AUTHORITY over a checked-in literal (here
  `_KNOWN_GATE_RULES`), and a drift-lock test re-verifies the literal
  against a fresh scan every run. `src/frob/registry/_staleness.py`'s
  `missing_gate_rule_ids`/`sync_gate_rule_entries` is the second relevant
  precedent: idempotent, sorted, single-batch-bump YAML synthesis
  (REG010's own remedy), directly reusable as the Tier-A handler body for
  "generated-registry regeneration."
- `frob.gates._models.Violation` (the finding object every gate emits)
  already carries `rule`, `severity`, `file`, `line`, `message`, optional
  `symref` (T-0148, exact-symbol waiver precision) and `metric` (T-0289,
  ratchet-aware waiver ceiling). This is enough structure to key a fix
  handler off `rule` and locate the exact site (`file`, `line`) -- no new
  field is needed on `Violation` itself for Tier A/B dispatch. Tier C's
  fix-it emission format (below) is a NEW model, not an extension of
  `Violation`, because a fix-it additionally carries a proposed patch body
  `Violation` has no field for.
- No warm/incremental daemon exists yet (T-0177 is designed, not built;
  `frob serve` is today a stateless FastMCP adapter, `docs/modules/
  serve.md`). "Daemon-warm `--fix`" is therefore a documented future
  integration point, not a mechanism this design can build against
  something real -- see the dedicated section below.

## Fix-handler protocol (per rule id)

One handler = one rule id = one tier. A rule id has EXACTLY one tier at a
time (never "sometimes Tier A, sometimes Tier B" for the same id -- if a
rule's remedy is sometimes ambiguous, the WHOLE rule is Tier B or C, and
the handler internally no-ops on the ambiguous case, exactly as
`fix_doc002_unique_slug` already does for a 0-or-2+-candidate DOC002).

```python
class FixApplied(BaseModel):        # already exists (_fix_engine.py)
    rule: str
    file: str
    line: int
    detail: str                     # one-line human-readable rewrite summary

# Tier A: pure function, filesystem-mutating, no gate/test re-run of its own.
TierAHandler = Callable[[Path, GraphSnapshot, TicketQueue], list[FixApplied]]

# Tier B: same signature PLUS a rollback token; the transaction engine
# (below), not the handler, owns re-run-and-rollback.
class TierBFix(BaseModel):
    rule: str
    file: str
    line: int
    detail: str
    backup: bytes                   # pre-fix byte snapshot of every file it touched
    affected_gates: tuple[str, ...] # gate ids to re-run to verify this ONE fix
    bound_tests: tuple[str, ...]    # frob:tests node ids bound to the touched symbol(s)

TierBHandler = Callable[[Path, GraphSnapshot, TicketQueue], list[TierBFix]]

# Tier C: never mutates. Returns a proposed patch for a human/agent to accept.
class FixIt(BaseModel):
    rule: str
    file: str
    line: int
    message: str                    # the ORIGINAL violation message (remedy embedded, T-0148 precedent)
    proposed_patch: str | None       # unified-diff hunk, or None if no mechanical proposal exists
    reason_unfixable: str            # WHY this is Tier C: "requires judgment", "ambiguous candidate set", etc.

TierCEmitter = Callable[[Path, GraphSnapshot, Violation], FixIt | None]
```

A rule id is registered in exactly one of three tables, each living next
to its tier's engine module:

- `_fix_engine.py`: `TIER_A_HANDLERS: dict[str, TierAHandler]` (today:
  `apply_tier_a_fixes` calls four handlers positionally; the registry
  field ticket below promotes this to an explicit `dict[str, ...]` keyed
  by rule id so the fixability scanner in "fixability registry field" has
  something to introspect by name, not just call in sequence).
- `_fix_engine_tier_b.py` (new): `TIER_B_HANDLERS: dict[str, TierBHandler]`.
- `_fix_engine_tier_c.py` (new): `TIER_C_EMITTERS: dict[str, TierCEmitter]`.

A rule id present in none of the three tables is `manual` -- the fourth
fixability value, meaning "no handler exists, `--fix` does nothing for
this rule, a human resolves it by hand." This is the default for every
new gate rule until someone deliberately writes a handler; it is NOT an
error state, and the fixability registry (below) records it as a real,
correct value rather than an unwired gap -- the whole POINT of the
generated-verified field is that `manual` can never be silently WRONG
(claiming `auto` for a rule with no handler), only honestly absent.

## Transaction / rollback model (Tier B)

Tier B exists because some remedies are semantics-preserving only
CONDITIONALLY on the rest of the tree -- the rewrite itself is mechanical,
but whether it is SAFE depends on state the handler cannot fully see
ahead of time (a release-sync regenerating four artifacts from one
manifest is only correct if the manifest itself was authoritative; a
stale-waiver removal is only correct if the finding it "matches zero" was
observed on a genuinely full, unscoped run, T-1064's own documented
caveat). Tier B's contract: apply, then PROVE, then keep or revert --
never apply-and-hope.

1. **Snapshot.** Before mutating anything, the handler reads and retains
   the pre-fix bytes of every file it is about to touch
   (`TierBFix.backup`). This is a per-fix, in-memory backup -- NOT
   `frob.mutate`'s on-disk crash-safe journal (`_journal.py`); Tier B fixes
   run start-to-finish inside one `frob check --fix` process invocation,
   so there is no cross-process crash window to journal against the way
   `frob mutate` needs to. (If a future Tier B handler needs to survive a
   process crash mid-fix, it becomes a `frob mutate` CALLER internally,
   not a reason to duplicate journal machinery here.)
2. **Apply.** The handler performs its rewrite(s), returning the
   `TierBFix` record (files touched, `affected_gates`, `bound_tests`).
3. **Re-verify.** The transaction engine re-runs exactly
   `affected_gates` (via `frob check --only <gate-ids>`'s own existing
   in-process gate-subset machinery, `_STAGE_GROUPS`/`--only` resolution
   in `check_runner.py`) PLUS every pytest node id in `bound_tests`
   (`frob test`'s own touched-set runner). "Affected gates" is the SAME
   rule id that produced the finding plus any gate the fix engine's own
   author declares depends on the touched file/symbol (e.g. a release-
   sync fix re-runs REL002 AND fmt, since it rewrote four files fmt also
   inspects) -- a fixed, per-handler-declared list, never a guess computed
   at fix time.
4. **Regression check.** "Clean" means: the rule id that produced the
   original finding no longer fires at that site, NO gate in
   `affected_gates` reports a NEW error-severity violation that was not
   present before the fix (compared against the SAME `frob check --delta`
   baseline machinery every other gate already uses, `docs/modules/
   gates.md`'s baseline/`--delta` section), and every `bound_tests` node
   id passes.
5. **Commit or rollback.** Clean -> keep the mutated bytes, record the fix
   in the same `FixApplied`-shaped report Tier A uses (a `TierBFix` that
   survives step 4 is reported identically to a `FixApplied`, so a caller
   never needs to branch on tier to read the output). NOT clean -> restore
   every touched file from `TierBFix.backup` byte-for-byte, and emit a
   `FixRolledBack` record (rule, file, line, `regression_detail`: which
   gate/test newly failed and its own message) -- disclosed, never
   silent. A rolled-back fix is reported as UNFIXED for this run, exactly
   like a Tier C finding would be; `--fix` never retries it automatically
   in the same invocation (retrying blind is the exact anti-pattern
   `frob ticket fail`'s own doc already calls out for a different
   mechanism -- same principle here).

Tier B fixes apply and verify ONE AT A TIME, not batched -- a batch that
rolls back cannot tell which of N fixes caused the regression without
re-running N more times to bisect it, so there is no batching win once
you account for the rollback path; sequential-with-per-fix-verify is both
simpler and never slower than a batch-then-bisect design in the failure
case, and no slower than batching in the success case since the gate/test
re-run cost is paid per rule id either way (Tier A instead re-runs its
handful of affected gates ONCE at the end of the whole batch, because
Tier A fixes are proven semantics-preserving by construction -- there is
nothing to bisect).

## Gate re-run semantics (both tiers, stated precisely)

- **Tier A:** `apply_tier_a_fixes` returns every `FixApplied` across ALL
  four (soon more) handlers in one pass, with no re-run of its own. The
  CLI orchestration layer (the wiring ticket below) then re-runs the
  UNION of every rule id actually fixed, once, in the SAME `--fix`
  invocation, and reports the residual violation count for exactly those
  rules -- this is what acceptance criterion 0's "affected gates re-run
  clean in the same invocation" means concretely. If a residual violation
  remains after re-run (a handler's own no-op branch left something
  behind, or a fix's rewrite collided with a concurrent hand-edit), that
  finding is reported plainly as still-open, not swallowed.
- **Tier B:** re-run is PER FIX, described above -- affected gates plus
  bound tests, before the next Tier B fix in the batch even starts, so a
  regression is caught and rolled back before it can compound with a
  later fix in the same run.
- **Tier C:** never mutates, so there is nothing to re-run; a Tier C
  finding stays exactly as `frob check` (no `--fix`) already reports it,
  with a `FixIt` record additionally emitted (below).

**T-1260 implementation note:** the "CLI orchestration layer" described
above is `frob.app.check_runner._apply_tier_a_and_reverify`, called from
`run` only when `cfg.check_fix` (the `--fix` flag,
`src/frob/_cli_parsers/_check.py`) is set. It loads/builds the graph
snapshot and ticket queue exactly as a normal `frob check` run does, calls
`apply_tier_a_fixes` once, then re-runs the FULL gates stage once (rather
than a per-rule-id gate subset -- the union computed at this v1's
granularity is "the whole gates stage", since Tier A rules span several
different gate families and there is no cheaper reliable way yet to
select just the affected ones) and folds the residual per-fixed-rule
violation count into the `fix_report` it returns. Tier B/C are not wired
here (T-1261+); `fix_report["rolled_back"]`/`["fixits"]` are always `[]`
for now, never a missing key.

`--fix`'s own exit code/summary line reports three counts every run:
fixed (Tier A applied + Tier B committed), rolled-back (Tier B reverted,
with reasons), and fix-its emitted (Tier C, unresolved) -- never a bare
"N fixed" that hides a same-run rollback.

## `frob doctor` fold-vs-delegate decision

**Delegate, do not fold.** `frob doctor` and `frob check --fix` solve
different problems with an easily-confused surface overlap ("frob has a
repair command") and must stay two commands:

- `frob doctor` diagnoses **environment/derived-state** health: is the
  native extension importable, is a `.frob/*.db`/`*-lock.json` artifact
  byte-valid, did a `frob mutate` crash mid-run leaving a source file in
  mutant form. Every one of these is a precondition for `frob check`
  itself to produce TRUSTWORTHY findings at all (T-0570's own module
  docstring: "the doctor-first choke point that catches it before dozens
  of misleading findings follow"). None of it is a GATE FINDING -- there
  is no `rule`/`Violation` object for "the sqlite cache is corrupt," so
  none of it fits the fix-handler protocol above (no rule id to key a
  handler off).
- `frob check --fix` repairs **gate findings** -- `Violation` objects with
  a `rule` id, produced by a check run against SOURCE. It has nothing to
  say about whether the native extension is importable.
- The one point of real overlap: `frob doctor`'s stale-mutate-journal
  report ALREADY names its own remedy command (re-run `frob mutate`) and
  restoring a crashed journal is itself a mechanical, semantics-preserving
  operation (`restore_stale_journals`) -- structurally Tier-A-shaped. This
  is deliberately NOT folded into `--fix` in this design: `frob doctor`'s
  restore path already runs automatically at the START of the next `frob
  mutate` invocation (its own startup check), so there is no live gap to
  close, and pulling doctor's restore into check's fix engine would give
  `--fix` a reason to touch a file `frob check` itself never looked at
  (doctor's targets are not gate findings). If a future doctor surface
  ever DOES need `--fix`-shaped auto-repair with its own rollback, it
  should get there by calling into the SAME Tier-A/B protocol as a THIRD
  caller (alongside `frob check --fix`), not by merging the two commands.
  Not built here; flagged as an open question below, not silently
  dropped.

## Daemon-warm `--fix`

No warm/incremental daemon exists in this codebase today (T-0177 is
DESIGNED, not built -- `docs/audits/perf.md` L11, `frob serve` is a
stateless FastMCP adapter with no persistent graph process). `--fix`
therefore always runs cold: it builds/loads `GraphSnapshot` in-process for
the single invocation, exactly like every other `frob check` path does
today, and pays that cost every time. This design does not build daemon
support -- there is nothing warm to attach to yet. The forward-compatible
seam is narrow and already implied by the handler signatures above: every
`TierAHandler`/`TierBHandler` takes `GraphSnapshot` as a plain argument,
never re-deriving it internally or holding process-global state -- so
WHENEVER T-0177's daemon lands, wiring `--fix` to consume a warm snapshot
instead of a freshly-built one is a change to the CALLER (the CLI
orchestration layer passes in a daemon-supplied snapshot instead of
building one), not to any handler. No handler needs to change. This is
recorded here as the documented integration point the epic's own prompt
asked for, not implemented as a child ticket -- there is no daemon for it
to integrate with yet, and speculatively coding against T-0177's
not-yet-built interface would be exactly the kind of guess this epic's
own anti-goals reject.

## Fixability registry field (generated-verified)

Every known gate rule id gets exactly one fixability value:
`auto` (has a `TIER_A_HANDLERS` entry), `verified` (has a
`TIER_B_HANDLERS` entry), `assisted` (has a `TIER_C_EMITTERS` entry), or
`manual` (none of the three -- the honest default). This mirrors
`_rule_id_scan.py`'s own generated-verified shape exactly: a scanner is
the AUTHORITY, a checked-in literal is the GENERATED artifact, and a
drift-lock test re-verifies the literal against a fresh scan every run.

Concretely:

<!-- frob:waive DOC006 reason="design proposal explicitly marked (new) -- this file has not been built yet, this section describes what a future child ticket should add" -->
- `src/frob/gates/_fixability_scan.py` (new): `generated_fixability() ->
  dict[str, Literal["auto", "verified", "assisted", "manual"]]` -- imports
  `TIER_A_HANDLERS`, `TIER_B_HANDLERS`, `TIER_C_EMITTERS` (the three
  dicts from the protocol section above) and `known_gate_rule_ids()`
  (already exists, `_rule_id_scan.py`), and returns EVERY known rule id
  mapped to whichever of the four values applies. A rule id present in
  more than one table is a hard scanner error (`FixabilityConflict`), not
  a silent last-write-wins -- the "exactly one tier per rule id" rule
  above is enforced here, mechanically, not just by convention.
- `_KNOWN_RULE_FIXABILITY` in `frob.gates.__init__` (or a similarly
  central module): the checked-in literal dict, generated by pasting
  `generated_fixability()`'s output, exactly as `_KNOWN_GATE_RULES` works
  today.
<!-- frob:waive DOC006 reason="design proposal explicitly marked (new) -- this test does not exist yet, this section describes what a future child ticket should add" -->
- `tests/test_gates.py::TestRuleFixability` (new): re-verifies the
  checked-in literal against a fresh `generated_fixability()` call every
  test run -- a maintainer who wires a new Tier A/B/C handler and forgets
  to update the literal fails loud immediately, same drift-lock shape as
  `TestKnownGateRuleIds`.
- This is the concrete mechanism for acceptance criterion 3 ("every rule
  id carries a fixability tier that is generated-verified against the fix
  engine's actual handler table, so an unwired fixability claim is a
  check failure"): "unwired claim" literally cannot exist here, because
  the literal's only source of truth IS the handler tables -- there is no
  path to hand-write `auto` for a rule with no `TIER_A_HANDLERS` entry
  without the drift-lock test catching it on the next run.
- Where it surfaces: `docs/design/registry/check-coverage.yaml`'s
  existing `CHK-GATE-<rule>` entries (T-0560/REG010 precedent) gain a
  `fixability:` field alongside `disposition:`, synthesized the same
  idempotent way `sync_gate_rule_entries` already synthesizes missing
  entries -- reusing that exact function's shape (sorted, single-batch
  total-bump, append-only) rather than inventing a second YAML-mutation
  pattern for what is structurally the same operation.

## Fix-it emission format (Tier C, for agents)

A `FixIt` (protocol section above) is the unit an agent (or a human) acts
on. Emission format, both as an in-process return value and as `--fix
--json`'s external shape:

```json
{
  "rule": "DOC002",
  "file": "docs/modules/gates.md",
  "line": 118,
  "message": "DOC002: anchor '#--fix-tier-a' does not resolve in docs/modules/gates.md (closest: '#--fix-tier-a-deterministic-auto-fix-handlers-t-1138', '#--fix-tier-b-transactions')",
  "proposed_patch": null,
  "reason_unfixable": "2 candidates at or above the fuzzy-match cutoff -- ambiguous, never guessed"
}
```

- `message` is always the ORIGINAL violation message verbatim (every
  gate message already embeds its own remedy, per this repo's existing
  convention, `_models.py`'s `Violation` docstring) -- a `FixIt` never
  paraphrases or drops that text, only adds structure around it.
- `proposed_patch`, when present, is a unified-diff hunk an agent can
  apply directly (`git apply`) or read as a suggestion; `null` when no
  mechanical proposal exists at all (the emitter can name WHY it is Tier
  C but genuinely has no candidate rewrite to propose -- this is common
  and not a bug, e.g. a bare `TODO001` finding with no ticket to bind to
  yet).
- `reason_unfixable` is mandatory, non-empty, free text -- the same
  "always disclose why," never-silent posture this repo's waiver
  discipline (`WAIVE001`, reason required) already enforces elsewhere,
  applied to "why didn't `--fix` touch this" instead of "why is this
  waived."
- A batch of `FixIt`s is a flat JSON array under `--fix --json`'s
  existing `fixits` key (sibling to the existing `--json` violations
  array `frob check --json` already emits) -- no new top-level command,
  no new output mode; `--fix` is additive to `frob check`'s existing
  reporting shape, not a parallel one.

## The two anti-goals, as enforced invariants

**No auto-waivers, ever.** Enforced by construction, not by convention:
no fix-handler signature in the protocol above returns anything that
writes a `frob:waive` comment, and the ONE existing handler that touches
waiver text at all (`fix_inv006_carried_waiver`) is explicitly NOT "auto-
waiving" in the sense this anti-goal means -- it carries an EXISTING
human-authored disposition verbatim from a source site to a destination
site created by a code split, never synthesizing a NEW judgment call (its
own docstring states this precisely, and `_fix_inv006_carried_waiver_for_
file`'s `kind != "waiver"` guard refuses to act on anything but an actual
prior waiver). `WAIVE002` (a waiver whose rule id can never match) and
`WAIVE004` (a waiver matching zero findings on a full run) are the gates
that would catch a hypothetical auto-waiver ever slipping in: any fix
handler that inserted a NEW `frob:waive` line for a rule it did not also
prove already had a genuine prior disposition would either immediately
trip `WAIVE004` (nothing to match, since the "finding" the waiver claims
to suppress was fabricated by the same fix) or be structurally
indistinguishable from hand-editing a waiver in, which code review (not a
gate) is the backstop for. The design-level enforcement is: this
protocol's own type signatures have no return path that produces a waiver
directive except the one, audited, carry-only exception.

**No threshold loosening, ever.** Enforced the same way "regression"
is defined in the Tier B transaction model above: step 4's "clean" check
compares against the EXISTING baseline/ratchet machinery
(`frob check --delta`, and for ratchet-backed rules specifically
`frob.gates._ratchet`'s own ceiling state) -- a fix is never permitted to
raise a ratchet ceiling, widen a `metric`-gated waiver's `ceiling=N`
(T-0289), or touch `frob.toml`'s `[gates.severity]` dial as a SIDE EFFECT
of "fixing" something. No handler in the protocol above accepts
`frob.toml` or the ratchet state file as a target it may write -- their
`Path` arguments are always the graph root for locating SOURCE files, not
a config-mutation handle. `REL001`/`REL002`'s own coherence checks (never
suppressed by `--fix`, since they are not in any handler table until this
epic explicitly wires a release-sync Tier-A handler that REGENERATES the
version quartet FROM the single manifest -- it never edits the manifest
itself, only the three derived artifacts) are the concrete existing gate
that would catch a hypothetical threshold-loosening attempt through the
release-version path specifically.

## Open questions (not guessed, disclosed)

1. Should `frob doctor` eventually gain its OWN `--repair` flag that calls
   into this same Tier-A/B protocol as a third caller (for e.g. clearing a
   corrupt derived-state cache file, which is safely regenerable)? Not
   decided here -- flagged for a future ticket if doctor's read-only
   posture ever becomes a real friction point, not built speculatively.
2. Tier B's per-fix sequential re-run cost (gate + bound-test re-run per
   fix, not batched) could be slow on a finding set with many Tier B
   candidates in one run. No child ticket files a perf mitigation for
   this pre-emptively -- correctness (never batching past what can be
   individually rolled back) is prioritized over speed for a v1; revisit
   only if a real `--fix` run measures this as a bottleneck.
3. Whether `fixability:` belongs in `check-coverage.yaml`'s
   `CHK-GATE-<rule>` entries (this design's choice) versus a wholly
   separate registry file is a naming/placement call, not a design
   uncertainty -- reusing the existing REG010 entry is preferred because
   it is already the per-rule-id home this repo maintains, but the child
   ticket implementing it should confirm the YAML shape reads cleanly
   before committing to it.
</content>
