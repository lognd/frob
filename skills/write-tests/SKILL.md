---
name: write-tests
description: Write unit, integration, and system tests before or alongside implementation. Use when the user says "write tests for X", "add tests", or as part of the develop pipeline.
---

# write-tests

Tests before code. Unit first, integration second, system third.

## Get signatures without reading files

**If using frob:**
```bash
frob outline src/<module>/__init__.py
```

**Otherwise:**
```bash
grep -n "^def \|^    def \|^class " src/<module>/__init__.py
```

## Unit tests

For each public function, get minimal context then dispatch or write:

**If using frob (dispatch to tester agent):**
```bash
frob bundle src/<module>/__init__.py <function_name> > /tmp/ctx.md
```

**Otherwise:** read just the function with grep + context lines:
```bash
grep -n -A 20 "^def <function_name>" src/<module>/__init__.py
```

### Test structure (language-agnostic)

**Python / pytest:**
```python
class TestFunctionName:
    def test_happy_path(self):
        result = function_name(valid_input)
        # assert success

    def test_error_case(self):
        result = function_name(bad_input)
        # assert failure with correct reason

    def test_edge_empty(self):
        result = function_name(empty_input)
        # assert appropriate handling
```

**For typani Result types specifically:**

typani is the project's result/error library. All accessors are properties -- never `()`.

```python
# Success
assert result.is_ok
assert result.danger_ok == expected   # crashes if is_err

# Failure
assert result.is_err
assert result.danger_err == SomeError.Variant   # crashes if is_ok

# Safe (no crash)
assert result.ok == expected   # returns None on Err
assert result.err is None      # returns None on Ok

# Option[T]
assert opt.is_some
assert opt.danger_some == expected
```

**C++ / Google Test:**
```cpp
TEST(FunctionNameTest, HappyPath) {
    EXPECT_EQ(function_name(valid_input), expected);
}
TEST(FunctionNameTest, ErrorCase) {
    EXPECT_THROW(function_name(bad_input), std::invalid_argument);
    // or EXPECT_FALSE, EXPECT_EQ with error code, etc.
}
```

**If the tester agent returned BLOCKER:**
- Bypass permissions OFF: surface BLOCKER + SUGGESTION to user verbatim before continuing.
- Bypass permissions ON: dispatch /oracle, apply DECISION, resume.
Never write tests that paper over a design flaw to make them pass.

## After writing tests: verify they COLLECT

```bash
pytest tests/test_<module>.py --collect-only 2>&1 | head -20
```

Tests SHOULD fail (not implemented). What must NOT happen:
- Import errors
- Syntax errors
- Collection errors

Fix any collection errors immediately before continuing.

## Integration tests

Dispatch to the **integration-tester** agent (Sonnet). It tests real data flowing
across Python module boundaries -- no subprocess, no mocking.

Agent prompt template:
```
Modules to integrate: {module_a} + {module_b}
Interaction: {one sentence describing how A's output feeds B}
Test file: tests/integration/test_{a}_{b}.py
```

Integration-tester will report BLOCKER if the modules have incompatible interfaces.

## System tests (CLI commands)

Dispatch to the **system-tester** agent (Sonnet). It runs the real binary via
subprocess and asserts exact output, exit codes, and JSON field values.

Agent prompt template:
```
Command: frob {subcommand}
Runner source: {frob outline src/frob/app/{subcommand}_runner.py}
Test file: tests/system/test_cli_{subcommand}.py
Existing tests (if extending): {current file content or "none"}
```

System-tester will report BLOCKER if the CLI contract is inconsistent.

For third-party tool tests (ruff, gcc, etc.), use `@pytest.mark.skipif(shutil.which(...))`.
System-tester knows this pattern.

## Speed: use testmon for incremental runs

Install once: `pip install pytest-testmon`

```bash
# First run: builds dependency map (~same speed as normal)
pytest --testmon

# Subsequent runs: only runs tests touching changed files (very fast)
pytest --testmon

# Force full run (e.g., after deps change):
pytest --testmon --force
```

After writing a new test, run it alone first:
```bash
pytest tests/test_module.py::TestClass::test_name -x --tb=short
```

## Coverage checklist

Every public function:
- [ ] Happy path (success case)
- [ ] Each error/failure variant (returned, not raised)
- [ ] Empty/null/boundary input
- [ ] System test if it has a CLI entry point

No mocking of internal modules. Use real code. Only mock at system boundary (filesystem, network).
