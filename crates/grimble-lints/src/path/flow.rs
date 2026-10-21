//! `PATH002` and `PATH003`: a path turned into a string, then handled as text.
//!
//! One pass per function (or the module for Python scripts) follows def-use by name: a binding
//! whose value comes from a path-conversion callee is tainted, and a sink that mixes a tainted
//! value with a literal separator (`PATH002`) or builds a command-line string from one
//! (`PATH003`) is a site. Roles come from the per-language tables below; a language without
//! them is Unresolved in the caller, never clean.

// frob:ticket 01M41RV691XZQ5W2EW821PHK3V

use std::collections::BTreeSet;

use tree_sitter::Node;

use super::Kind;
use super::literal::{decode, is_string_literal};
use crate::syntax::{children, idents, text};

pub(super) use crate::syntax::Lang;

/// A sink before it is bound to a range and test context.
#[derive(Debug, Clone, Copy)]
pub(super) struct Raw<'t> {
    pub kind: Kind,
    pub node: Node<'t>,
}

/// Rust methods that turn a path into text.
const RUST_CONVERT: &[&str] = &["to_str", "to_string_lossy", "display", "as_os_str"];
/// Methods that split, trim, search or join text by a separator argument.
const SEP_METHODS: &[&str] = &[
    "split",
    "rsplit",
    "splitn",
    "rsplitn",
    "split_once",
    "rsplit_once",
    "split_terminator",
    "trim_start_matches",
    "trim_end_matches",
    "trim_matches",
    "strip_prefix",
    "strip_suffix",
    "starts_with",
    "ends_with",
    "contains",
    "find",
    "rfind",
    "replace",
    "matches",
    "join",
    "partition",
    "rpartition",
    "startswith",
    "endswith",
    "strip",
    "lstrip",
    "rstrip",
    "index",
    "count",
];
/// Name fragments that make a Python identifier a path by convention.
const PY_PATHY: &[&str] = &["path", "dir", "cwd", "root", "folder"];
/// Python callees that run a command line.
const PY_COMMANDS: &[&str] = &[
    "os.system",
    "os.popen",
    "Popen",
    "check_output",
    "check_call",
];
/// First words that make a string a command line by itself.
const SHELL_WORDS: &[&str] = &[
    "git",
    "sh",
    "bash",
    "zsh",
    "cmd",
    "powershell",
    "pwsh",
    "cargo",
    "python",
    "python3",
    "node",
    "npm",
];

fn is_function(lang: Lang, n: Node<'_>) -> bool {
    match lang {
        Lang::Rust => n.kind() == "function_item",
        Lang::Python => n.kind() == "function_definition",
    }
}

/// Every site in `root`, one scope at a time.
pub(super) fn scan<'t>(lang: Lang, root: Node<'t>, src: &str) -> Vec<Raw<'t>> {
    let mut scopes = vec![root];
    let mut stack = vec![root];
    while let Some(n) = stack.pop() {
        for c in children(n) {
            if is_function(lang, c) {
                scopes.push(c);
            }
            stack.push(c);
        }
    }
    let mut out = Vec::new();
    for scope in scopes {
        let mut f = Flow {
            lang,
            src,
            scope,
            taint: BTreeSet::new(),
            pathy: BTreeSet::new(),
            out: Vec::new(),
        };
        f.visit(scope);
        tracing::trace!(kind = scope.kind(), sites = f.out.len(), "path flow scope");
        out.extend(f.out);
    }
    out
}

struct Flow<'t, 's> {
    lang: Lang,
    src: &'s str,
    scope: Node<'t>,
    taint: BTreeSet<String>,
    pathy: BTreeSet<String>,
    out: Vec<Raw<'t>>,
}

