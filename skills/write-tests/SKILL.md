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
```python
assert result.is_ok
assert result.danger_ok == expected

assert result.is_err
assert result.danger_err == SomeError.Variant
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

Write by hand -- they need cross-module knowledge that agents lack.
Focus on: module A output feeding module B input, error propagation at boundaries.

## System tests (CLI tools)

Use subprocess with real binaries on fixture projects:

```python
import shutil, subprocess, pytest
FROB = [sys.executable, "-m", "frob"]

def run(*args, input=None):
    return subprocess.run(FROB + list(args), capture_output=True, text=True, input=input)

def test_cmd_exits_zero(fixture_path):
    r = run("cmd", str(fixture_path))
    assert r.returncode == 0
```

For third-party tools (ruff, gcc, etc.):
```python
@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff not installed")
def test_with_ruff():
    ...
```

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
