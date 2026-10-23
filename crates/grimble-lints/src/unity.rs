//! Unity lifecycle pairing: a subscription or acquire made in `Awake`, `Start` or `OnEnable` that no
//! teardown root (`OnDisable`, `OnDestroy`) undoes (PAIR001, Unity vocabulary).
//!
//! The pairs live in the [`PAIRS`] table, so a new Unity acquire is a data change. The check is
//! structural and per class: it reads the setup roots, then the teardown roots (following calls to
//! methods of the same class), and pairs each acquire with a release.
//!
//! - An anonymous handler (`ev += x => ..`) can never be removed by text, so it is Unknown.
//! - A release under a branch or loop in the teardown root is conditional, so it is Unknown.
//! - A release of a different event, handler, receiver or handle does not pair the acquire.
//! - A `+=` counts as a subscription only when the target is a declared or well-known event, the
//!   handler is a method of the class or an anonymous function; `total += value` is arithmetic.
//! - A `partial` class may release in another part this file cannot see, so its sites are Unknown.
//! - Static events pair by their full target text (`GameManager.OnWin`).

// frob:ticket 01M4D955ZSR7MHM6TXXD49JJ4V

use std::collections::HashSet;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gob_text::TextRange;
use tree_sitter::Node;

use crate::res::{Certainty, ScanError, count_word, normalise, span, text};

/// How a release is tied to its acquire.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tie {
    /// `target += handler` paired by a `-=` of the same target and handler.
    Event,
    /// Same receiver, same first argument (and same type arguments when both name them).
    Handler,
    /// Same receiver, any arguments.
    Receiver,
    /// The release names the handle the acquire returned.
    HandleArg,
}

/// How an acquire is recognised.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Start {
    /// `target += handler`.
    Event,
    /// A call of one of `names`, on `receiver` when given.
    Method {
        /// The required receiver text (`Addressables`), or any receiver.
        receiver: Option<&'static str>,
        /// The acquiring method names, type arguments ignored.
        names: &'static [&'static str],
    },
}

/// One Unity acquire and the release that pairs it.
#[derive(Debug, Clone, Copy)]
pub struct Pair {
    /// Stable pair id, reported on every site.
    pub id: &'static str,
    /// The acquire.
    pub start: Start,
    /// Release method names, type arguments ignored (empty for events, which use `-=`).
    pub release: &'static [&'static str],
    /// Methods that release every acquire on the same receiver (`RemoveAllListeners`).
    pub clears: &'static [&'static str],
    /// How the release is tied to the acquire.
    pub tie: Tie,
    /// A type-name fragment the receiver's declared type must carry to be certain.
    pub type_hint: Option<&'static str>,
}

/// Methods in which an acquire is made.
const SETUP_ROOTS: &[&str] = &["Awake", "OnEnable", "Start"];

/// Methods in which a release must be made.
const TEARDOWN_ROOTS: &[&str] = &["OnDisable", "OnDestroy"];

/// Event names that are subscriptions even when declared in another file.
const KNOWN_EVENTS: &[&str] = &[
    "performed",
    "started",
    "canceled",
    "sceneLoaded",
    "sceneUnloaded",
    "activeSceneChanged",
    "onClick",
    "onValueChanged",
    "onSubmit",
    "onEndEdit",
    "logMessageReceived",
    "applicationFocusChanged",
    "Completed",
];

/// Receiver-name fragments that make an untyped `Enable()` look like an input action.
const ACTION_NAME_HINTS: &[&str] = &["action", "input", "control"];

/// The Unity acquire/release table (the Unity vocabulary of PAIR001).
pub const PAIRS: &[Pair] = &[
    Pair {
        id: "event-subscription",
        start: Start::Event,
        release: &[],
        clears: &[],
        tie: Tie::Event,
        type_hint: None,
    },
    Pair {
        id: "register-callback",
        start: Start::Method {
            receiver: None,
            names: &["RegisterCallback", "RegisterValueChangedCallback"],
        },
        release: &["UnregisterCallback", "UnregisterValueChangedCallback"],
        clears: &[],
        tie: Tie::Handler,
        type_hint: None,
    },
    Pair {
        id: "unity-event-listener",
        start: Start::Method {
            receiver: None,
            names: &["AddListener"],
        },
        release: &["RemoveListener"],
        clears: &["RemoveAllListeners"],
        tie: Tie::Handler,
        type_hint: None,
    },
    Pair {
        id: "input-action-enable",
        start: Start::Method {
            receiver: None,
            names: &["Enable"],
        },
        release: &["Disable"],
        clears: &[],
        tie: Tie::Receiver,
        type_hint: Some("InputAction"),
    },
    Pair {
        id: "addressables-handle",
        start: Start::Method {
            receiver: Some("Addressables"),
            names: &["LoadAssetAsync", "LoadAssetsAsync", "LoadSceneAsync"],
        },
        release: &["Release", "UnloadSceneAsync"],
        clears: &[],
        tie: Tie::HandleArg,
        type_hint: None,
    },
    Pair {
        id: "addressables-instance",
        start: Start::Method {
            receiver: Some("Addressables"),
            names: &["InstantiateAsync"],
        },
        release: &["ReleaseInstance", "Release"],
        clears: &[],
        tie: Tie::Receiver,
        type_hint: None,
    },
];

