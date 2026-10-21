//! The cargo packages a ticket scope touches, with their reverse dependencies.
//!
//! A tool stage whose arguments carry the `{packages}` token runs over only these packages at
//! land (frob:ticket 01M4HADVZ8JGBB406JJAJGEC9Q; the design is in
//! docs/design/build-test-ci.md, "Fast lands"). The analysis reads the workspace's
//! `Cargo.toml` files directly: package names, and the dependency tables of the other
//! workspace packages. Anything it cannot place widens to the whole workspace.

use crate::core::Core;
use std::collections::{BTreeMap, BTreeSet};

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

/// Whether a manifest is a cargo-fuzz package: it sits outside the workspace, so `cargo -p` cannot name it.
fn is_standalone(doc: &toml::Table) -> bool {
    doc.get("package")
        .and_then(|p| p.get("metadata"))
        .and_then(|m| m.get("cargo-fuzz"))
        .and_then(toml::Value::as_bool)
        .unwrap_or(false)
}

impl Workspace {
    /// Read the `[package]` name and dependency names of each manifest in `paths` (repo-relative `Cargo.toml` paths).
    pub(crate) fn load<'a>(core: &Core, paths: impl IntoIterator<Item = &'a String>) -> Self {
        let mut raw: Vec<(String, String, BTreeSet<String>)> = Vec::new();
        for path in paths
            .into_iter()
            .filter(|p| *p == "Cargo.toml" || p.ends_with("/Cargo.toml"))
        {
            let text = match core.text(path) {
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
            if is_standalone(&doc) {
                tracing::debug!(%path, "standalone package (outside the workspace); ignored");
                continue;
            }
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

    /// The packages `files` touch plus their direct dependents, and the transitive dependents of
    /// every package that owns a file in `api` (a change that can break callers further out).
    ///
    /// Callers that cannot tell what changed pass `files` as `api`, which keeps the full closure
    /// (frob:ticket 01M4MH62ATTYVEF66Y4C93BJQC).
    pub(crate) fn affected(&self, files: &BTreeSet<String>, api: &BTreeSet<String>) -> Affected {
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
        let api_owners: BTreeSet<&str> = api
            .iter()
            .filter_map(|f| self.owner(f))
            .map(|p| p.name.as_str())
            .collect();
        let direct: Vec<&str> = hit
            .iter()
            .flat_map(|n| rdeps.get(n).into_iter().flatten().copied())
            .collect();
        hit.extend(direct);
        let mut queue: Vec<&str> = api_owners.into_iter().collect();
        let mut seen: BTreeSet<&str> = queue.iter().copied().collect();
        while let Some(n) = queue.pop() {
            for r in rdeps.get(n).into_iter().flatten() {
                hit.insert(r);
                if seen.insert(r) {
                    queue.push(r);
                }
            }
        }
        tracing::info!(packages = hit.len(), "affected cargo packages computed");
        Affected::Packages(hit.into_iter().map(str::to_owned).collect())
    }
}

/// Whether the public surface of Rust source `base` differs from `now`.
///
/// The surface is every `pub` item signature (through its first `{` or `;`), the bodies of
/// `pub enum`, `pub trait` and `macro_rules!` items, and bodiless trait items; comments and
/// private code are ignored, so a body-only edit compares equal. Restricted `pub(crate)` items
/// do not count.
pub fn public_surface_differs(base: &str, now: &str) -> bool {
    surface(base) != surface(now)
}

/// Opening minus closing braces on `line`.
fn brace_delta(line: &str) -> i32 {
    line.chars().fold(0, |d, c| match c {
        '{' => d + 1,
        '}' => d - 1,
        _ => d,
    })
}

/// The sorted public-surface fragments of `src`, whitespace-normalised.
fn surface(src: &str) -> Vec<String> {
    let mut out = Vec::new();
    let lines: Vec<&str> = src.lines().map(str::trim).collect();
    let mut i = 0;
    while i < lines.len() {
        let line = lines[i];
        let restricted = ["pub(crate)", "pub(super)", "pub(self)", "pub(in"]
            .iter()
            .any(|r| line.starts_with(r));
        let whole_body = !restricted
            && (line.starts_with("pub enum")
                || line.starts_with("pub trait")
                || line.starts_with("pub unsafe trait")
                || line.starts_with("macro_rules!"));
        let public = !restricted && line.starts_with("pub");
        let bodiless =
            (line.starts_with("fn ") || line.starts_with("type ") || line.starts_with("const "))
                && line.ends_with(';');
        if whole_body {
            let mut depth: i32 = 0;
            let mut text = String::new();
            while i < lines.len() {
                let l = lines[i];
                i += 1;
                if l.starts_with("//") {
                    continue;
                }
                text.push_str(l);
                text.push(' ');
                depth += brace_delta(l);
                if depth <= 0 && (l.contains('{') || l.ends_with(';') || text.contains('}')) {
                    break;
                }
            }
            out.push(text.split_whitespace().collect::<Vec<_>>().join(" "));
            continue;
        }
        if public {
            let mut text = String::new();
            while i < lines.len() {
                let l = lines[i];
                i += 1;
                let cut = l.find(['{', ';']).map_or(l.len(), |p| p + 1);
                text.push_str(&l[..cut]);
                text.push(' ');
                if cut < l.len() || l.contains('{') || l.ends_with(';') || l.ends_with(',') {
                    break;
                }
            }
            out.push(text.split_whitespace().collect::<Vec<_>>().join(" "));
            continue;
        }
        if bodiless || line.starts_with("#[macro_export") {
            out.push(line.to_owned());
        }
        i += 1;
    }
    out.sort();
    out
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

    // frob:tests crates/gob-check/src/packages.rs::is_standalone
    #[test]
    fn a_cargo_fuzz_manifest_is_standalone() {
        let fuzz: toml::Table = "[package]\nname = \"f\"\n[package.metadata]\ncargo-fuzz = true\n"
            .parse()
            .unwrap();
        let plain: toml::Table = "[package]\nname = \"p\"\n".parse().unwrap();
        assert!(is_standalone(&fuzz));
        assert!(!is_standalone(&plain));
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
            w.affected(
                &files(&["crates/b/src/lib.rs"]),
                &files(&["crates/b/src/lib.rs"])
            ),
            Affected::Packages(vec!["b".to_owned(), "c".to_owned()])
        );
        assert_eq!(
            w.affected(
                &files(&["crates/a/src/x.rs", "docs/x.md"]),
                &files(&["crates/a/src/x.rs"])
            ),
            Affected::Packages(vec!["a".to_owned(), "b".to_owned(), "c".to_owned()])
        );
    }

    // frob:ticket 01M4HADVZ8JGBB406JJAJGEC9Q
    // frob:tests crates/gob-check/src/packages.rs::affected
    #[test]
    fn a_workspace_level_file_or_no_packages_means_everything() {
        let w = ws(&[("a", "crates/a", &[])]);
        assert_eq!(
            w.affected(&files(&["Cargo.lock"]), &files(&[])),
            Affected::Everything
        );
        assert_eq!(
            w.affected(&files(&[".cargo/config.toml"]), &files(&[])),
            Affected::Everything
        );
        assert_eq!(
            Workspace::default().affected(&files(&["crates/a/x.rs"]), &files(&[])),
            Affected::Everything
        );
        assert_eq!(
            w.affected(&files(&["README.md"]), &files(&[])),
            Affected::Packages(Vec::new())
        );
    }

    // frob:ticket 01M4MH62ATTYVEF66Y4C93BJQC
    // frob:tests crates/gob-check/src/packages.rs::affected
    #[test]
    fn a_body_only_change_names_direct_dependents_and_an_api_change_the_closure() {
        let w = ws(&[
            ("core", "crates/core", &[]),
            ("mid", "crates/mid", &["core"]),
            ("top", "crates/top", &["mid"]),
            ("leaf", "crates/leaf", &[]),
        ]);
        let touched = files(&["crates/core/src/lib.rs"]);
        let names = |a: Affected| match a {
            Affected::Packages(p) => p,
            Affected::Everything => panic!("narrowed"),
        };
        assert_eq!(names(w.affected(&touched, &files(&[]))), ["core", "mid"]);
        assert_eq!(
            names(w.affected(&touched, &touched)),
            ["core", "mid", "top"]
        );
        assert_eq!(
            names(w.affected(&files(&["crates/leaf/src/lib.rs"]), &files(&[]))),
            ["leaf"]
        );
    }

    // frob:ticket 01M4MH62ATTYVEF66Y4C93BJQC
    // frob:tests crates/gob-check/src/packages.rs::public_surface_differs
    #[test]
    fn the_public_surface_ignores_bodies_and_sees_signatures_and_variants() {
        let base =
            "pub fn f(a: u32) -> u32 {\n    a + 1\n}\nfn private() {}\npub enum E {\n    A,\n}\n";
        assert!(!public_surface_differs(
            base,
            &base.replace("a + 1", "a + 2")
        ));
        assert!(!public_surface_differs(
            base,
            &base.replace("fn private() {}", "fn other() {}")
        ));
        assert!(public_surface_differs(
            base,
            &base.replace("a: u32", "a: u64")
        ));
        assert!(public_surface_differs(
            base,
            &base.replace("    A,", "    A,\n    B,")
        ));
        assert!(public_surface_differs(
            base,
            &format!("{base}pub struct S;\n")
        ));
        assert!(!public_surface_differs(
            base,
            &format!("{base}pub(crate) struct S;\n")
        ));
    }
}
