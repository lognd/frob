//! `TESTQ002`: a sleep, a wall-clock read or an unseeded random source inside a test body.
//!
//! Only the test's own body is inspected (closures included, helper bodies not followed). A test
//! that pins the source of the nondeterminism is exempt: a paused or frozen clock, a patched
//! sleep, a seeded generator.

// frob:ticket 01M4D957J2HZ655A1H8DJ4K8YD

use tree_sitter::Node;

use super::ctx::{Callee, Ctx};
use crate::syntax::{Lang, text};

/// What kind of nondeterminism a call is.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Class {
    Sleep,
    Clock,
    Rng,
}

/// One nondeterministic call in a test body.
pub(super) struct Hit<'t> {
    /// The call node.
    pub node: Node<'t>,
    /// The path called, expanded through imports (`std::thread::sleep`).
    pub detail: String,
}

fn ends(e: &[String], tail: &[&str]) -> bool {
    e.len() >= tail.len()
        && e[e.len() - tail.len()..]
            .iter()
            .zip(tail)
            .all(|(a, b)| a == b)
}

fn rust_class(e: &[String]) -> Option<Class> {
    let last = e.last()?.as_str();
    let prev = e.len().checked_sub(2).map(|i| e[i].as_str());
    if last == "sleep" && matches!(prev, Some("thread" | "time" | "task" | "timer")) {
        return Some(Class::Sleep);
    }
    let clock = matches!(
        (prev, last),
        (
            Some("Instant" | "SystemTime" | "Utc" | "Local" | "Zoned" | "Timestamp"),
            "now"
        ) | (Some("OffsetDateTime"), "now_utc" | "now_local")
    );
    if clock {
        return Some(Class::Clock);
    }
    let rng = (prev == Some("rand") && matches!(last, "thread_rng" | "random" | "rng"))
        || matches!(last, "from_entropy" | "from_os_rng");
    rng.then_some(Class::Rng)
}

fn py_class(e: &[String], args_empty: bool) -> Option<Class> {
    let last = e.last()?.as_str();
    if ["time", "asyncio", "trio", "anyio"]
        .iter()
        .any(|m| ends(e, &[m, "sleep"]))
    {
        return Some(Class::Sleep);
    }
    let clock = (ends(e, &["time", last])
        && matches!(
            last,
            "time" | "monotonic" | "perf_counter" | "time_ns" | "monotonic_ns" | "process_time"
        ))
        || (ends(e, &["datetime", last]) && matches!(last, "now" | "utcnow" | "today"))
        || ends(e, &["date", "today"]);
    if clock {
        return Some(Class::Clock);
    }
    let first = e.first()?.as_str();
    let rng = match (first, e.len()) {
        ("random", 2) => match last {
            "seed" => false,
            "Random" => args_empty,
            _ => true,
        },
        ("numpy", 3..) if e[1] == "random" => match last {
            "seed" => false,
            "default_rng" | "RandomState" => args_empty,
            _ => true,
        },
        ("os", 2) => last == "urandom",
        ("secrets", 2) => true,
        _ => false,
    };
    rng.then_some(Class::Rng)
}

fn args_empty(n: Node<'_>) -> bool {
    n.child_by_field_name("arguments")
        .is_none_or(|a| a.named_child_count() == 0)
}

/// True when the call is a seeding call (`random.seed(1)`, `torch.manual_seed(1)`).
fn is_seed(e: &[String]) -> bool {
    e.last().is_some_and(|l| l == "seed" || l == "manual_seed")
}

/// Calls at module level, outside any function or class.
fn module_calls<'t>(cx: &Ctx<'t>, n: Node<'t>, out: &mut Vec<Callee<'t>>) {
    if matches!(n.kind(), "function_definition" | "class_definition") {
        return;
    }
    if n.kind() == "call"
        && let Some(c) = cx.callee(n)
    {
        out.push(c);
    }
    let mut cur = n.walk();
    for c in n.children(&mut cur) {
        module_calls(cx, c, out);
    }
}

/// Every nondeterministic call of `func`; `marks` is the text of its attributes or decorators.
pub(super) fn find<'t>(cx: &Ctx<'t>, func: Node<'t>, marks: &str, root: Node<'t>) -> Vec<Hit<'t>> {
    let Some(body) = func.child_by_field_name("body") else {
        return Vec::new();
    };
    let calls = cx.scan_body(body).calls;
    let expanded: Vec<Vec<String>> = calls.iter().map(|c| cx.expand(&c.segs)).collect();
    let lower = format!("{marks}{}", text(func, cx.src)).to_ascii_lowercase();

    let (no_sleep, no_clock, no_rng) = match cx.lang {
        Lang::Rust => {
            let paused = marks.contains("start_paused")
                || expanded.iter().any(|e| ends(e, &["time", "pause"]));
            (paused, paused, false)
        }
        Lang::Python => {
            let patched = calls.iter().zip(&expanded).any(|(c, e)| {
                matches!(
                    e.last().map(String::as_str),
                    Some("patch" | "setattr" | "object")
                ) && text(c.node, cx.src).contains("sleep")
            }) || (marks.contains("patch") && marks.contains("sleep"));
            let frozen = ["freeze_time", "freezegun", "time_machine"]
                .iter()
                .any(|w| lower.contains(w));
            let mut top = Vec::new();
            module_calls(cx, root, &mut top);
            let seeded = expanded.iter().any(|e| is_seed(e))
                || top.iter().any(|c| is_seed(&cx.expand(&c.segs)));
            (patched, frozen, seeded)
        }
    };

    let mut hits = Vec::new();
    for (c, e) in calls.iter().zip(&expanded) {
        if c.tokens || c.method {
            continue;
        }
        let class = match cx.lang {
            Lang::Rust => rust_class(e),
            Lang::Python => py_class(e, args_empty(c.node)),
        };
        let Some(class) = class else { continue };
        let exempt = match class {
            Class::Sleep => no_sleep || (cx.lang == Lang::Python && text_is_zero_arg(cx, c.node)),
            Class::Clock => no_clock,
            Class::Rng => no_rng,
        };
        if exempt {
            continue;
        }
        let sep = if cx.lang == Lang::Rust { "::" } else { "." };
        hits.push(Hit {
            node: c.node,
            detail: e.join(sep),
        });
    }
    hits
}

/// `sleep(0)`: a yield, not a wait.
fn text_is_zero_arg(cx: &Ctx<'_>, call: Node<'_>) -> bool {
    call.child_by_field_name("arguments")
        .is_some_and(|a| text(a, cx.src).trim_matches(['(', ')', ' ']) == "0")
}
