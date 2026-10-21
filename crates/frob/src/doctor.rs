//! `frob doctor`: report the environment; findings never make it fail.

use gob_path::Shown;
use std::collections::BTreeMap;
use std::time::Duration;

use frob_mirror::github::adapter::{HttpRequest, HttpTransport, Method};
use frob_mirror::github::http::NativeTransport;
use frob_obligations::tick_protect::{self, ProtectionProbe, Reply, Verdict};
use frob_worktree::gc::{self, Mode, pass::Report};
use gob_cache::{Cache, CacheConfig};
use gob_check::{OtherCopy, SiblingRow};
use gob_cli::{CliError, Context, Outcome, Payload};
use gob_exec::{Limits, Outcome as ExecOutcome, Program, Runner, Spec, find_sibling};
use gob_symbols::{Fidelity, adapter_for, fidelity_report};
use gob_walk::{WalkConfig, walk};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;
use crate::config::FrobConfig;
use crate::init::{DriverVerdict, configured_driver, fix_command, judge_driver};
use crate::mirror_recreate_cmd::{TOKEN_VARS, resolve_repo};
use crate::workspace::{Located, registered_tables, table_refs};

/// How long a `--version` probe may run.
const PROBE_TIMEOUT: Duration = Duration::from_secs(10);

/// One-line summary of `frob doctor` (the generic verb's metadata).
pub const SUMMARY: &str =
    "Report toolchain, git, cache, config and ledger health; never fails on findings.";

// frob:ticket 01M47QSHBWSGEYXJ56PR6FQBS9
/// The flags and survey behind `frob doctor`, run through the generic `gob-product` verb.
#[derive(Debug, Clone, Copy, Default)]
pub struct Doctor {
    /// Also report each language adapter's fidelity and capability precisions.
    languages: bool,
    /// Run the garbage-collection pass now, unthrottled, and report what it reclaimed.
    fix: bool,
    /// Also run the dry-run garbage-collection plan (what a pass would reclaim); costly, so opt-in.
    gc_plan: bool,
}

/// One capability of an adapter with its precision label.
#[derive(Debug, Serialize, JsonSchema)]
pub struct CapabilityRow {
    /// Capability name (`resolve_ref`, `apply_targets`, ...).
    pub capability: String,
    /// Precision label (`lexical+imports`, `none`, `not-applicable`, ...).
    pub precision: String,
}

/// One language adapter.
#[derive(Debug, Serialize, JsonSchema)]
pub struct LanguageRow {
    /// Language tag (`rust`, `markdown`).
    pub language: String,
    /// Fidelity level, `F0` to `F4` (universal-model.md 3.3).
    pub fidelity: String,
    /// Adapter name, version and grammar identity (the cache key component).
    pub adapter: String,
    /// Walked files this adapter claims.
    pub files: usize,
    /// Capability precisions in table order.
    pub capabilities: Vec<CapabilityRow>,
}

/// A walked file extension no adapter claims: one opaque unit per file at F0.
#[derive(Debug, Serialize, JsonSchema)]
pub struct UnadaptedRow {
    /// The extension with its dot, or `(none)`.
    pub extension: String,
    /// Always `F0`.
    pub fidelity: String,
    /// Always `opaque(no-adapter)`.
    pub unit: String,
    /// Walked files with this extension.
    pub files: usize,
}

/// `doctor --languages`: adapters and the extensions that have none.
#[derive(Debug, Serialize, JsonSchema)]
pub struct LanguagesReport {
    /// Every adapter, then the F0 adapter.
    pub adapters: Vec<LanguageRow>,
    /// Extensions with no adapter, sorted.
    pub unadapted: Vec<UnadaptedRow>,
}

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
    /// Ledger-branch protection through the hosting API: `protected`, `unprotected`, `unresolved` or `skipped`.
    pub protection: String,
    /// What the hosting API said (or why it could not be asked) when `protection` is not `protected`.
    pub protection_detail: Option<String>,
}

/// The configured ledger merge driver against the running frob.
#[derive(Debug, Serialize, JsonSchema)]
pub struct DriverCheck {
    /// `ok`, `mismatch` (a different frob), `unresolvable`, `unset` or `skipped`.
    pub state: String,
    /// The configured driver command, when set.
    pub command: Option<String>,
    /// What went wrong, when not `ok`.
    pub detail: Option<String>,
    /// The exact command that fixes it, when not `ok`.
    pub fix: Option<String>,
}

