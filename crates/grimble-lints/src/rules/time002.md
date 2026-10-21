<!-- mdtest: rule=TIME002 -->
# TIME002 naive-aware-mix

A naive and a timezone-aware datetime compared or subtracted.

## What it does

Fires in Rust and Python when a comparison (`<`, `>`, `<=`, `>=`, `==`, `!=`) or a subtraction has one naive and one timezone-aware operand, or two naive operands read in different zones (UTC and local). Naivety is tracked by name through assignments: `datetime.now()` without a `tz`, `utcnow()`, `datetime(...)` without `tzinfo`, `strptime` without `%z` and `.replace(tzinfo=None)` are naive; `datetime.now(tz)`, `.astimezone(..)` and a `tzinfo` argument are aware; in Rust `NaiveDateTime`, `.naive_utc()` and `.naive_local()` are naive and `Utc::now()`, `Local::now()`, `.with_timezone(..)` and `DateTime` values are aware. An operand whose class is not decidable never fires. Other code languages report the rule Unresolved, never clean.

## Why it matters

Python raises `TypeError` on such a comparison, and where the languages allow it the result silently shifts by the zone offset.

## Remedy

Make both sides aware (attach a zone with `replace(tzinfo=..)` or read with `now(tz)`) before comparing or subtracting.

## Examples

### Fires case 1

```python expect=fire file=app/age.py
from datetime import datetime, timezone


def expired(deadline):
    start = datetime.now()
    end = datetime.now(timezone.utc)
    return end > start
```

### Fires case 2

```python expect=fire file=app/age.py
import datetime


def elapsed(tz):
    a = datetime.datetime.utcnow()
    b = datetime.datetime.now()
    return b - a
```

### Fires case 3

```rust expect=fire file=src/lib.rs
use chrono::{Local, Utc};

pub fn later(n: chrono::NaiveDateTime) -> bool {
    let a = Utc::now();
    let b = Local::now().naive_local();
    a.naive_utc() < b || a > b
}
```

### Clean case 4

```python expect=clean file=app/age.py
from datetime import datetime, timezone


def expired():
    start = datetime.now(timezone.utc)
    end = datetime.now(timezone.utc)
    return end > start
```

### Clean case 5

```python expect=clean file=app/age.py
from datetime import datetime, timezone


def span(naive):
    other = datetime(2020, 1, 1)
    aware = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return naive - other, aware - aware, naive.replace(tzinfo=timezone.utc) > aware
```

### Clean case 6

```rust expect=clean file=src/lib.rs
use chrono::Utc;

pub fn order() -> bool {
    let a = Utc::now();
    let b = Utc::now();
    a < b
}
```

### Unresolved case 7

```typescript expect=unresolved file=src/a.ts
export const late = (a: Date, b: Date) => a < b;
```
