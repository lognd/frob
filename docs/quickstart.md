# frob quickstart

A real end-to-end walkthrough of the enforcement loop -- `annotate -> check
-> fix-or-waive` -- captured on a fresh demo repo. Every command below was
actually run; output is trimmed of debug logging noise but not altered.

---

## Setup

```bash
mkdir demo && cd demo && git init -q
```

```
src/demo/__init__.py   # empty package
src/demo/calc.py       # one existing function: add(a, b)
```

`frob.toml` needs a test runner before `frob test` can run anything:

```toml
[[test.runner]]
language = "python"
command = ["uv", "run", "pytest", "-q", "{ids}"]
all_command = ["uv", "run", "pytest", "-q"]
cwd = "."
```

Runner config lives in `frob.toml` at the repo root, not `[tool.frob]` in
`pyproject.toml` -- `frob test`/`frob check` look for a dedicated file.

Commit the starting point on `main` (frob's default `check`/`test` base).

---

## 1. Build the obligation graph

```
$ frob graph build
build_graph: done, parsed=2 hits=0 symbols=1 edges=0 malformed=0
graph build: files parsed=2 cache_hits=0 symbols=1 edges=0 malformed=0
```

This populates `.frob/cache.db` (gitignored, always rebuildable) with every
symbol's identity and digests.

---

## 2. File a ticket

```
$ frob ticket new --title "Add multiply function" --kind feature \
    --scope "src/demo/calc.py"
created T-0001: Add multiply function
```

```
$ frob ticket show T-0001
T-0001  [queued]  Add multiply function  (feature)
blocked_by=[] scope=['src/demo/calc.py']
```

`frob ticket start` moves a ticket to `in-progress` and runs the pre-work
sweep (dup + xref over scope). Starting a fresh `queued` ticket takes both
legal state-machine steps for you (`queued -> planned -> in-progress`);
use `frob ticket plan` if you want to stage the planned state explicitly,
and `frob ticket sweep <id>` to re-record the sweep after widening a
ticket's scope mid-flight.

```
$ frob ticket start T-0001
auto-planned T-0001 (queued -> planned)
record_prework: T-0001 sweep recorded (dup=0, xref=1) at .frob/prework/T-0001.json
swept T-0001: dup_findings=0 xref_hits=1
```

---

## 3. Write code with `frob:ticket` and `frob:tests` directives

```python
# src/demo/calc.py

# frob:ticket T-0001
def multiply(a: int, b: int) -> int:
    """Return the product of a and b."""
    return a * b
```

```python
# tests/test_calc.py

# frob:ticket T-0001
from demo.calc import add, multiply


# frob:tests src/demo/calc.py::add
def test_add() -> None:
    assert add(2, 3) == 5


# frob:tests src/demo/calc.py::multiply
def test_multiply() -> None:
    assert multiply(2, 3) == 6
```

Also add `tests/test_calc.py` and the ticket file itself to T-0001's `scope`
in the frontmatter -- the scope gate enforces the declared blast radius
against every changed file, including the ticket file's own state change.

---

## 4. `frob check` -- see the violation, then the remedy

```
$ frob check . --ticket T-0001
## Errors
  [gates] tests/test_calc.py:6  COV002  COV002: tests/test_calc.py::test_add changed with no frob:ticket edge to an open ticket; run: frob ticket new, then add: frob:ticket <id>
  [gates] tests/test_calc.py:11 COV002  COV002: tests/test_calc.py::test_multiply changed with no frob:ticket edge to an open ticket; run: frob ticket new, then add: frob:ticket <id>
  [gates] .frob/coverage-stamp:0 TEST006  TEST006: no coverage stamp found; run: make coverage

frob check .  [FAIL]  ...
```

(This was captured before the `# frob:ticket T-0001` line was added above
`from demo.calc import ...` in the test file -- every violation message
embeds its own remedy command.) After adding that directive and re-running
`frob ticket start T-0001` to refresh the pre-work sweep against the new
scope:

```
$ frob check . --ticket T-0001 --only coverage
frob check .  [PASS]  0 errors  0 warnings
```

```
$ frob check . --ticket T-0001 --only prework
frob check .  [PASS]  0 errors  0 warnings
```

The rest of `frob check .` (no `--only`) still reports open floors this
minimal demo doesn't clear: `TEST002` (fewer than `min_unit_cases=3` unit
tests per symbol), `TEST003` (the package owes an integration test as an
interface), `COV001` (no `frob:doc` edge on either function), `TEST006` (no
coverage stamp -- run `make coverage`). Each of those is a real, separate
obligation with its own remedy line; closing them is more work than a
one-function quickstart needs to demonstrate the loop, and each can be
waived explicitly (`frob:waive RULE-ID reason="..."`) if a ticket
intentionally defers it.

---

## 5. `frob ack`

```
$ frob ack src/demo/calc.py::multiply --facet sig
acknowledge: src/demo/calc.py::multiply facet=sig digest=813c0c5d...
write_lock: 1 entries -> frob.lock
acked src/demo/calc.py::multiply
```

`frob.lock` now records the current `sig` digest for `multiply`. If its
signature changes later without a re-ack, `frob check` fails `DRIFT001` --
that's the drift half of enforcement: nothing declared can silently break.

---

## 6. `frob test --base main`

```
$ frob test --base main
select_tests: touched=9 ripple=0 selected_langs=1 unbound=0
selection: touched=9 ripple=0 unbound=0 fallback=package
[PASS] python  exit=0  0.38s
```

`frob test` diffed against `main`, resolved the touched hunks to symrefs,
pulled in every `frob:tests` edge bound to them, and ran exactly that
selection through the configured pytest runner -- not the whole suite.

---

## 7. Close the ticket

Append a Done report and fill in `evidence`, then close:

```markdown
## Done report

Changed: src/demo/calc.py::multiply
Evidence: tests/test_calc.py::test_multiply
Filed: none
Gates: frob check --ticket T-0001 clean for coverage/scope/drift/prework;
  test-count and doc-coverage floors intentionally deferred for this walkthrough
```

```
$ frob ticket close T-0001
tickets: T-0001 transitioned in-progress -> done
T-0001 closed (done)
```

`close` re-verifies `evidence` is non-empty and a Done report section
exists -- editing the frontmatter directly to `state: done` without both is
rejected.

---

## Next steps

- `docs/gates.md` -- the full rule catalog (DRIFT/COV/SCOPE/PRE/INV/TEST/POL)
  and what closes each one out.
- `docs/agentic-workflow.md` -- running this same loop through the
  planner/implementer/reviewer/prover agents instead of by hand.
- `docs/testing.md` -- the touched-set selection algorithm and the
  `[[test.runner]]` registry for other languages.
