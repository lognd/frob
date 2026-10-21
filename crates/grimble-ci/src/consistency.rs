//! CI012: the CI configuration agrees with the repository's manifests and ownership files.
//!
//! Four joins: the toolchain a step installs against `rust-toolchain.toml`, numeric toolchains
//! against the highest `rust-version` of the Cargo manifests, the ecosystems the manifests imply
//! against Dependabot's `updates`, and `CODEOWNERS` against `.github`.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use std::collections::BTreeSet;

use gob_rules::Severity;
use serde_yaml_ng::Value;

use crate::finding::{CiFinding, fire};
use crate::workflow::{Workflow, key, run_of, scalar, uses_of, with_of};

/// Rule id of the consistency rule.
pub const CI012: &str = "CI012";

/// The repository files CI012 joins the workflows with.
pub(crate) struct Repo<'a> {
    /// Every repo-relative file path of the walk.
    pub files: &'a [String],
    /// The text of a file, `None` when unreadable.
    pub read: &'a dyn Fn(&str) -> Option<String>,
}

/// Findings of CI012 for the parsed workflows of `repo`.
pub(crate) fn check(repo: &Repo<'_>, workflows: &[Workflow<'_>]) -> Vec<CiFinding> {
    let mut out = Vec::new();
    let pinned = pinned_channel(repo);
    let msrv = max_msrv(repo);
    tracing::debug!(?pinned, ?msrv, "CI012 manifest facts");
    for wf in workflows {
        for (job, tc) in toolchains(wf) {
            if let (Some(p), true) = (&pinned, tc.from_step)
                && !compatible(&tc.value, p)
            {
                out.push(fire(
                    CI012,
                    Severity::Warn,
                    (wf.path, wf.within_job(&job, &tc.value)),
                    format!("job `{job}` installs Rust `{}` but `rust-toolchain.toml` pins `{p}`; use the pinned channel (or drop the explicit toolchain so rustup reads the file)", tc.value),
                    format!("{}:{job}:toolchain:{}", wf.path, tc.value),
                ));
            }
            if let (Some(min), Some(v)) = (msrv, version_of(&tc.value))
                && v < min
            {
                out.push(fire(
                    CI012,
                    Severity::Warn,
                    (wf.path, wf.within_job(&job, &tc.value)),
                    format!("job `{job}` tests Rust `{}`, older than the manifests' `rust-version` {}.{}; raise the CI toolchain or lower `rust-version`", tc.value, min.0, min.1),
                    format!("{}:{job}:msrv:{}", wf.path, tc.value),
                ));
            }
        }
    }
    if let Some(first) = workflows.first() {
        dependabot(repo, first, &mut out);
        codeowners(repo, first.path, &mut out);
    }
    out
}

/// A toolchain a job uses.
struct Toolchain {
    /// The toolchain text (`1.80`, `stable`).
    value: String,
    /// True for an installing step, false for a matrix entry.
    from_step: bool,
}

/// `(job id, toolchain)` for every literal toolchain of the workflow.
fn toolchains(wf: &Workflow<'_>) -> Vec<(String, Toolchain)> {
    let mut out = Vec::new();
    for job in wf.jobs() {
        for step in job.steps() {
            if let Some(v) = step_toolchain(step) {
                out.push((
                    job.id.to_owned(),
                    Toolchain {
                        value: v,
                        from_step: true,
                    },
                ));
            }
        }
        let matrix = key(job.value, "strategy").and_then(|s| key(s, "matrix"));
        for k in ["toolchain", "rust", "rust-version", "rust_version"] {
            let Some(Value::Sequence(seq)) = matrix.and_then(|m| key(m, k)) else {
                continue;
            };
            for v in seq.iter().filter_map(scalar).filter(|v| !v.contains("${{")) {
                out.push((
                    job.id.to_owned(),
                    Toolchain {
                        value: v,
                        from_step: false,
                    },
                ));
            }
        }
    }
    out
}

