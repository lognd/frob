//! Grammar-level patterns (docs/design/shared/rules.md section 3, level 1): a pattern written in the target
//! language's own syntax, with `$X` (one node) and `$$$ARGS` (zero or more siblings)
//! metavariables, and fix templates that splice the captures back in.
//!
//! A pattern is parsed with the same tree-sitter grammar as the source, so `print($$$ARGS)`
//! means "a call to `print` with any arguments" in every language that spells calls that way.

// frob:ticket 01M4PPRHCTN3TZ0TJF8NRQ4KHD

use std::collections::BTreeMap;
use std::ops::Range;

use gob_languages::{Language, ParseLimits, ParseResult, ParsedTree, parse};
use tree_sitter::Node;

/// Marker prefix of the identifier a metavariable is rewritten to before parsing.
const SINGLE: &str = "__GOBMV1_";
/// Marker prefix for a multi (`$$$`) metavariable.
const MULTI: &str = "__GOBMVN_";

/// Why a pattern could not be compiled or run.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum GrammarError {
    /// The language name is not one the engine knows.
    #[error("unknown language `{0}`")]
    UnknownLanguage(String),
    /// The pattern or the source did not parse.
    #[error("{what} did not parse as {language}")]
    Parse {
        /// `pattern` or `source`.
        what: &'static str,
        /// The language tag.
        language: String,
    },
    /// The pattern has no syntax node.
    #[error("pattern is empty")]
    Empty,
    /// A fix template names a metavariable the pattern never binds.
    #[error("fix uses `${0}` which the pattern does not bind")]
    UnboundInFix(String),
}

/// What one metavariable captured: its source text.
pub type Bindings = BTreeMap<String, String>;

/// One place a pattern matched.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Match {
    /// Byte range of the matched node in the source.
    pub range: Range<usize>,
    /// Metavariable name to captured source text.
    pub bindings: Bindings,
}

/// A source edit: replace `range` with `text`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Edit {
    /// Byte range to replace.
    pub range: Range<usize>,
    /// The replacement text.
    pub text: String,
}

/// A pattern compiled for one language.
#[derive(Debug, Clone)]
pub struct Pattern {
    language: Language,
    tree: ParsedTree,
    /// The pattern was wrapped in a function body because the grammar has no bare expressions.
    wrapped: bool,
}

/// Resolve a language tag (`python`, `rust`, ...) to a [`Language`].
///
/// # Errors
///
/// [`GrammarError::UnknownLanguage`] when no language has that name.
pub fn language_by_name(name: &str) -> Result<Language, GrammarError> {
    Language::ALL
        .into_iter()
        .find(|l| l.name() == name)
        .ok_or_else(|| GrammarError::UnknownLanguage(name.to_owned()))
}

/// Rewrite `$$$X` and `$X` into marker identifiers every grammar accepts.
fn rewrite(pattern: &str) -> String {
    let mut out = String::with_capacity(pattern.len() + 16);
    let b = pattern.as_bytes();
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'$' {
            let dollars = b[i..].iter().take_while(|&&c| c == b'$').count();
            let name = ident_len(&b[i + dollars..]);
            if (dollars == 1 || dollars == 3) && name > 0 {
                out.push_str(if dollars == 3 { MULTI } else { SINGLE });
                out.push_str(&pattern[i + dollars..i + dollars + name]);
                i += dollars + name;
                continue;
            }
        }
        let ch = pattern[i..].chars().next().unwrap_or(' ');
        out.push(ch);
        i += ch.len_utf8();
    }
    out
}

/// Length of the leading `[A-Z0-9_]+` metavariable name starting with a letter or `_`.
fn ident_len(b: &[u8]) -> usize {
    match b.first() {
        Some(c) if c.is_ascii_uppercase() || *c == b'_' => b
            .iter()
            .take_while(|c| c.is_ascii_uppercase() || c.is_ascii_digit() || **c == b'_')
            .count(),
        _ => 0,
    }
}

/// `(is_multi, name)` when `text` is exactly one marker identifier.
fn marker(text: &str) -> Option<(bool, &str)> {
    text.strip_prefix(MULTI)
        .map(|n| (true, n))
        .or_else(|| text.strip_prefix(SINGLE).map(|n| (false, n)))
}

fn parse_as(
    language: Language,
    text: &str,
    what: &'static str,
) -> Result<ParsedTree, GrammarError> {
    match parse(language, text, &ParseLimits::default()) {
        ParseResult::Parsed(t) => Ok(t),
        ParseResult::Unresolved(_) => Err(GrammarError::Parse {
            what,
            language: language.name().to_owned(),
        }),
    }
}

