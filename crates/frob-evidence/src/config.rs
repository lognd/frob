//! The `[evidence]` table of `frob.toml`.

use gob_config::ConfigTable;

/// Default `[evidence] store`: the local, non-authoritative artifact directory.
pub const DEFAULT_STORE: &str = "dir:.git/frob/artifacts";

/// How evidence is captured and where large blobs go.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "evidence")]
pub struct EvidenceTable {
    /// Programs the `command` provider may run (the first word of the command must be listed).
    #[config(default = vec!["cargo".to_owned(), "git".to_owned()])]
    pub allowed_tools: Vec<String>,
    /// Transcripts up to this many bytes are stored inline in the event file.
    #[config(default = 16_384)]
    pub inline_max_bytes: u64,
    /// Blob store: `dir:<path>` (relative paths start at the repository root, `.git/` at the common dir) or an `https://` URL (recorded only).
    #[config(default = crate::config::DEFAULT_STORE.to_owned())]
    pub store: String,
    /// Wall-clock limit in seconds for one provider process.
    #[config(default = 1800)]
    pub timeout_secs: u64,
    /// Value for `cargo nextest run --profile`; empty leaves nextest's own default.
    #[config(default = String::new())]
    pub nextest_profile: String,
}
