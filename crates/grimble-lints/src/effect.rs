//! React effect cleanup: a `useEffect` that starts a request, timer, listener or subscription and
//! returns no cleanup that undoes it (PAIR001, React vocabulary).
//!
//! The pairs live in the [`PAIRS`] table, so a new effect-started API is a data change. The check
//! is structural: it reads the effect callback, finds the cleanups it returns, and pairs each
//! acquire with a release inside a returned cleanup.
//!
//! - A `return` inside a nested function is not the effect's cleanup; only returns of the effect
//!   callback itself count, and a `return` under a branch is a conditional cleanup.
//! - A cleanup that releases a different handle, a different event type or a different handler
//!   does not pair the acquire.
//! - An `async` effect callback returns a promise, never a cleanup, so every acquire in it fires.

// frob:ticket 01M4D95REZP3PP4F2WD7ASNXV3

use std::collections::HashSet;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gob_text::TextRange;
use tree_sitter::Node;

use crate::res::{
    Certainty, ScanError, bound_name, count_word, is_function, normalise, span, text,
};

/// How the release is tied to its acquire.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tie {
    /// A release call whose argument names the handle the acquire returned (`clearInterval(id)`).
    HandleArg,
    /// `removeEventListener` on the same target with the same type and handler, or an abort.
    Listener,
    /// An abort of the controller whose signal was passed, or a flag set in the cleanup.
    Request,
    /// The returned handle called, or a release method on the handle or the same receiver.
    Handle,
}

/// How an effect-started acquire is recognised.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Start {
    /// A call whose callee text is exactly this (`setInterval`).
    Call(&'static str),
    /// A method call of this name (`addEventListener`).
    Method(&'static str),
    /// `new Ctor(..)` (`IntersectionObserver`).
    New(&'static str),
}

/// One effect-started acquire and the release that pairs it.
#[derive(Debug, Clone, Copy)]
pub struct Pair {
    /// Stable pair id, reported on every site.
    pub id: &'static str,
    /// The acquire.
    pub start: Start,
    /// Release callee texts (`HandleArg`) or method names (the other ties).
    pub release: &'static [&'static str],
    /// How the release is tied to the acquire.
    pub tie: Tie,
}

/// Hooks whose first argument is an effect callback.
const EFFECT_HOOKS: &[&str] = &["useEffect", "useLayoutEffect", "useInsertionEffect"];

/// The effect-started acquire/release table (the React vocabulary of PAIR001).
pub const PAIRS: &[Pair] = &[
    Pair {
        id: "set-interval",
        start: Start::Call("setInterval"),
        release: &["clearInterval"],
        tie: Tie::HandleArg,
    },
    Pair {
        id: "set-timeout",
        start: Start::Call("setTimeout"),
        release: &["clearTimeout"],
        tie: Tie::HandleArg,
    },
    Pair {
        id: "animation-frame",
        start: Start::Call("requestAnimationFrame"),
        release: &["cancelAnimationFrame"],
        tie: Tie::HandleArg,
    },
    Pair {
        id: "add-event-listener",
        start: Start::Method("addEventListener"),
        release: &["removeEventListener"],
        tie: Tie::Listener,
    },
    Pair {
        id: "fetch",
        start: Start::Call("fetch"),
        release: &["abort"],
        tie: Tie::Request,
    },
    Pair {
        id: "subscribe",
        start: Start::Method("subscribe"),
        release: &["unsubscribe"],
        tie: Tie::Handle,
    },
    Pair {
        id: "add-listener",
        start: Start::Method("addListener"),
        release: &["removeListener"],
        tie: Tie::Handle,
    },
    Pair {
        id: "intersection-observer",
        start: Start::New("IntersectionObserver"),
        release: &["disconnect", "unobserve"],
        tie: Tie::Handle,
    },
    Pair {
        id: "resize-observer",
        start: Start::New("ResizeObserver"),
        release: &["disconnect", "unobserve"],
        tie: Tie::Handle,
    },
    Pair {
        id: "mutation-observer",
        start: Start::New("MutationObserver"),
        release: &["disconnect"],
        tie: Tie::Handle,
    },
    Pair {
        id: "web-socket",
        start: Start::New("WebSocket"),
        release: &["close"],
        tie: Tie::Handle,
    },
    Pair {
        id: "event-source",
        start: Start::New("EventSource"),
        release: &["close"],
        tie: Tie::Handle,
    },
];

/// Why an acquire is reported.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Reason {
    /// The effect returns no cleanup function.
    NoCleanup,
    /// The effect callback is `async`, so it returns a promise instead of a cleanup.
    AsyncEffect,
    /// A cleanup is returned but releases something else.
    CleanupMissesAcquire,
    /// The only pairing cleanup is returned under a branch, so another path leaks.
    ConditionalCleanup,
    /// The returned cleanup is a value the scan cannot read (an imported or computed function).
    OpaqueCleanup,
}

