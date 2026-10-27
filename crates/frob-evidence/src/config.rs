//! The `[evidence]` table of `frob.toml`.

use std::path::Path;

use gob_config::{ConfigError, ConfigTable};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

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
    // frob:ticket 01M5B4R6YPM1D0A41AX7MRCHXP
    /// Per-tool report field for the `command` provider: tool name to the dotted path of the executed-test count in the JSON the tool prints on stdout (for example `jest = "numTotalTests"`); a listed tool that ran no test is refused, an unlisted tool is UNMEASURED for granular evidence (exit code only).
    #[config(default = std::collections::BTreeMap::new())]
    pub report_fields: std::collections::BTreeMap<String, String>,
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
    // frob:ticket 01M5B28YM1QJJ5PCZ7SJ5VX9W8
    /// Non-passing pytest outcomes (`skipped`, `xfailed`, `xpassed`) that count as executed tests and so may satisfy evidence; empty (the default) lets none, and they are counted apart either way.
    #[config(default = Vec::<String>::new())]
    pub non_passing_counts: Vec<String>,
}

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// One coverage minimum: the files matching `scope` must reach `line` and `branch` percent.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CoverageThreshold {
    /// A path glob over the covered files, or a directory prefix (no glob characters).
    pub scope: String,
    /// Minimum line coverage in percent (0 to 100); omit to leave lines unchecked.
    #[serde(default)]
    pub line: Option<f64>,
    /// Minimum branch coverage in percent (0 to 100); omit to leave branches unchecked.
    #[serde(default)]
    pub branch: Option<f64>,
}

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q
/// Coverage minimums per scope, measured from an lcov report (COV004), and whether a tested language must have measured coverage.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "coverage", materialize)]
pub struct CoverageConfig {
    /// The merged lcov report COV004 reads, relative to the repository root; `--coverage` evidence capture writes it.
    #[config(default = "lcov.info".to_owned())]
    pub report: String,
    /// Minimums per scope, written as `[[coverage.threshold]]` entries.
    #[config(default = Vec::new())]
    pub threshold: Vec<CoverageThreshold>,
    /// When true, a language that has tests but no coverage report is a COV004 finding (a missing coverage tool is reported as not run instead).
    #[config(default = true, enforcement)]
    pub require_reports: bool,
}

impl CoverageConfig {
    /// Load `[coverage]` from `<root>/frob.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, crate::workspace::PRODUCT)?.value)
    }
}
