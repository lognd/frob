<!-- mdtest: rule=PARSE001 -->
# Backslash continuation of a wrapped directive

## Python: break between arguments

```python expect=clean
# frob:invariant name \
# because it is wrapped
def a():
    pass
```

## Python: break in the middle of a token

```python expect=clean
# frob:accept COV006 because=\
# "reason"
def b():
    pass
```

## Rust: slash comments

```rust expect=clean
// frob:accept COV006 \
// because="wrapped"
fn c() {}
```

## Rust: block comment lines

```rust expect=clean
/* frob:accept COV006 \
 * because="wrapped" */
fn d() {}
```

## TypeScript: slash comments

```typescript expect=clean
// frob:accept COV006 \
// because="wrapped"
function e() {}
```

## Rust: a continuation still reports a malformed tail

```rust expect=fire
// frob:accept COV006 \
// color=red because="x" // error: PARSE001
fn f() {}
```
