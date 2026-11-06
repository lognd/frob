//! Offline `RustSec` advisory snapshot: a directory of advisory TOML files (the advisory-db layout,
//! `crates/<name>/RUSTSEC-YYYY-NNNN.toml`), read without network access.

use std::path::{Path, PathBuf};

use gob_path::Shown;
use semver::{Version, VersionReq};
use serde::Deserialize;

use crate::VetError;

/// One advisory against one crate.
#[derive(Debug, Clone)]
pub struct Advisory {
    /// Advisory id (`RUSTSEC-2024-0001`).
    pub id: String,
    /// Affected crate.
    pub package: String,
    /// One-line title.
    pub title: String,
    patched: Vec<VersionReq>,
    unaffected: Vec<VersionReq>,
}

#[derive(Deserialize)]
struct RawFile {
    advisory: RawAdvisory,
    #[serde(default)]
    versions: RawVersions,
}

#[derive(Deserialize)]
struct RawAdvisory {
    id: String,
    package: String,
    #[serde(default)]
    title: String,
}

#[derive(Deserialize, Default)]
struct RawVersions {
    #[serde(default)]
    patched: Vec<String>,
    #[serde(default)]
    unaffected: Vec<String>,
}

impl Advisory {
    /// Parse one advisory file's text.
    ///
    /// # Errors
    /// [`VetError::Parse`] on invalid TOML or an invalid version requirement.
    pub fn parse(what: &str, text: &str) -> Result<Self, VetError> {
        let err = |message: String| VetError::Parse {
            what: what.to_owned(),
            message,
        };
        let raw: RawFile = toml::from_str(text).map_err(|e| err(e.to_string()))?;
        let reqs = |v: &[String]| -> Result<Vec<VersionReq>, VetError> {
            v.iter()
                .map(|s| VersionReq::parse(s).map_err(|e| err(format!("{s}: {e}"))))
                .collect()
        };
        Ok(Self {
            id: raw.advisory.id,
            package: raw.advisory.package,
            title: raw.advisory.title,
            patched: reqs(&raw.versions.patched)?,
            unaffected: reqs(&raw.versions.unaffected)?,
        })
    }

    /// True when `version` is neither patched nor unaffected.
    pub fn affects(&self, version: &Version) -> bool {
        !self
            .patched
            .iter()
            .chain(&self.unaffected)
            .any(|r| r.matches(version))
    }

    /// The fixed-version requirements, as written (`>=1.2.3`), empty when no fix exists.
    pub fn fixed(&self) -> Vec<String> {
        self.patched.iter().map(ToString::to_string).collect()
    }
}

/// A loaded snapshot of advisories.
#[derive(Debug, Clone, Default)]
pub struct Snapshot {
    advisories: Vec<Advisory>,
}

impl Snapshot {
    /// Build from already parsed advisories.
    pub fn new(advisories: Vec<Advisory>) -> Self {
        Self { advisories }
    }

    /// Load every `*.toml` below `dir` recursively (non-advisory files such as READMEs are ignored).
    ///
    /// # Errors
    /// [`VetError::Io`] when a directory cannot be read; [`VetError::Parse`] on a bad advisory.
    pub fn load(dir: &Path) -> Result<Self, VetError> {
        let mut advisories = Vec::new();
        walk(dir, &mut advisories)?;
        tracing::info!(count = advisories.len(), dir = %Shown::of(dir), "advisory snapshot loaded");
        Ok(Self { advisories })
    }

    /// Advisories for `package` that affect `version`.
    pub fn affecting<'a>(&'a self, package: &str, version: &Version) -> Vec<&'a Advisory> {
        self.advisories
            .iter()
            .filter(|a| a.package == package && a.affects(version))
            .collect()
    }

    /// Advisories for `package` that have no fixed version (they affect every release).
    pub fn unfixed<'a>(&'a self, package: &str) -> Vec<&'a Advisory> {
        self.advisories
            .iter()
            .filter(|a| a.package == package && a.patched.is_empty())
            .collect()
    }
}

/// Wrap an I/O failure on `p` as a [`VetError::Io`].
fn io(p: &Path, e: &std::io::Error) -> VetError {
    VetError::Io {
        path: Shown::of(p).to_string(),
        message: e.to_string(),
    }
}

/// Read and parse the advisory file at `path`.
fn parse_advisory(path: &Path) -> Result<Advisory, VetError> {
    let text = std::fs::read_to_string(path).map_err(|e| io(path, &e))?;
    Advisory::parse(&Shown::of(path).to_string(), &text)
}

fn walk(dir: &Path, out: &mut Vec<Advisory>) -> Result<(), VetError> {
    let mut entries: Vec<_> = std::fs::read_dir(dir)
        .map_err(|e| io(dir, &e))?
        .collect::<Result<_, _>>()
        .map_err(|e| io(dir, &e))?;
    entries.sort_by_key(std::fs::DirEntry::path);
    for entry in entries {
        let path = entry.path();
        if path.is_dir() {
            walk(&path, out)?;
        } else if path.extension().is_some_and(|e| e == "toml")
            && path
                .file_name()
                .is_some_and(|n| Shown::of(Path::new(n)).as_str().starts_with("RUSTSEC-"))
        {
            out.push(parse_advisory(&path)?);
        }
    }
    Ok(())
}

