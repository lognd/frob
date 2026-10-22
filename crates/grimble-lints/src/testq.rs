//! Test-quality sites: `TESTQ001` to `TESTQ003` (lint catalogue row K20).
//!
//! [`scan`] finds, in the tests of one Rust or Python file, a test with no assertion
//! (`TESTQ001`), a sleep, wall-clock read or unseeded random source in a test body (`TESTQ002`)
//! and control flow in a test body (`TESTQ003`, off by default: [`Kind::default_enabled`]).
//!
//! `TESTQ001` follows same-file helpers and is three-valued: a helper whose body is out of sight
//! (imported from a support module, a `mod x;` file, a mixin base) yields a site with
//! [`Certainty::Unknown`], which the consumer reports as Unresolved rather than as a hit. A
//! language without test roles reports every kind unresolved. Mapping a site to a severity belongs
//! to the rule that consumes it.

// frob:ticket 01M4D957J2HZ655A1H8DJ4K8YD

mod assert;
mod ctx;
mod nondet;

use std::path::Path;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gob_text::TextRange;
use tree_sitter::Node;

use crate::res::Certainty;
use crate::syntax::{Lang, children, text};
use ctx::Ctx;

pub use crate::res::ScanError;

/// Rust attribute names that make a function a test.
const RUST_TEST_ATTRS: &[&str] = &[
    "test",
    "rstest",
    "test_case",
    "wasm_bindgen_test",
    "quickcheck",
];

/// Python base classes that do not hide helpers from a test class.
const CLOSED_BASES: &[&str] = &[
    "TestCase",
    "IsolatedAsyncioTestCase",
    "TransactionTestCase",
    "SimpleTestCase",
    "object",
];

/// Which test-quality shape a site is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Kind {
    /// `TESTQ001`: a test that asserts nothing, directly or through a helper.
    NoAssertion,
    /// `TESTQ002`: a sleep, wall-clock read or unseeded random source in a test.
    Nondeterminism,
    /// `TESTQ003`: `if`, a loop or `match` in a test body.
    ControlFlow,
}

impl Kind {
    /// The rule id this kind belongs to.
    pub fn rule_id(self) -> &'static str {
        match self {
            Self::NoAssertion => "TESTQ001",
            Self::Nondeterminism => "TESTQ002",
            Self::ControlFlow => "TESTQ003",
        }
    }

    /// Whether the rule runs unless a project turns it on; control flow in tests is a taste call.
    pub fn default_enabled(self) -> bool {
        !matches!(self, Self::ControlFlow)
    }
}

/// One test-quality site.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Site {
    /// The shape found.
    pub kind: Kind,
    /// The test name, call or construct, as byte offsets in the scanned text.
    pub range: TextRange,
    /// 1-based line where the site starts.
    pub line: usize,
    /// Whether the syntax alone decides it; an Unknown site is Unresolved, never a hit.
    pub certainty: Certainty,
    /// What was found: the test name, the call path, or the construct kind.
    pub detail: String,
}

/// The result of one scan: the sites, and the rules that could not be decided.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Report {
    /// Sites in source order.
    pub sites: Vec<Site>,
    /// Kinds the language has no test roles for: Unresolved, never clean.
    pub unresolved: Vec<Kind>,
}

/// True when `language` has the test roles the TESTQ rules need.
pub fn has_test_roles(language: Language) -> bool {
    Lang::of(language).is_some()
}

/// True when a Python file at `path` is a test file by name or directory.
pub fn is_test_file(path: &Path) -> bool {
    let stem = path
        .file_stem()
        .map(std::ffi::OsStr::as_encoded_bytes)
        .unwrap_or_default();
    stem.starts_with(b"test_")
        || stem.ends_with(b"_test")
        || stem == b"conftest"
        || path
            .components()
            .any(|c| c.as_os_str() == "tests" || c.as_os_str() == "test")
}

/// One test function found in the file.
struct Test<'t> {
    func: Node<'t>,
    /// Attribute or decorator text, for exemptions.
    marks: String,
    skipped: bool,
    /// Rust `should_panic` or a `Result` return: the test fails by other means.
    exempt: bool,
    /// A Python test class with bases that may hide helper methods.
    class_open: bool,
}

fn attr_name(item: &str) -> String {
    let inner = item
        .trim()
        .trim_start_matches("#[")
        .trim_end_matches(']')
        .trim();
    let head = inner
        .split(|c: char| c == '(' || c == '=' || c.is_whitespace())
        .next()
        .unwrap_or_default();
    head.rsplit("::").next().unwrap_or_default().to_owned()
}

fn rust_test<'t>(cx: &Ctx<'t>, f: Node<'t>) -> Option<Test<'t>> {
    let mut attrs = Vec::new();
    let mut prev = f.prev_sibling();
    while let Some(p) = prev {
        match p.kind() {
            "attribute_item" => attrs.push(text(p, cx.src).to_owned()),
            "line_comment" | "block_comment" => {}
            _ => break,
        }
        prev = p.prev_sibling();
    }
    let names: Vec<String> = attrs.iter().map(|a| attr_name(a)).collect();
    if !names.iter().any(|n| RUST_TEST_ATTRS.contains(&n.as_str())) {
        return None;
    }
    let returns_result = f
        .child_by_field_name("return_type")
        .is_some_and(|r| text(r, cx.src).contains("Result"));
    Some(Test {
        func: f,
        marks: attrs.join("\n"),
        skipped: names.iter().any(|n| n == "ignore"),
        exempt: returns_result || names.iter().any(|n| n == "should_panic"),
        class_open: false,
    })
}

