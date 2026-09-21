# frob.gates._registry -- gate registration interface (T-4661)

One sentence: a detector declares itself once, in one module, and the
job list, the known-rule-id set, the doc rule table, and the
check-coverage entries are all DERIVED views over that declaration --
adding a detector becomes a one-file change instead of four hand-edits.

## The problem this closes

Before this leaf, wiring a new gate detector into `frob check` meant
touching four separate, independently hand-maintained places:

1. the job list (`frob.gates.__init__`'s `_ALL_GATES`,
   `_CANONICAL_GATE_ORDER`, `_GATE_STAGE_GROUPS`),
2. the rule-id registry (`frob.gates._waive._KNOWN_GATE_RULES`),
3. the rule table in `docs/modules/gates.md`,
4. the `gate_rule_entries` in `docs/design/registry/check-coverage.yaml`.

All four live in shared, whole-file lease hotspots, so two gate
tickets could never run concurrently, and a finished detector could sit
unwired for weeks waiting for a lease to free up. Measured, in the week
this leaf was filed: TESTMOCK001 (T-3997), RACE001/RACE002 (T-3953),
SYS118 (T-3964), COV010 (T-4230), and SYS116/SYS117 (T-4612) each
shipped UNWIRED because `gates/__init__.py` and `_waive.py` were leased
by other in-progress tickets -- spawning the T-4647/T-4605 fold-in
tickets purely to wire already-finished work in after the fact.

## The registration interface

`frob.gates._registry.register_gate()` (or the `@gate(...)` decorator
form) is the one place a detector declares:

- `job` -- the job name, matching `_ALL_GATES`'s existing naming.
- `rule_ids` -- every rule id the job can emit.
- `stage_groups` -- which `frob check --only <group>` group(s)
  (`gates-fast`/`gates-native`/`gates-security`) the job runs under.
- `severity` -- the job's default `frob.gates._models.Severity`.
- `reads` -- the files the job reads (for SELFAUDIT001/`via`
  bookkeeping).

Registration is refused, never silently overwritten, on a duplicate
job name (`RegistryError.DuplicateJob`) or a rule id already claimed by
a DIFFERENT job (`RegistryError.DuplicateRuleId`) -- the exact
conflict shapes a single flat `frozenset` literal could never detect,
because a set has no notion of "owner".

## The four derived views

| View | Function | Replaces |
|---|---|---|
| Job list | `derive_job_names()` | `_ALL_GATES` |
| Known-rule-id set | `derive_known_rule_ids()` | `_KNOWN_GATE_RULES` |
| Doc rule table | `derive_doc_rule_table()` | the `gates.md` enumeration |
| Check-coverage entries | `derive_check_coverage_entries()` | `check-coverage.yaml`'s `gate_rule_entries` |

`find_unregistered_live_rule_ids()` is the GATERULE001-shaped
completeness check sourced from this registry: given an injected
candidate-scan callable (kept as an injected callable, not a direct
import of `frob.gates._rule_id_scan`, so this module stays independent
of that module's own leased neighbors), it reports every rule id live
in source but absent from `derive_known_rule_ids()` -- the same
"detected but not silently accepted" contract the legacy scan already
enforces.

## Migration posture (this leaf's own scope boundary)

This leaf builds the registry and proves the derivation is sound. It
does NOT migrate every existing hand-maintained gate to call
`register_gate()` itself -- that would touch `gates/__init__.py` and
`_waive.py`, both leased by concurrent tickets at filing time (see the
Done report for the exact lease snapshot). Instead, `seed_legacy_bulk()`
registers the CURRENT hand-maintained job set and rule-id set as one
bulk `"legacy"` entry, so `derive_job_names()` and
`derive_known_rule_ids()` already equal today's `_ALL_GATES`/
`_KNOWN_GATE_RULES` byte-for-byte (`tests/unit/test_gate_registry.py::
TestDerivedViewsMatchLegacyExactly`).

A NEW detector never touches the legacy bulk entry: it calls
`register_gate()` directly and immediately appears in all four derived
views, with zero edits to `gates/__init__.py`, `_waive.py`, `gates.md`,
or `check-coverage.yaml`. This is proven directly by
`tests/unit/test_gate_registry.py::TestAddingADetectorTouchesOneFile::
test_adding_a_detector_touches_one_file`, which registers a fake
detector (`FAKE_T4661_001`) through the registry alone and asserts it
appears in the derived job list, known-rule-id set, and check-coverage
view, while asserting the fake id was never written into either
hotspot source file.

Migrating each existing gate module off the bulk entry one detector at
a time (T-4647 and friends), and opening registration to a consumer
repo's own rule ids -- today `_KNOWN_GATE_RULES` is a closed frozenset
frob's own ids only (T-3854) -- are follow-up leaves that become
one-file changes precisely because this registry now exists.

## Reference

### RegistryError

`frob.gates._registry.RegistryError` -- fallible outcomes of
`register_gate`: `DuplicateJob`, `DuplicateRuleId`, `EmptyRuleIds`.

### GateRegistration

`frob.gates._registry.GateRegistration` -- one detector's stored
declaration (`job`, `rule_ids`, `stage_groups`, `severity`, `reads`),
the record every derived view reads from.

### register_gate

`frob.gates._registry.register_gate()` -- registers one detector job,
returning a `Result[GateRegistration, RegistryError]`. See "The
registration interface" above.

### gate

`frob.gates._registry.gate()` -- the `@gate(...)` decorator form of
`register_gate`, for use directly above a detector function at module
import time. Raises `RuntimeError` on a registration conflict, since a
decorator has no caller to hand a `Result` back to.

### seed_legacy_bulk

`frob.gates._registry.seed_legacy_bulk()` -- the one-time legacy
baseline seed described in "Migration posture" above. Idempotent for
identical arguments; refuses a second call with different data.

### reset_registry_for_tests

`frob.gates._registry.reset_registry_for_tests()` -- test-only escape
hatch clearing the process-wide registry table between test cases.

### derive_job_names

`frob.gates._registry.derive_job_names()` -- the job-list derived view.
See "The four derived views" above.

### derive_known_rule_ids

`frob.gates._registry.derive_known_rule_ids()` -- the known-rule-id-set
derived view, `_KNOWN_GATE_RULES`'s direct successor.

### CheckCoverageEntry

`frob.gates._registry.CheckCoverageEntry` -- one derived
`check-coverage.yaml` `gate_rule_entries` row (`id`, `disposition`,
`name`).

### derive_check_coverage_entries

`frob.gates._registry.derive_check_coverage_entries()` -- the
check-coverage.yaml derived view: one `CheckCoverageEntry` per known
rule id.

### derive_doc_rule_table

`frob.gates._registry.derive_doc_rule_table()` -- the doc rule table
derived view: every known rule id, sorted.

### find_unregistered_live_rule_ids

`frob.gates._registry.find_unregistered_live_rule_ids()` -- the
GATERULE001-shaped completeness check described in "The four derived
views" above, sourced from this registry instead of a second
hand-maintained literal.

## Wiring status

As of this leaf, `frob.gates.__init__`'s job list and
`frob.gates._waive._KNOWN_GATE_RULES` are NOT yet re-pointed at this
registry's derived views (that edit is `gates/__init__.py`/`_waive.py`
territory, both leased by other in-progress tickets at filing time --
see the Done report's disclosure). `frob.gates._registry` today stands
alongside the legacy lists, proven equivalent by test, ready for the
one-line wiring hunk T-4647 already tracks.
