//! `TICK004`: committed ledger files that hold an absolute home path.
//!
//! The ledger is committed and pushed, so a `/home/<name>/...` path in an event
//! publishes the user name and directory layout. The scan is a plain byte scan of
//! every file below the tickets directory at the ledger tip; it never parses TOML
//! or Markdown and never rewrites anything.

use gob_rules::{Finding, Severity};

use crate::error::Result;
use crate::ledger::Ledger;
use crate::rules::{Tick004, id_of};

// frob:ticket 01M41PM9TCJ8MJQREJ733PZ67A

/// The first absolute home path in `bytes`: what it looked like and its byte offset.
///
/// Matches `/home/<name>/`, `/Users/<name>/`, `/root/` and the Windows forms
/// `C:\Users\<name>\`, `C:\\Users\\<name>\\` (escaped) and `C:/Users/<name>/`. A
/// Unix form must start an absolute path (the byte before it does not continue a
/// path), so `crates/root/` and `../home/x/` are not hits.
pub fn find_home_path(bytes: &[u8]) -> Option<(usize, &'static str)> {
    for (i, &b) in bytes.iter().enumerate() {
        let hit = match b {
            b'/' if starts_path(bytes, i) => unix_hit(&bytes[i..]),
            b':' if i > 0 && bytes[i - 1].is_ascii_alphabetic() => windows_hit(&bytes[i + 1..]),
            _ => None,
        };
        if let Some(kind) = hit {
            let start = if b == b':' { i - 1 } else { i };
            return Some((start, kind));
        }
    }
    None
}

/// True when the byte before `at` does not continue a path, so a `/` at `at` begins an absolute one.
fn starts_path(bytes: &[u8], at: usize) -> bool {
    at == 0 || !(is_name(bytes[at - 1]) || matches!(bytes[at - 1], b'/' | b'\\' | b'~'))
}

fn is_name(b: u8) -> bool {
    b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-' | b'.')
}

/// A non-empty user name at the start of `rest` followed by `sep`.
fn named_then(rest: &[u8], sep: &[u8]) -> bool {
    let n = rest.iter().take_while(|b| is_name(**b)).count();
    n > 0 && rest[n..].starts_with(sep)
}

fn unix_hit(at: &[u8]) -> Option<&'static str> {
    if at.starts_with(b"/root/") {
        return Some("/root/");
    }
    if let Some(rest) = at.strip_prefix(b"/home/")
        && named_then(rest, b"/")
    {
        return Some("/home/<name>/");
    }
    if let Some(rest) = at.strip_prefix(b"/Users/")
        && named_then(rest, b"/")
    {
        return Some("/Users/<name>/");
    }
    None
}

/// `rest` follows the `:` of a drive letter.
fn windows_hit(rest: &[u8]) -> Option<&'static str> {
    for (lead, sep, kind) in [
        (&b"\\Users\\"[..], &b"\\"[..], "C:\\Users\\<name>\\"),
        (
            &b"\\\\Users\\\\"[..],
            &b"\\\\"[..],
            "C:\\\\Users\\\\<name>\\\\",
        ),
        (&b"/Users/"[..], &b"/"[..], "C:/Users/<name>/"),
    ] {
        if let Some(tail) = rest.strip_prefix(lead)
            && named_then(tail, sep)
        {
            return Some(kind);
        }
    }
    None
}

/// `TICK004` for one committed file: a finding when `bytes` holds an absolute home path.
pub fn tick004(path: &str, bytes: &[u8]) -> Option<Finding> {
    let (offset, kind) = find_home_path(bytes)?;
    let rule = id_of(&Tick004);
    Some(Finding::new(
        rule,
        Severity::Warn,
        None,
        format!(
            "{path}: absolute home path ({kind}) at byte {offset}; it publishes the local user name and directory layout. \
             Frob does not rewrite committed ledgers: if this repository is public, rewrite the value yourself (for example `~/` or a path relative to the repository parent) in a new commit"
        ),
        path,
    ))
}

impl Ledger {
    /// `TICK004` findings for every file below the tickets directory at the ledger tip, one per file.
    ///
    /// # Errors
    ///
    /// Git read failures.
    pub fn home_path_findings(&self) -> Result<Vec<Finding>> {
        let ref_name = self.ledger_ref()?;
        let Some(tip) = self.tip_of(&ref_name)? else {
            return Ok(Vec::new());
        };
        let hex = tip.to_string();
        let dir = self.config().dir.clone();
        let mut out = Vec::new();
        let mut scanned = 0usize;
        for rel in self.list_files(&format!("{hex}:{dir}"))? {
            let path = format!("{dir}/{rel}");
            let Some(bytes) = self.repo().read_blob_at(&hex, &path)? else {
                continue;
            };
            scanned += 1;
            out.extend(tick004(&path, &bytes));
        }
        tracing::info!(
            scanned,
            findings = out.len(),
            "ledger home-path scan finished"
        );
        Ok(out)
    }
}
