//! `cargo dev publish`: publish the workspace crates to crates.io in dependency order.
//!
//! The run is resumable by construction: every crate whose exact version is
//! already on the index is skipped, so a re-run after a partial failure
//! continues at the first unpublished crate and never needs a version bump.
//! The registry and the cargo invocation are traits ([`Registry`],
//! [`CargoRunner`]) so tests drive the whole flow with fakes and nothing
//! reaches crates.io; [`CratesIo`] and [`CargoCli`] are the real
//! implementations, spawned through `gob-exec` (PROC001).
//! crates.io rate limits are handled, not fatal: a 429 carries the time to retry
//! (`Retry-After` or "try again after `<date>`"); [`run`] and [`reserve`] wait it out
//! within `max_wait` and otherwise stop with [`PublishError::RateLimitBudget`], which
//! names the next crate and the retry time and maps to [`RESUMABLE_EXIT`].
//! [`reserve`] publishes 0.0.0 placeholders for names missing from the index, paced
//! to the new-crate limit, so a first release only publishes new versions.
//! Design: `docs/design/releases.md` section 5 (publishing) and `monorepo.md` 4.
// frob:ticket 01M4069Y65FA7GGXG2F6N2KET1
// frob:ticket 01M42026M27TR9YV0C60JTYGH0

use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde::Deserialize;

/// Base URL of the crates.io sparse index.
pub const INDEX_URL: &str = "https://index.crates.io";

/// Wall-clock limit for one `cargo publish` (package, verify build, upload).
const PUBLISH_TIMEOUT: Duration = Duration::from_mins(30);
/// Wall-clock limit for one metadata or index read.
const READ_TIMEOUT: Duration = Duration::from_mins(2);
/// Process exit status of a run that stopped on the rate limit and can be re-run later (`EX_TEMPFAIL`).
pub const RESUMABLE_EXIT: u8 = 75;
/// Wait assumed when a 429 names no retry time.
const FALLBACK_WAIT: Duration = Duration::from_mins(5);
/// Slack added to a stated retry time so the retry lands after it.
const RETRY_SLACK: Duration = Duration::from_secs(5);

/// Why a publish run stopped.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum PublishError {
    /// `cargo metadata` output could not be read.
    #[error("workspace metadata: {0}")]
    Metadata(String),
    /// The publishable crates depend on each other in a cycle.
    #[error("dependency cycle among publishable crates: {0:?}")]
    Cycle(Vec<String>),
    /// The registry could not be queried.
    #[error("registry query for {krate} failed: {reason}")]
    Registry {
        /// Crate being queried.
        krate: String,
        /// What went wrong.
        reason: String,
    },
    /// `cargo publish` failed; re-running resumes at this crate.
    #[error("cargo publish of {krate} {version} failed: {reason}; re-run to resume here")]
    Cargo {
        /// Crate that failed.
        krate: String,
        /// Version that failed.
        version: String,
        /// What went wrong.
        reason: String,
    },
    /// The registry answered 429 to one attempt; [`run`] and [`reserve`] wait or give up.
    #[error("{krate} {version}: crates.io rate limit, retry after {retry_at}")]
    RateLimited {
        /// Crate being published.
        krate: String,
        /// Version being published.
        version: String,
        /// How long to wait from now.
        wait: Duration,
        /// Earliest retry time, UTC.
        retry_at: String,
    },
    /// The rate-limit wait budget is spent; re-running at `retry_at` resumes at this crate.
    #[error(
        "crates.io rate limit: next is {krate} {version}, retry after {retry_at}; waiting would exceed --max-wait; re-run then to resume here"
    )]
    RateLimitBudget {
        /// Next crate to publish.
        krate: String,
        /// Its version.
        version: String,
        /// Earliest retry time, UTC.
        retry_at: String,
    },
    /// The index never showed a freshly published version.
    #[error("{krate} {version} did not appear on the index after {attempts} checks")]
    IndexTimeout {
        /// Crate awaited.
        krate: String,
        /// Version awaited.
        version: String,
        /// Number of index checks made.
        attempts: u32,
    },
}

/// One publishable workspace crate and the publishable crates it needs first.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Crate {
    /// Package name.
    pub name: String,
    /// Package version.
    pub version: String,
    /// Names of publishable workspace crates this one needs first (dev-dependencies without a version excluded).
    pub deps: BTreeSet<String>,
    /// Repository URL from the manifest, for a placeholder's description.
    pub repository: Option<String>,
    /// SPDX license expression from the manifest, for a placeholder.
    pub license: Option<String>,
}

#[derive(Deserialize)]
struct Metadata {
    packages: Vec<Package>,
}

#[derive(Deserialize)]
struct Package {
    name: String,
    version: String,
    publish: Option<Vec<String>>,
    #[serde(default)]
    repository: Option<String>,
    #[serde(default)]
    license: Option<String>,
    dependencies: Vec<Dependency>,
}

#[derive(Deserialize)]
struct Dependency {
    name: String,
    path: Option<String>,
    /// `null` for a normal dependency, `"dev"` or `"build"` otherwise.
    #[serde(default)]
    kind: Option<String>,
    /// Version requirement; `*` when the manifest gives only a path.
    #[serde(default)]
    req: Option<String>,
}

impl Dependency {
    /// Whether the published crate needs this one on the index first.
    ///
    /// Cargo strips a path-only dev-dependency from the packaged manifest, so it
    /// imposes no order (and may close a cycle, as `gob-macros` tests do).
    fn orders_publish(&self) -> bool {
        let stripped =
            self.kind.as_deref() == Some("dev") && self.req.as_deref().is_none_or(|r| r == "*");
        self.path.is_some() && !stripped
    }
}

impl Package {
    /// `publish = false` shows up in metadata as an empty list; a list must name crates.io.
    fn publishable(&self) -> bool {
        self.publish
            .as_ref()
            .is_none_or(|regs| regs.iter().any(|r| r == "crates-io"))
    }
}

