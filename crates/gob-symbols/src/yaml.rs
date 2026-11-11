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
//!   (quoted, with spaces or dots) are not units in the line scan.
//!
//! # Tree-sitter path (F2)
//!
//! When the `yaml` grammar is compiled in and the text parses without errors, the
//! file is folded from the syntax tree instead of the line scan:
//!
//! - every block-sequence item is a `unit(key, impl)` named by its zero-based index
//!   (`jobs.build.steps.0`), spanning from its `-`; the keys inside it nest under it,
//!   so a directive above a `- uses:` step binds to that step alone.
//! - an anchor (`&name`) on a mapping value or sequence item names that key or item
//!   unit; an alias (`*name`) is a `Depends` reference from the unit holding it to the
//!   unit carrying the nearest preceding anchor of that name.
//! - on a parse error or a missing grammar the line scan above is used unchanged.

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K

use std::sync::Arc;

use gob_ir::{GroupOrder, NodeId, NodeSpec, Operator, ScopeGraph, TermError, reserved};
use gob_languages::{
    Language, ParseLimits, ParseResult, ParsedTree, UnresolvedReason, grammar_identity, parse,
};

use crate::adapter::{
    Adapter, CapabilityDecl, ConcreteTree, Fidelity, FileInput, FoldError, Folded, Lang,
    ParseStatus,
};
use crate::fold::{Cx, base_file, file_root_spec};
use crate::model::{FileSymbols, RefKind, RefSite};
use crate::pipeline::EXTRACTOR_VERSION;
use crate::symref::Symref;
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
        gob_caps::lang_fidelity(Lang::Yaml)
    }

    fn capabilities(&self) -> CapabilityDecl {
        CapabilityDecl::for_lang(Lang::Yaml)
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

// frob:ticket 01M4MDH6NJXB6YK5NZFKC4NSBJ
/// Folds `text` as YAML: from the syntax tree when it parses cleanly, else by line scan.
pub(crate) fn fold_text(text: &str, input: &FileInput<'_>) -> Result<Folded, FoldError> {
    fold_with(text, input, false).map(|(folded, _)| folded)
}

// frob:ticket 01M5CH6Z005WE93MXMAP17WEBJ
/// Folds a GitHub Actions workflow: YAML units plus `uses`, `run` and `${{ }}` region nodes.
///
/// The flag is true when the syntax tree was used, so `uses:` references came from term nodes.
pub(crate) fn fold_workflow(
    text: &str,
    input: &FileInput<'_>,
) -> Result<(Folded, bool), FoldError> {
    fold_with(text, input, true)
}

/// Shared fold entry; `workflow` turns on the Actions region nodes of the tree path.
fn fold_with(
    text: &str,
    input: &FileInput<'_>,
    workflow: bool,
) -> Result<(Folded, bool), FoldError> {
    match parse(Language::Yaml, text, &ParseLimits::default()) {
        ParseResult::Parsed(t) if !t.has_errors() => {
            fold_tree(&t, input, workflow).map(|f| (f, workflow))
        }
        ParseResult::Parsed(_) => {
            tracing::debug!(path = input.path, "yaml syntax errors; using the line scan");
            fold_lines(text, input).map(|f| (f, false))
        }
        ParseResult::Unresolved(u) => {
            tracing::debug!(path = input.path, reason = %u.reason, "yaml tree unavailable; using the line scan");
            fold_lines(text, input).map(|f| (f, false))
        }
    }
}

/// An anchor definition: its name, byte offset and the unit it names.
struct AnchorDef {
    name: String,
    at: usize,
    unit: NodeId,
}

/// An alias use: the unit holding it (`None` for the file), its name and offset.
struct AliasUse {
    holder: Option<NodeId>,
    name: String,
    at: usize,
}

/// State of one tree fold.
struct TreeFold<'a, 'c> {
    cx: &'a mut Cx<'c>,
    anchors: Vec<AnchorDef>,
    aliases: Vec<AliasUse>,
    /// Indexes into `aliases` not yet attributed to a unit.
    loose: Vec<usize>,
    /// True when workflow region nodes (`uses`, `run`, `${{ }}`) are built.
    workflow: bool,
    /// External `uses:` references as (byte offset, reference text).
    uses: Vec<(usize, String)>,
}

/// The scalar leaf node under `n` (a flow or block node wrapper), if any.
fn scalar_leaf(n: tree_sitter::Node<'_>) -> Option<tree_sitter::Node<'_>> {
    if is_scalar(n.kind()) {
        return Some(n);
    }
    let mut cur = n.walk();
    n.named_children(&mut cur).find_map(scalar_leaf)
}

/// True for the node kinds that hold scalar text.
fn is_scalar(kind: &str) -> bool {
    matches!(
        kind,
        "plain_scalar" | "double_quote_scalar" | "single_quote_scalar" | "block_scalar"
    )
}

/// The text a scalar node denotes: quotes and block-scalar header removed.
fn scalar_body(kind: &str, raw: &str) -> String {
    match kind {
        "double_quote_scalar" | "single_quote_scalar" => raw
            .get(1..raw.len().saturating_sub(1))
            .unwrap_or(raw)
            .to_owned(),
        "block_scalar" => raw.split_once('\n').map_or("", |(_, rest)| rest).to_owned(),
        _ => raw.to_owned(),
    }
}

/// Byte ranges (start, end) and inner text of each `${{ ... }}` in `raw`.
fn expressions(raw: &str) -> Vec<(usize, usize, &str)> {
    let mut out = Vec::new();
    let mut from = 0;
    while let Some(open) = raw[from..].find("${{") {
        let start = from + open;
        let Some(close) = raw[start..].find("}}") else {
            break;
        };
        let end = start + close + 2;
        out.push((start, end, raw[start + 3..end - 2].trim()));
        from = end;
    }
    out
}

/// The text of `n` in `text`.
fn slice<'t>(text: &'t str, n: tree_sitter::Node<'_>) -> &'t str {
    &text[n.start_byte()..n.end_byte()]
}

/// The anchor name on the direct children of `value` (`&name`), if any.
fn anchor_of(text: &str, value: tree_sitter::Node<'_>) -> Option<String> {
    let mut cur = value.walk();
    let found = value.children(&mut cur).find(|c| c.kind() == "anchor");
    found.map(|a| slice(text, a).trim_start_matches('&').to_owned())
}

/// The key text of a pair and whether it is a simple unit name.
fn pair_key<'t>(text: &'t str, pair: tree_sitter::Node<'_>) -> Option<(&'t str, bool)> {
    let raw = slice(text, pair.child_by_field_name("key")?).trim();
    let simple = !raw.is_empty()
        && raw
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-');
    Some((raw, simple))
}

impl TreeFold<'_, '_> {
    /// Collect the units under `node` into `out`; aliases seen join `loose`.
    fn walk(
        &mut self,
        text: &str,
        node: tree_sitter::Node<'_>,
        out: &mut Vec<NodeId>,
    ) -> Result<(), TermError> {
        match node.kind() {
            "block_mapping_pair" => {
                let named = pair_key(text, node).filter(|(_, simple)| *simple);
                let value = node.child_by_field_name("value");
                self.walk_unit(text, node, named.map(|(k, _)| k.to_owned()), value, out)
            }
            "block_sequence_item" => {
                let mut index = 0;
                let mut prev = node.prev_named_sibling();
                while let Some(p) = prev {
                    if p.kind() == "block_sequence_item" {
                        index += 1;
                    }
                    prev = p.prev_named_sibling();
                }
                let value = node.named_child(0);
                self.walk_unit(text, node, Some(index.to_string()), value, out)
            }
            "alias" => {
                self.aliases.push(AliasUse {
                    holder: None,
                    name: slice(text, node).trim_start_matches('*').to_owned(),
                    at: node.start_byte(),
                });
                self.loose.push(self.aliases.len() - 1);
                Ok(())
            }
            kind if self.workflow && is_scalar(kind) => self.expression_regions(text, node, out),
            _ => {
                let mut cur = node.walk();
                for c in node.named_children(&mut cur) {
                    self.walk(text, c, out)?;
                }
                Ok(())
            }
        }
    }

    /// Adds a `region(expr)` node for each `${{ }}` inside scalar `node`.
    fn expression_regions(
        &mut self,
        text: &str,
        node: tree_sitter::Node<'_>,
        out: &mut Vec<NodeId>,
    ) -> Result<(), TermError> {
        let raw = slice(text, node);
        for (start, end, inner) in expressions(raw) {
            let loc = self
                .cx
                .loc(node.start_byte() + start, node.start_byte() + end);
            let body = self.cx.add(
                NodeSpec::new(Operator::lit("text", inner), loc.clone()),
                &[],
            )?;
            out.push(
                self.cx
                    .add(NodeSpec::new(Operator::region("expr"), loc), &[body])?,
            );
            tracing::trace!(expr = inner, "workflow expression region");
        }
        Ok(())
    }

    /// Adds the `run` shell region or `uses` instantiate node for a pair named `name`.
    fn step_regions(
        &mut self,
        text: &str,
        name: &str,
        value: Option<tree_sitter::Node<'_>>,
        out: &mut Vec<NodeId>,
    ) -> Result<(), TermError> {
        let Some(leaf) = value.and_then(scalar_leaf) else {
            return Ok(());
        };
        let body = scalar_body(leaf.kind(), slice(text, leaf));
        let loc = self.cx.node_loc(leaf);
        match name {
            "run" => {
                let script = self.cx.add(
                    NodeSpec::new(Operator::lit("text", &body), loc.clone()),
                    &[],
                )?;
                out.push(
                    self.cx
                        .add(NodeSpec::new(Operator::region("shell"), loc), &[script])?,
                );
                tracing::trace!(bytes = body.len(), "workflow shell region");
            }
            "uses" => {
                let reference = body.trim();
                if reference.is_empty() || reference.starts_with('.') {
                    return Ok(());
                }
                let reference = reference.strip_prefix("docker://").unwrap_or(reference);
                let target = self.cx.add(
                    NodeSpec::new(Operator::reference(reference), loc.clone()),
                    &[],
                )?;
                out.push(self.cx.add(
                    NodeSpec::new(Operator::apply("instantiate"), loc),
                    &[target],
                )?);
                self.uses.push((leaf.start_byte(), reference.to_owned()));
                tracing::trace!(reference, "workflow instantiate node");
            }
            _ => {}
        }
        Ok(())
    }

    /// Fold `node` (a pair or item) as a unit named `name`, or pass its units up when unnamed.
    fn walk_unit(
        &mut self,
        text: &str,
        node: tree_sitter::Node<'_>,
        name: Option<String>,
        value: Option<tree_sitter::Node<'_>>,
        out: &mut Vec<NodeId>,
    ) -> Result<(), TermError> {
        let mark = self.loose.len();
        let mut nested = Vec::new();
        let mut cur = node.walk();
        for c in node.named_children(&mut cur) {
            if node.kind() == "block_mapping_pair" && c.id() == pair_key_id(node) {
                continue;
            }
            self.walk(text, c, &mut nested)?;
        }
        let Some(name) = name else {
            out.extend(nested);
            return Ok(());
        };
        if self.workflow && node.kind() == "block_mapping_pair" {
            self.step_regions(text, &name, value, &mut nested)?;
        }
        let (start, end) = (node.start_byte(), node.end_byte());
        let loc = self.cx.loc(start, end);
        let key = self
            .cx
            .add(NodeSpec::new(Operator::lit("key", &name), loc.clone()), &[])?;
        let sig = self.cx.add(
            NodeSpec::new(Operator::group(GroupOrder::Sequence), loc.clone())
                .attr(reserved::FACET, "sig"),
            &[key],
        )?;
        let body = self.cx.add(
            NodeSpec::new(Operator::lit("text", &text[start..end]), loc.clone()),
            &[],
        )?;
        let mut children = vec![sig, body];
        children.extend(nested);
        let unit = self.cx.add(
            NodeSpec::new(Operator::unit("key", "impl"), loc).named(&name),
            &children,
        )?;
        for i in self.loose.split_off(mark) {
            self.aliases[i].holder = Some(unit);
        }
        if let Some(anchor) = value.and_then(|v| anchor_of(text, v)) {
            self.anchors.push(AnchorDef {
                name: anchor,
                at: start,
                unit,
            });
        }
        out.push(unit);
        Ok(())
    }
}

/// The job (`jobs.<name>`) of `file` containing byte `offset`, else the file itself.
pub(crate) fn owner_of(file: &FileSymbols, offset: usize) -> Symref {
    let at = u32::try_from(offset).unwrap_or(u32::MAX).into();
    file.symbols
        .iter()
        .find(|s| {
            let segs = s.symref.segments();
            segs.len() == 2 && segs[0] == "jobs" && s.span.contains(at)
        })
        .map_or_else(|| Symref::file(&file.path), |s| s.symref.clone())
}

/// The node id of a pair's key child (skipped when folding the pair's value side).
fn pair_key_id(pair: tree_sitter::Node<'_>) -> usize {
    pair.child_by_field_name("key")
        .map_or(usize::MAX, |k| k.id())
}

/// Fold a clean syntax tree (fidelity F2 units, anchors and aliases as references).
fn fold_tree(
    tree: &ParsedTree,
    input: &FileInput<'_>,
    workflow: bool,
) -> Result<Folded, FoldError> {
    let text: &str = &tree.text;
    let mut cx = Cx::new(input.path, "yaml", text);
    let mut tf = TreeFold {
        cx: &mut cx,
        anchors: Vec::new(),
        aliases: Vec::new(),
        loose: Vec::new(),
        workflow,
        uses: Vec::new(),
    };
    let mut units = Vec::new();
    tf.walk(text, tree.root(), &mut units)?;
    let (anchors, aliases, uses) = (tf.anchors, tf.aliases, tf.uses);
    let root = cx.add(file_root_spec(&cx, input.size as usize), &units)?;
    let term = cx.b.finish(root)?;
    let scopes = ScopeGraph::from_term(&term);
    let v = view::build(&term, input.path, Naming::Model);
    let mut file = base_file(input, "yaml");
    file.fidelity = Fidelity::F1;
    file.parse_status = ParseStatus::Complete;
    for a in &aliases {
        let target = anchors
            .iter()
            .filter(|d| d.name == a.name && d.at <= a.at)
            .max_by_key(|d| d.at)
            .and_then(|d| v.by_node.get(&d.unit));
        let Some(target) = target else {
            tracing::trace!(alias = %a.name, "alias without a preceding anchored unit");
            continue;
        };
        let from = a
            .holder
            .and_then(|h| v.by_node.get(&h).cloned())
            .unwrap_or_else(|| Symref::file(input.path));
        file.refs.push(RefSite {
            from,
            name: target.to_string(),
            qualifier: None,
            kind: RefKind::Depends,
        });
    }
    file.symbols = v.symbols;
    file.extras = v.extras;
    for (at, name) in uses {
        file.refs.push(RefSite {
            from: owner_of(&file, at),
            name,
            qualifier: None,
            kind: RefKind::Instantiate,
        });
    }
    tracing::debug!(
        path = input.path,
        keys = file.symbols.len(),
        refs = file.refs.len(),
        "yaml tree folded"
    );
    Ok(Folded { term, scopes, file })
}

/// Fold by the line scan (fidelity F1), the fallback when no clean tree is available.
fn fold_lines(text: &str, input: &FileInput<'_>) -> Result<Folded, FoldError> {
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

    fn fold(text: &str) -> crate::model::FileSymbols {
        let size = u32::try_from(text.len()).expect("small");
        let input = FileInput {
            path: "ci.yml",
            digest: "d",
            size,
        };
        fold_text(text, &input).expect("fold").file
    }

    // frob:ticket 01M4MDH6NJXB6YK5NZFKC4NSBJ
    // frob:tests crates/gob-symbols/src/yaml.rs::fold_text
    #[test]
    fn each_sequence_item_is_its_own_unit() {
        let t = "steps:\n  - uses: a@v1\n  - uses: b@v1\n";
        let f = fold(t);
        let refs: Vec<String> = f.symbols.iter().map(|s| s.symref.to_string()).collect();
        assert!(refs.iter().any(|r| r.ends_with("steps.0")), "{refs:?}");
        assert!(refs.iter().any(|r| r.ends_with("steps.1.uses")), "{refs:?}");
        let first = f
            .symbols
            .iter()
            .find(|s| s.symref.to_string().ends_with("steps.0"))
            .expect("item");
        let (a, b) = (u32::from(first.span.start()), u32::from(first.span.end()));
        assert_eq!(&t[a as usize..b as usize], "- uses: a@v1");
    }

    // frob:ticket 01M4MDH6NJXB6YK5NZFKC4NSBJ
    // frob:tests crates/gob-symbols/src/yaml.rs::fold_text
    #[test]
    fn an_alias_references_the_anchored_key_unit() {
        let t = "base: &defaults\n  retries: 3\nprod:\n  <<: *defaults\n  host: x\n";
        let f = fold(t);
        assert_eq!(f.refs.len(), 1, "{:?}", f.refs);
        let r = &f.refs[0];
        assert!(r.name.ends_with("base"), "{}", r.name);
        assert!(r.from.to_string().ends_with("prod"), "{}", r.from);
        assert_eq!(r.kind, RefKind::Depends);
    }

    /// Term operator tags under the whole fold of workflow `text`.
    fn workflow_ops(text: &str) -> Vec<String> {
        let size = u32::try_from(text.len()).expect("small");
        let input = FileInput {
            path: ".github/workflows/ci.yml",
            digest: "d",
            size,
        };
        let (folded, _) = fold_workflow(text, &input).expect("fold");
        let term = &folded.term;
        term.ids()
            .map(|id| format!("{:?}", term.node(id).op()))
            .collect()
    }

    const WF: &str =
        "jobs:\n  b:\n    steps:\n      - uses: a/b@v1\n      - run: echo ${{ github.sha }}\n";

    // frob:ticket 01M5CH6Z005WE93MXMAP17WEBJ
    // frob:tests crates/gob-symbols/src/yaml.rs::fold_workflow
    #[test]
    fn uses_is_an_instantiate_apply_node() {
        assert!(
            workflow_ops(WF)
                .iter()
                .any(|t| t.contains("Apply") && t.contains("instantiate"))
        );
    }

    // frob:ticket 01M5CH6Z005WE93MXMAP17WEBJ
    // frob:tests crates/gob-symbols/src/yaml.rs::fold_workflow
    #[test]
    fn run_is_a_shell_region() {
        assert!(
            workflow_ops(WF)
                .iter()
                .any(|t| t.contains("Region") && t.contains("shell"))
        );
    }

    // frob:ticket 01M5CH6Z005WE93MXMAP17WEBJ
    // frob:tests crates/gob-symbols/src/yaml.rs::fold_workflow
    #[test]
    fn expression_is_an_expr_region() {
        assert!(
            workflow_ops(WF)
                .iter()
                .any(|t| t.contains("Region") && t.contains("expr"))
        );
    }

    // frob:ticket 01M5CH6Z005WE93MXMAP17WEBJ
    // frob:tests crates/gob-symbols/src/yaml.rs::fold_workflow
    #[test]
    fn plain_yaml_has_no_region_nodes() {
        let ops = names_of_plain();
        assert!(!ops.iter().any(|t| t.contains("Region")));
    }

    /// Operator tags of the plain (non-workflow) fold of [`WF`].
    fn names_of_plain() -> Vec<String> {
        let input = FileInput {
            path: "ci.yml",
            digest: "d",
            size: u32::try_from(WF.len()).expect("small"),
        };
        let folded = fold_text(WF, &input).expect("fold");
        folded
            .term
            .ids()
            .map(|id| format!("{:?}", folded.term.node(id).op()))
            .collect()
    }

    // frob:ticket 01M4MDH6NJXB6YK5NZFKC4NSBJ
    // frob:tests crates/gob-symbols/src/yaml.rs::fold_text
    #[test]
    // frob:accept PATH001 because="false positive: the literal is YAML with a backslash-n escape, not a drive path"
    fn broken_yaml_falls_back_to_the_line_scan() {
        let f = fold("a:\n  b: [1\nc: 2\n");
        assert!(!f.symbols.is_empty());
    }
}
