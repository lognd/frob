//! Change detection (`cargo dev changes`, `cargo dev ci --since`): map a diff to CI job sets.
//!
//! The mapping is data, `crates/gob-dev/changes.toml`, shared with the `changes` job of
//! `.github/workflows/ci.yml` (through `.github/scripts/plan-jobs.py`, which needs no compile).
//! A docs-only diff selects only the steps in `docs_only_steps`; anything else selects the full
//! set. Process spawning goes through `gob-exec` (PROC001). Design: `docs/design/build-test-ci.md`
//! section 6 (ruff `determine_changes`).
// frob:ticket 01M47QVD03PGCAZ301WHC5Q4MF

use std::path::Path;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde::Deserialize;

/// The mapping data, embedded so the tool needs no file at run time.
const MAP_TOML: &str = include_str!("../changes.toml");

/// Wall-clock limit for the `git diff` query.
const DIFF_TIMEOUT: Duration = Duration::from_mins(2);

/// Why a plan could not be computed.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum ChangesError {
    /// `changes.toml` is malformed or names an unknown class.
    #[error("changes.toml: {0}")]
    Map(String),
    /// `git diff` could not list the changed files.
    #[error("git diff {base}: {reason}")]
    Diff {
        /// The diff base that was requested.
        base: String,
        /// Why listing failed.
        reason: String,
    },
}

/// One class of paths in `changes.toml`.
#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
struct Class {
    name: String,
    prefixes: Vec<String>,
}

/// The parsed mapping data.
#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct ChangeMap {
    /// Ci step names a docs-only diff still runs.
    docs_only_steps: Vec<String>,
    /// The path classes.
    class: Vec<Class>,
}

/// Which job sets a diff needs.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
#[allow(clippy::struct_excessive_bools)] // one flag per CI job output
pub struct Plan {
    /// Some non-docs file changed, so a Rust job can be affected.
    pub rust: bool,
    /// A change outside crunk needs the whole workspace.
    pub full: bool,
    /// A crunk crate or `docs/crunk` changed.
    pub crunk: bool,
    /// The node Tailwind runtime (and playwright) paths changed.
    pub node: bool,
    /// A workflow or local action changed.
    pub workflows: bool,
    /// Every changed path is documentation no Rust job reads.
    pub docs_only: bool,
}

impl Plan {
    /// The plan that runs everything, used when the diff cannot be read.
    #[must_use]
    pub fn everything() -> Self {
        Self {
            rust: true,
            full: true,
            crunk: false,
            node: true,
            workflows: true,
            docs_only: false,
        }
    }

    /// `key=value` lines for `$GITHUB_OUTPUT`.
    #[must_use]
    pub fn render(&self) -> Vec<String> {
        [
            ("rust", self.rust),
            ("full", self.full),
            ("crunk", self.crunk),
            ("node", self.node),
            ("workflows", self.workflows),
            ("docs_only", self.docs_only),
        ]
        .iter()
        .map(|(k, v)| format!("{k}={v}"))
        .collect()
    }
}

impl ChangeMap {
    /// The mapping embedded from `changes.toml`.
    ///
    /// # Errors
    /// [`ChangesError::Map`] when the data is malformed or names an unknown class.
    pub fn builtin() -> Result<Self, ChangesError> {
        Self::parse(MAP_TOML)
    }

    /// Parse mapping data and check every class name is known.
    fn parse(text: &str) -> Result<Self, ChangesError> {
        let map: Self = toml::from_str(text).map_err(|e| ChangesError::Map(e.to_string()))?;
        for c in &map.class {
            if !["docs", "crunk", "node", "workflows"].contains(&c.name.as_str()) {
                return Err(ChangesError::Map(format!("unknown class {:?}", c.name)));
            }
        }
        Ok(map)
    }

    fn matches(&self, class: &str, path: &str) -> bool {
        self.class
            .iter()
            .filter(|c| c.name == class)
            .flat_map(|c| &c.prefixes)
            .any(|p| path.starts_with(p.as_str()))
    }

    /// Map the changed `paths` to the job sets that must run.
    #[must_use]
    pub fn plan<S: AsRef<str>>(&self, paths: &[S]) -> Plan {
        let paths: Vec<&str> = paths
            .iter()
            .map(AsRef::as_ref)
            .filter(|p| !p.is_empty())
            .collect();
        let rest: Vec<&str> = paths
            .iter()
            .copied()
            .filter(|p| !self.matches("docs", p))
            .collect();
        let plan = Plan {
            rust: !rest.is_empty(),
            full: rest.iter().any(|p| !self.matches("crunk", p)),
            crunk: rest.iter().any(|p| self.matches("crunk", p)),
            node: rest.iter().any(|p| self.matches("node", p)),
            workflows: rest.iter().any(|p| self.matches("workflows", p)),
            docs_only: !paths.is_empty() && rest.is_empty(),
        };
        tracing::info!(paths = paths.len(), ?plan, "change plan computed");
        plan
    }

    /// The ci steps `plan` selects from `all`: the docs-only subset for a docs-only diff, else all.
    #[must_use]
    pub fn select_steps(&self, plan: &Plan, all: &[String]) -> Vec<String> {
        if !plan.docs_only {
            return all.to_vec();
        }
        all.iter()
            .filter(|s| self.docs_only_steps.contains(s))
            .cloned()
            .collect()
    }
}