/// Order the publishable crates of `cargo metadata --no-deps` JSON, dependencies first.
///
/// Crates with `publish = false` are left out. Ties break by name so the
/// order is deterministic.
///
/// # Errors
/// [`PublishError::Metadata`] for unreadable JSON and [`PublishError::Cycle`]
/// when the crates depend on each other in a cycle.
pub fn plan(metadata_json: &str) -> Result<Vec<Crate>, PublishError> {
    let meta: Metadata =
        serde_json::from_str(metadata_json).map_err(|e| PublishError::Metadata(e.to_string()))?;
    let names: BTreeSet<&str> = meta
        .packages
        .iter()
        .filter(|p| p.publishable())
        .map(|p| p.name.as_str())
        .collect();
    let mut pending: BTreeMap<String, Crate> = meta
        .packages
        .iter()
        .filter(|p| p.publishable())
        .map(|p| {
            let deps = p
                .dependencies
                .iter()
                .filter(|d| {
                    d.orders_publish() && names.contains(d.name.as_str()) && d.name != p.name
                })
                .map(|d| d.name.clone())
                .collect();
            (
                p.name.clone(),
                Crate {
                    name: p.name.clone(),
                    version: p.version.clone(),
                    deps,
                    repository: p.repository.clone(),
                    license: p.license.clone(),
                },
            )
        })
        .collect();
    let mut ordered: Vec<Crate> = Vec::with_capacity(pending.len());
    let mut placed: BTreeSet<String> = BTreeSet::new();
    while !pending.is_empty() {
        let ready: Vec<String> = pending
            .values()
            .filter(|c| c.deps.is_subset(&placed))
            .map(|c| c.name.clone())
            .collect();
        if ready.is_empty() {
            let stuck: Vec<String> = pending.keys().cloned().collect();
            tracing::error!(?stuck, "publish dependency cycle");
            return Err(PublishError::Cycle(stuck));
        }
        for name in ready {
            if let Some(c) = pending.remove(&name) {
                placed.insert(name);
                ordered.push(c);
            }
        }
    }
    tracing::info!(crates = ordered.len(), "publish order planned");
    Ok(ordered)
}

/// Read access to the registry index.
pub trait Registry {
    /// Whether `name` at exactly `version` is on the index (yanked counts).
    ///
    /// # Errors
    /// [`PublishError::Registry`] when the index cannot be read.
    fn has_version(&self, name: &str, version: &str) -> Result<bool, PublishError>;

    /// Whether any version of `name` is on the index.
    ///
    /// # Errors
    /// [`PublishError::Registry`] when the index cannot be read.
    fn has_crate(&self, name: &str) -> Result<bool, PublishError>;
}

/// The cargo side of a publish.
pub trait CargoRunner {
    /// Run `cargo publish` for one crate.
    ///
    /// # Errors
    /// [`PublishError::RateLimited`] on a 429, [`PublishError::Cargo`] when cargo otherwise fails.
    fn publish(&self, krate: &Crate) -> Result<(), PublishError>;

    /// Publish a code-free 0.0.0 placeholder that reserves the name of `krate`.
    ///
    /// # Errors
    /// As [`CargoRunner::publish`].
    fn reserve(&self, krate: &Crate) -> Result<(), PublishError>;
}

/// Default budget for waiting out rate limits.
pub const DEFAULT_MAX_WAIT: Duration = Duration::from_mins(30);

/// Knobs of one publish run.
#[derive(Debug, Clone, Copy)]
pub struct Options {
    /// Print the order and publish nothing (no registry reads either).
    pub dry_run: bool,
    /// Index checks after each publish before giving up.
    pub index_attempts: u32,
    /// Pause between index checks.
    pub index_interval: Duration,
    /// Total time to spend waiting out 429 answers before stopping resumably.
    pub max_wait: Duration,
}

impl Default for Options {
    /// Real publish; wait up to ten minutes for each crate to reach the index.
    fn default() -> Self {
        Self {
            dry_run: false,
            index_attempts: 60,
            index_interval: Duration::from_secs(10),
            max_wait: DEFAULT_MAX_WAIT,
        }
    }
}

/// What a run did, by crate name, in order.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct Report {
    /// Crates published by this run.
    pub published: Vec<String>,
    /// Crates skipped because the version was already on the index.
    pub skipped: Vec<String>,
}

/// Publish `order` through `cargo`, skipping versions `registry` already holds.
///
/// After each publish the index is polled (via `sleep` between checks) so the
/// next dependent resolves its dependency. With `opts.dry_run` only the order
/// is printed through `say`.
///
/// # Errors
/// The first [`PublishError`] stops the run; completed crates stay published
/// and a re-run resumes after them.
pub fn run(
    order: &[Crate],
    registry: &dyn Registry,
    cargo: &dyn CargoRunner,
    opts: &Options,
    say: &mut dyn FnMut(&str),
    sleep: &dyn Fn(Duration),
) -> Result<Report, PublishError> {
    let mut report = Report::default();
    let mut waited = Duration::ZERO;
    if opts.dry_run {
        say(&format!(
            "dry run: {} crates in publish order, nothing published",
            order.len()
        ));
        for (i, c) in order.iter().enumerate() {
            say(&format!("{:>3}. {} {}", i + 1, c.name, c.version));
        }
        return Ok(report);
    }
    for c in order {
        if registry.has_version(&c.name, &c.version)? {
            tracing::info!(krate = %c.name, version = %c.version, "already on the index; skipped");
            say(&format!(
                "skip {} {} (already on the index)",
                c.name, c.version
            ));
            report.skipped.push(c.name.clone());
            continue;
        }
        say(&format!("publish {} {}", c.name, c.version));
        with_rate_limit(c, opts.max_wait, &mut waited, say, sleep, || {
            cargo.publish(c)
        })?;
        wait_for_index(registry, c, opts, sleep)?;
        tracing::info!(krate = %c.name, version = %c.version, "published");
        report.published.push(c.name.clone());
    }
    say(&format!(
        "done: {} published, {} already on the index",
        report.published.len(),
        report.skipped.len()
    ));
    Ok(report)
}

