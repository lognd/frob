//! Rust extraction: symbols, imports and call sites from a tree-sitter tree.

use std::collections::HashMap;
use std::fmt::Write as _;

use gob_languages::ParsedTree;
use tree_sitter::Node;

use crate::model::{
    CallSite, Digests, FileSymbols, ImportEdge, SymbolKind, SymbolRecord, Visibility, collapse_ws,
};
use crate::paths::crate_and_module;
use crate::symref::Symref;

/// Where the item being visited lives.
#[derive(Clone)]
struct Scope {
    qual: Vec<String>,
    parent: Option<usize>,
    /// Inside an impl or trait: functions are methods.
    member: bool,
    /// Visibility inherited by members that carry no modifier (trait items,
    /// enum variants) or `None` to read each item's own modifier.
    inherit: Option<Visibility>,
    implements: Option<String>,
    /// True inside `impl` blocks (members without a modifier are not private
    /// in the trait-impl case; the impl block visibility gates them later).
    trait_impl: bool,
}

struct Extractor<'a> {
    text: &'a str,
    path: &'a str,
    module: Vec<String>,
    out: FileSymbols,
    parents: Vec<Option<usize>>,
    raw_calls: Vec<(usize, CallSite)>,
}

/// Extracts everything from a parsed Rust file.
pub fn extract(tree: &ParsedTree, path: &str, out: FileSymbols) -> FileSymbols {
    let (_, module) = crate_and_module(path);
    let mut ex = Extractor {
        text: &tree.text,
        path,
        module,
        out,
        parents: Vec::new(),
        raw_calls: Vec::new(),
    };
    let scope = Scope {
        qual: Vec::new(),
        parent: None,
        member: false,
        inherit: None,
        implements: None,
        trait_impl: false,
    };
    ex.items(tree.root(), &scope);
    ex.finish()
}

fn node_text<'t>(text: &'t str, n: Node<'_>) -> &'t str {
    &text[n.start_byte()..n.end_byte()]
}

