//! The framework registry and per-member detection (language-engines.md section 4, ~5E0V6W3).
//!
//! A [`FrameworkEntry`] declares how a framework is detected and how its routes are discovered. Built-in
//! entries are listed here; a crate that links in more submits them with `inventory::submit!`.
//! Detection runs for every `package.json` of the repository (every workspace member, never only the root).

// frob:ticket 01M47QKVBB5G9N1QZP3AVXTRHX

use std::collections::BTreeSet;
use std::path::Path;

use gob_symbols::NodeProjects;
use gob_walk::FileEntry;
use tracing::{debug, info, warn};

use crate::nextjs;
use crate::react_router;
use crate::repo::Repo;
use crate::types::{Detection, Discovery, Problem};

/// Extensions of a JavaScript or TypeScript config file stem such as `next.config`.
const CONFIG_EXTENSIONS: [&str; 5] = ["js", "mjs", "cjs", "ts", "mts"];

/// One way a framework shows itself in a workspace member.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Detector {
    /// The member's `package.json` lists this package in any dependency table.
    Dependency(&'static str),
    /// The member directory holds `<stem>.<js|mjs|cjs|ts|mts>`.
    ConfigFile(&'static str),
    /// The member directory holds at least one file under this sub-directory.
    Directory(&'static str),
}

/// A registrable framework: submit one with `inventory::submit!` to make it visible to [`frameworks`].
pub struct FrameworkEntry {
    /// The registry name, unique (`react-router`).
    pub name: &'static str,
    /// The detectors; the framework is present in a member when any matches.
    pub detectors: &'static [Detector],
    /// Finds the routes and entrypoints of one detected member.
    pub discover: fn(&Repo<'_>, &Detection) -> Discovery,
}

inventory::collect!(FrameworkEntry);

static BUILTIN: [FrameworkEntry; 2] = [nextjs::ENTRY, react_router::ENTRY];

/// Every known framework, built-ins first-registered wins on a name clash, sorted by name.
pub fn frameworks() -> Vec<&'static FrameworkEntry> {
    let mut all: Vec<&'static FrameworkEntry> = BUILTIN
        .iter()
        .chain(inventory::iter::<FrameworkEntry>())
        .collect();
    all.sort_by_key(|e| e.name);
    let before = all.len();
    all.dedup_by_key(|e| e.name);
    if all.len() != before {
        warn!(dropped = before - all.len(), "duplicate framework names");
    }
    all
}

/// The member directory of a `package.json` path (empty at the root).
fn dir_of(pkg: &str) -> &str {
    pkg.rsplit_once('/').map_or("", |(d, _)| d)
}

/// `dir` joined with `rel` (`rel` alone when `dir` is the root).
pub(crate) fn join(dir: &str, rel: &str) -> String {
    if dir.is_empty() {
        rel.to_owned()
    } else {
        format!("{dir}/{rel}")
    }
}

/// True when `path` lies under a `node_modules` directory.
pub(crate) fn in_node_modules(path: &str) -> bool {
    path.split('/').any(|s| s == "node_modules")
}

/// The evidence line of `detector` in the member at `dir`, when it matches.
fn matches(
    detector: &Detector,
    deps: &BTreeSet<String>,
    dir: &str,
    files: &BTreeSet<&str>,
) -> Option<String> {
    match detector {
        Detector::Dependency(name) => deps.contains(*name).then(|| format!("dependency {name}")),
        Detector::ConfigFile(stem) => CONFIG_EXTENSIONS.iter().find_map(|ext| {
            let name = format!("{stem}.{ext}");
            files
                .contains(join(dir, &name).as_str())
                .then(|| format!("config {name}"))
        }),
        Detector::Directory(sub) => {
            let prefix = format!("{}/", join(dir, sub));
            files
                .iter()
                .any(|f| f.starts_with(&prefix))
                .then(|| format!("directory {sub}"))
        }
    }
}

/// Detects the registered frameworks in every workspace member of the repository at `root`.
///
/// `files` is the walked file list (repo-relative paths); manifests that fail to parse are returned as
/// problems alongside, never silently skipped.
pub fn detect(root: &Path, files: &[FileEntry]) -> (Vec<Detection>, Vec<Problem>) {
    detect_with(&frameworks(), root, files)
}

/// Like [`detect`], over an explicit list of framework `entries`.
pub fn detect_with(
    entries: &[&FrameworkEntry],
    root: &Path,
    files: &[FileEntry],
) -> (Vec<Detection>, Vec<Problem>) {
    let set: BTreeSet<&str> = files.iter().map(|f| f.path.as_str()).collect();
    let mut projects = NodeProjects::new(root);
    let mut found = Vec::new();
    let mut problems = Vec::new();
    for pkg in set
        .iter()
        .filter(|p| (**p == "package.json" || p.ends_with("/package.json")) && !in_node_modules(p))
    {
        let package = match projects.load_package(pkg) {
            Ok(p) => p.clone(),
            Err(reason) => {
                warn!(member = pkg, reason, "member manifest not readable");
                problems.push(Problem {
                    path: (*pkg).to_owned(),
                    reason: reason.clone(),
                });
                continue;
            }
        };
        let dir = dir_of(pkg);
        for entry in entries {
            let evidence: Vec<String> = entry
                .detectors
                .iter()
                .filter_map(|d| matches(d, &package.dependencies, dir, &set))
                .collect();
            if evidence.is_empty() {
                debug!(member = pkg, framework = entry.name, "not detected");
                continue;
            }
            info!(
                member = pkg,
                framework = entry.name,
                ?evidence,
                "framework detected"
            );
            found.push(Detection {
                framework: entry.name,
                member: (*pkg).to_owned(),
                dir: dir.to_owned(),
                evidence,
            });
        }
    }
    found.sort();
    (found, problems)
}
