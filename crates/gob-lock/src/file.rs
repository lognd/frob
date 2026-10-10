//! The lock file model, its TOML form and atomic persistence.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

/// The on-disk format version this crate writes (version 1 is still read, as all-REATTEST).
pub const LOCK_VERSION: u32 = 2;

/// The oldest file format version this crate can read.
const OLDEST_VERSION: u32 = 1;

/// The digest scheme a version-1 file is taken to use when it does not say (code-model.md 2).
const LEGACY_SCHEME: u32 = 1;

/// The digest scheme this build computes and expects in a current lock (the gob-ir scheme).
pub const DIGEST_SCHEME: u32 = gob_ir::DIGEST_SCHEME;

/// The lock file name of `product` (`frob` gives `frob.lock`).
pub fn file_name(product: &str) -> String {
    format!("{product}.lock")
}

/// Why a lock file could not be read, parsed or written.
#[derive(Debug, thiserror::Error)]
pub enum LockError {
    /// The file could not be read or written.
    #[error("E-LOCK-IO: {context} {path}: {source}")]
    Io {
        /// What was being attempted.
        context: &'static str,
        /// The file involved.
        path: PathBuf,
        /// The OS error.
        source: std::io::Error,
    },
    /// The file is not valid lock TOML.
    #[error("E-LOCK-PARSE: {path}: {message}")]
    Parse {
        /// The file (or `<memory>`).
        path: PathBuf,
        /// The parser message.
        message: String,
    },
    /// The file was written by a newer format version.
    #[error("E-LOCK-VERSION: {path} has version {found}, this build reads up to {LOCK_VERSION}")]
    Version {
        /// The file.
        path: PathBuf,
        /// The version found.
        found: u32,
    },
    // frob:ticket 01M4GK4M8KKRE7X7JCP6YJ5K96
    /// The file is a leftover frob v1 lock, a format this build never read.
    #[error(
        "E-LOCK-V1: {path} is a v1 frob.lock (frob v1 wrote it; this build reads version {OLDEST_VERSION} to {LOCK_VERSION}); delete it and run `frob ack --all` to regenerate"
    )]
    LegacyV1 {
        /// The file.
        path: PathBuf,
    },
    /// The in-memory lock could not be rendered as TOML (a bug).
    #[error("E-LOCK-RENDER: {0}")]
    Render(String),
}

/// A bound doc section and its digest at ack time.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LockTarget {
    /// The `path#slug` of the doc section.
    #[serde(rename = "ref")]
    pub target: String,
    /// Hex digest of that section when acknowledged.
    pub digest: String,
}

/// One acknowledged symbol (`[[symbol]]`); its map key in [`LockFile::entries`] is the symref.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LockEntry {
    /// The stable identity when it differs from the symref (`None`: the identity is the symref).
    pub identity: Option<String>,
    /// Hex digest of the signature facet.
    pub sig: String,
    /// Hex digest of the body facet.
    pub body: String,
    /// Hex digest of the doc-comment facet.
    pub doc: String,
    /// Hex digest of the attribute facet (empty: not recorded).
    pub attr: String,
    /// Hex digest of the language-neutral contract facet (empty: not recorded).
    pub contract: String,
    /// Who acknowledged (`Name <email>` or `unknown`).
    pub acked_by: String,
    /// When (RFC 3339, UTC).
    pub acked_at: String,
    /// Why, when the actor gave a reason.
    pub reason: Option<String>,
    /// Doc sections bound to the symbol, sorted by `target`.
    pub targets: Vec<LockTarget>,
}

impl LockEntry {
    /// An entry with sig, body and doc digests and the actor and time; attr and contract are empty.
    pub fn new(sig: &str, body: &str, doc: &str, acked_by: &str, acked_at: &str) -> Self {
        Self {
            identity: None,
            sig: sig.to_owned(),
            body: body.to_owned(),
            doc: doc.to_owned(),
            attr: String::new(),
            contract: String::new(),
            acked_by: acked_by.to_owned(),
            acked_at: acked_at.to_owned(),
            reason: None,
            targets: Vec::new(),
        }
    }

