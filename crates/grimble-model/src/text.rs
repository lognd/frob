//! Canonical spellings shared by the formatter, the U adapter and the rules (grmb-spec 9.3).

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use std::fmt::Write as _;

use gob_walk::Selector;
use gob_walk::selector::{Expr, Node};

use crate::ast::{
    Atom, ClaimWhat, Clause, ClauseKind, Evidence, Exception, KeyVal, Quantity, Sel, Value,
};

/// A string literal with minimal escapes.
pub fn quote(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\t' => out.push_str("\\t"),
            '\r' => out.push_str("\\r"),
            c if c.is_control() => {
                let _ = write!(out, "\\u{{{:x}}}", u32::from(c));
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// `N unit` with `%` attached; a missing unit prints the bare number.
pub fn quantity_text(q: &Quantity) -> String {
    if q.unit.is_empty() {
        q.number.clone()
    } else if q.unit.starts_with('%') {
        format!("{}{}", q.number, q.unit)
    } else {
        format!("{} {}", q.number, q.unit)
    }
}

/// The canonical spelling of a value.
pub fn value_text(v: &Value) -> String {
    match v {
        Value::Str(s) => quote(s),
        Value::Number(n) | Value::Date(n) | Value::Ident(n) => n.clone(),
        Value::Quantity(q) => quantity_text(q),
        Value::List(items) => {
            let parts: Vec<String> = items.iter().map(value_text).collect();
            format!("[{}]", parts.join(", "))
        }
    }
}

/// The U literal kind of a scalar value.
pub fn value_kind(v: &Value) -> &'static str {
    match v {
        Value::Str(_) => "string",
        Value::Number(_) => "number",
        Value::Quantity(_) => "quantity",
        Value::Date(_) => "date",
        Value::Ident(_) => "ident",
        Value::List(_) => "list",
    }
}

fn flatten(node: &Node, and: bool, out: &mut Vec<Node>) {
    match (&node.expr, and) {
        (Expr::And(ops), true) | (Expr::Or(ops), false) => {
            for o in ops {
                flatten(o, and, out);
            }
        }
        _ => out.push(canon_node(node)),
    }
}

fn node_text(n: &Node) -> String {
    Selector::new(n.clone()).to_string()
}

/// Flattens nested `&` and `|` and sorts operands by printed form (grmb-spec 9.3 item 3).
pub fn canon_node(node: &Node) -> Node {
    let expr = match &node.expr {
        Expr::And(_) | Expr::Or(_) => {
            let and = matches!(node.expr, Expr::And(_));
            let mut ops = Vec::new();
            flatten(node, and, &mut ops);
            ops.sort_by_key(node_text);
            if and { Expr::And(ops) } else { Expr::Or(ops) }
        }
        Expr::Not(inner) => Expr::Not(Box::new(canon_node(inner))),
        Expr::Kind(ks) => {
            let mut ks = ks.clone();
            ks.sort();
            ks.dedup();
            Expr::Kind(ks)
        }
        other => other.clone(),
    };
    Node {
        expr,
        span: node.span,
    }
}

/// The canonical selector text; unparsable text is kept as written.
pub fn selector_text(sel: &Sel) -> String {
    match &sel.parsed {
        Ok(s) => node_text(&canon_node(s.root())),
        Err(_) => sel.text.trim().to_owned(),
    }
}

/// An atom as written.
pub fn atom_text(a: &Atom) -> String {
    a.written()
}

fn key_vals_text(kvs: &[KeyVal]) -> String {
    kvs.iter()
        .map(|kv| format!("{}={}", kv.key.text, value_text(&kv.value.value)))
        .collect::<Vec<_>>()
        .join(" ")
}

/// The canonical level name (aliases replaced, grmb-spec 4.5).
pub fn canonical_level(level: &str) -> &str {
    match level {
        "acceptance" => "customer_test",
        "unit" => "component_unit_test",
        other => other,
    }
}

/// The canonical text of an exception without the trailing `;`.
pub fn exception_text(e: &Exception) -> String {
    let mut out = format!("{} {}", e.kind.keyword(), e.rule.text);
    if let Some(on) = &e.on {
        let _ = write!(out, " on {}", on.written());
    }
    if !e.attrs.is_empty() {
        let _ = write!(out, " {}", key_vals_text(&e.attrs));
    }
    out
}

/// The clause keyword used for anchors and ordering.
pub fn clause_key(k: &ClauseKind) -> &'static str {
    match k {
        ClauseKind::Alias(_) => "alias",
        ClauseKind::RenamedFrom(_) => "renamed_from",
        ClauseKind::Attr { .. } => "attr",
        ClauseKind::Exception(e) => e.kind.keyword(),
        ClauseKind::Kind(_) => "kind",
        ClauseKind::Clearance(_) => "clearance",
        ClauseKind::Owns(_) => "owns",
        ClauseKind::Surface(_) => "surface",
        ClauseKind::May(_) => "may",
        ClauseKind::Excuses(_) => "excuses",
        ClauseKind::Label(_) => "label",
        ClauseKind::Quantity(k, _) => k.keyword(),
        ClauseKind::Fanout(_) => "fanout",
        ClauseKind::Growth(_) => "growth",
        ClauseKind::Transport(_) => "transport",
        ClauseKind::Condition(_) => "condition",
        ClauseKind::Producer(_) => "producer",
        ClauseKind::Consumer(_) => "consumer",
        ClauseKind::Contract(_) => "contract",
        ClauseKind::Shape(_) => "shape",
        ClauseKind::Versioning(_) => "versioning",
        ClauseKind::What(ClaimWhat::Noflow(..)) => "noflow",
        ClauseKind::What(ClaimWhat::Reach(..)) => "reach",
        ClauseKind::What(ClaimWhat::Bound { .. }) => "bound",
        ClauseKind::Proof(_) => "proof",
        ClauseKind::Assumed(_) => "assumed",
        ClauseKind::Evidence(_) => "evidence",
        ClauseKind::Level(_) => "level",
        ClauseKind::Ref(_) => "ref",
        ClauseKind::Runnable(_) => "runnable",
        ClauseKind::Link(l) => l.kind.keyword(),
        ClauseKind::Version(_) => "version",
        ClauseKind::Digest(_) => "digest",
        ClauseKind::Hole(_) => "hole",
    }
}

