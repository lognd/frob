//! `UNITY302`: a Rigidbody force or move applied from `Update` or `LateUpdate` instead of
//! `FixedUpdate`.
//!
//! Physics steps on the fixed timestep, so a force applied once per rendered frame scales with the
//! frame rate. The scan follows calls to methods of the same class (a coroutine helper is skipped,
//! it may wait on `WaitForFixedUpdate`) and reports:
//!
//! - `AddForce`-style calls and `MovePosition`/`MoveRotation` on a receiver known to be a body;
//!   a force-style call on a receiver that cannot be resolved is Unknown (Unresolved), never Warn;
//! - `transform.position`, `transform.rotation`, `Translate` and `Rotate` in a class that has
//!   Rigidbody evidence and does not make the body kinematic.
//!
//! A one-shot `ForceMode.Impulse` or `VelocityChange` under an edge-triggered input check
//! (`GetKeyDown`, `wasPressedThisFrame`, ...) is exempt: it runs once per press, not per frame.

// frob:ticket 01M4D94ZPDYBATXNCVY3XRQ6RM

use std::collections::HashSet;

use gob_languages::Language;
use tree_sitter::Node;

use crate::res::{Certainty, ScanError, span, text};
use crate::unity::{arguments_of, declared_type, last_segment, member_call, named_children};
use crate::unity_common::{Finding, live_named, walk};

/// The rule id reported on every finding.
pub const RULE: &str = "UNITY302";

/// Methods that run once per rendered frame.
const FRAME_ROOTS: &[&str] = &["Update", "LateUpdate"];

/// Force and torque methods of a body.
const FORCES: &[&str] = &[
    "AddForce",
    "AddRelativeForce",
    "AddTorque",
    "AddRelativeTorque",
    "AddForceAtPosition",
    "AddExplosionForce",
];

/// Kinematic move methods of a body.
const MOVES: &[&str] = &["MovePosition", "MoveRotation"];

/// `Transform` calls that move or turn it.
const TRANSFORM_CALLS: &[&str] = &["Translate", "Rotate"];

/// `Transform` members whose assignment moves or turns it.
const TRANSFORM_TARGETS: &[&str] = &["transform.position", "transform.rotation"];

/// Condition fragments that fire once per press rather than every frame.
const EDGE_TRIGGERS: &[&str] = &[
    "GetKeyDown",
    "GetButtonDown",
    "GetMouseButtonDown",
    "wasPressedThisFrame",
    "WasPressedThisFrame",
    "WasPerformedThisFrame",
    "wasReleasedThisFrame",
    "triggered",
];

/// Force modes that apply a single instantaneous push.
const ONE_SHOT_MODES: &[&str] = &["Impulse", "VelocityChange"];

/// Type-name fragments of a physics body.
const BODY_TYPES: &[&str] = &["Rigidbody", "ArticulationBody"];

/// Members of other components that hand back a body.
const BODY_MEMBERS: &[&str] = &["rigidbody", "rigidbody2D", "attachedRigidbody"];

/// What a call receiver is known to be.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Receiver {
    Body,
    Other,
    Unresolved,
}

/// The initializer text of the local or field `name`, if it has one.
fn initializer(class: Node<'_>, name: &str, src: &str) -> Option<String> {
    let mut stack = vec![class];
    while let Some(n) = stack.pop() {
        if n.kind() == "variable_declarator"
            && n.child_by_field_name("name")
                .is_some_and(|c| text(c, src) == name)
        {
            return text(n, src).split_once('=').map(|(_, v)| v.to_owned());
        }
        stack.extend(named_children(n));
    }
    None
}

/// Whether `recv` is a physics body, judged from names, `GetComponent` and declared types.
fn classify(recv: &str, class: Node<'_>, src: &str) -> Receiver {
    let r = recv.strip_prefix("this.").unwrap_or(recv);
    if BODY_MEMBERS.contains(&last_segment(r))
        || BODY_TYPES.iter().any(|t| r.contains(&format!("<{t}")))
    {
        return Receiver::Body;
    }
    if r.contains('.') || r.contains('(') {
        return Receiver::Unresolved;
    }
    match declared_type(class, r, src) {
        Some(t) if t == "var" => {
            let init = initializer(class, r, src).unwrap_or_default();
            if BODY_TYPES.iter().any(|b| init.contains(&format!("<{b}"))) {
                Receiver::Body
            } else {
                Receiver::Unresolved
            }
        }
        Some(t) if BODY_TYPES.iter().any(|b| t.contains(b)) => Receiver::Body,
        Some(_) => Receiver::Other,
        None => Receiver::Unresolved,
    }
}

/// Class-wide facts about whether `transform` motion fights a physics body.
struct BodyFacts {
    has_body: bool,
    kinematic: bool,
}

fn body_facts(class: Node<'_>, src: &str) -> BodyFacts {
    let compact: String = text(class, src).split_whitespace().collect();
    let mut typed = false;
    let mut stack = vec![class];
    while let Some(n) = stack.pop() {
        if matches!(
            n.kind(),
            "variable_declaration" | "property_declaration" | "parameter"
        ) && n
            .child_by_field_name("type")
            .is_some_and(|t| BODY_TYPES.iter().any(|b| text(t, src).contains(b)))
        {
            typed = true;
        }
        stack.extend(named_children(n));
    }
    let facts = BodyFacts {
        has_body: typed
            || BODY_TYPES.iter().any(|b| {
                compact.contains(&format!("<{b}")) || compact.contains(&format!("typeof({b}"))
            }),
        kinematic: compact.contains("isKinematic=true")
            || compact.contains("RigidbodyType2D.Kinematic"),
    };
    tracing::debug!(
        has_body = facts.has_body,
        kinematic = facts.kinematic,
        "body facts"
    );
    facts
}

