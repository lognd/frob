//! Unpaired resource acquisition: an acquire call with no paired release in its scope.
//!
//! The pairs live in the [`PAIRS`] table, so a new acquire/release API is a data change, not a new
//! detector. The check is structural (no taint, no path sensitivity): a release call anywhere in
//! the acquire's scope pairs it.

// frob:ticket 01M1T07NY615PQ6RAEB4CESXMT

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gob_text::{TextRange, TextSize};
use tree_sitter::Node;

/// Where a release must appear to pair with an acquire.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScopeKind {
    /// The enclosing class, else the outermost enclosing function, else the file.
    ClassOrFunction,
    /// The enclosing class, else the file.
    ClassOrFile,
    /// The whole file.
    File,
}

/// How an acquire call is recognised.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Acquire {
    /// A call whose callee text is exactly this (`setTimeout`, `performance.mark`).
    Call(&'static str),
    /// A method call of this name; with a constructor, only on receivers built by `new Ctor`.
    Method(&'static str, Option<&'static str>),
    /// `new Ctor(..)` bound to a name; the bound name is the receiver.
    New(&'static str),
}

/// One acquire/release API pair.
#[derive(Debug, Clone, Copy)]
pub struct Pair {
    /// Stable pair id, reported on every site.
    pub id: &'static str,
    /// The acquire call.
    pub acquire: Acquire,
    /// Release callee texts (for [`Acquire::Call`]) or method names (otherwise).
    pub release: &'static [&'static str],
    /// Where a release counts.
    pub scope: ScopeKind,
    /// True when the release must be a method call on the acquire's receiver.
    pub same_receiver: bool,
    /// True when the acquire's result is the handle the release needs.
    pub needs_handle: bool,
}

/// The known acquire/release API table.
pub const PAIRS: &[Pair] = &[
    Pair {
        id: "performance-mark",
        acquire: Acquire::Call("performance.mark"),
        release: &["performance.clearMarks"],
        scope: ScopeKind::File,
        same_receiver: false,
        needs_handle: false,
    },
    Pair {
        id: "map-set",
        acquire: Acquire::Method("set", Some("Map")),
        release: &["delete", "clear"],
        scope: ScopeKind::ClassOrFile,
        same_receiver: true,
        needs_handle: false,
    },
    Pair {
        id: "set-timeout",
        acquire: Acquire::Call("setTimeout"),
        release: &["clearTimeout"],
        scope: ScopeKind::ClassOrFunction,
        same_receiver: false,
        needs_handle: true,
    },
    Pair {
        id: "set-interval",
        acquire: Acquire::Call("setInterval"),
        release: &["clearInterval"],
        scope: ScopeKind::ClassOrFunction,
        same_receiver: false,
        needs_handle: true,
    },
    Pair {
        id: "add-event-listener",
        acquire: Acquire::Method("addEventListener", None),
        release: &["removeEventListener"],
        scope: ScopeKind::ClassOrFunction,
        same_receiver: true,
        needs_handle: false,
    },
    Pair {
        id: "object-url",
        acquire: Acquire::Call("URL.createObjectURL"),
        release: &["URL.revokeObjectURL"],
        scope: ScopeKind::ClassOrFunction,
        same_receiver: false,
        needs_handle: false,
    },
    Pair {
        id: "abort-controller",
        acquire: Acquire::New("AbortController"),
        release: &["abort"],
        scope: ScopeKind::ClassOrFunction,
        same_receiver: true,
        needs_handle: true,
    },
];

/// How sure the scan is that the site leaks.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Certainty {
    /// No paired release exists in scope and the handle goes nowhere else.
    Certain,
    /// The handle is used elsewhere in scope or discarded, so a release may live out of sight.
    Unknown,
}

/// One acquire with no paired release in scope.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Site {
    /// The [`Pair::id`] that is unpaired.
    pub pair: &'static str,
    /// The acquire call, as byte offsets in the scanned text.
    pub range: TextRange,
    /// Whether the syntax alone decides it.
    pub certainty: Certainty,
}

/// Why a file could not be scanned.
#[derive(Debug, thiserror::Error)]
pub enum ScanError {
    /// The file did not parse within the limits, or its grammar is not built in.
    #[error("E-RES-PARSE: {0}")]
    Parse(String),
}

/// Test-framework callbacks whose bodies are exempt.
const TEST_CALLEES: &[&str] = &[
    "describe",
    "it",
    "test",
    "suite",
    "specify",
    "beforeEach",
    "afterEach",
    "beforeAll",
    "afterAll",
];