impl Extractor<'_> {
    fn t(&self, n: Node<'_>) -> &str {
        node_text(self.text, n)
    }

    fn items(&mut self, container: Node<'_>, scope: &Scope) {
        let mut cursor = container.walk();
        let children: Vec<Node<'_>> = container.named_children(&mut cursor).collect();
        for node in children {
            self.item(node, scope);
        }
    }

    fn visibility(&self, node: Node<'_>, scope: &Scope) -> Visibility {
        let mut c = node.walk();
        let modifier = node
            .children(&mut c)
            .find(|k| k.kind() == "visibility_modifier");
        match modifier {
            Some(m) => {
                let t = collapse_ws(self.t(m));
                if t == "pub" {
                    Visibility::Public
                } else if t.replace(' ', "") == "pub(self)" {
                    Visibility::Private
                } else {
                    Visibility::Crate
                }
            }
            None => scope.inherit.unwrap_or(if scope.trait_impl {
                Visibility::Public
            } else {
                Visibility::Private
            }),
        }
    }

    /// Doc comment text for `node`: contiguous `///` or `/** */` siblings
    /// directly above it (attributes in between are skipped).
    fn doc(&self, node: Node<'_>) -> String {
        let mut lines: Vec<String> = Vec::new();
        let mut cur = node.prev_sibling();
        while let Some(p) = cur {
            match p.kind() {
                "attribute_item" => {}
                "line_comment" => {
                    let t = self.t(p).trim_end();
                    if t.starts_with("///") && !t.starts_with("////") {
                        lines.push(t[3..].trim().to_owned());
                    } else {
                        break;
                    }
                }
                "block_comment" => {
                    let t = self.t(p);
                    if t.starts_with("/**") && !t.starts_with("/***") && t != "/**/" {
                        let inner = t.trim_start_matches("/**").trim_end_matches("*/");
                        lines.push(collapse_ws(inner));
                    } else {
                        break;
                    }
                }
                _ => break,
            }
            cur = p.prev_sibling();
        }
        lines.reverse();
        lines.join("\n")
    }

    fn span_of(node: Node<'_>) -> gob_text::TextRange {
        let clamp = |n: usize| gob_text::TextSize::new(u32::try_from(n).unwrap_or(u32::MAX));
        gob_text::TextRange::new(clamp(node.start_byte()), clamp(node.end_byte()))
    }

    /// Appends a record from precomputed facet texts; returns its index.
    #[allow(
        clippy::too_many_arguments,
        reason = "one record constructor, all inputs distinct"
    )]
    fn record(
        &mut self,
        node: Node<'_>,
        segments: Vec<String>,
        kind: SymbolKind,
        visibility: Visibility,
        facets: (&str, &str, &str),
        scope: &Scope,
        implements: Option<String>,
    ) -> usize {
        let symref = Symref::symbol(self.path, segments);
        tracing::trace!(%symref, ?kind, "rust symbol");
        self.out.symbols.push(SymbolRecord {
            symref,
            kind,
            span: Self::span_of(node),
            visibility,
            digests: Digests::of_facets(facets.0, facets.1, facets.2),
            parent: None,
            implements,
        });
        self.parents.push(scope.parent);
        self.out.symbols.len() - 1
    }

    /// Appends a record whose sig is the item text minus `body`.
    #[allow(
        clippy::too_many_arguments,
        reason = "one record constructor, all inputs distinct"
    )]
    fn push(
        &mut self,
        node: Node<'_>,
        segments: Vec<String>,
        kind: SymbolKind,
        visibility: Visibility,
        body: Option<Node<'_>>,
        scope: &Scope,
        implements: Option<String>,
    ) -> usize {
        let (sig, body_text) = match body {
            Some(b) => {
                let head = &self.text[node.start_byte()..b.start_byte()];
                let tail = &self.text[b.end_byte()..node.end_byte()];
                (
                    collapse_ws(&format!("{head} {tail}")),
                    collapse_ws(self.t(b)),
                )
            }
            None => (collapse_ws(self.t(node)), String::new()),
        };
        let doc = self.doc(node);
        self.record(
            node,
            segments,
            kind,
            visibility,
            (&sig, &body_text, &doc),
            scope,
            implements,
        )
    }

    fn qual_of(&self, idx: usize) -> Vec<String> {
        self.out.symbols[idx].symref.segments().to_vec()
    }

    fn named(&self, node: Node<'_>) -> Option<String> {
        node.child_by_field_name("name")
            .map(|n| self.t(n).to_owned())
    }

    fn item(&mut self, node: Node<'_>, scope: &Scope) {
        let kind = node.kind();
        match kind {
            "use_declaration" => self.use_decl(node),
            "function_item" | "function_signature_item" => self.function(node, scope),
            "struct_item" | "union_item" => {
                self.simple(node, SymbolKind::Struct, scope);
            }
            "enum_item" => self.enum_item(node, scope),
            "trait_item" => self.trait_item(node, scope),
            "impl_item" => self.impl_item(node, scope),
            "mod_item" => self.mod_item(node, scope),
            "const_item" => self.value_item(node, SymbolKind::Const, scope),
            "static_item" => self.value_item(node, SymbolKind::Static, scope),
            "type_item" => {
                self.simple(node, SymbolKind::TypeAlias, scope);
            }
            "macro_definition" => self.macro_def(node, scope),
            _ => {}
        }
    }

    fn qual_with(scope: &Scope, name: &str) -> Vec<String> {
        let mut q = scope.qual.clone();
        q.push(name.to_owned());
        q
    }

    fn simple(&mut self, node: Node<'_>, kind: SymbolKind, scope: &Scope) -> Option<usize> {
        let name = self.named(node)?;
        let vis = self.visibility(node, scope);
        let body = node.child_by_field_name("body");
        let q = Self::qual_with(scope, &name);
        Some(self.push(node, q, kind, vis, body, scope, scope.implements.clone()))
    }

    fn function(&mut self, node: Node<'_>, scope: &Scope) {
        let Some(name) = self.named(node) else { return };
        let vis = self.visibility(node, scope);
        let body = node.child_by_field_name("body");
        let kind = if scope.member {
            SymbolKind::Method
        } else {
            SymbolKind::Function
        };
        let q = Self::qual_with(scope, &name);
        let sym = self.push(node, q, kind, vis, body, scope, scope.implements.clone());
        if let Some(b) = body {
            self.calls(b, sym);
        }
    }

    fn value_item(&mut self, node: Node<'_>, kind: SymbolKind, scope: &Scope) {
        let Some(name) = self.named(node) else { return };
        let vis = self.visibility(node, scope);
        let body = node.child_by_field_name("value");
        let q = Self::qual_with(scope, &name);
        self.push(node, q, kind, vis, body, scope, scope.implements.clone());
    }

    fn macro_def(&mut self, node: Node<'_>, scope: &Scope) {
        let Some(name_node) = node.child_by_field_name("name") else {
            return;
        };
        let name = self.t(name_node).to_owned();
        let sig = collapse_ws(&format!("macro_rules! {name}"));
        let body = collapse_ws(&self.text[name_node.end_byte()..node.end_byte()]);
        let doc = self.doc(node);
        let vis = if self.has_macro_export(node) {
            Visibility::Public
        } else {
            Visibility::Private
        };
        let q = Self::qual_with(scope, &name);
        self.record(
            node,
            q,
            SymbolKind::Macro,
            vis,
            (&sig, &body, &doc),
            scope,
            None,
        );
    }

    fn has_macro_export(&self, node: Node<'_>) -> bool {
        let mut cur = node.prev_sibling();
        while let Some(p) = cur {
            match p.kind() {
                "attribute_item" => {
                    if self.t(p).contains("macro_export") {
                        return true;
                    }
                }
                "line_comment" | "block_comment" => {}
                _ => return false,
            }
            cur = p.prev_sibling();
        }
        false
    }

    fn enum_item(&mut self, node: Node<'_>, scope: &Scope) {
        let Some(sym) = self.simple(node, SymbolKind::Enum, scope) else {
            return;
        };
        let vis = self.visibility(node, scope);
        let Some(body) = node.child_by_field_name("body") else {
            return;
        };
        let inner = Scope {
            qual: self.qual_of(sym),
            parent: Some(sym),
            member: false,
            inherit: Some(vis),
            implements: None,
            trait_impl: false,
        };
        let mut c = body.walk();
        let variants: Vec<Node<'_>> = body
            .named_children(&mut c)
            .filter(|n| n.kind() == "enum_variant")
            .collect();
        for v in variants {
            let Some(name) = self.named(v) else { continue };
            let q = Self::qual_with(&inner, &name);
            let vbody = v.child_by_field_name("body");
            self.push(v, q, SymbolKind::Variant, vis, vbody, &inner, None);
        }
    }

    fn trait_item(&mut self, node: Node<'_>, scope: &Scope) {
        let Some(sym) = self.simple(node, SymbolKind::Trait, scope) else {
            return;
        };
        let vis = self.visibility(node, scope);
        if let Some(body) = node.child_by_field_name("body") {
            let inner = Scope {
                qual: self.qual_of(sym),
                parent: Some(sym),
                member: true,
                inherit: Some(vis),
                implements: None,
                trait_impl: false,
            };
            self.items(body, &inner);
        }
    }

    fn type_name(&self, node: Node<'_>) -> String {
        match node.kind() {
            "generic_type" | "reference_type" | "pointer_type" => node
                .child_by_field_name("type")
                .map_or_else(|| collapse_ws(self.t(node)), |n| self.type_name(n)),
            "scoped_type_identifier" => node
                .child_by_field_name("name")
                .map_or_else(|| collapse_ws(self.t(node)), |n| self.t(n).to_owned()),
            _ => collapse_ws(self.t(node)),
        }
    }

    fn impl_item(&mut self, node: Node<'_>, scope: &Scope) {
        let Some(ty) = node.child_by_field_name("type") else {
            return;
        };
        let tname = self.type_name(ty);
        let tr: Option<String> = node
            .child_by_field_name("trait")
            .map(|n| self.t(n).split_whitespace().collect());
        let label = tr.clone().unwrap_or_else(|| "impl".to_owned());
        let mut q = scope.qual.clone();
        q.push(format!("{tname}[{label}]"));
        // Visibility of the block is patched in `finish` from the target type.
        let sym = self.push(
            node,
            q,
            SymbolKind::Impl,
            Visibility::Public,
            node.child_by_field_name("body"),
            scope,
            tr.clone(),
        );
        if let Some(body) = node.child_by_field_name("body") {
            let mut member_qual = scope.qual.clone();
            member_qual.push(tname);
            let inner = Scope {
                qual: member_qual,
                parent: Some(sym),
                member: true,
                inherit: None,
                implements: tr.clone(),
                trait_impl: tr.is_some(),
            };
            self.items(body, &inner);
        }
    }

    fn mod_item(&mut self, node: Node<'_>, scope: &Scope) {
        let Some(sym) = self.simple(node, SymbolKind::Module, scope) else {
            return;
        };
        if let Some(body) = node.child_by_field_name("body") {
            let inner = Scope {
                qual: self.qual_of(sym),
                parent: Some(sym),
                member: false,
                inherit: None,
                implements: None,
                trait_impl: false,
            };
            self.items(body, &inner);
        }
    }

    // ---- imports ----

    fn use_decl(&mut self, node: Node<'_>) {
        let Some(arg) = node.child_by_field_name("argument") else {
            return;
        };
        let mut paths = Vec::new();
        self.flatten_use(arg, &[], &mut paths);
        for p in paths {
            let target = self.normalize_import(&p);
            tracing::trace!(file = self.path, %target, "rust import");
            self.out.imports.push(ImportEdge {
                from_file: self.path.to_owned(),
                target,
            });
        }
    }

    fn flatten_use(&self, node: Node<'_>, prefix: &[String], out: &mut Vec<Vec<String>>) {
        let with = |segs: Vec<String>| {
            let mut v = prefix.to_vec();
            v.extend(segs);
            v
        };
        match node.kind() {
            "scoped_use_list" => {
                let mut pre = prefix.to_vec();
                if let Some(p) = node.child_by_field_name("path") {
                    pre.extend(split_path(self.t(p)));
                }
                if let Some(list) = node.child_by_field_name("list") {
                    self.flatten_use(list, &pre, out);
                }
            }
            "use_list" => {
                let mut c = node.walk();
                for ch in node.named_children(&mut c) {
                    self.flatten_use(ch, prefix, out);
                }
            }
            "use_as_clause" => {
                if let Some(p) = node.child_by_field_name("path") {
                    self.flatten_use(p, prefix, out);
                }
            }
            "use_wildcard" => {
                let mut segs = Vec::new();
                let mut c = node.walk();
                if let Some(p) = node.named_children(&mut c).next() {
                    segs = split_path(self.t(p));
                }
                segs.push("*".to_owned());
                out.push(with(segs));
            }
            "line_comment" | "block_comment" => {}
            _ => {
                let segs = split_path(self.t(node));
                if segs.len() == 1 && segs[0] == "self" && !prefix.is_empty() {
                    out.push(prefix.to_vec());
                } else {
                    out.push(with(segs));
                }
            }
        }
    }

    fn normalize_import(&self, segs: &[String]) -> String {
        let join = |v: &[String]| v.join("::");
        match segs.first().map(String::as_str) {
            Some("self") => {
                let mut v = vec!["crate".to_owned()];
                v.extend(self.module.iter().cloned());
                v.extend(segs[1..].iter().cloned());
                join(&v)
            }
            Some("super") => {
                let mut module = self.module.clone();
                let mut i = 0;
                while segs.get(i).is_some_and(|s| s == "super") {
                    module.pop();
                    i += 1;
                }
                let mut v = vec!["crate".to_owned()];
                v.extend(module);
                v.extend(segs[i..].iter().cloned());
                join(&v)
            }
            _ => join(segs),
        }
    }

    // ---- calls ----

    fn calls(&mut self, body: Node<'_>, caller: usize) {
        let mut stack = vec![body];
        while let Some(n) = stack.pop() {
            if n.kind() == "call_expression"
                && let Some(f) = n.child_by_field_name("function")
            {
                self.call_target(f, caller);
            }
            let mut c = n.walk();
            let kids: Vec<Node<'_>> = n.named_children(&mut c).collect();
            // Reverse so the stack pops in source order.
            stack.extend(kids.into_iter().rev());
        }
    }

    fn call_target(&mut self, f: Node<'_>, caller: usize) {
        let (name, qualifier, method) = match f.kind() {
            "identifier" => (self.t(f).to_owned(), None, false),
            "scoped_identifier" => {
                let leaf = f.child_by_field_name("name").map(|n| self.t(n).to_owned());
                let qual = f.child_by_field_name("path").and_then(|p| {
                    strip_generics(self.t(p))
                        .rsplit("::")
                        .next()
                        .map(str::to_owned)
                });
                match leaf {
                    Some(n) => (n, qual, false),
                    None => return,
                }
            }
            "field_expression" => match f.child_by_field_name("field") {
                Some(n) => (self.t(n).to_owned(), None, true),
                None => return,
            },
            "generic_function" => {
                if let Some(inner) = f.child_by_field_name("function") {
                    self.call_target(inner, caller);
                }
                return;
            }
            _ => return,
        };
        self.raw_calls.push((
            caller,
            CallSite {
                caller: Symref::file(self.path),
                callee: name,
                qualifier,
                method,
            },
        ));
    }

    // ---- post-processing ----

    fn finish(mut self) -> FileSymbols {
        self.patch_impl_visibility();
        self.disambiguate();
        let refs: Vec<Symref> = self.out.symbols.iter().map(|s| s.symref.clone()).collect();
        for (s, p) in self.out.symbols.iter_mut().zip(&self.parents) {
            s.parent = p.map(|i| refs[i].clone());
        }
        for (idx, mut call) in self.raw_calls {
            call.caller = refs[idx].clone();
            self.out.calls.push(call);
        }
        self.out
    }

    /// Impl blocks and their members take the visibility of the target type
    /// when it is defined in this file; otherwise the block is public.
    fn patch_impl_visibility(&mut self) {
        let types: HashMap<Vec<String>, Visibility> = self
            .out
            .symbols
            .iter()
            .filter(|s| {
                matches!(
                    s.kind,
                    SymbolKind::Struct
                        | SymbolKind::Enum
                        | SymbolKind::TypeAlias
                        | SymbolKind::Trait
                )
            })
            .map(|s| (s.symref.segments().to_vec(), s.visibility))
            .collect();
        for s in &mut self.out.symbols {
            if s.kind == SymbolKind::Impl {
                let mut segs = s.symref.segments().to_vec();
                if let Some(last) = segs.last_mut()
                    && let Some((ty, _)) = last.split_once('[')
                {
                    *last = ty.to_owned();
                }
                s.visibility = types.get(&segs).copied().unwrap_or(Visibility::Public);
            }
        }
    }

    /// Makes symrefs unique within the file: colliding trait-impl members
    /// become `Type[Trait].m`, remaining collisions get a `[dupN]` suffix.
    fn disambiguate(&mut self) {
        let mut counts: HashMap<Symref, usize> = HashMap::new();
        for s in &self.out.symbols {
            *counts.entry(s.symref.clone()).or_default() += 1;
        }
        for s in &mut self.out.symbols {
            let n = s.symref.segments().len();
            if counts[&s.symref] > 1
                && s.kind != SymbolKind::Impl
                && let Some(tr) = &s.implements
                && n >= 2
            {
                let mut segs = s.symref.segments().to_vec();
                segs[n - 2] = format!("{}[{tr}]", segs[n - 2]);
                s.symref = s.symref.with_segments(segs);
            }
        }
        let mut seen: HashMap<Symref, usize> = HashMap::new();
        for s in &mut self.out.symbols {
            let n = seen.entry(s.symref.clone()).or_default();
            *n += 1;
            if *n > 1 {
                let mut segs = s.symref.segments().to_vec();
                if let Some(last) = segs.last_mut() {
                    let _ = write!(last, "[dup{n}]");
                }
                s.symref = s.symref.with_segments(segs);
            }
        }
    }
}

fn split_path(s: &str) -> Vec<String> {
    strip_generics(s)
        .split("::")
        .map(|p| p.split_whitespace().collect::<String>())
        .filter(|p| !p.is_empty())
        .collect()
}

/// Removes `<...>` generic arguments (nesting-aware).
fn strip_generics(s: &str) -> String {
    let mut depth = 0u32;
    let mut out = String::new();
    for ch in s.chars() {
        match ch {
            '<' => depth += 1,
            '>' => depth = depth.saturating_sub(1),
            _ if depth == 0 => out.push(ch),
            _ => {}
        }
    }
    out
}
