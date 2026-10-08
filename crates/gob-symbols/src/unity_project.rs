//! Unity project model: `.asmdef` assemblies and `.asmref` folders as packages (D94).
//!
//! Unity generates its `.csproj` files and they are not committed, so the
//! assemblies come from `.asmdef` files (code-model.md section 3, dotnet-unity.md
//! section 1). Each assembly definition is one package whose id is the repo-relative
//! `.asmdef` path; the C# files of the implicit `Assembly-CSharp` family (no asmdef
//! above them) are the virtual packages `unity:Assembly-CSharp`,
//! `unity:Assembly-CSharp-Editor`, `unity:Assembly-CSharp-firstpass` and
//! `unity:Assembly-CSharp-Editor-firstpass`.
//!
//! A file belongs to the nearest enclosing `.asmdef`, or to the assembly an
//! enclosing `.asmref` points at. References by name and by `GUID:<guid>` become
//! package edges; a GUID resolves through the `.meta` file beside the target
//! `.asmdef`. Anything that cannot be resolved (a malformed definition, an
//! unknown GUID, an `.asmref` whose target is missing) is reported through
//! [`UnityProjects::findings`] and leaves the package Unresolved (never ruled
//! out of reach). A name that matches no repository assembly is an external
//! (engine or registry package) assembly: it holds no repository callables, so it is
//! listed in [`Assembly::external`] and is not an edge.
//!
//! Asmdef references are not transitive in Unity, but the package closure the graph
//! computes is, which only widens reach (sound).

// frob:ticket 01M44YQWGP5553K61QKC8HB0GQ

use std::collections::{BTreeMap, HashMap};
use std::path::{Path, PathBuf};

use serde::Deserialize;

use crate::dotnet::MalformedProject;

/// Id prefix of the implicit (virtual) assemblies.
const IMPLICIT_PREFIX: &str = "unity:";

/// Top-level directories Unity regenerates or never compiles; their C# is ignored.
const GENERATED_ROOTS: [&str; 6] = ["Library", "Temp", "obj", "Logs", "UserSettings", "Builds"];

/// Directory names the project scan never enters (hidden directories are skipped too).
const SKIPPED_DIRS: [&str; 4] = ["node_modules", "Library", "Temp", "obj"];

/// Folders whose scripts compile into the `-firstpass` assemblies.
const FIRSTPASS_ROOTS: [&str; 3] = [
    "Assets/Plugins/",
    "Assets/Standard Assets/",
    "Assets/Pro Standard Assets/",
];

/// The define constraint that gates test assemblies.
const TEST_CONSTRAINT: &str = "UNITY_INCLUDE_TESTS";

/// Well-known GUIDs of `UnityEngine.TestRunner` and `UnityEditor.TestRunner`.
const TEST_RUNNER_GUIDS: [&str; 2] = [
    "27619889b8ba8c24980f49ee34dbb44a",
    "0acc523941302664db1f4e943627d69b",
];

/// Whether a test assembly runs in the editor only or in a player.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TestMode {
    /// Runs in the editor without entering play mode.
    EditMode,
    /// Runs in play mode (or a player build).
    PlayMode,
}

/// The raw JSON of an `.asmdef`.
#[derive(Debug, Deserialize, Default)]
#[serde(rename_all = "camelCase", default)]
struct RawAsmdef {
    name: String,
    references: Vec<String>,
    include_platforms: Vec<String>,
    exclude_platforms: Vec<String>,
    define_constraints: Vec<String>,
    precompiled_references: Vec<String>,
    override_references: bool,
    auto_referenced: Option<bool>,
    allow_unsafe_code: bool,
}

/// The raw JSON of an `.asmref`.
#[derive(Debug, Deserialize, Default)]
#[serde(default)]
struct RawAsmref {
    reference: String,
}

/// One parsed `.asmdef`: an assembly and the package it maps to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Assembly {
    /// Package id: the repo-relative `.asmdef` path.
    pub id: String,
    /// The assembly name.
    pub name: String,
    /// Repo-relative directory of the `.asmdef`.
    pub dir: String,
    /// The `GUID` from the `.asmdef.meta`, lowercased, when the meta exists.
    pub guid: Option<String>,
    /// `references` entries verbatim (`Name` or `GUID:<guid>`).
    pub references: Vec<String>,
    /// `includePlatforms`.
    pub include_platforms: Vec<String>,
    /// `excludePlatforms`.
    pub exclude_platforms: Vec<String>,
    /// `defineConstraints`.
    pub define_constraints: Vec<String>,
    /// `precompiledReferences` (DLL names).
    pub precompiled_references: Vec<String>,
    /// `overrideReferences`.
    pub override_references: bool,
    /// `autoReferenced` (defaults to true).
    pub auto_referenced: bool,
    /// `allowUnsafeCode`.
    pub allow_unsafe_code: bool,
    /// Reference names that match no repository assembly (engine and registry packages).
    pub external: Vec<String>,
}

