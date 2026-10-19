//! Offline `RustSec` advisory snapshot: a directory of advisory TOML files (the advisory-db layout,
//! `crates/<name>/RUSTSEC-YYYY-NNNN.toml`), read without network access.

use std::path::Path;

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
}

fn walk(dir: &Path, out: &mut Vec<Advisory>) -> Result<(), VetError> {
    let io = |p: &Path, e: std::io::Error| VetError::Io {
        path: Shown::of(p).to_string(),
        message: e.to_string(),
    };
    let mut entries: Vec<_> = std::fs::read_dir(dir)
        .map_err(|e| io(dir, e))?
        .collect::<Result<_, _>>()
        .map_err(|e| io(dir, e))?;
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
            let text = std::fs::read_to_string(&path).map_err(|e| io(&path, e))?;
            out.push(Advisory::parse(&Shown::of(&path).to_string(), &text)?);
        }
    }
    Ok(())
}
