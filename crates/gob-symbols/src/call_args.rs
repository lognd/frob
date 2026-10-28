//! Statically known call arguments of Rust and Python call sites.
//!
//! The capability rules (`grimble-bind` CAP001) judge a use against the `may` grant arguments
//! of its atom, so they need the argument a call passes when the source states it. [`call_args`]
//! parses one file and returns, per call, each argument it can fold to a value: a string
//! literal, an f-string or format without interpolation, a `+` concatenation of literals, a
//! tuple, list or array of those, a path or string conversion wrapped around one, and a name
//! bound exactly once to such a value (a Rust `const` / `static`, a Python module-level
//! assignment no other statement rebinds). Everything else is `None`: the caller must treat an
//! argument it cannot fold as unknown, never as a pass.

// frob:ticket 01M5XNNH61Z437EDDB05X9CAQE

use std::collections::BTreeMap;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use tree_sitter::Node;

/// Deepest chain of constants and wrappers followed while folding one argument.
const MAX_DEPTH: usize = 8;

/// The folded value of one call argument.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ArgValue {
    /// A string known in full.
    Str(String),
    /// A tuple, list or array; an element that does not fold is `None`. Integers are kept as
    /// their decimal text so a `("host", 443)` pair reads as `["host", "443"]`.
    Seq(Vec<Option<String>>),
}

/// One call with the arguments the source states.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CallArgs {
    /// Byte offset of the call in the file.
    pub offset: usize,
    /// One-based line of the call.
    pub line: u32,
    /// The callee as written (`os.getenv`, `std::fs::read`, `sock.connect`).
    pub callee: String,
    /// Positional arguments in order; `None` when one does not fold (or is a splat).
    pub args: Vec<Option<ArgValue>>,
    /// Keyword arguments (Python) by name.
    pub kwargs: BTreeMap<String, Option<ArgValue>>,
}

fn text<'a>(src: &'a str, n: Node<'_>) -> &'a str {
    &src[n.start_byte()..n.end_byte()]
}

fn line(n: Node<'_>) -> u32 {
    u32::try_from(n.start_position().row + 1).unwrap_or(u32::MAX)
}

/// Every call in `source` with its foldable arguments, in source order. `language` is the
/// adapter tag (`rust` or `python`); other languages and unparsable files give nothing.
pub fn call_args(language: &str, source: &str) -> Vec<CallArgs> {
    let lang = match language {
        "rust" => Language::Rust,
        "python" => Language::Python,
        _ => return Vec::new(),
    };
    let ParseResult::Parsed(tree) = parse(lang, source, &ParseLimits::default()) else {
        tracing::debug!(language, "call_args: file not parsed");
        return Vec::new();
    };
    let src: &str = &tree.text;
    let python = lang == Language::Python;
    let consts = collect_consts(src, tree.root(), python);
    let cx = Cx {
        src,
        consts,
        python,
    };
    let mut out = Vec::new();
    let mut stack = vec![tree.root()];
    while let Some(n) = stack.pop() {
        let mut c = n.walk();
        for ch in n.children(&mut c) {
            stack.push(ch);
        }
        let is_call = if python {
            n.kind() == "call"
        } else {
            n.kind() == "call_expression"
        };
        if !is_call {
            continue;
        }
        let (Some(f), Some(a)) = (
            n.child_by_field_name("function"),
            n.child_by_field_name("arguments"),
        ) else {
            continue;
        };
        out.push(cx.call(n, f, a));
    }
    out.sort_by_key(|c| c.offset);
    tracing::debug!(language, calls = out.len(), "call_args: scanned");
    out
}

struct Cx<'a> {
    src: &'a str,
    /// Foldable constants by name: `None` for a name bound more than once (ambiguous).
    consts: BTreeMap<String, Option<usize>>,
    python: bool,
}