impl Assembly {
    /// True when `includePlatforms` is exactly `[Editor]`.
    pub fn editor_only(&self) -> bool {
        self.include_platforms.len() == 1 && self.include_platforms[0] == "Editor"
    }

    /// True when the assembly is gated by `UNITY_INCLUDE_TESTS` and references the Unity test runner.
    pub fn is_test(&self) -> bool {
        self.define_constraints.iter().any(|c| c == TEST_CONSTRAINT)
            && self.references.iter().any(|r| {
                r == "UnityEngine.TestRunner"
                    || guid_of(r).is_some_and(|g| TEST_RUNNER_GUIDS.contains(&g.as_str()))
            })
    }

    /// The test mode of a test assembly: a `PlayMode` or `EditMode` path segment decides, else an editor-only definition is `EditMode`.
    pub fn test_mode(&self) -> Option<TestMode> {
        if !self.is_test() {
            return None;
        }
        let seg = |name: &str| self.dir.split('/').any(|s| s == name);
        Some(if seg("PlayMode") {
            TestMode::PlayMode
        } else if seg("EditMode") || self.editor_only() {
            TestMode::EditMode
        } else {
            TestMode::PlayMode
        })
    }
}

/// What a `.cs` file maps to in the Unity project model.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UnityAssignment {
    /// The file belongs to this assembly package (an `.asmdef` path or an implicit `unity:` id).
    Assembly(String),
    /// The file sits in generated output (`Library`, `Temp`, `obj`, hidden or `~` folders) and is ignored.
    Ignored,
    /// The Unity model does not own the file (outside the Unity trees, or an unresolvable `.asmref`).
    None,
}

/// The `GUID:` payload of a reference, lowercased.
fn guid_of(reference: &str) -> Option<String> {
    let (head, tail) = reference.split_at_checked(5)?;
    head.eq_ignore_ascii_case("GUID:")
        .then(|| tail.trim().to_ascii_lowercase())
}

/// The `guid:` value of a Unity `.meta` file's text.
fn meta_guid(text: &str) -> Option<String> {
    text.lines().find_map(|l| {
        l.trim()
            .strip_prefix("guid:")
            .map(|g| g.trim().to_ascii_lowercase())
    })
}

/// The directory part of a repo-relative path (empty at the root).
fn dir_of(path: &str) -> &str {
    path.rsplit_once('/').map_or("", |(d, _)| d)
}

/// An `.asmref` and what it names.
#[derive(Debug, Clone)]
struct AsmRefFile {
    path: String,
    target: Result<String, String>,
}

/// What an `.asmref` resolves to.
enum AsmrefTarget {
    Resolved(String),
    Dangling,
}

/// Everything found in one scan of the work tree.
#[derive(Debug, Default)]
struct Index {
    asmdefs: BTreeMap<String, Result<Assembly, String>>,
    asmrefs: Vec<AsmRefFile>,
    by_dir_def: HashMap<String, String>,
    by_dir_ref: HashMap<String, usize>,
    by_name: HashMap<String, String>,
    by_guid: HashMap<String, String>,
    edges: HashMap<String, Vec<String>>,
    findings: Vec<MalformedProject>,
}

/// Lazily scanned Unity assemblies of one work tree.
#[derive(Debug)]
pub struct UnityProjects {
    root: PathBuf,
    unity_project: bool,
    index: Option<Index>,
    ancestors: HashMap<String, bool>,
}

fn scan(dir: &Path, rel: &str, out: &mut Vec<String>) {
    let Ok(read) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in read.flatten() {
        let Ok(name) = entry.file_name().into_string() else {
            continue;
        };
        let child = if rel.is_empty() {
            name.clone()
        } else {
            format!("{rel}/{name}")
        };
        let Ok(kind) = entry.file_type() else {
            continue;
        };
        if kind.is_dir() {
            if !SKIPPED_DIRS.contains(&name.as_str()) && !name.starts_with('.') {
                scan(&entry.path(), &child, out);
            }
        } else if name.ends_with(".asmdef") || name.ends_with(".asmref") {
            out.push(child);
        }
    }
}

