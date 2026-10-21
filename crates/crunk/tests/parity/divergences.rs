//! `tests/crunk-parity/divergences.toml`: the reasoned list of differences from the Python crunk.

use serde::Deserialize;

use super::corpus::parity_root;

/// What a divergence says differs: the exit code, the stdout, or both.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Field {
    /// The process exit code.
    Exit,
    /// The (projected) standard output.
    Stdout,
}

/// One reasoned divergence covering one or more cases.
#[derive(Debug, Clone, Deserialize)]
pub struct Divergence {
    /// A short stable name; failures cite it.
    pub id: String,
    /// The `<project>/<name>` case ids it covers.
    pub cases: Vec<String>,
    /// The fields that differ for every covered case.
    pub fields: Vec<Field>,
    /// Why the Rust crunk is allowed to differ.
    pub reason: String,
}

#[derive(Deserialize)]
struct File {
    #[serde(default)]
    divergence: Vec<Divergence>,
}

/// Parse a divergence list from TOML text.
pub fn parse(text: &str) -> Result<Vec<Divergence>, toml::de::Error> {
    toml::from_str::<File>(text).map(|f| f.divergence)
}

/// The committed divergence list.
pub fn load() -> Vec<Divergence> {
    let path = parity_root().join("divergences.toml");
    let text =
        std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read divergences.toml: {e}"));
    parse(&text).unwrap_or_else(|e| panic!("parse divergences.toml: {e}"))
}
