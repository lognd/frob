//! `docs/README.md`: the index of every document under `docs/` with its status header.
//!
//! The status vocabulary and its parser live in [`gob_symbols::parse_header`], shared with the
//! DOC003 rule, so the index and the rule can never disagree about what a header says.

// frob:ticket 01M4H0RKJHHWWT0XC17W5JD1VG

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use gob_symbols::{DocStatus, parse_header};

use super::{cell, md_header};
use crate::files::GenFile;

/// Repository path of the generated index.
const PATH: &str = "docs/README.md";
/// The documentation directory, relative to the workspace root.
const DOCS_DIR: &str = "docs";
/// A directory with more generated pages than this is listed as one row.
const COLLAPSE_OVER: usize = 20;
/// The word shown for a document whose header has no valid status.
const NO_STATUS: &str = "invalid";

/// Why the documentation index could not be generated.
#[derive(Debug, thiserror::Error)]
pub enum DocsIndexError {
    /// A directory or document could not be read.
    #[error("read {}: {source}", gob_path::Shown::with_home(path, None))]
    Io {
        /// The path.
        path: PathBuf,
        /// Underlying error.
        source: std::io::Error,
    },
}

/// One markdown document found under `docs/`.
struct Doc {
    /// Path relative to `docs/`, with forward slashes.
    rel: String,
    /// Title from the first `# ` heading, else the file name.
    title: String,
    /// The status word shown in the index.
    status: String,
    /// The owner, or a dash.
    owner: String,
}

/// The vocabulary section of the index, in the words the DOC003 rule enforces.
const VOCABULARY: &str = "Each hand-written document starts with a header block (Status, Owner, Decisions) in this vocabulary, and the DOC003 rule checks it:

- `current`: decided and, where it names code, built.
- `draft`: decided or proposed but not (fully) built, or still under review.
- `superseded-by X`: replaced by the document X, which must exist.
- `historical`: kept as a record; nothing new is built from it.
- `generated`: written by a generator named on its first line and checked by `cargo dev gen --check`; it carries the generator marker instead of a header block and is never edited by hand.
";

/// The status word the index shows for a parsed header.
fn status_word(status: &Result<DocStatus, gob_symbols::StatusProblem>) -> String {
    match status {
        Ok(DocStatus::Current) => "current".to_owned(),
        Ok(DocStatus::Draft) => "draft".to_owned(),
        Ok(DocStatus::Historical) => "historical".to_owned(),
        Ok(DocStatus::Generated) => "generated".to_owned(),
        Ok(DocStatus::SupersededBy(x)) => format!("superseded-by {x}"),
        Err(_) => NO_STATUS.to_owned(),
    }
}

/// Every file under `dir`, recursively and sorted, as paths below it.
fn walk(dir: &Path, out: &mut Vec<PathBuf>) -> Result<(), DocsIndexError> {
    let io = |source| DocsIndexError::Io {
        path: dir.to_path_buf(),
        source,
    };
    let mut entries: Vec<PathBuf> = std::fs::read_dir(dir)
        .map_err(io)?
        .map(|e| e.map(|e| e.path()))
        .collect::<Result<_, _>>()
        .map_err(io)?;
    entries.sort();
    for path in entries {
        if path.is_dir() {
            walk(&path, out)?;
        } else {
            out.push(path);
        }
    }
    Ok(())
}

/// `path` below `base` as a forward-slash string on every platform (the committed index form).
fn relative(base: &Path, path: &Path) -> String {
    gob_path::forward_slashes(path.strip_prefix(base).unwrap_or(path))
}

/// The directory part of the relative path `rel` (empty at the top).
fn dir_of(rel: &str) -> &str {
    rel.rsplit_once('/').map_or("", |(dir, _)| dir)
}

/// The section a document sorts under: its first path component, or the top level.
fn section_of(rel: &str) -> &str {
    rel.split_once('/').map_or("", |(first, _)| first)
}

/// The documents and the non-markdown files below `docs_dir`, apart from the index itself.
fn collect(docs_dir: &Path) -> Result<(Vec<Doc>, BTreeMap<String, usize>), DocsIndexError> {
    let mut paths = Vec::new();
    walk(docs_dir, &mut paths)?;
    let mut docs = Vec::new();
    let mut others: BTreeMap<String, usize> = BTreeMap::new();
    for path in paths {
        let rel = relative(docs_dir, &path);
        if path.extension().is_none_or(|e| e != "md") {
            *others.entry(dir_of(&rel).to_owned()).or_default() += 1;
            continue;
        }
        if rel == "README.md" {
            continue;
        }
        let text = std::fs::read_to_string(&path).map_err(|source| DocsIndexError::Io {
            path: path.clone(),
            source,
        })?;
        let header = parse_header(&text);
        let title = header.title.clone().unwrap_or_else(|| rel.clone());
        docs.push(Doc {
            rel,
            title,
            status: status_word(&header.status),
            owner: header.owner.unwrap_or_else(|| "-".to_owned()),
        });
    }
    Ok((docs, others))
}

