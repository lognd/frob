<!-- mdtest: rule=TESTQ003 -->
# TESTQ003 control-flow-in-test

An if, a loop or a match in a test body (off unless the project enables it).

## What it does

Fires in Rust, Python, TypeScript/JavaScript and C# test files for an `if`, a loop or a `match` inside a test body. Control flow in a test is a taste call, so the rule is off by default and is not applicable until the project opts in with `[rules.TESTQ003] severity = "error"` in `grimble.toml`; `severity = "off"` keeps it off. A code language with no test roles is reported Unresolved once, never clean.

## Why it matters

A branch in a test means some runs check less than others, and the reader has to work out which path ran before trusting the result.

## Remedy

Split the cases into separate tests, or parametrize one test over the inputs.

## Examples

### Fires case 1

```python expect=fire file=tests/test_flow.py
def test_each():
    for value in (1, 2, 3):
        assert value > 0
```

### Clean case 2

```python expect=clean file=tests/test_flow.py
def test_one():
    assert 1 > 0
```