/// The literal toolchain a step installs.
fn step_toolchain(step: &Value) -> Option<String> {
    let found = if let Some(uses) = uses_of(step) {
        let (action, r) = uses.split_once('@').unwrap_or((uses, ""));
        match action {
            "dtolnay/rust-toolchain" => with_of(step, "toolchain").or_else(|| Some(r.to_owned())),
            "actions-rs/toolchain" | "actions-rust-lang/setup-rust-toolchain" => {
                with_of(step, "toolchain")
            }
            _ => None,
        }
    } else {
        run_of(step).and_then(rustup_toolchain)
    };
    found.filter(|v| !v.is_empty() && !v.contains("${{"))
}

/// The toolchain named by a `rustup default|toolchain install|override set` line.
fn rustup_toolchain(run: &str) -> Option<String> {
    for line in run.lines() {
        let words: Vec<&str> = line.split_whitespace().collect();
        let at = words.iter().position(|w| *w == "rustup")?;
        let rest = &words[at + 1..];
        let tail = match rest {
            ["default", t, ..] | ["toolchain", "install", t, ..] | ["override", "set", t, ..] => {
                Some(*t)
            }
            _ => None,
        };
        if let Some(t) = tail {
            return Some(t.to_owned());
        }
    }
    None
}

/// `rust-toolchain.toml` (or the legacy `rust-toolchain`) channel at the repo root.
fn pinned_channel(repo: &Repo<'_>) -> Option<String> {
    let name = ["rust-toolchain.toml", "rust-toolchain"]
        .into_iter()
        .find(|n| repo.files.iter().any(|f| f == n))?;
    let text = (repo.read)(name)?;
    match toml::from_str::<toml::Table>(&text) {
        Ok(t) => t
            .get("toolchain")?
            .get("channel")?
            .as_str()
            .map(str::to_owned),
        Err(_) => Some(text.trim().to_owned()).filter(|t| !t.contains(['\n', '[', '='])),
    }
}

/// `(major, minor)` of a numeric toolchain text.
fn version_of(v: &str) -> Option<(u64, u64)> {
    let mut parts = v.split('.');
    let major = parts.next()?.parse().ok()?;
    let minor = parts.next()?.parse().ok()?;
    Some((major, minor))
}

/// True when CI toolchain `ci` agrees with pinned `pinned` (named channels are not compared).
fn compatible(ci: &str, pinned: &str) -> bool {
    let named = |s: &str| s.starts_with(|c: char| c.is_ascii_alphabetic());
    if named(ci) {
        return true;
    }
    if named(pinned) {
        return !pinned.starts_with("nightly") && !pinned.starts_with("beta");
    }
    ci == pinned || pinned.starts_with(&format!("{ci}.")) || ci.starts_with(&format!("{pinned}."))
}

/// The highest `rust-version` of the Cargo manifests.
fn max_msrv(repo: &Repo<'_>) -> Option<(u64, u64)> {
    repo.files
        .iter()
        .filter(|f| f.rsplit('/').next() == Some("Cargo.toml") && !skipped(f))
        .filter_map(|f| toml::from_str::<toml::Table>(&(repo.read)(f)?).ok())
        .flat_map(|t| {
            let pkg = t
                .get("package")
                .and_then(|p| p.get("rust-version"))
                .cloned();
            let ws = t
                .get("workspace")
                .and_then(|w| w.get("package"))
                .and_then(|p| p.get("rust-version"))
                .cloned();
            [pkg, ws]
        })
        .flatten()
        .filter_map(|v| version_of(v.as_str()?))
        .max()
}

/// True for a path under a dependency or build directory.
fn skipped(path: &str) -> bool {
    path.split('/')
        .any(|c| matches!(c, "node_modules" | "target" | "vendor"))
}