/// Run `attempt`, waiting out [`PublishError::RateLimited`] answers while `waited` stays within `max_wait`.
///
/// Past the budget the answer becomes [`PublishError::RateLimitBudget`] naming `c`.
fn with_rate_limit(
    c: &Crate,
    max_wait: Duration,
    waited: &mut Duration,
    say: &mut dyn FnMut(&str),
    sleep: &dyn Fn(Duration),
    mut attempt: impl FnMut() -> Result<(), PublishError>,
) -> Result<(), PublishError> {
    loop {
        match attempt() {
            Err(PublishError::RateLimited { wait, retry_at, .. }) => {
                if *waited + wait > max_wait {
                    tracing::warn!(krate = %c.name, %retry_at, ?waited, ?max_wait, "rate-limit wait budget spent");
                    return Err(PublishError::RateLimitBudget {
                        krate: c.name.clone(),
                        version: c.version.clone(),
                        retry_at,
                    });
                }
                tracing::info!(krate = %c.name, ?wait, %retry_at, "rate limited; waiting");
                say(&format!(
                    "rate limited on {}; waiting {}s (until {retry_at})",
                    c.name,
                    wait.as_secs()
                ));
                sleep(wait);
                *waited += wait;
            }
            other => return other,
        }
    }
}

/// Knobs of a [`reserve`] run.
#[derive(Debug, Clone, Copy)]
pub struct ReserveOptions {
    /// Publish for real; without it the missing names and the plan are listed.
    pub apply: bool,
    /// New names crates.io accepts in a burst before pacing starts.
    pub burst: u32,
    /// Pause between new names once the burst is used.
    pub interval: Duration,
    /// Total time to spend waiting out 429 answers before stopping resumably.
    pub max_wait: Duration,
}

impl Default for ReserveOptions {
    /// Dry run; a burst of five, then one new name per ten minutes.
    fn default() -> Self {
        Self {
            apply: false,
            burst: 5,
            interval: Duration::from_mins(10),
            max_wait: DEFAULT_MAX_WAIT,
        }
    }
}

/// What a [`reserve`] run did, by crate name.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct ReserveReport {
    /// Names reserved by this run.
    pub reserved: Vec<String>,
    /// Names already on the index.
    pub present: Vec<String>,
    /// Names a dry run would reserve.
    pub missing: Vec<String>,
}

/// Reserve every name of `order` that is not on the index with a 0.0.0 placeholder.
///
/// Without `opts.apply` only the missing names and the pacing plan go to `say`.
/// Applied, the first `opts.burst` names go out at once and later ones are
/// spaced by `opts.interval`; a 429 is waited out as in [`run`]. Re-running
/// skips names already reserved.
///
/// # Errors
/// The first [`PublishError`] stops the run; reserved names stay reserved.
pub fn reserve(
    order: &[Crate],
    registry: &dyn Registry,
    cargo: &dyn CargoRunner,
    opts: &ReserveOptions,
    say: &mut dyn FnMut(&str),
    sleep: &dyn Fn(Duration),
) -> Result<ReserveReport, PublishError> {
    let mut report = ReserveReport::default();
    let mut missing: Vec<&Crate> = Vec::new();
    for c in order {
        if registry.has_crate(&c.name)? {
            report.present.push(c.name.clone());
        } else {
            missing.push(c);
        }
    }
    say(&format!(
        "{} names missing from crates.io, {} present",
        missing.len(),
        report.present.len()
    ));
    if !opts.apply {
        for (i, c) in missing.iter().enumerate() {
            say(&format!("{:>3}. {}", i + 1, c.name));
            report.missing.push(c.name.clone());
        }
        let paced = missing.len().saturating_sub(opts.burst as usize);
        say(&format!(
            "plan: the first {} at once, then one every {}s ({} paced, about {} min in all)",
            opts.burst,
            opts.interval.as_secs(),
            paced,
            opts.interval.as_secs() * paced as u64 / 60
        ));
        say("dry run: nothing published; pass --apply to publish the placeholders");
        return Ok(report);
    }
    let mut waited = Duration::ZERO;
    for (n, c) in missing.iter().enumerate() {
        if n >= opts.burst as usize {
            say(&format!("pacing: waiting {}s", opts.interval.as_secs()));
            sleep(opts.interval);
        }
        say(&format!("reserve {}", c.name));
        with_rate_limit(c, opts.max_wait, &mut waited, say, sleep, || {
            cargo.reserve(c)
        })?;
        tracing::info!(krate = %c.name, "name reserved");
        report.reserved.push(c.name.clone());
    }
    say(&format!(
        "done: {} reserved, {} already present",
        report.reserved.len(),
        report.present.len()
    ));
    Ok(report)
}

/// How long to wait before retrying, when `text` (cargo or HTTP output) reports a 429.
///
/// Reads a `Retry-After` header (seconds or an HTTP date) first, then the
/// "try again after `<date>`" message crates.io sends; a 429 naming no time waits
/// five minutes. `None` when `text` is not a rate limit.
pub fn rate_limit_wait(text: &str, now: jiff::Timestamp) -> Option<Duration> {
    let lower = text.to_ascii_lowercase();
    let limited = lower.contains("429")
        || lower.contains("too many requests")
        || lower.contains("try again after");
    if !limited {
        return None;
    }
    let until = |date: &str| -> Option<Duration> {
        let at = jiff::fmt::rfc2822::parse(date.trim()).ok()?.timestamp();
        let secs = at.as_second() - now.as_second();
        Some(Duration::from_secs(u64::try_from(secs).unwrap_or(0)))
    };
    let header = lower.find("retry-after:").map(|i| {
        let rest = text[i + "retry-after:".len()..]
            .lines()
            .next()
            .unwrap_or("");
        rest.trim().to_owned()
    });
    let hinted = header
        .and_then(|v| {
            v.parse::<u64>()
                .map(Duration::from_secs)
                .ok()
                .or_else(|| until(&v))
        })
        .or_else(|| {
            let i = lower.find("try again after ")? + "try again after ".len();
            let rest = text[i..].lines().next().unwrap_or("");
            let date = rest.split(" or ").next().unwrap_or(rest);
            until(date.trim_end_matches('.'))
        });
    Some(hinted.unwrap_or(FALLBACK_WAIT) + RETRY_SLACK)
}

