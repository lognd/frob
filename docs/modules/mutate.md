# frob.mutate -- mutation testing (the honest quality oracle)

One sentence: `frob mutate` perturbs a file's source with small semantic
mutations (flip a comparison, swap an operator, negate a boolean), runs the
tests against each mutant, and reports which SURVIVED -- a survivor is a
behavior change no test caught, i.e. a real gap the coverage and case-count
gates only approximate.

<!-- frob:describes src/frob/mutate/__init__.py::run_mutations -->
```bash
frob mutate src/pkg/m.py                       # default: uv run pytest -q
frob mutate src/pkg/m.py -- python -m pytest -q tests/test_m.py
frob mutate src/pkg/m.py --json
```

Output is the mutation score (killed / total) and a list of survivors with
their file:line and what was mutated. Exit 1 when any mutant survived, so a
weak suite fails CI.

## Why it matters

TEST002 counts cases and TEST005 measures coverage, but both are gameable:
an assert-free test executes the code (100% coverage) and adds a case while
verifying nothing. Mutation testing cannot be gamed that way -- a test that
does not assert the result kills no mutant, so the score collapses to the
truth. It is the quality oracle docs/modules/fuzz.md and the TEST family point at.

## Public API

<!-- frob:describes src/frob/mutate/__init__.py::MutateError -->
<!-- frob:describes src/frob/mutate/__init__.py::Mutant -->
<!-- frob:describes src/frob/mutate/__init__.py::MutationResult -->
<!-- frob:describes src/frob/mutate/__init__.py::MutationResult.score -->
<!-- frob:describes src/frob/mutate/__init__.py::_Mutator.visit_Compare -->
<!-- frob:describes src/frob/mutate/__init__.py::_Mutator.visit_BinOp -->
<!-- frob:describes src/frob/mutate/__init__.py::_Mutator.visit_BoolOp -->
<!-- frob:describes src/frob/mutate/__init__.py::_Mutator.visit_Constant -->
<!-- frob:describes src/frob/mutate/__init__.py::generate_mutants -->
<!-- frob:describes src/frob/mutate/__init__.py::run_mutations -->

```python
class MutateError(ErrorSet)      # fallible outcomes: ParseFailed, NoSource
class Mutant(BaseModel)          # one applied mutation: file, line, description
class MutationResult(BaseModel)  # outcome of testing one function's mutants
    score -> float               # killed / total (1.0 when total == 0)

# ast.NodeTransformer hooks; each applies at most one point mutation, chosen
# by a running counter, and leaves every other visited node untouched.
def _Mutator.visit_Compare(node) -> ast.Compare  # maybe swap the comparison op
def _Mutator.visit_BinOp(node) -> ast.BinOp      # maybe swap the arithmetic op
def _Mutator.visit_BoolOp(node) -> ast.BoolOp    # maybe swap and/or
def _Mutator.visit_Constant(node) -> ast.Constant  # maybe negate a bool literal

def generate_mutants(source, file, line_ranges=None) -> Result[tuple[Mutant, ...], MutateError]
def run_mutations(root, file, test_argv, timeout_s=300.0, max_mutants=None, line_ranges=None) -> Result[MutationResult, MutateError]

MUTATION_RUN_ENV = "FROB_MUTATION_RUN"  # set to "1" in every spawned test process
```

`max_mutants` caps how many mutation points are explored (first N in
source order, deterministic); `line_ranges` restricts points to the given
inclusive `(start, end)` line spans -- TEST016 (T-0755) uses both to keep
its diff-scoped pass bounded and anchored to the diff's own changed lines.

Every test process `run_mutations` spawns gets `MUTATION_RUN_ENV=1` in its
environment. This is the recursion guard for self-referential evidence: a
test that itself invokes the mutation harness against the real repo (the
TEST016 self-check) must skip when it sees the sentinel, otherwise each
mutant run re-enters the harness and the suite forks without bound.

## v1 scope (honest)

- Python source, mutated via a small AST transformer: comparison swaps
  (`<`<->`>=`, `==`<->`!=`), arithmetic swaps (`+`<->`-`, `*`<->`//`),
  boolean-operator swaps (`and`<->`or`), and boolean-constant negation.
- One mutation per run; the file is restored after every mutant and on any
  error via a `finally`, so a crashed run that reaches Python-level error
  handling never leaves mutated source behind.

  <!-- frob:invariant INV-017 -->
- A mutant that hangs the tests past the timeout counts as killed.
- Other languages and a MUT gate (a mutation-score floor on
  invariant-anchored symbols) are recorded follow-on work.

## Crash-safe backup journal (T-0857)

<!-- frob:describes src/frob/mutate/_journal.py::write_journal -->
<!-- frob:describes src/frob/mutate/_journal.py::restore_stale_journals -->
<!-- frob:describes src/frob/mutate/_journal.py::list_stale_journals -->
<!-- frob:describes src/frob/mutate/_journal.py::remove_journal -->
<!-- frob:describes src/frob/mutate/_journal.py::JournalError -->
<!-- frob:describes src/frob/mutate/_journal.py::MutationJournalEntry -->
<!-- frob:describes src/frob/mutate/_journal.py::StaleJournal -->

The `finally`-based restore above does not survive a KILLED process --
a `SIGKILL`, an OOM kill, or the T-0755 fork-bomb scenario never reaches
Python's `finally` at all, so the target file was found sitting in mutant
form (the last `ast.unparse` output) with the true content nowhere on
disk. The T-0755 fork-bomb recovery had to reconstruct the original by
hand from git plus reapplied uncommitted edits.

