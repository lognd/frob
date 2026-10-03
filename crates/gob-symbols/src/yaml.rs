//! The YAML adapter (fidelity F1): block-mapping keys as nested units.
//!
//! # Mapping (rho)
//!
//! - The document is `unit(file, impl)`; every block-mapping key made of
//!   alphanumerics, `_` and `-` is a `unit(key, impl)` named by the key, nested
//!   under the key whose block it sits in. The symref is `path::outer.inner`.
//! - A unit spans from its key to the last content line of its block (trailing
//!   blank and comment lines excluded). Its Sig facet is the key name; its Body
//!   facet is the exact text of that span, so any edit inside the block changes it.
//! - Keys of sequence items, flow collections, block scalars and exotic keys
//!   (quoted, with spaces or dots) are not units. No tree-sitter grammar is
//!   involved: the scan is line based, which is all comment binding needs.

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K

use std::sync::Arc;

use gob_ir::{GroupOrder, NodeId, NodeSpec, Operator, ScopeGraph, TermError, reserved};
use gob_languages::{Language, ParseLimits, UnresolvedReason, grammar_identity};

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, ParseStatus,
};
use crate::fold::{Cx, base_file, file_root_spec};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::view::{self, Naming};

/// The YAML adapter.
#[derive(Debug, Clone, Copy, Default)]
pub struct YamlAdapter;

impl Adapter for YamlAdapter {
    fn language(&self) -> &'static str {
        "yaml"
    }

    fn identity(&self) -> String {
        format!(
            "gob-symbols/v{EXTRACTOR_VERSION}/{}",
            grammar_identity(Language::Yaml)
        )
    }

    fn fidelity(&self) -> Fidelity {
        Fidelity::F1
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::default()
    }

    fn parse(&self, text: &str, _limits: &ParseLimits) -> ConcreteTree {
        ConcreteTree::Source(Arc::from(text))
    }

    fn fold(&self, tree: &ConcreteTree, input: &FileInput<'_>) -> Result<Folded, FoldError> {
        match tree {
            ConcreteTree::Source(text) => fold_text(text, input),
            _ => crate::fold::failed_file(input, "yaml", UnresolvedReason::GrammarUnavailable),
        }
    }
}

/// One block-mapping key found by the line scan.
#[derive(Debug)]
struct Key {
    name: String,
    indent: usize,
    start: usize,
    end: usize,
    unit: bool,
    kids: Vec<usize>,
}

/// The key name of a content line (indent stripped), when it starts a block-mapping entry.
///
/// Returns the raw key text and whether it is simple enough to be a unit name.
fn key_of(line: &str) -> Option<(&str, bool)> {
    let first = line.chars().next()?;
    if matches!(
        first,
        '#' | '-' | '{' | '[' | '&' | '*' | '!' | '|' | '>' | '%' | '@' | '`'
    ) {
        return None;
    }
    let colon = if matches!(first, '"' | '\'') {
        let close = line[1..].find(first)? + 1;
        if !line[close + 1..].starts_with(':') {
            return None;
        }
        close + 1
    } else {
        let mut at = None;
        for (i, _) in line.match_indices(':') {
            let after = &line[i + 1..];
            if after.is_empty() || after.starts_with([' ', '\t']) {
                at = Some(i);
                break;
            }
        }
        at?
    };
    let raw = line[..colon].trim_end();
    if raw.is_empty() || raw.contains(" #") {
        return None;
    }
    let simple = raw
        .chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-');
    Some((raw, simple))
}

/// True when the value after a key's colon opens a block scalar (`|`, `>` and variants).
fn opens_block_scalar(line: &str, colon_after: usize) -> bool {
    let v = line[colon_after..].trim_start();
    v.starts_with(['|', '>'])
}