/// Poll the index until `c` appears or the attempts run out.
fn wait_for_index(
    registry: &dyn Registry,
    c: &Crate,
    opts: &Options,
    sleep: &dyn Fn(Duration),
) -> Result<(), PublishError> {
    for attempt in 1..=opts.index_attempts {
        if registry.has_version(&c.name, &c.version)? {
            return Ok(());
        }
        tracing::debug!(krate = %c.name, attempt, "not on the index yet");
        sleep(opts.index_interval);
    }
    Err(PublishError::IndexTimeout {
        krate: c.name.clone(),
        version: c.version.clone(),
        attempts: opts.index_attempts,
    })
}

/// Sparse-index path of a crate: `1/a`, `2/ab`, `3/a/abc`, `ab/cd/abcd...`.
pub fn index_path(name: &str) -> String {
    let n = name.to_ascii_lowercase();
    match n.len() {
        0 | 1 => format!("1/{n}"),
        2 => format!("2/{n}"),
        3 => format!("3/{}/{n}", &n[..1]),
        _ => format!("{}/{}/{n}", &n[..2], &n[2..4]),
    }
}

/// Whether sparse-index `body` (one JSON object per line) lists `version`.
///
/// # Errors
/// [`PublishError::Registry`] when a line is not JSON.
pub fn index_lists(name: &str, body: &str, version: &str) -> Result<bool, PublishError> {
    #[derive(Deserialize)]
    struct Line {
        vers: String,
    }
    for line in body.lines().filter(|l| !l.trim().is_empty()) {
        let parsed: Line = serde_json::from_str(line).map_err(|e| PublishError::Registry {
            krate: name.to_owned(),
            reason: format!("unreadable index line: {e}"),
        })?;
        if parsed.vers == version {
            return Ok(true);
        }
    }
    Ok(false)
}

fn runner() -> Runner {
    Runner::new(Limits { jobs: 1 })
}

/// The crates.io sparse index, read with `curl` (no HTTP client in the tree).
#[derive(Debug, Default)]
pub struct CratesIo;

impl CratesIo {
    /// Fetch the index page of `name`: `Some(body)` on 200, `None` when the crate is absent.
    fn fetch(name: &str) -> Result<Option<String>, PublishError> {
        let fail = |reason: String| PublishError::Registry {
            krate: name.to_owned(),
            reason,
        };
        let spec = Spec {
            program: Program::Tool {
                name: "curl".to_owned(),
            },
            args: [
                "--proto",
                "=https",
                "--tlsv1.2",
                "-sS",
                "--max-time",
                "60",
                "-w",
                "\n%{http_code}",
                &format!("{INDEX_URL}/{}", index_path(name)),
            ]
            .map(str::to_owned)
            .to_vec(),
            cwd: None,
            env: Vec::new(),
            timeout: READ_TIMEOUT,
            capture: true,
        };
        let out = runner().run(&spec).map_err(|e| fail(e.to_string()))?;
        if out.status != Outcome::Exited(0) {
            return Err(fail(format!(
                "curl ended {:?}: {}",
                out.status,
                out.stderr.trim()
            )));
        }
        let (body, code) = out.stdout.rsplit_once('\n').unwrap_or(("", &out.stdout));
        match code.trim() {
            "200" => Ok(Some(body.to_owned())),
            "404" | "410" => Ok(None),
            other => Err(fail(format!("index answered HTTP {other}"))),
        }
    }
}

impl Registry for CratesIo {
    fn has_version(&self, name: &str, version: &str) -> Result<bool, PublishError> {
        match Self::fetch(name)? {
            Some(body) => index_lists(name, &body, version),
            None => Ok(false),
        }
    }

    fn has_crate(&self, name: &str) -> Result<bool, PublishError> {
        Self::fetch(name).map(|body| body.is_some())
    }
}

/// Runs `cargo publish -p <crate> --locked` in the workspace root.
#[derive(Debug)]
pub struct CargoCli {
    /// Workspace root to publish from.
    pub root: PathBuf,
    /// The run's clock, read for a rate-limit retry time.
    pub clock: std::sync::Arc<dyn gob_time::Clock>,
}

impl CargoCli {
    /// Run `cargo publish` with `args`, echo its output and classify the result.
    fn publish_with(&self, krate: &Crate, args: &[&str]) -> Result<(), PublishError> {
        let spec = Spec {
            program: Program::Cargo,
            args: args.iter().map(|a| (*a).to_owned()).collect(),
            cwd: Some(self.root.clone()),
            env: Vec::new(),
            timeout: PUBLISH_TIMEOUT,
            capture: true,
        };
        let out = runner().run(&spec).map_err(|e| PublishError::Cargo {
            krate: krate.name.clone(),
            version: krate.version.clone(),
            reason: e.to_string(),
        })?;
        for line in out.stdout.lines().chain(out.stderr.lines()) {
            crate::out::emit(line);
        }
        publish_outcome(
            out.status,
            &out.stderr,
            krate,
            jiff::Timestamp::from_second(self.clock.now().unix()).unwrap_or_default(),
        )
    }
}

