//! Deterministic text dumps of a folded file for the conformance corpus and `grimble graph`.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

use std::fmt::Write as _;

use gob_ir::{AttrValue, NodeId, Operator, Resolution, ScopeGraph, Term, Universal};

use crate::fold::FoldedFile;

fn op_text(op: &Operator) -> String {
    match op {
        Operator::Universal(u) => match u {
            Universal::Unit { kind, role } => format!("unit kind={kind} role={role}"),
            Universal::Anon { kind } => format!("anon kind={kind}"),
            Universal::Ref { name } => format!("ref {name:?}"),
            Universal::Apply { kind } => format!("apply kind={kind}"),
            Universal::Bind { kind, mode } => format!("bind kind={kind} mode={mode}"),
            Universal::Group { order } => format!("group {}", order.as_str()),
            Universal::Lit { kind, lexeme } => format!("lit kind={kind} {lexeme:?}"),
            Universal::Attr { name } => format!("attr name={name}"),
            Universal::Comment { text } => format!("comment {text:?}"),
            Universal::Region { kind } => format!("region kind={kind}"),
            Universal::Phase { kind } => format!("phase kind={kind}"),
            Universal::Hole { kind } => format!("hole kind={kind}"),
            Universal::Opaque { reason, payload } => {
                format!("opaque reason={reason} bytes={}", payload.len())
            }
        },
        Operator::Adapter(a) => format!("{}.{}", a.lang, a.name),
    }
}

fn node(term: &Term, id: NodeId, depth: usize, out: &mut String) {
    let n = term.node(id);
    let pad = "  ".repeat(depth);
    let _ = write!(out, "{pad}{}:{}", n.op().sort().name(), op_text(n.op()));
    if let Some(name) = n.name() {
        let _ = write!(out, " name={name}");
    }
    if !n.binders().is_empty() {
        let _ = write!(out, " binders={:?}", n.binders());
    }
    if let Some(span) = n.location().span() {
        let _ = write!(
            out,
            " @{}..{}",
            u32::from(span.range.start()),
            u32::from(span.range.end())
        );
    }
    if let Some(AttrValue::Str(a)) = n.attrs().get("grmb.anchor") {
        let _ = write!(out, " anchor={a}");
    }
    if n.attrs().get_str(gob_ir::reserved::FACET) == Some("sig") {
        out.push_str(" facet=sig");
    }
    if let Some(sym) = term.symref_of(id) {
        let _ = write!(out, " symref={sym}");
    }
    out.push('\n');
    for &c in n.children() {
        node(term, c, depth + 1, out);
    }
}

/// The term as an indented tree: sort, operator, name, byte range, anchor, symref.
pub fn dump_term(term: &Term) -> String {
    let mut out = String::new();
    let _ = writeln!(
        out,
        "lang_param={:?}",
        term.node(term.root()).lang_param().unwrap_or("")
    );
    node(term, term.root(), 0, &mut out);
    out
}

/// Every reference of the term with its resolution status in the scope graph.
pub fn dump_refs(term: &Term, scopes: &ScopeGraph) -> String {
    let mut out = String::new();
    for r in scopes.refs() {
        let Some(id) = r.node else { continue };
        let res = scopes.resolve_name(r.scope, &r.name);
        let text = match res {
            Resolution::Must(d) => format!("Must {}", scopes.decl(d).name),
            Resolution::May(ds) => format!(
                "May {}",
                ds.iter()
                    .map(|d| scopes.decl(*d).name.clone())
                    .collect::<Vec<_>>()
                    .join("|")
            ),
            Resolution::Unknown => "Unknown".to_owned(),
        };
        let span = term.node(id).location().span();
        let _ = writeln!(
            out,
            "ref {:?} @{} -> {text}",
            r.name,
            span.map_or(0, |s| u32::from(s.range.start()))
        );
    }
    out
}

/// The full dump of a folded file: term, references and bound directives.
pub fn dump(f: &FoldedFile) -> String {
    let mut out = dump_term(&f.term);
    out.push_str("--- refs\n");
    out.push_str(&dump_refs(&f.term, &f.scopes));
    out.push_str("--- directives\n");
    for d in &f.directives {
        let _ = writeln!(
            out,
            "{} {:?} -> {}{}",
            d.hit.qualified(),
            d.hit.args,
            d.anchor,
            d.hit
                .problem
                .as_ref()
                .map_or(String::new(), |(r, _)| format!(" [{r}]"))
        );
    }
    out
}

/// The U signature of a folded file: location-free alpha print plus every unit's five facet
/// digests. Two files with equal signatures are the same term (the round-trip contract).
pub fn u_signature(f: &FoldedFile) -> String {
    let mut out = f.term.print_alpha(f.term.root());
    for u in f.term.units() {
        let _ = write!(out, "\n{}", u.symref);
        for (facet, d) in f.term.facet_digests(u.node) {
            let _ = write!(out, " {}={d:?}", facet.name());
        }
    }
    out
}
