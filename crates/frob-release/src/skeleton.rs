//! Writing the `changelog.d/<ULID>.<type>.md` skeleton that `frob ticket fragment` produces.
//!
//! Design: `documentation.md` section 6. The text comes from the ticket title (or an explicit
//! `--text`), is validated by the same code `release changelog --check` runs, and is written
//! only when it passes, so a skeleton can never break the compile. Nothing here commits.

use std::fs;
use std::path::{Path, PathBuf};

// frob:ticket 01M4FDQXEST75DK0NHDH4P5H15
use crate::error::SkeletonError;
use crate::fragment::{Kind, TicketResolver, files_of, parse_one};

/// The fragment type a ticket of type `ticket_type` defaults to (see `documentation.md` section 6).
///
/// bug and incident are `fixed`; security is `security`; story and epic are `added`; every other
/// type (task, docs, chore, invariant, custom, unknown) is `changed`. A task that adds a
/// capability should pass `--type added`; the default never claims more than "changed".
#[must_use]
pub fn default_kind(ticket_type: &str) -> Kind {
    match ticket_type {
        "bug" | "incident" => Kind::Fixed,
        "security" => Kind::Security,
        "story" | "epic" => Kind::Added,
        _ => Kind::Changed,
    }
}

/// What to write for one ticket.
#[derive(Debug, Clone)]
pub struct Request<'a> {
    /// Repository (worktree) root holding `changelog.d`.
    pub root: &'a Path,
    /// The ticket ULID, upper case.
    pub ulid: &'a str,
    /// The ticket title, the default text.
    pub title: &'a str,
    /// Fragment type.
    pub kind: Kind,
    /// Text put before the title-derived body (`[release] fragment_prefix`); usually empty.
    pub prefix: &'a str,
    /// Explicit text replacing the title-derived one.
    pub text: Option<&'a str>,
    /// Replace an existing fragment of the ticket.
    pub force: bool,
}

/// A fragment that was written.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Written {
    /// File name inside changelog.d.
    pub file: String,
    /// Full path of the file.
    pub path: PathBuf,
    /// The body written, with trailing newline.
    pub body: String,
    /// Names of existing fragments of this ticket that `force` removed.
    pub replaced: Vec<String>,
}

/// The default body: `<prefix><title>.`, with a period added when the title has no end punctuation.
///
/// `prefix` is the repository's `[release] fragment_prefix`; empty by default.
#[must_use]
pub fn skeleton_text(title: &str, prefix: &str) -> String {
    // frob:ticket 01M4FDQXEST75DK0NHDH4P5H15
    let t = title.split_whitespace().collect::<Vec<_>>().join(" ");
    let end = if t.ends_with(['.', '!', '?']) {
        ""
    } else {
        "."
    };
    format!("{prefix}{t}{end}")
}

/// Validate and write the fragment of `req`; the file is created only when the body passes.
///
/// # Errors
/// [`SkeletonError::Exists`] when the ticket has a fragment and `force` is off,
/// [`SkeletonError::UnknownTicket`] when `resolver` does not know the ULID,
/// [`SkeletonError::Invalid`] when the body fails fragment validation (nothing is written),
/// [`SkeletonError::Io`] when the directory or file cannot be written.
pub fn write(req: &Request<'_>, resolver: &dyn TicketResolver) -> Result<Written, SkeletonError> {
    let dir = req.root.join("changelog.d");
    let file = format!("{}.{}.md", req.ulid, req.kind.as_str());
    if resolver.handle(req.ulid).is_none() {
        return Err(SkeletonError::UnknownTicket {
            ulid: req.ulid.to_owned(),
        });
    }
    let found = files_of(&dir, req.ulid);
    if let Some(first) = found.first()
        && !req.force
    {
        tracing::info!(file = %first, "fragment exists; refusing without --force");
        return Err(SkeletonError::Exists {
            file: first.clone(),
        });
    }
    let text = req.text.map_or_else(
        || skeleton_text(req.title, req.prefix),
        |t| t.trim().to_owned(),
    );
    let body = format!("{text}\n");
    parse_one(&file, &body, resolver).map_err(SkeletonError::Invalid)?;
    fs::create_dir_all(&dir).map_err(|e| SkeletonError::Io(e.to_string()))?;
    for name in &found {
        tracing::info!(file = %name, "force: removing the existing fragment");
        fs::remove_file(dir.join(name)).map_err(|e| SkeletonError::Io(e.to_string()))?;
    }
    let path = dir.join(&file);
    fs::write(&path, &body).map_err(|e| SkeletonError::Io(e.to_string()))?;
    tracing::info!(file = %file, forced = !found.is_empty(), "fragment written");
    Ok(Written {
        file,
        path,
        body,
        replaced: found,
    })
}
