//! `frob doctor`: report the environment; findings never make it fail.

use std::time::Duration;

use gob_cache::{Cache, CacheConfig};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;
use crate::config::FrobConfig;
use crate::workspace::{Located, registered_tables, table_refs};

/// How long a `--version` probe may run.
const PROBE_TIMEOUT: Duration = Duration::from_secs(10);

/// Report toolchain, git, cache, config and ledger health; never fails on findings.
#[derive(Debug, Clone, Copy, Default, gob_cli::Command)]
#[command(
    verb = "doctor",
    product = "frob",
    idempotent = true,
    exits(ok, refused)
)]
pub struct Doctor;

/// Versions of the tools frob shells out to.
#[derive(Debug, Serialize, JsonSchema)]
pub struct Toolchain {
    /// First line of `rustc --version`, when found.
    pub rustc: Option<String>,
    /// First line of `cargo --version`, when found.
    pub cargo: Option<String>,
}

/// Git discovery result.
#[derive(Debug, Serialize, JsonSchema)]
pub struct GitInfo {
    /// True when `cwd` is inside a repository.
    pub discovered: bool,
    /// Work tree root.
    pub root: Option<String>,
    /// Checked-out branch; absent when detached or not a repository.
    pub branch: Option<String>,
    /// `HEAD` commit id; absent on an unborn branch.
    pub head: Option<String>,
    /// True when this checkout is a linked worktree.
    pub linked_worktree: bool,
    /// Why discovery or a read failed.
    pub error: Option<String>,
}

/// Cache health.
#[derive(Debug, Serialize, JsonSchema)]
pub struct CacheInfo {
    /// `ok`, `null-fallback` (could not open) or `skipped: <why>`.
    pub state: String,
    /// Cache directory.
    pub dir: Option<String>,
    /// Rows in the artifacts table.
    pub artifacts: u64,
    /// Rows in the findings table.
    pub findings: u64,
    /// Rows in the repo-rule table.
    pub repo_rule: u64,
}

/// Config materialization status.
#[derive(Debug, Serialize, JsonSchema)]
pub struct ConfigInfo {
    /// The config file.
    pub path: String,
    /// True when it exists.
    pub present: bool,
    /// Materialized knobs absent from the file (each is a CFG001 finding).
    pub missing_knobs: usize,
    /// Load error (unknown key, bad TOML), when any.
    pub error: Option<String>,
}

/// Ledger ref reachability.
#[derive(Debug, Serialize, JsonSchema)]
pub struct LedgerInfo {
    /// The configured `[tickets] ref`.
    pub r#ref: String,
    /// True when the ref resolves to an object.
    pub reachable: bool,
    /// What it resolves to.
    pub oid: Option<String>,
    /// Why it does not resolve.
    pub error: Option<String>,
}

/// Output of `doctor`.
#[derive(Debug, Serialize, JsonSchema)]
pub struct DoctorData {
    /// Tool versions.
    pub toolchain: Toolchain,
    /// Git discovery.
    pub git: GitInfo,
    /// Cache health.
    pub cache: CacheInfo,
    /// Config status.
    pub config: ConfigInfo,
    /// Ledger ref.
    pub ledger: LedgerInfo,
}

/// First stdout line of `<program> --version`, or `None` when it cannot run.
fn probe(runner: &Runner, program: Program, cwd: &std::path::Path) -> Option<String> {
    let label = program.label();
    let spec = Spec {
        program,
        args: vec!["--version".to_owned()],
        cwd: Some(cwd.to_path_buf()),
        env: Vec::new(),
        timeout: PROBE_TIMEOUT,
        capture: true,
    };
    match runner.run(&spec) {
        Ok(out) if out.status == ExecOutcome::Exited(0) => {
            out.stdout.lines().next().map(str::to_owned)
        }
        Ok(out) => {
            tracing::warn!(tool = %label, status = ?out.status, "version probe failed");
            None
        }
        Err(e) => {
            tracing::warn!(tool = %label, error = %e, "version probe unavailable");
            None
        }
    }
}

