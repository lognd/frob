//! The cargo packages a ticket scope touches, with their reverse dependencies.
//!
//! A tool stage whose arguments carry the `{packages}` token runs over only these packages at
//! land (frob:ticket 01M4HADVZ8JGBB406JJAJGEC9Q; the design is in
//! docs/design/build-test-ci.md, "Fast lands"). The analysis reads the workspace's
//! `Cargo.toml` files directly: package names, and the dependency tables of the other
//! workspace packages. Anything it cannot place widens to the whole workspace.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

/// Files outside every package whose change can affect any package.
const WORKSPACE_WIDE: [&str; 8] = [
    "Cargo.toml",
    "Cargo.lock",
    "rust-toolchain",
    "rust-toolchain.toml",
    "clippy.toml",
    ".clippy.toml",
    "rustfmt.toml",
    ".rustfmt.toml",
];

/// One workspace package: its name, directory (repo-relative, empty for the root) and workspace dependencies.
#[derive(Debug, Clone, PartialEq, Eq)]
struct Package {
    name: String,
    dir: String,
    deps: BTreeSet<String>,
}

/// The workspace packages read from the walked `Cargo.toml` files.
#[derive(Debug, Default)]
pub(crate) struct Workspace {
    packages: Vec<Package>,
}

/// What a scope affects: a named set of packages, or everything.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum Affected {
    /// These packages: the owners of the scoped files and everything depending on them.
    Packages(Vec<String>),
    /// The scope cannot be narrowed (workspace-level file, no packages found).
    Everything,
}

impl Workspace {
    /// Read the `[package]` name and dependency names of each manifest in `paths` (repo-relative `Cargo.toml` paths).
    pub(crate) fn load<'a>(root: &Path, paths: impl IntoIterator<Item = &'a String>) -> Self {
        let mut raw: Vec<(String, String, BTreeSet<String>)> = Vec::new();
        for path in paths
            .into_iter()
            .filter(|p| *p == "Cargo.toml" || p.ends_with("/Cargo.toml"))
        {
            let text = match std::fs::read_to_string(root.join(path)) {
                Ok(t) => t,
                Err(e) => {
                    tracing::warn!(%path, error = %e, "manifest unreadable; ignored");
                    continue;
                }
            };
            let Ok(doc) = text.parse::<toml::Table>() else {
                tracing::warn!(%path, "manifest does not parse; ignored");
                continue;
            };
            let Some(name) = doc
                .get("package")
                .and_then(|p| p.get("name"))
                .and_then(toml::Value::as_str)
            else {
                continue;
            };
            let dir = path
                .strip_suffix("Cargo.toml")
                .unwrap_or("")
                .trim_end_matches('/');
            let mut deps = BTreeSet::new();
            for table in ["dependencies", "dev-dependencies", "build-dependencies"] {
                if let Some(t) = doc.get(table).and_then(toml::Value::as_table) {
                    for (key, value) in t {
                        let real = value
                            .get("package")
                            .and_then(toml::Value::as_str)
                            .unwrap_or(key);
                        deps.insert(real.to_owned());
                    }
                }
            }
            raw.push((name.to_owned(), dir.to_owned(), deps));
        }
        let names: BTreeSet<String> = raw.iter().map(|(n, _, _)| n.clone()).collect();
        let packages = raw
            .into_iter()
            .map(|(name, dir, deps)| Package {
                name,
                dir,
                deps: deps.into_iter().filter(|d| names.contains(d)).collect(),
            })
            .collect();
        Self { packages }
    }

    /// The package owning `file`: the one with the longest directory prefix.
    fn owner(&self, file: &str) -> Option<&Package> {
        self.packages
            .iter()
            .filter(|p| {
                p.dir.is_empty()
                    || file
                        .strip_prefix(p.dir.as_str())
                        .is_some_and(|r| r.starts_with('/'))
            })
            .max_by_key(|p| p.dir.len())
    }

    /// The packages `files` touch plus every package that depends on them, transitively.
    pub(crate) fn affected(&self, files: &BTreeSet<String>) -> Affected {
        if self.packages.is_empty() {
            return Affected::Everything;
        }
        let mut hit: BTreeSet<&str> = BTreeSet::new();
        for file in files {
            if let Some(p) = self.owner(file) {
                hit.insert(p.name.as_str());
            } else {
                let base = file.rsplit('/').next().unwrap_or(file);
                if WORKSPACE_WIDE.contains(&base) || file.starts_with(".cargo/") {
                    tracing::info!(%file, "workspace-level file in scope; no package narrowing");
                    return Affected::Everything;
                }
            }
        }
        let mut rdeps: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
        for p in &self.packages {
            for d in &p.deps {
                rdeps.entry(d.as_str()).or_default().push(p.name.as_str());
            }
        }
        let mut queue: Vec<&str> = hit.iter().copied().collect();
        while let Some(n) = queue.pop() {
            for r in rdeps.get(n).into_iter().flatten() {
                if hit.insert(r) {
                    queue.push(r);
                }
            }
        }
        tracing::info!(packages = hit.len(), "affected cargo packages computed");
        Affected::Packages(hit.into_iter().map(str::to_owned).collect())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ws(entries: &[(&str, &str, &[&str])]) -> Workspace {
        Workspace {
            packages: entries
                .iter()
                .map(|(n, d, deps)| Package {
                    name: (*n).to_owned(),
                    dir: (*d).to_owned(),
                    deps: deps.iter().map(|s| (*s).to_owned()).collect(),
                })
                .collect(),
        }
    }

    fn files(f: &[&str]) -> BTreeSet<String> {
        f.iter().map(|s| (*s).to_owned()).collect()
    }

    // frob:ticket 01M4HADVZ8JGBB406JJAJGEC9Q
    // frob:tests crates/gob-check/src/packages.rs::affected
    #[test]
    fn a_crate_file_affects_its_package_and_reverse_dependencies_only() {
        let w = ws(&[
            ("a", "crates/a", &[]),
            ("b", "crates/b", &["a"]),
            ("c", "crates/c", &["b"]),
            ("d", "crates/d", &[]),
        ]);
        assert_eq!(
            w.affected(&files(&["crates/b/src/lib.rs"])),
            Affected::Packages(vec!["b".to_owned(), "c".to_owned()])
        );
        assert_eq!(
            w.affected(&files(&["crates/a/src/x.rs", "docs/x.md"])),
            Affected::Packages(vec!["a".to_owned(), "b".to_owned(), "c".to_owned()])
        );
    }

    // frob:ticket 01M4HADVZ8JGBB406JJAJGEC9Q
    // frob:tests crates/gob-check/src/packages.rs::affected
    #[test]
    fn a_workspace_level_file_or_no_packages_means_everything() {
        let w = ws(&[("a", "crates/a", &[])]);
        assert_eq!(w.affected(&files(&["Cargo.lock"])), Affected::Everything);
        assert_eq!(
            w.affected(&files(&[".cargo/config.toml"])),
            Affected::Everything
        );
        assert_eq!(
            Workspace::default().affected(&files(&["crates/a/x.rs"])),
            Affected::Everything
        );
        assert_eq!(
            w.affected(&files(&["README.md"])),
            Affected::Packages(Vec::new())
        );
    }
}
