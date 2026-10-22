//! An order-preserving document tree and an RFC 6902 engine addressed by stable id.
//!
//! `crunk edit` reads a design file (TOML) into a [`Node`], applies a JSON Patch to a clone and
//! only then lets the caller validate and write the result, so a failed operation leaves the
//! original untouched. A path segment that is not an index or `-` names an array element by its
//! `id` (or, failing that, `name`) field: `/key/hero.title/text` edits the `text` of the content
//! key whose `id` is `hero.title`.

// frob:ticket 01M4CXRA570ABD65ZDFAFVVZ8Y

use std::collections::BTreeSet;

use indexmap::IndexMap;
use serde::{Deserialize, Serialize};

/// Fields that name an array element, in lookup order.
const ID_FIELDS: [&str; 2] = ["id", "name"];

/// Fields whose string value counts as the id of a touched object, in report order.
const TOUCH_FIELDS: [&str; 3] = ["id", "name", "node"];

/// A TOML value with table keys kept in file order.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Node {
    /// A boolean.
    Bool(bool),
    /// An integer.
    Int(i64),
    /// A float.
    Float(f64),
    /// A string.
    Str(String),
    /// An array (also an array of tables).
    Arr(Vec<Node>),
    /// A table.
    Map(IndexMap<String, Node>),
}

/// One RFC 6902 operation as written in the patch file.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Op {
    /// `add`, `remove`, `replace`, `move`, `copy` or `test`.
    pub op: String,
    /// The JSON Pointer the operation targets.
    pub path: String,
    /// Source pointer of `move` and `copy`.
    #[serde(default)]
    pub from: Option<String>,
    /// Operand of `add`, `replace` and `test`.
    #[serde(default)]
    pub value: Option<serde_json::Value>,
}

/// Why a patch could not be applied; every variant leaves the document unchanged.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum PatchError {
    /// The patch text is not a JSON array of operations.
    #[error("the patch is not a JSON array of RFC 6902 operations: {0}")]
    Malformed(String),
    /// An operation name is not one of the six.
    #[error("operation {index}: unknown op {op:?}")]
    UnknownOp {
        /// Position in the patch.
        index: usize,
        /// The name given.
        op: String,
    },
    /// A pointer is not valid RFC 6901 syntax.
    #[error("operation {index}: pointer {pointer:?} must be empty or start with /")]
    BadPointer {
        /// Position in the patch.
        index: usize,
        /// The pointer given.
        pointer: String,
    },
    /// A required member (`value`, `from`) is missing, or a value is `null` (TOML has none).
    #[error("operation {index}: {op} needs a non-null {member}")]
    Missing {
        /// Position in the patch.
        index: usize,
        /// The operation.
        op: String,
        /// The missing member.
        member: &'static str,
    },
    /// A pointer does not lead anywhere.
    #[error("operation {index}: nothing at {pointer}: {why}")]
    NoTarget {
        /// Position in the patch.
        index: usize,
        /// The pointer that failed.
        pointer: String,
        /// What was wrong.
        why: String,
    },
    /// A `test` operation compared unequal.
    #[error("operation {index}: test failed at {pointer}")]
    TestFailed {
        /// Position in the patch.
        index: usize,
        /// The pointer tested.
        pointer: String,
    },
}

/// Where a segment lands in its container.
enum Slot {
    Key(String),
    Idx(usize),
    End,
}

/// Split an RFC 6901 pointer into unescaped segments; `None` when it is not a pointer.
#[must_use]
pub fn parse_pointer(pointer: &str) -> Option<Vec<String>> {
    if pointer.is_empty() {
        return Some(Vec::new());
    }
    let rest = pointer.strip_prefix('/')?;
    Some(
        rest.split('/')
            .map(|s| s.replace("~1", "/").replace("~0", "~"))
            .collect(),
    )
}

/// True for an RFC 6901 array index: digits without a leading zero.
fn is_index(seg: &str) -> bool {
    !seg.is_empty()
        && seg.bytes().all(|b| b.is_ascii_digit())
        && (seg == "0" || !seg.starts_with('0'))
}

