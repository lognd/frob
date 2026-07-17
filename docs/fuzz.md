# frob.fuzz -- enforced property fuzzing with invariant-respecting generators

One sentence: fuzzing stops being optional -- every fuzz-obligated function
must have a property test fed by registered generators that produce only
values satisfying each type's invariants, and a missing generator or
missing fuzz binding is a gate failure, not a code-review hope.

The generator registry is shared infrastructure: the same strategies that
fuzz a function also drive observational clone probing (docs/dup.md R6).

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
   `tests/strategies.py` -- for third-party types you cannot modify.

Anything else is `Err(NoGenerator)` -- and, for obligated signatures, a
FUZZ002 violation naming the type and the three ways to fix it.

Cross-language posture (honest): the registry, gates, and directives are
language-generic; 0.x ships Python execution via hypothesis. Rust maps to
`proptest::Arbitrary`, TypeScript to fast-check arbitraries in
`tests/strategies.ts` -- their runners plug into the same `[[test.runner]]`
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

## Public API

```python
# frob/fuzz/__init__.py
def register(tp: type, strategy: object) -> None
    # Project-level registration hook (imported from tests/strategies.py).
def resolve(tp: type) -> Result[object, FuzzError]
    # Derived -> declared -> registered; Err(NoGenerator) otherwise.
def obligations(snapshot: GraphSnapshot, policy: FuzzPolicy)
        -> tuple[FuzzObligation, ...]
    # Pure: which symbols owe fuzzing under the configured enforce mode.
def stamp_fuzz(root: Path, results: tuple[FuzzResult, ...])
        -> Result[Unit, FuzzError]

class FuzzObligation(BaseModel):  # frozen
    ref: str
    reason: str                   # "invariant INV-007 anchor" | "public"

class FuzzResult(BaseModel):      # frozen
    ref: str
    body_digest: str
    examples: int
    falsified: str | None         # minimal counterexample repr, if found

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

## Dependencies and integration points

- hypothesis (dev dependency), `frob.graph` (anchors, digests),
  `frob.testing` (runner integration, selection), `frob.gates` (FUZZ
  rules), `frob.tickets` (counterexample recording).
- Agents: prover writes the property tests FUZZ001 demands; implementer
  runs `frob test --fuzz` before closing invariant-anchored tickets.