/// Classify a finished `cargo publish`: success, a rate limit to wait out, or a failure.
///
/// # Errors
/// [`PublishError::RateLimited`] when `stderr` reports a 429, else [`PublishError::Cargo`].
pub fn publish_outcome(
    status: Outcome,
    stderr: &str,
    krate: &Crate,
    now: jiff::Timestamp,
) -> Result<(), PublishError> {
    match status {
        Outcome::Exited(0) => Ok(()),
        other => match rate_limit_wait(stderr, now) {
            Some(wait) => Err(PublishError::RateLimited {
                krate: krate.name.clone(),
                version: krate.version.clone(),
                wait,
                retry_at: now
                    .checked_add(jiff::SignedDuration::try_from(wait).unwrap_or_default())
                    .map_or_else(|_| "unknown".to_owned(), |t| t.to_string()),
            }),
            None => Err(PublishError::Cargo {
                krate: krate.name.clone(),
                version: krate.version.clone(),
                reason: format!("cargo ended {other:?}"),
            }),
        },
    }
}

/// Manifest of the code-free 0.0.0 placeholder that reserves `krate`'s name.
pub fn placeholder_manifest(krate: &Crate) -> String {
    let repo = krate.repository.as_deref().unwrap_or("https://crates.io");
    let description = format!("Name reservation for {}; see {repo}", krate.name);
    let mut m = format!(
        "[package]\nname = {:?}\nversion = \"0.0.0\"\nedition = \"2021\"\ndescription = {description:?}\n",
        krate.name
    );
    if let Some(license) = &krate.license {
        m.push_str(&format!("license = {license:?}\n"));
    }
    if let Some(repository) = &krate.repository {
        m.push_str(&format!("repository = {repository:?}\n"));
    }
    m.push_str("\n# Keep cargo from adopting the workspace this directory sits in.\n[workspace]\n");
    m
}

impl CargoRunner for CargoCli {
    fn publish(&self, krate: &Crate) -> Result<(), PublishError> {
        self.publish_with(krate, &["publish", "-p", &krate.name, "--locked"])
    }

    fn reserve(&self, krate: &Crate) -> Result<(), PublishError> {
        let dir = self.root.join("target").join("reserve").join(&krate.name);
        let fail = |e: std::io::Error| PublishError::Cargo {
            krate: krate.name.clone(),
            version: "0.0.0".to_owned(),
            reason: format!("placeholder in {}: {e}", dir.display()),
        };
        std::fs::create_dir_all(dir.join("src")).map_err(fail)?;
        std::fs::write(dir.join("Cargo.toml"), placeholder_manifest(krate)).map_err(fail)?;
        std::fs::write(dir.join("src").join("lib.rs"), "").map_err(fail)?;
        let manifest = dir.join("Cargo.toml");
        let placeholder = Crate {
            version: "0.0.0".to_owned(),
            ..krate.clone()
        };
        self.publish_with(
            &placeholder,
            &[
                "publish",
                "--manifest-path",
                &manifest.to_string_lossy(),
                "--allow-dirty",
            ],
        )
    }
}

/// `cargo metadata --no-deps` JSON of the workspace at `root`.
///
/// # Errors
/// [`PublishError::Metadata`] when cargo cannot be run or fails.
pub fn read_metadata(root: &std::path::Path) -> Result<String, PublishError> {
    let spec = Spec {
        program: Program::Cargo,
        args: ["metadata", "--no-deps", "--format-version", "1"]
            .map(str::to_owned)
            .to_vec(),
        cwd: Some(root.to_path_buf()),
        env: Vec::new(),
        timeout: READ_TIMEOUT,
        capture: true,
    };
    let out = runner()
        .run(&spec)
        .map_err(|e| PublishError::Metadata(e.to_string()))?;
    if out.status == Outcome::Exited(0) {
        Ok(out.stdout)
    } else {
        Err(PublishError::Metadata(format!(
            "cargo metadata ended {:?}: {}",
            out.status,
            out.stderr.trim()
        )))
    }
}

#[cfg(test)]
mod tests {
    use std::cell::RefCell;
    use std::collections::BTreeSet;

    use super::*;