impl Pattern {
    /// Compile `pattern` for the language tagged `language`.
    ///
    /// # Errors
    ///
    /// [`GrammarError`] when the language is unknown or the pattern does not parse.
    pub fn compile(language: &str, pattern: &str) -> Result<Self, GrammarError> {
        let language = language_by_name(language)?;
        let rewritten = rewrite(pattern.trim());
        let bare = parse_as(language, &rewritten, "pattern")?;
        let (tree, wrapped) = if bare.has_errors() && language == Language::Rust {
            (
                parse_as(
                    language,
                    &format!("fn __gob() {{\n{rewritten}\n}}"),
                    "pattern",
                )?,
                true,
            )
        } else {
            (bare, false)
        };
        if tree.has_errors() {
            return Err(GrammarError::Parse {
                what: "pattern",
                language: language.name().to_owned(),
            });
        }
        let this = Self {
            language,
            tree,
            wrapped,
        };
        this.core().ok_or(GrammarError::Empty)?;
        tracing::debug!(language = language.name(), pattern, "pattern compiled");
        Ok(this)
    }

    /// Every match of the pattern in `source`, in source order.
    ///
    /// # Errors
    ///
    /// [`GrammarError::Parse`] when `source` does not parse at all.
    pub fn find(&self, source: &str) -> Result<Vec<Match>, GrammarError> {
        let target = parse_as(self.language, source, "source")?;
        let core = self.core().ok_or(GrammarError::Empty)?;
        let mut out = Vec::new();
        let mut stack = vec![target.root()];
        while let Some(n) = stack.pop() {
            let mut cur = n.walk();
            stack.extend(n.children(&mut cur));
            if n.kind() == core.kind() {
                let mut b = Bindings::new();
                if self.node_matches(core, n, source, &mut b) {
                    out.push(Match {
                        range: n.start_byte()..n.end_byte(),
                        bindings: b,
                    });
                }
            }
        }
        out.sort_by_key(|m| (m.range.start, m.range.end));
        tracing::debug!(matches = out.len(), "pattern searched");
        Ok(out)
    }

    /// The pattern's core node: the root, or the wrapper function's body, minus wrappers.
    fn core(&self) -> Option<Node<'_>> {
        let mut start = self.tree.root();
        if self.wrapped {
            start = start.child(0)?.child_by_field_name("body")?;
        }
        core_node(start, &self.tree.text)
    }

    fn pat_text(&self, n: Node<'_>) -> &str {
        &self.tree.text[n.start_byte()..n.end_byte()]
    }

    /// Whether pattern node `p` matches target node `t`, extending `b`.
    fn node_matches(&self, p: Node<'_>, t: Node<'_>, src: &str, b: &mut Bindings) -> bool {
        if p.child_count() == 0 {
            if let Some((false, name)) = marker(self.pat_text(p)) {
                return bind(b, name, &src[t.start_byte()..t.end_byte()]);
            }
            return p.kind() == t.kind() && self.pat_text(p) == &src[t.start_byte()..t.end_byte()];
        }
        if p.kind() != t.kind() {
            return false;
        }
        let ps = parts(p);
        let ts = parts(t);
        self.seq_matches(&ps, &ts, src, b)
    }

    fn seq_matches(&self, ps: &[Node<'_>], ts: &[Node<'_>], src: &str, b: &mut Bindings) -> bool {
        let Some((&p, prest)) = ps.split_first() else {
            return ts.is_empty();
        };
        if p.child_count() == 0
            && let Some((true, name)) = marker(self.pat_text(p))
        {
            for k in 0..=ts.len() {
                let mut trial = b.clone();
                let text = match (ts.first(), k.checked_sub(1).and_then(|i| ts.get(i))) {
                    (Some(f), Some(l)) if k > 0 => &src[f.start_byte()..l.end_byte()],
                    _ => "",
                };
                if bind(&mut trial, name, text)
                    && self.seq_matches(prest, &ts[k..], src, &mut trial)
                {
                    *b = trial;
                    return true;
                }
            }
            return false;
        }
        let Some((&t, trest)) = ts.split_first() else {
            return false;
        };
        let mut trial = b.clone();
        if self.node_matches(p, t, src, &mut trial)
            && self.seq_matches(prest, trest, src, &mut trial)
        {
            *b = trial;
            return true;
        }
        false
    }
}