/// The string value of the first of `fields` present on a table.
fn field_of<'a>(map: &'a IndexMap<String, Node>, fields: &[&str]) -> Option<&'a str> {
    fields.iter().find_map(|f| match map.get(*f) {
        Some(Node::Str(s)) => Some(s.as_str()),
        _ => None,
    })
}

/// Resolve `seg` against `node`; an id segment must name exactly one element.
fn slot(node: &Node, seg: &str) -> Result<Slot, String> {
    match node {
        Node::Map(_) => Ok(Slot::Key(seg.to_owned())),
        Node::Arr(items) => {
            if seg == "-" {
                return Ok(Slot::End);
            }
            if is_index(seg) {
                return seg
                    .parse()
                    .map(Slot::Idx)
                    .map_err(|_| format!("index {seg} is too large"));
            }
            let hits: Vec<usize> = items
                .iter()
                .enumerate()
                .filter(|(_, n)| matches!(n, Node::Map(m) if field_of(m, &ID_FIELDS) == Some(seg)))
                .map(|(i, _)| i)
                .collect();
            match hits.as_slice() {
                [i] => Ok(Slot::Idx(*i)),
                [] => Err(format!("no element has id or name {seg:?}")),
                _ => Err(format!("{} elements have id or name {seg:?}", hits.len())),
            }
        }
        _ => Err(format!("cannot step into a scalar with {seg:?}")),
    }
}

/// The node at `segs`, if it exists.
fn get<'a>(root: &'a Node, segs: &[String]) -> Result<&'a Node, String> {
    let mut cur = root;
    for seg in segs {
        cur = match (slot(cur, seg)?, cur) {
            (Slot::Key(k), Node::Map(m)) => m.get(&k).ok_or(format!("no key {k:?}"))?,
            (Slot::Idx(i), Node::Arr(a)) => a.get(i).ok_or(format!("no element {i}"))?,
            _ => return Err("`-` names no existing element".to_owned()),
        };
    }
    Ok(cur)
}

/// The mutable node at `segs`, if it exists.
fn get_mut<'a>(root: &'a mut Node, segs: &[String]) -> Result<&'a mut Node, String> {
    let mut cur = root;
    for seg in segs {
        let s = slot(cur, seg)?;
        cur = match (s, cur) {
            (Slot::Key(k), Node::Map(m)) => m.get_mut(&k).ok_or(format!("no key {k:?}"))?,
            (Slot::Idx(i), Node::Arr(a)) => a.get_mut(i).ok_or(format!("no element {i}"))?,
            _ => return Err("`-` names no existing element".to_owned()),
        };
    }
    Ok(cur)
}

/// Insert `value` at `segs` with RFC 6902 `add` semantics.
fn add(root: &mut Node, segs: &[String], value: Node) -> Result<(), String> {
    let Some((last, parent_segs)) = segs.split_last() else {
        *root = value;
        return Ok(());
    };
    let parent = get_mut(root, parent_segs)?;
    match (slot(parent, last)?, parent) {
        (Slot::Key(k), Node::Map(m)) => {
            m.insert(k, value);
            Ok(())
        }
        (Slot::End, Node::Arr(a)) => {
            a.push(value);
            Ok(())
        }
        (Slot::Idx(i), Node::Arr(a)) if i <= a.len() => {
            a.insert(i, value);
            Ok(())
        }
        (Slot::Idx(i), Node::Arr(a)) => Err(format!("index {i} is past the end ({})", a.len())),
        _ => Err("the parent is not a table or array".to_owned()),
    }
}

/// Remove and return the node at `segs`.
fn remove(root: &mut Node, segs: &[String]) -> Result<Node, String> {
    let Some((last, parent_segs)) = segs.split_last() else {
        return Err("the document root cannot be removed".to_owned());
    };
    let parent = get_mut(root, parent_segs)?;
    match (slot(parent, last)?, parent) {
        (Slot::Key(k), Node::Map(m)) => m.shift_remove(&k).ok_or(format!("no key {k:?}")),
        (Slot::Idx(i), Node::Arr(a)) if i < a.len() => Ok(a.remove(i)),
        _ => Err("no such element".to_owned()),
    }
}