fn load_asmdef(root: &Path, path: &str) -> Result<Assembly, String> {
    let text = std::fs::read_to_string(root.join(path)).map_err(|e| e.to_string())?;
    let raw: RawAsmdef = serde_json::from_str(text.trim_start_matches('\u{feff}'))
        .map_err(|e| format!("malformed asmdef JSON: {e}"))?;
    if raw.name.is_empty() {
        return Err("asmdef has no name".to_owned());
    }
    let guid = std::fs::read_to_string(root.join(format!("{path}.meta")))
        .ok()
        .and_then(|t| meta_guid(&t));
    Ok(Assembly {
        id: path.to_owned(),
        name: raw.name,
        dir: dir_of(path).to_owned(),
        guid,
        references: raw.references,
        include_platforms: raw.include_platforms,
        exclude_platforms: raw.exclude_platforms,
        define_constraints: raw.define_constraints,
        precompiled_references: raw.precompiled_references,
        override_references: raw.override_references,
        auto_referenced: raw.auto_referenced.unwrap_or(true),
        allow_unsafe_code: raw.allow_unsafe_code,
        external: Vec::new(),
    })
}

fn finding(path: &str, reason: String) -> MalformedProject {
    tracing::warn!(path, %reason, "unity assembly unresolved");
    MalformedProject {
        path: path.to_owned(),
        reason,
    }
}

impl Index {
    fn build(root: &Path, unity_project: bool) -> Self {
        let mut files = Vec::new();
        if unity_project {
            // Vendored trees outside Assets and Packages hold assemblies Unity never compiles.
            for tree in ["Assets", "Packages"] {
                scan(&root.join(tree), tree, &mut files);
            }
        } else {
            scan(root, "", &mut files);
        }
        files.sort();
        let mut ix = Index::default();
        for path in &files {
            if path.ends_with(".asmdef") {
                let parsed = load_asmdef(root, path);
                if let Err(reason) = &parsed {
                    ix.findings.push(finding(path, reason.clone()));
                }
                ix.asmdefs.insert(path.clone(), parsed);
            } else {
                let target = std::fs::read_to_string(root.join(path))
                    .map_err(|e| e.to_string())
                    .and_then(|t| {
                        serde_json::from_str::<RawAsmref>(t.trim_start_matches('\u{feff}'))
                            .map_err(|e| format!("malformed asmref JSON: {e}"))
                    })
                    .and_then(|r| {
                        if r.reference.is_empty() {
                            Err("asmref has no reference".to_owned())
                        } else {
                            Ok(r.reference)
                        }
                    });
                ix.asmrefs.push(AsmRefFile {
                    path: path.clone(),
                    target,
                });
            }
        }
        for (id, parsed) in &ix.asmdefs {
            let Ok(a) = parsed else { continue };
            ix.by_dir_def
                .entry(a.dir.clone())
                .or_insert_with(|| id.clone());
            if let Some(prev) = ix.by_name.insert(a.name.clone(), id.clone()) {
                ix.findings.push(finding(
                    id,
                    format!("assembly name `{}` is also defined by {prev}", a.name),
                ));
            }
            if let Some(g) = &a.guid {
                ix.by_guid.insert(g.clone(), id.clone());
            }
        }
        for (i, r) in ix.asmrefs.iter().enumerate() {
            ix.by_dir_ref.entry(dir_of(&r.path).to_owned()).or_insert(i);
        }
        ix.resolve_edges();
        ix.resolve_asmref_findings();
        ix.findings
            .sort_by(|a, b| a.path.cmp(&b.path).then_with(|| a.reason.cmp(&b.reason)));
        tracing::info!(
            asmdefs = ix.asmdefs.len(),
            asmrefs = ix.asmrefs.len(),
            findings = ix.findings.len(),
            "unity assemblies indexed"
        );
        ix
    }

    fn lookup(&self, reference: &str) -> Option<&String> {
        match guid_of(reference) {
            Some(g) => self.by_guid.get(&g),
            None => self.by_name.get(reference),
        }
    }

