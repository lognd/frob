//! Check out the corpus and run the base and head binaries over it.
//!
//! Each project is fetched at its pinned commit into `<work>/<name>` (shallow, reused when the
//! directory already sits on that commit). Before every tool run the tree is cleaned of untracked
//! and ignored files so the first binary's caches cannot speed up or poison the second, and the
//! base/head order alternates between tools to spread any page-cache advantage evenly.
// frob:ticket 01M47QV23EAN5DE6DDV9HS3VP7

use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::{Limits, Program, Runner, Spec};

use super::{
    Corpus, EcosystemError, Project, ProjectReport, Report, Tool, ToolRun, classify, compare,
};

/// Longest a single tool run may take before it counts as a crash.
const TOOL_TIMEOUT: Duration = Duration::from_secs(600);

/// Longest a git step may take.
const GIT_TIMEOUT: Duration = Duration::from_mins(15);

/// What to run.
#[derive(Debug, Clone)]
pub struct Options {
    /// The parsed corpus.
    pub corpus: Corpus,
    /// Directory holding the base build's `frob`, `grimble` and `crunk`.
    pub base_bin: PathBuf,
    /// Directory holding the head build's binaries.
    pub head_bin: PathBuf,
    /// Directory the projects are checked out in.
    pub work: PathBuf,
    /// Restrict the run to these project names (all when empty).
    pub only: Vec<String>,
    /// Per-run timeout.
    pub timeout: Duration,
}

impl Options {
    /// Options with the default timeout and no project filter.
    #[must_use]
    pub fn new(corpus: Corpus, base_bin: PathBuf, head_bin: PathBuf, work: PathBuf) -> Self {
        Self {
            corpus,
            base_bin,
            head_bin,
            work,
            only: Vec::new(),
            timeout: TOOL_TIMEOUT,
        }
    }
}

fn git(runner: &Runner, cwd: &Path, args: &[&str]) -> Result<String, String> {
    let out = runner
        .run(&Spec {
            program: Program::Git,
            args: args.iter().map(|a| (*a).to_owned()).collect(),
            cwd: Some(cwd.to_path_buf()),
            env: vec![("GIT_TERMINAL_PROMPT".to_owned(), "0".to_owned())],
            timeout: GIT_TIMEOUT,
            capture: true,
        })
        .map_err(|e| format!("git {}: {e}", args.first().copied().unwrap_or_default()))?;
    match out.status {
        gob_exec::Outcome::Exited(0) => Ok(out.stdout_raw),
        other => Err(format!(
            "git {} ended {other:?}: {}",
            args.first().copied().unwrap_or_default(),
            out.stderr.trim()
        )),
    }
}

/// Make `<work>/<name>` a clean tree at the project's pinned commit and return its path.
///
/// # Errors
/// [`EcosystemError::Checkout`] when git cannot fetch or check out the commit.
pub fn checkout(
    runner: &Runner,
    work: &Path,
    project: &Project,
) -> Result<PathBuf, EcosystemError> {
    let fail = |detail: String| EcosystemError::Checkout {
        project: project.name.clone(),
        detail,
    };
    let dir = work.join(&project.name);
    if dir.join(".git").exists()
        && git(runner, &dir, &["rev-parse", "HEAD"]).is_ok_and(|h| h.trim() == project.sha)
    {
        tracing::debug!(project = %project.name, "checkout reused");
        git(runner, &dir, &["clean", "-fdxq"]).map_err(fail)?;
        return Ok(dir);
    }
    if dir.exists() {
        std::fs::remove_dir_all(&dir).map_err(|e| fail(format!("clear stale checkout: {e}")))?;
    }
    std::fs::create_dir_all(&dir).map_err(|e| fail(format!("create checkout dir: {e}")))?;
    tracing::info!(project = %project.name, repo = %project.repo, "fetching");
    git(runner, &dir, &["init", "-q"]).map_err(fail)?;
    git(
        runner,
        &dir,
        &["fetch", "-q", "--depth", "1", &project.repo, &project.sha],
    )
    .map_err(fail)?;
    git(runner, &dir, &["checkout", "-q", "--detach", "FETCH_HEAD"]).map_err(fail)?;
    Ok(dir)
}