    /// The recorded digest of doc section `target`, if one was bound at ack time.
    pub fn target_digest(&self, target: &str) -> Option<&str> {
        self.targets
            .iter()
            .find(|t| t.target == target)
            .map(|t| t.digest.as_str())
    }
}

/// One end of a flow: the identity bound there and its Contract facet digest at ack time.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FlowEnd {
    /// The stable identity of the unit at this end.
    pub identity: String,
    /// Hex digest of its Contract facet (SYS006 compares the two ends of a flow over this).
    pub contract: String,
    /// Hex digest of the Contract facet of the flow's contract entity shape at ack time, when
    /// the flow names a contract whose one `shape` identity was Exact (binding.md 5.2 and 6.6).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub shape_contract: Option<String>,
}

/// What an [`AckLogEntry`] records.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AckLogKind {
    /// `ack --rename OLD NEW`: the entry of `subject` was re-keyed to `target`.
    Rename,
}

/// One append-only record of an ack decision that the entries themselves do not show.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AckLogEntry {
    /// What was decided.
    pub kind: AckLogKind,
    /// The anchor acted on (the old anchor of a rename).
    pub subject: String,
    /// The anchor it became (the new anchor of a rename).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub target: Option<String>,
    /// `Name <email>` or `unknown`.
    pub actor: String,
    /// When (RFC 3339, UTC).
    pub at: String,
    /// Why, as given to `--reason`.
    pub reason: String,
}

/// One acknowledged flow (`[[flow]]`); its map key in [`LockFile::flows`] is the flow key.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FlowEntry {
    /// The producing end.
    pub producer: FlowEnd,
    /// The consuming end.
    pub consumer: FlowEnd,
    /// Who acknowledged.
    pub acked_by: String,
    /// When (RFC 3339, UTC).
    pub acked_at: String,
    /// Why, when the actor gave a reason.
    pub reason: Option<String>,
}

/// Which kind of lock entry a re-attestation concerns.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum EntryKind {
    /// A `[[symbol]]` entry.
    Symbol,
    /// A `[[flow]]` entry.
    Flow,
}

/// One entry that must be re-attested because the file predates this build's format or scheme.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reattest {
    /// The symref or flow key.
    pub key: String,
    /// Symbol or flow.
    pub kind: EntryKind,
    /// The file format version the entry was read under.
    pub file_version: u32,
    /// The digest scheme the entry was recorded under.
    pub digest_scheme: u32,
}

impl Reattest {
    /// A one-line reason naming what differs from this build.
    pub fn why(&self) -> String {
        let mut parts = Vec::new();
        if self.file_version != LOCK_VERSION {
            parts.push(format!(
                "file version {} (this build writes {LOCK_VERSION})",
                self.file_version
            ));
        }
        if self.digest_scheme != DIGEST_SCHEME {
            parts.push(format!(
                "digest scheme {} (this build computes {DIGEST_SCHEME})",
                self.digest_scheme
            ));
        }
        parts.join(" and ")
    }
}

/// A whole lock file: header and typed entries keyed by symref string or flow key.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LockFile {
    /// Format version as read; [`LOCK_VERSION`] for any file this build wrote.
    pub version: u32,
    /// The digest scheme the entries were recorded under, separate from `version`.
    pub digest_scheme: u32,
    /// Symbol entries in symref order.
    pub entries: BTreeMap<String, LockEntry>,
    /// Flow entries in flow-key order.
    pub flows: BTreeMap<String, FlowEntry>,
    /// The rename chain: old symref to the symref its entry was re-keyed to (`ack --rename`).
    pub renamed: BTreeMap<String, String>,
    /// The append-only ack log (`[[ack_log]]`): decisions such as renames, oldest first.
    pub ack_log: Vec<AckLogEntry>,
}

