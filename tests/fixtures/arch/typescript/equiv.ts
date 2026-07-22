// T-0615 N:1 equivalence fixture (typescript side).
//
// Same structural shape as `equiv.py` / `equiv.rs` / `equiv.kt`: one base
// class, one derived class with a field, an overridden method (TS DOES
// have a static `override` keyword -- unlike python, this one IS captured
// in `NormalizedFunction.overrides`), and a "dispatch" free function
// using TS's own idiomatic dispatch construct: `switch`. TS's
// `switch_statement` is walked for NESTING DEPTH (`_TS_NESTING_TYPES`)
// but is NOT one of the branch-producing node types
// (`frob.arch._typescript`'s `NormalizedBranch` collection only fires on
// `if_statement`) -- so `dispatchKind` below scores ZERO branches, a
// third distinct shape alongside python's ONE (elif-folded) and rust/
// kotlin's THREE (one per match-arm/when-entry).

class Creature {
  speak(): string {
    return "...";
  }
}

class Animal extends Creature {
  name: string;
  age: number = 1;

  constructor(name: string, age = 1) {
    super();
    this.name = name;
    this.age = age;
  }

  override speak(): string {
    return this.name;
  }
}

function configurePipeline(a: boolean, b: boolean, c: boolean, d: number): boolean {
  if (a) {
    if (b) {
      if (c) {
        for (let i = 0; i < d; i++) {
          if (i) {
            while (i) {
              if (a && b) {
              }
              i -= 1;
            }
          }
        }
      }
    }
  }
  return a;
}

function dispatchKind(kind: string): number {
  switch (kind) {
    case "happy":
      return 0;
    case "sad":
      return 1;
    default:
      return 2;
  }
}
