//! Gathering the human review lock's inputs (crunk.md 4.1): which screen states need a review,
//! the digest of every input each depends on, the recorded `[[review]]` entries and the
//! introducing commit's signature. The judgment itself is `crunk_rules::review::judge`.

// frob:ticket 01M4CXSM408E7A05DWKENDB7V4

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::time::Duration;

use crunk_rules::review::{AckSignature, ReviewFacts, Subject, judge};
use crunk_spec::DesignSpec;
use crunk_spec::table::{Provenance, ReviewRequirement, ScreenConfig};
use crunk_tokens::TokenSet;
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_lock::{LockFile, ReviewEntry, ReviewVerdict};

/// The lock file this product keeps its reviews in.
pub fn lock_path(root: &Path) -> PathBuf {
    root.join(gob_lock::file_name(crate::PRODUCT))
}

/// Where the signature of the commit that introduced an ack comes from.
pub trait SignatureSource {
    /// The signature of the first commit that put `digest` into `crunk.lock`.
    fn signature(&self, digest: &str) -> AckSignature;
}

/// [`SignatureSource`] over `git log -S`.
#[derive(Debug, Clone)]
pub struct GitSignatures {
    root: PathBuf,
}

impl GitSignatures {
    /// Signatures read from the git repository at `root`.
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
        }
    }
}

impl SignatureSource for GitSignatures {
    fn signature(&self, digest: &str) -> AckSignature {
        let spec = Spec {
            program: Program::Git,
            args: vec![
                "log".to_owned(),
                "--reverse".to_owned(),
                "--format=%G?%x1f%GF%x1f%GK".to_owned(),
                format!("-S{digest}"),
                "--".to_owned(),
                gob_lock::file_name(crate::PRODUCT),
            ],
            cwd: Some(self.root.clone()),
            env: Vec::new(),
            timeout: Duration::from_secs(30),
            capture: true,
        };
        let out = match Runner::new(Limits { jobs: 1 }).run(&spec) {
            Ok(out) if out.status == Outcome::Exited(0) => out,
            Ok(out) => {
                tracing::warn!(status = ?out.status, "git log for ack signature failed");
                return AckSignature::Unsigned(
                    "the ack is not committed yet, or git could not read the history".to_owned(),
                );
            }
            Err(err) => {
                tracing::warn!(%err, "git log for ack signature did not run");
                return AckSignature::Unsigned(format!("git did not run: {err}"));
            }
        };
        let Some(line) = out.stdout_raw.lines().next() else {
            return AckSignature::Unsigned("the ack is not committed yet".to_owned());
        };
        parse_signature(line)
    }
}

/// Read one `%G?%x1f%GF%x1f%GK` line: good (`G`) or good-with-unknown-validity (`U`) is a signature.
pub fn parse_signature(line: &str) -> AckSignature {
    let mut parts = line.split('\u{1f}');
    let status = parts.next().unwrap_or("N");
    let fingerprint = parts.next().unwrap_or("");
    let key = parts.next().unwrap_or("");
    match status {
        "G" | "U" => AckSignature::Good(
            if fingerprint.is_empty() {
                key
            } else {
                fingerprint
            }
            .to_owned(),
        ),
        "N" => AckSignature::Unsigned("the commit is not signed".to_owned()),
        other => {
            AckSignature::Unsigned(format!("the commit signature is not good (status {other})"))
        }
    }
}

/// 32 hex chars of the blake3 of `bytes`.
fn hex(bytes: &[u8]) -> String {
    blake3::hash(bytes).to_hex()[..32].to_owned()
}

/// True when `screen` needs a recorded human review.
pub fn needs_review(screen: &ScreenConfig) -> bool {
    match screen.review {
        Some(ReviewRequirement::Human) => true,
        Some(ReviewRequirement::Skip) => false,
        None => screen.provenance == Some(Provenance::Agent),
    }
}

/// Every file under `root/rel` (a file itself, or a directory walked in name order).
#[allow(
    clippy::disallowed_methods,
    reason = "screen sources are declared by the spec and may lie outside the walk"
)]
fn source_files(root: &Path, rel: &str) -> Vec<PathBuf> {
    fn walk(dir: &Path, out: &mut Vec<PathBuf>) {
        let Ok(read) = std::fs::read_dir(dir) else {
            return;
        };
        let mut paths: Vec<PathBuf> = read.filter_map(Result::ok).map(|e| e.path()).collect();
        paths.sort();
        for p in paths {
            let name = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
            if name.starts_with('.') || name == "node_modules" || name == "target" {
                continue;
            }
            if p.is_dir() {
                // frob:ticket 01M5MDT81QR8F0E67N61AYZDN2
                if gob_walk::is_generated_dir(&p) {
                    tracing::debug!(dir = ?p, "review: generated report directory skipped");
                    continue;
                }
                walk(&p, out);
            } else {
                out.push(p);
            }
        }
    }
    let path = root.join(rel);
    let mut out = Vec::new();
    if path.is_dir() {
        walk(&path, &mut out);
    } else if path.is_file() {
        out.push(path);
    }
    out
}

