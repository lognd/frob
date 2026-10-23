//! `TESTQ002` for TypeScript and JavaScript tests: timers, clock reads and unseeded random sources.
//!
//! A test that pins the source is exempt. Fake timers, a set system time, a stubbed `Math.random`
//! or `Date.now`: a hook outside the test body may do it, so the whole file is searched for pins.

// frob:ticket 01M5K9QNQFYJNXZSSG2X91FJBQ

use tree_sitter::Node;

use super::ctx::Ctx;
use super::nondet::{Class, Hit, args_empty, strip, visit};
use crate::syntax::text;

/// Leading path segments that name a global object or a node module namespace, not a receiver.
const GLOBALS: &[&str] = &[
    "globalThis",
    "window",
    "global",
    "self",
    "timers",
    "promises",
    "perf_hooks",
];

/// `crypto` members that draw random bytes.
const CRYPTO_RNG: &[&str] = &[
    "randomUUID",
    "getRandomValues",
    "randomBytes",
    "randomInt",
    "randomFill",
    "randomFillSync",
    "generateKeySync",
];

/// Calls that replace a global: their arguments say which one.
const STUBBERS: &[&str] = &["spyOn", "stub", "replace", "mock", "stubGlobal", "fake"];

/// The class of a call to `e` (already import-expanded), when it is nondeterministic.
fn call_class(e: &[String]) -> Option<Class> {
    let s = strip(e, GLOBALS);
    match s.as_slice() {
        ["Date"]
        | ["Date" | "performance", "now"]
        | ["process", "hrtime" | "uptime"]
        | ["process", "hrtime", "bigint"] => Some(Class::Clock),
        ["crypto", .., last] if CRYPTO_RNG.contains(last) => Some(Class::Rng),
        ["Math", "random"] | ["uuid", "v1" | "v4" | "v6" | "v7"] | ["nanoid", "nanoid"] => {
            Some(Class::Rng)
        }
        ["setTimeout" | "setInterval"] | ["scheduler", "wait"] => Some(Class::Sleep),
        _ => None,
    }
}

/// What the file pins; a pinned class is not reported.
#[derive(Default)]
struct Pins {
    sleep: bool,
    clock: bool,
    rng: bool,
}

impl Pins {
    /// Pin the classes whose names appear in the argument text of a stubbing call.
    fn pin_args(&mut self, args: &str) {
        self.rng |= (args.contains("Math") && args.contains("random")) || args.contains("crypto");
        self.clock |= args.contains("Date") || args.contains("performance");
        self.sleep |= args.contains("setTimeout") || args.contains("setInterval");
    }

    /// Find fake timers, a set system time and stubbed globals anywhere under `root`.
    fn find<'t>(cx: &Ctx<'t>, root: Node<'t>) -> Self {
        let mut pins = Self::default();
        for c in cx.scan_body(root).calls {
            let e = cx.expand(&c.segs);
            let Some(last) = e.last().map(String::as_str) else {
                continue;
            };
            let first = e.first().map_or("", String::as_str);
            match last {
                "useFakeTimers" | "installFakeTimers" => {
                    pins.sleep = true;
                    pins.clock = true;
                }
                "install" | "withGlobal"
                    if matches!(first, "lolex" | "FakeTimers" | "@sinonjs") =>
                {
                    pins.sleep = true;
                    pins.clock = true;
                }
                "setSystemTime" => pins.clock = true,
                "clock" if first == "cy" => {
                    pins.sleep = true;
                    pins.clock = true;
                }
                _ if first.eq_ignore_ascii_case("mockdate") => pins.clock = true,
                _ if STUBBERS.contains(&last) => pins.pin_args(text(c.node, cx.src)),
                _ => {}
            }
        }
        visit(root, &mut |n| {
            if n.kind() == "assignment_expression"
                && let Some(left) = n.child_by_field_name("left")
            {
                let left: String = text(left, cx.src).split_whitespace().collect();
                pins.pin_args(&left);
            }
        });
        if pins.sleep || pins.clock || pins.rng {
            tracing::debug!(
                sleep = pins.sleep,
                clock = pins.clock,
                rng = pins.rng,
                "script test pins nondeterminism"
            );
        }
        pins
    }
}

/// `setTimeout(fn, 0)`: a yield to the event loop, not a wait.
fn zero_delay(cx: &Ctx<'_>, call: Node<'_>) -> bool {
    call.child_by_field_name("arguments").is_some_and(|a| {
        let mut cur = a.walk();
        let last = a.named_children(&mut cur).last();
        last.is_some_and(|l| text(l, cx.src).trim() == "0")
    })
}

/// Every nondeterministic call or `new Date()` in the body of the test function `func`.
pub(super) fn find<'t>(cx: &Ctx<'t>, func: Node<'t>, root: Node<'t>) -> Vec<Hit<'t>> {
    let Some(body) = func.child_by_field_name("body") else {
        return Vec::new();
    };
    let pins = Pins::find(cx, root);
    let mut hits = Vec::new();
    visit(body, &mut |n| match n.kind() {
        "call_expression" => {
            let Some(c) = cx.callee(n) else { return };
            if c.method {
                return;
            }
            let e = cx.expand(&c.segs);
            let exempt = match call_class(&e) {
                None => return,
                Some(Class::Sleep) => pins.sleep || zero_delay(cx, n),
                Some(Class::Clock) => pins.clock,
                Some(Class::Rng) => pins.rng,
            };
            if !exempt {
                hits.push(Hit {
                    node: n,
                    detail: e.join("."),
                });
            }
        }
        "new_expression" => {
            let Some(ctor) = n.child_by_field_name("constructor") else {
                return;
            };
            let e = cx.expand(&cx.chain(ctor));
            if strip(&e, GLOBALS) == ["Date"] && args_empty(n) && !pins.clock {
                hits.push(Hit {
                    node: n,
                    detail: "new Date".to_owned(),
                });
            }
        }
        _ => {}
    });
    hits
}
