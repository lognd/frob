//! Host-path portability sites: `PATH001`, `PATH002` and `PATH003` (rules.md section 3.1).
//!
//! [`scan`] reports an absolute host path literal (`PATH001`, every language with a string
//! literal), a path turned into a string and then split, joined, compared or searched with a
//! literal separator (`PATH002`), and a path interpolated into one command-line string
//! (`PATH003`). `PATH002` and `PATH003` need the path-conversion roles of a language
//! ([`has_conversion_roles`]); for any other code language the [`Report`] lists them as
//! unresolved instead of silently clean. Mapping a site to a severity belongs to the rule that
//! consumes it; [`default_severity`] gives the shipped defaults.

// frob:ticket 01M41RV691XZQ5W2EW821PHK3V

mod flow;
mod literal;

use gob_languages::{Language, ParseLimits, ParseResult, parse};
use gob_text::TextRange;

use flow::Lang;

/// Which portability shape a site is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Kind {
    /// `PATH001`: a string literal that is an absolute host path.
    AbsoluteHostPath,
    /// `PATH002`: a path-derived string handled with a literal separator.
    StringPathSeparator,
    /// `PATH003`: a path-derived string interpolated into one command-line string.
    PathInCommandLine,
}

impl Kind {
    /// The rule id this kind belongs to.
    pub fn rule_id(self) -> &'static str {
        match self {
            Self::AbsoluteHostPath => "PATH001",
            Self::StringPathSeparator => "PATH002",
            Self::PathInCommandLine => "PATH003",
        }
    }
}

/// The severity a finding carries.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Severity {
    /// Reported, never gating.
    Advisory,
    /// Reported, gating only when configured so.
    Warn,
    /// Gating.
    Error,
}

/// One portability site.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Site {
    /// The shape found.
    pub kind: Kind,
    /// The literal or expression, as byte offsets in the scanned text.
    pub range: TextRange,
    /// 1-based line where the site starts.
    pub line: usize,
    /// Whether the site is inside test code (a `#[test]` or `#[cfg(test)]` item, a `test_` function).
    pub in_test: bool,
}

/// Knobs of [`scan`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Options {
    /// Literals `PATH001` accepts as written (`[path] allowed`).
    pub allowed: Vec<String>,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            allowed: vec!["/dev/null".to_owned()],
        }
    }
}

/// The result of one scan: the sites, and the rules that could not be decided.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Report {
    /// Sites in source order.
    pub sites: Vec<Site>,
    /// Kinds the language has no path-conversion roles for: Unresolved, never clean.
    pub unresolved: Vec<Kind>,
}

/// Why a file could not be scanned.
#[derive(Debug, thiserror::Error)]
pub enum ScanError {
    /// The file did not parse within the limits, or its grammar is not built in.
    #[error("E-PATH-PARSE: {0}")]
    Parse(String),
}

/// True when `language` has the path-conversion roles `PATH002` and `PATH003` need.
pub fn has_conversion_roles(language: Language) -> bool {
    lang_of(language).is_some()
}

fn lang_of(language: Language) -> Option<Lang> {
    match language {
        Language::Rust => Some(Lang::Rust),
        Language::Python => Some(Lang::Python),
        _ => None,
    }
}

/// True when `language` has string literals `PATH001` can read.
fn has_literals(language: Language) -> bool {
    matches!(
        language,
        Language::Rust | Language::Python | Language::TypeScript | Language::CSharp
    )
}

/// The severity a kind ships with; `test_context` is a test file or a site with `in_test`.
pub fn default_severity(kind: Kind, test_context: bool) -> Severity {
    match kind {
        Kind::AbsoluteHostPath if test_context => Severity::Advisory,
        Kind::AbsoluteHostPath | Kind::StringPathSeparator | Kind::PathInCommandLine => {
            Severity::Warn
        }
    }
}

/// True when a repository-relative `path` names a test or fixture file.
pub fn is_test_path(path: &str) -> bool {
    let norm = path.replace('\\', "/");
    let name = norm.rsplit('/').next().unwrap_or(&norm);
    norm.split('/')
        .any(|c| matches!(c, "tests" | "test" | "fixtures" | "__tests__"))
        || name.starts_with("test_")
        || name.contains("_test.")
        || name.contains(".test.")
        || name.contains(".spec.")
}

