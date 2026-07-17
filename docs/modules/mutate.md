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

def generate_mutants(source, file) -> Result[tuple[Mutant, ...], MutateError]
def run_mutations(root, file, test_argv, timeout_s=300.0) -> Result[MutationResult, MutateError]
```

## v1 scope (honest)

- Python source, mutated via a small AST transformer: comparison swaps
  (`<`<->`>=`, `==`<->`!=`), arithmetic swaps (`+`<->`-`, `*`<->`//`),
  boolean-operator swaps (`and`<->`or`), and boolean-constant negation.
- One mutation per run; the file is restored after every mutant and on any
  error, so a crashed run never leaves mutated source behind.
- A mutant that hangs the tests past the timeout counts as killed.
- Other languages and a MUT gate (a mutation-score floor on
  invariant-anchored symbols) are recorded follow-on work.