/// Bind `name` to `text`; a repeated name must capture identical text.
fn bind(b: &mut Bindings, name: &str, text: &str) -> bool {
    if let Some(prev) = b.get(name) {
        prev == text
    } else {
        b.insert(name.to_owned(), text.to_owned());
        true
    }
}

/// A node's children, minus separators that carry no meaning.
fn parts(n: Node<'_>) -> Vec<Node<'_>> {
    let mut cur = n.walk();
    n.children(&mut cur)
        .filter(|c| c.kind() != "," || c.is_named())
        .collect()
}

/// Descend through wrappers (module, expression statement) that span exactly their only child.
fn core_node<'a>(root: Node<'a>, text: &str) -> Option<Node<'a>> {
    let mut n = root;
    loop {
        let mut cur = n.walk();
        let kids: Vec<_> = n.named_children(&mut cur).collect();
        match kids.as_slice() {
            [only]
                if n.id() == root.id()
                    || (only.start_byte() == n.start_byte()
                        && matches!(text[only.end_byte()..n.end_byte()].trim(), "" | ";")) =>
            {
                n = *only;
            }
            [] if n.id() == root.id() => return None,
            _ => return Some(n),
        }
    }
}

// frob:ticket 01M4PQ6C6RQWFSHHS3EPKVAH8E
/// One node of a snippet's parse tree, as shown to a rule author.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TreeNode {
    /// Nesting depth below the root (the root is 0).
    pub depth: usize,
    /// The grammar's name for the node, `hole` for a metavariable, or `ERROR`.
    pub kind: String,
    /// The source text of a leaf (a metavariable as the author wrote it); `None` for inner nodes.
    pub text: Option<String>,
}

/// How a snippet reads in its language: whether it parses and the tree the parser got.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Inspection {
    /// The snippet parsed with no error node (possibly inside a function wrapper).
    pub parses: bool,
    /// The tree in preorder; named nodes, errors and the leaves under an error.
    pub tree: Vec<TreeNode>,
}

/// Show a marker identifier as the metavariable the author wrote (`$X`, `$$$ARGS`, `$$$`).
fn hole_text(multi: bool, name: &str) -> String {
    let dollars = if multi { "$$$" } else { "$" };
    if name == "_" && multi {
        dollars.to_owned()
    } else {
        format!("{dollars}{name}")
    }
}

/// Write bare `$$$` as `$$$_` so it becomes a marker like the named forms.
fn name_anonymous(pattern: &str) -> String {
    let b = pattern.as_bytes();
    let mut out = String::with_capacity(pattern.len() + 4);
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'$' {
            let dollars = b[i..].iter().take_while(|&&c| c == b'$').count();
            out.push_str(&pattern[i..i + dollars]);
            if dollars == 3 && ident_len(&b[i + dollars..]) == 0 {
                out.push('_');
            }
            i += dollars;
            continue;
        }
        let ch = pattern[i..].chars().next().unwrap_or(' ');
        out.push(ch);
        i += ch.len_utf8();
    }
    out
}

/// Append `node` and the shown part of its subtree to `out` in preorder.
fn collect_tree(node: Node<'_>, depth: usize, text: &str, out: &mut Vec<TreeNode>) {
    collect_under(node, depth, text, false, out);
}

/// [`collect_tree`] with `in_error` set when an ancestor is an error node, where tokens show too.
fn collect_under(
    node: Node<'_>,
    depth: usize,
    text: &str,
    in_error: bool,
    out: &mut Vec<TreeNode>,
) {
    let leaf = node.child_count() == 0;
    let raw = &text[node.start_byte()..node.end_byte()];
    let hole = leaf.then(|| marker(raw)).flatten();
    let shown = node.is_named() || node.is_error() || node.is_missing() || in_error;
    if shown {
        let kind = match (hole.is_some(), node.is_named() || node.is_error()) {
            (true, _) => "hole".to_owned(),
            (false, true) => node.kind().to_owned(),
            (false, false) => "token".to_owned(),
        };
        out.push(TreeNode {
            depth,
            kind,
            text: match hole {
                Some((multi, name)) => Some(hole_text(multi, name)),
                None => leaf.then(|| raw.to_owned()),
            },
        });
    }
    let mut cur = node.walk();
    for c in node.children(&mut cur) {
        // Anonymous tokens are noise except under an error, where they are what the parser saw.
        if c.is_named() || in_error || node.is_error() || c.is_error() || c.is_missing() {
            collect_under(
                c,
                depth + usize::from(shown),
                text,
                in_error || node.is_error(),
                out,
            );
        }
    }
}