/// True when the condition fires once per press rather than every frame.
fn is_edge_trigger(cond: &str) -> bool {
    EDGE_TRIGGERS.iter().any(|t| cond.contains(t))
}

/// True when a call's `ForceMode` argument is a one-shot mode.
fn is_one_shot(call: Node<'_>, src: &str) -> bool {
    arguments_of(call).iter().any(|a| {
        let t = text(*a, src);
        t.starts_with("ForceMode") && ONE_SHOT_MODES.iter().any(|m| t.ends_with(m))
    })
}

/// The method an unqualified or `this.` call names.
fn callee(call: Node<'_>, src: &str) -> Option<String> {
    let f = text(call.child_by_field_name("function")?, src);
    let f = f.strip_prefix("this.").unwrap_or(f);
    (!f.contains('.') && !f.contains('<')).then(|| f.to_owned())
}

/// The finding for `n` when it is a force or move reachable from a frame root.
fn judge(
    n: Node<'_>,
    guarded: bool,
    class: Node<'_>,
    facts: &BodyFacts,
    src: &str,
) -> Option<Finding> {
    let range = span(n.start_byte(), n.end_byte());
    let found = |certainty, what: &str| {
        Some(Finding {
            rule: RULE,
            range,
            certainty,
            message: format!(
                "{what} runs every rendered frame in Update; apply physics from FixedUpdate"
            ),
        })
    };
    if n.kind() == "assignment_expression" {
        let left = n.child_by_field_name("left")?;
        let target = text(left, src);
        let target = target.strip_prefix("this.").unwrap_or(target);
        return (TRANSFORM_TARGETS.contains(&target) && facts.has_body && !facts.kinematic)
            .then(|| {
                found(
                    Certainty::Certain,
                    &format!("Assigning {target} of a Rigidbody object"),
                )
            })
            .flatten();
    }
    let call = member_call(n, src)?;
    let recv = call.receiver.as_str();
    if TRANSFORM_CALLS.contains(&call.name.as_str()) && recv == "transform" {
        return (facts.has_body && !facts.kinematic)
            .then(|| {
                found(
                    Certainty::Certain,
                    &format!("transform.{} on a Rigidbody object", call.name),
                )
            })
            .flatten();
    }
    let is_force = FORCES.contains(&call.name.as_str());
    if !is_force && !MOVES.contains(&call.name.as_str()) {
        return None;
    }
    if guarded && is_one_shot(n, src) {
        tracing::debug!("one-shot impulse under an edge trigger is exempt");
        return None;
    }
    let what = format!("{}.{}", recv, call.name);
    match classify(recv, class, src) {
        Receiver::Body => found(Certainty::Certain, &what),
        Receiver::Unresolved if is_force => found(Certainty::Unknown, &what),
        Receiver::Unresolved | Receiver::Other => None,
    }
}

/// Scans one class declaration.
fn scan_class(class: Node<'_>, src: &str, out: &mut Vec<Finding>) {
    let Some(body) = class.child_by_field_name("body") else {
        return;
    };
    let methods: Vec<(String, Node<'_>)> = live_named(body, src, &[])
        .into_iter()
        .filter(|m| m.kind() == "method_declaration")
        .filter_map(|m| Some((text(m.child_by_field_name("name")?, src).to_owned(), m)))
        .collect();
    let facts = body_facts(class, src);
    let mut seen: HashSet<(String, bool)> = HashSet::new();
    let mut work: Vec<(Node<'_>, bool)> = methods
        .iter()
        .filter(|(name, _)| FRAME_ROOTS.contains(&name.as_str()))
        .map(|(_, m)| (*m, false))
        .collect();
    while let Some((method, guard)) = work.pop() {
        let Some(mbody) = method.child_by_field_name("body") else {
            continue;
        };
        let mut stack = vec![(mbody, guard)];
        while let Some((n, g)) = stack.pop() {
            out.extend(judge(n, g, class, &facts, src));
            if n.kind() == "invocation_expression"
                && let Some(name) = callee(n, src)
                && let Some((_, m)) = methods.iter().find(|(mn, _)| *mn == name)
                && !m
                    .child_by_field_name("returns")
                    .is_some_and(|r| text(r, src).contains("IEnumerator"))
                && seen.insert((name, g))
            {
                work.push((*m, g));
            }
            let cond = (n.kind() == "if_statement")
                .then(|| n.child_by_field_name("condition"))
                .flatten();
            let edge = cond.is_some_and(|c| is_edge_trigger(text(c, src)));
            for c in live_named(n, src, &[]) {
                let under = g || (edge && Some(c.id()) != cond.map(|x| x.id()));
                stack.push((c, under));
            }
        }
    }
}

/// Every Rigidbody force or move that runs per rendered frame in `src`, in source order.
///
/// A language other than C# yields nothing.
///
/// # Errors
///
/// [`ScanError::Parse`] when the file does not parse within the limits.
pub fn scan(language: Language, src: &str) -> Result<Vec<Finding>, ScanError> {
    let mut out = Vec::new();
    walk(language, src, &[], |n| {
        if n.kind() == "class_declaration" {
            scan_class(n, src, &mut out);
        }
    })?;
    out.sort_by_key(|f| f.range.start());
    out.dedup_by_key(|f| f.range);
    tracing::debug!(findings = out.len(), "per-frame physics scanned");
    Ok(out)
}
