# frob.fuzz -- enforced property fuzzing with invariant-respecting generators

One sentence: fuzzing stops being optional -- every fuzz-obligated function
must have a property test fed by registered generators that produce only
values satisfying each type's invariants, and a missing generator or
missing fuzz binding is a gate failure, not a code-review hope.

The generator registry is shared infrastructure: the same strategies that
fuzz a function also drive observational clone probing (docs/modules/dup.md R6).
`register`/`resolve` default to a process-global `FuzzRegistry` for the
common single-project case; a caller hosting more than one project in one
process constructs its own `FuzzRegistry()` and passes it explicitly
(T-0469), so registrations never bleed across projects sharing a process.

## The Arbitrary protocol

A type becomes generatable exactly one of three ways (checked in order):

1. **Derived**: pydantic models derive automatically -- field constraints
   become strategy bounds, and generated candidates are round-tripped
   through `model_validate` so custom validators act as the invariant
   filter (rejection sampling with a bounded retry budget; a model whose
   validators reject too often fails loudly with the observed rate).
2. **Declared**: a `__fuzz__()` classmethod returning a hypothesis
   strategy -- the escape hatch for invariants that rejection sampling
   can't hit efficiently (construct-then-repair generators).
3. **Registered**: `frob.fuzz.register(Type, strategy)` in the project's
   <!-- frob:waive DOC006 reason="illustrative downstream-project filename convention, not a path this repo ships" -->`tests/strategies.py` -- for third-party types you cannot modify.

Anything else is `Err(NoGenerator)` -- and, for obligated signatures, a
FUZZ002 violation naming the type and the three ways to fix it.

Cross-language posture (honest): the registry, gates, and directives are
language-generic; 0.x ships Python execution via hypothesis. Rust maps to
`proptest::Arbitrary`, TypeScript to fast-check arbitraries in
<!-- frob:waive DOC006 reason="illustrative downstream-project filename convention, not a path this repo ships" -->`tests/strategies.ts` -- their runners plug into the same `[[test.runner]]`
registry with a `fuzz_command`, but wiring them is recorded work, not
alpha scope.

## Binding and enforcement

A fuzz test binds with the existing DSL: `frob:tests <symref> kind="fuzz"`.

| Rule | Fails when |
|---|---|
| FUZZ001 | fuzz-obligated function has no kind="fuzz" TESTS edge |
| FUZZ002 | a type in a fuzz-obligated signature has no generator by any of the three ways |
| FUZZ003 | fuzz stamp missing or stale (obligated targets changed since the last recorded fuzz run) |

Obligation scope, `frob.toml`:

```toml
[fuzz]
enforce = "invariant-anchored"   # off | invariant-anchored | public
budget_s = 60                    # per frob test --fuzz run
max_reject_rate = 0.99           # derived-generator rejection ceiling
```

`invariant-anchored` (default): every function carrying a `frob:invariant`
anchor is fuzz-obligated -- the things you claim matter are the things that
get fuzzed. `public`: every public function with generatable parameters.
Waivable per-site as always (`frob:waive FUZZ001 reason="..."`).

## Execution and corpus

- `frob test --fuzz [--budget S]` runs the kind="fuzz" bindings (touched-
  set selection applies: only fuzz targets bound to touched symbols run,
  `--all --fuzz` runs everything).
- Corpus per target under `.frob/corpus/<sha-of-symref>/`: hypothesis
  database files, content-addressed by target so renames start fresh and
  stale corpora die with their symbol. The corpus directory is LRU-capped
  (`[fuzz].corpus_entries`) like the dup verdict cache.
- The fuzz stamp (`.frob/fuzz-stamp.json`) records, per target, the body
  digest at the last completed budgeted run -- FUZZ003 compares digests,
  never wall-clock age, so an untouched function never re-obligates.

  <!-- frob:invariant INV-012 -->

## Public API

<!-- frob:describes src/frob/fuzz/_arbitrary.py::register -->
<!-- frob:describes src/frob/fuzz/_arbitrary.py::resolve -->
<!-- frob:describes src/frob/fuzz/_arbitrary.py::FuzzRegistry -->
<!-- frob:describes src/frob/fuzz/_obligations.py::obligations -->
<!-- frob:describes src/frob/fuzz/_stamp.py::stamp_fuzz -->
<!-- frob:describes src/frob/fuzz/_stamp.py::load_fuzz_stamp -->
<!-- frob:describes src/frob/fuzz/_run.py::run_fuzz -->
<!-- frob:describes src/frob/fuzz/_rules.py::FUZZ001 -->
<!-- frob:describes src/frob/fuzz/_rules.py::FUZZ002 -->
<!-- frob:describes src/frob/fuzz/_rules.py::FUZZ003 -->
<!-- frob:describes src/frob/fuzz/_models.py::FuzzEnforce -->
<!-- frob:describes src/frob/fuzz/_models.py::FuzzObligation -->
<!-- frob:describes src/frob/fuzz/_models.py::FuzzResult -->
<!-- frob:describes src/frob/fuzz/_models.py::FuzzPolicy -->
<!-- frob:describes src/frob/fuzz/_models.py::FuzzError -->