/// Bytes and item count of one garbage-collection category.
#[derive(Debug, Serialize, JsonSchema)]
pub struct GcCategory {
    /// `worktrees`, `build`, `caches`, `artifacts` or `land-base`.
    pub category: String,
    /// How many items.
    pub items: usize,
    /// Their total bytes.
    pub bytes: u64,
}

/// What `doctor --fix` collected.
#[derive(Debug, Serialize, JsonSchema)]
pub struct GcFixed {
    /// Bytes reclaimed by the pass.
    pub reclaimed_bytes: u64,
    /// Reclaimed per category.
    pub by_category: Vec<GcCategory>,
    /// Problems the pass met (they never fail it).
    pub warnings: Vec<String>,
}

/// Garbage-collection state: the last pass, current usage, and what a pass would reclaim now.
#[derive(Debug, Serialize, JsonSchema)]
pub struct GcInfo {
    /// `ok`, or `skipped: <why>` when there is no repository or the report could not be built.
    pub state: String,
    /// Unix seconds of the last pass, absent when none ran.
    pub last_run_unix: Option<i64>,
    /// Bytes the last pass reclaimed.
    pub last_reclaimed_bytes: u64,
    /// Bytes reclaimed over all passes.
    pub total_reclaimed_bytes: u64,
    /// Passes so far.
    pub passes: u64,
    /// Current usage per category.
    pub usage: Vec<frob_worktree::gc::stamp::Usage>,
    /// What a pass would reclaim now (a dry run), per category.
    pub would_reclaim: Vec<GcCategory>,
    /// Total bytes a pass would reclaim now.
    pub would_reclaim_bytes: u64,
    /// Things a pass keeps on purpose, with reasons.
    pub kept: Vec<frob_worktree::gc::pass::Kept>,
    /// Present with `--fix`: what the pass just collected.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub fixed: Option<GcFixed>,
}

/// Lease-file health: unreadable lease files and what `--fix` did about them.
#[derive(Debug, Serialize, JsonSchema)]
pub struct LeaseInfo {
    /// `ok`, or `skipped: <why>` when there is no repository work tree or the store could not be read.
    pub state: String,
    /// Lease files that cannot be parsed (path and parse error); they are skipped by every verb.
    pub corrupt: Vec<frob_lease::CorruptLease>,
    /// Present with `--fix`: where each corrupt file was moved (`<name>.toml.corrupt`).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub quarantined: Option<Vec<String>>,
}

/// Local lands not on origin: the row 52 count `frob refresh` prints, as a doctor section.
#[derive(Debug, Serialize, JsonSchema)]
pub struct LandsInfo {
    /// `ok`, or `skipped: <why>` when there is no work tree, remote base ref or readable ledger.
    pub state: String,
    /// Done tickets whose land commit origin's base lacks, as `<handle> at <commit>`.
    pub lands: Vec<String>,
    /// Tickets whose latest lease event is an eviction.
    pub evicted: usize,
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
    /// Merge driver resolution.
    pub driver: DriverCheck,
    /// Sibling binaries: which location is used and any second copy with its version.
    pub siblings: Vec<SiblingRow>,
    /// Garbage collection: last pass, usage and what a pass would reclaim.
    pub gc: GcInfo,
    /// Lease files: corrupt ones and their quarantine.
    pub leases: LeaseInfo,
    /// Local lands origin's base lacks (distributed-tickets.md row 52).
    pub lands: LandsInfo,
    /// Language adapters; present only with `--languages`.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub languages: Option<LanguagesReport>,
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

/// The siblings frob spawns, in discovery order.
const SIBLING_PRODUCTS: [&str; 2] = ["grimble", "crunk"];

/// Discover `product` with [`find_sibling`] and probe the copy in use and any second copy.
// frob:ticket 01M421F7Q66MW38R7J1JS1VMBC
fn sibling_row(runner: &Runner, product: &str, cwd: &std::path::Path) -> SiblingRow {
    let version_of = |path: &std::path::Path| {
        probe(
            runner,
            Program::Hook {
                path: path.to_path_buf(),
            },
            cwd,
        )
    };
    let Ok(found) = find_sibling(product) else {
        return SiblingRow {
            product: product.to_owned(),
            location: "absent".to_owned(),
            path: None,
            version: None,
            other: None,
        };
    };
    let version = version_of(&found.path);
    let other = found.other.as_deref().map(|p| {
        let other_version = version_of(p);
        OtherCopy {
            path: Shown::of(p).to_string(),
            differs: other_version != version,
            version: other_version,
        }
    });
    SiblingRow {
        product: product.to_owned(),
        location: found.origin.label().to_owned(),
        path: Some(Shown::of(&found.path).to_string()),
        version,
        other,
    }
}

/// `Doctor` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct DoctorArgs {
    #[arg(
        long,
        help = "Report each adapter's fidelity and capability precisions"
    )]
    languages: bool,
    #[arg(
        long,
        help = "Run the garbage-collection pass now, unthrottled, and report it"
    )]
    fix: bool,
    #[arg(
        long,
        help = "Also run the dry-run garbage-collection plan (slower): what a pass would reclaim"
    )]
    gc_plan: bool,
}

