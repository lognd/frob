//! `UNITY201` and `UNITY202`: lookups and managed allocation in Unity hot code.
//!
//! Hot code is a per-frame or per-physics-step callback (`Update`, `LateUpdate`, `FixedUpdate`,
//! `OnGUI`, `OnAnimatorMove`, the `*Stay` collision and trigger messages) and every method of the
//! same class it calls, transitively (any overload; a generic helper too). `Awake`, `Start` and
//! `OnEnable` run once, so they are not roots: a helper reached only from them is clean, while one
//! also called from `Update` is reported. A coroutine helper (`IEnumerator`) is not followed, it
//! may run rarely, and a static method is never a root since Unity does not call it.
//!
//! - `UNITY201` reports a component or object lookup: `GetComponent`, `GetComponentInChildren`,
//!   `GetComponentInParent`, `GetComponents`, `TryGetComponent`, `FindObjectOfType` and its kin,
//!   `GameObject.Find*`, `transform.Find` and `Camera.main`. The remedy is to cache the result in
//!   `Awake`. An unqualified `Find*` the class defines itself is followed, not reported.
//! - `UNITY202` reports `new` of a managed collection (`List`, `Dictionary`, ...), a
//!   `StringBuilder` or `object`, or an array. Value types (`Vector3`) and unknown types are never
//!   reported. The remedy is a reused field or a pool.
//!
//! A lazy cache is exempt: assigning a field from the lookup or allocation under an `if` whose
//! condition tests null (or negates), or with `??=`, runs once. Lambda bodies inside a hot method
//! are scanned, since they usually run in that frame. Zero allocation as a global target is
//! contested, hence the rules are Advisory and the callers decide severity.

// frob:ticket CC940D3

use std::collections::{HashSet, VecDeque};

use gob_languages::Language;
use tree_sitter::Node;

use crate::res::{Certainty, ScanError, span, text};
use crate::unity::named_children;
use crate::unity_common::{Finding, live_named, walk};

/// The rule id of a lookup in hot code.
pub const RULE_LOOKUP: &str = "UNITY201";

/// The rule id of a managed allocation in hot code.
pub const RULE_ALLOC: &str = "UNITY202";

/// Messages Unity calls once per frame, physics step or while a contact persists.
const HOT_ROOTS: &[&str] = &[
    "Update",
    "LateUpdate",
    "FixedUpdate",
    "OnGUI",
    "OnAnimatorMove",
    "OnTriggerStay",
    "OnTriggerStay2D",
    "OnCollisionStay",
    "OnCollisionStay2D",
];

/// Lookups that walk components or the scene, on any receiver.
const LOOKUPS: &[&str] = &[
    "GetComponent",
    "GetComponents",
    "GetComponentInChildren",
    "GetComponentsInChildren",
    "GetComponentInParent",
    "GetComponentsInParent",
    "TryGetComponent",
    "FindObjectOfType",
    "FindObjectsOfType",
    "FindFirstObjectByType",
    "FindAnyObjectByType",
    "FindObjectsByType",
    "FindWithTag",
    "FindGameObjectWithTag",
    "FindGameObjectsWithTag",
];

/// Scene-wide lookups that, called unqualified, may be the class's own helper.
const SCENE_LOOKUPS: &[&str] = &[
    "FindObjectOfType",
    "FindObjectsOfType",
    "FindFirstObjectByType",
    "FindAnyObjectByType",
    "FindObjectsByType",
    "FindWithTag",
    "FindGameObjectWithTag",
    "FindGameObjectsWithTag",
];

/// Reference types that allocate on `new`.
const MANAGED_TYPES: &[&str] = &[
    "List",
    "Dictionary",
    "HashSet",
    "Queue",
    "Stack",
    "LinkedList",
    "SortedList",
    "SortedSet",
    "SortedDictionary",
    "StringBuilder",
    "object",
    "Object",
];

/// Where a hot method came from: its node and the root it was reached from.
struct Hot<'t> {
    method: Node<'t>,
    root: String,
}