/// Every portability site of `text` parsed as `language`, in source order.
///
/// A language without string literals yields nothing. A tree with syntax errors is still scanned.
///
/// # Errors
///
/// [`ScanError`] when the file does not parse.
pub fn scan(language: Language, text: &str, options: &Options) -> Result<Report, ScanError> {
    if !has_literals(language) {
        return Ok(Report::default());
    }
    let tree = match parse(language, text, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => tree,
        ParseResult::Unresolved(u) => return Err(ScanError::Parse(u.reason.to_string())),
    };
    let mut raw: Vec<(Kind, tree_sitter::Node<'_>)> = Vec::new();
    let mut stack = vec![tree.root()];
    while let Some(n) = stack.pop() {
        if literal::is_string_literal(language, n)
            && literal::decode(&text[n.byte_range()])
                .is_some_and(|v| literal::is_absolute_host_path(&v, &options.allowed))
        {
            raw.push((Kind::AbsoluteHostPath, n));
        }
        let mut cur = n.walk();
        stack.extend(n.children(&mut cur));
    }
    let mut unresolved = Vec::new();
    if let Some(lang) = lang_of(language) {
        raw.extend(
            flow::scan(lang, tree.root(), text)
                .into_iter()
                .map(|r| (r.kind, r.node)),
        );
    } else {
        unresolved.extend([Kind::StringPathSeparator, Kind::PathInCommandLine]);
        tracing::debug!(language = language.name(), "path roles missing: unresolved");
    }
    let mut sites: Vec<Site> = raw
        .into_iter()
        .map(|(kind, n)| Site {
            kind,
            range: tree.node_range(&n),
            line: n.start_position().row + 1,
            in_test: in_test(language, n, text),
        })
        .collect();
    sites.sort_by_key(|s| (s.range.start(), s.kind));
    sites.dedup();
    tracing::debug!(
        language = language.name(),
        sites = sites.len(),
        unresolved = unresolved.len(),
        "path sites scanned"
    );
    Ok(Report { sites, unresolved })
}

/// True when `node` sits inside test code.
fn in_test(language: Language, node: tree_sitter::Node<'_>, src: &str) -> bool {
    let mut cur = Some(node);
    while let Some(n) = cur {
        match (language, n.kind()) {
            (Language::Rust, "function_item" | "mod_item") => {
                let mut prev = n.prev_sibling();
                while let Some(p) =
                    prev.filter(|p| matches!(p.kind(), "attribute_item" | "line_comment"))
                {
                    if p.kind() == "attribute_item" && src[p.byte_range()].contains("test") {
                        return true;
                    }
                    prev = p.prev_sibling();
                }
            }
            (Language::Python, "function_definition" | "class_definition") => {
                let name = n
                    .child_by_field_name("name")
                    .map_or("", |c| &src[c.byte_range()]);
                if name.starts_with("test") || name.starts_with("Test") {
                    return true;
                }
            }
            _ => {}
        }
        cur = n.parent();
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/grimble-lints/src/path.rs::Kind.rule_id
    #[test]
    fn rule_ids_follow_kinds() {
        assert_eq!(Kind::AbsoluteHostPath.rule_id(), "PATH001");
        assert_eq!(Kind::StringPathSeparator.rule_id(), "PATH002");
        assert_eq!(Kind::PathInCommandLine.rule_id(), "PATH003");
    }

    // frob:tests crates/grimble-lints/src/path.rs::has_conversion_roles
    #[test]
    fn only_rust_and_python_have_roles() {
        assert!(has_conversion_roles(Language::Rust));
        assert!(has_conversion_roles(Language::Python));
        assert!(!has_conversion_roles(Language::TypeScript));
        assert!(!has_conversion_roles(Language::CSharp));
    }

    // frob:tests crates/grimble-lints/src/path.rs::default_severity
    #[test]
    fn host_path_is_advisory_in_tests() {
        assert_eq!(
            default_severity(Kind::AbsoluteHostPath, true),
            Severity::Advisory
        );
        assert_eq!(
            default_severity(Kind::AbsoluteHostPath, false),
            Severity::Warn
        );
        assert_eq!(
            default_severity(Kind::PathInCommandLine, true),
            Severity::Warn
        );
    }

    // frob:tests crates/grimble-lints/src/path.rs::is_test_path
    #[test]
    fn test_paths_are_recognised() {
        assert!(is_test_path("crates/x/tests/a.rs"));
        assert!(is_test_path("pkg\\test_a.py"));
        assert!(is_test_path("web/a.spec.ts"));
        assert!(!is_test_path("crates/x/src/lib.rs"));
    }

    // frob:tests crates/grimble-lints/src/path.rs::scan
    #[test]
    fn allowed_literal_is_quiet() {
        let r = scan(
            Language::Rust,
            "fn f() -> &'static str { \"/dev/null\" }",
            &Options::default(),
        )
        .expect("parses");
        assert!(r.sites.is_empty());
    }
}