/// `(start, end)` byte ranges are not storable beside the tree, so constants keep the byte
/// offset of their value node and are re-found by `value_at`.
fn collect_consts(src: &str, root: Node<'_>, python: bool) -> BTreeMap<String, Option<usize>> {
    let mut found: BTreeMap<String, Vec<usize>> = BTreeMap::new();
    let mut binds: BTreeMap<String, usize> = BTreeMap::new();
    let mut stack = vec![root];
    while let Some(n) = stack.pop() {
        let mut c = n.walk();
        for ch in n.children(&mut c) {
            stack.push(ch);
        }
        if python {
            if n.kind() == "identifier" && is_python_binding(n) {
                *binds.entry(text(src, n).to_owned()).or_default() += 1;
            }
            if n.kind() == "assignment"
                && n.parent().is_some_and(|p| {
                    p.kind() == "expression_statement"
                        && p.parent().is_some_and(|g| g.kind() == "module")
                })
                && let (Some(l), Some(r)) = (
                    n.child_by_field_name("left"),
                    n.child_by_field_name("right"),
                )
                && l.kind() == "identifier"
            {
                found
                    .entry(text(src, l).to_owned())
                    .or_default()
                    .push(r.start_byte());
            }
        } else if matches!(n.kind(), "const_item" | "static_item") {
            let mutable = {
                let mut cc = n.walk();
                n.children(&mut cc).any(|k| k.kind() == "mutable_specifier")
            };
            if let (Some(name), Some(v)) = (
                n.child_by_field_name("name"),
                n.child_by_field_name("value"),
            ) {
                let e = found.entry(text(src, name).to_owned()).or_default();
                if mutable {
                    e.push(usize::MAX);
                    e.push(usize::MAX);
                } else {
                    e.push(v.start_byte());
                }
            }
        }
    }
    found
        .into_iter()
        .map(|(name, at)| {
            let unique = at.len() == 1 && (!python || binds.get(&name) == Some(&1));
            let v = if unique { Some(at[0]) } else { None };
            (name, v)
        })
        .collect()
}

/// True when this identifier node introduces or rebinds a name (an over-approximation: a miss
/// would let a shadowed constant fold, an extra hit only leaves one unfolded).
fn is_python_binding(n: Node<'_>) -> bool {
    let Some(p) = n.parent() else { return false };
    match p.kind() {
        "parameters"
        | "lambda_parameters"
        | "typed_parameter"
        | "pattern_list"
        | "tuple_pattern"
        | "list_pattern"
        | "as_pattern_target"
        | "global_statement"
        | "nonlocal_statement"
        | "dotted_name"
        | "aliased_import"
        | "list_splat_pattern"
        | "dictionary_splat_pattern" => true,
        "default_parameter"
        | "typed_default_parameter"
        | "function_definition"
        | "class_definition"
        | "named_expression" => p.child_by_field_name("name") == Some(n),
        "assignment" | "augmented_assignment" | "for_statement" | "for_in_clause" => {
            p.child_by_field_name("left") == Some(n)
        }
        _ => false,
    }
}