T-0857 closes that gap with a journal:

<!-- frob:describes src/frob/mutate/_journal.py::write_journal -->
```python
from frob.mutate._journal import (
    JournalError,
    MutationJournalEntry,
    StaleJournal,
    write_journal,
    remove_journal,
    list_stale_journals,
    restore_stale_journals,
)
```

- `JournalError` -- fallible outcomes: `Collision`.
- `MutationJournalEntry` -- one target's pre-mutation bytes, persisted.
- `StaleJournal` -- a journal found on disk, needing restore.
- `write_journal` -- journal `original` bytes before mutating.
- `remove_journal` -- drop the journal after a successful restore.
- `list_stale_journals` -- read-only report (`frob doctor`'s view).
- `restore_stale_journals` -- restore + remove every stale journal on disk.

`run_mutations` now:

1. Calls `restore_stale_journals(root)` FIRST, before generating or
   applying any mutant -- a journal left by a PRIOR crashed run is put
   back before this run touches anything, logged loudly at WARNING.
2. Calls `write_journal(root, target, original_bytes)` with the target's
   raw bytes BEFORE the first mutant write. The journal file itself is
   written atomically (temp file + `os.replace`) so a crash mid-journal-
   write never leaves a half-written journal mistaken for a valid one.
3. Restores from `original_bytes` (not a re-read of the journal) and
   calls `remove_journal` in the `finally`, same as before T-0857 -- the
   journal is redundant bookkeeping on the normal-exit path, only load-
   bearing when that `finally` never runs.

Journal files live under `.frob/mutate-backup/` (already covered by the
repo's blanket `.frob/` gitignore entry), one file per target, keyed by a
hash of the target's resolved path so two files can never collide on
filename. Content is base64-encoded RAW BYTES, restored with
`Path.write_bytes` -- never decoded/re-encoded text -- so a restore is
byte-exact (the T-0441 CRLF lesson: a text-mode round trip silently
rewrites CRLF line endings to the platform default).

A journal that already exists for a target when `write_journal` is called
is only a problem if its content DIFFERS from what this run is about to
write: the SAME content is idempotent (a resumed run, or a repeated
call), a DIFFERENT content returns `Err(JournalError.Collision)` and
`run_mutations` aborts with `MutateError.JournalCollision` rather than
silently clobbering another run's backup -- this is the guard against two
concurrent mutation runs (the fork-bomb shape) corrupting each other's
journals.

`frob doctor` reports the same stale-journal state read-only via
`list_stale_journals` (`DoctorReport.mutate_journals`) -- see
`docs/guides/install.md#mutate-backup-journal-needs-restore-t-0857` for
the doctor-side detail. Doctor never restores anything itself; only
`run_mutations`' own startup check (`restore_stale_journals`) performs
the actual restore.

### PID reuse: why "is the writer alive" is not enough (T-0857 reviewer fix)

A reviewer caught a real gap in this ticket's first pass: "stale" was
originally defined purely as "the writer's PID is not alive" (a signal-0
`os.kill` probe). That is not sufficient on its own -- if a crashed
writer's PID number gets recycled by the OS for an unrelated process
before the next check runs, the probe reports "alive" FOREVER, even
though the original writer is long gone. `list_stale_journals` would then
exclude that journal forever, `DoctorReport.mutate_journals` would stay
empty, and `frob doctor` would report CLEAN while a real source file sat
in mutant form on disk with no distinguishing signal anywhere.

The fix: every journal also records the writer's `starttime` (field 22 of
`/proc/<pid>/stat`, the kernel's own process-start timestamp in clock
ticks since boot -- stable for that PID's whole lifetime, and different
for whatever process the kernel later hands the same PID number to). A
journal is stale when its PID is dead, OR the PID is alive but its
CURRENT starttime no longer matches the journal's recorded one -- exactly
the PID-reuse signature. `restore_stale_journals`/`list_stale_journals`
both use this via `_is_stale`, tested directly: a journal written against
a genuinely live PID with a deliberately MISMATCHED recorded `starttime`
(simulating the recycled-PID case with no actual PID recycling needed) is
correctly treated as stale and restorable.

This is Linux-specific (`/proc` is not portable). Where `/proc/<pid>/stat`
cannot be read at journal-write time (non-Linux, a sandboxed/restricted
environment), `starttime` is persisted as `None` and staleness falls back
to PID-only liveness -- the residual PID-reuse window this ticket cannot
close everywhere. `write_journal`'s own content-hash collision check
happens to catch most real occurrences of this in practice (the next
legitimate run's original bytes will very likely differ from whatever the
recycled-PID journal recorded, so `write_journal` refuses rather than
corrupts) -- but that is a lucky side effect, not a guarantee. If `frob
doctor` stays clean but a target keeps refusing with `JournalCollision`,
inspect `.frob/mutate-backup/<hash>.json` by hand -- the recorded PID may
have been reused.

### Recursion guard (considered, not changed)

The ticket that added this journal (T-0857) also asked whether any
evidence test importing `frob.mutate` against the real repo needs
hardening to honor `MUTATION_RUN_ENV`. Checked against the actual test
suite: `tests/test_mutate.py`'s self-referential subprocess test and
`tests/test_tickets_mutation_evidence.py`'s TEST016 self-check both
already gate on `MUTATION_RUN_ENV` (the T-0755 guard, unchanged by this
ticket) before invoking the harness against the real repo -- no
additional test currently invokes `frob.mutate` against the real repo
without that guard. No code change was needed for this part; recorded
here so the check is not silently assumed rather than verified.