    /// Metadata JSON for packages `(name, publish_false, [path deps])`, all at 1.2.3.
    fn metadata(pkgs: &[(&str, bool, &[&str])]) -> String {
        let items: Vec<String> = pkgs
            .iter()
            .map(|(name, nopub, deps)| {
                let mut deps: Vec<String> = deps
                    .iter()
                    .map(|d| format!(r#"{{"name":"{d}","path":"/x/{d}","kind":null}}"#))
                    .collect();
                deps.push(r#"{"name":"serde","path":null}"#.to_owned());
                let publish = if *nopub { "[]" } else { "null" };
                format!(
                    r#"{{"name":"{name}","version":"1.2.3","publish":{publish},"dependencies":[{}]}}"#,
                    deps.join(",")
                )
            })
            .collect();
        format!(r#"{{"packages":[{}]}}"#, items.join(","))
    }

    #[derive(Default)]
    struct Fake {
        on_index: RefCell<BTreeSet<String>>,
        published: RefCell<Vec<String>>,
        fail_on: Option<&'static str>,
        /// Index checks that answer "absent" after a publish before it shows up.
        lag: RefCell<u32>,
        lag_len: u32,
        /// Crates whose next publish or reserve answers 429, with the wait it names.
        limits: RefCell<Vec<(&'static str, Duration)>>,
        reserved: RefCell<Vec<String>>,
    }

    impl Fake {
        fn limit(&self, krate: &Crate) -> Result<(), PublishError> {
            let mut limits = self.limits.borrow_mut();
            if let Some(i) = limits.iter().position(|(n, _)| *n == krate.name) {
                let (_, wait) = limits.remove(i);
                return Err(PublishError::RateLimited {
                    krate: krate.name.clone(),
                    version: krate.version.clone(),
                    wait,
                    retry_at: "2026-10-04T04:00:00Z".to_owned(),
                });
            }
            Ok(())
        }
    }

    impl Registry for Fake {
        fn has_version(&self, name: &str, version: &str) -> Result<bool, PublishError> {
            let key = format!("{name}@{version}");
            if self.published.borrow().iter().any(|p| p == name) && *self.lag.borrow() > 0 {
                *self.lag.borrow_mut() -= 1;
                return Ok(false);
            }
            Ok(self.on_index.borrow().contains(&key))
        }

        fn has_crate(&self, name: &str) -> Result<bool, PublishError> {
            let prefix = format!("{name}@");
            Ok(self.reserved.borrow().iter().any(|r| r == name)
                || self
                    .on_index
                    .borrow()
                    .iter()
                    .any(|k| k.starts_with(&prefix)))
        }
    }

    impl CargoRunner for Fake {
        fn reserve(&self, krate: &Crate) -> Result<(), PublishError> {
            self.limit(krate)?;
            self.reserved.borrow_mut().push(krate.name.clone());
            Ok(())
        }

        fn publish(&self, krate: &Crate) -> Result<(), PublishError> {
            self.limit(krate)?;
            if self.fail_on == Some(krate.name.as_str()) {
                return Err(PublishError::Cargo {
                    krate: krate.name.clone(),
                    version: krate.version.clone(),
                    reason: "boom".to_owned(),
                });
            }
            self.published.borrow_mut().push(krate.name.clone());
            *self.lag.borrow_mut() = self.lag_len;
            self.on_index
                .borrow_mut()
                .insert(format!("{}@{}", krate.name, krate.version));
            Ok(())
        }
    }

    fn names(order: &[Crate]) -> Vec<&str> {
        order.iter().map(|c| c.name.as_str()).collect()
    }

    fn five() -> Vec<Crate> {
        // Declared out of order on purpose; e depends on d depends on c ... a is the leaf.
        plan(&metadata(&[
            ("e", false, &["d"]),
            ("d", false, &["c"]),
            ("c", false, &["a", "b"]),
            ("b", false, &["a"]),
            ("a", false, &[]),
        ]))
        .expect("plans")
    }

    fn go(
        order: &[Crate],
        fake: &Fake,
        opts: &Options,
    ) -> (Result<Report, PublishError>, Vec<String>) {
        let mut lines = Vec::new();
        let r = run(
            order,
            fake,
            fake,
            opts,
            &mut |l| lines.push(l.to_owned()),
            &|_| {},
        );
        (r, lines)
    }

    #[test]
    fn orders_dependencies_first_and_leaves_out_publish_false() {
        let order = plan(&metadata(&[
            ("zed", false, &["mid"]),
            ("mid", false, &["leaf", "private"]),
            ("leaf", false, &[]),
            ("private", true, &[]),
        ]))
        .unwrap();
        assert_eq!(names(&order), ["leaf", "mid", "zed"]);
        assert!(order[1].deps.contains("leaf") && !order[1].deps.contains("private"));
    }

    // frob:ticket 01M4172YE3SZDG17J1CAZS0RRT
    #[test]
    fn path_only_dev_dependencies_do_not_order_or_cycle_but_versioned_ones_do() {
        let json = r#"{"packages":[
            {"name":"a","version":"1","publish":null,"dependencies":[{"name":"b","path":"/x/b","kind":"dev","req":"*"}]},
            {"name":"b","version":"1","publish":null,"dependencies":[{"name":"a","path":"/x/a","kind":null,"req":"^1"}]}]}"#;
        assert_eq!(names(&plan(json).unwrap()), ["a", "b"]);
        let versioned = json.replace(r#""kind":"dev","req":"*""#, r#""kind":"dev","req":"^1""#);
        assert!(matches!(plan(&versioned), Err(PublishError::Cycle(_))));
    }

    #[test]
    fn cycles_are_an_error_naming_the_stuck_crates() {
        let err = plan(&metadata(&[("a", false, &["b"]), ("b", false, &["a"])])).unwrap_err();
        assert_eq!(err, PublishError::Cycle(vec!["a".into(), "b".into()]));
    }

    #[test]
    fn this_workspace_reads_and_plans_without_a_cycle() {
        let root = crate::workspace_root().unwrap();
        let json = read_metadata(&root).unwrap();
        let order = plan(&json).unwrap();
        let seen: BTreeSet<&str> = order.iter().map(|c| c.name.as_str()).collect();
        for (i, c) in order.iter().enumerate() {
            let before: BTreeSet<&str> = order[..i].iter().map(|c| c.name.as_str()).collect();
            assert!(
                c.deps.iter().all(|d| before.contains(d.as_str())),
                "{}",
                c.name
            );
            assert!(seen.contains(c.name.as_str()));
        }
    }

    #[test]
    fn unreadable_metadata_is_an_error() {
        assert!(matches!(plan("nope"), Err(PublishError::Metadata(_))));
    }

    // frob:tests publish_starts_at_the_first_unpublished_crate
    #[test]
    fn publish_starts_at_the_first_unpublished_crate() {
        let order = five();
        assert_eq!(names(&order), ["a", "b", "c", "d", "e"]);
        let fake = Fake::default();
        for c in &order[..3] {
            fake.on_index
                .borrow_mut()
                .insert(format!("{}@{}", c.name, c.version));
        }
        let (r, lines) = go(&order, &fake, &Options::default());
        let report = r.unwrap();
        assert_eq!(*fake.published.borrow(), ["d", "e"]);
        assert_eq!(report.skipped, ["a", "b", "c"]);
        assert_eq!(report.published, ["d", "e"]);
        assert!(lines[0].starts_with("skip a "));
        assert!(lines[3].starts_with("publish d "));
    }

    #[test]
    fn a_different_version_on_the_index_does_not_count() {
        let order = five();
        let fake = Fake::default();
        fake.on_index.borrow_mut().insert("a@1.2.2".to_owned());
        let (r, _) = go(&order, &fake, &Options::default());
        r.unwrap();
        assert_eq!(fake.published.borrow().len(), 5);
    }

    #[test]
    fn a_failure_stops_the_run_and_a_rerun_resumes_at_the_failed_crate() {
        let order = five();
        let mut fake = Fake {
            fail_on: Some("c"),
            ..Fake::default()
        };
        let (r, _) = go(&order, &fake, &Options::default());
        assert!(matches!(r, Err(PublishError::Cargo { ref krate, .. }) if krate == "c"));
        assert_eq!(*fake.published.borrow(), ["a", "b"]);
        fake.fail_on = None;
        fake.published.borrow_mut().clear();
        let (r, _) = go(&order, &fake, &Options::default());
        let report = r.unwrap();
        assert_eq!(*fake.published.borrow(), ["c", "d", "e"]);
        assert_eq!(report.skipped, ["a", "b"]);
    }

    #[test]
    fn waits_for_the_index_between_dependents_and_times_out_if_it_never_shows() {
        let order = five();
        let fake = Fake {
            lag_len: 3,
            ..Fake::default()
        };
        let slept = RefCell::new(0u32);
        let mut sink = |_: &str| {};
        run(
            &order,
            &fake,
            &fake,
            &Options::default(),
            &mut sink,
            &|_| {
                *slept.borrow_mut() += 1;
            },
        )
        .unwrap();
        assert_eq!(
            *slept.borrow(),
            15,
            "three waits after each of five publishes"
        );

        let slow = Fake {
            lag_len: 100,
            ..Fake::default()
        };
        let opts = Options {
            index_attempts: 4,
            ..Options::default()
        };
        let (r, _) = go(&order, &slow, &opts);
        assert!(matches!(
            r,
            Err(PublishError::IndexTimeout { attempts: 4, .. })
        ));
        assert_eq!(
            *slow.published.borrow(),
            ["a"],
            "stops before the dependent"
        );
    }

    // frob:tests dry_run_prints_the_order_and_publishes_nothing
    #[test]
    fn dry_run_prints_the_order_and_publishes_nothing() {
        let order = five();
        let fake = Fake::default();
        let opts = Options {
            dry_run: true,
            ..Options::default()
        };
        let (r, lines) = go(&order, &fake, &opts);
        assert_eq!(r.unwrap(), Report::default());
        assert!(fake.published.borrow().is_empty());
        let listed: Vec<&str> = lines[1..]
            .iter()
            .map(|l| l.split_whitespace().nth(1).unwrap())
            .collect();
        assert_eq!(listed, ["a", "b", "c", "d", "e"]);
    }

    #[test]
    fn index_paths_follow_the_sparse_layout() {
        assert_eq!(index_path("a"), "1/a");
        assert_eq!(index_path("ab"), "2/ab");
        assert_eq!(index_path("abc"), "3/a/abc");
        assert_eq!(index_path("Frob-Cli"), "fr/ob/frob-cli");
    }

    #[test]
    fn index_lists_matches_the_exact_version_including_yanked() {
        let body = "{\"vers\":\"0.1.0\",\"yanked\":true}\n{\"vers\":\"0.2.0\",\"yanked\":false}\n";
        assert!(index_lists("x", body, "0.1.0").unwrap());
        assert!(!index_lists("x", body, "0.3.0").unwrap());
        assert!(index_lists("x", "garbage", "0.1.0").is_err());
    }

    /// Run with a recording sleep; returns the result, the say lines and the sleeps.
    #[allow(clippy::type_complexity)]
    fn go_sleeps(
        order: &[Crate],
        fake: &Fake,
        opts: &Options,
    ) -> (Result<Report, PublishError>, Vec<String>, Vec<Duration>) {
        let mut lines = Vec::new();
        let sleeps = RefCell::new(Vec::new());
        let r = run(
            order,
            fake,
            fake,
            opts,
            &mut |l| lines.push(l.to_owned()),
            &|d| sleeps.borrow_mut().push(d),
        );
        (r, lines, sleeps.into_inner())
    }

    fn ts(s: &str) -> jiff::Timestamp {
        s.parse().unwrap()
    }

    // frob:tests rate_limit_within_the_budget_waits_and_continues
    #[test]
    fn rate_limit_within_the_budget_waits_and_continues() {
        let order = five();
        let fake = Fake {
            limits: RefCell::new(vec![("c", Duration::from_mins(10))]),
            ..Fake::default()
        };
        let opts = Options {
            index_attempts: 1,
            ..Options::default()
        };
        let (r, lines, sleeps) = go_sleeps(&order, &fake, &opts);
        assert_eq!(r.unwrap().published, ["a", "b", "c", "d", "e"]);
        assert_eq!(sleeps, [Duration::from_mins(10)]);
        assert!(lines.iter().any(|l| l.starts_with("rate limited on c")));
    }

    // frob:tests rate_limit_past_the_budget_stops_resumably_naming_the_next_crate
    #[test]
    fn rate_limit_past_the_budget_stops_resumably_naming_the_next_crate() {
        let order = five();
        let fake = Fake {
            limits: RefCell::new(vec![("c", Duration::from_mins(45))]),
            ..Fake::default()
        };
        let (r, _, sleeps) = go_sleeps(&order, &fake, &Options::default());
        let Err(PublishError::RateLimitBudget {
            krate, retry_at, ..
        }) = r
        else {
            panic!("expected the budget error");
        };
        assert_eq!(
            (krate.as_str(), retry_at.as_str()),
            ("c", "2026-10-04T04:00:00Z")
        );
        assert!(sleeps.is_empty());
        assert_eq!(*fake.published.borrow(), ["a", "b"]);
        // The re-run after the retry time resumes at c.
        let (r, _, _) = go_sleeps(&order, &fake, &Options::default());
        assert_eq!(r.unwrap().published, ["c", "d", "e"]);
    }

    #[test]
    fn the_budget_is_shared_across_crates() {
        let order = five();
        let fake = Fake {
            limits: RefCell::new(vec![
                ("a", Duration::from_mins(20)),
                ("b", Duration::from_mins(20)),
            ]),
            ..Fake::default()
        };
        let (r, _, sleeps) = go_sleeps(&order, &fake, &Options::default());
        assert!(matches!(r, Err(PublishError::RateLimitBudget { ref krate, .. }) if krate == "b"));
        assert_eq!(sleeps, [Duration::from_mins(20)]);
    }

    #[test]
    fn retry_time_comes_from_the_message_or_the_header() {
        let now = ts("2026-10-04T03:00:00Z");
        let msg = "error: failed to publish\n\nCaused by:\n  the remote server responded with an error (status 429 Too Many Requests): You have published too many new crates in a short period of time. Please try again after Sun, 04 Oct 2026 03:10:00 GMT or email help@crates.io to have your limit increased.";
        assert_eq!(rate_limit_wait(msg, now), Some(Duration::from_secs(605)));
        assert_eq!(
            rate_limit_wait("HTTP/2 429\nRetry-After: 90\n", now),
            Some(Duration::from_secs(95))
        );
        assert_eq!(
            rate_limit_wait("429\nretry-after: Sun, 04 Oct 2026 03:01:00 GMT", now),
            Some(Duration::from_secs(65))
        );
        assert_eq!(
            rate_limit_wait("status 429", now),
            Some(FALLBACK_WAIT + RETRY_SLACK)
        );
        assert_eq!(
            rate_limit_wait("try again after Sun, 04 Oct 2026 02:00:00 GMT", now),
            Some(RETRY_SLACK),
            "a past time waits only the slack"
        );
        assert_eq!(rate_limit_wait("error: compile failed", now), None);
    }

    #[test]
    fn cargo_output_is_classified_into_success_rate_limit_or_failure() {
        let c = &five()[0];
        let now = ts("2026-10-04T03:00:00Z");
        assert!(publish_outcome(Outcome::Exited(0), "", c, now).is_ok());
        let limited = publish_outcome(Outcome::Exited(101), "status 429. Retry-After: 60", c, now);
        assert!(matches!(
            limited,
            Err(PublishError::RateLimited { wait, ref retry_at, .. })
                if wait == Duration::from_secs(65) && retry_at == "2026-10-04T03:01:05Z"
        ));
        assert!(matches!(
            publish_outcome(Outcome::Exited(101), "error: boom", c, now),
            Err(PublishError::Cargo { .. })
        ));
    }

    fn reserve_go(
        order: &[Crate],
        fake: &Fake,
        opts: &ReserveOptions,
    ) -> (
        Result<ReserveReport, PublishError>,
        Vec<String>,
        Vec<Duration>,
    ) {
        let mut lines = Vec::new();
        let sleeps = RefCell::new(Vec::new());
        let r = reserve(
            order,
            fake,
            fake,
            opts,
            &mut |l| lines.push(l.to_owned()),
            &|d| sleeps.borrow_mut().push(d),
        );
        (r, lines, sleeps.into_inner())
    }

    // frob:tests reserve_without_apply_lists_missing_names_and_the_plan_and_publishes_nothing
    #[test]
    fn reserve_without_apply_lists_missing_names_and_the_plan_and_publishes_nothing() {
        let order = five();
        let fake = Fake::default();
        fake.reserved.borrow_mut().push("a".to_owned());
        let opts = ReserveOptions {
            burst: 2,
            ..ReserveOptions::default()
        };
        let (r, lines, sleeps) = reserve_go(&order, &fake, &opts);
        let report = r.unwrap();
        assert_eq!(report.missing, ["b", "c", "d", "e"]);
        assert_eq!(report.present, ["a"]);
        assert!(report.reserved.is_empty());
        assert_eq!(*fake.reserved.borrow(), ["a"], "nothing new reserved");
        assert!(fake.published.borrow().is_empty() && sleeps.is_empty());
        let text = lines.join("\n");
        assert!(text.contains("4 names missing"), "{text}");
        assert!(
            text.contains("plan: the first 2 at once, then one every 600s (2 paced"),
            "{text}"
        );
        assert!(text.contains("pass --apply"), "{text}");
    }

    #[test]
    fn reserve_apply_paces_after_the_burst_and_resumes_past_reserved_names() {
        let order = five();
        let fake = Fake::default();
        fake.reserved.borrow_mut().push("a".to_owned());
        let opts = ReserveOptions {
            apply: true,
            burst: 2,
            ..ReserveOptions::default()
        };
        let (r, _, sleeps) = reserve_go(&order, &fake, &opts);
        assert_eq!(r.unwrap().reserved, ["b", "c", "d", "e"]);
        assert_eq!(sleeps, [opts.interval, opts.interval]);
        let (r, _, sleeps) = reserve_go(&order, &fake, &opts);
        assert!(r.unwrap().reserved.is_empty());
        assert!(sleeps.is_empty());
    }

    #[test]
    fn reserve_waits_out_a_rate_limit_and_stops_resumably_past_the_budget() {
        let order = five();
        let fake = Fake {
            limits: RefCell::new(vec![("b", Duration::from_mins(3))]),
            ..Fake::default()
        };
        let opts = ReserveOptions {
            apply: true,
            ..ReserveOptions::default()
        };
        let (r, _, sleeps) = reserve_go(&order, &fake, &opts);
        assert_eq!(r.unwrap().reserved.len(), 5);
        assert_eq!(sleeps, [Duration::from_mins(3)]);

        let slow = Fake {
            limits: RefCell::new(vec![("c", Duration::from_mins(90))]),
            ..Fake::default()
        };
        let (r, _, _) = reserve_go(&order, &slow, &opts);
        assert!(matches!(r, Err(PublishError::RateLimitBudget { ref krate, .. }) if krate == "c"));
        assert_eq!(*slow.reserved.borrow(), ["a", "b"]);
    }

    #[test]
    fn the_placeholder_manifest_has_no_code_and_points_at_the_repository() {
        let c = Crate {
            repository: Some("https://example.org/r".to_owned()),
            license: Some("MIT".to_owned()),
            ..five()[0].clone()
        };
        let m = placeholder_manifest(&c);
        assert!(m.contains("name = \"a\"") && m.contains("version = \"0.0.0\""));
        assert!(m.contains("description = \"Name reservation for a; see https://example.org/r\""));
        assert!(m.contains("license = \"MIT\"") && m.contains("[workspace]"));
        assert!(!m.contains("dependencies"));
    }
}
