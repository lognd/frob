<!-- mdtest: rule=PARSE001 -->
# PARSE001 malformed directive

## Rust: unterminated quote

```rust expect=fire
/* frob:accept COV006 because="oops */ // error: PARSE001
fn a() {}
```

## Rust: missing required argument

```rust expect=fire
/* frob:accept COV006 */ // error: PARSE001
fn a() {}
```

## Rust: unknown key

```rust expect=fire
/* frob:ticket 01J9QKX3M8Z4T7N2V5B6C0D1E2 color=red */ // error: PARSE001
fn a() {}
```

## Rust: missing verb

```rust expect=fire
/* frob: hello */ // error: PARSE001
fn a() {}
```

## Rust: invalid rule id and non-ticket value

```rust expect=fire
/* frob:accept notarule because=x */ // error: PARSE001
/* frob:ticket banana */ // error: PARSE001
fn a() {}
```

## Rust: text after a closing quote

```rust expect=fire
/* frob:invariant "name"x */ // error: PARSE001
fn a() {}
```

## Markdown: bad doc anchor

```markdown expect=fire
# Title

<!-- frob:doc not-an-anchor --> <!-- error: PARSE001 -->
```

## TOML: missing argument

```toml expect=fire
# frob:invariant
key = 1
```

## Clean: every milestone-1 verb written correctly

```rust expect=clean
// frob:ticket 01J9QKX3M8Z4T7N2V5B6C0D1E2
fn a() {}

// frob:todo 01J9QKX3M8Z4T7N2V5B6C0D1E2 finish the parser later
fn b() {}

// frob:doc docs/design/code-model.md#the-directive-dsl
fn c() {}

// frob:tests src/lib.rs::c kind=unit
fn d() {}

// frob:invariant "no panics"
fn e() {}

// frob:accept COV006 because="style#dispatch-tables" until=2027-01-01
fn f() {}

// frob:defer COV006 because="split later" ticket=01J9QKX3M8Z4T7N2V5B6C0D1E2
fn g() {}
```

## Clean: not directives

```rust expect=clean
let s = "// frob:bogus";
// grimble:binds anything at all
// see frob:ticket in the docs
// plain comment: with a colon
fn a() {}
```

## Clean: markdown fenced code is not scanned

````markdown expect=clean
# Title

```
<!-- frob:bogus -->
```

<!-- frob:invariant fine -->
````