fn py_test<'t>(cx: &Ctx<'t>, f: Node<'t>) -> Option<Test<'t>> {
    let name = text(f.child_by_field_name("name")?, cx.src);
    let outer = match f.parent() {
        Some(p) if p.kind() == "decorated_definition" => p,
        _ => f,
    };
    let marks: Vec<String> = children(outer)
        .into_iter()
        .filter(|c| c.kind() == "decorator")
        .map(|c| text(c, cx.src).to_owned())
        .collect();
    let class_open = match outer.parent() {
        Some(block) if block.kind() == "block" => {
            let class = block.parent().filter(|c| c.kind() == "class_definition")?;
            let bases: Vec<&str> = class
                .child_by_field_name("superclasses")
                .map(|s| {
                    children(s)
                        .into_iter()
                        .filter(Node::is_named)
                        .map(|b| text(b, cx.src))
                        .collect()
                })
                .unwrap_or_default();
            let cname = text(class.child_by_field_name("name")?, cx.src);
            let is_case = bases.iter().any(|b| b.contains("TestCase"));
            if !(cname.starts_with("Test") || is_case) || !name.starts_with("test") {
                return None;
            }
            bases
                .iter()
                .any(|b| !CLOSED_BASES.contains(&b.rsplit('.').next().unwrap_or_default()))
        }
        Some(m) if m.kind() == "module" => {
            if !name.starts_with("test") {
                return None;
            }
            false
        }
        _ => return None,
    };
    let skipped = marks.iter().any(|m| {
        let head = m
            .trim_start_matches('@')
            .split('(')
            .next()
            .unwrap_or_default();
        head.trim().rsplit('.').next() == Some("skip")
    });
    Some(Test {
        func: f,
        marks: marks.join("\n"),
        skipped,
        exempt: false,
        class_open,
    })
}

fn discover<'t>(cx: &Ctx<'t>, n: Node<'t>, out: &mut Vec<Test<'t>>) {
    let found = match (cx.lang, n.kind()) {
        (Lang::Rust, "function_item") => rust_test(cx, n),
        (Lang::Python, "function_definition") => py_test(cx, n),
        _ => None,
    };
    out.extend(found);
    for c in children(n) {
        discover(cx, c, out);
    }
}

/// The outermost control-flow constructs of `n`, not descending into nested functions.
fn control_flow<'t>(lang: Lang, n: Node<'t>, out: &mut Vec<Node<'t>>) {
    let kinds: &[&str] = match lang {
        Lang::Rust => &[
            "if_expression",
            "for_expression",
            "while_expression",
            "loop_expression",
            "match_expression",
        ],
        Lang::Python => &[
            "if_statement",
            "for_statement",
            "while_statement",
            "match_statement",
        ],
    };
    if kinds.contains(&n.kind()) {
        out.push(n);
        return;
    }
    if matches!(n.kind(), "function_item" | "function_definition") {
        return;
    }
    for c in children(n) {
        control_flow(lang, c, out);
    }
}

/// Every test-quality site of `text` parsed as `language`, in source order.
///
/// A language without test roles yields no sites and lists every kind as unresolved. Python
/// module-level `test*` functions count as tests; use [`is_test_file`] to decide whether to scan
/// a file at all.
///
/// # Errors
///
/// [`ScanError`] when the file does not parse.
pub fn scan(language: Language, text: &str) -> Result<Report, ScanError> {
    let Some(lang) = Lang::of(language) else {
        tracing::debug!(language = language.name(), "test roles missing: unresolved");
        return Ok(Report {
            sites: Vec::new(),
            unresolved: vec![Kind::NoAssertion, Kind::Nondeterminism, Kind::ControlFlow],
        });
    };
    let tree = match parse(language, text, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => tree,
        ParseResult::Unresolved(u) => return Err(ScanError::Parse(u.reason.to_string())),
    };
    let root = tree.root();
    let cx = Ctx::build(lang, root, text);
    let mut tests = Vec::new();
    discover(&cx, root, &mut tests);

    let mut sites = Vec::new();
    let mut push = |kind, node: Node<'_>, certainty, detail: String| {
        sites.push(Site {
            kind,
            range: tree.node_range(&node),
            line: node.start_position().row + 1,
            certainty,
            detail,
        });
    };
    for t in tests.iter().filter(|t| !t.skipped) {
        let name_node = t.func.child_by_field_name("name").unwrap_or(t.func);
        let name = crate::syntax::text(name_node, text).to_owned();
        if !t.exempt {
            let verdict = assert::Resolver::new(&cx, t.class_open).function(t.func, 0);
            match verdict {
                assert::Verdict::No => {
                    push(
                        Kind::NoAssertion,
                        name_node,
                        Certainty::Certain,
                        name.clone(),
                    );
                }
                assert::Verdict::Unknown => {
                    push(
                        Kind::NoAssertion,
                        name_node,
                        Certainty::Unknown,
                        name.clone(),
                    );
                }
                assert::Verdict::Asserts => {}
            }
        }
        for h in nondet::find(&cx, t.func, &t.marks, root) {
            push(Kind::Nondeterminism, h.node, Certainty::Certain, h.detail);
        }
        if let Some(body) = t.func.child_by_field_name("body") {
            let mut flow = Vec::new();
            control_flow(lang, body, &mut flow);
            for n in flow {
                push(
                    Kind::ControlFlow,
                    n,
                    Certainty::Certain,
                    n.kind().to_owned(),
                );
            }
        }
    }
    sites.sort_by_key(|s| (s.range.start(), s.kind));
    sites.dedup();
    tracing::debug!(
        language = language.name(),
        tests = tests.len(),
        sites = sites.len(),
        "testq sites scanned"
    );
    Ok(Report {
        sites,
        unresolved: Vec::new(),
    })
}
