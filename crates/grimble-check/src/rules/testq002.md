<!-- mdtest: rule=TESTQ002 -->
# TESTQ002 nondeterministic-test

A sleep, wall-clock read or unseeded random source in a test body.

## What it does

Fires in Rust, Python, TypeScript/JavaScript and C# test files for a call in a test body that makes the outcome depend on time or chance: a sleep, a wall-clock read (`time.time()`, `datetime.now()`, `SystemTime::now()`, `Date.now()`) or an unseeded random source (`random.random()`, `Math.random()`, `new Random()`). A test that pins the source (fake timers, a set system time, a stubbed `Math.random`, a seeded generator) stays quiet. Network calls are not covered. A code language with no test roles is reported Unresolved once, never clean.

## Why it matters

A test that sleeps is slow, and one that reads the clock or a random value passes or fails by luck, so a red run cannot be trusted and a green one proves little.

## Remedy

Inject the clock or the seed, or use fake timers, so the test controls the value it reads.

## Examples

### Fires case 1

```python expect=fire file=tests/test_wait.py
import time


def test_waits():
    time.sleep(1)
    assert True
```

### Fires case 2

```python expect=fire file=tests/test_rand.py
import random


def test_roll():
    value = random.random()
    assert value < 2
```

### Clean case 3

```python expect=clean file=tests/test_wait.py
def test_adds():
    assert 1 + 2 == 3
```
