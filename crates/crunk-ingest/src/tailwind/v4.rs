//! The static Tailwind 4 reader: `@theme` custom properties of a CSS-first config.
//!
//! The fallback when the project's own Tailwind cannot be run. `--namespace-key: value` custom
//! properties of every `@theme` / `@theme inline` block are read through the CSS adapter, `var()`
//! references among them are resolved, and a `calc()` or an unresolvable `var()` is kept verbatim
//! and reported as opaque, never guessed.

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

use std::collections::HashSet;

use gob_ir::{Model, NodeId, style};
use gob_symbols::fold_file;
use gob_walk::{Digest, FileEntry, LanguageHint};
use indexmap::IndexMap;

use crate::lex::{Kind, inner_tokens, tokenize};
use crate::parse::FoldFailure;

/// Tailwind 4's built-in `@theme` namespaces, longest first so `font-weight` beats `font`.
const KNOWN_NAMESPACES: [&str; 16] = [
    "inset-shadow",
    "font-weight",
    "drop-shadow",
    "breakpoint",
    "container",
    "spacing",
    "tracking",
    "leading",
    "shadow",
    "aspect",
    "radius",
    "color",
    "blur",
    "ease",
    "font",
    "text",
];

/// What the static v4 reader found in one CSS file.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct V4Read {
    /// Namespace-stripped `{key: value}` of every `@theme` custom property, in order.
    pub theme: IndexMap<String, String>,
    /// The raw `--name` of every `@theme` custom property with its resolved value, in order.
    pub raw: IndexMap<String, String>,
    /// Raw names whose value stayed opaque (`calc()` or an unresolved `var()`).
    pub opaque: Vec<String>,
    /// The first `@config "path"` reference.
    pub config_ref: Option<String>,
    /// Whether `@import "tailwindcss"` or an `@theme` rule was seen.
    pub is_v4: bool,
}

/// Strip a known `--<namespace>-` prefix: `--color-primary` is `primary`; an unknown namespace
/// keeps the whole name minus `--`.
pub fn split_namespace(var_name: &str) -> String {
    let bare = var_name.strip_prefix("--").unwrap_or(var_name);
    for ns in KNOWN_NAMESPACES {
        if bare == ns {
            return bare.to_owned();
        }
        if let Some(rest) = bare.strip_prefix(ns).and_then(|r| r.strip_prefix('-')) {
            return rest.to_owned();
        }
    }
    bare.to_owned()
}

/// The text of the first quoted string in an at-rule prelude.
fn first_string(prelude: &str) -> Option<String> {
    let toks = tokenize(prelude);
    toks.iter()
        .find(|t| t.kind == Kind::Str)
        .map(|t| unquote(t.text(prelude)))
}

fn unquote(text: &str) -> String {
    let inner = text
        .strip_prefix(['"', '\''])
        .and_then(|t| t.strip_suffix(['"', '\'']))
        .unwrap_or(text);
    inner.to_owned()
}

/// The `--name` a value refers to when it is only one `var(--name)` call.
fn sole_var_reference(raw: &str) -> Option<String> {
    let toks: Vec<_> = tokenize(raw)
        .into_iter()
        .filter(|t| !t.is_trivia())
        .collect();
    let [only] = toks.as_slice() else {
        return None;
    };
    if only.kind != Kind::Function || !only.text(raw).to_ascii_lowercase().starts_with("var(") {
        return None;
    }
    inner_tokens(raw, only)
        .into_iter()
        .find(|t| t.kind == Kind::Ident && t.text(raw).starts_with("--"))
        .map(|t| t.text(raw).to_owned())
}

/// Whether `calc(` appears anywhere in the value, nested calls included.
fn contains_calc(raw: &str) -> bool {
    tokenize(raw).iter().any(|t| {
        t.kind == Kind::Function
            && (t.text(raw).to_ascii_lowercase().starts_with("calc(")
                || t.inner.is_some()
                    && contains_calc(&raw[t.inner.map_or(0, |i| i.0)..t.inner.map_or(0, |i| i.1)]))
    })
}

