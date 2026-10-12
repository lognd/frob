//! `frob release changelog` and `frob release status`: compile `changelog.d/<ulid>.<type>.md` fragments into CHANGELOG.md.
//!
//! Design: `documentation.md` section 6 and `releases.md` sections 3 and 6a. Fragments are
//! validated against the ledger (through a [`TicketResolver`]), rendered into one version
//! section at the top of CHANGELOG.md (below the header), and removed only after the file
//! write succeeded. Every compiled section ends with a BLAKE3 marker, so `--check` detects a
//! hand edit of an older section without needing git history.

pub mod adopt;
pub mod bump;
pub mod changelog;
pub mod ci;
pub mod config;
pub mod culprit;
pub mod cut;
pub mod error;
pub mod fragment;
pub mod rel001;
pub mod rel002;
pub mod rel003;
pub mod skeleton;
pub mod status;

use std::fs;
use std::path::{Path, PathBuf};

pub use config::{ProductTags, ReleaseConfig};
pub use error::{FragmentError, ReleaseError, SkeletonError};
pub use fragment::{Fragment, Kind, TicketResolver, parse_name};

/// What the command does with its result.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Write CHANGELOG.md and remove the compiled fragments.
    Write,
    /// Render the section and touch nothing.
    DryRun,
    /// Validate fragments and existing sections; touch nothing.
    Check,
}

/// Inputs of one run.
#[derive(Debug, Clone)]
pub struct Options {
    /// Release version, `MAJOR.MINOR.PATCH[-pre]`.
    pub version: String,
    /// Section date, `YYYY-MM-DD` (injected so output is deterministic).
    pub date: String,
    /// What to do with the result.
    pub mode: Mode,
}

/// What a run produced.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Outcome {
    /// The rendered section; `None` when there were no fragments.
    pub section: Option<String>,
    /// Names of the fragments compiled (or that would be).
    pub fragments: Vec<String>,
    /// True when CHANGELOG.md was written and fragments removed.
    pub written: bool,
}

fn valid_version(v: &str) -> bool {
    let (core, pre) = v.split_once('-').map_or((v, None), |(c, p)| (c, Some(p)));
    let nums: Vec<&str> = core.split('.').collect();
    nums.len() == 3
        && nums
            .iter()
            .all(|n| !n.is_empty() && n.bytes().all(|b| b.is_ascii_digit()))
        && pre.is_none_or(|p| {
            !p.is_empty() && p.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'.')
        })
}

fn valid_date(d: &str) -> bool {
    let b = d.as_bytes();
    b.len() == 10
        && b.iter().enumerate().all(|(i, c)| {
            if i == 4 || i == 7 {
                *c == b'-'
            } else {
                c.is_ascii_digit()
            }
        })
}

fn io(op: &'static str, path: &Path, e: &std::io::Error) -> ReleaseError {
    ReleaseError::Io {
        op,
        path: path.to_owned(),
        reason: e.to_string(),
    }
}

/// Run the changelog compile for the repository at `root`.
///
/// # Errors
/// [`ReleaseError`] for a bad version or date, any invalid fragment (all listed), a version
/// already present, a hand-edited or unmarked section, or an I/O failure.
pub fn run(
    root: &Path,
    opts: &Options,
    resolver: &dyn TicketResolver,
) -> Result<Outcome, ReleaseError> {
    if !valid_version(&opts.version) {
        return Err(ReleaseError::InvalidVersion(opts.version.clone()));
    }
    if !valid_date(&opts.date) {
        return Err(ReleaseError::InvalidDate(opts.date.clone()));
    }
    let dir = root.join("changelog.d");
    let log = root.join("CHANGELOG.md");
    let fragments = fragment::read_all(&dir, resolver).map_err(ReleaseError::Fragments)?;
    let existing = match fs::read_to_string(&log) {
        Ok(t) => Some(t),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => None,
        Err(e) => return Err(io("read", &log, &e)),
    };
    if let Some(t) = &existing {
        changelog::verify(t)?;
    }
    let names: Vec<String> = fragments.iter().map(|f| f.file.clone()).collect();
    if fragments.is_empty() {
        tracing::info!("no fragments; nothing to compile");
        return Ok(Outcome {
            section: None,
            fragments: names,
            written: false,
        });
    }
    if existing
        .as_deref()
        .is_some_and(|t| changelog::has_version(t, &opts.version))
    {
        return Err(ReleaseError::VersionExists(opts.version.clone()));
    }
    let products = ProductTags::load(root)?;
    let section = changelog::render_section(&opts.version, &opts.date, &fragments, &products);
    if opts.mode != Mode::Write {
        return Ok(Outcome {
            section: Some(section),
            fragments: names,
            written: false,
        });
    }
    let (header, rest) = match &existing {
        Some(t) if changelog::is_generated(t) => {
            let (h, s) = changelog::split(t);
            (h.to_owned(), s.concat())
        }
        Some(t) => {
            tracing::info!("adopting a hand-written CHANGELOG.md");
            let (above, rest) = changelog::split_adopted(t);
            (spaced(above), rest.to_owned())
        }
        None => (
            changelog::initial_header(root.join("CHANGELOG-v1.md").is_file()),
            String::new(),
        ),
    };
    let new_text = format!("{header}{section}\n{rest}");
    write_atomic(&log, &new_text)?;
    tracing::info!(version = %opts.version, count = fragments.len(), "wrote CHANGELOG.md");
    for f in &fragments {
        let p: PathBuf = dir.join(&f.file);
        fs::remove_file(&p).map_err(|e| io("remove", &p, &e))?;
    }
    Ok(Outcome {
        section: Some(section),
        fragments: names,
        written: true,
    })
}

/// `above` ended so that a following section starts after one blank line (empty stays empty).
fn spaced(above: &str) -> String {
    let mut out = above.trim_end_matches('\n').to_owned();
    if !out.is_empty() {
        out.push_str("\n\n");
    }
    out
}

/// Write `text` to `path` through a sibling temp file and a rename, so a failure leaves the old file.
fn write_atomic(path: &Path, text: &str) -> Result<(), ReleaseError> {
    gob_fs::write_atomic(path, text.as_bytes()).map_err(|e| io("write", path, &e))
}