/// Replace each directory of more than [`COLLAPSE_OVER`] generated pages by one summary row.
fn collapse(docs: Vec<Doc>) -> Vec<Doc> {
    let mut counts: BTreeMap<String, usize> = BTreeMap::new();
    for d in docs.iter().filter(|d| d.status == "generated") {
        *counts.entry(dir_of(&d.rel).to_owned()).or_default() += 1;
    }
    let big = |d: &Doc| {
        d.status == "generated" && counts.get(dir_of(&d.rel)).copied() > Some(COLLAPSE_OVER)
    };
    let mut out: Vec<Doc> = docs.into_iter().filter(|d| !big(d)).collect();
    for (dir, n) in counts.into_iter().filter(|(_, n)| *n > COLLAPSE_OVER) {
        out.push(Doc {
            rel: format!("{dir}/"),
            title: format!("One page per entry ({n} pages)"),
            status: "generated".to_owned(),
            owner: "-".to_owned(),
        });
    }
    out.sort_by(|a, b| a.rel.cmp(&b.rel));
    out
}

/// The index page text for `docs` and the non-markdown directories `others`.
fn render(docs: Vec<Doc>, others: &BTreeMap<String, usize>) -> String {
    let mut out = md_header("docs-index");
    out.push_str("\n# Documentation index\n\n");
    out.push_str(
        "This is the one index of every document under docs/. It lists each document with the status in its header.\n\n",
    );
    out.push_str(VOCABULARY);
    let mut sections: BTreeMap<String, Vec<Doc>> = BTreeMap::new();
    for d in collapse(docs) {
        sections
            .entry(section_of(d.rel.trim_end_matches('/')).to_owned())
            .or_default()
            .push(d);
    }
    for (section, rows) in &sections {
        let name = if section.is_empty() {
            "top level"
        } else {
            section
        };
        let _ = write!(
            out,
            "\n## {name}\n\n| Document | Title | Status | Owner |\n|---|---|---|---|\n"
        );
        for d in rows {
            let _ = writeln!(
                out,
                "| [{rel}]({rel}) | {} | {} | {} |",
                cell(&d.title),
                cell(&d.status),
                cell(&d.owner),
                rel = d.rel
            );
        }
    }
    if !others.is_empty() {
        out.push_str("\n## Supporting files\n\n");
        for (dir, n) in others {
            let dir = format!("{dir}/");
            let _ = writeln!(out, "- [{dir}]({dir}): {n} files that are not documents.");
        }
    }
    out
}

/// The index page under the standard generated marker, read from the `docs/` tree below `root`.
///
/// # Errors
/// [`DocsIndexError`] when the tree cannot be read.
pub fn generate(root: &Path) -> Result<Vec<GenFile>, DocsIndexError> {
    tracing::debug!(path = PATH, "rendering documentation index");
    let (docs, others) = collect(&root.join(DOCS_DIR))?;
    tracing::info!(documents = docs.len(), "indexed documents");
    Ok(vec![GenFile {
        path: PATH.to_owned(),
        content: render(docs, &others),
    }])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    // frob:tests crates/gob-dev/src/render/docs_index.rs::generate
    fn lists_each_document_with_its_status_under_a_valid_marker() {
        let dir = tempfile::tempdir().expect("tempdir");
        let docs = dir.path().join(DOCS_DIR).join("design");
        std::fs::create_dir_all(&docs).expect("mkdir");
        std::fs::write(docs.join("a.md"), "# Alpha\n\nStatus: draft\nOwner: frob\n").expect("a");
        std::fs::write(docs.join("b.md"), "# Beta\n\nno header\n").expect("b");
        let files = generate(dir.path()).expect("generate");
        assert_eq!(files.len(), 1);
        assert_eq!(files[0].path, PATH);
        let text = &files[0].content;
        assert!(text.contains("| Alpha | draft | frob |"), "{text}");
        assert!(text.contains("| Beta | invalid | - |"), "{text}");
        assert_eq!(crate::files::marker_problem(text), None);
    }

    #[test]
    // frob:tests crates/gob-dev/src/render/docs_index.rs::relative
    fn relative_uses_forward_slashes_even_for_backslash_separators() {
        let rel = relative(Path::new("docs"), Path::new("docs/crunk\\README.md"));
        assert_eq!(rel, "crunk/README.md");
        assert_eq!(dir_of(&rel), "crunk");
        assert_eq!(section_of(&rel), "crunk");
    }
}