/// Why an acquire is reported.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Reason {
    /// The class has no `OnDisable` or `OnDestroy` at all.
    NoTeardown,
    /// A teardown root exists but releases something else.
    TeardownMissesAcquire,
    /// The only pairing release sits under a branch or loop, so another path leaks.
    ConditionalTeardown,
    /// The handler is an anonymous function, which no release can name.
    AnonymousHandler,
    /// The acquire's handle is not bound to a name, so no release can be matched to it.
    UnboundHandle,
}

/// One Unity acquire with no pairing release.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Site {
    /// The [`Pair::id`] that is unpaired.
    pub pair: &'static str,
    /// The acquire, as byte offsets in the scanned text.
    pub range: TextRange,
    /// The name of the first teardown root where the release belongs, if the class has one.
    pub teardown: Option<TextRange>,
    /// Whether the syntax alone decides it.
    pub certainty: Certainty,
    /// Why the acquire is reported.
    pub reason: Reason,
}

/// An acquire found in a setup root.
struct Acquire<'t> {
    pair: &'static Pair,
    node: Node<'t>,
    receiver: String,
    generics: Option<String>,
    /// The handler: the `+=` right side, or the first call argument.
    handler: Option<Node<'t>>,
    bound: Option<String>,
    certainty: Certainty,
}

/// A release found in a teardown root.
struct Release {
    receiver: String,
    /// `-=`, or the method name without type arguments.
    name: String,
    generics: Option<String>,
    args: Vec<String>,
    conditional: bool,
}