/// The path of the first top-level `@config "path";` (the CSS adapter keeps no node for this
/// block-less at-rule, so the source is tokenized; blocks are single tokens, so only top-level
/// statements are seen).
fn top_level_config_ref(source: &str) -> Option<String> {
    let toks = tokenize(source);
    let mut iter = toks.iter().filter(|t| !t.is_trivia());
    while let Some(tok) = iter.next() {
        if tok.kind == Kind::AtKeyword && tok.text(source).eq_ignore_ascii_case("@config") {
            return iter
                .next()
                .filter(|t| t.kind == Kind::Str)
                .map(|t| unquote(t.text(source)));
        }
    }
    None
}

/// Resolve a `var(--x)`-only value against `raw_vars`; `calc()` and anything unresolvable come
/// back verbatim with `true` (opaque).
fn resolve(
    raw: &str,
    raw_vars: &IndexMap<String, String>,
    seen: &mut HashSet<String>,
) -> (String, bool) {
    let text = raw.trim().to_owned();
    if contains_calc(&text) {
        return (text, true);
    }
    let Some(reference) = sole_var_reference(&text) else {
        return (text, false);
    };
    if seen.contains(&reference) {
        return (text, true);
    }
    let Some(next) = raw_vars.get(&reference) else {
        return (text, true);
    };
    seen.insert(reference);
    resolve(next, raw_vars, seen)
}

/// Read the `@theme` blocks, `@config` reference and v4 markers of CSS `source`.
///
/// # Errors
///
/// [`FoldFailure`] when the CSS adapter builds an ill-formed term (an adapter bug); malformed
/// CSS yields fewer entries instead.
pub fn read_v4(source: &str) -> Result<V4Read, FoldFailure> {
    let entry = FileEntry {
        path: "tailwind-config.css".to_owned(),
        size: source.len() as u64,
        digest: Digest::of(source.as_bytes()),
        language: LanguageHint::Other("css".to_owned()),
    };
    let folded = fold_file(&entry, source).map_err(|e| FoldFailure {
        path: entry.path.clone(),
        detail: e.to_string(),
    })?;
    let model = Model::new(folded.term, folded.scopes);
    let mut out = V4Read::default();
    let mut theme_nodes: HashSet<NodeId> = HashSet::new();
    for at in style::at_rules(&model) {
        match at.name.to_ascii_lowercase().as_str() {
            "theme" => {
                out.is_v4 = true;
                theme_nodes.insert(at.node);
            }
            "import" if first_string(&at.prelude).as_deref() == Some("tailwindcss") => {
                out.is_v4 = true;
            }
            _ => {}
        }
    }
    out.config_ref = top_level_config_ref(source);
    let mut raw_vars: IndexMap<String, String> = IndexMap::new();
    for prop in style::custom_properties(&model) {
        if prop.owner.is_some_and(|o| theme_nodes.contains(&o)) {
            raw_vars.insert(prop.name.clone(), prop.raw.trim().to_owned());
        }
    }
    for (name, raw) in &raw_vars {
        let mut seen = HashSet::from([name.clone()]);
        let (value, opaque) = resolve(raw, &raw_vars, &mut seen);
        if opaque {
            out.opaque.push(name.clone());
        }
        out.raw.insert(name.clone(), value.clone());
        out.theme.insert(split_namespace(name), value);
    }
    if !out.opaque.is_empty() {
        tracing::info!(
            count = out.opaque.len(),
            names = %out.opaque.join(", "),
            "tailwind config parse: @theme values kept opaque (calc() or unresolved var())"
        );
    }
    tracing::debug!(
        entries = out.theme.len(),
        "tailwind config parse: v4 @theme read"
    );
    Ok(out)
}