/// A call or `new` expression found in the file.
struct Call {
    start: usize,
    end: usize,
    /// Callee text without a `window.` or `globalThis.` prefix; the constructor for `new`.
    callee: String,
    /// Method name and normalised receiver for member calls.
    member: Option<(String, String)>,
    is_new: bool,
    /// Normalised name the result is bound to.
    bound: Option<String>,
    /// Scope ranges per [`ScopeKind`]: class-or-function, class-or-file, file.
    scopes: [(usize, usize); 3],
    in_test: bool,
}

pub(crate) fn text<'a>(n: Node<'_>, src: &'a str) -> &'a str {
    src.get(n.start_byte()..n.end_byte()).unwrap_or_default()
}

/// Receiver or name text with `this.` and global-object prefixes removed.
pub(crate) fn normalise(s: &str) -> String {
    let s = s.trim();
    for p in ["this.", "window.", "globalThis.", "self."] {
        if let Some(rest) = s.strip_prefix(p) {
            return rest.to_owned();
        }
    }
    s.to_owned()
}

pub(crate) fn is_function(kind: &str) -> bool {
    matches!(
        kind,
        "function_declaration"
            | "function_expression"
            | "function"
            | "generator_function"
            | "generator_function_declaration"
            | "arrow_function"
            | "method_definition"
    )
}

fn is_class(kind: &str) -> bool {
    matches!(
        kind,
        "class_declaration" | "class" | "abstract_class_declaration"
    )
}

fn range(n: Node<'_>) -> (usize, usize) {
    (n.start_byte(), n.end_byte())
}

/// The name an expression's value is bound to, if its parent binds it.
pub(crate) fn bound_name(node: Node<'_>, src: &str) -> Option<String> {
    let mut cur = node;
    let mut parent = node.parent()?;
    while matches!(
        parent.kind(),
        "await_expression" | "parenthesized_expression"
    ) {
        cur = parent;
        parent = parent.parent()?;
    }
    let same = |field: &str| {
        parent
            .child_by_field_name(field)
            .is_some_and(|c| c.id() == cur.id())
    };
    match parent.kind() {
        "variable_declarator" if same("value") => parent
            .child_by_field_name("name")
            .map(|n| normalise(text(n, src))),
        "assignment_expression" if same("right") => parent
            .child_by_field_name("left")
            .map(|n| normalise(text(n, src))),
        "public_field_definition" | "field_definition" if same("value") => parent
            .child_by_field_name("name")
            .or_else(|| parent.child_by_field_name("property"))
            .map(|n| normalise(text(n, src))),
        _ => None,
    }
}

/// Scope ranges (see [`ScopeKind`] order) of the expression `node`.
fn scopes_of(node: Node<'_>, file: (usize, usize)) -> [(usize, usize); 3] {
    let mut outer_fn = None;
    let mut class = None;
    let mut cur = node.parent();
    while let Some(n) = cur {
        if is_class(n.kind()) {
            class = Some(range(n));
            break;
        }
        if is_function(n.kind()) {
            outer_fn = Some(range(n));
        }
        cur = n.parent();
    }
    [
        class.or(outer_fn).unwrap_or(file),
        class.unwrap_or(file),
        file,
    ]
}

/// True when some ancestor call is a test-framework callee such as `it(...)`.
fn under_test_call(node: Node<'_>, src: &str) -> bool {
    let mut cur = node.parent();
    while let Some(n) = cur {
        if n.kind() == "call_expression"
            && let Some(f) = n.child_by_field_name("function")
            && f.kind() == "identifier"
            && TEST_CALLEES.contains(&text(f, src))
        {
            return true;
        }
        cur = n.parent();
    }
    false
}

fn collect(node: Node<'_>, src: &str, file: (usize, usize), out: &mut Vec<Call>) {
    let kind = node.kind();
    if kind == "call_expression" || kind == "new_expression" {
        let is_new = kind == "new_expression";
        let callee_node = node.child_by_field_name(if is_new { "constructor" } else { "function" });
        if let Some(c) = callee_node {
            let member = (!is_new && c.kind() == "member_expression")
                .then(|| {
                    let obj = c.child_by_field_name("object")?;
                    let prop = c.child_by_field_name("property")?;
                    Some((text(prop, src).to_owned(), normalise(text(obj, src))))
                })
                .flatten();
            let scopes = scopes_of(node, file);
            out.push(Call {
                start: node.start_byte(),
                end: node.end_byte(),
                callee: normalise(text(c, src)),
                member,
                is_new,
                bound: bound_name(node, src),
                scopes,
                in_test: under_test_call(node, src),
            });
        }
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect(child, src, file, out);
    }
}