/// One effect-started acquire with no pairing cleanup.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Site {
    /// The [`Pair::id`] that is unpaired.
    pub pair: &'static str,
    /// The acquire, as byte offsets in the scanned text.
    pub range: TextRange,
    /// Whether the syntax alone decides it.
    pub certainty: Certainty,
    /// Why the acquire is reported.
    pub reason: Reason,
}

/// A returned value of the effect callback.
struct Returned<'t> {
    node: Node<'t>,
    /// The function when the value is a readable cleanup, else `None` (opaque).
    cleanup: Option<Node<'t>>,
    /// True when the return sits directly in the callback body, not under a branch.
    unconditional: bool,
}

/// An acquire found in an effect body.
struct Acquire<'t> {
    pair: &'static Pair,
    node: Node<'t>,
    bound: Option<String>,
    receiver: String,
    args: Vec<Node<'t>>,
}

fn named_children(n: Node<'_>) -> Vec<Node<'_>> {
    let mut cur = n.walk();
    n.named_children(&mut cur)
        .filter(|c| c.kind() != "comment")
        .collect()
}

fn args_of(call: Node<'_>) -> Vec<Node<'_>> {
    call.child_by_field_name("arguments")
        .map(named_children)
        .unwrap_or_default()
}

/// The hook name when `call` is `useEffect(..)` or `React.useEffect(..)`.
fn effect_callback<'t>(call: Node<'t>, src: &str) -> Option<Node<'t>> {
    if call.kind() != "call_expression" {
        return None;
    }
    let callee = normalise(text(call.child_by_field_name("function")?, src));
    let name = callee.rsplit('.').next().unwrap_or(&callee);
    if !EFFECT_HOOKS.contains(&name) {
        return None;
    }
    args_of(call)
        .first()
        .copied()
        .filter(|a| is_function(a.kind()))
}

fn is_async(f: Node<'_>) -> bool {
    f.child(0).is_some_and(|c| c.kind() == "async")
}

fn strip_wrappers(mut n: Node<'_>) -> Node<'_> {
    while matches!(n.kind(), "parenthesized_expression" | "await_expression") {
        match named_children(n).first() {
            Some(c) => n = *c,
            None => break,
        }
    }
    n
}

/// A function bound to `name` anywhere in `body` (a declaration or `const name = () => ..`).
fn local_function<'t>(body: Node<'t>, name: &str, src: &str) -> Option<Node<'t>> {
    let mut stack = vec![body];
    while let Some(n) = stack.pop() {
        let named = |field: &str| {
            n.child_by_field_name(field)
                .is_some_and(|c| text(c, src) == name)
        };
        if n.kind() == "function_declaration" && named("name") {
            return Some(n);
        }
        if n.kind() == "variable_declarator"
            && named("name")
            && let Some(v) = n.child_by_field_name("value").map(strip_wrappers)
            && is_function(v.kind())
        {
            return Some(v);
        }
        stack.extend(named_children(n));
    }
    None
}

/// Classifies one returned expression into [`Returned`] values (a ternary yields one per arm).
fn classify<'t>(
    expr: Node<'t>,
    body: Node<'t>,
    src: &str,
    unconditional: bool,
    out: &mut Vec<Returned<'t>>,
) {
    let expr = strip_wrappers(expr);
    if expr.kind() == "ternary_expression" {
        for field in ["consequence", "alternative"] {
            if let Some(arm) = expr.child_by_field_name(field) {
                classify(arm, body, src, false, out);
            }
        }
        return;
    }
    let cleanup = if is_function(expr.kind()) {
        Some(expr)
    } else if expr.kind() == "identifier" {
        local_function(body, text(expr, src), src)
    } else {
        None
    };
    out.push(Returned {
        node: expr,
        cleanup,
        unconditional,
    });
}

/// The values the effect callback itself returns; returns inside nested functions are skipped.
///
/// A bare `return;`, `return undefined` and `return null` return no cleanup and are dropped.
fn returns<'t>(func: Node<'t>, src: &str) -> Vec<Returned<'t>> {
    let mut out = Vec::new();
    let Some(body) = func.child_by_field_name("body") else {
        return out;
    };
    if body.kind() != "statement_block" {
        classify(body, body, src, true, &mut out);
        return out;
    }
    let mut stack = vec![body];
    while let Some(n) = stack.pop() {
        if n.kind() == "return_statement" {
            if let Some(value) = named_children(n).first().copied()
                && !matches!(text(value, src), "undefined" | "null")
            {
                let direct = n.parent().is_some_and(|p| p.id() == body.id());
                classify(value, body, src, direct, &mut out);
            }
            continue;
        }
        stack.extend(
            named_children(n)
                .into_iter()
                .filter(|c| !is_function(c.kind())),
        );
    }
    out
}