impl Default for LockFile {
    fn default() -> Self {
        Self {
            version: LOCK_VERSION,
            digest_scheme: DIGEST_SCHEME,
            entries: BTreeMap::new(),
            flows: BTreeMap::new(),
            renamed: BTreeMap::new(),
            ack_log: Vec::new(),
        }
    }
}

/// The version-1 entry shape (`[entries."<symref>"]`, three facets).
#[derive(Deserialize)]
struct RowV1 {
    sig: String,
    body: String,
    doc: String,
    acked_by: String,
    acked_at: String,
    #[serde(default)]
    reason: Option<String>,
    #[serde(default)]
    targets: Vec<LockTarget>,
}

/// The version-1 file shape.
#[derive(Deserialize)]
struct FileV1 {
    #[serde(default = "legacy_scheme")]
    digest_scheme: u32,
    #[serde(default)]
    entries: BTreeMap<String, RowV1>,
}

const fn legacy_scheme() -> u32 {
    LEGACY_SCHEME
}

/// Just the version, read first to choose the file shape.
#[derive(Deserialize)]
struct Header {
    version: u32,
}

/// One `[[symbol]]` table on disk.
#[derive(Serialize, Deserialize)]
struct SymbolRow {
    identity: String,
    symref: String,
    sig: String,
    body: String,
    doc: String,
    attr: String,
    contract: String,
    acked_by: String,
    acked_at: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    reason: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    targets: Vec<LockTarget>,
}

/// One `[[flow]]` table on disk.
#[derive(Serialize, Deserialize)]
struct FlowRow {
    key: String,
    producer: FlowEnd,
    consumer: FlowEnd,
    acked_by: String,
    acked_at: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    reason: Option<String>,
}

/// The version-2 file shape.
#[derive(Serialize, Deserialize)]
struct FileV2 {
    version: u32,
    digest_scheme: u32,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    symbol: Vec<SymbolRow>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    flow: Vec<FlowRow>,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    renamed: BTreeMap<String, String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    ack_log: Vec<AckLogEntry>,
}

impl LockFile {
    fn from_v1(v1: FileV1) -> Self {
        let entries = v1
            .entries
            .into_iter()
            .map(|(k, r)| {
                let mut e = LockEntry::new(&r.sig, &r.body, &r.doc, &r.acked_by, &r.acked_at);
                e.reason = r.reason;
                e.targets = r.targets;
                (k, e)
            })
            .collect();
        Self {
            version: 1,
            digest_scheme: v1.digest_scheme,
            entries,
            flows: BTreeMap::new(),
            renamed: BTreeMap::new(),
            ack_log: Vec::new(),
        }
    }

    fn from_v2(v2: FileV2, origin: &Path) -> Result<Self, LockError> {
        let dup = |what: &str, key: &str| LockError::Parse {
            path: origin.to_path_buf(),
            message: format!("duplicate {what} entry `{key}`"),
        };
        let mut lock = Self {
            version: v2.version,
            digest_scheme: v2.digest_scheme,
            entries: BTreeMap::new(),
            flows: BTreeMap::new(),
            renamed: v2.renamed,
            ack_log: v2.ack_log,
        };
        for r in v2.symbol {
            let e = LockEntry {
                identity: (r.identity != r.symref).then_some(r.identity),
                sig: r.sig,
                body: r.body,
                doc: r.doc,
                attr: r.attr,
                contract: r.contract,
                acked_by: r.acked_by,
                acked_at: r.acked_at,
                reason: r.reason,
                targets: r.targets,
            };
            if lock.entries.insert(r.symref.clone(), e).is_some() {
                return Err(dup("symbol", &r.symref));
            }
        }
        for r in v2.flow {
            let e = FlowEntry {
                producer: r.producer,
                consumer: r.consumer,
                acked_by: r.acked_by,
                acked_at: r.acked_at,
                reason: r.reason,
            };
            if lock.flows.insert(r.key.clone(), e).is_some() {
                return Err(dup("flow", &r.key));
            }
        }
        Ok(lock)
    }

