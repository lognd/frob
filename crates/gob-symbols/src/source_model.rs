//! One example's source text and language to the [`gob_ir::Model`] the executor reads.

// frob:ticket 01M4MC43CFCTQ7TQCHCF0C0YRR

use gob_ir::Model;
use gob_walk::{Digest, FileEntry, LanguageHint};

use crate::adapter::FoldError;
use crate::pipeline::fold_file;

/// The file extension that selects the adapter for a language tag (`rust` -> `rs`).
///
/// Unknown tags are taken as an extension themselves, so `json` reaches the opaque adapter.
fn extension_of_tag(tag: &str) -> String {
    let tag = tag.trim_start_matches('.').to_ascii_lowercase();
    match tag.as_str() {
        "rust" => "rs",
        "python" => "py",
        "markdown" => "md",
        "typescript" => "ts",
        "javascript" => "js",
        "csharp" | "c#" => "cs",
        "yaml" => "yml",
        other => other,
    }
    .to_owned()
}

/// Builds the [`Model`] of `text` read as `language` (a tag such as `rust`, or an extension).
///
/// The artifact is named `example.<ext>`. Source that does not parse still yields a Model: its
/// bad regions are `hole` nodes, and a language with no adapter folds to one `opaque` node, so a
/// broken example is judged by the rule instead of failing the run.
///
/// # Errors
///
/// [`FoldError`] only when an adapter builds an ill-formed term (an adapter bug).
pub fn model_of_source(language: &str, text: &str) -> Result<Model, FoldError> {
    let path = format!("example.{}", extension_of_tag(language));
    model_of_source_at(&path, text)
}

/// Builds the [`Model`] of `text` as the file `path`; the extension picks the adapter.
///
/// Like [`model_of_source`] but the artifact keeps the caller's repository path, so a rule that
/// reads `file.path` sees the path an example named.
///
/// # Errors
///
/// [`FoldError`] only when an adapter builds an ill-formed term (an adapter bug).
pub fn model_of_source_at(path: &str, text: &str) -> Result<Model, FoldError> {
    let entry = FileEntry {
        language: LanguageHint::from_path(path),
        digest: Digest::of(text.as_bytes()),
        size: text.len() as u64,
        path: path.to_owned(),
    };
    tracing::debug!(path = %entry.path, bytes = text.len(), "building example model");
    let folded = fold_file(&entry, text)?;
    Ok(Model::new(folded.term, folded.scopes))
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_text::SourceText;

    /// Lines (1-based) of every node whose operator satisfies `pick`.
    fn lines_where(
        model: &Model,
        text: &str,
        pick: impl Fn(&gob_ir::Operator) -> bool,
    ) -> Vec<u32> {
        let source = SourceText::new(text).expect("source fits");
        let term = model.term();
        term.ids()
            .filter(|id| pick(term.node(*id).op()))
            .filter_map(|id| term.node(id).location().span())
            .filter_map(|s| source.line_col(s.range.start()))
            .map(|lc| lc.line)
            .collect()
    }

    // frob:tests crates/gob-symbols/src/source_model.rs::model_of_source
    #[test]
    fn rust_source_has_a_function_and_a_call_on_line_three() {
        let text = "fn f(x: u32) -> u32 {\n    let y = 1;\n    g(x)\n}\n";
        let model = model_of_source("rust", text).expect("model");
        let fns = lines_where(&model, text, |op| op.tag() == "unit");
        assert!(!fns.is_empty(), "a function unit node");
        let calls = lines_where(&model, text, |op| op.tag() == "apply");
        assert!(calls.contains(&3), "an apply node on line 3: {calls:?}");
    }

    // frob:tests crates/gob-symbols/src/source_model.rs::model_of_source
    #[test]
    fn a_syntax_error_yields_a_model_with_an_unread_node() {
        let model = model_of_source("rust", "fn f( { let = ;\n").expect("model, not an error");
        let term = model.term();
        assert!(
            term.ids()
                .any(|id| term.node(id).op().is_hole() || term.node(id).op().is_opaque()),
            "a hole or opaque node marks the unread region"
        );
    }

    // frob:tests crates/gob-symbols/src/source_model.rs::model_of_source
    #[test]
    fn a_language_without_an_adapter_folds_to_an_opaque_node() {
        let model = model_of_source("json", "{\"a\": 1}").expect("model");
        let term = model.term();
        assert!(term.ids().any(|id| term.node(id).op().is_opaque()));
    }

    // frob:tests crates/gob-symbols/src/source_model.rs::model_of_source_at
    #[test]
    fn the_artifact_keeps_the_path_it_was_given() {
        let model = model_of_source_at("src/core/a.py", "import requests\n").expect("model");
        assert_eq!(model.term().locator(), "src/core/a.py");
    }
}