/// True when `text` mentions the custom property `name` as a whole identifier.
fn mentions(text: &str, name: &str) -> bool {
    text.match_indices(name).any(|(i, _)| {
        !text[i + name.len()..]
            .chars()
            .next()
            .is_some_and(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
    })
}

/// Platform ids a screen applies to, as input digests (`applies_to` ids and `tag:` entries).
fn platform_inputs(
    spec: &DesignSpec,
    screen: &ScreenConfig,
    inputs: &mut BTreeMap<String, String>,
) {
    for (id, platform) in &spec.platforms {
        let applies = screen.applies_to.as_ref().is_none_or(|list| {
            list.iter().any(|e| {
                e == id
                    || e.strip_prefix("tag:")
                        .is_some_and(|t| platform.tags.iter().any(|pt| pt == t))
            })
        });
        if applies {
            let json = serde_json::to_vec(platform).unwrap_or_default();
            inputs.insert(format!("spec:platform/{id}"), hex(&json));
        }
    }
}

/// The reviewable subjects of `spec`: one per state of each screen that needs a review.
///
/// # Errors
/// The token set could not be built (colliding token names); the message says why.
#[allow(
    clippy::disallowed_methods,
    reason = "screen sources and rendered pngs are spec-declared paths outside the walk"
)]
pub fn subjects(spec: &DesignSpec) -> Result<Vec<Subject>, String> {
    let screens: Vec<&ScreenConfig> = spec.screens.values().filter(|s| needs_review(s)).collect();
    if screens.is_empty() {
        return Ok(Vec::new());
    }
    let tokens =
        TokenSet::from_spec(spec).map_err(|e| format!("the token set cannot be built: {e}"))?;
    let fonts = hex(&serde_json::to_vec(&spec.typography).unwrap_or_default());
    let mut out = Vec::new();
    for screen in screens {
        let mut shared: BTreeMap<String, String> = BTreeMap::new();
        shared.insert(
            "spec:screen".to_owned(),
            hex(&serde_json::to_vec(&ScreenHeader::of(screen)).unwrap_or_default()),
        );
        platform_inputs(spec, screen, &mut shared);
        shared.insert("font:typography".to_owned(), fonts.clone());
        let mut text = String::new();
        let declared = screen.sources.as_ref();
        for rel in declared.into_iter().flatten() {
            for file in source_files(&spec.root, rel) {
                let bytes = std::fs::read(&file).unwrap_or_default();
                let shown =
                    gob_path::forward_slashes(file.strip_prefix(&spec.root).unwrap_or(&file));
                shared.insert(format!("source:{shown}"), hex(&bytes));
                text.push_str(&String::from_utf8_lossy(&bytes));
                text.push('\n');
            }
        }
        for token in tokens.iter() {
            if declared.is_some() && !mentions(&text, &token.name) {
                continue;
            }
            let mut canon = format!(
                "{:?}",
                token
                    .value
                    .css()
                    .unwrap_or_else(|| format!("{:?}", token.value))
            );
            for (mode, value) in &token.modes {
                let _ = write!(
                    canon,
                    "|{mode}={:?}",
                    value.css().unwrap_or_else(|| format!("{value:?}"))
                );
            }
            shared.insert(format!("token:{}", token.name), hex(canon.as_bytes()));
        }
        for state in &screen.states {
            let mut inputs = shared.clone();
            inputs.insert(
                "spec:state".to_owned(),
                hex(&serde_json::to_vec(state).unwrap_or_default()),
            );
            let render = spec
                .root
                .join(".crunk/render")
                .join(&screen.id)
                .join(format!("{}.png", state.id));
            if let Ok(bytes) = std::fs::read(&render) {
                inputs.insert("render".to_owned(), hex(&bytes));
            }
            out.push(Subject {
                id: format!("screen/{}/{}", screen.id, state.id),
                screen: screen.id.clone(),
                inputs,
            });
        }
    }
    tracing::debug!(subjects = out.len(), "review subjects built");
    Ok(out)
}

/// The screen's own fields minus its states (each state is its own subject).
#[derive(serde::Serialize)]
struct ScreenHeader<'a> {
    id: &'a str,
    entry: &'a str,
    applies_to: &'a Option<Vec<String>>,
}

impl<'a> ScreenHeader<'a> {
    fn of(s: &'a ScreenConfig) -> Self {
        Self {
            id: &s.id,
            entry: &s.entry,
            applies_to: &s.applies_to,
        }
    }
}

/// Judge every reviewable subject of `spec` against `<root>/crunk.lock`.
pub fn gather(spec: &DesignSpec, signatures: &dyn SignatureSource) -> ReviewFacts {
    let subjects = match subjects(spec) {
        Ok(s) => s,
        Err(why) => {
            tracing::warn!(%why, "review subjects cannot be built");
            return ReviewFacts {
                findings: Vec::new(),
                unreadable: Some(why),
            };
        }
    };
    if subjects.is_empty() {
        return ReviewFacts::default();
    }
    let lock = match LockFile::load(&lock_path(&spec.root)) {
        Ok(lock) => lock,
        Err(err) => {
            tracing::warn!(%err, "crunk.lock cannot be read");
            return ReviewFacts {
                findings: Vec::new(),
                unreadable: Some(err.to_string()),
            };
        }
    };
    let findings = subjects
        .iter()
        .map(|subject| {
            let entry = lock.reviews.get(&subject.id);
            let signature = (spec.review.require_signed)
                .then(|| entry.filter(|e| e.digest == subject.digest()))
                .flatten()
                .map(|e| signatures.signature(&e.digest));
            judge(subject, entry, &spec.review, signature.as_ref())
        })
        .collect();
    ReviewFacts {
        findings,
        unreadable: None,
    }
}

