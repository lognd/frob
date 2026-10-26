//! `TICK004`: committed ledger files that hold an absolute home path.
//!
//! The ledger is committed and pushed, so a `/home/<name>/...` path in an event
//! publishes the user name and directory layout. The scan is a plain byte scan of
//! every file below the tickets directory at the ledger tip; it never parses TOML
//! or Markdown and never rewrites anything.

use gob_path::Shown;
use gob_rules::{Finding, Severity};

use crate::error::Result;
use crate::ledger::Ledger;
use crate::rules::tick004::Tick004;
use crate::tick::id_of;

// frob:ticket 01M41PM9TCJ8MJQREJ733PZ67A

/// The `/root` home root (the hit label is `/root/`); spelled from parts so this file holds no literal home path.
const ROOT_HOME: &str = concat!("/", "root");
/// Hit label for a `/home/<name>/` path.
const HOME_KIND: &str = concat!("/", "home", "/<name>/");
/// Hit label for a `/Users/<name>/` path.
const USERS_KIND: &str = concat!("/", "Users", "/<name>/");
/// Hit label for a `C:\Users\<name>\` path.
const WIN_KIND: &str = concat!("C:", r"\", "Users", r"\", "<name>", r"\");
/// Hit label for a `C:/Users/<name>/` path.
const FWD_KIND: &str = concat!("C:/", "Users", "/<name>/");
/// Hit label for an escaped `C:\\Users\\<name>\\` path.
const ESC_KIND: &str = concat!("C:", r"\\", "Users", r"\\", "<name>", r"\\");
/// Lead bytes of an escaped Windows users root, after the drive colon.
const ESC_LEAD: &[u8] = concat!(r"\\", "Users", r"\\").as_bytes();
/// Separator bytes of the escaped Windows form.
const ESC_SEP: &[u8] = r"\\".as_bytes();

/// Format tag of the clean-scan record; bump it when the scan rules change so old records are ignored.
const CLEAN_SCAN_VERSION: &str = "v1";

/// The first absolute home path in `bytes`: what it looked like and its byte offset.
///
/// Matches `/home/<name>/`, `/Users/<name>/`, `/root/` and the Windows forms
/// `C:\Users\<name>\`, `C:\\Users\\<name>\\` (escaped) and `C:/Users/<name>/`. The account name must
/// be plausible (name characters only), so a documentation placeholder such as `<n>` is not a hit. A
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

// frob:ticket 01M41RHBJ03PGD6JY0J6JTAH9Q
/// The byte range of the first absolute home root in `bytes`: the `/home/<name>` part, without what follows.
///
/// The same hits as [`find_home_path`]; a repair replaces exactly this range so the rest of the path survives.
pub fn find_home_root(bytes: &[u8]) -> Option<std::ops::Range<usize>> {
    let (start, kind) = find_home_path(bytes)?;
    if kind == "/root/" {
        return Some(start..start + ROOT_HOME.len());
    }
    // Everything before the user name: `/home/`, `/Users/`, `C:\Users\`, and so on.
    let lead = kind.find('<').unwrap_or(kind.len());
    let name_at = start + lead;
    let name = bytes[name_at..].iter().take_while(|b| is_name(**b)).count();
    Some(start..name_at + name)
}

// frob:ticket 01M41VT71KGG1AXT491SKCPWMA
/// The byte range of the first absolute path, in either style, that ends at the directory `dir` (such as `app-wt`).
///
/// The range runs from the path root (`/`, `C:\`, `C:/`, escaped `C:\\`, any mix of separators) through
/// `dir`, so a repair replaces it with `dir` alone and keeps the ticket component after it. A path is
/// recognised by its component pattern, so it matches whichever host wrote it. `dir` must be followed by a
/// separator or the end of a name; `app-wt-x` and `my-app-wt` are not hits.
pub fn find_worktree_dir(bytes: &[u8], dir: &str) -> Option<std::ops::Range<usize>> {
    let d = dir.as_bytes();
    let mut from = 0;
    while let Some(rel) = find_sub(&bytes[from..], d) {
        let at = from + rel;
        from = at + 1;
        let end = at + d.len();
        if bytes.get(end).is_some_and(|b| is_name(*b)) || !(at > 0 && is_sep(bytes[at - 1])) {
            continue;
        }
        let mut start = at;
        while start > 0 && is_path_byte(bytes[start - 1]) {
            start -= 1;
        }
        if let Some(root) = root_offset(&bytes[start..at]) {
            return Some(start + root..end);
        }
    }
    None
}

fn find_sub(hay: &[u8], needle: &[u8]) -> Option<usize> {
    hay.windows(needle.len()).position(|w| w == needle)
}

fn is_sep(b: u8) -> bool {
    matches!(b, b'/' | b'\\')
}

/// A byte that can sit inside an absolute path of either style, drive colon and short names included.
fn is_path_byte(b: u8) -> bool {
    is_name(b) || is_sep(b) || matches!(b, b':' | b'~' | b'+' | b'@')
}

/// Where in `span` (the path text before a directory name) the absolute root begins, if one does.
fn root_offset(span: &[u8]) -> Option<usize> {
    let skip = if span.starts_with(b"file://") { 7 } else { 0 };
    let rest = &span[skip..];
    let drive =
        rest.len() > 2 && rest[0].is_ascii_alphabetic() && rest[1] == b':' && is_sep(rest[2]);
    (drive || rest.first() == Some(&b'/')).then_some(skip)
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
    if let Some(rest) = at.strip_prefix(b"/root/")
        && rest.first().is_some_and(|b| is_name(*b))
    {
        return Some("/root/");
    }
    if let Some(rest) = at.strip_prefix(b"/home/")
        && named_then(rest, b"/")
    {
        return Some(HOME_KIND);
    }
    if let Some(rest) = at.strip_prefix(b"/Users/")
        && named_then(rest, b"/")
    {
        return Some(USERS_KIND);
    }
    None
}

/// `rest` follows the `:` of a drive letter.
fn windows_hit(rest: &[u8]) -> Option<&'static str> {
    for (lead, sep, kind) in [
        (&b"\\Users\\"[..], &b"\\"[..], WIN_KIND),
        (ESC_LEAD, ESC_SEP, ESC_KIND),
        (&b"/Users/"[..], &b"/"[..], FWD_KIND),
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
    let rule = id_of::<Tick004>();
    Some(Finding::new(
        rule,
        Severity::Error,
        None,
        format!(
            "{path}: absolute home path ({kind}) at byte {offset}; it publishes the local user name and directory layout. \
             Run `frob ticket doctor --fix` to scrub it in a new commit (history is never rewritten); a hand edit to `~/` or a path relative to the repository parent also clears it"
        ),
        path,
    ))
}

// frob:ticket 01M4DPJHJG8CH9J2H24S030HC7
impl Ledger {
    /// `TICK004` findings for the files below the tickets directory at the ledger tip, one per file.
    ///
    /// Files whose blob the last recorded clean scan already covered are skipped; only changed files are read.
    ///
    /// # Errors
    ///
    /// Git read failures.
    pub fn home_path_findings(&self) -> Result<Vec<Finding>> {
        self.home_path_scan().map(|(findings, _)| findings)
    }

    /// As [`Ledger::home_path_findings`], also returning how many files were actually read.
    ///
    /// # Errors
    ///
    /// Git read failures.
    pub fn home_path_scan(&self) -> Result<(Vec<Finding>, usize)> {
        let ref_name = self.ledger_ref()?;
        let Some(tip) = self.tip_of(&ref_name)? else {
            return Ok((Vec::new(), 0));
        };
        let hex = tip.to_string();
        let dir = self.config().dir.clone();
        let known_clean = self.clean_blobs(&dir);
        let mut out = Vec::new();
        let mut scanned = 0usize;
        let mut skipped = 0usize;
        for (rel, oid) in self.list_blobs(&format!("{hex}:{dir}"))? {
            if known_clean.contains(&oid) {
                skipped += 1;
                continue;
            }
            let path = format!("{dir}/{rel}");
            let bytes = self.repo().read_blob(&oid)?;
            scanned += 1;
            out.extend(tick004(&path, &bytes));
        }
        if out.is_empty() {
            self.record_clean_scan(&hex);
        }
        tracing::info!(
            scanned,
            skipped,
            findings = out.len(),
            "ledger home-path scan finished"
        );
        Ok((out, scanned))
    }

    /// Where the last clean `TICK004` scan is recorded: a local file beside the ticket index, never committed.
    fn clean_scan_path(&self) -> std::path::PathBuf {
        self.index_path().with_file_name("tick004-clean")
    }

    /// Blob ids that the last recorded clean scan covered; empty when there is no usable record.
    ///
    /// Blobs are content addressed, so a blob present in a clean tree is clean now whatever path it sits at.
    fn clean_blobs(&self, dir: &str) -> std::collections::HashSet<gob_git::Oid> {
        let Ok(text) = std::fs::read_to_string(self.clean_scan_path()) else {
            tracing::debug!("no recorded clean TICK004 scan; scanning every file");
            return std::collections::HashSet::default();
        };
        let Some(old) = text
            .trim()
            .strip_prefix(CLEAN_SCAN_VERSION)
            .map(str::trim)
            .filter(|h| !h.is_empty())
        else {
            tracing::debug!("recorded clean TICK004 scan has another version; scanning every file");
            return std::collections::HashSet::default();
        };
        match self.list_blobs(&format!("{old}:{dir}")) {
            Ok(blobs) => blobs.into_iter().map(|(_, oid)| oid).collect(),
            Err(e) => {
                tracing::warn!(error = %e, "recorded clean TICK004 scan unreadable; scanning every file");
                std::collections::HashSet::default()
            }
        }
    }

    /// Record that the ledger at commit `hex` held no home path; best effort, a failure only costs a full scan next time.
    fn record_clean_scan(&self, hex: &str) {
        let path = self.clean_scan_path();
        if let Some(parent) = path.parent()
            && let Err(e) = std::fs::create_dir_all(parent)
        {
            tracing::warn!(error = %e, "cannot create the clean-scan record directory");
            return;
        }
        if let Err(e) = std::fs::write(&path, format!("{CLEAN_SCAN_VERSION} {hex}\n")) {
            tracing::warn!(error = %e, path = %Shown::of(&path), "cannot record the clean TICK004 scan");
        }
    }
}

// frob:ticket 01M42EZ8J63P84XFKTR2GXRW72
impl Ledger {
    /// `TICK005` findings for every ledger file at the tip that matches a local private-term rule.
    ///
    /// Local-only: with no private rules (CI without the local files) it reads nothing and reports nothing.
    ///
    /// # Errors
    ///
    /// Git read failures, or an unusable local privacy file.
    pub fn private_term_findings(&self) -> Result<Vec<Finding>> {
        let rules = self.redaction()?;
        if rules.no_private() {
            tracing::debug!("no local private-term rules; TICK005 not evaluated");
            return Ok(Vec::new());
        }
        let ref_name = self.ledger_ref()?;
        let Some(tip) = self.tip_of(&ref_name)? else {
            return Ok(Vec::new());
        };
        let hex = tip.to_string();
        let dir = self.config().dir.clone();
        let mut out = Vec::new();
        for (rel, oid) in self.list_blobs(&format!("{hex}:{dir}"))? {
            let path = format!("{dir}/{rel}");
            let bytes = self.repo().read_blob(&oid)?;
            out.extend(crate::redact::tick005(&path, &bytes, rules));
        }
        tracing::info!(findings = out.len(), "ledger private-term scan finished");
        Ok(out)
    }
}