impl Doctor {
    /// Add the `--languages` and `--fix` flags to the generic `doctor` verb.
    pub fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<DoctorArgs>(cmd)
    }

    /// Read the flags back from the parsed matches.
    ///
    /// # Errors
    ///
    /// Never today; the signature matches the verb contract.
    pub fn from_matches(matches: &gob_cli::clap::ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<DoctorArgs>(matches)?;
        Ok(Self {
            languages: a.languages,
            fix: a.fix,
            gc_plan: a.gc_plan,
        })
    }

    /// Survey the environment and return the report.
    ///
    /// # Errors
    ///
    /// A refusal when the merge-driver check cannot read the repository config.
    pub fn run(&self, ctx: &Context) -> Outcome<DoctorData> {
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
        // frob:ticket 01M42EZ8J63P84XFKTR2GXRW72
        if let Some(repo) = &located.repo {
            frob_ledger::redact::RuleSet::mention_local_files(repo.common_dir());
        }

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
            path: Shown::of(&path).to_string(),
            missing_knobs: findings.len(),
            error: config_error,
        };

        let (ledger, protection) = ledger_with_protection(&located, &cfg);
        let driver = driver_check(&located)?;
        let siblings: Vec<SiblingRow> = SIBLING_PRODUCTS
            .iter()
            .map(|p| sibling_row(&runner, p, &ctx.cwd))
            .collect();
        let gc = gc_info(&located, &cfg, self.fix, self.gc_plan, &ctx.clock);
        let leases = lease_info(&located, &cfg, self.fix, &ctx.clock);
        let lands = lands_info(&located, &cfg, &ctx.clock);
        let languages = self
            .languages
            .then(|| languages_report(&located.root, &cfg));
        tracing::info!(
            git = git.discovered,
            cache = %cache.state,
            ledger = ledger.reachable,
            missing_knobs = config.missing_knobs,
            "doctor finished"
        );
        let mut warnings: Vec<String> = driver
            .detail
            .as_ref()
            .zip(driver.fix.as_ref())
            .map(|(d, f)| format!("{d}; fix: {f}"))
            .into_iter()
            .collect();
        for c in &leases.corrupt {
            warnings.push(format!(
                "corrupt lease file {} ({}); remedy: run `frob doctor --fix` to move it aside as <name>.toml.corrupt",
                Shown::of(&c.path),
                c.message
            ));
        }
        warnings.extend(lands_warning(&lands, &cfg.sync.remote));
        // frob:ticket 01M5BJ2EVKDA4RYRDFRVHZ1FDQ
        warnings.extend(crate::agent_cmd::drift_warnings(&located.root, &cfg));
        warnings.extend(sibling_warnings(&siblings));
        let payload = Payload::new(DoctorData {
            toolchain,
            git,
            cache,
            config,
            ledger,
            driver,
            siblings,
            gc,
            leases,
            lands,
            languages,
        })
        .with_findings(findings.into_iter().chain(protection).collect());
        Ok(warnings
            .into_iter()
            .fold(payload, gob_cli::Payload::with_warning))
    }
}

