//! `REL002`: the workspace crates and the wheel do not share one version.
//!
//! One lockstep version covers every crate and the wheel (`releases.md` section 5,
//! `monorepo.md` section 4). [`evaluate`] reads the workspace `Cargo.toml`, the effective
//! version of every member (explicit, or inherited with `version.workspace = true`) and the
//! wheel's `pyproject.toml` when one exists, and reports each member that differs from the
//! workspace version. A manifest that cannot be read is an Unresolved finding naming it and
//! the reason, never a silent skip.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use gob_rules::{Finding, Rule, RuleId, Severity};
use toml::{Table, Value};

/// Wheel metadata files, relative to the repository root, in lookup order.
pub const WHEEL_METADATA: [&str; 2] = ["pyproject.toml", "packaging/pypi/pyproject.toml"];

/// The version Cargo assumes for a package that declares none.
const CARGO_DEFAULT_VERSION: &str = "0.0.0";

// frob:ticket 01M4069WNGJ8YR9DTTM9K9K8V5
/// Crates or the wheel whose version differs from the workspace version.
///
/// Every crate and the wheel are released at one version, so a crate left behind (or
/// ahead) means a published crate set that cannot be installed together. The workspace
/// version is `[workspace.package] version`; a member inheriting it with
/// `version.workspace = true` is equal by construction. A wheel whose version is dynamic
/// under the `maturin` backend reads `Cargo.toml` and is equal by construction too. A manifest
/// that cannot be parsed is reported Unresolved with the reason.
///
/// ## Remedy
///
/// Run `frob release cut VERSION`, which sets every crate and the wheel to VERSION in
/// one commit (`frob release bump VERSION` rewrites the versions alone), or make the named
/// member inherit the workspace version with `version.workspace = true`.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "REL002",
    slug = "lockstep-version-mismatch",
    family = "REL",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Rel002;

/// What [`evaluate`] found and how many manifests it examined.
#[derive(Debug, Clone, Default)]
pub struct Evaluation {
    /// `REL002` findings: one per mismatching member, one Unresolved per unreadable manifest.
    pub findings: Vec<Finding>,
    /// Member manifests (and the wheel metadata) examined.
    pub subjects: usize,
}

/// Why a manifest could not be turned into a version.
#[derive(Debug, thiserror::Error)]
pub enum ManifestError {
    /// The file could not be read.
    #[error("cannot be read: {0}")]
    Read(String),
    /// The file is not valid TOML.
    #[error("is not valid TOML: {0}")]
    Parse(String),
    /// A table or key the version lives in has the wrong shape or is missing.
    #[error("{0}")]
    Shape(String),
}

/// The workspace manifest facts REL002 needs.
struct Workspace {
    /// `[workspace.package] version`, when declared.
    version: Option<String>,
    /// Member directories relative to the root (`.` is the root package).
    members: Vec<String>,
}

/// One member's effective version.
struct Member {
    /// Package name, or the directory when unnamed.
    name: String,
    /// Manifest path relative to the root, with `/` separators.
    manifest: String,
    /// Effective version.
    version: String,
}

