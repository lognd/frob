//! `DOC003`: every document under `docs/` carries one status header from the fixed vocabulary.

// frob:ticket 01M4H0RKJHHWWT0XC17W5JD1VG

use std::path::Path;

use gob_rules::{Finding, RuleDecl as _};
use gob_symbols::{DocStatus, StatusProblem, parse_header};
use gob_text::{FileInterner, Span};

use crate::rules::doc003::Doc003;
use crate::todo::range;
use crate::unity::tracked_paths;
use crate::util::finding_def;

/// The directory the rule covers.
const DOCS_DIR: &str = "docs";

/// The vocabulary a finding quotes.
const VOCABULARY: &str = "current, draft, historical, generated or superseded-by <document>";

/// True for a tracked markdown path under the docs directory.
fn is_doc(path: &str) -> bool {
    let p = Path::new(path);
    p.starts_with(DOCS_DIR) && p.extension().is_some_and(|e| e == "md")
}

/// True when `target` names a file beside `path` or under the docs directory.
fn target_exists(root: &Path, path: &str, target: &str) -> bool {
    let beside = Path::new(path).parent().unwrap_or(Path::new(""));
    root.join(beside).join(target).is_file() || root.join(DOCS_DIR).join(target).is_file()
}

/// The finding for one problem of the document `path`, anchored on its status line.
fn problem(
    files: &mut FileInterner,
    text: &str,
    path: &str,
    line: u32,
    message: String,
) -> Finding {
    let offset: usize = text
        .split_inclusive('\n')
        .take(line.saturating_sub(1) as usize)
        .map(str::len)
        .sum();
    let span = Span::new(files.intern(path), range(offset, 0));
    finding_def(Doc003::DEF, Some(span), message, path)
}

/// DOC003 over one document: a missing, unknown or dangling status.
fn check_doc(root: &Path, path: &str, text: &str, files: &mut FileInterner) -> Option<Finding> {
    let header = parse_header(text);
    let message = match &header.status {
        Ok(DocStatus::SupersededBy(target)) if !target_exists(root, path, target) => {
            format!("`superseded-by {target}` names a document that does not exist")
        }
        Ok(_) => return None,
        Err(StatusProblem::Missing) => {
            format!("no `Status:` line in the header block; use one of {VOCABULARY}")
        }
        Err(StatusProblem::Unknown(got)) => {
            format!("status `{got}` is not in the vocabulary ({VOCABULARY})")
        }
        Err(StatusProblem::NoTarget) => "`superseded-by` names no document".to_owned(),
    };
    Some(problem(files, text, path, header.status_line, message))
}

/// DOC003 over every tracked markdown document under `docs/`; generated pages are exempt.
pub(crate) fn doc003(root: &Path, files: &mut FileInterner) -> Vec<Finding> {
    let mut out = Vec::new();
    for path in tracked_paths(root).into_iter().filter(|p| is_doc(p)) {
        let Ok(text) = std::fs::read_to_string(root.join(&path)) else {
            tracing::debug!(%path, "document not readable; skipped");
            continue;
        };
        if let Some(f) = check_doc(root, &path, &text, files) {
            tracing::info!(%path, "DOC003 finding");
            out.push(f);
        }
    }
    out
}