/// Receivers built by `new <ctor>` anywhere in the file, as normalised names.
fn constructed(calls: &[Call], ctor: &str) -> Vec<String> {
    calls
        .iter()
        .filter(|c| c.is_new && c.callee == ctor)
        .filter_map(|c| c.bound.clone())
        .collect()
}

pub(crate) fn count_word(haystack: &str, word: &str) -> usize {
    let ident = |c: char| c.is_alphanumeric() || c == '_' || c == '$';
    haystack
        .match_indices(word)
        .filter(|(i, _)| {
            !haystack[..*i].chars().next_back().is_some_and(ident)
                && !haystack[i + word.len()..].chars().next().is_some_and(ident)
        })
        .count()
}

pub(crate) fn span(start: usize, end: usize) -> TextRange {
    let clamp = |n: usize| TextSize::new(u32::try_from(n).unwrap_or(u32::MAX));
    TextRange::new(clamp(start), clamp(end))
}

fn scope_index(kind: ScopeKind) -> usize {
    match kind {
        ScopeKind::ClassOrFunction => 0,
        ScopeKind::ClassOrFile => 1,
        ScopeKind::File => 2,
    }
}

/// The receiver (empty for plain calls) when `c` is an acquire of `pair`.
fn acquires<'a>(pair: &Pair, c: &'a Call, maps: &[String]) -> Option<&'a str> {
    match pair.acquire {
        Acquire::Call(name) => (!c.is_new && c.callee == name).then_some(""),
        Acquire::Method(name, ctor) => {
            let (m, recv) = c.member.as_ref()?;
            (m == name && ctor.is_none_or(|_| maps.contains(recv))).then_some(recv.as_str())
        }
        Acquire::New(ctor) => (c.is_new && c.callee == ctor)
            .then_some(c.bound.as_deref())
            .flatten(),
    }
}