/// The Dependabot ecosystems the manifests imply.
fn ecosystems(repo: &Repo<'_>, has_workflows: bool) -> BTreeSet<&'static str> {
    let mut set = BTreeSet::new();
    for f in repo.files.iter().filter(|f| !skipped(f)) {
        let name = f.rsplit('/').next().unwrap_or(f);
        let eco = match name {
            "Cargo.toml" => "cargo",
            "package.json" => "npm",
            "requirements.txt" | "pyproject.toml" | "Pipfile" => "pip",
            "go.mod" => "gomod",
            "Gemfile" => "bundler",
            "pom.xml" => "maven",
            n if n.ends_with(".csproj") => "nuget",
            _ if gob_symbols::is_dockerfile_path(f) => "docker",
            _ => continue,
        };
        set.insert(eco);
    }
    if has_workflows {
        set.insert("github-actions");
    }
    set
}

/// Dependabot (or Renovate) coverage of the implied ecosystems.
fn dependabot(repo: &Repo<'_>, anchor: &Workflow<'_>, out: &mut Vec<CiFinding>) {
    let implied = ecosystems(repo, true);
    let has = |p: &str| repo.files.iter().any(|f| f == p);
    let renovate = [
        "renovate.json",
        "renovate.json5",
        ".renovaterc",
        ".renovaterc.json",
        ".github/renovate.json",
        ".github/renovate.json5",
    ];
    if renovate.iter().any(|p| has(p)) {
        tracing::debug!("renovate configured; dependency-update check skipped");
        return;
    }
    let Some(path) = [".github/dependabot.yml", ".github/dependabot.yaml"]
        .into_iter()
        .find(|p| has(p))
    else {
        out.push(fire(
            CI012,
            Severity::Warn,
            (anchor.path, (0, 0)),
            format!("no `.github/dependabot.yml` or Renovate config, yet the repository uses {}; add a Dependabot config with one `updates` entry per ecosystem", join(&implied)),
            "dependabot:absent".to_owned(),
        ));
        return;
    };
    let Some(Value::Mapping(root)) =
        (repo.read)(path).and_then(|t| serde_yaml_ng::from_str::<Value>(&t).ok())
    else {
        tracing::warn!(path, "dependabot config unreadable; CI012 skips it");
        return;
    };
    let declared: BTreeSet<String> = root
        .get("updates")
        .and_then(Value::as_sequence)
        .into_iter()
        .flatten()
        .filter_map(|u| key(u, "package-ecosystem").and_then(Value::as_str))
        .map(|e| {
            if e == "uv" {
                "pip".to_owned()
            } else {
                e.to_owned()
            }
        })
        .collect();
    let missing: BTreeSet<&str> = implied
        .iter()
        .copied()
        .filter(|e| !declared.contains(*e))
        .collect();
    if !missing.is_empty() {
        out.push(fire(
            CI012,
            Severity::Warn,
            (path, (0, 0)),
            format!("Dependabot has no `updates` entry for {}, which the repository uses; add one per ecosystem", join(&missing)),
            "dependabot:missing".to_owned(),
        ));
    }
}

/// Comma-joined, backquoted names.
fn join<'a>(names: impl IntoIterator<Item = &'a &'a str>) -> String {
    names
        .into_iter()
        .map(|n| format!("`{n}`"))
        .collect::<Vec<_>>()
        .join(", ")
}

/// CODEOWNERS covering `.github` when the file exists.
fn codeowners(repo: &Repo<'_>, anchor: &str, out: &mut Vec<CiFinding>) {
    let Some(path) = ["CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"]
        .into_iter()
        .find(|p| repo.files.iter().any(|f| f == p))
    else {
        tracing::debug!(
            anchor,
            "no CODEOWNERS; the .github coverage check is skipped"
        );
        return;
    };
    let Some(text) = (repo.read)(path) else {
        return;
    };
    let covered = text
        .lines()
        .filter(|l| !l.trim_start().starts_with('#'))
        .filter_map(|l| l.split_whitespace().next())
        .any(|p| {
            matches!(
                p,
                "*" | "/.github/"
                    | ".github/"
                    | "/.github/**"
                    | ".github/**"
                    | "/.github"
                    | ".github"
            )
        });
    if !covered {
        out.push(fire(
            CI012,
            Severity::Warn,
            (path, (0, 0)),
            "CODEOWNERS has no entry covering `.github`, so workflow changes need no owner review; add `/.github/ @your-org/maintainers`".to_owned(),
            "codeowners:github".to_owned(),
        ));
    }
}