/// The receiver text (`None` for an unqualified call) and method name of a call.
fn target(call: Node<'_>, src: &str) -> Option<(Option<String>, String)> {
    let f = call.child_by_field_name("function")?;
    let base = |n: Node<'_>| match n.kind() {
        "generic_name" => named_children(n).first().map(|k| text(*k, src).to_owned()),
        _ => Some(text(n, src).to_owned()),
    };
    match f.kind() {
        "identifier" | "generic_name" => Some((None, base(f)?)),
        "member_access_expression" => {
            let recv: String = text(f.child_by_field_name("expression")?, src)
                .split_whitespace()
                .collect();
            let name = base(f.child_by_field_name("name")?)?;
            if recv == "this" {
                return Some((None, name));
            }
            Some((
                Some(recv.strip_prefix("this.").unwrap_or(&recv).to_owned()),
                name,
            ))
        }
        "conditional_access_expression" => {
            let binding = named_children(f)
                .into_iter()
                .find(|c| c.kind() == "member_binding_expression")?;
            Some((
                Some("?".to_owned()),
                base(binding.child_by_field_name("name")?)?,
            ))
        }
        _ => None,
    }
}

/// True when a `Find` receiver is a `Transform` or the static `GameObject`.
fn is_transform_find(recv: &str) -> bool {
    recv == "GameObject" || recv.ends_with("transform") || recv.ends_with("Transform")
}

/// What the lookup at `n` is, when it is one.
fn lookup(n: Node<'_>, own: &HashSet<String>, src: &str) -> Option<String> {
    if n.kind() == "member_access_expression" {
        let recv: String = text(n.child_by_field_name("expression")?, src)
            .split_whitespace()
            .collect();
        let name = text(n.child_by_field_name("name")?, src);
        return (name == "main" && matches!(recv.as_str(), "Camera" | "UnityEngine.Camera"))
            .then(|| "Camera.main".to_owned());
    }
    if n.kind() != "invocation_expression" {
        return None;
    }
    let (recv, name) = target(n, src)?;
    let hit = match recv.as_deref() {
        None => {
            LOOKUPS.contains(&name.as_str())
                && !(SCENE_LOOKUPS.contains(&name.as_str()) && own.contains(&name))
        }
        Some(r) => LOOKUPS.contains(&name.as_str()) || (name == "Find" && is_transform_find(r)),
    };
    hit.then(|| format!("{name}()"))
}

/// The last name segment of a type, without generic arguments (`System.List<int>` gives `List`).
fn type_name(t: &str) -> String {
    let head = t.split('<').next().unwrap_or(t);
    head.rsplit('.').next().unwrap_or(head).trim().to_owned()
}

/// The type text a target-typed `new()` takes from its declaration or assigned field.
fn target_type(n: Node<'_>, field_types: &[(String, String)], src: &str) -> Option<String> {
    let parent = n.parent()?;
    match parent.kind() {
        "variable_declarator" => {
            let t = text(parent.parent()?.child_by_field_name("type")?, src);
            (t != "var").then(|| t.to_owned())
        }
        "assignment_expression" => {
            let left = text(parent.child_by_field_name("left")?, src);
            let left = left.strip_prefix("this.").unwrap_or(left);
            field_types
                .iter()
                .find(|(name, _)| name == left)
                .map(|(_, t)| t.clone())
        }
        _ => None,
    }
}

/// What the allocation at `n` is, when it is a managed one.
fn allocation(n: Node<'_>, field_types: &[(String, String)], src: &str) -> Option<String> {
    match n.kind() {
        "array_creation_expression" | "implicit_array_creation_expression" => {
            Some("a new array".to_owned())
        }
        "object_creation_expression" => {
            let t = type_name(text(n.child_by_field_name("type")?, src));
            MANAGED_TYPES
                .contains(&t.as_str())
                .then(|| format!("new {t}"))
        }
        "implicit_object_creation_expression" => {
            let t = type_name(&target_type(n, field_types, src)?);
            MANAGED_TYPES
                .contains(&t.as_str())
                .then(|| format!("new {t}"))
        }
        _ => None,
    }
}

/// The declared type of every field of the class body.
fn fields(body: Node<'_>, src: &str) -> Vec<(String, String)> {
    let mut out = Vec::new();
    for f in named_children(body)
        .into_iter()
        .filter(|f| f.kind() == "field_declaration")
    {
        for d in named_children(f)
            .into_iter()
            .filter(|d| d.kind() == "variable_declaration")
        {
            let Some(t) = d.child_by_field_name("type").map(|t| text(t, src)) else {
                continue;
            };
            for v in named_children(d)
                .into_iter()
                .filter(|v| v.kind() == "variable_declarator")
            {
                if let Some(name) = v.child_by_field_name("name") {
                    out.push((text(name, src).to_owned(), t.to_owned()));
                }
            }
        }
    }
    out
}

/// True when `cond` tests for null or negates, the guard of a lazy cache.
fn is_null_guard(cond: &str) -> bool {
    cond.contains("null") || cond.trim_start().starts_with('!')
}