/// Collect the ids of every object along `segs` (root excluded) and of id segments used.
fn touch(root: &Node, segs: &[String], out: &mut BTreeSet<String>) {
    let mut cur = root;
    for seg in segs {
        let Ok(s) = slot(cur, seg) else { return };
        let next = match (s, cur) {
            (Slot::Key(k), Node::Map(m)) => m.get(&k),
            (Slot::Idx(i), Node::Arr(a)) => a.get(i),
            _ => None,
        };
        if matches!(cur, Node::Arr(_)) && !is_index(seg) && seg != "-" {
            out.insert(seg.clone());
        }
        let Some(next) = next else { return };
        note_ids(next, out);
        cur = next;
    }
}

/// Record the id-like string fields of a table node.
fn note_ids(node: &Node, out: &mut BTreeSet<String>) {
    if let Node::Map(m) = node {
        for f in TOUCH_FIELDS {
            if let Some(Node::Str(s)) = m.get(f) {
                out.insert(s.clone());
            }
        }
    }
}

/// The id of the document itself (its `id`, else `name`), used when no inner object was touched.
#[must_use]
pub fn root_id(root: &Node) -> Option<String> {
    match root {
        Node::Map(m) => field_of(m, &ID_FIELDS).map(str::to_owned),
        _ => None,
    }
}

/// Parse a patch file's text into operations.
///
/// # Errors
///
/// [`PatchError::Malformed`] when the text is not a JSON array of operation objects.
pub fn parse_ops(text: &str) -> Result<Vec<Op>, PatchError> {
    serde_json::from_str(text).map_err(|e| PatchError::Malformed(e.to_string()))
}

/// Apply `ops` to a clone of `doc`; the result and the ids the operations touched.
///
/// # Errors
///
/// The first failing operation as a [`PatchError`]; `doc` is never modified.
pub fn apply(doc: &Node, ops: &[Op]) -> Result<(Node, BTreeSet<String>), PatchError> {
    let mut cur = doc.clone();
    let mut touched = BTreeSet::new();
    for (index, op) in ops.iter().enumerate() {
        step(&mut cur, index, op, &mut touched)?;
        tracing::debug!(index, op = %op.op, path = %op.path, "patch op applied");
    }
    if touched.is_empty()
        && !ops.is_empty()
        && let Some(id) = root_id(&cur)
    {
        touched.insert(id);
    }
    Ok((cur, touched))
}

/// Apply one operation to `cur`.
fn step(
    cur: &mut Node,
    index: usize,
    op: &Op,
    touched: &mut BTreeSet<String>,
) -> Result<(), PatchError> {
    let segs = pointer(index, &op.path)?;
    let no_target = |pointer: &str, why: String| PatchError::NoTarget {
        index,
        pointer: pointer.to_owned(),
        why,
    };
    let missing = |member| PatchError::Missing {
        index,
        op: op.op.clone(),
        member,
    };
    let value = || -> Result<Node, PatchError> {
        let v = op.value.clone().filter(|v| !v.is_null());
        let v = v.ok_or_else(|| missing("value"))?;
        serde_json::from_value(v).map_err(|e| no_target(&op.path, format!("bad value: {e}")))
    };
    let from = || -> Result<(Vec<String>, &str), PatchError> {
        let f = op.from.as_deref().ok_or_else(|| missing("from"))?;
        Ok((pointer(index, f)?, f))
    };
    touch(cur, &segs, touched);
    match op.op.as_str() {
        "add" | "replace" => {
            let v = value()?;
            note_ids(&v, touched);
            if op.op == "replace" {
                get(cur, &segs).map_err(|w| no_target(&op.path, w))?;
                remove_and_add(cur, &segs, v)
            } else {
                add(cur, &segs, v)
            }
            .map_err(|w| no_target(&op.path, w))
        }
        "remove" => remove(cur, &segs)
            .map(drop)
            .map_err(|w| no_target(&op.path, w)),
        "test" => {
            let v = value()?;
            match get(cur, &segs) {
                Ok(n) if *n == v => Ok(()),
                Ok(_) => Err(PatchError::TestFailed {
                    index,
                    pointer: op.path.clone(),
                }),
                Err(w) => Err(no_target(&op.path, w)),
            }
        }
        "move" | "copy" => {
            let (fsegs, fptr) = from()?;
            touch(cur, &fsegs, touched);
            if op.op == "move" && segs.len() > fsegs.len() && segs.starts_with(&fsegs) {
                return Err(no_target(&op.path, "cannot move into its own child".into()));
            }
            let moved = if op.op == "move" {
                remove(cur, &fsegs)
            } else {
                get(cur, &fsegs).cloned()
            }
            .map_err(|w| no_target(fptr, w))?;
            note_ids(&moved, touched);
            add(cur, &segs, moved).map_err(|w| no_target(&op.path, w))
        }
        other => Err(PatchError::UnknownOp {
            index,
            op: other.to_owned(),
        }),
    }
}