/// Judge the configured merge driver; a missing repository or an unset driver is not a problem.
fn driver_check(located: &Located) -> Result<DriverCheck, CliError> {
    let mut check = DriverCheck {
        state: "skipped".to_owned(),
        command: None,
        detail: None,
        fix: None,
    };
    if located.repo.is_none() {
        return Ok(check);
    }
    let Some(command) = configured_driver(&located.root)? else {
        "unset".clone_into(&mut check.state);
        return Ok(check);
    };
    let (state, detail) = match judge_driver(&command)? {
        DriverVerdict::Same => ("ok", None),
        DriverVerdict::Other(p) => (
            "mismatch",
            Some(format!(
                "merge driver `{command}` resolves to {p}, a different frob than the running one"
            )),
        ),
        DriverVerdict::Unresolvable(why) => (
            "unresolvable",
            Some(format!("merge driver `{command}` does not resolve: {why}")),
        ),
    };
    if detail.is_some() {
        check.fix = Some(fix_command());
    }
    state.clone_into(&mut check.state);
    check.detail = detail;
    check.command = Some(command);
    tracing::info!(state = %check.state, "merge driver checked");
    Ok(check)
}

/// Adapters with their fidelity and capabilities, plus the walked extensions with none.
fn languages_report(root: &std::path::Path, cfg: &FrobConfig) -> LanguagesReport {
    let mut exclude = vec!["/.frob/".to_owned(), "/target/".to_owned()];
    exclude.extend(cfg.check.exclude.iter().cloned());
    let walked = walk(
        root,
        &WalkConfig {
            exclude,
            size_cap: cfg.check.size_cap,
            ..WalkConfig::default()
        },
    );
    let files = match walked {
        Ok(w) => w.files,
        Err(e) => {
            tracing::warn!(error = %e, "walk failed; language report has no file counts");
            Vec::new()
        }
    };
    let mut claimed: BTreeMap<&'static str, usize> = BTreeMap::new();
    let mut unadapted: BTreeMap<String, usize> = BTreeMap::new();
    for f in &files {
        if let Some(a) = adapter_for(&f.language) {
            *claimed.entry(a.language()).or_default() += 1;
        } else {
            let ext = std::path::Path::new(&f.path)
                .extension()
                .map(crate::pathtext::name_text)
                .map_or_else(
                    || "(none)".to_owned(),
                    |e| format!(".{}", e.to_ascii_lowercase()),
                );
            *unadapted.entry(ext).or_default() += 1;
        }
    }
    let mut rows: Vec<LanguageRow> = fidelity_report()
        .into_iter()
        .map(|a| LanguageRow {
            language: a.language.to_owned(),
            fidelity: a.fidelity.to_string(),
            adapter: a.identity,
            files: claimed.get(a.language).copied().unwrap_or(0),
            capabilities: a
                .capabilities
                .into_iter()
                .map(|(c, p)| CapabilityRow {
                    capability: c.name().to_owned(),
                    precision: p.label().to_owned(),
                })
                .collect(),
        })
        .collect();
    for r in &mut rows {
        if r.language == "opaque" {
            r.files = unadapted.values().sum();
        }
    }
    tracing::info!(
        adapters = rows.len(),
        extensions = unadapted.len(),
        "language report"
    );
    LanguagesReport {
        adapters: rows,
        unadapted: unadapted
            .into_iter()
            .map(|(extension, files)| UnadaptedRow {
                extension,
                fidelity: Fidelity::F0.to_string(),
                unit: "opaque(no-adapter)".to_owned(),
                files,
            })
            .collect(),
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
            error: Some(format!("no git repository at or above {}", Shown::of(cwd))),
        };
    };
    let (branch, head, error) = match repo.head() {
        Ok(h) => (h.branch, h.oid.map(|o| o.to_string()), None),
        Err(e) => (None, None, Some(e.to_string())),
    };
    GitInfo {
        discovered: true,
        root: repo.work_dir().map(|p| Shown::of(p).to_string()),
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
        dir: Some(Shown::of(&dir).to_string()),
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
            protection: "skipped".to_owned(),
            protection_detail: None,
        },
        Err(e) => LedgerInfo {
            r#ref: name,
            reachable: false,
            oid: None,
            error: Some(e),
            protection: "skipped".to_owned(),
            protection_detail: None,
        },
    }
}

/// The ledger section with its branch-protection verdict, and the `TICK011` finding when there is one.
// frob:ticket 01M3ZX81C81M8ZQWTGQZK2SR2P
fn ledger_with_protection(
    located: &Located,
    cfg: &FrobConfig,
) -> (LedgerInfo, Option<gob_rules::Finding>) {
    let mut ledger = ledger_info(located, cfg);
    let remote = located
        .repo
        .as_ref()
        .and_then(|r| r.remote_url("origin"))
        .unwrap_or_default();
    let finding = protection_check(&mut ledger, cfg, &remote, &GithubProbe);
    (ledger, finding)
}