/// Scan `text` into the flat list of keys (document order) with block extents.
fn scan_keys(text: &str) -> Vec<Key> {
    let mut keys: Vec<Key> = Vec::new();
    let mut open: Vec<usize> = Vec::new();
    let mut seq: Option<usize> = None;
    let mut scalar: Option<usize> = None;
    let mut offset = 0;
    for raw in text.split_inclusive('\n') {
        let line_start = offset;
        offset += raw.len();
        let body = raw.trim_end_matches(['\n', '\r']);
        let content = body.trim_start();
        let indent = body.len() - content.len();
        if content.is_empty() {
            continue;
        }
        if let Some(s) = scalar {
            if indent > s {
                extend(&mut keys, &open, line_start + body.len());
                continue;
            }
            scalar = None;
        }
        if content.starts_with('#') {
            continue;
        }
        if let Some(d) = seq {
            if indent > d {
                extend(&mut keys, &open, line_start + body.len());
                continue;
            }
            seq = None;
        }
        if content.starts_with('-') && (content.len() == 1 || content[1..].starts_with([' ', '\t']))
        {
            seq = Some(indent);
            while open.last().is_some_and(|&k| keys[k].indent > indent) {
                open.pop();
            }
            extend(&mut keys, &open, line_start + body.len());
            continue;
        }
        let Some((name, simple)) = key_of(content) else {
            extend(&mut keys, &open, line_start + body.len());
            continue;
        };
        while open.last().is_some_and(|&k| keys[k].indent >= indent) {
            open.pop();
        }
        extend(&mut keys, &open, line_start + body.len());
        let idx = keys.len();
        if let Some(&p) = open.last() {
            keys[p].kids.push(idx);
        }
        let after = content.find(name).map_or(0, |i| i + name.len());
        let colon_after = content[after..]
            .find(':')
            .map_or(content.len(), |c| after + c + 1);
        if opens_block_scalar(content, colon_after) {
            scalar = Some(indent);
        }
        keys.push(Key {
            name: name.to_owned(),
            indent,
            start: line_start + indent,
            end: line_start + body.len(),
            unit: simple,
            kids: Vec::new(),
        });
        open.push(idx);
    }
    keys
}

/// Extend every open key to `end` (a content line belongs to all enclosing blocks).
fn extend(keys: &mut [Key], open: &[usize], end: usize) {
    for &k in open {
        keys[k].end = end;
    }
}

/// Fold `key` and its nested keys; non-unit keys pass their units up to the caller.
fn fold_key(
    cx: &mut Cx<'_>,
    keys: &[Key],
    i: usize,
    out: &mut Vec<NodeId>,
) -> Result<(), TermError> {
    let k = &keys[i];
    let mut nested = Vec::new();
    for &c in &k.kids {
        fold_key(cx, keys, c, &mut nested)?;
    }
    if !k.unit {
        out.extend(nested);
        return Ok(());
    }
    let loc = cx.loc(k.start, k.end);
    let name = cx.add(
        NodeSpec::new(Operator::lit("key", &k.name), loc.clone()),
        &[],
    )?;
    let sig = cx.add(
        NodeSpec::new(Operator::group(GroupOrder::Sequence), loc.clone())
            .attr(reserved::FACET, "sig"),
        &[name],
    )?;
    let body = cx.add(
        NodeSpec::new(Operator::lit("text", &cx.text[k.start..k.end]), loc.clone()),
        &[],
    )?;
    let mut children = vec![sig, body];
    children.extend(nested);
    out.push(cx.add(
        NodeSpec::new(Operator::unit("key", "impl"), loc).named(&k.name),
        &children,
    )?);
    Ok(())
}

fn fold_text(text: &str, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    let mut cx = Cx::new(input.path, "yaml", text);
    let keys = scan_keys(text);
    let mut units = Vec::new();
    let nested: std::collections::HashSet<usize> =
        keys.iter().flat_map(|k| k.kids.iter().copied()).collect();
    for i in (0..keys.len()).filter(|i| !nested.contains(i)) {
        fold_key(&mut cx, &keys, i, &mut units)?;
    }
    let root = cx.add(file_root_spec(&cx, input.size as usize), &units)?;
    let term = cx.b.finish(root)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Model);
    let mut file = base_file(input, "yaml");
    file.fidelity = Fidelity::F1;
    file.parse_status = ParseStatus::Complete;
    file.symbols = v.symbols;
    file.extras = v.extras;
    tracing::debug!(
        path = input.path,
        keys = file.symbols.len(),
        "yaml file folded"
    );
    Ok(Folded { term, scopes, file })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn names(text: &str) -> Vec<(String, usize, usize)> {
        scan_keys(text)
            .into_iter()
            .map(|k| (k.name, k.start, k.end))
            .collect()
    }

    #[test]
    fn nested_keys_and_extents() {
        let t = "on:\n  push:\n    branches: [a]\n# c\n\nname: x\n";
        let k = names(t);
        assert_eq!(k.len(), 4);
        assert_eq!(&t[k[0].1..k[0].2], "on:\n  push:\n    branches: [a]");
        assert_eq!(&t[k[3].1..k[3].2], "name: x");
    }

    #[test]
    fn sequence_items_and_block_scalars_hide_keys() {
        let t = "steps:\n  - name: a\n    run: |\n      x: y\n  - uses: b\nnext: 1\n";
        let k: Vec<String> = scan_keys(t).into_iter().map(|k| k.name).collect();
        assert_eq!(k, ["steps", "next"]);
    }
}