/// The canonical order rank of a clause (grmb-spec 9.3 item 3, extended to every clause).
pub fn clause_rank(k: &ClauseKind) -> u8 {
    match k {
        ClauseKind::Kind(_) => 0,
        ClauseKind::Clearance(_) => 1,
        ClauseKind::Owns(_) => 2,
        ClauseKind::May(_) => 3,
        ClauseKind::Excuses(_) => 4,
        ClauseKind::Surface(_) => 5,
        ClauseKind::Producer(_) => 6,
        ClauseKind::Consumer(_) => 7,
        ClauseKind::Contract(_) => 8,
        ClauseKind::Label(_) => 9,
        ClauseKind::Quantity(..) => 10,
        ClauseKind::Fanout(_) => 11,
        ClauseKind::Growth(_) => 12,
        ClauseKind::Transport(_) => 13,
        ClauseKind::Condition(_) => 14,
        ClauseKind::Shape(_) => 15,
        ClauseKind::Versioning(_) => 16,
        ClauseKind::What(_) => 17,
        ClauseKind::Proof(_) => 18,
        ClauseKind::Assumed(_) => 19,
        ClauseKind::Evidence(_) => 20,
        ClauseKind::Level(_) => 21,
        ClauseKind::Ref(_) => 22,
        ClauseKind::Runnable(_) => 23,
        ClauseKind::Version(_) => 24,
        ClauseKind::Digest(_) => 25,
        ClauseKind::Link(_) => 26,
        ClauseKind::Attr { .. } => 27,
        ClauseKind::Exception(_) => 28,
        ClauseKind::Alias(_) => 29,
        ClauseKind::RenamedFrom(_) => 30,
        ClauseKind::Hole(_) => 31,
    }
}