pub(crate) fn named_children(n: Node<'_>) -> Vec<Node<'_>> {
    let mut cur = n.walk();
    n.named_children(&mut cur)
        .filter(|c| c.kind() != "comment")
        .collect()
}

fn is_anonymous(n: Node<'_>) -> bool {
    matches!(
        n.kind(),
        "lambda_expression" | "anonymous_method_expression"
    )
}

fn is_nested_function(n: Node<'_>) -> bool {
    is_anonymous(n) || n.kind() == "local_function_statement"
}

fn is_branch(n: Node<'_>) -> bool {
    matches!(
        n.kind(),
        "if_statement"
            | "switch_statement"
            | "for_statement"
            | "foreach_statement"
            | "while_statement"
            | "do_statement"
            | "conditional_expression"
            | "switch_expression"
            | "catch_clause"
            | "conditional_access_expression"
    )
}

/// The expression an `argument` node wraps (the node itself for anything else).
fn unity_arg_expr(arg: Node<'_>) -> Node<'_> {
    if arg.kind() == "argument" {
        named_children(arg).first().copied().unwrap_or(arg)
    } else {
        arg
    }
}

pub(crate) fn arguments_of(call: Node<'_>) -> Vec<Node<'_>> {
    call.child_by_field_name("arguments")
        .map(|a| {
            named_children(a)
                .into_iter()
                .map(|a| unity_arg_expr(a))
                .collect()
        })
        .unwrap_or_default()
}

/// The last dotted segment of a target (`GameManager.OnWin` gives `OnWin`).
pub(crate) fn last_segment(s: &str) -> &str {
    s.rsplit('.').next().unwrap_or(s).trim()
}

/// A member call split into receiver, method name and type arguments.
pub(crate) struct MemberCall {
    pub(crate) receiver: String,
    pub(crate) name: String,
    pub(crate) generics: Option<String>,
}

pub(crate) fn member_call(call: Node<'_>, src: &str) -> Option<MemberCall> {
    let f = call.child_by_field_name("function")?;
    if f.kind() != "member_access_expression" {
        return None;
    }
    let obj = f.child_by_field_name("expression")?;
    let name = f.child_by_field_name("name")?;
    let (base, generics) = if name.kind() == "generic_name" {
        let kids = named_children(name);
        let base = kids.first().map(|k| text(*k, src).to_owned())?;
        let args = kids
            .iter()
            .find(|k| k.kind() == "type_argument_list")
            .map(|k| text(*k, src).to_owned());
        (base, args)
    } else {
        (text(name, src).to_owned(), None)
    };
    Some(MemberCall {
        receiver: normalise(text(obj, src)),
        name: base,
        generics,
    })
}

/// The name an acquire's result is bound to (`var h = ..`, `h = ..`), looking through `await`.
fn bound_name(node: Node<'_>, src: &str) -> Option<String> {
    let mut cur = node;
    let mut parent = node.parent()?;
    while matches!(
        parent.kind(),
        "await_expression" | "parenthesized_expression" | "cast_expression"
    ) {
        cur = parent;
        parent = parent.parent()?;
    }
    match parent.kind() {
        "variable_declarator" => parent
            .child_by_field_name("name")
            .map(|n| normalise(text(n, src))),
        "assignment_expression"
            if parent
                .child_by_field_name("right")
                .is_some_and(|r| r.id() == cur.id()) =>
        {
            parent
                .child_by_field_name("left")
                .map(|n| normalise(text(n, src)))
        }
        _ => None,
    }
}

/// Per-class facts the acquire filter needs.
struct ClassFacts {
    methods: HashSet<String>,
    events: HashSet<String>,
}

fn class_facts(body: Node<'_>, src: &str) -> ClassFacts {
    let mut facts = ClassFacts {
        methods: HashSet::new(),
        events: HashSet::new(),
    };
    for m in named_children(body) {
        match m.kind() {
            "method_declaration" => {
                if let Some(n) = m.child_by_field_name("name") {
                    facts.methods.insert(text(n, src).to_owned());
                }
            }
            "event_field_declaration" | "event_declaration" => {
                let mut stack = vec![m];
                while let Some(n) = stack.pop() {
                    if matches!(n.kind(), "variable_declarator" | "event_declaration")
                        && let Some(name) = n.child_by_field_name("name")
                    {
                        facts.events.insert(text(name, src).to_owned());
                    }
                    stack.extend(named_children(n));
                }
            }
            _ => {}
        }
    }
    facts
}

/// True when `target += handler` is a subscription rather than arithmetic.
fn is_subscription(target: &str, handler: Node<'_>, facts: &ClassFacts, src: &str) -> bool {
    let last = last_segment(target);
    let on_style = last
        .strip_prefix("On")
        .or_else(|| last.strip_prefix("on"))
        .and_then(|rest| rest.chars().next())
        .is_some_and(char::is_uppercase);
    is_anonymous(handler)
        || facts.events.contains(last)
        || KNOWN_EVENTS.contains(&last)
        || on_style
        || (matches!(handler.kind(), "identifier" | "member_access_expression")
            && facts.methods.contains(last_segment(text(handler, src))))
}

/// The declared type text of the variable, field, property or parameter `name` in `class`.
pub(crate) fn declared_type(class: Node<'_>, name: &str, src: &str) -> Option<String> {
    let mut stack = vec![class];
    while let Some(n) = stack.pop() {
        let named = |field: &str| {
            n.child_by_field_name(field)
                .is_some_and(|c| text(c, src) == name)
        };
        match n.kind() {
            "property_declaration" | "parameter" if named("name") => {
                return n
                    .child_by_field_name("type")
                    .map(|t| text(t, src).to_owned());
            }
            "variable_declaration" => {
                let declares = named_children(n).into_iter().any(|d| {
                    d.kind() == "variable_declarator" && {
                        d.child_by_field_name("name")
                            .is_some_and(|c| text(c, src) == name)
                    }
                });
                if declares {
                    return n
                        .child_by_field_name("type")
                        .map(|t| text(t, src).to_owned());
                }
            }
            _ => {}
        }
        stack.extend(named_children(n));
    }
    None
}

/// How sure the acquire is: a typed receiver is certain, a name hint is Unknown, else not an acquire.
fn gate(pair: &Pair, receiver: &str, class: Node<'_>, src: &str) -> Option<Certainty> {
    let Some(hint) = pair.type_hint else {
        return Some(Certainty::Certain);
    };
    let last = last_segment(receiver);
    if declared_type(class, last, src).is_some_and(|t| t.contains(hint)) {
        return Some(Certainty::Certain);
    }
    let lower = last.to_lowercase();
    ACTION_NAME_HINTS
        .iter()
        .any(|h| lower.contains(h))
        .then_some(Certainty::Unknown)
}

fn event_acquire<'t>(n: Node<'t>, facts: &ClassFacts, src: &str) -> Option<Acquire<'t>> {
    if n.kind() != "assignment_expression" {
        return None;
    }
    let op = n.child_by_field_name("operator")?;
    let left = n.child_by_field_name("left")?;
    let right = n.child_by_field_name("right")?;
    let target = normalise(text(left, src));
    if text(op, src) != "+=" || !is_subscription(&target, right, facts, src) {
        return None;
    }
    Some(Acquire {
        pair: &PAIRS[0],
        node: n,
        receiver: target,
        generics: None,
        handler: Some(right),
        bound: None,
        certainty: Certainty::Certain,
    })
}

fn call_acquire<'t>(n: Node<'t>, class: Node<'t>, src: &str) -> Option<Acquire<'t>> {
    if n.kind() != "invocation_expression" {
        return None;
    }
    let call = member_call(n, src)?;
    let pair = PAIRS.iter().find(|p| match p.start {
        Start::Method { receiver, names } => {
            names.contains(&call.name.as_str()) && receiver.is_none_or(|r| r == call.receiver)
        }
        Start::Event => false,
    })?;
    let certainty = gate(pair, &call.receiver, class, src)?;
    Some(Acquire {
        pair,
        node: n,
        receiver: call.receiver,
        generics: call.generics,
        handler: arguments_of(n).first().copied(),
        bound: bound_name(n, src),
        certainty,
    })
}

/// Acquires in the body of one setup root, skipping nested functions.
fn acquires_in<'t>(
    body: Node<'t>,
    class: Node<'t>,
    facts: &ClassFacts,
    src: &str,
) -> Vec<Acquire<'t>> {
    let mut out = Vec::new();
    let mut stack = vec![body];
    while let Some(n) = stack.pop() {
        if let Some(a) = event_acquire(n, facts, src).or_else(|| call_acquire(n, class, src)) {
            out.push(a);
        }
        stack.extend(
            named_children(n)
                .into_iter()
                .filter(|c| !is_nested_function(*c)),
        );
    }
    out
}