impl<'t> Flow<'t, '_> {
    fn visit(&mut self, node: Node<'t>) {
        if node != self.scope && is_function(self.lang, node) {
            return;
        }
        self.at(node);
        for c in children(node) {
            self.visit(c);
        }
    }

    fn flag(&mut self, kind: Kind, node: Node<'t>) {
        self.out.push(Raw { kind, node });
    }

    fn at(&mut self, node: Node<'t>) {
        match (self.lang, node.kind()) {
            (Lang::Rust, "let_declaration") => self.bind(node, "pattern", "value"),
            (Lang::Python, "assignment") => self.bind(node, "left", "right"),
            (Lang::Python, "typed_parameter" | "typed_default_parameter") => self.param(node),
            (Lang::Rust, "call_expression") | (Lang::Python, "call") => self.method_sink(node),
            (Lang::Rust, "binary_expression") | (Lang::Python, "binary_operator") => {
                self.concat_or_compare(node);
            }
            (Lang::Python, "comparison_operator") => self.compare_all(node),
            (Lang::Rust, "macro_invocation") => self.format_macro(node),
            (Lang::Python, "string") => self.fstring(node),
            _ => {}
        }
    }

    /// Record the names bound by `pattern = value` when the value is a string made from a path.
    fn bind(&mut self, node: Node<'t>, pat: &str, val: &str) {
        let (Some(p), Some(v)) = (node.child_by_field_name(pat), node.child_by_field_name(val))
        else {
            return;
        };
        let mut names = Vec::new();
        idents(p, self.src, &mut names);
        if self.tainted(v) {
            tracing::trace!(?names, "path-derived string bound");
            self.taint.extend(names.iter().cloned());
        }
        if self.lang == Lang::Python && text(v, self.src).starts_with("Path(") {
            self.pathy.extend(names);
        }
    }

    fn param(&mut self, node: Node<'t>) {
        let ty = node
            .child_by_field_name("type")
            .map_or("", |t| text(t, self.src));
        if matches!(ty, "Path" | "PurePath" | "pathlib.Path") {
            let mut names = Vec::new();
            idents(node, self.src, &mut names);
            if let Some(first) = names.first() {
                self.pathy.insert(first.clone());
            }
        }
    }

    fn is_pathy(&self, expr: Node<'_>) -> bool {
        let t = text(expr, self.src);
        if self.pathy.contains(t) || t.starts_with("Path(") {
            return true;
        }
        let last = t.rsplit('.').next().unwrap_or(t).to_ascii_lowercase();
        PY_PATHY.iter().any(|m| last.contains(m))
    }

    fn tainted(&self, node: Node<'_>) -> bool {
        let hit = match (self.lang, node.kind()) {
            (Lang::Rust, "field_identifier") => RUST_CONVERT.contains(&text(node, self.src)),
            (Lang::Rust, "identifier") => {
                let t = text(node, self.src);
                let after_dot = node.prev_sibling().is_some_and(|p| p.kind() == ".");
                (after_dot && RUST_CONVERT.contains(&t)) || (!after_dot && self.taint.contains(t))
            }
            (Lang::Python, "identifier") => self.taint.contains(text(node, self.src)),
            (Lang::Python, "interpolation") => node
                .child_by_field_name("expression")
                .is_some_and(|e| self.is_pathy(e)),
            (Lang::Python, "call") => self.py_conversion(node),
            _ => false,
        };
        hit || children(node).into_iter().any(|c| self.tainted(c))
    }

    fn py_conversion(&self, call: Node<'_>) -> bool {
        let Some(f) = call.child_by_field_name("function") else {
            return false;
        };
        match text(f, self.src) {
            "os.fspath" | "fspath" => true,
            "str" => call
                .child_by_field_name("arguments")
                .and_then(|a| a.named_child(0))
                .is_some_and(|a| self.is_pathy(a)),
            _ => false,
        }
    }

    /// True when a literal in the subtree contains `/` or `\`.
    fn has_sep_literal(&self, node: Node<'_>) -> bool {
        if self.is_literal(node) {
            return decode(text(node, self.src)).is_some_and(|v| v.contains(['/', '\\']));
        }
        children(node).into_iter().any(|c| self.has_sep_literal(c))
    }

    fn is_literal(&self, node: Node<'_>) -> bool {
        node.kind() == "char_literal"
            || (self.lang == Lang::Rust && node.kind() == "string_literal")
            || is_string_literal(
                match self.lang {
                    Lang::Rust => gob_languages::Language::Rust,
                    Lang::Python => gob_languages::Language::Python,
                },
                node,
            )
    }

    /// `receiver.method(args)` where the receiver is path text and an argument is a separator.
    fn method_sink(&mut self, call: Node<'t>) {
        let Some(func) = call.child_by_field_name("function") else {
            return;
        };
        let (recv, name) = match (self.lang, func.kind()) {
            (Lang::Rust, "field_expression") => (
                func.child_by_field_name("value"),
                func.child_by_field_name("field"),
            ),
            (Lang::Python, "attribute") => (
                func.child_by_field_name("object"),
                func.child_by_field_name("attribute"),
            ),
            _ => return,
        };
        let (Some(recv), Some(name), Some(args)) =
            (recv, name, call.child_by_field_name("arguments"))
        else {
            return;
        };
        let method = text(name, self.src);
        if !SEP_METHODS.contains(&method) {
            return;
        }
        let fires = if self.lang == Lang::Python && method == "join" {
            self.has_sep_literal(recv) && self.tainted(args)
        } else {
            self.tainted(recv) && self.has_sep_literal(args)
        };
        if fires {
            self.flag(Kind::StringPathSeparator, call);
        }
    }

    fn operator(&self, node: Node<'_>) -> String {
        node.child_by_field_name("operator")
            .map_or_else(String::new, |o| self.src[o.byte_range()].to_owned())
    }

    fn concat_or_compare(&mut self, node: Node<'t>) {
        match self.operator(node).as_str() {
            "+" => {
                if node
                    .parent()
                    .is_some_and(|p| p.kind() == node.kind() && self.operator(p) == "+")
                {
                    return;
                }
                let mut lits = Vec::new();
                self.literal_pieces(node, &mut lits);
                self.classify(node, &lits);
            }
            "==" | "!=" => {
                let (Some(l), Some(r)) = (
                    node.child_by_field_name("left"),
                    node.child_by_field_name("right"),
                ) else {
                    return;
                };
                if (self.tainted(l) && self.has_sep_literal(r))
                    || (self.tainted(r) && self.has_sep_literal(l))
                {
                    self.flag(Kind::StringPathSeparator, node);
                }
            }
            _ => {}
        }
    }

    fn compare_all(&mut self, node: Node<'t>) {
        let ops = children(node);
        let tainted = ops.iter().any(|c| self.tainted(*c));
        let sep = ops
            .iter()
            .any(|c| self.is_literal(*c) && self.has_sep_literal(*c));
        if tainted && sep {
            self.flag(Kind::StringPathSeparator, node);
        }
    }

    /// The decoded value of each string literal directly in the expression tree.
    fn literal_pieces(&self, node: Node<'_>, out: &mut Vec<String>) {
        if self.is_literal(node) && node.kind() != "char_literal" {
            out.extend(decode(text(node, self.src)));
            return;
        }
        for c in children(node) {
            self.literal_pieces(c, out);
        }
    }

    fn format_macro(&mut self, mac: Node<'t>) {
        let name = mac
            .child_by_field_name("macro")
            .map_or("", |m| text(m, self.src));
        if name.rsplit("::").next() != Some("format") {
            return;
        }
        let mut lits = Vec::new();
        self.literal_pieces(mac, &mut lits);
        self.classify(mac, &lits);
    }

    fn fstring(&mut self, node: Node<'t>) {
        let kids = children(node);
        if !kids.iter().any(|c| c.kind() == "interpolation") {
            return;
        }
        let lits: Vec<String> = kids
            .iter()
            .filter(|c| c.kind() == "string_content")
            .map(|c| text(*c, self.src).to_owned())
            .collect();
        self.classify(node, &lits);
    }

    /// Decide between `PATH003` and `PATH002` for a string-building expression.
    fn classify(&mut self, node: Node<'t>, lits: &[String]) {
        if lits.is_empty() || !self.tainted(node) {
            return;
        }
        let joined = lits.concat();
        let trimmed = joined.trim();
        let spaced = trimmed.contains(char::is_whitespace);
        let shell_word = trimmed
            .split_whitespace()
            .next()
            .is_some_and(|w| SHELL_WORDS.contains(&w));
        if spaced && (shell_word || self.command_bound(node)) {
            self.flag(Kind::PathInCommandLine, node);
        } else if joined.contains(['/', '\\']) {
            self.flag(Kind::StringPathSeparator, node);
        }
    }

    fn is_command_call(&self, n: Node<'_>) -> bool {
        let Some(f) = n.child_by_field_name("function") else {
            return false;
        };
        let t = text(f, self.src);
        match (self.lang, n.kind()) {
            (Lang::Rust, "call_expression") => {
                t.ends_with("Command::new")
                    || (f.kind() == "field_expression"
                        && f.child_by_field_name("field")
                            .is_some_and(|m| matches!(text(m, self.src), "arg" | "args" | "env")))
            }
            (Lang::Python, "call") => t.starts_with("subprocess.") || PY_COMMANDS.contains(&t),
            _ => false,
        }
    }

    /// True when the string flows into a command call, directly or through a binding.
    fn command_bound(&self, node: Node<'_>) -> bool {
        let mut cur = node;
        while let Some(p) = cur.parent() {
            if is_function(self.lang, p) {
                break;
            }
            if self.is_command_call(p) {
                return true;
            }
            if matches!(p.kind(), "let_declaration" | "assignment") {
                let pat = p
                    .child_by_field_name("pattern")
                    .or_else(|| p.child_by_field_name("left"));
                let mut names = Vec::new();
                if let Some(pat) = pat {
                    idents(pat, self.src, &mut names);
                }
                return self.name_in_command(self.scope, &names);
            }
            if matches!(p.kind(), "expression_statement" | "block") {
                break;
            }
            cur = p;
        }
        false
    }

    fn name_in_command(&self, node: Node<'_>, names: &[String]) -> bool {
        if self.is_command_call(node) {
            let mut used = Vec::new();
            idents(node, self.src, &mut used);
            if used.iter().any(|u| names.contains(u)) {
                return true;
            }
        }
        children(node)
            .into_iter()
            .any(|c| self.name_in_command(c, names))
    }
}