/// A [`ProtectionProbe`] over the native GitHub transport, with the token from the environment.
struct GithubProbe;

impl ProtectionProbe for GithubProbe {
    fn get(&self, path: &str) -> Result<Reply, String> {
        let token = TOKEN_VARS
            .iter()
            .find_map(|v| std::env::var(v).ok().filter(|t| !t.is_empty()))
            .ok_or_else(|| "no GH_TOKEN or GITHUB_TOKEN set".to_owned())?;
        let req = HttpRequest {
            method: Method::Get,
            path: path.to_owned(),
            query: vec![],
            body: None,
        };
        NativeTransport::new(token)
            .send(&req)
            .map(|r| Reply {
                status: r.status,
                body: r.body,
            })
            .map_err(|e| format!("hosting API unreachable: {e}"))
    }
}

/// Judge the ledger branch's protection into `info` and return the `TICK011` finding, if any.
///
/// Only the orphan ticket-branch layout has a ledger branch; any other layout is `skipped`.
/// An answer that force pushes or deletion are allowed is an Error finding; no token, no
/// GitHub remote or an unreachable API is Unresolved, never clean (security.md 2.11).
// frob:ticket 01M3ZX81C81M8ZQWTGQZK2SR2P
fn protection_check(
    info: &mut LedgerInfo,
    cfg: &FrobConfig,
    remote: &str,
    probe: &dyn ProtectionProbe,
) -> Option<gob_rules::Finding> {
    if cfg.tickets.ref_mode != crate::config::RefModeKnob::Orphan {
        tracing::debug!("ledger protection skipped: not the orphan ticket-branch layout");
        return None;
    }
    let branch = &cfg.tickets.branch;
    let verdict = match resolve_repo(None, &cfg.mirror.repo, remote) {
        Some((owner, repo)) => tick_protect::check_branch(probe, &owner, &repo, branch),
        None => Verdict::Unresolved(
            "no GitHub repository: set [mirror] repo or an origin remote".to_owned(),
        ),
    };
    let (state, detail) = match &verdict {
        Verdict::Protected => ("protected", None),
        Verdict::Unprotected(open) => ("unprotected", Some(open.join("; "))),
        Verdict::Unresolved(why) => ("unresolved", Some(why.clone())),
    };
    state.clone_into(&mut info.protection);
    info.protection_detail = detail;
    tick_protect::tick011(&verdict, branch)
}

/// The lease-file section: corrupt files, and with `fix` quarantine them (kept as `.toml.corrupt`, never deleted).
// frob:ticket 01M42MGP62EPY4K7C29M0388X5
fn lease_info(
    located: &Located,
    cfg: &FrobConfig,
    fix: bool,
    clock: &std::sync::Arc<dyn gob_time::Clock>,
) -> LeaseInfo {
    let skipped = |why: String| LeaseInfo {
        state: format!("skipped: {why}"),
        corrupt: Vec::new(),
        quarantined: None,
    };
    let Some(repo) = located.repo.as_ref().filter(|r| r.work_dir().is_some()) else {
        return skipped("not a git work tree".to_owned());
    };
    let store = match frob_lease::LeaseStore::open(repo, cfg.lease.clone(), clock.clone()) {
        Ok(s) => s,
        Err(e) => return skipped(format!("lease store: {e}")),
    };
    let corrupt = match store.corrupt_leases() {
        Ok(c) => c,
        Err(e) => return skipped(e.to_string()),
    };
    let quarantined = if fix && !corrupt.is_empty() {
        match store.quarantine_corrupt() {
            Ok(moved) => Some(moved.iter().map(|p| Shown::of(p).to_string()).collect()),
            Err(e) => {
                tracing::warn!(error = %e, "lease quarantine failed");
                None
            }
        }
    } else {
        None
    };
    tracing::info!(
        corrupt = corrupt.len(),
        fixed = quarantined.is_some(),
        "lease doctor section"
    );
    LeaseInfo {
        state: "ok".to_owned(),
        corrupt: if quarantined.is_some() {
            Vec::new()
        } else {
            corrupt
        },
        quarantined,
    }
}