impl Cx<'_> {
    fn call(&self, call: Node<'_>, f: Node<'_>, args: Node<'_>) -> CallArgs {
        let mut positional = Vec::new();
        let mut kwargs = BTreeMap::new();
        let mut c = args.walk();
        for a in args.named_children(&mut c) {
            match a.kind() {
                "comment" => {}
                "keyword_argument" => {
                    let name = a
                        .child_by_field_name("name")
                        .map(|n| text(self.src, n).to_owned())
                        .unwrap_or_default();
                    let v = a.child_by_field_name("value").and_then(|v| self.eval(v, 0));
                    kwargs.insert(name, v);
                }
                "list_splat" | "dictionary_splat" => positional.push(None),
                _ => positional.push(self.eval(a, 0)),
            }
        }
        CallArgs {
            offset: call.start_byte(),
            line: line(call),
            callee: text(self.src, f).to_owned(),
            args: positional,
            kwargs,
        }
    }

    fn eval_str(&self, n: Node<'_>, depth: usize) -> Option<String> {
        match self.eval(n, depth)? {
            ArgValue::Str(s) => Some(s),
            ArgValue::Seq(_) => None,
        }
    }

    fn eval(&self, n: Node<'_>, depth: usize) -> Option<ArgValue> {
        if depth > MAX_DEPTH {
            return None;
        }
        let d = depth + 1;
        if self.python {
            self.eval_python(n, d)
        } else {
            self.eval_rust(n, d)
        }
    }

    fn constant(&self, name: &str, depth: usize, root: Node<'_>) -> Option<ArgValue> {
        let at = (*self.consts.get(name)?)?;
        let mut node = root.descendant_for_byte_range(at, at)?;
        // widen to the whole value expression that starts at `at`
        while let Some(p) = node.parent() {
            if p.start_byte() == at && p.end_byte() > node.end_byte() && p.kind() != "module" {
                match p.kind() {
                    "assignment"
                    | "const_item"
                    | "static_item"
                    | "expression_statement"
                    | "source_file" => break,
                    _ => node = p,
                }
            } else {
                break;
            }
        }
        self.eval(node, depth)
    }

    fn eval_python(&self, n: Node<'_>, d: usize) -> Option<ArgValue> {
        match n.kind() {
            "string" => py_string(self.src, n).map(ArgValue::Str),
            "concatenated_string" => {
                let mut s = String::new();
                let mut c = n.walk();
                for part in n.named_children(&mut c) {
                    s.push_str(&py_string(self.src, part)?);
                }
                Some(ArgValue::Str(s))
            }
            "parenthesized_expression" => self.eval(n.named_child(0)?, d),
            "integer" => Some(ArgValue::Str(text(self.src, n).to_owned())),
            "identifier" => self.constant(text(self.src, n), d, root_of(n)),
            "binary_operator" => {
                let op = n.child_by_field_name("operator")?;
                if text(self.src, op) != "+" {
                    return None;
                }
                let l = self.eval_str(n.child_by_field_name("left")?, d)?;
                let r = self.eval_str(n.child_by_field_name("right")?, d)?;
                Some(ArgValue::Str(l + &r))
            }
            "tuple" | "list" => Some(ArgValue::Seq(self.elements(n, d))),
            "call" => {
                let f = text(self.src, n.child_by_field_name("function")?);
                let args = n.child_by_field_name("arguments")?;
                let mut cursor = args.walk();
                let parts: Vec<Node<'_>> = args.named_children(&mut cursor).collect();
                match f {
                    "Path" | "PurePath" | "PosixPath" | "pathlib.Path" | "pathlib.PurePath"
                    | "str" | "os.fspath" | "os.path.normpath" | "bytes.decode" => {
                        if parts.len() == 1 {
                            self.eval(parts[0], d)
                        } else {
                            None
                        }
                    }
                    "os.path.join" | "posixpath.join" => {
                        let mut out = String::new();
                        for (i, part) in parts.iter().enumerate() {
                            let s = self.eval_str(*part, d)?;
                            if i > 0 {
                                // an absolute later part would discard the earlier ones
                                if s.starts_with('/') {
                                    return None;
                                }
                                if !out.ends_with('/') {
                                    out.push('/');
                                }
                            }
                            out.push_str(&s);
                        }
                        Some(ArgValue::Str(out))
                    }
                    _ => None,
                }
            }
            _ => None,
        }
    }

    fn eval_rust(&self, n: Node<'_>, d: usize) -> Option<ArgValue> {
        match n.kind() {
            "string_literal" => rust_string(self.src, n).map(ArgValue::Str),
            "raw_string_literal" => {
                let t = text(self.src, n).strip_prefix('r')?;
                let hashes = t.chars().take_while(|c| *c == '#').count();
                let body = t.get(hashes + 1..t.len().checked_sub(hashes + 1)?)?;
                Some(ArgValue::Str(body.to_owned()))
            }
            "integer_literal" => {
                let t = text(self.src, n);
                let digits: String = t.chars().take_while(char::is_ascii_digit).collect();
                (!digits.is_empty() && digits.len() == t.len().min(digits.len()))
                    .then_some(ArgValue::Str(digits))
            }
            "parenthesized_expression" | "reference_expression" => self.eval(
                n.child_by_field_name("value")
                    .or_else(|| n.named_child(0))?,
                d,
            ),
            "identifier" | "scoped_identifier" => {
                let t = text(self.src, n);
                let name = t.rsplit("::").next().unwrap_or(t);
                self.constant(name, d, root_of(n))
            }
            "tuple_expression" | "array_expression" => Some(ArgValue::Seq(self.elements(n, d))),
            "call_expression" => {
                let f = n.child_by_field_name("function")?;
                let ft = text(self.src, f);
                let args = n.child_by_field_name("arguments")?;
                let mut cursor = args.walk();
                let parts: Vec<Node<'_>> = args.named_children(&mut cursor).collect();
                let wrapper = [
                    "Path::new",
                    "PathBuf::from",
                    "String::from",
                    "OsString::from",
                    "OsStr::new",
                    "Cow::Borrowed",
                    "Some",
                ]
                .iter()
                .any(|w| ft == *w || ft.ends_with(&format!("::{w}")));
                if wrapper && parts.len() == 1 {
                    return self.eval(parts[0], d);
                }
                // `x.as_str()`, `x.to_string()` and friends keep the value
                if f.kind() == "field_expression"
                    && parts.is_empty()
                    && f.child_by_field_name("field").is_some_and(|m| {
                        matches!(
                            text(self.src, m),
                            "as_str" | "to_string" | "to_owned" | "into" | "as_ref" | "as_path"
                        )
                    })
                {
                    return self.eval(f.child_by_field_name("value")?, d);
                }
                None
            }
            _ => None,
        }
    }

    fn elements(&self, n: Node<'_>, d: usize) -> Vec<Option<String>> {
        let mut c = n.walk();
        n.named_children(&mut c)
            .filter(|k| k.kind() != "comment")
            .map(|k| self.eval_str(k, d))
            .collect()
    }
}

