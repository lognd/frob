//! Cached tree-sitter queries and span-reporting capture iteration.

use std::collections::HashMap;
use std::sync::{Mutex, PoisonError};

use gob_text::TextRange;
use tree_sitter::StreamingIterator;

use crate::grammar::ts_language;
use crate::{Language, ParsedTree};

/// Failure to compile a query.
#[derive(Debug, Clone, thiserror::Error)]
pub enum QueryError {
    /// The language's grammar is not compiled in.
    #[error("grammar for {0} is unavailable")]
    GrammarUnavailable(&'static str),
    /// The query source did not compile.
    #[error("query for {language} failed to compile: {message}")]
    Compile {
        /// Language name.
        language: &'static str,
        /// Compiler message with location.
        message: String,
    },
}

/// A query compiled once for one language.
#[derive(Debug)]
pub struct CompiledQuery {
    language: Language,
    query: tree_sitter::Query,
}

impl CompiledQuery {
    /// The language this query was compiled for.
    pub fn language(&self) -> Language {
        self.language
    }
}

/// One captured node: capture name, span and source text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Capture {
    /// The capture name without the leading `@`.
    pub name: String,
    /// Byte range of the captured node.
    pub node_range: TextRange,
    /// Source text of the captured node.
    pub text: String,
}

type Cache = Mutex<HashMap<(Language, &'static str), &'static CompiledQuery>>;

fn cache() -> &'static Cache {
    static CACHE: std::sync::OnceLock<Cache> = std::sync::OnceLock::new();
    CACHE.get_or_init(Mutex::default)
}

/// Compiles `source` for `language` once per process and returns the cached
/// result on later calls.
///
/// # Errors
///
/// [`QueryError::GrammarUnavailable`] when the feature is off,
/// [`QueryError::Compile`] when the query is invalid (failures are not cached).
pub fn compiled_query(
    language: Language,
    source: &'static str,
) -> Result<&'static CompiledQuery, QueryError> {
    let mut map = cache().lock().unwrap_or_else(PoisonError::into_inner);
    if let Some(hit) = map.get(&(language, source)) {
        return Ok(hit);
    }
    let ts = ts_language(language).ok_or(QueryError::GrammarUnavailable(language.name()))?;
    let query = tree_sitter::Query::new(&ts, source).map_err(|e| {
        tracing::warn!(language = language.name(), error = %e, "query compile failed");
        QueryError::Compile {
            language: language.name(),
            message: e.to_string(),
        }
    })?;
    tracing::debug!(language = language.name(), "query compiled");
    let leaked: &'static CompiledQuery = Box::leak(Box::new(CompiledQuery { language, query }));
    map.insert((language, source), leaked);
    Ok(leaked)
}

/// Runs `query` over `tree` and yields every capture in match order.
///
/// A query compiled for a different language than the tree yields nothing.
pub fn captures(query: &CompiledQuery, tree: &ParsedTree) -> impl Iterator<Item = Capture> {
    let mut out = Vec::new();
    if query.language == tree.language {
        let mut cursor = tree_sitter::QueryCursor::new();
        let names = query.query.capture_names();
        let mut matches = cursor.matches(&query.query, tree.root(), tree.text.as_bytes());
        while let Some(m) = matches.next() {
            for c in m.captures() {
                let text = c.node.utf8_text(tree.text.as_bytes()).unwrap_or_default();
                out.push(Capture {
                    name: names[c.index as usize].to_owned(),
                    node_range: tree.node_range(&c.node),
                    text: text.to_owned(),
                });
            }
        }
    } else {
        tracing::warn!(
            query = query.language.name(),
            tree = tree.language.name(),
            "language mismatch"
        );
    }
    out.into_iter()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parse::tests::parsed;

    #[cfg(any(feature = "markdown", feature = "toml"))]
    fn texts(lang: Language, q: &'static str, src: &str) -> Vec<(String, String)> {
        let tree = parsed(lang, src);
        captures(compiled_query(lang, q).unwrap(), &tree)
            .map(|c| (c.name, c.text))
            .collect()
    }

    #[cfg(feature = "rust")]
    #[test]
    fn rust_fn_names_with_spans() {
        let src = "fn alpha() {}\nstruct S;\nfn beta(x: u8) {}\n";
        let q = "(function_item name: (identifier) @name)";
        let tree = parsed(Language::Rust, src);
        let caps: Vec<_> = captures(compiled_query(Language::Rust, q).unwrap(), &tree).collect();
        assert_eq!(caps.len(), 2);
        assert_eq!(caps[0].text, "alpha");
        assert_eq!(caps[1].text, "beta");
        assert_eq!(&src[caps[1].node_range.to_usize_range()], "beta");
    }

    #[cfg(feature = "markdown")]
    #[test]
    fn markdown_headings() {
        let got = texts(
            Language::Markdown,
            "(atx_heading (inline) @heading)",
            "# One\n\ntext\n\n## Two\n",
        );
        assert_eq!(
            got,
            vec![
                ("heading".into(), "One".into()),
                ("heading".into(), "Two".into())
            ]
        );
    }

    #[cfg(feature = "toml")]
    #[test]
    fn toml_table_headers() {
        let got = texts(
            Language::Toml,
            "(table (bare_key) @name)",
            "[package]\nname = \"x\"\n[deps]\n",
        );
        assert_eq!(
            got,
            vec![
                ("name".into(), "package".into()),
                ("name".into(), "deps".into())
            ]
        );
    }

    #[cfg(feature = "rust")]
    #[test]
    fn compiles_once_and_reports_errors() {
        let q = "(function_item name: (identifier) @n)";
        let a = compiled_query(Language::Rust, q).unwrap();
        let b = compiled_query(Language::Rust, q).unwrap();
        assert!(std::ptr::eq(a, b));
        assert!(matches!(
            compiled_query(Language::Rust, "(not_a_node) @x"),
            Err(QueryError::Compile { .. })
        ));
    }

    #[cfg(all(feature = "rust", feature = "toml"))]
    #[test]
    fn mismatched_language_yields_nothing() {
        let q = compiled_query(Language::Rust, "(identifier) @i").unwrap();
        let tree = parsed(Language::Toml, "a = 1\n");
        assert_eq!(captures(q, &tree).count(), 0);
    }
}