/// True when the assignment `n` caches into a field, once.
fn is_lazy_cache(n: Node<'_>, lazy: bool, field_types: &[(String, String)], src: &str) -> bool {
    if n.kind() != "assignment_expression" {
        return false;
    }
    let Some(left) = n.child_by_field_name("left") else {
        return false;
    };
    let left = text(left, src);
    let left = left.strip_prefix("this.").unwrap_or(left);
    let op = n
        .child_by_field_name("operator")
        .map_or("=", |o| text(o, src));
    field_types.iter().any(|(name, _)| name == left) && (op == "??=" || (lazy && op == "="))
}

/// The class's methods, in source order, as `(name, node)`.
fn methods<'t>(body: Node<'t>, src: &str) -> Vec<(String, Node<'t>)> {
    live_named(body, src, &[])
        .into_iter()
        .filter(|m| m.kind() == "method_declaration")
        .filter_map(|m| Some((text(m.child_by_field_name("name")?, src).to_owned(), m)))
        .collect()
}

/// True for a `static` method or an `IEnumerator` coroutine.
fn is_static(m: Node<'_>, src: &str) -> bool {
    named_children(m)
        .into_iter()
        .any(|c| c.kind() == "modifier" && text(c, src) == "static")
}

/// True for a coroutine method.
fn is_coroutine(m: Node<'_>, src: &str) -> bool {
    m.child_by_field_name("returns")
        .is_some_and(|r| text(r, src).contains("IEnumerator"))
}

/// Scans one class declaration.
fn scan_class(class: Node<'_>, src: &str, out: &mut Vec<Finding>) {
    let Some(body) = class.child_by_field_name("body") else {
        return;
    };
    if is_static(class, src) {
        return;
    }
    let methods = methods(body, src);
    let own: HashSet<String> = methods.iter().map(|(n, _)| n.clone()).collect();
    let field_types = fields(body, src);
    let mut seen: HashSet<usize> = HashSet::new();
    let mut work: VecDeque<Hot<'_>> = methods
        .iter()
        .filter(|(name, m)| HOT_ROOTS.contains(&name.as_str()) && !is_static(*m, src))
        .map(|(name, m)| Hot {
            method: *m,
            root: name.clone(),
        })
        .collect();
    seen.extend(work.iter().map(|h| h.method.id()));
    while let Some(hot) = work.pop_front() {
        let Some(mbody) = hot.method.child_by_field_name("body") else {
            continue;
        };
        let mut stack = vec![(mbody, false)];
        while let Some((n, lazy)) = stack.pop() {
            if is_lazy_cache(n, lazy, &field_types, src) {
                tracing::debug!("lazy cache is exempt");
                continue;
            }
            let hit = lookup(n, &own, src)
                .map(|w| {
                    (
                        RULE_LOOKUP,
                        format!(
                            "{w} runs every frame (reachable from {}); cache the result in Awake",
                            hot.root
                        ),
                    )
                })
                .or_else(|| {
                    allocation(n, &field_types, src).map(|w| {
                        (
                            RULE_ALLOC,
                            format!(
                                "{w} allocates every frame (reachable from {}); reuse a field or a pool",
                                hot.root
                            ),
                        )
                    })
                });
            if let Some((rule, message)) = hit {
                out.push(Finding {
                    rule,
                    range: span(n.start_byte(), n.end_byte()),
                    certainty: Certainty::Certain,
                    message,
                });
            }
            if n.kind() == "invocation_expression"
                && let Some((None, name)) = target(n, src)
            {
                for (mn, m) in &methods {
                    if *mn == name && !is_coroutine(*m, src) && seen.insert(m.id()) {
                        work.push_back(Hot {
                            method: *m,
                            root: hot.root.clone(),
                        });
                    }
                }
            }
            let cond = (n.kind() == "if_statement")
                .then(|| n.child_by_field_name("condition"))
                .flatten();
            let guarded = cond.is_some_and(|c| is_null_guard(text(c, src)));
            let consequence = n.child_by_field_name("consequence").map(|c| c.id());
            for c in live_named(n, src, &[]) {
                let under = lazy || (guarded && Some(c.id()) == consequence);
                stack.push((c, under));
            }
        }
    }
}

/// Every lookup and managed allocation in hot code of `src`, in source order.
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
    out.dedup_by_key(|f| (f.range, f.rule));
    tracing::debug!(findings = out.len(), "hot-path code scanned");
    Ok(out)
}