    fn to_v2(&self) -> FileV2 {
        FileV2 {
            version: self.version,
            digest_scheme: self.digest_scheme,
            symbol: self
                .entries
                .iter()
                .map(|(k, e)| SymbolRow {
                    identity: e.identity.clone().unwrap_or_else(|| k.clone()),
                    symref: k.clone(),
                    sig: e.sig.clone(),
                    body: e.body.clone(),
                    doc: e.doc.clone(),
                    attr: e.attr.clone(),
                    contract: e.contract.clone(),
                    acked_by: e.acked_by.clone(),
                    acked_at: e.acked_at.clone(),
                    reason: e.reason.clone(),
                    targets: e.targets.clone(),
                })
                .collect(),
            flow: self
                .flows
                .iter()
                .map(|(k, e)| FlowRow {
                    key: k.clone(),
                    producer: e.producer.clone(),
                    consumer: e.consumer.clone(),
                    acked_by: e.acked_by.clone(),
                    acked_at: e.acked_at.clone(),
                    reason: e.reason.clone(),
                })
                .collect(),
            renamed: self.renamed.clone(),
            ack_log: self.ack_log.clone(),
        }
    }

    // frob:ticket 01M3Z714820D1SK6X44T9R1B70
    /// Re-keys the symbol entry `old` to `new` keeping every digest, retargets flow ends that
    /// named `old`, and records `old -> new` in the rename chain.
    ///
    /// Returns false (changing nothing) when there is no entry for `old` or one already exists
    /// for `new`.
    pub fn rename(&mut self, old: &str, new: &str) -> bool {
        if self.entries.contains_key(new) {
            return false;
        }
        let Some(entry) = self.entries.remove(old) else {
            return false;
        };
        self.entries.insert(new.to_owned(), entry);
        for flow in self.flows.values_mut() {
            for end in [&mut flow.producer, &mut flow.consumer] {
                if end.identity == old {
                    new.clone_into(&mut end.identity);
                }
            }
        }
        // Chains collapse: anything that pointed at `old` now points at `new`.
        for target in self.renamed.values_mut() {
            if target == old {
                new.clone_into(target);
            }
        }
        self.renamed.insert(old.to_owned(), new.to_owned());
        tracing::info!(old, new, "lock entry re-keyed by rename");
        true
    }

    /// Appends a `rename` record to the ack log: who re-keyed `old` to `new`, when and why.
    pub fn log_rename(&mut self, old: &str, new: &str, actor: &str, at: &str, reason: &str) {
        self.ack_log.push(AckLogEntry {
            kind: AckLogKind::Rename,
            subject: old.to_owned(),
            target: Some(new.to_owned()),
            actor: actor.to_owned(),
            at: at.to_owned(),
            reason: reason.to_owned(),
        });
        tracing::info!(old, new, actor, "rename recorded in the ack log");
    }

    /// True when the file was written under another format version or digest scheme than this build's.
    pub const fn is_stale(&self) -> bool {
        self.version != LOCK_VERSION || self.digest_scheme != DIGEST_SCHEME
    }

    /// Every entry needing re-attestation: all of them when [`LockFile::is_stale`], else none.
    ///
    /// Nothing is silently accepted: callers turn each item into a finding (DRIFT004).
    pub fn reattest(&self) -> Vec<Reattest> {
        if !self.is_stale() {
            return Vec::new();
        }
        let entry = |key: &String, kind| Reattest {
            key: key.clone(),
            kind,
            file_version: self.version,
            digest_scheme: self.digest_scheme,
        };
        let out: Vec<Reattest> = self
            .entries
            .keys()
            .map(|k| entry(k, EntryKind::Symbol))
            .chain(self.flows.keys().map(|k| entry(k, EntryKind::Flow)))
            .collect();
        tracing::warn!(
            entries = out.len(),
            version = self.version,
            digest_scheme = self.digest_scheme,
            "lock predates this build: every entry needs re-attestation"
        );
        out
    }

    /// Stamps the header as current without touching any digest; the only caller is the ack planner.
    pub(crate) fn adopt_current_header(&mut self) {
        self.version = LOCK_VERSION;
        self.digest_scheme = DIGEST_SCHEME;
    }