/// Run `bin_dir/<tool> check --json` in `dir` and classify the result.
pub fn run_tool(
    runner: &Runner,
    bin_dir: &Path,
    tool: Tool,
    dir: &Path,
    timeout: Duration,
) -> ToolRun {
    let exe = bin_dir.join(tool.name());
    if let Err(e) = git(runner, dir, &["clean", "-fdxq"]) {
        return ToolRun::crashed(format!("could not reset the checkout: {e}"));
    }
    if tool == Tool::Frob {
        let cfg = dir.join("frob.toml");
        if !cfg.exists()
            && let Err(e) = std::fs::write(&cfg, "")
        {
            return ToolRun::crashed(format!("could not write frob.toml: {e}"));
        }
    }
    let result = runner.run(&Spec {
        program: Program::Hook { path: exe.clone() },
        args: vec!["check".to_owned(), "--json".to_owned()],
        cwd: Some(dir.to_path_buf()),
        env: vec![("NO_COLOR".to_owned(), "1".to_owned())],
        timeout,
        capture: true,
    });
    match result {
        Ok(out) => {
            let wall_ms = out.duration.as_secs_f64() * 1000.0;
            let run = classify(out.status, &out.stdout_raw, &out.stderr, wall_ms);
            tracing::info!(tool = tool.name(), status = ?run.status, wall_ms, "ran");
            run
        }
        Err(e) => {
            tracing::warn!(tool = tool.name(), error = %e, "could not spawn");
            ToolRun::crashed(format!("could not start {}: {e}", exe.to_string_lossy()))
        }
    }
}

