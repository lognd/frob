//! `Cargo.lock` reader: the packages, their sources and who depends on whom.

use std::collections::{BTreeMap, BTreeSet};

use serde::Deserialize;

use crate::VetError;

/// One locked package.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub struct Package {
    /// Crate name.
    pub name: String,
    /// Locked version.
    pub version: String,
    /// Registry or git source; absent for workspace members and path dependencies.
    #[serde(default)]
    pub source: Option<String>,
    /// Dependency entries (`name` or `name version` or `name version (source)`).
    #[serde(default)]
    pub dependencies: Vec<String>,
}

#[derive(Deserialize)]
struct Lock {
    #[serde(default)]
    package: Vec<Package>,
}

/// Parse `Cargo.lock` text into its packages.
///
/// # Errors
/// [`VetError::Parse`] when the text is not a valid lockfile.
pub fn parse_lockfile(text: &str) -> Result<Vec<Package>, VetError> {
    let lock: Lock = toml::from_str(text).map_err(|e| VetError::Parse {
        what: "Cargo.lock".to_owned(),
        message: e.to_string(),
    })?;
    tracing::debug!(packages = lock.package.len(), "lockfile parsed");
    Ok(lock.package)
}

/// Names of external packages that a source-less (workspace) package depends on directly.
pub fn direct_names(packages: &[Package]) -> BTreeSet<String> {
    let external: BTreeSet<&str> = packages
        .iter()
        .filter(|p| p.source.is_some())
        .map(|p| p.name.as_str())
        .collect();
    packages
        .iter()
        .filter(|p| p.source.is_none())
        .flat_map(|p| p.dependencies.iter())
        .filter_map(|d| d.split_whitespace().next())
        .filter(|n| external.contains(n))
        .map(str::to_owned)
        .collect()
}

/// Versions locked per external crate name, sorted.
pub fn versions_by_name(packages: &[Package]) -> BTreeMap<String, BTreeSet<String>> {
    let mut out: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for p in packages.iter().filter(|p| p.source.is_some()) {
        out.entry(p.name.clone())
            .or_default()
            .insert(p.version.clone());
    }
    out
}
