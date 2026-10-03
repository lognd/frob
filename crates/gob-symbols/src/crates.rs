//! Workspace crate dependency closure, so a call can only reach crates it links.
//!
//! Shared by the symbol graph (cross-crate path resolution through `use`
//! imports) and COV001's unresolved-call poison. Rust can
//! only call into the crate itself and the crates it (transitively) depends
//! on, so callables elsewhere are ruled out soundly. Only path and workspace
//! dependencies matter (external crates hold no repository callables). A file
//! with no `Cargo.toml` above it is never ruled out.

use std::collections::{BTreeSet, HashMap};
use std::path::{Path, PathBuf};

/// Named direct dependencies: (extern crate name with dashes mapped to underscores, crate directory).
type NamedDeps = Vec<(String, String)>;

/// Lazily parsed crate manifests and their transitive dependency closures.
#[derive(Debug)]
pub struct CrateDeps {
    root: PathBuf,
    /// Repo-relative dir of each `[workspace.dependencies]` path entry, by dependency name.
    workspace: HashMap<String, String>,
    /// Nearest manifest directory per source directory (`None`: no manifest above).
    owner: HashMap<String, Option<String>>,
    direct: HashMap<String, NamedDeps>,
    names: HashMap<String, Option<String>>,
    closure: HashMap<String, BTreeSet<String>>,
}

/// Joins `base` and a relative `rel` (`..` and `.` folded) into a repo-relative `/` path.
fn join_rel(base: &str, rel: &str) -> String {
    let mut parts: Vec<&str> = base.split('/').filter(|p| !p.is_empty()).collect();
    for seg in rel.split('/') {
        match seg {
            "" | "." => {}
            ".." => {
                parts.pop();
            }
            s => parts.push(s),
        }
    }
    parts.join("/")
}

/// The value of `key = "..."` inside an inline table or line, if present.
fn quoted_value<'a>(text: &'a str, key: &str) -> Option<&'a str> {
    let at = text.find(&format!("{key} = \""))? + key.len() + 4;
    let rest = &text[at..];
    rest.find('"').map(|end| &rest[..end])
}

/// Dependency entries of a manifest: `(name, inline text)` per dependency line, and bare tables.
fn dependency_entries(manifest: &str) -> Vec<(String, String)> {
    let mut out: Vec<(String, String)> = Vec::new();
    let mut in_deps = false;
    let mut table_dep: Option<usize> = None;
    for raw in manifest.lines() {
        let line = raw.trim();
        if let Some(header) = line.strip_prefix('[').and_then(|l| l.strip_suffix(']')) {
            table_dep = None;
            in_deps = header.ends_with("dependencies") && !header.starts_with("workspace.");
            if let Some((_, name)) = header.rsplit_once("dependencies.") {
                out.push((name.to_owned(), String::new()));
                table_dep = Some(out.len() - 1);
            }
            continue;
        }
        if let Some(i) = table_dep {
            out[i].1.push_str(line);
            out[i].1.push(' ');
        } else if in_deps && let Some((name, rest)) = line.split_once('=') {
            let name = name.trim();
            match name.strip_suffix(".workspace") {
                Some(bare) => out.push((bare.to_owned(), "workspace = true".to_owned())),
                None => out.push((name.to_owned(), rest.to_owned())),
            }
        }
    }
    out
}

/// The `[package] name` of a manifest, dashes mapped to underscores.
fn package_name_of(manifest: &str) -> Option<String> {
    let mut in_package = false;
    for raw in manifest.lines() {
        let line = raw.trim();
        if line.starts_with('[') {
            in_package = line == "[package]";
        } else if in_package
            && let Some((key, rest)) = line.split_once('=')
            && key.trim() == "name"
        {
            return quoted_value(&format!("name = {}", rest.trim()), "name")
                .map(|n| n.replace('-', "_"));
        }
    }
    None
}

impl CrateDeps {
    /// Dependency data for the work tree `root`.
    pub fn new(root: &Path) -> Self {
        let mut s = Self {
            root: root.to_path_buf(),
            workspace: HashMap::new(),
            owner: HashMap::new(),
            direct: HashMap::new(),
            names: HashMap::new(),
            closure: HashMap::new(),
        };
        if let Ok(text) = std::fs::read_to_string(root.join("Cargo.toml")) {
            let mut in_ws = false;
            for raw in text.lines() {
                let line = raw.trim();
                if line.starts_with('[') {
                    in_ws = line == "[workspace.dependencies]";
                } else if in_ws
                    && let Some((name, rest)) = line.split_once('=')
                    && let Some(p) = quoted_value(rest, "path")
                {
                    s.workspace.insert(name.trim().to_owned(), join_rel("", p));
                }
            }
        }
        s
    }

