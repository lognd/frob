---
name: write-tests
description: Write unit, integration, and system tests before or alongside implementation. Use when the user says "write tests for X", "add tests", or as part of the develop pipeline. Dispatches Haiku tester agents for individual test files.
---

# write-tests

Tests before code. Unit first, integration second, system third.

## Before writing a single test

Run outline on every file being tested:

```bash
frob outline src/frob/<module>/__init__.py
```

This shows all public functions + signatures at ~50 tokens each.
If signatures are not yet written (stubs exist), read the stub directly -- it is small.

## Unit tests

For each public function, dispatch a `tester` agent:

```bash
frob bundle src/frob/<module>/__init__.py <function_name> > /tmp/ctx.md
```

Then use the `tester` agent (see `agents/tester/SKILL.md`) with this prompt template:

```
You are writing pytest unit tests. Context:

{contents of /tmp/ctx.md}

Task: write tests for `{function_name}` covering:
- Happy path: valid input returns Ok(expected)
- Error path: each FeatureError variant is returned (not raised)
- Edge cases: empty input, None where allowed, boundary values

File: tests/test_{module}.py
Class: Test{FunctionName}

Return ONLY a unified diff. No explanation. No prose.
```

Apply the diff:

```bash
git apply /tmp/tester_output.diff
```

Verify the test file parses (no syntax errors):

```bash
python -c "import ast; ast.parse(open('tests/test_{module}.py').read())"
```

## Integration tests

Integration tests check that two modules work together correctly.
Write them by hand (they require cross-module knowledge that Haiku lacks).

Focus on:
- Module A produces output that Module B consumes
- Error from A propagates correctly through B
- Shared data models round-trip correctly

File: `tests/test_integration_{a}_{b}.py`

## System tests

System tests run the CLI end-to-end via subprocess. Add to `tests/test_system.py`.

Template for a new command:

```python
def test_{cmd}_exits_zero(fixture):
    r = run("{cmd}", str(fixture))
    assert r.returncode == 0

def test_{cmd}_output_contains(fixture):
    r = run("{cmd}", str(fixture))
    assert "expected_string" in r.stdout

def test_{cmd}_json(fixture):
    r = run("{cmd}", str(fixture), "--json")
    data = json.loads(r.stdout)
    assert "expected_key" in data

def test_{cmd}_error_exits_nonzero(fixture):
    r = run("{cmd}", str(fixture), "bad-arg")
    assert r.returncode != 0
```

## After writing tests

Run them immediately to check for errors in the tests themselves:

```bash
pytest tests/test_{module}.py -x --tb=short 2>&1 | frob parse pytest --exit-code $?
```

At this stage tests SHOULD fail (implementation is `...`). That is correct.
What must NOT happen: import errors, syntax errors, or test collection errors.

Fix any collection errors before continuing.

## Coverage checklist

Every public function needs:
- [ ] At least one happy-path test (Ok result)
- [ ] One test per ErrorSet variant (Err result returned, not raised)
- [ ] One edge case test (empty, None, boundary)
- [ ] One system test (CLI invocation, for commands)

No mocking of internal modules. Hit real code. Only mock filesystem and network
at the system boundary (use `tmp_path` fixture for files).
