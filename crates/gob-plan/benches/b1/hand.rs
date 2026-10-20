//! Handwritten Rust forms of TODO001, COV001 and DOC002, the baseline the plans race.

use std::collections::{BTreeMap, BTreeSet, VecDeque};

use gob_ir::eval::Ctx;
use gob_ir::{AttrValue, Location, Model, NodeId, Operator, Universal};
use gob_text::SourceText;
use regex::Regex;

use super::{Found, Prepared};

/// Call levels a test may go through in COV001 (the rule's `depth` knob).
const COV_DEPTH: usize = 12;

fn comment_text(model: &Model, id: NodeId) -> Option<&str> {
    match model.term().node(id).op() {
        Operator::Universal(Universal::Comment { text }) => Some(text),
        _ => None,
    }
}

/// The first and last-character line of `id`, when it has a text span and the file is known.
fn lines_of(model: &Model, source: &SourceText, id: NodeId) -> Option<(u32, u32)> {
    let Location::Text { range, .. } = model.term().node(id).location() else {
        return None;
    };
    let last = if range.is_empty() {
        range.start()
    } else {
        gob_text::TextSize::new(u32::from(range.end()) - 1)
    };
    Some((
        source.line_col(range.start())?.line,
        source.line_col(last)?.line,
    ))
}

/// The name of the first `frob:<name>` directive in a comment.
fn directive_name(text: &str) -> Option<&str> {
    let rest = &text[text.find("frob:")? + "frob:".len()..];
    let end = rest
        .find(|c: char| !(c.is_ascii_alphanumeric() || c == '_' || c == '-'))
        .unwrap_or(rest.len());
    (end > 0).then(|| &rest[..end])
}

/// TODO001 by hand: a marker comment with no owner id and no `frob:todo` on its line or the
/// line above.
pub fn todo001(p: &Prepared) -> Vec<Found> {
    let marker = Regex::new(r"\b(TODO|FIXME|XXX|HACK)\b").expect("static pattern");
    let owned = Regex::new(r"\b[A-Z]+\([0-9A-Z]{26}\)").expect("static pattern");
    let mut directives: Vec<(u32, u32)> = Vec::new();
    let mut candidates: Vec<(NodeId, u32, u32)> = Vec::new();
    for id in p.model.term().ids() {
        let Some(text) = comment_text(&p.model, id) else {
            continue;
        };
        let Some((start, end)) = lines_of(&p.model, &p.source, id) else {
            continue;
        };
        if directive_name(text) == Some("todo") {
            directives.push((start, end));
        }
        if marker.is_match(text) && !owned.is_match(text) {
            candidates.push((id, start, end));
        }
    }
    let near = |end: u32, start: u32| end == start || end + 1 == start;
    let mut out: Vec<Found> = candidates
        .into_iter()
        .filter(|&(_, cs, ce)| {
            !directives
                .iter()
                .any(|&(ds, de)| near(de, cs) || near(ce, ds))
        })
        .map(|(id, ..)| (false, id))
        .collect();
    out.sort();
    out
}

fn attr_true(model: &Model, id: NodeId, key: &str) -> bool {
    matches!(
        model.term().node(id).attrs().get(key),
        Some(AttrValue::Bool(true))
    )
}

fn is_canonical_unit(model: &Model, id: NodeId, kind: Option<&str>) -> bool {
    let n = model.term().node(id);
    matches!(n.op(), Operator::Universal(Universal::Unit { kind: k, .. })
        if kind.is_none_or(|want| k == want))
        && n.attrs().get_str(gob_ir::reserved::FACET) != Some("sig")
}

fn inside_test(model: &Model, id: NodeId) -> bool {
    let mut cur = model.term().node(id).parent();
    while let Some(a) = cur {
        if attr_true(model, a, "test") {
            return true;
        }
        cur = model.term().node(a).parent();
    }
    false
}