/// Every acquire in `text` parsed as `language` with no paired release in scope, in source order.
///
/// A language without a detector yields no sites; a tree with syntax errors is still scanned.
///
/// # Errors
///
/// [`ScanError::Parse`] when the file does not parse within the limits.
pub fn scan(language: Language, text: &str) -> Result<Vec<Site>, ScanError> {
    if !matches!(
        language,
        Language::TypeScript | Language::Tsx | Language::JavaScript | Language::Jsx
    ) {
        return Ok(Vec::new());
    }
    let tree = match parse(language, text, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => tree,
        ParseResult::Unresolved(u) => return Err(ScanError::Parse(u.reason.to_string())),
    };
    let file = (0, text.len());
    let mut calls = Vec::new();
    collect(tree.root(), text, file, &mut calls);
    let mut sites = Vec::new();
    for pair in PAIRS {
        let maps = match pair.acquire {
            Acquire::Method(_, Some(ctor)) => constructed(&calls, ctor),
            _ => Vec::new(),
        };
        for c in calls.iter().filter(|c| !c.in_test) {
            let Some(receiver) = acquires(pair, c, &maps) else {
                continue;
            };
            let (lo, hi) = c.scopes[scope_index(pair.scope)];
            let released = calls.iter().any(|r| {
                r.start >= lo
                    && r.end <= hi
                    && if pair.same_receiver {
                        r.member.as_ref().is_some_and(|(m, recv)| {
                            pair.release.contains(&m.as_str()) && recv == receiver
                        })
                    } else {
                        !r.is_new && pair.release.contains(&r.callee.as_str())
                    }
            });
            if released {
                continue;
            }
            let handle = pair.needs_handle.then_some(c.bound.as_deref());
            let certainty = match handle {
                Some(None) => Certainty::Unknown,
                Some(Some(name)) => {
                    let scope_text = text.get(lo..hi).unwrap_or_default();
                    let bare = name.rsplit('.').next().unwrap_or(name);
                    if count_word(scope_text, bare) > 1 {
                        Certainty::Unknown
                    } else {
                        Certainty::Certain
                    }
                }
                None => Certainty::Certain,
            };
            sites.push(Site {
                pair: pair.id,
                range: span(c.start, c.end),
                certainty,
            });
        }
    }
    sites.sort_by_key(|s| (s.range.start(), s.pair));
    tracing::debug!(
        language = language.name(),
        sites = sites.len(),
        "unpaired acquires scanned"
    );
    Ok(sites)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn found(text: &str) -> Vec<(&'static str, Certainty)> {
        scan(Language::TypeScript, text)
            .expect("scan")
            .into_iter()
            .map(|s| (s.pair, s.certainty))
            .collect()
    }

    // frob:tests crates/grimble-lints/src/res.rs::scan
    #[test]
    fn mark_map_set_and_timeout_without_release_each_yield_one_site() {
        assert_eq!(
            found("function f() { performance.mark('a'); }\n"),
            [("performance-mark", Certainty::Certain)]
        );
        assert_eq!(
            found("const cache = new Map();\nfunction f(k) { cache.set(k, 1); }\n"),
            [("map-set", Certainty::Certain)]
        );
        assert_eq!(
            found("function f() { const t = setTimeout(() => {}, 5); }\n"),
            [("set-timeout", Certainty::Certain)]
        );
    }

    // frob:tests crates/grimble-lints/src/res.rs::scan
    #[test]
    fn paired_release_in_scope_is_quiet() {
        assert!(
            found("function f() { performance.mark('a'); performance.clearMarks('a'); }\n")
                .is_empty()
        );
        assert!(
            found("class C { m = new Map(); put(k) { this.m.set(k, 1); } drop(k) { this.m.delete(k); } }\n")
                .is_empty()
        );
        assert!(
            found("function f() { const t = setTimeout(g, 5); clearTimeout(t); }\n").is_empty()
        );
        assert!(
            found("class C { start() { this.t = setTimeout(g, 5); } stop() { clearTimeout(this.t); } }\n")
                .is_empty()
        );
    }

    // frob:tests crates/grimble-lints/src/res.rs::scan
    #[test]
    fn release_on_another_receiver_or_in_another_scope_does_not_pair() {
        assert_eq!(
            found(
                "const a = new Map(); const b = new Map();\nfunction f() { a.set(1, 1); b.delete(1); }\n"
            ),
            [("map-set", Certainty::Certain)]
        );
        assert_eq!(
            found(
                "function f() { const t = setTimeout(g, 5); }\nfunction h() { clearTimeout(x); }\n"
            ),
            [("set-timeout", Certainty::Certain)]
        );
    }

    // frob:tests crates/grimble-lints/src/res.rs::scan
    #[test]
    fn other_table_rows_fire_unpaired_and_stay_quiet_paired() {
        let cases = [
            (
                "function f() { setInterval(g, 5); }",
                "function f() { const i = setInterval(g, 5); clearInterval(i); }",
                "set-interval",
            ),
            (
                "function f(el) { el.addEventListener('x', g); }",
                "function f(el) { el.addEventListener('x', g); el.removeEventListener('x', g); }",
                "add-event-listener",
            ),
            (
                "function f(b) { return URL.createObjectURL(b); }",
                "function f(b) { const u = URL.createObjectURL(b); URL.revokeObjectURL(u); }",
                "object-url",
            ),
            (
                "function f() { const c = new AbortController(); }",
                "function f() { const c = new AbortController(); c.abort(); }",
                "abort-controller",
            ),
        ];
        for (bad, good, id) in cases {
            assert!(found(bad).iter().any(|(p, _)| *p == id), "{id}: {bad}");
            assert!(found(good).is_empty(), "{id}: {good}");
        }
    }

    // frob:tests crates/grimble-lints/src/res.rs::scan
    #[test]
    fn escaping_or_discarded_handles_are_unknown_and_tests_are_exempt() {
        assert_eq!(
            found("function f() { const t = setTimeout(g, 5); return t; }\n"),
            [("set-timeout", Certainty::Unknown)]
        );
        assert_eq!(
            found("function f() { setTimeout(g, 5); }\n"),
            [("set-timeout", Certainty::Unknown)]
        );
        assert!(
            found("it('x', () => { const m = new Map(); m.set(1, 1); performance.mark('a'); });\n")
                .is_empty()
        );
        assert!(
            found("function f(m) { m.set(1, 1); }\n").is_empty(),
            "receiver not built by new Map"
        );
    }

    // frob:tests crates/grimble-lints/src/res.rs::scan
    #[test]
    fn javascript_is_scanned_and_other_languages_have_no_sites() {
        assert_eq!(
            scan(Language::JavaScript, "performance.mark('a');\n")
                .expect("scan")
                .len(),
            1
        );
        assert!(
            scan(Language::Python, "performance.mark('a')\n")
                .expect("scan")
                .is_empty()
        );
    }
}
