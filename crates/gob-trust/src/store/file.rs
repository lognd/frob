//! Reading and writing `trust.toml`: a restricted TOML of `[[entry]]` tables of string and integer keys.

use std::fs;
use std::path::{Path, PathBuf};

use super::entry::{Entry, RepoIdentity};
use super::error::StoreError;
use crate::error::TrustError;
use crate::key::MachineKey;
use crate::mac::Tag;

fn io(op: &'static str, path: &Path) -> impl FnOnce(std::io::Error) -> StoreError {
    let path = path.to_owned();
    move |source| StoreError::Trust(TrustError::Io { op, path, source })
}

fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

fn unesc(s: &str) -> Option<String> {
    let mut out = String::new();
    let mut it = s.chars();
    while let Some(c) = it.next() {
        if c == '\\' {
            match it.next()? {
                '\\' => out.push('\\'),
                '"' => out.push('"'),
                _ => return None,
            }
        } else {
            out.push(c);
        }
    }
    Some(out)
}

/// Render the entries as the file text.
fn render(entries: &[Entry]) -> String {
    let mut s = String::from(
        "# gob trust store: entries are MAC'd; edit with `trust revoke`, not by hand.\n",
    );
    for e in entries {
        let lines = [
            "\n[[entry]]".to_owned(),
            format!("subject = \"{}\"", esc(e.subject())),
            format!("who = \"{}\"", esc(e.who())),
            format!("root = \"{}\"", esc(&e.root().to_string_lossy())),
            format!("root_commit = \"{}\"", esc(&e.identity().root_commit)),
            format!("remote_url = \"{}\"", esc(&e.identity().remote_url)),
            format!("granted_at = {}", e.granted_at()),
            format!("expires_at = {}", e.expires_at()),
            format!("network = {}", e.network()),
            format!("mac = \"{}\"", e.tag().to_hex()),
        ];
        for l in lines {
            s.push_str(&l);
            s.push('\n');
        }
    }
    s
}

#[derive(Default)]
struct Block {
    strs: Vec<(String, String)>,
    ints: Vec<(String, u64)>,
    network: Option<bool>,
}

impl Block {
    fn s(&self, k: &str) -> Option<String> {
        self.strs
            .iter()
            .find(|(n, _)| n == k)
            .map(|(_, v)| v.clone())
    }
    fn n(&self, k: &str) -> Option<u64> {
        self.ints.iter().find(|(n, _)| n == k).map(|(_, v)| *v)
    }

    fn feed(&mut self, line: &str) {
        let Some((k, v)) = line.split_once(" = ") else {
            return;
        };
        if let Some(q) = v.strip_prefix('"').and_then(|v| v.strip_suffix('"')) {
            if let Some(u) = unesc(q) {
                self.strs.push((k.to_owned(), u));
            }
        } else if let Ok(n) = v.parse::<u64>() {
            self.ints.push((k.to_owned(), n));
        } else if k == "network" {
            self.network = v.parse().ok();
        }
    }

    fn into_entry(self, key: &MachineKey) -> Option<Entry> {
        let tag = Tag::from_hex(&self.s("mac")?)?;
        let identity = RepoIdentity {
            root: PathBuf::from(self.s("root")?),
            root_commit: self.s("root_commit")?,
            remote_url: self.s("remote_url")?,
        };
        Entry::from_parts(
            key,
            identity,
            self.s("subject")?,
            self.s("who")?,
            (self.n("granted_at")?, self.n("expires_at")?),
            self.network?,
            tag,
        )
    }
}

/// Parse `text`, returning verified entries and the count of blocks that failed verification.
fn parse(text: &str, key: &MachineKey) -> (Vec<Entry>, usize) {
    let mut blocks: Vec<Block> = Vec::new();
    let mut stray = 0;
    for line in text
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
    {
        if line == "[[entry]]" {
            blocks.push(Block::default());
        } else if let Some(b) = blocks.last_mut() {
            b.feed(line);
        } else {
            stray += 1;
        }
    }
    let total = blocks.len();
    let entries: Vec<Entry> = blocks
        .into_iter()
        .filter_map(|b| b.into_entry(key))
        .collect();
    let inert = total - entries.len() + stray;
    (entries, inert)
}

/// Load and verify the store file; a missing file is an empty store.
pub(super) fn load(path: &Path, key: &MachineKey) -> Result<(Vec<Entry>, usize), StoreError> {
    match fs::read_to_string(path) {
        Ok(text) => Ok(parse(&text, key)),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok((Vec::new(), 0)),
        Err(e) => Err(io("read trust store", path)(e)),
    }
}

/// Write the entries atomically, owner-only.
pub(super) fn save(path: &Path, entries: &[Entry]) -> Result<(), StoreError> {
    if let Some(dir) = path.parent() {
        fs::create_dir_all(dir).map_err(io("create trust store directory", dir))?;
    }
    gob_fs::write_atomic_private(path, render(entries).as_bytes())
        .map_err(io("write trust store", path))
}

/// The permission bits when the file is group- or world-writable (Unix); `None` otherwise.
pub(super) fn writable_mode(path: &Path) -> Option<u32> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mode = fs::metadata(path).ok()?.permissions().mode() & 0o7777;
        (mode & 0o022 != 0).then_some(mode)
    }
    #[cfg(not(unix))]
    {
        let _ = path;
        None
    }
}