    fn resolve_edges(&mut self) {
        let ids: Vec<String> = self.asmdefs.keys().cloned().collect();
        let mut edges = HashMap::new();
        let mut new_findings = Vec::new();
        let mut externals: Vec<(String, Vec<String>)> = Vec::new();
        for id in &ids {
            let Ok(a) = &self.asmdefs[id] else { continue };
            let mut out = Vec::new();
            let mut ext = Vec::new();
            for r in &a.references {
                match self.lookup(r) {
                    Some(t) => out.push(t.clone()),
                    None if guid_of(r).is_some() => {
                        new_findings.push(finding(id, format!("unresolved reference {r}")));
                    }
                    None => ext.push(r.clone()),
                }
            }
            out.sort();
            out.dedup();
            edges.insert(id.clone(), out);
            externals.push((id.clone(), ext));
        }
        for (id, ext) in externals {
            if let Some(Ok(a)) = self.asmdefs.get_mut(&id) {
                a.external = ext;
            }
        }
        self.edges = edges;
        self.findings.extend(new_findings);
    }

    fn resolve_asmref_findings(&mut self) {
        let mut new = Vec::new();
        for r in &self.asmrefs {
            match &r.target {
                Err(reason) => new.push(finding(&r.path, reason.clone())),
                Ok(t) if self.lookup(t).is_none() => {
                    new.push(finding(&r.path, format!("unresolved asmref target {t}")));
                }
                Ok(_) => {}
            }
        }
        self.findings.extend(new);
    }

    /// The `.asmref` in `dir`, as `Some(target)` where `target` is `None` when it cannot be resolved.
    fn asmref_target(&self, dir: &str) -> Option<AsmrefTarget> {
        let r = &self.asmrefs[*self.by_dir_ref.get(dir)?];
        Some(match r.target.as_ref().ok().and_then(|t| self.lookup(t)) {
            Some(id) => AsmrefTarget::Resolved(id.clone()),
            None => AsmrefTarget::Dangling,
        })
    }
}

/// True when `id` names an implicit Unity assembly.
pub(crate) fn is_implicit(id: &str) -> bool {
    id.starts_with(IMPLICIT_PREFIX)
}

/// True when `id` is a Unity assembly package (an `.asmdef` path or an implicit assembly).
pub(crate) fn is_unity_package(id: &str) -> bool {
    id.ends_with(".asmdef") || is_implicit(id)
}

/// The implicit assembly id a script at `path` compiles into.
fn implicit_for(path: &str) -> String {
    let first = FIRSTPASS_ROOTS.iter().any(|r| path.starts_with(r));
    let editor = path.split('/').any(|s| s == "Editor");
    let name = match (first, editor) {
        (false, false) => "Assembly-CSharp",
        (false, true) => "Assembly-CSharp-Editor",
        (true, false) => "Assembly-CSharp-firstpass",
        (true, true) => "Assembly-CSharp-Editor-firstpass",
    };
    format!("{IMPLICIT_PREFIX}{name}")
}

impl UnityProjects {
    /// An empty model for the work tree `root`.
    pub fn new(root: &Path) -> Self {
        Self {
            root: root.to_path_buf(),
            unity_project: root.join("ProjectSettings/ProjectVersion.txt").is_file(),
            index: None,
            ancestors: HashMap::new(),
        }
    }

    /// True when the work tree root is a Unity project (`ProjectSettings/ProjectVersion.txt`).
    pub fn is_unity_project(&self) -> bool {
        self.unity_project
    }

    fn index(&mut self) -> &Index {
        self.index
            .get_or_insert_with(|| Index::build(&self.root, self.unity_project))
    }

    /// True when directory `dir` or an ancestor directly holds an `.asmdef` or `.asmref`.
    fn has_marker_above(&mut self, dir: &str) -> bool {
        if let Some(hit) = self.ancestors.get(dir) {
            return *hit;
        }
        let here = std::fs::read_dir(self.root.join(dir))
            .into_iter()
            .flatten()
            .flatten()
            .filter_map(|e| e.file_name().into_string().ok())
            .any(|n| n.ends_with(".asmdef") || n.ends_with(".asmref"));
        let hit = here
            || match dir.rsplit_once('/') {
                Some((up, _)) => self.has_marker_above(up),
                None if dir.is_empty() => false,
                None => self.has_marker_above(""),
            };
        self.ancestors.insert(dir.to_owned(), hit);
        hit
    }