/// The methods of the class by name.
fn methods_of<'t>(body: Node<'t>, src: &str) -> Vec<(String, Node<'t>)> {
    named_children(body)
        .into_iter()
        .filter(|m| m.kind() == "method_declaration")
        .filter_map(|m| {
            let name = text(m.child_by_field_name("name")?, src).to_owned();
            Some((name, m))
        })
        .collect()
}

/// The callee name when `call` is `Helper()` or `this.Helper()`.
fn local_callee(call: Node<'_>, src: &str) -> Option<String> {
    let f = call.child_by_field_name("function")?;
    let t = normalise(text(f, src));
    (!t.contains('.') && !t.contains('<')).then_some(t)
}

/// Every release reachable from the teardown roots, following calls to methods of the class.
fn releases(methods: &[(String, Node<'_>)], src: &str) -> Vec<Release> {
    let mut out = Vec::new();
    let mut visited: HashSet<String> = HashSet::new();
    let mut work: Vec<(Node<'_>, bool)> = Vec::new();
    for (name, m) in methods {
        if TEARDOWN_ROOTS.contains(&name.as_str()) {
            visited.insert(name.clone());
            work.push((*m, false));
        }
    }
    while let Some((start, start_cond)) = work.pop() {
        let mut stack = vec![(start, start_cond)];
        while let Some((n, cond)) = stack.pop() {
            if is_nested_function(n) {
                continue;
            }
            collect_release(n, cond, src, &mut out);
            if n.kind() == "invocation_expression"
                && let Some(callee) = local_callee(n, src)
                && let Some((_, m)) = methods.iter().find(|(name, _)| *name == callee)
                && visited.insert(callee)
            {
                work.push((*m, cond));
            }
            let child_cond = cond || is_branch(n);
            stack.extend(named_children(n).into_iter().map(|c| (c, child_cond)));
        }
    }
    out
}

fn collect_release(n: Node<'_>, conditional: bool, src: &str, out: &mut Vec<Release>) {
    if n.kind() == "assignment_expression"
        && n.child_by_field_name("operator")
            .is_some_and(|o| text(o, src) == "-=")
        && let (Some(left), Some(right)) = (
            n.child_by_field_name("left"),
            n.child_by_field_name("right"),
        )
    {
        out.push(Release {
            receiver: normalise(text(left, src)),
            name: "-=".to_owned(),
            generics: None,
            args: vec![normalise(text(right, src))],
            conditional,
        });
    } else if n.kind() == "invocation_expression"
        && let Some(call) = member_call(n, src)
    {
        out.push(Release {
            receiver: call.receiver,
            name: call.name,
            generics: call.generics,
            args: arguments_of(n)
                .into_iter()
                .map(|a| normalise(text(a, src)))
                .collect(),
            conditional,
        });
    }
}

/// True when release `r` pairs acquire `a`.
fn pairs(a: &Acquire<'_>, r: &Release, src: &str) -> bool {
    let pair = a.pair;
    if r.receiver == a.receiver && pair.clears.contains(&r.name.as_str()) {
        return true;
    }
    let handler = a.handler.map(|h| normalise(text(h, src)));
    match pair.tie {
        Tie::Event => {
            r.name == "-=" && r.receiver == a.receiver && r.args.first() == handler.as_ref()
        }
        Tie::Handler => {
            pair.release.contains(&r.name.as_str())
                && r.receiver == a.receiver
                && r.args.first() == handler.as_ref()
                && (a.generics.is_none() || r.generics.is_none() || a.generics == r.generics)
        }
        Tie::Receiver => pair.release.contains(&r.name.as_str()) && r.receiver == a.receiver,
        Tie::HandleArg => {
            pair.release.contains(&r.name.as_str())
                && a.bound
                    .as_ref()
                    .is_some_and(|b| r.args.iter().any(|x| count_word(x, b) > 0))
        }
    }
}

fn judge(
    a: &Acquire<'_>,
    rels: &[Release],
    has_teardown: bool,
    src: &str,
) -> Option<(Certainty, Reason)> {
    if matches!(a.pair.tie, Tie::Event | Tie::Handler) && a.handler.is_some_and(is_anonymous) {
        return Some((Certainty::Unknown, Reason::AnonymousHandler));
    }
    if a.pair.tie == Tie::HandleArg && a.bound.is_none() {
        return Some((Certainty::Unknown, Reason::UnboundHandle));
    }
    let hits: Vec<&Release> = rels.iter().filter(|r| pairs(a, r, src)).collect();
    if hits.iter().any(|r| !r.conditional) {
        return None;
    }
    if !hits.is_empty() {
        return Some((Certainty::Unknown, Reason::ConditionalTeardown));
    }
    let reason = if has_teardown {
        Reason::TeardownMissesAcquire
    } else {
        Reason::NoTeardown
    };
    Some((a.certainty, reason))
}

/// True when the class declaration carries the `partial` modifier.
fn is_partial(class: Node<'_>, src: &str) -> bool {
    named_children(class)
        .iter()
        .any(|c| c.kind() == "modifier" && text(*c, src) == "partial")
}

/// Scans one class declaration.
fn scan_class(class: Node<'_>, src: &str, out: &mut Vec<Site>) {
    let Some(body) = class.child_by_field_name("body") else {
        return;
    };
    let partial = is_partial(class, src);
    let methods = methods_of(body, src);
    let facts = class_facts(body, src);
    let rels = releases(&methods, src);
    let teardown = methods
        .iter()
        .find(|(name, _)| TEARDOWN_ROOTS.contains(&name.as_str()))
        .and_then(|(_, m)| m.child_by_field_name("name"))
        .map(|n| span(n.start_byte(), n.end_byte()));
    for (name, m) in &methods {
        if !SETUP_ROOTS.contains(&name.as_str()) {
            continue;
        }
        let Some(mbody) = m.child_by_field_name("body") else {
            continue;
        };
        for a in acquires_in(mbody, class, &facts, src) {
            if let Some((mut certainty, reason)) = judge(&a, &rels, teardown.is_some(), src) {
                // The release may sit in another part of a partial class, which this file cannot see.
                if partial {
                    certainty = Certainty::Unknown;
                }
                out.push(Site {
                    pair: a.pair.id,
                    range: span(a.node.start_byte(), a.node.end_byte()),
                    teardown,
                    certainty,
                    reason,
                });
            }
        }
    }
}

/// Every Unity acquire in `text` parsed as `language` with no pairing release, in source order.
///
/// A language other than C# yields no sites; a tree with syntax errors is still scanned.
///
/// # Errors
///
/// [`ScanError::Parse`] when the file does not parse within the limits.
pub fn scan(language: Language, text: &str) -> Result<Vec<Site>, ScanError> {
    if language != Language::CSharp {
        return Ok(Vec::new());
    }
    let tree = match parse(language, text, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => tree,
        ParseResult::Unresolved(u) => return Err(ScanError::Parse(u.reason.to_string())),
    };
    let mut sites = Vec::new();
    let mut stack = vec![tree.root()];
    while let Some(n) = stack.pop() {
        if n.kind() == "class_declaration" {
            scan_class(n, text, &mut sites);
        }
        stack.extend(named_children(n));
    }
    sites.sort_by_key(|s| (s.range.start(), s.pair));
    tracing::debug!(
        language = language.name(),
        sites = sites.len(),
        "unpaired unity acquires scanned"
    );
    Ok(sites)
}