/// The files changed between `base` and the work tree head, one repo-relative path each.
///
/// # Errors
/// [`ChangesError::Diff`] when git cannot be run or exits non-zero.
pub fn diff_paths(root: &Path, base: &str) -> Result<Vec<String>, ChangesError> {
    let fail = |reason: String| {
        tracing::error!(base, %reason, "git diff failed");
        ChangesError::Diff {
            base: base.to_owned(),
            reason,
        }
    };
    let spec = Spec {
        program: Program::Git,
        args: ["diff", "--name-only", base, "HEAD"]
            .iter()
            .map(|s| (*s).to_owned())
            .collect(),
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: DIFF_TIMEOUT,
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .map_err(|e| fail(e.to_string()))?;
    if out.status != Outcome::Exited(0) {
        return Err(fail(format!("{:?}", out.status)));
    }
    Ok(out.stdout.lines().map(str::to_owned).collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn map() -> ChangeMap {
        ChangeMap::builtin().unwrap()
    }

    fn all_steps() -> Vec<String> {
        ["fmt", "clippy", "nextest", "gen", "check"]
            .iter()
            .map(|s| (*s).to_owned())
            .collect()
    }

    // frob:tests crates/gob-dev/src/changes.rs::ChangeMap.select_steps
    #[test]
    fn docs_only_diff_selects_only_fmt_gen_and_check() {
        let m = map();
        let plan = m.plan(&["notes/a.md", "docs/design/x.md", "changelog.d/a.added.md"]);
        assert!(plan.docs_only && !plan.rust && !plan.full && !plan.crunk);
        assert_eq!(m.select_steps(&plan, &all_steps()), ["fmt", "gen", "check"]);
    }

    // frob:tests crates/gob-dev/src/changes.rs::ChangeMap.plan
    #[test]
    fn rust_diff_selects_the_full_set() {
        let m = map();
        for path in [
            "crates/gob-fix/src/lib.rs",
            "Cargo.lock",
            "docs/guides/x.md",
        ] {
            let plan = m.plan(&[path]);
            assert!(plan.rust && plan.full && !plan.docs_only, "{path}");
            assert_eq!(m.select_steps(&plan, &all_steps()), all_steps(), "{path}");
        }
        // Docs mixed with code is not docs only.
        let plan = m.plan(&["notes/a.md", "crates/gob-fix/src/lib.rs"]);
        assert!(plan.full && !plan.docs_only);
    }

    // frob:tests crates/gob-dev/src/changes.rs::ChangeMap.plan
    #[test]
    fn crunk_diff_runs_the_crunk_job_not_the_workspace() {
        let plan = map().plan(&["crates/crunk-values/src/color.rs", "tickets/x/ticket.md"]);
        assert!(plan.rust && plan.crunk && !plan.full && !plan.node);
        // Mixed with a gob crate the workspace job covers crunk too.
        let plan = map().plan(&[
            "crates/crunk-values/src/lib.rs",
            "crates/gob-fix/src/lib.rs",
        ]);
        assert!(plan.full);
        // docs/crunk is read by the generated-file check, so it is not docs.
        assert!(map().plan(&["docs/crunk/ci.md"]).crunk);
    }

    // frob:tests crates/gob-dev/src/changes.rs::ChangeMap.plan
    #[test]
    fn node_diff_selects_the_node_and_playwright_job() {
        let m = map();
        assert!(m.plan(&["crates/crunk-tailwind/node/helper.mjs"]).node);
        assert!(m.plan(&["crates/crunk-tailwind/tests/a.rs"]).node);
        assert!(!m.plan(&["crates/crunk-values/src/lib.rs"]).node);
    }

    // frob:tests crates/gob-dev/src/changes.rs::ChangeMap.plan
    #[test]
    fn workflow_diff_sets_the_workflows_flag_and_runs_everything() {
        let m = map();
        let plan = m.plan(&[".github/workflows/ci.yml"]);
        assert!(plan.workflows && plan.rust && plan.full && !plan.docs_only);
        assert!(!m.plan(&["crates/gob-fix/src/lib.rs"]).workflows);
    }

    // frob:tests crates/gob-dev/src/changes.rs::ChangeMap.parse
    #[test]
    fn unknown_class_names_are_rejected() {
        let bad = "docs_only_steps = []\n[[class]]\nname = \"mystery\"\nprefixes = []\n";
        assert!(matches!(ChangeMap::parse(bad), Err(ChangesError::Map(_))));
    }

    // frob:tests crates/gob-dev/src/changes.rs::Plan.render
    #[test]
    fn render_prints_key_value_lines() {
        let lines = Plan::everything().render();
        assert_eq!(lines[0], "rust=true");
        assert_eq!(lines[1], "full=true");
        assert_eq!(lines[5], "docs_only=false");
    }

    // frob:tests crates/gob-dev/src/changes.rs::ChangeMap.plan
    #[test]
    fn an_empty_diff_is_not_docs_only() {
        let plan = map().plan::<&str>(&[]);
        assert!(!plan.docs_only && !plan.rust);
    }
}