    /// The assembly owning repo-relative `.cs` `file`.
    pub fn assign(&mut self, file: &str) -> UnityAssignment {
        let first = file.split('/').next().unwrap_or("");
        let in_tree = matches!(first, "Assets" | "Packages");
        if self.unity_project && GENERATED_ROOTS.contains(&first) {
            tracing::debug!(file, "unity generated tree ignored");
            return UnityAssignment::Ignored;
        }
        if in_tree
            && file
                .split('/')
                .any(|s| s.starts_with('.') || s.ends_with('~'))
        {
            tracing::debug!(file, "hidden unity folder ignored");
            return UnityAssignment::Ignored;
        }
        if !self.unity_project && !self.has_marker_above(dir_of(file)) {
            return UnityAssignment::None;
        }
        let mut cur = dir_of(file).to_owned();
        loop {
            let ix = self.index();
            if let Some(id) = ix.by_dir_def.get(&cur) {
                return UnityAssignment::Assembly(id.clone());
            }
            if let Some(target) = ix.asmref_target(&cur) {
                return match target {
                    AsmrefTarget::Resolved(id) => UnityAssignment::Assembly(id),
                    AsmrefTarget::Dangling => UnityAssignment::None,
                };
            }
            match cur.rsplit_once('/') {
                Some((up, _)) => cur = up.to_owned(),
                None if cur.is_empty() => break,
                None => cur = String::new(),
            }
        }
        if self.unity_project && in_tree {
            return UnityAssignment::Assembly(implicit_for(file));
        }
        UnityAssignment::None
    }

    /// The assembly definition behind package `id`; the parse error text when it is malformed, `None` for implicit and unknown ids.
    pub fn assembly(&mut self, id: &str) -> Option<Result<Assembly, String>> {
        self.index().asmdefs.get(id).cloned()
    }

    /// Every `.asmdef` package id, sorted.
    pub fn assemblies(&mut self) -> Vec<String> {
        self.index().asmdefs.keys().cloned().collect()
    }

    /// The package dependency edges of `id`: its resolved references (implicit assemblies reference every auto-referenced assembly).
    pub fn references(&mut self, id: &str) -> Vec<String> {
        let ix = self.index();
        if !is_implicit(id) {
            return ix.edges.get(id).cloned().unwrap_or_default();
        }
        let name = id.strip_prefix(IMPLICIT_PREFIX).unwrap_or(id);
        let mut out: Vec<String> = ix
            .asmdefs
            .iter()
            .filter_map(|(i, a)| {
                a.as_ref()
                    .ok()
                    .filter(|a| a.auto_referenced)
                    .map(|_| i.clone())
            })
            .collect();
        let mut add = |n: &str| out.push(format!("{IMPLICIT_PREFIX}{n}"));
        match name {
            "Assembly-CSharp-Editor" => {
                add("Assembly-CSharp");
                add("Assembly-CSharp-firstpass");
                add("Assembly-CSharp-Editor-firstpass");
            }
            "Assembly-CSharp" | "Assembly-CSharp-Editor-firstpass" => {
                add("Assembly-CSharp-firstpass");
            }
            _ => {}
        }
        out.sort();
        out
    }

    /// The packages that reference `id` directly, sorted.
    pub fn referenced_by(&mut self, id: &str) -> Vec<String> {
        let ix = self.index();
        let mut out: Vec<String> = ix
            .edges
            .iter()
            .filter(|(_, to)| to.iter().any(|t| t == id))
            .map(|(from, _)| from.clone())
            .collect();
        out.sort();
        out
    }

    /// The assembly name of package `id` (the file stem when it is malformed).
    pub fn assembly_name(&mut self, id: &str) -> String {
        if let Some(n) = id.strip_prefix(IMPLICIT_PREFIX) {
            return n.to_owned();
        }
        match self.assembly(id) {
            Some(Ok(a)) => a.name,
            _ => id
                .rsplit('/')
                .next()
                .map_or(id, |f| f.strip_suffix(".asmdef").unwrap_or(f))
                .to_owned(),
        }
    }

    /// True when package `id` is malformed or has an unresolved reference (its reach cannot be ruled out).
    pub fn is_unresolved(&mut self, id: &str) -> bool {
        if is_implicit(id) {
            return false;
        }
        let ix = self.index();
        matches!(ix.asmdefs.get(id), Some(Err(_)) | None)
            || ix.findings.iter().any(|f| f.path == id)
    }

    /// Unresolved findings (malformed definitions, unknown GUIDs, dangling `.asmref`s) for the `.asmdef` and `.asmref` files among `files`, sorted.
    pub fn findings(&mut self, files: &[&str]) -> Vec<MalformedProject> {
        self.index()
            .findings
            .iter()
            .filter(|f| files.contains(&f.path.as_str()))
            .cloned()
            .collect()
    }
}