/// Parse a pointer or report which operation had a bad one.
fn pointer(index: usize, ptr: &str) -> Result<Vec<String>, PatchError> {
    parse_pointer(ptr).ok_or_else(|| PatchError::BadPointer {
        index,
        pointer: ptr.to_owned(),
    })
}

/// Replace the existing node at `segs` with `value` in place.
fn remove_and_add(root: &mut Node, segs: &[String], value: Node) -> Result<(), String> {
    *get_mut(root, segs)? = value;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn doc() -> Node {
        let text = "name = \"btn\"\n[[props]]\nname = \"size\"\nkind = \"enum\"\n[[props]]\nname = \"tone\"\nkind = \"enum\"\n";
        toml_edit::de::from_str(text).unwrap()
    }

    fn ops(text: &str) -> Vec<Op> {
        parse_ops(text).unwrap()
    }

    // frob:tests crates/crunk/src/patch.rs::apply
    #[test]
    fn patch_addresses_array_elements_by_name() {
        let (out, touched) = apply(
            &doc(),
            &ops(r#"[{"op":"replace","path":"/props/tone/kind","value":"bool"}]"#),
        )
        .unwrap();
        let Node::Map(m) = out else { panic!() };
        let Some(Node::Arr(props)) = m.get("props") else {
            panic!()
        };
        assert!(
            matches!(&props[1], Node::Map(p) if p.get("kind") == Some(&Node::Str("bool".into())))
        );
        assert!(touched.contains("tone"));
        assert!(!touched.contains("size"));
    }

    // frob:tests crates/crunk/src/patch.rs::apply
    #[test]
    fn patch_failure_leaves_the_source_alone() {
        let d = doc();
        let r = apply(
            &d,
            &ops(r#"[{"op":"remove","path":"/props/size"},{"op":"remove","path":"/props/nope"}]"#),
        );
        assert!(matches!(r, Err(PatchError::NoTarget { index: 1, .. })));
        assert_eq!(d, doc());
    }

    // frob:tests crates/crunk/src/patch.rs::parse_pointer
    #[test]
    fn pointer_unescapes_tilde_sequences() {
        assert_eq!(
            parse_pointer("/a~1b/c~0d"),
            Some(vec!["a/b".into(), "c~d".into()])
        );
        assert_eq!(parse_pointer("a"), None);
        assert_eq!(parse_pointer(""), Some(vec![]));
    }

    // frob:tests crates/crunk/src/patch.rs::apply
    #[test]
    fn patch_supports_move_copy_test_and_append() {
        let p = r#"[
            {"op":"test","path":"/name","value":"btn"},
            {"op":"copy","from":"/name","path":"/label"},
            {"op":"move","from":"/label","path":"/title"},
            {"op":"add","path":"/props/-","value":{"name":"x","kind":"bool"}}
        ]"#;
        let (out, _) = apply(&doc(), &ops(p)).unwrap();
        let Node::Map(m) = out else { panic!() };
        assert_eq!(m.get("title"), Some(&Node::Str("btn".into())));
        assert!(!m.contains_key("label"));
        assert!(matches!(m.get("props"), Some(Node::Arr(a)) if a.len() == 3));
    }
}
