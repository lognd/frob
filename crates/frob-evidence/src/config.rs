//! The `[evidence]` table of `frob.toml`.

use gob_config::ConfigTable;

/// Default `[evidence] store`: the local, non-authoritative artifact directory.
pub const DEFAULT_STORE: &str = "dir:.git/frob/artifacts";

/// How evidence is captured and where large blobs go.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "evidence", materialize)]
pub struct EvidenceTable {
    /// Programs the `command` provider may run (the first word of the command must be listed); the `pytest`, `vitest`, `jest` and `dotnet` providers need their own name listed too.
    #[config(default = vec!["cargo".to_owned(), "git".to_owned(), "pytest".to_owned(), "vitest".to_owned(), "jest".to_owned(), "dotnet".to_owned()])]
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
    /// Identities (git `user.email`) that may attest a criterion; `frob init` and `config sync` write the repository owner's email, and an empty list means nobody may.
    #[config(default = Vec::<String>::new(), enforcement)]
    pub attesters: Vec<String>,
    /// Value for `cargo nextest run --profile`; empty leaves nextest's own default.
    #[config(default = String::new())]
    pub nextest_profile: String,
}

// frob:ticket 01M44YQWY2SWCH7PS9F9W0WEA9
/// The `dotnet` evidence provider (`[evidence.dotnet]`).
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "evidence.dotnet", materialize)]
pub struct DotnetTable {
    /// Path of the `dotnet` executable the provider runs; empty finds `dotnet` on `PATH`.
    #[config(default = String::new())]
    pub path: String,
}

// frob:ticket 01M44YQZWPY9W2S61NW7TYPNJQ
/// The `unity` evidence provider (`[evidence.unity]`).
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "evidence.unity", materialize)]
pub struct UnityTable {
    /// Path of the Unity editor executable the provider runs, used whatever `ProjectSettings/ProjectVersion.txt` says; empty looks for the version that file names under Unity Hub's standard install locations.
    #[config(default = String::new())]
    pub editor: String,
}

// frob:ticket 01M4FDPNXX3X842GBA3FP0SDK3
/// How `frob test` and the `pytest` provider find the Python interpreter (`[tests]`).
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "tests", materialize)]
pub struct TestsTable {
    /// Interpreter that runs `-m pytest` (a name on `PATH` or a path, relative ones from the repository root); empty uses `.venv` in the repository root when it has one, else `pytest` on `PATH`.
    #[config(default = String::new())]
    pub python: String,
}