fn is_cleanup_fn(out: &[Returned<'_>], n: Node<'_>) -> bool {
    out.iter()
        .any(|r| r.cleanup.is_some_and(|c| c.id() == n.id()))
}

/// Acquires in the effect body, skipping the returned cleanup functions.
fn acquires<'t>(func: Node<'t>, returned: &[Returned<'t>], src: &str) -> Vec<Acquire<'t>> {
    let mut out = Vec::new();
    let Some(body) = func.child_by_field_name("body") else {
        return out;
    };
    let mut stack = vec![body];
    while let Some(n) = stack.pop() {
        if is_cleanup_fn(returned, n) {
            continue;
        }
        if let Some(a) = acquire_of(n, src) {
            out.push(a);
        }
        stack.extend(named_children(n));
    }
    out.sort_by_key(|a| a.node.start_byte());
    out
}

fn acquire_of<'t>(n: Node<'t>, src: &str) -> Option<Acquire<'t>> {
    let (callee_node, is_new) = match n.kind() {
        "call_expression" => (n.child_by_field_name("function")?, false),
        "new_expression" => (n.child_by_field_name("constructor")?, true),
        _ => return None,
    };
    let callee = normalise(text(callee_node, src));
    let (member, receiver) = if !is_new && callee_node.kind() == "member_expression" {
        let obj = callee_node.child_by_field_name("object")?;
        let prop = callee_node.child_by_field_name("property")?;
        (Some(text(prop, src).to_owned()), normalise(text(obj, src)))
    } else {
        (None, String::new())
    };
    let pair = PAIRS.iter().find(|p| match p.start {
        Start::Call(name) => !is_new && member.is_none() && callee == name,
        Start::Method(name) => member.as_deref() == Some(name),
        Start::New(ctor) => is_new && callee == ctor,
    })?;
    Some(Acquire {
        pair,
        node: n,
        bound: bound_name(n, src),
        receiver,
        args: args_of(n),
    })
}

/// A call inside a cleanup: callee text, and method name plus receiver for member calls.
struct Release<'t> {
    callee: String,
    member: Option<(String, String)>,
    args: Vec<Node<'t>>,
}

fn releases_in<'t>(cleanup: Node<'t>, src: &str) -> Vec<Release<'t>> {
    let mut out = Vec::new();
    let mut stack = vec![cleanup];
    while let Some(n) = stack.pop() {
        if n.kind() == "call_expression"
            && let Some(f) = n.child_by_field_name("function")
        {
            let member = (f.kind() == "member_expression")
                .then(|| {
                    let obj = f.child_by_field_name("object")?;
                    let prop = f.child_by_field_name("property")?;
                    Some((text(prop, src).to_owned(), normalise(text(obj, src))))
                })
                .flatten();
            out.push(Release {
                callee: normalise(text(f, src)),
                member,
                args: args_of(n),
            });
        }
        stack.extend(named_children(n));
    }
    out
}

/// The controller name in a `{ signal: ctrl.signal }` or `ctrl.signal` argument text.
fn signal_owner(arg: &str) -> Option<String> {
    let i = arg.find(".signal")?;
    let head = &arg[..i];
    let start = head
        .rfind(|c: char| !(c.is_alphanumeric() || c == '_' || c == '$' || c == '.'))
        .map_or(0, |p| p + 1);
    let owner = &head[start..];
    (!owner.is_empty()).then(|| normalise(owner))
}

fn aborts(releases: &[Release<'_>], owner: &str) -> bool {
    releases.iter().any(|r| {
        r.member
            .as_ref()
            .is_some_and(|(m, recv)| m == "abort" && recv == owner)
    })
}

/// True when some release in `releases` pairs `a`.
fn paired(a: &Acquire<'_>, releases: &[Release<'_>], cleanup_has_flag: bool, src: &str) -> bool {
    let pair = a.pair;
    match pair.tie {
        Tie::HandleArg => a.bound.as_ref().is_some_and(|b| {
            releases.iter().any(|r| {
                !r.args.is_empty()
                    && pair.release.contains(&r.callee.as_str())
                    && r.args.iter().any(|x| count_word(text(*x, src), b) > 0)
            })
        }),
        Tie::Listener => {
            let arg = |i: usize| a.args.get(i).map(|n| text(*n, src).trim());
            if let Some(owner) = a.args.get(2).and_then(|o| signal_owner(text(*o, src))) {
                return aborts(releases, &owner);
            }
            let (Some(kind), Some(handler)) = (arg(0), arg(1)) else {
                return false;
            };
            !a.args.get(1).is_some_and(|h| is_function(h.kind()))
                && releases.iter().any(|r| {
                    r.member.as_ref().is_some_and(|(m, recv)| {
                        pair.release.contains(&m.as_str()) && *recv == a.receiver
                    }) && r.args.first().map(|x| text(*x, src).trim()) == Some(kind)
                        && r.args.get(1).map(|x| text(*x, src).trim()) == Some(handler)
                })
        }
        Tie::Request => match a.args.get(1).and_then(|o| signal_owner(text(*o, src))) {
            Some(owner) => aborts(releases, &owner),
            None => cleanup_has_flag,
        },
        Tie::Handle => releases.iter().any(|r| {
            let called = a.bound.as_ref().is_some_and(|b| {
                (r.callee == *b && r.member.is_none())
                    || r.member.as_ref().is_some_and(|(m, recv)| {
                        recv == b && (m == "unsubscribe" || pair.release.contains(&m.as_str()))
                    })
            });
            let on_receiver = !a.receiver.is_empty()
                && r.member.as_ref().is_some_and(|(m, recv)| {
                    *recv == a.receiver && pair.release.contains(&m.as_str())
                });
            called || on_receiver
        }),
    }
}

