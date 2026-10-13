<!-- mdtest: rule=PARSE001 -->
# PARSE001 on the milestone-2 claim directives

## Rust: unknown atom in an effect set

```rust expect=fire
/* grimble:effects reads(src/a.rs::x) teleport */ // error: PARSE001
fn a() {}
```

## Rust: unclosed reads

```rust expect=fire
/* grimble:effects reads(src/a.rs::x */ // error: PARSE001
fn a() {}
```

## Rust: empty writes argument

```rust expect=fire
/* grimble:effects writes() */ // error: PARSE001
fn a() {}
```

## Rust: level keyword joined with an atom

```rust expect=fire
/* grimble:effects io clock */ // error: PARSE001
fn a() {}
```

## Rust: total with panic

```rust expect=fire
/* grimble:effects clock panic total */ // error: PARSE001
fn a() {}
```

## Rust: total alone

```rust expect=fire
/* grimble:effects total */ // error: PARSE001
fn a() {}
```

## Rust: empty effect set

```rust expect=fire
/* grimble:effects */ // error: PARSE001
fn a() {}
```

## Rust: core takes no arguments

```rust expect=fire
/* grimble:core now */ // error: PARSE001
fn a() {}
```

## Rust: calls target is not a symref

```rust expect=fire
/* grimble:calls src/a.rs::f ::x */ // error: PARSE001
fn a() {}
```

## Clean: every valid effect set

```rust expect=clean
// grimble:effects none
fn a() {}

// grimble:effects honest
fn b() {}

// grimble:effects io total
fn c() {}

// grimble:effects any
fn d() {}

// grimble:effects clock rng env fs net stdio exit panic diverge
fn e() {}

// grimble:effects reads(src/a.rs::STATE) writes(src/b.rs::Cache.map) fs total
fn f() {}
```

## Clean: deprecated spellings raise DSL003, not PARSE001

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
    // grimble:calls src/b.rs::run src/c.rs::Handler.handle
    f();
}
```