/// The local-lands section from `frob_land::divergence`; report only, because the repair (`frob land --relaunch`) merges the remote base into a branch and `--fix` never rewrites history.
// frob:ticket 01M5E2MWBXD6DQSNE9AX511AFF
fn lands_info(
    located: &Located,
    cfg: &FrobConfig,
    clock: &std::sync::Arc<dyn gob_time::Clock>,
) -> LandsInfo {
    let skipped = |why: String| LandsInfo {
        state: format!("skipped: {why}"),
        lands: Vec::new(),
        evicted: 0,
    };
    let Some(repo) = located.repo.as_ref().filter(|r| r.work_dir().is_some()) else {
        return skipped("not a git work tree".to_owned());
    };
    let base = cfg
        .tickets
        .r#ref
        .strip_prefix("refs/heads/")
        .unwrap_or(&cfg.tickets.r#ref);
    let remote_base = format!("refs/remotes/{}/{base}", cfg.sync.remote);
    let ledger = frob_ledger::Ledger::open(repo.clone(), cfg.ledger(), clock.clone());
    match frob_land::divergence::diverged_lands(&ledger, &remote_base) {
        Ok(d) => {
            tracing::info!(
                lands = d.lands.len(),
                evicted = d.evicted,
                "lands doctor section"
            );
            LandsInfo {
                state: "ok".to_owned(),
                lands: d
                    .lands
                    .iter()
                    .map(|l| format!("{} at {}", l.handle, l.commit))
                    .collect(),
                evicted: d.evicted,
            }
        }
        Err(e) => {
            tracing::warn!(error = %e, "local land scan failed");
            skipped(e.to_string())
        }
    }
}

/// One warning per sibling product whose PATH copy differs from the one next to frob.
fn sibling_warnings(siblings: &[SiblingRow]) -> Vec<String> {
    siblings
        .iter()
        .filter_map(|row| {
            let other = row.other.as_ref().filter(|o| o.differs)?;
            Some(format!(
                "{} on PATH ({}) differs from the one next to frob ({}); frob uses the one next to it",
                row.product,
                other.version.as_deref().unwrap_or("version unknown"),
                row.version.as_deref().unwrap_or("version unknown"),
            ))
        })
        .collect()
}

/// The doctor warning for local lands origin lacks, with the relaunch remedy; `None` when there are none.
fn lands_warning(lands: &LandsInfo, remote: &str) -> Option<String> {
    (!lands.lands.is_empty()).then(|| {
        format!(
            "{} local lands not on {remote}: {}; remedy: `frob land --relaunch <ticket>` for each",
            lands.lands.len(),
            lands.lands.join(", ")
        )
    })
}

/// Group `report`'s actions by category.
fn by_category(report: &Report) -> Vec<GcCategory> {
    let mut map: BTreeMap<&str, (usize, u64)> = BTreeMap::new();
    for a in &report.actions {
        let e = map.entry(a.category.as_str()).or_default();
        e.0 += 1;
        e.1 += a.bytes;
    }
    map.into_iter()
        .map(|(category, (items, bytes))| GcCategory {
            category: category.to_owned(),
            items,
            bytes,
        })
        .collect()
}

/// An empty garbage-collection section carrying why nothing was measured.
fn gc_skipped(why: &str) -> GcInfo {
    GcInfo {
        state: format!("skipped: {why}"),
        last_run_unix: None,
        last_reclaimed_bytes: 0,
        total_reclaimed_bytes: 0,
        passes: 0,
        usage: Vec::new(),
        would_reclaim: Vec::new(),
        would_reclaim_bytes: 0,
        kept: Vec::new(),
        fixed: None,
    }
}

/// The garbage-collection section: stamp stats always; the costly dry-run plan only with `fix` or `plan_wanted`.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29
fn gc_info(
    located: &Located,
    cfg: &FrobConfig,
    fix: bool,
    plan_wanted: bool,
    clock: &std::sync::Arc<dyn gob_time::Clock>,
) -> GcInfo {
    let Some(repo) = located.repo.as_ref().filter(|r| r.work_dir().is_some()) else {
        return gc_skipped("not a git work tree");
    };
    let leases = match frob_lease::LeaseStore::open(repo, cfg.lease.clone(), clock.clone()) {
        Ok(l) => l,
        Err(e) => return gc_skipped(&format!("lease store: {e}")),
    };
    let ledger = match gob_git::Repo::discover(&located.root) {
        Ok(r) => frob_ledger::Ledger::open(r, cfg.ledger(), clock.clone()),
        Err(e) => return gc_skipped(&e.to_string()),
    };
    let run = |mode| gc::glue::run_for(&ledger, &leases, &cfg.worktree, &cfg.gc, mode);
    let fixed = fix.then(|| {
        let r = run(Mode::Forced);
        GcFixed {
            reclaimed_bytes: r.reclaimed_bytes,
            by_category: by_category(&r),
            warnings: r.warnings,
        }
    });
    // The dry-run plan walks every worktree and ticket event log; only pay for it when asked.
    let plan = if fix || plan_wanted {
        run(Mode::DryRun)
    } else {
        tracing::debug!("gc dry-run plan skipped; pass --gc-plan to include it");
        Report::default()
    };
    let stamp = gc::stamp::load(repo.common_dir());
    tracing::info!(
        passes = stamp.passes,
        would_reclaim = plan.reclaimed_bytes,
        fixed = fixed.is_some(),
        "gc doctor section"
    );
    GcInfo {
        state: "ok".to_owned(),
        last_run_unix: (stamp.last_run_unix != 0).then_some(stamp.last_run_unix),
        last_reclaimed_bytes: stamp.last_reclaimed_bytes,
        total_reclaimed_bytes: stamp.total_reclaimed_bytes,
        passes: stamp.passes,
        usage: plan.usage.clone(),
        would_reclaim: by_category(&plan),
        would_reclaim_bytes: plan.reclaimed_bytes,
        kept: plan.kept,
        fixed,
    }
}

#[cfg(test)]
mod protection_tests {
    use super::*;
    use gob_rules::Severity;

    struct Fixed(Result<Reply, String>);

    impl ProtectionProbe for Fixed {
        fn get(&self, _path: &str) -> Result<Reply, String> {
            self.0.clone()
        }
    }

    fn orphan() -> FrobConfig {
        let mut cfg = FrobConfig::default();
        cfg.tickets.ref_mode = crate::config::RefModeKnob::Orphan;
        cfg
    }

    fn info() -> LedgerInfo {
        LedgerInfo {
            r#ref: "r".to_owned(),
            reachable: true,
            oid: None,
            error: None,
            protection: "skipped".to_owned(),
            protection_detail: None,
        }
    }

    const REMOTE: &str = "https://github.com/o/r.git";

    // frob:tests crates/frob/src/doctor.rs::protection_check
    #[test]
    fn allowed_force_push_is_an_error() {
        let body = r#"{"allow_force_pushes":{"enabled":true},"allow_deletions":{"enabled":false}}"#;
        let probe = Fixed(Ok(Reply {
            status: 200,
            body: body.to_owned(),
        }));
        let mut i = info();
        let f = protection_check(&mut i, &orphan(), REMOTE, &probe).expect("finding");
        assert_eq!(f.severity, Severity::Error);
        assert_eq!(i.protection, "unprotected");
    }

    // frob:tests crates/frob/src/doctor.rs::protection_check
    #[test]
    fn unreachable_api_is_unresolved_not_clean() {
        let probe = Fixed(Err("no token".to_owned()));
        let mut i = info();
        let f = protection_check(&mut i, &orphan(), REMOTE, &probe).expect("finding");
        assert_eq!(f.severity, Severity::Unresolved);
        assert_eq!(i.protection, "unresolved");
    }

    // frob:tests crates/frob/src/doctor.rs::protection_check
    #[test]
    fn non_orphan_layout_is_skipped() {
        let probe = Fixed(Err("never asked".to_owned()));
        let mut i = info();
        assert!(protection_check(&mut i, &FrobConfig::default(), REMOTE, &probe).is_none());
        assert_eq!(i.protection, "skipped");
    }
}

#[cfg(test)]
mod lands_tests {
    use super::*;

    // frob:tests lands_info
    #[test]
    fn outside_a_work_tree_the_lands_section_is_skipped() {
        let dir = tempfile::tempdir().unwrap();
        let located = Located {
            repo: None,
            root: dir.path().to_path_buf(),
        };
        let clock: std::sync::Arc<dyn gob_time::Clock> = std::sync::Arc::new(gob_time::SystemClock);
        let info = lands_info(&located, &FrobConfig::default(), &clock);
        assert!(info.state.starts_with("skipped"));
        assert!(info.lands.is_empty());
    }
}
