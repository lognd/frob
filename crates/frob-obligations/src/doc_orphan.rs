//! `DOC007`: a document under `docs/` that no link chain from a root page reaches.

// frob:ticket 01M67VEKBESFK2C23JMXV82RW9

use std::path::Path;

use frob_doc::{Page, orphans};
use gob_rules::{Finding, RuleDecl as _};
use gob_text::{FileInterner, Span};

use crate::rules::doc007::Doc007;
use crate::todo::range;
use crate::unity::tracked_paths;
use crate::util::finding_def;

/// Why the rule is a heuristic, quoted in every finding so a waiver can answer it.
const HEURISTIC: &str = "orphans are found by following markdown links from the root pages; \
    waive with `frob:waive DOC007` when a tool or a non-markdown reference is the page's only entry";

/// True for a tracked markdown path.
fn is_markdown(path: &str) -> bool {
    Path::new(path).extension().is_some_and(|e| e == "md")
}

/// DOC007 over every tracked markdown page: `docs/` pages unreachable from a root page.
pub(crate) fn doc007(root: &Path, files: &mut FileInterner) -> Vec<Finding> {
    let loaded: Vec<(String, String)> = tracked_paths(root)
        .into_iter()
        .filter(|p| is_markdown(p))
        .filter_map(|p| match std::fs::read_to_string(root.join(&p)) {
            Ok(text) => Some((p, text)),
            Err(why) => {
                tracing::debug!(path = %p, %why, "page not readable; skipped");
                None
            }
        })
        .collect();
    let pages: Vec<Page<'_>> = loaded
        .iter()
        .map(|(path, text)| Page { path, text })
        .collect();
    let found = match orphans(&pages) {
        Ok(found) => found,
        Err(why) => {
            tracing::warn!(%why, "DOC007 skipped");
            return Vec::new();
        }
    };
    found
        .into_iter()
        .map(|path| {
            tracing::info!(%path, "DOC007 finding");
            let span = Span::new(files.intern(&path), range(0, 0));
            let message = format!(
                "no page links to this document from the docs index or a root page ({HEURISTIC})"
            );
            finding_def(Doc007::DEF, Some(span), message, &path)
        })
        .collect()
}
