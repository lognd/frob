# frob.mutate -- mutation testing (the honest quality oracle)

One sentence: `frob mutate` perturbs a file's source with small semantic
mutations (flip a comparison, swap an operator, negate a boolean), runs the
tests against each mutant, and reports which SURVIVED -- a survivor is a
behavior change no test caught, i.e. a real gap the coverage and case-count
gates only approximate.

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
truth. It is the quality oracle docs/fuzz.md and the TEST family point at.

## v1 scope (honest)

- Python source, mutated via a small AST transformer: comparison swaps
  (`<`<->`>=`, `==`<->`!=`), arithmetic swaps (`+`<->`-`, `*`<->`//`),
  boolean-operator swaps (`and`<->`or`), and boolean-constant negation.
- One mutation per run; the file is restored after every mutant and on any
  error, so a crashed run never leaves mutated source behind.
- A mutant that hangs the tests past the timeout counts as killed.
- Other languages and a MUT gate (a mutation-score floor on
  invariant-anchored symbols) are recorded follow-on work.
