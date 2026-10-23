//! `TESTQ002` for `C#` tests: sleeps, clock reads and unseeded random sources.
//!
//! `new Random(seed)` is seeded and quiet; a delay given a `TimeProvider` is under test control.

// frob:ticket 01M5K9QNQFYJNXZSSG2X91FJBQ

use tree_sitter::Node;

use super::ctx::Ctx;
use super::nondet::{Class, Hit, strip, visit};
use crate::syntax::text;

/// Leading namespace segments that do not change which type is meant.
const NAMESPACES: &[&str] = &[
    "System",
    "Diagnostics",
    "Threading",
    "Tasks",
    "Security",
    "Cryptography",
];

/// The class of an invocation of `e`, when it is nondeterministic.
fn call_class(e: &[String]) -> Option<Class> {
    let s = strip(e, NAMESPACES);
    match s.as_slice() {
        ["Thread", "Sleep"] | ["Task", "Delay"] => Some(Class::Sleep),
        ["Guid", "NewGuid" | "CreateVersion7"]
        | ["Random", "Shared", _]
        | ["RandomNumberGenerator", _] => Some(Class::Rng),
        ["Stopwatch", "StartNew" | "GetTimestamp"]
        | [
            "TimeProvider",
            "System",
            "GetUtcNow" | "GetLocalNow" | "GetTimestamp",
        ] => Some(Class::Clock),
        _ => None,
    }
}

/// True when `e` reads the wall clock as a property (`DateTime.Now`).
fn clock_property(e: &[String]) -> bool {
    matches!(
        strip(e, NAMESPACES).as_slice(),
        ["DateTime", "Now" | "UtcNow" | "Today"] | ["DateTimeOffset", "Now" | "UtcNow"]
    )
}

/// A delay of zero, or one handed a `TimeProvider`: a yield or a controlled wait, not real time.
fn controlled_delay(cx: &Ctx<'_>, call: Node<'_>) -> bool {
    let args = call
        .child_by_field_name("arguments")
        .map(|a| text(a, cx.src))
        .unwrap_or_default();
    let inner = args.trim_matches(['(', ')', ' ']);
    inner == "0" || inner == "TimeSpan.Zero" || args.to_ascii_lowercase().contains("timeprovider")
}

/// Every nondeterministic call, clock property or unseeded `new Random()` in the method `func`.
pub(super) fn find<'t>(cx: &Ctx<'t>, func: Node<'t>) -> Vec<Hit<'t>> {
    let Some(body) = func.child_by_field_name("body") else {
        return Vec::new();
    };
    let mut hits = Vec::new();
    visit(body, &mut |n| match n.kind() {
        "invocation_expression" => {
            let Some(c) = cx.callee(n) else { return };
            if c.method {
                return;
            }
            let e = cx.expand(&c.segs);
            let exempt = match call_class(&e) {
                None => return,
                Some(Class::Sleep) => controlled_delay(cx, n),
                Some(_) => false,
            };
            if !exempt {
                hits.push(Hit {
                    node: n,
                    detail: e.join("."),
                });
            }
        }
        "member_access_expression" => {
            let e = cx.chain(n);
            if clock_property(&e) {
                hits.push(Hit {
                    node: n,
                    detail: e.join("."),
                });
            }
        }
        "object_creation_expression" => {
            let unseeded = n
                .child_by_field_name("arguments")
                .is_none_or(|a| a.named_child_count() == 0);
            let ty = n.child_by_field_name("type").map(|t| text(t, cx.src));
            let ty = ty.map(|t| t.trim_start_matches("System."));
            if unseeded && ty == Some("Random") {
                hits.push(Hit {
                    node: n,
                    detail: "new Random".to_owned(),
                });
            }
        }
        _ => {}
    });
    hits
}