    /// The directory of the crate owning repo-relative file `path`, when a manifest sits above it.
    pub fn crate_of(&mut self, path: &str) -> Option<String> {
        let dir = path.rsplit_once('/').map_or("", |(d, _)| d).to_owned();
        if let Some(hit) = self.owner.get(&dir) {
            return hit.clone();
        }
        let mut cur = dir.clone();
        let found = loop {
            if self.root.join(&cur).join("Cargo.toml").is_file() {
                break Some(cur.clone());
            }
            match cur.rsplit_once('/') {
                Some((up, _)) => cur = up.to_owned(),
                None if cur.is_empty() => break None,
                None => cur = String::new(),
            }
        };
        self.owner.insert(dir, found.clone());
        found
    }

    fn direct_deps(&mut self, krate: &str) -> NamedDeps {
        if let Some(d) = self.direct.get(krate) {
            return d.clone();
        }
        let text =
            std::fs::read_to_string(self.root.join(krate).join("Cargo.toml")).unwrap_or_default();
        let mut deps = NamedDeps::new();
        for (name, inline) in dependency_entries(&text) {
            let extern_name = name.replace('-', "_");
            if let Some(p) = quoted_value(&inline, "path") {
                deps.push((extern_name, join_rel(krate, p)));
            } else if inline.contains("workspace = true")
                && let Some(dir) = self.workspace.get(&name)
            {
                deps.push((extern_name, dir.clone()));
            }
        }
        self.direct.insert(krate.to_owned(), deps.clone());
        deps
    }

    /// The package name of crate directory `krate`, dashes mapped to underscores (its extern name).
    pub fn package_name(&mut self, krate: &str) -> Option<String> {
        if let Some(n) = self.names.get(krate) {
            return n.clone();
        }
        let text =
            std::fs::read_to_string(self.root.join(krate).join("Cargo.toml")).unwrap_or_default();
        let name = package_name_of(&text);
        self.names.insert(krate.to_owned(), name.clone());
        name
    }

    /// Every extern crate name nameable inside crate `from` (itself and its direct dependencies) with its directory.
    pub fn extern_crates(&mut self, from: &str) -> Vec<(String, String)> {
        let mut out: Vec<(String, String)> = self.direct_deps(from);
        if let Some(own) = self.package_name(from) {
            out.push((own, from.to_owned()));
        }
        out
    }

    /// The crate directory that the extern crate `name` denotes inside crate `from`.
    ///
    /// `from` itself under its own package name (integration tests name their crate), else a
    /// direct dependency of that name; never a transitive one, which `use` cannot name.
    pub fn extern_crate(&mut self, from: &str, name: &str) -> Option<String> {
        if self.package_name(from).as_deref() == Some(name) {
            return Some(from.to_owned());
        }
        self.direct_deps(from)
            .into_iter()
            .find(|(n, _)| n == name)
            .map(|(_, dir)| dir)
    }

    /// True when code in crate `from` can call code in crate `to` (itself or a transitive dependency).
    pub fn can_reach(&mut self, from: &str, to: &str) -> bool {
        if from == to {
            return true;
        }
        if !self.closure.contains_key(from) {
            let mut seen = BTreeSet::new();
            let mut stack = vec![from.to_owned()];
            while let Some(c) = stack.pop() {
                for (_, d) in self.direct_deps(&c) {
                    if seen.insert(d.clone()) {
                        stack.push(d);
                    }
                }
            }
            tracing::debug!(krate = from, deps = seen.len(), "crate dependency closure");
            self.closure.insert(from.to_owned(), seen);
        }
        self.closure[from].contains(to)
    }

    /// Like [`Self::can_reach`] for files, never ruling out a file with no manifest above it.
    pub fn file_can_reach(&mut self, from_file: &str, to_file: &str) -> bool {
        match (self.crate_of(from_file), self.crate_of(to_file)) {
            (Some(a), Some(b)) => self.can_reach(&a, &b),
            _ => true,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_path_workspace_and_table_dependencies() {
        let m = "[package]\nname = \"a\"\n[dependencies]\nb = { path = \"../b\" }\nc.workspace = true\nserde = \"1\"\n[dev-dependencies.d]\npath = \"../d\"\n";
        let e = dependency_entries(m);
        let names: Vec<&str> = e.iter().map(|(n, _)| n.as_str()).collect();
        assert_eq!(names, ["b", "c", "serde", "d"], "{e:?}");
        assert_eq!(quoted_value(&e[0].1, "path"), Some("../b"));
        assert!(e[1].1.contains("workspace = true"));
        assert_eq!(quoted_value(&e[3].1, "path"), Some("../d"));
    }

    #[test]
    fn package_name_maps_dashes() {
        let m = "[package]\nname = \"frob-ack\"\nversion = \"0\"\n[dependencies]\nname = \"no\"\n";
        assert_eq!(package_name_of(m).as_deref(), Some("frob_ack"));
        assert_eq!(package_name_of("[workspace]\n"), None);
    }

    #[test]
    fn join_rel_folds_dots() {
        assert_eq!(join_rel("crates/a", "../b"), "crates/b");
        assert_eq!(join_rel("", "crates/x"), "crates/x");
    }
}