fn rule_id() -> RuleId {
    Rel002
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

fn read_table(path: &Path) -> Result<Table, ManifestError> {
    let text = std::fs::read_to_string(path).map_err(|e| ManifestError::Read(e.to_string()))?;
    text.parse::<Table>()
        .map_err(|e| ManifestError::Parse(e.to_string().replace('\n', " ")))
}

fn unresolved(subject: &str, err: &ManifestError) -> Finding {
    tracing::warn!(subject, %err, "REL002: unresolved manifest");
    Finding::new(
        rule_id(),
        Severity::Unresolved,
        None,
        format!(
            "REL002: `{subject}` {err}; its version could not be compared with the workspace version"
        ),
        &format!("unresolved:{subject}"),
    )
}

fn mismatch(kind: &str, name: &str, manifest: &str, version: &str, expected: &str) -> Finding {
    tracing::debug!(
        name,
        manifest,
        version,
        expected,
        "REL002: lockstep mismatch"
    );
    Finding::new(
        rule_id(),
        Severity::Error,
        None,
        format!(
            "{kind} `{name}` ({manifest}) is at version {version} but the lockstep version is {expected}; run `frob release cut VERSION` (or `frob release bump VERSION`) to set every crate and the wheel to one version"
        ),
        &format!("{manifest}@{version}"),
    )
}

/// Expand one `[workspace] members` entry; only literal paths and a trailing `/*` are supported.
fn expand(root: &Path, pattern: &str) -> Result<Vec<String>, ManifestError> {
    let Some(parent) = pattern.strip_suffix("/*") else {
        if pattern.contains(['*', '?', '[']) {
            return Err(ManifestError::Shape(format!(
                "workspace member pattern `{pattern}` is not a literal path or a `dir/*` glob"
            )));
        }
        return Ok(vec![pattern.to_owned()]);
    };
    if parent.contains(['*', '?', '[']) {
        return Err(ManifestError::Shape(format!(
            "workspace member pattern `{pattern}` is not a literal path or a `dir/*` glob"
        )));
    }
    let dir = root.join(parent);
    let mut found: Vec<String> = std::fs::read_dir(&dir)
        .map_err(|e| ManifestError::Read(format!("{}: {e}", dir.display())))?
        .filter_map(Result::ok)
        .filter(|e| e.path().join("Cargo.toml").is_file())
        .filter_map(|e| e.file_name().to_str().map(|n| format!("{parent}/{n}")))
        .collect();
    found.sort();
    Ok(found)
}

fn workspace(root: &Path, table: &Table, out: &mut Evaluation) -> Option<Workspace> {
    let ws = table.get("workspace")?.as_table()?;
    let version = ws
        .get("package")
        .and_then(Value::as_table)
        .and_then(|p| p.get("version"))
        .and_then(Value::as_str)
        .map(str::to_owned);
    let strings = |key: &str| -> Vec<String> {
        ws.get(key)
            .and_then(Value::as_array)
            .map(|a| {
                a.iter()
                    .filter_map(Value::as_str)
                    .map(str::to_owned)
                    .collect()
            })
            .unwrap_or_default()
    };
    let exclude = strings("exclude");
    let mut members = Vec::new();
    if table.contains_key("package") {
        members.push(".".to_owned());
    }
    for pattern in strings("members") {
        match expand(root, &pattern) {
            Ok(dirs) => members.extend(dirs.into_iter().filter(|d| !exclude.contains(d))),
            Err(e) => out.findings.push(unresolved(&pattern, &e)),
        }
    }
    Some(Workspace { version, members })
}

fn member(
    root: &Path,
    dir: &str,
    ws_version: Option<&str>,
) -> Result<Member, (String, ManifestError)> {
    let manifest = if dir == "." {
        "Cargo.toml".to_owned()
    } else {
        format!("{dir}/Cargo.toml")
    };
    let fail = |e| (manifest.clone(), e);
    let table = read_table(&root.join(&manifest)).map_err(fail)?;
    let Some(package) = table.get("package").and_then(Value::as_table) else {
        return Err(fail(ManifestError::Shape(
            "has no [package] table".to_owned(),
        )));
    };
    let name = package
        .get("name")
        .and_then(Value::as_str)
        .unwrap_or(dir)
        .to_owned();
    let version = match package.get("version") {
        None => CARGO_DEFAULT_VERSION.to_owned(),
        Some(Value::String(v)) => v.clone(),
        Some(Value::Table(t)) if t.get("workspace").and_then(Value::as_bool) == Some(true) => {
            ws_version.map(str::to_owned).ok_or_else(|| {
                fail(ManifestError::Shape(
                    "inherits the workspace version but [workspace.package] declares none"
                        .to_owned(),
                ))
            })?
        }
        Some(_) => {
            return Err(fail(ManifestError::Shape(
                "package.version is neither a string nor `{ workspace = true }`".to_owned(),
            )));
        }
    };
    Ok(Member {
        name,
        manifest,
        version,
    })
}

/// The wheel metadata present under `root`, if any.
fn wheel_path(root: &Path) -> Option<PathBuf> {
    WHEEL_METADATA
        .iter()
        .map(|p| root.join(p))
        .find(|p| p.is_file())
}

/// What the wheel metadata says about the version.
enum Wheel {
    /// No `[project]` table: not a wheel definition.
    Absent,
    /// A static version string.
    Static(String),
    /// A dynamic version that maturin reads from `Cargo.toml`, equal by construction.
    FollowsCargo,
}

/// The wheel's version declaration.
fn wheel_version(path: &Path) -> Result<Wheel, ManifestError> {
    let table = read_table(path)?;
    let Some(project) = table.get("project").and_then(Value::as_table) else {
        return Ok(Wheel::Absent);
    };
    if let Some(v) = project.get("version").and_then(Value::as_str) {
        return Ok(Wheel::Static(v.to_owned()));
    }
    let dynamic = project
        .get("dynamic")
        .and_then(Value::as_array)
        .is_some_and(|a| a.iter().any(|d| d.as_str() == Some("version")));
    let backend = table
        .get("build-system")
        .and_then(Value::as_table)
        .and_then(|b| b.get("build-backend"))
        .and_then(Value::as_str)
        .unwrap_or("");
    match (dynamic, backend) {
        (true, "maturin") => Ok(Wheel::FollowsCargo),
        (true, other) => Err(ManifestError::Shape(format!(
            "has a dynamic version from build backend `{other}`, which is not read"
        ))),
        (false, _) => Err(ManifestError::Shape(
            "declares neither a version nor a dynamic version".to_owned(),
        )),
    }
}

/// The most common version among `members`, ties to the lowest string.
fn majority(members: &[Member]) -> Option<String> {
    let mut counts: BTreeMap<&str, usize> = BTreeMap::new();
    for m in members {
        *counts.entry(m.version.as_str()).or_default() += 1;
    }
    counts
        .into_iter()
        .max_by(|a, b| a.1.cmp(&b.1).then_with(|| b.0.cmp(a.0)))
        .map(|(v, _)| v.to_owned())
}

// frob:ticket 01M4069WNGJ8YR9DTTM9K9K8V5
/// Evaluate `REL002` for the repository at `root`.
///
/// Without a workspace `Cargo.toml` the rule is not applicable and the evaluation is empty.
/// When `[workspace.package]` declares no version, the expected version is the one most
/// members share, so a lone straggler is still named.
pub fn evaluate(root: &Path) -> Evaluation {
    let mut out = Evaluation::default();
    let root_manifest = root.join("Cargo.toml");
    if !root_manifest.is_file() {
        tracing::info!("REL002 not applicable: no Cargo.toml at the repository root");
        return out;
    }
    let table = match read_table(&root_manifest) {
        Ok(t) => t,
        Err(e) => {
            out.subjects += 1;
            out.findings.push(unresolved("Cargo.toml", &e));
            return out;
        }
    };
    let Some(ws) = workspace(root, &table, &mut out) else {
        tracing::info!("REL002 not applicable: Cargo.toml has no [workspace] table");
        return out;
    };
    let mut members = Vec::new();
    for dir in &ws.members {
        out.subjects += 1;
        match member(root, dir, ws.version.as_deref()) {
            Ok(m) => members.push(m),
            Err((manifest, e)) => out.findings.push(unresolved(&manifest, &e)),
        }
    }
    let Some(expected) = ws.version.clone().or_else(|| majority(&members)) else {
        tracing::info!("REL002 has no version to compare against");
        return out;
    };
    for m in members.iter().filter(|m| m.version != expected) {
        out.findings.push(mismatch(
            "crate",
            &m.name,
            &m.manifest,
            &m.version,
            &expected,
        ));
    }
    if let Some(path) = wheel_path(root) {
        out.subjects += 1;
        let rel = path
            .strip_prefix(root)
            .unwrap_or(&path)
            .to_string_lossy()
            .replace('\\', "/");
        match wheel_version(&path) {
            Ok(Wheel::Static(v)) if v != expected => {
                out.findings
                    .push(mismatch("wheel", "frob", &rel, &v, &expected));
            }
            Ok(_) => tracing::debug!(wheel = %rel, "REL002: wheel agrees or follows Cargo.toml"),
            Err(e) => out.findings.push(unresolved(&rel, &e)),
        }
    } else {
        tracing::debug!("REL002: no wheel metadata present");
    }
    tracing::info!(
        subjects = out.subjects,
        findings = out.findings.len(),
        %expected,
        "REL002 evaluated"
    );
    out
}
