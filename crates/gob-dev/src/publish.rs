//! `cargo dev publish`: publish the workspace crates to crates.io in dependency order.
//!
//! The run is resumable by construction: every crate whose exact version is
//! already on the index is skipped, so a re-run after a partial failure
//! continues at the first unpublished crate and never needs a version bump.
//! The registry and the cargo invocation are traits ([`Registry`],
//! [`CargoRunner`]) so tests drive the whole flow with fakes and nothing
//! reaches crates.io; [`CratesIo`] and [`CargoCli`] are the real
//! implementations, spawned through `gob-exec` (PROC001).
//! Design: `docs/design/releases.md` section 5 (publishing) and `monorepo.md` 4.
// frob:ticket 01M4069Y65FA7GGXG2F6N2KET1

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
}

/// The cargo side of a publish.
pub trait CargoRunner {
    /// Run `cargo publish` for one crate.
    ///
    /// # Errors
    /// [`PublishError::Cargo`] when cargo fails.
    fn publish(&self, krate: &Crate) -> Result<(), PublishError>;
}

/// Knobs of one publish run.
#[derive(Debug, Clone, Copy)]
pub struct Options {
    /// Print the order and publish nothing (no registry reads either).
    pub dry_run: bool,
    /// Index checks after each publish before giving up.
    pub index_attempts: u32,
    /// Pause between index checks.
    pub index_interval: Duration,
}

impl Default for Options {
    /// Real publish; wait up to ten minutes for each crate to reach the index.
    fn default() -> Self {
        Self {
            dry_run: false,
            index_attempts: 60,
            index_interval: Duration::from_secs(10),
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
        cargo.publish(c)?;
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

impl Registry for CratesIo {
    fn has_version(&self, name: &str, version: &str) -> Result<bool, PublishError> {
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
            "200" => index_lists(name, body, version),
            "404" | "410" => Ok(false),
            other => Err(fail(format!("index answered HTTP {other}"))),
        }
    }
}

/// Runs `cargo publish -p <crate> --locked` in the workspace root.
#[derive(Debug)]
pub struct CargoCli {
    /// Workspace root to publish from.
    pub root: PathBuf,
}

impl CargoRunner for CargoCli {
    fn publish(&self, krate: &Crate) -> Result<(), PublishError> {
        let fail = |reason: String| PublishError::Cargo {
            krate: krate.name.clone(),
            version: krate.version.clone(),
            reason,
        };
        let spec = Spec {
            program: Program::Cargo,
            args: ["publish", "-p", &krate.name, "--locked"]
                .map(str::to_owned)
                .to_vec(),
            cwd: Some(self.root.clone()),
            env: Vec::new(),
            timeout: PUBLISH_TIMEOUT,
            capture: false,
        };
        let out = runner().run(&spec).map_err(|e| fail(e.to_string()))?;
        match out.status {
            Outcome::Exited(0) => Ok(()),
            other => Err(fail(format!("cargo ended {other:?}"))),
        }
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
    }

    impl CargoRunner for Fake {
        fn publish(&self, krate: &Crate) -> Result<(), PublishError> {
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
}