```python
# frob/fuzz/__init__.py
def register(tp: type, strategy: object, *, registry: FuzzRegistry | None = None) -> None
    # Project-level registration hook (imported from tests/strategies.py).
def resolve(tp: type, *, registry: FuzzRegistry | None = None) -> Result[object, FuzzError]
    # Derived -> declared -> registered; Err(NoGenerator) otherwise.

class FuzzRegistry:
    # A registered-strategy table scoped to one instance (T-0469); default
    # module-level registry serves the single-project case, multi-project
    # hosts pass their own instance to register()/resolve().
def obligations(snapshot: GraphSnapshot, policy: FuzzPolicy)
        -> tuple[FuzzObligation, ...]
    # Pure: which symbols owe fuzzing under the configured enforce mode.
def stamp_fuzz(root: Path, results: tuple[FuzzResult, ...])
        -> Result[Unit, FuzzError]
    # Writes the digest-per-target fuzz stamp so FUZZ003 can detect staleness.
def load_fuzz_stamp(root: Path) -> dict[str, str] | None
    # Reads the fuzz stamp back; None when absent or unreadable.
def run_fuzz(targets: tuple[type[BaseModel], ...], budget_s: int, ...)
    # Exercises each target's resolved Arbitrary strategy within budget.
def FUZZ001(...) -> tuple[Violation, ...]
    # Flags a fuzz-obligated function with no kind="fuzz" TESTS edge.
def FUZZ002(...) -> tuple[Violation, ...]
    # Flags an obligated signature whose type has no generator.
def FUZZ003(...) -> tuple[Violation, ...]
    # Flags a missing or stale fuzz stamp for an obligated target.

class FuzzEnforce(StrEnum):
    # The `[fuzz].enforce` obligation scope: off | invariant-anchored | public.
    OFF = "off"
    INVARIANT_ANCHORED = "invariant-anchored"
    PUBLIC = "public"

class FuzzObligation(BaseModel):  # frozen
    ref: str
    reason: str                   # "invariant INV-007 anchor" | "public"

class FuzzResult(BaseModel):      # frozen
    ref: str
    body_digest: str
    examples: int
    falsified: str | None         # minimal counterexample repr, if found

class FuzzPolicy(BaseModel):      # frozen
    # The `[fuzz]` table: obligation scope, per-run budget, rejection ceiling.
    enforce: FuzzEnforce
    budget_s: int
    max_reject_rate: float

class FuzzError(ErrorSet):
    NoGenerator   = "Type has no derived, declared, or registered strategy"
    RejectionRate = "Derived generator exceeded max_reject_rate"
    StampFailed   = "Fuzz stamp read/write failed"
```

## Design decisions

- **Rejection sampling first, repair second.** Deriving from pydantic
  validators covers most models with zero authored code; the declared
  classmethod exists precisely for the invariants where rejection is
  hopeless (sorted lists, checksummed ids). The rejection-rate ceiling
  turns "my generator is secretly never producing values" into a loud
  failure instead of a fuzz run that silently tested nothing.
- **Digest-based staleness, not time-based.** Same rule as coverage and
  the lock file: evidence is stale when the code moved, not when the
  calendar did.
- **Invariant-anchored default.** Fuzz-everything-public is available but
  noisy; tying the default obligation to `frob:invariant` anchors keeps
  the mandate aligned with declared criticality and gives the prover
  agent a precise work queue.
- **Counterexamples become failure-log entries.** A falsified property in
  an agent run is recorded on the ticket (`frob ticket fail`) with the
  minimal example, so the reproduction survives the session.

<a id="implementation-notes"></a>

## Implementation notes (T-0002, library slice)

This slice ships `src/frob/fuzz/**` as a standalone library: models,
`resolve`/`register`, `obligations`, `FUZZ001`/`FUZZ002`/`FUZZ003`,
`stamp_fuzz`/`load_fuzz_stamp`, and `run_fuzz`. It does NOT wire the CLI
(`__main__.py`/`config.py`/`app.py`) or `frob.gates.run_gates` -- that is
separate coordinator work on the same ticket, kept out of this change to
avoid merge conflicts on those shared files.