/// COV001 by hand: a public non-test function no test reaches through calls within the depth.
pub fn cov001(p: &Prepared) -> Vec<Found> {
    let calls = Ctx::new(&p.model).rel_calls();
    let term = p.model.term();
    let tests: Vec<NodeId> = term
        .ids()
        .filter(|&id| is_canonical_unit(&p.model, id, None) && attr_true(&p.model, id, "test"))
        .collect();
    // Every node a test reaches within the depth, and whether a walk met an unknown frontier.
    let mut reached: BTreeSet<NodeId> = BTreeSet::new();
    let mut doubt = false;
    for &t in &tests {
        let mut seen: BTreeMap<NodeId, usize> = BTreeMap::from([(t, 0)]);
        let mut queue = VecDeque::from([t]);
        while let Some(n) = queue.pop_front() {
            let d = seen[&n];
            doubt |= calls.is_unknown_out(n);
            if d == COV_DEPTH {
                continue;
            }
            for (m, _) in calls.image(n) {
                if let std::collections::btree_map::Entry::Vacant(e) = seen.entry(m) {
                    e.insert(d + 1);
                    queue.push_back(m);
                }
            }
        }
        reached.extend(seen.into_keys().filter(|&n| n != t));
    }
    let mut out: Vec<Found> = Vec::new();
    for id in term.ids() {
        if !is_canonical_unit(&p.model, id, Some("function"))
            || term.node(id).attrs().get_str("visibility") != Some("public")
            || inside_test(&p.model, id)
            || attr_true(&p.model, id, "test")
            || reached.contains(&id)
        {
            continue;
        }
        out.push((doubt, id));
    }
    out.sort();
    out
}

fn is_relative(s: &str) -> bool {
    let scheme = s.split_once(':').is_some_and(|(head, _)| {
        !head.is_empty()
            && head.starts_with(|c: char| c.is_ascii_alphabetic())
            && head
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || matches!(c, '+' | '-' | '.'))
    });
    !scheme && !s.starts_with('/') && !s.starts_with("//")
}

fn resolve(path: &str, from: &str) -> Option<String> {
    let mut parts: Vec<&str> = Vec::new();
    let base = if path.starts_with('/') {
        ""
    } else {
        from.rsplit_once('/').map_or("", |(dir, _)| dir)
    };
    for seg in base.split('/').chain(path.split('/')) {
        match seg {
            "" | "." => {}
            ".." => {
                parts.pop()?;
            }
            s => parts.push(s),
        }
    }
    Some(parts.join("/"))
}

/// The destination of a Markdown `link` node: the spelled name of its head `ref`.
fn link_dest(model: &Model, id: NodeId) -> Option<String> {
    let term = model.term();
    let n = term.node(id);
    if !matches!(n.op(), Operator::Universal(Universal::Apply { kind }) if kind == "link") {
        return None;
    }
    match term.node(*n.children().first()?).op() {
        Operator::Universal(Universal::Ref { name }) => Some(name.clone()),
        _ => None,
    }
}

/// The text of a heading section: the first literal in its `sig` facet child.
fn heading_text(model: &Model, id: NodeId) -> Option<String> {
    let term = model.term();
    term.node(id).children().iter().find_map(|&c| {
        let sig = term.node(c);
        if sig.attrs().get_str(gob_ir::reserved::FACET) != Some("sig") {
            return None;
        }
        sig.children()
            .iter()
            .find_map(|&l| match term.node(l).op() {
                Operator::Universal(Universal::Lit { lexeme, .. }) => Some(lexeme.clone()),
                _ => None,
            })
    })
}

/// DOC002 by hand: a relative link to a file or a heading that does not exist.
pub fn doc002(p: &Prepared) -> Vec<Found> {
    let term = p.model.term();
    let slugs: BTreeSet<String> = term
        .ids()
        .filter(|&id| is_canonical_unit(&p.model, id, Some("section")))
        .filter_map(|id| heading_text(&p.model, id))
        .map(|t| gob_symbols::slugify(&t))
        .collect();
    let mut out: Vec<Found> = Vec::new();
    for id in term.ids() {
        let Some(dest) = link_dest(&p.model, id) else {
            continue;
        };
        if !is_relative(&dest) {
            continue;
        }
        let (path, anchor) = dest
            .split_once('#')
            .map_or((&*dest, None), |(a, b)| (a, Some(b)));
        let exists = resolve(path, &p.path).as_deref() == Some(p.path.as_str());
        let missing_heading = anchor.is_some_and(|a| !slugs.contains(a));
        if !exists || missing_heading {
            out.push((false, id));
        }
    }
    out.sort();
    out
}