fn root_of(n: Node<'_>) -> Node<'_> {
    let mut cur = n;
    while let Some(p) = cur.parent() {
        cur = p;
    }
    cur
}

/// The contents of a Python `string` node, or `None` for bytes, an f-string with interpolation
/// or any escape sequence.
fn py_string(src: &str, n: Node<'_>) -> Option<String> {
    if n.kind() != "string" {
        return None;
    }
    let mut out = String::new();
    let mut c = n.walk();
    for ch in n.children(&mut c) {
        match ch.kind() {
            "string_start" => {
                let prefix = text(src, ch).to_ascii_lowercase();
                if prefix.contains('b') {
                    return None;
                }
            }
            "string_content" => out.push_str(text(src, ch)),
            "string_end" => {}
            _ => return None,
        }
    }
    (!out.contains('\\')).then_some(out)
}

/// The contents of a Rust `string_literal`, or `None` when it holds an escape.
fn rust_string(src: &str, n: Node<'_>) -> Option<String> {
    let t = text(src, n);
    let body = t.strip_prefix('"')?.strip_suffix('"')?;
    (!body.contains('\\')).then(|| body.to_owned())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn first(lang: &str, src: &str, callee: &str) -> CallArgs {
        call_args(lang, src)
            .into_iter()
            .find(|c| c.callee == callee)
            .unwrap_or_else(|| panic!("no call {callee}"))
    }

    #[allow(clippy::unnecessary_wraps)] // the expected vectors mix Some and None
    fn s(v: &str) -> Option<ArgValue> {
        Some(ArgValue::Str(v.to_owned()))
    }

    // frob:tests crates/gob-symbols/src/call_args.rs::call_args
    #[test]
    fn python_literals_constants_and_tuples_fold() {
        let src = "import os, socket\nBASE = 'config'\nHOST = 'a.com'\nopen('x.txt')\nos.getenv('HOME')\nopen(BASE + '/app.toml')\nsocket.create_connection((HOST, 443))\nopen(os.path.join(BASE, 'k'))\nopen(f'{BASE}/x')\nopen(name)\n";
        assert_eq!(first("python", src, "os.getenv").args, vec![s("HOME")]);
        assert_eq!(
            call_args("python", src)
                .into_iter()
                .filter(|c| c.callee == "open")
                .map(|c| c.args[0].clone())
                .collect::<Vec<_>>(),
            vec![s("x.txt"), s("config/app.toml"), s("config/k"), None, None]
        );
        assert_eq!(
            first("python", src, "socket.create_connection").args,
            vec![Some(ArgValue::Seq(vec![
                Some("a.com".into()),
                Some("443".into())
            ]))]
        );
    }

    // frob:tests crates/gob-symbols/src/call_args.rs::call_args
    #[test]
    fn python_rebound_constants_do_not_fold() {
        let src = "P = 'a'\ndef f(P):\n    open(P)\nQ = 'a'\nQ = 'b'\nopen(Q)\nR = 'r'\ndef g():\n    global R\n    R = input()\nopen(R)\n";
        let got: Vec<_> = call_args("python", src)
            .into_iter()
            .filter(|c| c.callee == "open")
            .map(|c| c.args[0].clone())
            .collect();
        assert_eq!(got, vec![None, None, None]);
    }

    // frob:tests crates/gob-symbols/src/call_args.rs::call_args
    #[test]
    fn python_keyword_and_splat_arguments_are_recorded() {
        let src = "open(file='x', mode='r')\nrun(*a)\n";
        assert_eq!(first("python", src, "open").kwargs["file"], s("x"));
        assert_eq!(first("python", src, "run").args, vec![None]);
    }

    // frob:tests crates/gob-symbols/src/call_args.rs::call_args
    #[test]
    fn rust_literals_consts_and_wrappers_fold() {
        let src = "const DIR: &str = \"config\";\nfn f() {\n  std::fs::read(\"a.txt\");\n  std::fs::read(Path::new(DIR));\n  std::env::var(\"HOME\");\n  TcpStream::connect((\"h.com\", 80));\n  Command::new(\"git\");\n  std::fs::read(&name);\n  std::fs::read(\"a\\\\b\");\n  std::fs::read(DIR.to_string());\n}\n";
        let reads: Vec<_> = call_args("rust", src)
            .into_iter()
            .filter(|c| c.callee == "std::fs::read")
            .map(|c| c.args[0].clone())
            .collect();
        assert_eq!(
            reads,
            vec![s("a.txt"), s("config"), None, None, s("config")]
        );
        assert_eq!(first("rust", src, "std::env::var").args, vec![s("HOME")]);
        assert_eq!(first("rust", src, "Command::new").args, vec![s("git")]);
        assert_eq!(
            first("rust", src, "TcpStream::connect").args,
            vec![Some(ArgValue::Seq(vec![
                Some("h.com".into()),
                Some("80".into())
            ]))]
        );
    }

    // frob:tests crates/gob-symbols/src/call_args.rs::call_args
    #[test]
    fn rust_duplicate_and_mutable_statics_do_not_fold() {
        let src = "mod a { const X: &str = \"1\"; }\nmod b { const X: &str = \"2\"; }\nstatic mut M: &str = \"m\";\nfn f() { g(X); g(M); }\n";
        let got: Vec<_> = call_args("rust", src)
            .into_iter()
            .filter(|c| c.callee == "g")
            .map(|c| c.args[0].clone())
            .collect();
        assert_eq!(got, vec![None, None]);
    }

    // frob:tests crates/gob-symbols/src/call_args.rs::call_args
    #[test]
    fn other_languages_give_nothing() {
        assert!(call_args("go", "f(1)").is_empty());
    }
}