/// Check out and run every selected project with both builds, and collect the report.
///
/// A project that cannot be fetched is recorded in the report and the corpus carries on.
pub fn run(opts: &Options, say: &mut dyn FnMut(&str)) -> Report {
    let runner = Runner::new(Limits { jobs: 1 });
    let mut report = Report::default();
    for project in &opts.corpus.projects {
        if !opts.only.is_empty() && !opts.only.contains(&project.name) {
            continue;
        }
        say(&format!("ecosystem: {}", project.name));
        let mut pr = ProjectReport {
            name: project.name.clone(),
            language: project.language,
            sha: project.sha.clone(),
            setup_error: None,
            tools: Vec::new(),
        };
        match checkout(&runner, &opts.work, project) {
            Err(e) => {
                tracing::warn!(project = %project.name, error = %e, "checkout failed");
                pr.setup_error = Some(e.to_string());
            }
            Ok(dir) => {
                for (i, tool) in project.tools().into_iter().enumerate() {
                    let go = |bin: &Path| run_tool(&runner, bin, tool, &dir, opts.timeout);
                    let (base, head) = if i % 2 == 0 {
                        let b = go(&opts.base_bin);
                        (b, go(&opts.head_bin))
                    } else {
                        let h = go(&opts.head_bin);
                        (go(&opts.base_bin), h)
                    };
                    pr.tools.push(compare(tool, &base, &head));
                }
            }
        }
        report.projects.push(pr);
    }
    report
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    use crate::ecosystem::{Language, Verdict};
    use std::os::unix::fs::PermissionsExt;

    fn script(dir: &Path, name: &str, body: &str) {
        let p = dir.join(name);
        std::fs::write(&p, format!("#!/bin/sh\n{body}\n")).unwrap();
        std::fs::set_permissions(&p, std::fs::Permissions::from_mode(0o755)).unwrap();
    }

    fn bins(dir: &Path, body: &str) -> PathBuf {
        std::fs::create_dir_all(dir).unwrap();
        for t in Tool::ALL {
            script(dir, t.name(), body);
        }
        dir.to_path_buf()
    }

    /// A one-commit local repository and its sha.
    fn origin(root: &Path, runner: &Runner) -> (PathBuf, String) {
        let repo = root.join("origin");
        std::fs::create_dir_all(&repo).unwrap();
        git(runner, &repo, &["init", "-q"]).unwrap();
        std::fs::write(repo.join("a.txt"), "x").unwrap();
        git(runner, &repo, &["add", "."]).unwrap();
        git(
            runner,
            &repo,
            &[
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@example.com",
                "commit",
                "-q",
                "-m",
                "c",
            ],
        )
        .unwrap();
        let sha = git(runner, &repo, &["rev-parse", "HEAD"])
            .unwrap()
            .trim()
            .to_owned();
        (repo, sha)
    }

    fn options(root: &Path, repo: &Path, sha: &str, base: PathBuf, head: PathBuf) -> Options {
        let corpus = Corpus {
            projects: vec![Project {
                name: "demo".into(),
                language: Language::Rust,
                repo: repo.to_string_lossy().into_owned(),
                sha: sha.to_owned(),
                tools: Some(vec![Tool::Frob, Tool::Grimble]),
            }],
        };
        Options::new(corpus, base, head, root.join("work"))
    }

    const CLEAN: &str = r#"echo '{"verb":"check","ok":true,"findings":[],"error":null}'"#;
    const ONE: &str = r#"echo '{"verb":"check","ok":false,"findings":[{"rule":"R9","severity":"error","file":"a.txt","line":1,"message":"m"}],"error":null}'; exit 1"#;

    // frob:tests crates/gob-dev/src/ecosystem/run.rs::checkout
    #[test]
    fn checkout_pins_the_commit_and_is_reusable() {
        let root = tempfile::tempdir().unwrap();
        let runner = Runner::new(Limits { jobs: 1 });
        let (repo, sha) = origin(root.path(), &runner);
        let p = Project {
            name: "demo".into(),
            language: Language::Rust,
            repo: repo.to_string_lossy().into_owned(),
            sha: sha.clone(),
            tools: None,
        };
        let work = root.path().join("work");
        let dir = checkout(&runner, &work, &p).unwrap();
        assert_eq!(
            git(&runner, &dir, &["rev-parse", "HEAD"]).unwrap().trim(),
            sha
        );
        std::fs::write(dir.join("junk"), "").unwrap();
        let again = checkout(&runner, &work, &p).unwrap();
        assert!(!again.join("junk").exists());
        let bad = Project {
            sha: "0".repeat(40),
            ..p
        };
        assert!(matches!(
            checkout(&runner, &work, &bad),
            Err(EcosystemError::Checkout { .. })
        ));
    }

    // frob:tests crates/gob-dev/src/ecosystem/run.rs::run
    #[test]
    fn a_head_crash_is_reported_not_hidden() {
        let root = tempfile::tempdir().unwrap();
        let runner = Runner::new(Limits { jobs: 1 });
        let (repo, sha) = origin(root.path(), &runner);
        let base = bins(&root.path().join("base"), CLEAN);
        let head = bins(
            &root.path().join("head"),
            "echo 'thread main panicked' >&2; exit 101",
        );
        let report = run(&options(root.path(), &repo, &sha, base, head), &mut |_| {});
        assert_eq!(
            report.head_crashes(),
            vec!["demo/frob".to_owned(), "demo/grimble".to_owned()]
        );
        assert!(matches!(
            report.projects[0].tools[0].verdict,
            Verdict::HeadFailed { .. }
        ));
        let md = crate::ecosystem::render(&report);
        assert!(md.contains("Head crashes (2)"), "{md}");
        assert!(md.contains("panicked"), "{md}");
    }

    // frob:tests crates/gob-dev/src/ecosystem/run.rs::run
    #[test]
    fn findings_diff_across_both_builds() {
        let root = tempfile::tempdir().unwrap();
        let runner = Runner::new(Limits { jobs: 1 });
        let (repo, sha) = origin(root.path(), &runner);
        let base = bins(&root.path().join("base"), CLEAN);
        let head = bins(&root.path().join("head"), ONE);
        let report = run(&options(root.path(), &repo, &sha, base, head), &mut |_| {});
        let Verdict::Compared { deltas, .. } = &report.projects[0].tools[0].verdict else {
            panic!("{report:?}");
        };
        assert_eq!((deltas[0].rule.as_str(), deltas[0].added), ("R9", 1));
        assert!(report.head_crashes().is_empty());
    }

    // frob:tests crates/gob-dev/src/ecosystem/run.rs::run
    #[test]
    fn a_missing_binary_is_a_crash_and_an_unfetchable_project_is_recorded() {
        let root = tempfile::tempdir().unwrap();
        let runner = Runner::new(Limits { jobs: 1 });
        let (repo, sha) = origin(root.path(), &runner);
        let base = bins(&root.path().join("base"), CLEAN);
        let missing = root.path().join("nope");
        let report = run(
            &options(root.path(), &repo, &sha, base.clone(), missing),
            &mut |_| {},
        );
        assert_eq!(report.head_crashes().len(), 2);
        let mut o = options(root.path(), &repo, &"1".repeat(40), base.clone(), base);
        o.work = root.path().join("work2");
        let report = run(&o, &mut |_| {});
        assert!(report.projects[0].setup_error.is_some());
    }
}
