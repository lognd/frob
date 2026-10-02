<!-- mdtest: rule=PARSE001 -->
# PARSE001 on the milestone-2 claim directives

## Rust: unknown atom in an effect set

```rust expect=fire
/* frob:effects reads(src/a.rs::x) teleport */ // error: PARSE001
fn a() {}
```

## Rust: unclosed reads

```rust expect=fire
/* frob:effects reads(src/a.rs::x */ // error: PARSE001
fn a() {}
```

## Rust: empty writes argument

```rust expect=fire
/* frob:effects writes() */ // error: PARSE001
fn a() {}
```

## Rust: level keyword joined with an atom

```rust expect=fire
/* frob:effects io clock */ // error: PARSE001
fn a() {}
```

## Rust: total with panic

```rust expect=fire
/* frob:effects clock panic total */ // error: PARSE001
fn a() {}
```

## Rust: total alone

```rust expect=fire
/* frob:effects total */ // error: PARSE001
fn a() {}
```

## Rust: empty effect set

```rust expect=fire
/* frob:effects */ // error: PARSE001
fn a() {}
```

## Rust: pure takes no arguments

```rust expect=fire
/* frob:pure now */ // error: PARSE001
fn a() {}
```

## Rust: trusted needs a because

```rust expect=fire
/* frob:trusted */ // error: PARSE001
fn a() {}
```

## Rust: hook takes one kind at most

```rust expect=fire
/* frob:hook route extra */ // error: PARSE001
fn a() {}
```

## Rust: calls target is not a symref

```rust expect=fire
/* frob:calls src/a.rs::f ::x */ // error: PARSE001
fn a() {}
```

## Clean: every valid effect set

```rust expect=clean
// frob:effects none
fn a() {}

// frob:effects honest
fn b() {}

// frob:effects io total
fn c() {}

// frob:effects any
fn d() {}

// frob:effects clock rng env fs net stdio exit panic diverge
fn e() {}

// frob:effects reads(src/a.rs::STATE) writes(src/b.rs::Cache.map) fs total
fn f() {}
```

## Clean: aliases and markers

```rust expect=clean
// frob:pure
fn a() {}

// frob:honest
fn b() {}

// frob:core
fn c() {}

// frob:shell
fn d() {}

// frob:hook
fn e() {}

// frob:hook route
fn f() {}

// frob:dispatcher
fn g() {}

// frob:idempotent
fn h() {}

// frob:trusted because="reviewed by the owner"
fn i() {}
```

## Clean: calls with symref targets

```rust expect=clean
fn a(f: fn()) {
    // frob:calls src/b.rs::run src/c.rs::Handler.handle
    f();
}
```