/// True when the cleanup assigns something (the `ignore = true` flag pattern of the React docs).
fn sets_flag(cleanup: Node<'_>) -> bool {
    let mut stack = vec![cleanup];
    while let Some(n) = stack.pop() {
        if n.kind() == "assignment_expression" {
            return true;
        }
        stack.extend(named_children(n));
    }
    false
}

/// True when a returned value is the acquire itself or the name it was bound to.
fn returns_handle(r: &Returned<'_>, a: &Acquire<'_>, src: &str) -> bool {
    let n = r.node;
    a.pair.tie == Tie::Handle
        && r.cleanup.is_none()
        && (n.id() == a.node.id()
            || a.bound.as_ref().is_some_and(|b| text(n, src) == b)
            || (n.start_byte() <= a.node.start_byte() && a.node.end_byte() <= n.end_byte()))
}

fn judge(
    a: &Acquire<'_>,
    returned: &[Returned<'_>],
    asynchronous: bool,
    src: &str,
) -> Option<(Certainty, Reason)> {
    if asynchronous {
        return Some((Certainty::Certain, Reason::AsyncEffect));
    }
    let mut unconditional = false;
    let mut conditional = false;
    let mut opaque = false;
    let mut readable = false;
    for r in returned {
        let hit = match r.cleanup {
            Some(c) => {
                readable = true;
                paired(a, &releases_in(c, src), sets_flag(c), src)
            }
            None if returns_handle(r, a, src) => true,
            None => {
                opaque = true;
                false
            }
        };
        match (hit, r.unconditional) {
            (true, true) => unconditional = true,
            (true, false) => conditional = true,
            _ => {}
        }
    }
    if unconditional {
        None
    } else if conditional {
        Some((Certainty::Unknown, Reason::ConditionalCleanup))
    } else if opaque {
        Some((Certainty::Unknown, Reason::OpaqueCleanup))
    } else if readable {
        Some((Certainty::Certain, Reason::CleanupMissesAcquire))
    } else {
        Some((Certainty::Certain, Reason::NoCleanup))
    }
}

/// Every effect-started acquire in `text` parsed as `language` with no pairing cleanup, in source order.
///
/// A language without React effects yields no sites; a tree with syntax errors is still scanned.
///
/// # Errors
///
/// [`ScanError::Parse`] when the file does not parse within the limits.
pub fn scan(language: Language, text: &str) -> Result<Vec<Site>, ScanError> {
    if !matches!(
        language,
        Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx
    ) {
        return Ok(Vec::new());
    }
    let tree = match parse(language, text, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => tree,
        ParseResult::Unresolved(u) => return Err(ScanError::Parse(u.reason.to_string())),
    };
    let mut sites = Vec::new();
    let mut seen = HashSet::new();
    let mut stack = vec![tree.root()];
    while let Some(n) = stack.pop() {
        if let Some(func) = effect_callback(n, text) {
            let asynchronous = is_async(func);
            let returned = if asynchronous {
                Vec::new()
            } else {
                returns(func, text)
            };
            for a in acquires(func, &returned, text) {
                if !seen.insert(a.node.id()) {
                    continue;
                }
                if let Some((certainty, reason)) = judge(&a, &returned, asynchronous, text) {
                    sites.push(Site {
                        pair: a.pair.id,
                        range: span(a.node.start_byte(), a.node.end_byte()),
                        certainty,
                        reason,
                    });
                }
            }
        }
        stack.extend(named_children(n));
    }
    sites.sort_by_key(|s| (s.range.start(), s.pair));
    tracing::debug!(
        language = language.name(),
        sites = sites.len(),
        "unpaired effect acquires scanned"
    );
    Ok(sites)
}
