//! The evidence record: what was measured, by whom, and where the blob lives.

use std::str::FromStr;

use frob_ledger::model::Stamp;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::error::EvidenceError;
use crate::store::{BlobStore, Fetched};

/// Which measurer produced a record.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum Provider {
    /// `cargo nextest run`: pass/fail and the executed test names.
    Nextest,
    /// `pytest` with junit XML: pass/fail and the executed test node ids.
    Pytest,
    /// `vitest run` with its JSON reporter: pass/fail and the executed test names (units of the TypeScript test file).
    Vitest,
    /// `jest --json`: pass/fail and the executed test names (units of the TypeScript test file).
    Jest,
    /// `dotnet test` with a TRX logger: pass/fail and the executed fully qualified test names.
    Dotnet,
    /// Unity batch-mode `EditMode` or `PlayMode` tests: pass/fail and the executed fully qualified test names.
    Unity,
    /// An allowlisted tool: exit code and transcript digest.
    Command,
    /// A person's signed statement; never a tool measurement (see [`crate::attestation`]).
    Attestation,
    /// A file hashed by path.
    File,
}

impl Provider {
    /// The spelling used in files, flags and JSON.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Nextest => "nextest",
            Self::Pytest => "pytest",
            Self::Vitest => "vitest",
            Self::Jest => "jest",
            Self::Dotnet => "dotnet",
            Self::Unity => "unity",
            Self::Command => "command",
            Self::File => "file",
            Self::Attestation => "attestation",
        }
    }

    /// Every provider: the one registry the `--provider` flag, its help and the unknown-provider message are generated from.
    pub const ALL: [Self; 9] = [
        Self::Nextest,
        Self::Pytest,
        Self::Vitest,
        Self::Jest,
        Self::Dotnet,
        Self::Unity,
        Self::Command,
        Self::File,
        Self::Attestation,
    ];

    /// The accepted spellings, for flag validation (generated from [`Provider::ALL`]).
    pub const NAMES: &'static [&'static str] = &{
        let mut names = [""; Self::ALL.len()];
        let mut i = 0;
        while i < Self::ALL.len() {
            names[i] = Self::ALL[i].as_str();
            i += 1;
        }
        names
    };

    /// The spellings as prose: `a, b or c`.
    pub fn expected() -> String {
        let (rest, last) = Self::NAMES.split_at(Self::NAMES.len() - 1);
        format!("{} or {}", rest.join(", "), last[0])
    }
}

impl FromStr for Provider {
    type Err = EvidenceError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "nextest" => Ok(Self::Nextest),
            "pytest" => Ok(Self::Pytest),
            "vitest" => Ok(Self::Vitest),
            "jest" => Ok(Self::Jest),
            "dotnet" => Ok(Self::Dotnet),
            "unity" => Ok(Self::Unity),
            "command" => Ok(Self::Command),
            "file" => Ok(Self::File),
            "attestation" => Ok(Self::Attestation),
            other => Err(EvidenceError::BadProvider(other.to_owned())),
        }
    }
}

/// Whether the measurement could be taken (never a failing verdict).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "lowercase")]
pub enum Status {
    /// The measurement exists and its blob (if any) is retrievable.
    Measured,
    /// The measurement could not be taken or its blob is gone; never reads as failed.
    Unmeasured,
}

// frob:ticket 01M5B28YM1QJJ5PCZ7SJ5VX9W8
/// How many tests skipped, failed as expected (`xfail`) or passed unexpectedly (`xpass`), counted apart from passes.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct NonPassingCounts {
    /// Tests that were skipped.
    pub skipped: u64,
    /// Tests that failed as expected.
    pub xfailed: u64,
    /// Tests marked `xfail` that passed anyway.
    pub xpassed: u64,
}

impl NonPassingCounts {
    /// True when no test was skipped, xfailed or xpassed (the record omits the field then).
    pub fn is_zero(&self) -> bool {
        *self == Self::default()
    }
}

