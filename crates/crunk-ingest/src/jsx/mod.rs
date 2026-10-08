//! JSX and TS sources for crunk: `style={{...}}` props and `className` class lists as
//! [`Declaration`]s and [`LocatedUtility`]s of a [`Bucket::Jsx`](crate::Bucket::Jsx) sheet.
//!
//! This is a thin mapping over the web engine (language-engines.md section 5): the TS adapter
//! folds JSX to `markup` elements and inline styles to `style` declarations, `class_tokens`
//! says whether a class value is fully static, and constants across files evaluate through
//! `ConstProject`. What is left here is what crunk adds: located, judgment-free facts in the
//! shape the rules read, with spans that address the source.
//!
//! - `style`: `style={{...}}` entries to declarations (never auto-fixed: see
//!   [`Stylesheet::is_fixable`](crate::Stylesheet::is_fixable)).
//! - `classes`: `className`/`class` attributes, `createElement`/`cloneElement` props and the
//!   class-string constants of plain `.ts` files.
//! - `ingest`: the project walk over `[jsx] globs`, with one cached result per source tree.
//!
//! # Known divergences from the Python crunk
//!
//! - Syntax errors read `jsx syntax error at line N`; Python carried tree-sitter's messages.
//! - A style key is the CSS spelling the adapter derives: `WebkitMask` is `-webkit-mask` and a
//!   custom property keeps its case (`--accentColor`); Python lowercased both.
//! - Numbers: React's full unitless list applies (`flex: 1` is no length); Python's covered
//!   seven properties, so it read `flex: 1` as `1px`.
//! - `style={{...} as CSSProperties}` and other wrapped objects are read; Python skipped them.
//! - A string value with an escape sequence keeps its whole raw text; Python kept the text up
//!   to the first escape.
//! - `createElement` identifiers resolve through the scope graph and the module graph
//!   (`ConstProject`): the visible constant wins, an ambiguous name no longer drops the site,
//!   and a constant from another file keeps its definition line only when it is in the same
//!   file (line 1 otherwise, as Python). A site that cannot be resolved is recorded in
//!   [`Stylesheet::dynamic_classes`](crate::Stylesheet); Python skipped it silently.
//! - `className` attributes with a part that is not statically known are recorded the same way.
//! - Callee recognition is by name (`createElement`, `cloneElement`, bare or on an object);
//!   Python classified by the resolved import when it had a module graph.
//! - The project's TS files (not only the `[jsx] globs` matches) feed constant resolution, and
//!   the whole result is cached by the digest of all of them; git-ignored files are skipped.

// frob:ticket 01M43ARYFVG86PAGGM78JGRZY3

mod classes;
mod cx;
mod literals;
mod project;
mod style;
mod tokens;

use gob_ir::Model;
use gob_symbols::{ConstProject, SymbolGraph, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};
use serde::{Deserialize, Serialize};

use crate::model::{Declaration, DynamicClass, LocatedUtility};
use crate::parse::FoldFailure;
use cx::Cx;

pub(crate) use project::ingest;

/// Everything read from one JSX or TS source; the cacheable unit.
#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
pub struct ParsedJsx {
    /// Inline-style declarations in source order (empty for a plain `.ts` file).
    pub declarations: Vec<Declaration>,
    /// Utility class tokens in source order.
    pub utilities: Vec<LocatedUtility>,
    /// Class sites with a part that is not statically known.
    pub dynamic_classes: Vec<DynamicClass>,
    /// Syntax errors, as messages.
    pub errors: Vec<String>,
}

/// True for a plain `.ts` file: it has no JSX, so only class-string constants are read.
fn is_plain_ts(path: &str) -> bool {
    std::path::Path::new(path)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("ts"))
}

/// Read the facts of `path`, whose folded form is in `project`.
///
/// # Panics
///
/// Never in practice: the caller adds `path` to `project` first.
pub(crate) fn parse_in_project(
    path: &str,
    source: &str,
    root_font_size: f64,
    project: &ConstProject<'_>,
) -> ParsedJsx {
    let model: &Model = project
        .model(path)
        .unwrap_or_else(|| unreachable!("{path} was added to the project before it is read"));
    let cx = Cx::new(model, source);
    let mut out = ParsedJsx::default();
    let mut found = classes::Found::default();
    if is_plain_ts(path) {
        classes::from_ts_constants(&cx, &mut found);
    } else {
        out.declarations = style::declarations(&cx, root_font_size);
        classes::from_attributes(&cx, &mut found);
    }
    classes::from_create_element(&cx, project, path, &mut found);
    out.utilities = found.utilities;
    out.dynamic_classes = found.dynamic;
    for id in model.term().ids() {
        if model.term().node(id).op().is_hole() {
            out.errors
                .push(format!("jsx syntax error at line {}", cx.line(id)));
        }
    }
    tracing::debug!(
        path,
        declarations = out.declarations.len(),
        utilities = out.utilities.len(),
        dynamic = out.dynamic_classes.len(),
        errors = out.errors.len(),
        "jsx: source read"
    );
    out
}

/// Parse one JSX or TS source in isolation: constants resolve within the file only.
///
/// `path` picks the grammar and mode (`.ts` reads class-string constants, anything else JSX).
/// Malformed source never fails: syntax errors become [`ParsedJsx::errors`].
///
/// # Errors
///
/// [`FoldFailure`] when the TS adapter builds an ill-formed term (an adapter bug).
pub fn parse_jsx_source(
    path: &str,
    source: &str,
    root_font_size: f64,
) -> Result<ParsedJsx, FoldFailure> {
    let entry = FileEntry {
        path: path.to_owned(),
        size: source.len() as u64,
        digest: Digest::of(source.as_bytes()),
        language: LanguageHint::from_path(path),
    };
    let folded = fold_file(&entry, source).map_err(|e| FoldFailure {
        path: path.to_owned(),
        detail: e.to_string(),
    })?;
    let graph = SymbolGraph::from_files(vec![folded.file.clone()]);
    let mut project = ConstProject::new(&graph);
    project.add_file(path, &folded);
    Ok(parse_in_project(path, source, root_font_size, &project))
}