impl Command for Doctor {
    type Data = DoctorData;

    fn from_matches(_matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<DoctorData> {
        let runner = Runner::new(Limits { jobs: 2 });
        let toolchain = Toolchain {
            rustc: probe(
                &runner,
                Program::Tool {
                    name: "rustc".to_owned(),
                },
                &ctx.cwd,
            ),
            cargo: probe(&runner, Program::Cargo, &ctx.cwd),
        };

        let located = Located::discover(&ctx.cwd);
        let git = git_info(&located, &ctx.cwd);

        let loaded = FrobConfig::load(&located.root);
        let (cfg, config_error) = match loaded {
            Ok(c) => (c, None),
            Err(e) => {
                tracing::info!(error = %e, "config did not load; using defaults");
                (FrobConfig::default(), Some(e.to_string()))
            }
        };

        let cache = cache_info(&located, &cfg);

        let descs = registered_tables();
        let findings = match gob_config::check(&located.root, PRODUCT, &table_refs(&descs)) {
            Ok(f) => f,
            Err(e) => {
                tracing::warn!(error = %e, "CFG001 check skipped");
                Vec::new()
            }
        };
        let path = located.root.join(format!("{PRODUCT}.toml"));
        let config = ConfigInfo {
            present: path.is_file(),
            path: path.display().to_string(),
            missing_knobs: findings.len(),
            error: config_error,
        };

        let ledger = ledger_info(&located, &cfg);
        tracing::info!(
            git = git.discovered,
            cache = %cache.state,
            ledger = ledger.reachable,
            missing_knobs = config.missing_knobs,
            "doctor finished"
        );
        Ok(Payload::new(DoctorData {
            toolchain,
            git,
            cache,
            config,
            ledger,
        })
        .with_findings(findings))
    }
}

fn git_info(located: &Located, cwd: &std::path::Path) -> GitInfo {
    let Some(repo) = &located.repo else {
        return GitInfo {
            discovered: false,
            root: None,
            branch: None,
            head: None,
            linked_worktree: false,
            error: Some(format!("no git repository at or above {}", cwd.display())),
        };
    };
    let (branch, head, error) = match repo.head() {
        Ok(h) => (h.branch, h.oid.map(|o| o.to_string()), None),
        Err(e) => (None, None, Some(e.to_string())),
    };
    GitInfo {
        discovered: true,
        root: repo.work_dir().map(|p| p.display().to_string()),
        branch,
        head,
        linked_worktree: repo.is_linked_worktree(),
        error,
    }
}

fn cache_info(located: &Located, cfg: &FrobConfig) -> CacheInfo {
    if located.repo.is_none() {
        return CacheInfo {
            state: "skipped: not a git repository".to_owned(),
            dir: None,
            artifacts: 0,
            findings: 0,
            repo_rule: 0,
        };
    }
    let dir = located.root.join(".frob");
    let cache = Cache::open_with(
        &dir,
        CacheConfig {
            busy_timeout: Duration::from_millis(cfg.cache.busy_timeout_ms),
        },
    );
    let stats = cache.stats();
    CacheInfo {
        state: if stats.null { "null-fallback" } else { "ok" }.to_owned(),
        dir: Some(dir.display().to_string()),
        artifacts: stats.artifacts,
        findings: stats.findings,
        repo_rule: stats.repo_rule,
    }
}

fn ledger_info(located: &Located, cfg: &FrobConfig) -> LedgerInfo {
    let name = cfg.tickets.r#ref.clone();
    let result = match &located.repo {
        Some(repo) => repo.rev_parse(&name).map_err(|e| e.to_string()),
        None => Err("not a git repository".to_owned()),
    };
    match result {
        Ok(oid) => LedgerInfo {
            r#ref: name,
            reachable: true,
            oid: Some(oid.to_string()),
            error: None,
        },
        Err(e) => LedgerInfo {
            r#ref: name,
            reachable: false,
            oid: None,
            error: Some(e),
        },
    }
}