/// File name of the stamp [`refresh`] writes beside the copied advisories.
pub const STAMP_FILE: &str = "SNAPSHOT.toml";

/// What a [`refresh`] did.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RefreshReport {
    /// Advisories copied into the snapshot.
    pub copied: usize,
    /// Stale advisory files removed from the snapshot (no longer in the source).
    pub removed: usize,
}

/// Collect every `RUSTSEC-*.toml` below `dir` as (path relative to `dir`, path).
fn collect_files(
    dir: &Path,
    rel: &Path,
    out: &mut Vec<(PathBuf, PathBuf)>,
) -> Result<(), VetError> {
    let mut entries: Vec<_> = std::fs::read_dir(dir)
        .map_err(|e| io(dir, &e))?
        .collect::<Result<_, _>>()
        .map_err(|e| io(dir, &e))?;
    entries.sort_by_key(std::fs::DirEntry::path);
    for entry in entries {
        let path = entry.path();
        let rel = rel.join(entry.file_name());
        if path.is_dir() {
            collect_files(&path, &rel, out)?;
        } else if path.extension().is_some_and(|e| e == "toml")
            && Shown::of(Path::new(&entry.file_name()))
                .as_str()
                .starts_with("RUSTSEC-")
        {
            out.push((rel, path));
        }
    }
    Ok(())
}

/// Collect the advisory files already in `dest` (none when it does not exist yet).
fn collect_existing(dest: &Path, out: &mut Vec<(PathBuf, PathBuf)>) -> Result<(), VetError> {
    if dest.is_dir() {
        collect_files(dest, Path::new(""), out)
    } else {
        Ok(())
    }
}

/// The paths in `old` whose relative name is absent from `files`.
fn stale_files(files: &[(PathBuf, PathBuf)], old: &[(PathBuf, PathBuf)]) -> Vec<PathBuf> {
    old.iter()
        .filter(|(rel, _)| !files.iter().any(|(r, _)| r == rel))
        .map(|(_, path)| path.clone())
        .collect()
}

/// Delete each of `paths`.
fn remove_all(paths: &[PathBuf]) -> Result<(), VetError> {
    paths
        .iter()
        .try_for_each(|p| std::fs::remove_file(p).map_err(|e| io(p, &e)))
}

/// Copy each (relative, source) pair under `dest`, creating directories as needed.
fn copy_all(files: &[(PathBuf, PathBuf)], dest: &Path) -> Result<(), VetError> {
    std::fs::create_dir_all(dest).map_err(|e| io(dest, &e))?;
    files.iter().try_for_each(|(rel, path)| {
        let target = dest.join(rel);
        let parent = target.parent().unwrap_or(dest);
        std::fs::create_dir_all(parent).map_err(|e| io(parent, &e))?;
        std::fs::copy(path, &target)
            .map(drop)
            .map_err(|e| io(&target, &e))
    })
}

/// Refresh the snapshot at `dest` from an advisory-db checkout at `source`, then stamp it `as_of`.
///
/// Every advisory in `source` is parsed first (a bad one aborts before `dest` is touched), then
/// `dest`'s advisory files are replaced by the source's and `SNAPSHOT.toml` records the date and
/// count. Pure file I/O: fetching the checkout (git, a tarball) is the caller's job.
///
/// # Errors
/// [`VetError::Io`] when a directory or file cannot be read or written; [`VetError::Parse`] when a
/// source advisory is invalid.
pub fn refresh(source: &Path, dest: &Path, as_of: &str) -> Result<RefreshReport, VetError> {
    let mut files = Vec::new();
    collect_files(source, Path::new(""), &mut files)?;
    for (_, path) in &files {
        parse_advisory(path)?;
    }
    let mut old = Vec::new();
    collect_existing(dest, &mut old)?;
    let stale = stale_files(&files, &old);
    let removed = stale.len();
    remove_all(&stale)?;
    copy_all(&files, dest)?;
    let stamp = dest.join(STAMP_FILE);
    let body = format!("as_of = \"{as_of}\"\ncount = {}\n", files.len());
    std::fs::write(&stamp, body).map_err(|e| io(&stamp, &e))?;
    tracing::info!(copied = files.len(), removed, as_of, dest = %Shown::of(dest), "advisory snapshot refreshed");
    Ok(RefreshReport {
        copied: files.len(),
        removed,
    })
}

/// The `as_of` date recorded by the last [`refresh`] of the snapshot at `dir`, if stamped.
pub fn stamp_as_of(dir: &Path) -> Option<String> {
    #[derive(Deserialize)]
    struct Stamp {
        as_of: String,
    }
    let text = std::fs::read_to_string(dir.join(STAMP_FILE)).ok()?;
    toml::from_str::<Stamp>(&text).ok().map(|s| s.as_of)
}