/// Parse `snippet` in `language` the way [`Pattern::compile`] does and report how it read.
///
/// # Errors
///
/// [`GrammarError::UnknownLanguage`] for a language tag the engine does not know, and
/// [`GrammarError::Parse`] when the parser gave up on the text altogether.
pub fn inspect(language: &str, snippet: &str) -> Result<Inspection, GrammarError> {
    let lang = language_by_name(language)?;
    let rewritten = rewrite(&name_anonymous(snippet.trim()));
    let bare = parse_as(lang, &rewritten, "pattern")?;
    let (tree, wrapped) = if bare.has_errors() && lang == Language::Rust {
        let wrapped = parse_as(lang, &format!("fn __gob() {{\n{rewritten}\n}}"), "pattern")?;
        if wrapped.has_errors() {
            (bare, false)
        } else {
            (wrapped, true)
        }
    } else {
        (bare, false)
    };
    let parses = !tree.has_errors();
    let pat = Pattern {
        language: lang,
        tree,
        wrapped,
    };
    let mut nodes = Vec::new();
    match pat.core() {
        Some(core) if parses => collect_tree(core, 0, &pat.tree.text, &mut nodes),
        _ => collect_tree(pat.tree.root(), 0, &pat.tree.text, &mut nodes),
    }
    tracing::debug!(language, parses, nodes = nodes.len(), "snippet inspected");
    Ok(Inspection {
        parses,
        tree: nodes,
    })
}

/// Render a fix template: `$$$NAME` and `$NAME` become the captured text.
///
/// # Errors
///
/// [`GrammarError::UnboundInFix`] when the template names a metavariable with no binding.
pub fn render(template: &str, bindings: &Bindings) -> Result<String, GrammarError> {
    let b = template.as_bytes();
    let mut out = String::with_capacity(template.len());
    let mut i = 0;
    while i < b.len() {
        if b[i] == b'$' {
            let dollars = b[i..].iter().take_while(|&&c| c == b'$').count();
            let name = ident_len(&b[i + dollars..]);
            if (dollars == 1 || dollars == 3) && name > 0 {
                let key = &template[i + dollars..i + dollars + name];
                let text = bindings
                    .get(key)
                    .ok_or_else(|| GrammarError::UnboundInFix(key.to_owned()))?;
                out.push_str(text);
                i += dollars + name;
                continue;
            }
        }
        let ch = template[i..].chars().next().unwrap_or(' ');
        out.push(ch);
        i += ch.len_utf8();
    }
    Ok(out)
}

/// Apply non-overlapping `edits` to `source`; overlapping later edits are skipped.
pub fn apply(source: &str, edits: &[Edit]) -> String {
    let mut sorted: Vec<&Edit> = edits.iter().collect();
    sorted.sort_by_key(|e| e.range.start);
    let mut out = String::with_capacity(source.len());
    let mut at = 0;
    for e in sorted {
        if e.range.start < at {
            tracing::debug!(start = e.range.start, "overlapping edit skipped");
            continue;
        }
        out.push_str(&source[at..e.range.start]);
        out.push_str(&e.text);
        at = e.range.end;
    }
    out.push_str(&source[at..]);
    out
}

#[cfg(test)]
mod inspect_tests {
    use super::*;

    // frob:ticket 01M4PQ6C6RQWFSHHS3EPKVAH8E
    // frob:tests crates/gob-pattern/src/grammar.rs::inspect
    #[test]
    fn a_snippet_that_does_not_parse_shows_the_tree_it_got() {
        let i = inspect("python", "except: $$$").unwrap();
        assert!(!i.parses);
        let kinds: Vec<_> = i.tree.iter().map(|n| (n.depth, n.kind.as_str())).collect();
        assert_eq!(
            kinds,
            [
                (0, "module"),
                (1, "ERROR"),
                (2, "token"),
                (2, "token"),
                (1, "expression_statement"),
                (2, "hole")
            ]
        );
        assert_eq!(i.tree[5].text.as_deref(), Some("$$$"));
    }

    // frob:ticket 01M4PQ6C6RQWFSHHS3EPKVAH8E
    // frob:tests crates/gob-pattern/src/grammar.rs::inspect
    #[test]
    fn a_snippet_that_parses_lists_its_nodes_and_an_unknown_language_errors() {
        let i = inspect("rust", "unsafe { $$$BODY }").unwrap();
        assert!(i.parses);
        assert!(i.tree.iter().any(|n| n.kind == "unsafe_block"));
        assert!(matches!(
            inspect("klingon", "x"),
            Err(GrammarError::UnknownLanguage(_))
        ));
    }
}
