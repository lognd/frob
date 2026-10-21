<!-- mdtest: rule=TIME001 -->
# TIME001 local-clock-read

A current-time read in the local zone, or without a zone, whose value is stored or sent.

## What it does

Fires in Rust and Python for a clock read that has no fixed zone (Python `datetime.now()` without a `tz`, `datetime.utcnow()`, `datetime.today()`, `date.today()`, `time.localtime()`; Rust `Local::now()`, `Local::today()`, `Zoned::now()`, `OffsetDateTime::now_local()`) when the value is stored, compared, returned or passed on. A value that is only displayed (printed, logged, formatted into a message) stays quiet, as do `time.time()`, `datetime.now(tz)`, `Utc::now()`, `SystemTime::now()` and `Instant::now()`. A read converted at once to an instant or a named zone (`.astimezone(tz)`, `.timestamp()`, `.with_timezone(..)`) is quiet too. Import aliases are resolved. Other code languages report the rule Unresolved, never clean.

## Why it matters

A stored local time changes meaning with the machine's zone and daylight saving, so the same record sorts and compares differently on two hosts.

## Remedy

Read the clock in UTC and tz-aware (`datetime.now(timezone.utc)`, `Utc::now()`), and convert to a local zone only for display.

## Examples

### Fires case 1

```python expect=fire file=app/stamp.py
import datetime


def stamp(record):
    record.created = datetime.datetime.now()
    return record
```

### Fires case 2

```python expect=fire file=app/stamp.py
from datetime import datetime as dt


def stamp():
    return dt.utcnow()
```

### Fires case 3

```rust expect=fire file=src/lib.rs
use chrono::Local;

pub struct Row {
    pub at: chrono::DateTime<Local>,
}

pub fn row() -> Row {
    Row { at: Local::now() }
}
```

### Fires case 4

```rust expect=fire file=src/lib.rs
use chrono::Local as L;

pub fn stamp() -> String {
    let now = L::now();
    store(now)
}

fn store(_t: chrono::DateTime<chrono::Local>) -> String {
    String::new()
}
```

### Clean case 5

```python expect=clean file=app/stamp.py
import datetime


def show():
    now = datetime.datetime.now()
    print(f"started at {now}")
```

### Clean case 6

```python expect=clean file=app/stamp.py
import datetime
import time


def stamp(record):
    record.created = datetime.datetime.now(datetime.timezone.utc)
    record.at = datetime.datetime.now(tz=datetime.timezone.utc)
    record.epoch = time.time()
    return record
```

### Clean case 7

```rust expect=clean file=src/lib.rs
use std::time::{Instant, SystemTime};

pub fn clocks() -> (SystemTime, Instant, chrono::DateTime<chrono::Utc>) {
    (SystemTime::now(), Instant::now(), chrono::Utc::now())
}
```

### Clean case 8

```rust expect=clean file=src/lib.rs
use chrono::Local;

pub fn show() {
    let now = Local::now();
    println!("started at {now}");
}
```

### Unresolved case 9

```typescript expect=unresolved file=src/a.ts
export const stamp = new Date();
```
