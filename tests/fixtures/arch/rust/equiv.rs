// T-0615 N:1 equivalence fixture (rust side).
//
// Same structural shape as `equiv.py` / `equiv.ts` / `equiv.kt`: a base
// trait, a struct implementing it with a field, an overriding (trait-
// fulfilling) method, and a "dispatch" free function using rust's own
// idiomatic dispatch construct: `match`. `frob.arch._rust` deliberately
// counts EACH match arm as its own `NormalizedBranch` (T-0612's explicit
// divergence from python's if/elif folding) -- so `dispatch_kind` below
// scores THREE branches, same as kotlin's `when` (T-0614) and unlike
// python's ONE (elif-folded) / TS's ZERO (switch not branch-producing).

trait Creature {
    fn speak(&self) -> String;
}

struct Animal {
    name: String,
    age: i32,
}

impl Creature for Animal {
    fn speak(&self) -> String {
        self.name.clone()
    }
}

fn configure_pipeline(a: bool, b: bool, c: bool, d: i32) -> bool {
    if a {
        if b {
            if c {
                for i in 0..d {
                    let mut n = i;
                    if n != 0 {
                        while n != 0 {
                            if a && b {
                            }
                            n -= 1;
                        }
                    }
                }
            }
        }
    }
    a
}

fn dispatch_kind(kind: &str) -> i32 {
    match kind {
        "happy" => 0,
        "sad" => 1,
        _ => 2,
    }
}