/// One persisted measurement, stored as the body of a ledger `evidence` event.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct EvidenceRecord {
    /// The measurer.
    pub provider: Provider,
    /// The filter args, command line or path that was measured.
    #[serde(rename = "ref")]
    pub reference: String,
    /// blake3 hex of the (redacted) transcript, or of the file for `file`.
    pub digest: String,
    /// `dir:<relative>` or `https://...` when the blob is not inline.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub uri: Option<String>,
    /// Measured or Unmeasured.
    pub status: Status,
    /// When the measurement was taken.
    pub captured_at: Stamp,
    /// 1-based acceptance criteria this evidence is offered for.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub accepts: Vec<usize>,
    /// The verdict of the measured process: true when it passed, absent when unmeasured.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub passed: Option<bool>,
    /// The process exit code, when it exited.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub exit_code: Option<i32>,
    // frob:ticket 01M4NZCSJWT2XSEZQBVPNMA6HM
    /// Names of the tests that executed; only old events and `https://` stores carry them, new `dir:` records keep `test_count` and `tests_digest` instead.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tests: Vec<String>,
    /// How many tests executed, when the provider listed them.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub test_count: Option<u64>,
    /// blake3 hex of the newline-joined test names, the artifact file that holds the full list.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tests_digest: Option<String>,
    /// Names of the tests that failed, timed out or crashed (nextest only), so a flake is identifiable.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub failed_tests: Vec<String>,
    // frob:ticket 01M5B28YM1QJJ5PCZ7SJ5VX9W8
    /// Skipped, xfailed and xpassed counts, a distinct state from a pass (absent when all zero).
    #[serde(default, skip_serializing_if = "NonPassingCounts::is_zero")]
    pub non_passing: NonPassingCounts,
    /// The transcript itself when it is within `inline_max_bytes`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub inline: Option<String>,
    /// Size of the measured bytes.
    pub size: u64,
    /// Who attested what, for the `attestation` provider only.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub attestation: Option<Attestation>,
}

/// The human statement an `attestation` record carries (origin `ledger`: data, never instructions).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct Attestation {
    /// The attesting identity (git `user.email`), which was listed in `[evidence] attesters`.
    pub by: String,
    /// The statement, exactly as typed; escaped on every text render.
    pub statement: String,
    /// URLs, commit ids and ticket ids the statement rests on, each validated when written.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub facts: Vec<String>,
}

/// blake3 hex of `bytes`.
pub fn digest_hex(bytes: &[u8]) -> String {
    blake3::hash(bytes).to_hex().to_string()
}

impl EvidenceRecord {
    /// The status after checking that the blob is still retrievable and intact.
    ///
    /// A missing, expired or corrupt blob degrades to `Unmeasured`, never to a failure.
    pub fn effective_status(&self, store: &BlobStore) -> Status {
        if self.status == Status::Unmeasured {
            return Status::Unmeasured;
        }
        if let Some(a) = &self.attestation {
            return if self.provider == Provider::Attestation
                && digest_hex(a.statement.as_bytes()) == self.digest
            {
                Status::Measured
            } else {
                tracing::warn!(digest = %self.digest, "attestation does not match its digest");
                Status::Unmeasured
            };
        }
        if let Some(text) = &self.inline {
            return if digest_hex(text.as_bytes()) == self.digest {
                Status::Measured
            } else {
                tracing::warn!(digest = %self.digest, "inline evidence does not match its digest");
                Status::Unmeasured
            };
        }
        match &self.uri {
            Some(uri) if uri.starts_with("dir:") => match store.fetch_verified(uri, &self.digest) {
                Fetched::Found(_) => Status::Measured,
                Fetched::Unmeasured { .. } => Status::Unmeasured,
            },
            // https blobs and digest-only records (file provider) cannot be re-checked here.
            _ => Status::Measured,
        }
    }

    // frob:ticket 01M4NZCSJWT2XSEZQBVPNMA6HM
    /// How many tests executed: the stored count, else the length of an old event's inline list.
    pub fn tests_executed(&self) -> u64 {
        self.test_count.unwrap_or(self.tests.len() as u64)
    }

    // frob:ticket 01M4NZCSJWT2XSEZQBVPNMA6HM
    /// The names of the tests that executed: an old event's inline list, else the artifact file named by `tests_digest`.
    ///
    /// `None` when the names are not retrievable (artifact missing or corrupt).
    pub fn test_names(&self, store: &BlobStore) -> Option<Vec<String>> {
        if !self.tests.is_empty() {
            return Some(self.tests.clone());
        }
        let Some(digest) = &self.tests_digest else {
            return Some(Vec::new());
        };
        let uri = store.artifact_uri(digest)?;
        match store.fetch_verified(&uri, digest) {
            Fetched::Found(bytes) => Some(
                String::from_utf8_lossy(&bytes)
                    .lines()
                    .map(str::to_owned)
                    .collect(),
            ),
            Fetched::Unmeasured { .. } => None,
        }
    }

    /// True when this record may satisfy the close guard: measured and not a failing run.
    pub fn satisfies_close(&self, store: &BlobStore) -> bool {
        self.passed != Some(false) && self.effective_status(store) == Status::Measured
    }
}