    /// Parses lock TOML; `origin` names the file in errors.
    ///
    /// A version-1 file loads with its entries intact and `version = 1`, so
    /// [`LockFile::reattest`] lists all of them.
    ///
    /// # Errors
    ///
    /// [`LockError::Parse`] for malformed TOML, [`LockError::Version`] for a newer format,
    /// [`LockError::LegacyV1`] for a lock frob v1 wrote (JSON, or TOML with no `version`).
    pub fn parse(text: &str, origin: &Path) -> Result<Self, LockError> {
        let parse_err = |e: toml::de::Error| LockError::Parse {
            path: origin.to_path_buf(),
            message: e.to_string(),
        };
        // frob:ticket 01M4GK4M8KKRE7X7JCP6YJ5K96
        let legacy = || LockError::LegacyV1 {
            path: origin.to_path_buf(),
        };
        if text.trim_start().starts_with('{') {
            return Err(legacy());
        }
        let header: Header = match toml::from_str(text) {
            Ok(h) => h,
            Err(_)
                if toml::from_str::<toml::Table>(text)
                    .is_ok_and(|t| !t.contains_key("version")) =>
            {
                return Err(legacy());
            }
            Err(e) => return Err(parse_err(e)),
        };
        match header.version {
            v if v > LOCK_VERSION => Err(LockError::Version {
                path: origin.to_path_buf(),
                found: v,
            }),
            v if v < OLDEST_VERSION => Err(legacy()),
            1 => Ok(Self::from_v1(toml::from_str(text).map_err(parse_err)?)),
            _ => Self::from_v2(toml::from_str(text).map_err(parse_err)?, origin),
        }
    }

    /// Parses lock TOML held in memory.
    ///
    /// # Errors
    ///
    /// As [`LockFile::parse`].
    pub fn from_toml(text: &str) -> Result<Self, LockError> {
        Self::parse(text, Path::new("<memory>"))
    }

    /// Renders stable TOML: sorted entries, trailing newline.
    ///
    /// # Errors
    ///
    /// [`LockError::Render`] if serialization fails (a bug) or the lock is a not-yet-migrated older version.
    pub fn to_toml(&self) -> Result<String, LockError> {
        if self.version != LOCK_VERSION {
            return Err(LockError::Render(format!(
                "lock is version {}; it can only be written after migration to {LOCK_VERSION}",
                self.version
            )));
        }
        let mut text =
            toml::to_string(&self.to_v2()).map_err(|e| LockError::Render(e.to_string()))?;
        if !text.ends_with('\n') {
            text.push('\n');
        }
        Ok(text)
    }

    /// Reads `path`; a missing file is an empty lock, not an error.
    ///
    /// # Errors
    ///
    /// [`LockError::Io`] for read failures other than not-found, plus parse errors.
    pub fn load(path: &Path) -> Result<Self, LockError> {
        match std::fs::read_to_string(path) {
            Ok(text) => {
                let lock = Self::parse(&text, path)?;
                tracing::debug!(path = %path.display(), entries = lock.entries.len(), "lock loaded");
                Ok(lock)
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                tracing::debug!(path = %path.display(), "no lock file; empty lock");
                Ok(Self::default())
            }
            Err(source) => Err(LockError::Io {
                context: "read",
                path: path.to_path_buf(),
                source,
            }),
        }
    }

    /// Writes `path` atomically (sibling temp file, then rename).
    ///
    /// # Errors
    ///
    /// [`LockError::Io`] when the temp file cannot be written or renamed, plus render errors.
    pub fn save(&self, path: &Path) -> Result<(), LockError> {
        let text = self.to_toml()?;
        gob_fs::write_atomic(path, text.as_bytes()).map_err(|source| LockError::Io {
            context: "write",
            path: path.to_path_buf(),
            source,
        })?;
        tracing::info!(path = %path.display(), entries = self.entries.len(), "lock saved");
        Ok(())
    }
}