/// Who is acking: git's `user.name <user.email>`, else `unknown`.
pub fn current_identity(root: &Path) -> String {
    let get = |key: &str| -> Option<String> {
        let spec = Spec {
            program: Program::Git,
            args: vec!["config".to_owned(), key.to_owned()],
            cwd: Some(root.to_path_buf()),
            env: Vec::new(),
            timeout: Duration::from_secs(10),
            capture: true,
        };
        let out = Runner::new(Limits { jobs: 1 }).run(&spec).ok()?;
        (out.status == Outcome::Exited(0))
            .then(|| out.stdout_raw.trim().to_owned())
            .filter(|s| !s.is_empty())
    };
    match (get("user.name"), get("user.email")) {
        (Some(n), Some(e)) => format!("{n} <{e}>"),
        (None, Some(e)) => e,
        (Some(n), None) => n,
        (None, None) => "unknown".to_owned(),
    }
}

/// What `ack` was asked to record.
#[derive(Debug, Clone)]
pub struct AckRequest {
    /// Subject ids to record; empty with `all_stale` means every subject that is not current.
    pub subjects: Vec<String>,
    /// Ack every subject whose review is missing or stale.
    pub all_stale: bool,
    /// Approved or rejected.
    pub verdict: ReviewVerdict,
    /// The reviewer identity.
    pub reviewer: String,
    /// RFC 3339 UTC time.
    pub at: String,
    /// Optional note.
    pub note: Option<String>,
    /// Recorded without a terminal.
    pub non_interactive: bool,
}

/// Why an ack was refused.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AckRefusal {
    /// A named subject is not a reviewable subject.
    UnknownSubject(String),
    /// The reviewer is not on the `[review] reviewers` allow-list.
    NotAReviewer(String),
    /// A rejection needs a note.
    NoteRequired,
    /// Nothing to record.
    Nothing,
}

impl std::fmt::Display for AckRefusal {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::UnknownSubject(s) => write!(
                f,
                "`{s}` is not a subject that needs review (see `crunk review`)"
            ),
            Self::NotAReviewer(r) => write!(f, "{r} is not listed in [review] reviewers"),
            Self::NoteRequired => write!(f, "a rejection needs --note"),
            Self::Nothing => write!(f, "no subject is stale or missing; nothing to ack"),
        }
    }
}

/// Record `req` into `lock` for `subjects`; returns the subject ids written.
///
/// # Errors
/// [`AckRefusal`] for an unknown subject, an unlisted reviewer, a rejection without a note, or
/// nothing to record.
pub fn record(
    lock: &mut LockFile,
    spec: &DesignSpec,
    subjects: &[Subject],
    req: &AckRequest,
) -> Result<Vec<String>, AckRefusal> {
    let listed = spec.review.reviewers.is_empty()
        || spec
            .review
            .reviewers
            .iter()
            .any(|r| req.reviewer == r.id || req.reviewer.contains(&format!("<{}>", r.id)));
    if !listed {
        return Err(AckRefusal::NotAReviewer(req.reviewer.clone()));
    }
    if req.verdict == ReviewVerdict::Rejected && req.note.is_none() {
        return Err(AckRefusal::NoteRequired);
    }
    let mut chosen: Vec<&Subject> = Vec::new();
    for id in &req.subjects {
        let s = subjects
            .iter()
            .find(|s| &s.id == id || s.screen == *id)
            .ok_or_else(|| AckRefusal::UnknownSubject(id.clone()))?;
        chosen.push(s);
    }
    if req.all_stale {
        chosen.extend(subjects.iter().filter(|s| {
            lock.reviews
                .get(&s.id)
                .is_none_or(|e| e.digest != s.digest())
        }));
    }
    if chosen.is_empty() {
        return Err(AckRefusal::Nothing);
    }
    let mut written = Vec::new();
    for s in chosen {
        if written.contains(&s.id) {
            continue;
        }
        lock.reviews.insert(
            s.id.clone(),
            ReviewEntry {
                digest: s.digest(),
                verdict: req.verdict,
                reviewer: req.reviewer.clone(),
                at: req.at.clone(),
                note: req.note.clone(),
                render: s.inputs.get("render").cloned(),
                non_interactive: req.non_interactive,
                inputs: s.inputs.clone(),
            },
        );
        tracing::info!(subject = %s.id, verdict = ?req.verdict, non_interactive = req.non_interactive, "review recorded");
        written.push(s.id.clone());
    }
    Ok(written)
}