- **`resolve` ordering deviates from the literal 1-2-3 list above.**
  `__fuzz__()` (declared) is checked *before* pydantic derivation, not
  after. The design-decisions section frames the declared classmethod as
  the escape hatch for models "where rejection sampling can't hit
  efficiently" -- if derivation ran first for every `BaseModel`, a
  `__fuzz__()` on such a model would never be consulted, which would
  defeat that stated purpose. Declared generators on non-pydantic types
  are unaffected by the ordering either way.
- **Derived-model rejection sampling uses hypothesis's own retry engine.**
  Each field's strategy is combined into a candidate dict, then
  round-tripped through `model_validate` inside a `hypothesis.strategies.composite`
  strategy that calls `hypothesis.reject()` on a `ValidationError` --
  hypothesis's own bounded-retry/`Unsatisfiable` machinery does the
  "bounded retries, fail loudly if the reject rate is too high" work the
  design section describes, rather than a hand-rolled counter compared
  against `max_reject_rate` at resolve time. `max_reject_rate` in
  `FuzzPolicy` is threaded through as documentation/config surface for the
  coordinator's future wiring; `run_fuzz`'s harness surfaces an
  `Unsatisfiable` failure as `FuzzResult.falsified`, not as a hard `Err`.
- **`obligations()` stays pure per the contract.** Under `enforce="public"`,
  it obligates every public function/method from the `GraphSnapshot` alone
  -- it does NOT filter by per-parameter generatability, since checking
  that would require importing the target module (impure, Python-only).
  That check is FUZZ002's job, run separately over the obligations this
  function returns, fed by `frob.fuzz.resolve_param_types` (best-effort
  dynamic import, `None` on any failure, treated as "skip" not "flag").
- **`run_fuzz` implements only the DERIVED-model round-trip harness.**
  Driving an arbitrary user function's actual property (calling the bound
  `frob:tests kind="fuzz"` test with generated args and checking a real
  assertion) needs `frob.testing`'s selection/execution machinery to find
  and call that bound function -- out of scope for this library slice.
  `run_fuzz(targets: tuple[type[BaseModel], ...], budget_s, ...)` instead
  proves the resolved strategy for each pydantic model target actually
  produces valid instances within budget, which is the real, honest v1
  capability: exercising the Arbitrary protocol's generators, not yet
  exercising project-authored properties.
- **`budget_s` is a real wall-clock cutoff (T-0469).** hypothesis's
  `settings(max_examples=...)` is only a per-batch example ceiling, so
  `run_fuzz` drives hypothesis in small batches (`_BATCH_EXAMPLES` per
  batch) and checks `time.monotonic()` against a `budget_s`-out deadline
  between batches -- the "custom stopping callback" earlier versions of
  this doc called out as missing. A hard `_MAX_TOTAL_EXAMPLES` safety
  ceiling still applies across all batches of one target, independent of
  `budget_s`, so a misconfigured huge budget cannot spin forever.
- **The generator registry is per-`FuzzRegistry`-instance, not hard-coded
  global (T-0469).** `register`/`resolve` default to a process-global
  `FuzzRegistry` instance for the common single-project case; a caller
  hosting more than one project in one process constructs its own
  `FuzzRegistry()` and passes it via the `registry=` keyword to keep
  registrations scoped instead of sharing one process-wide table.
- **hypothesis is an optional import.** Every module that touches it
  guards the import behind `HYPOTHESIS_AVAILABLE`; a worktree without it
  installed still imports `frob.fuzz` cleanly and every hypothesis-backed
  path returns `Err(FuzzError.NoGenerator)` / an empty result instead of
  raising `ImportError`. hypothesis needs to be added to `pyproject.toml`
  (dev or main dependency group, per docs/modules/fuzz.md's own "hypothesis (dev
  dependency)" line) for the resolve/run_fuzz hypothesis paths to do
  anything; `tests/test_fuzz.py`'s hypothesis-backed cases are marked
  `skipif(not HYPOTHESIS_AVAILABLE)` so `pytest` stays green either way.

## Dependencies and integration points

- hypothesis (dev dependency), `frob.graph` (anchors, digests),
  `frob.testing` (runner integration, selection), `frob.gates` (FUZZ
  rules), `frob.tickets` (counterexample recording).
- Agents: prover writes the property tests FUZZ001 demands; implementer
  runs `frob test --fuzz` before closing invariant-anchored tickets.