/// The canonical one-line text of a clause body (no `;`, no wrapping).
pub fn clause_text(k: &ClauseKind) -> String {
    match k {
        ClauseKind::Alias(i) => format!("alias {}", i.text),
        ClauseKind::RenamedFrom(i) => format!("renamed_from {}", i.text),
        ClauseKind::Attr { key, value } => match value {
            Some(v) => format!("attr {} = {}", key.text, value_text(&v.value)),
            None => format!("attr {}", key.text),
        },
        ClauseKind::Exception(e) => exception_text(e),
        ClauseKind::Kind(i) => format!("kind {}", i.text),
        ClauseKind::Clearance(i) => format!("clearance {}", i.text),
        ClauseKind::Owns(s) => format!("owns {}", selector_text(s)),
        ClauseKind::Surface(s) => format!("surface {}", selector_text(s)),
        ClauseKind::May(m) => {
            let mut out = format!("may {}", m.atom.written());
            if !m.args.is_empty() {
                let args: Vec<String> = m.args.iter().map(|a| quote(&a.value)).collect();
                let _ = write!(out, "({})", args.join(", "));
            }
            if let Some(at) = &m.at {
                let _ = write!(out, " at {}", selector_text(at));
            }
            out
        }
        ClauseKind::Excuses(e) => {
            format!("excuses {} {}", e.atom.written(), key_vals_text(&e.attrs))
                .trim_end()
                .to_owned()
        }
        ClauseKind::Label(i) => format!("label {}", i.text),
        ClauseKind::Quantity(key, q) => format!("{} {}", key.keyword(), quantity_text(q)),
        ClauseKind::Fanout(n) => format!("fanout {}", n.value),
        ClauseKind::Growth(q) => format!("growth {}", quantity_text(q)),
        ClauseKind::Transport(atoms) => {
            let parts: Vec<String> = atoms.iter().map(atom_text).collect();
            format!("transport {}", parts.join(", "))
        }
        ClauseKind::Condition(i) => format!("condition {}", i.text),
        ClauseKind::Producer(s) => format!("producer {}", selector_text(s)),
        ClauseKind::Consumer(s) => format!("consumer {}", selector_text(s)),
        ClauseKind::Contract(r) => format!("contract {}", r.written()),
        ClauseKind::Shape(s) => format!("shape {}", selector_text(s)),
        ClauseKind::Versioning(v) => format!("versioning {}", key_vals_text(&v.attrs)),
        ClauseKind::What(ClaimWhat::Noflow(a, b)) => {
            format!("noflow {} -> {}", a.written(), b.written())
        }
        ClauseKind::What(ClaimWhat::Reach(a, b)) => {
            format!("reach {} -> {}", a.written(), b.written())
        }
        ClauseKind::What(ClaimWhat::Bound {
            metric,
            target,
            limit,
        }) => format!(
            "bound {} {} <= {}",
            metric.text,
            target.written(),
            quantity_text(limit)
        ),
        ClauseKind::Proof(i) => format!("proof {}", i.text),
        ClauseKind::Assumed(kvs) => format!("assumed {}", key_vals_text(kvs)),
        ClauseKind::Evidence(Evidence::Tests(s)) => format!("evidence tests {}", selector_text(s)),
        ClauseKind::Evidence(Evidence::Ref(s)) => format!("evidence ref {}", quote(&s.value)),
        ClauseKind::Level(i) => format!("level {}", canonical_level(&i.text)),
        ClauseKind::Ref(s) => format!("ref {}", quote(&s.value)),
        ClauseKind::Runnable(s) => format!("runnable {}", selector_text(s)),
        ClauseKind::Link(l) => match &l.because {
            Some(b) => format!(
                "{} {} because={}",
                l.kind.keyword(),
                l.target.written(),
                quote(&b.value)
            ),
            None => format!("{} {}", l.kind.keyword(), l.target.written()),
        },
        ClauseKind::Version(s) => format!("version {}", quote(&s.value)),
        ClauseKind::Digest(s) => format!("digest {}", quote(&s.value)),
        ClauseKind::Hole(m) => format!("/* hole: {m} */"),
    }
}

/// Sorting key of a clause: rank, link kind / attr key, then canonical text.
pub fn clause_sort_key(c: &Clause) -> (u8, String) {
    (clause_rank(&c.kind), clause_text(&c.kind))
}
