//! The hook that reads an example's `model` text, so gob-plan never links a model parser.
//!
//! The `.grmb` parser lives in a higher layer (`grimble-model`); the product that has it installs
//! a [`ModelReader`] at startup, as `gob_git::install_content_backend` does for content.

// frob:ticket 01M5FRCMBS9DHQ223JWGN6RNW7
use std::sync::OnceLock;

/// One model node an example `model` declares: its dotted name, kind and `owns` selectors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ModelNodeRow {
    /// The node name, namespaces joined with `.`.
    pub name: String,
    /// The node kind (`component` when it declares none).
    pub kind: String,
    /// The path the node was read from.
    pub path: String,
    /// The `owns` selectors of the node.
    pub selectors: Vec<String>,
    /// The atoms the node grants everywhere with `may` (for example `net.listen`); a `may ... at`
    /// grant covers only part of the node's code and is not listed.
    pub grants: Vec<String>,
    /// The atoms the node excuses with `excuses ATOM because="..."`.
    pub excuses: Vec<String>,
}

/// Reads an example's `model` text into node rows; the error is a one-line refusal reason.
pub type ModelReader = fn(&str) -> Result<Vec<ModelNodeRow>, String>;

static READER: OnceLock<ModelReader> = OnceLock::new();

/// Installs the process-wide model reader; call once at startup. Returns false when one was
/// already installed (the first stays).
pub fn install_model_reader(reader: ModelReader) -> bool {
    let fresh = READER.set(reader).is_ok();
    tracing::debug!(fresh, "example model reader installed");
    fresh
}

/// Reads `text` through the installed reader.
///
/// # Errors
/// The reader's refusal, or a note that no reader is installed.
pub(crate) fn read_model(text: &str) -> Result<Vec<ModelNodeRow>, String> {
    let Some(reader) = READER.get() else {
        tracing::warn!("example model text with no model reader installed");
        return Err("no model reader is installed in this product".to_owned());
    };
    reader(text)
}
