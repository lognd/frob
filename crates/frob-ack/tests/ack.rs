//! Dogfood: ack and the DRIFT and AFFECT rules against a temporary git copy of a fixture crate.

use std::path::Path;
use std::time::Duration;

use frob_ack::{Inputs, ack, check, evaluate, register};
use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_git::Repo;
use gob_rules::Finding;
use serde_json::Value;

const LIB: &str = r#"// frob:doc docs/guide.md#greeting
pub fn greet(name: &str) -> String {
    format!("hello {name}")
}

pub fn plain(x: u32) -> u32 {
    x + 1
}

pub fn base(x: u32) -> u32 {
    x * 2
}

pub fn caller(x: u32) -> u32 {
    base(x) + 1
}
"#;

const GUIDE: &str =
    "# Guide\n\n## Greeting\n\nGreets a person by name.\n\n## Farewell\n\nSays goodbye.\n";

struct Fixture {
    dir: tempfile::TempDir,
}

fn git(dir: &Path, args: &[&str]) -> String {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|a| (*a).to_owned()).collect(),
        cwd: Some(dir.to_path_buf()),
        env: Vec::new(),
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 }).run(&spec).expect("run git");
    assert_eq!(
        out.status,
        Outcome::Exited(0),
        "git {args:?}: {}{}",
        out.stdout,
        out.stderr
    );
    out.stdout.trim().to_owned()
}

impl Fixture {
    fn new() -> Self {
        Self::with_autocrlf("false")
    }

    fn with_autocrlf(autocrlf: &str) -> Self {
        let dir = tempfile::tempdir().expect("tempdir");
        let p = dir.path();
        git(p, &["init", "-q"]);
        git(p, &["symbolic-ref", "HEAD", "refs/heads/main"]);
        git(p, &["config", "user.name", "Test User"]);
        git(p, &["config", "user.email", "test@example.com"]);
        git(p, &["config", "core.autocrlf", autocrlf]);
        std::fs::write(p.join(".gitignore"), ".frob/\n").unwrap();
        std::fs::create_dir_all(p.join("src")).unwrap();
        std::fs::create_dir_all(p.join("docs")).unwrap();
        std::fs::write(p.join("src/lib.rs"), LIB).unwrap();
        std::fs::write(p.join("docs/guide.md"), GUIDE).unwrap();
        git(p, &["add", "-A"]);
        git(p, &["commit", "-q", "-m", "fixture"]);
        Self { dir }
    }

    fn root(&self) -> &Path {
        self.dir.path()
    }

    fn commit_all(&self, message: &str) {
        git(self.root(), &["add", "-A"]);
        git(self.root(), &["commit", "-q", "-m", message]);
    }

    /// Rewrites `file` with CRLF line endings, as a `core.autocrlf=true` checkout would.
    fn to_crlf(&self, file: &str) {
        let path = self.root().join(file);
        let text = std::fs::read_to_string(&path)
            .unwrap()
            .replace("\r\n", "\n");
        std::fs::write(path, text.replace('\n', "\r\n")).unwrap();
    }

    fn edit(&self, file: &str, from: &str, to: &str) {
        let path = self.root().join(file);
        let text = std::fs::read_to_string(&path).unwrap();
        assert!(text.contains(from), "{from:?} not in {file}");
        std::fs::write(path, text.replace(from, to)).unwrap();
    }

    fn ack(&self, targets: &[&str]) -> frob_ack::AckOutcome {
        let t: Vec<String> = targets.iter().map(|s| (*s).to_owned()).collect();
        ack(
            self.root(),
            &t,
            false,
            Some("reviewed the contract in full"),
            gob_time::Clock::now(&gob_time::SystemClock),
        )
        .expect("ack")
    }

    fn findings(&self) -> Vec<Finding> {
        let inputs = Inputs::collect(self.root()).expect("collect");
        check(&inputs)
    }
}

fn ids(findings: &[Finding]) -> Vec<String> {
    findings.iter().map(|f| f.rule.to_string()).collect()
}

fn messages(findings: &[Finding], rule: &str) -> Vec<String> {
    findings
        .iter()
        .filter(|f| f.rule.as_str() == rule)
        .map(|f| f.message.clone())
        .collect()
}

// frob:tests crates/frob-ack/src/rules.rs::Drift003
#[test]
fn acked_signature_change_fires_drift003_and_ack_clears_it() {
    let fx = Fixture::new();
    let out = fx.ack(&["src/lib.rs::plain"]);
    assert_eq!(out.acked, ["src/lib.rs::plain"]);
    assert_eq!(out.branch.as_deref(), Some("main"));
    assert!(out.commit.is_some());
    let repo = Repo::discover(fx.root()).unwrap();
    let blob = repo
        .read_blob_at("main", "frob.lock")
        .unwrap()
        .expect("committed");
    assert!(
        String::from_utf8(blob)
            .unwrap()
            .contains("src/lib.rs::plain")
    );
    assert!(fx.root().join("frob.lock").exists());
    assert_eq!(ids(&fx.findings()), Vec::<String>::new());

    fx.edit(
        "src/lib.rs",
        "pub fn plain(x: u32) -> u32",
        "pub fn plain(x: u64) -> u64",
    );
    let found = fx.findings();
    assert_eq!(ids(&found), ["DRIFT003"], "{found:?}");
    assert!(messages(&found, "DRIFT003")[0].contains("src/lib.rs::plain"));

    let again = fx.ack(&["src/lib.rs::plain"]);
    assert_eq!(again.acked, ["src/lib.rs::plain"]);
    assert_eq!(ids(&fx.findings()), Vec::<String>::new());
    let log = git(fx.root(), &["log", "--format=%s", "main"]);
    assert_eq!(log.lines().filter(|l| *l == "ack: 1 symbols").count(), 2);
}

#[test]
fn reack_of_unchanged_state_is_a_no_op() {
    let fx = Fixture::new();
    fx.ack(&["src/lib.rs::plain"]);
    let head = git(fx.root(), &["rev-parse", "main"]);
    let out = fx.ack(&["src/lib.rs::plain"]);
    assert!(out.acked.is_empty() && out.commit.is_none());
    assert_eq!(git(fx.root(), &["rev-parse", "main"]), head);
}

// frob:tests crates/frob-ack/src/rules.rs::Drift002
#[test]
fn doc_to_missing_heading_fires_drift002_with_nearest_heading() {
    let fx = Fixture::new();
    fx.edit("src/lib.rs", "guide.md#greeting", "guide.md#greting");
    let found = fx.findings();
    assert_eq!(ids(&found), ["DRIFT002"], "{found:?}");
    let msg = &messages(&found, "DRIFT002")[0];
    assert!(msg.contains("docs/guide.md#greting"), "{msg}");
    assert!(
        msg.contains("nearest heading is `docs/guide.md#greeting`"),
        "{msg}"
    );

    fx.edit(
        "src/lib.rs",
        "docs/guide.md#greting",
        "docs/missing.md#greeting",
    );
    let msg = &messages(&fx.findings(), "DRIFT002")[0];
    assert!(
        msg.contains("docs/missing.md` is not in the repository"),
        "{msg}"
    );
}

// frob:tests crates/frob-ack/src/rules.rs::Drift001
#[test]
fn code_and_doc_changes_under_an_acked_binding_fire_drift001_naming_the_facet() {
    let fx = Fixture::new();
    fx.ack(&["src/lib.rs::greet"]);
    assert_eq!(ids(&fx.findings()), Vec::<String>::new());

    fx.edit(
        "docs/guide.md",
        "Greets a person by name.",
        "Greets everybody.",
    );
    let found = fx.findings();
    assert_eq!(ids(&found), ["DRIFT001"], "{found:?}");
    assert!(messages(&found, "DRIFT001")[0].contains("target facet"));
    fx.ack(&["src/lib.rs::greet"]);
    assert_eq!(ids(&fx.findings()), Vec::<String>::new());

    fx.edit("src/lib.rs", "hello {name}", "hi {name}");
    let found = fx.findings();
    assert_eq!(ids(&found), ["DRIFT001"], "{found:?}");
    assert!(messages(&found, "DRIFT001")[0].contains("body facet"));
    fx.ack(&["src/lib.rs::greet"]);

    fx.edit(
        "src/lib.rs",
        "pub fn greet(name: &str)",
        "pub fn greet(name: &String)",
    );
    let found = fx.findings();
    assert!(
        messages(&found, "DRIFT001")[0].contains("sig facet"),
        "{found:?}"
    );
}

// frob:tests crates/frob-ack/src/rules.rs::Drift001
#[test]
fn describes_in_a_doc_pairs_without_a_code_side_frob_doc() {
    let fx = Fixture::new();
    fx.edit(
        "docs/guide.md",
        "Says goodbye.",
        "<!-- frob:describes src/lib.rs::plain -->\nSays goodbye.",
    );
    fx.ack(&["src/lib.rs::plain"]);
    assert_eq!(ids(&fx.findings()), Vec::<String>::new());

    fx.edit("docs/guide.md", "Says goodbye.", "Says farewell.");
    let found = fx.findings();
    assert_eq!(ids(&found), ["DRIFT001"], "{found:?}");
    assert!(messages(&found, "DRIFT001")[0].contains("target facet"));
    fx.ack(&["src/lib.rs::plain"]);

    fx.edit(
        "src/lib.rs",
        "x + 1\n}\n\npub fn base",
        "x + 2\n}\n\npub fn base",
    );
    let found = fx.findings();
    assert_eq!(ids(&found), ["DRIFT001"], "{found:?}");
    assert!(messages(&found, "DRIFT001")[0].contains("body facet"));
}

// frob:tests crates/frob-ack/src/rules.rs::Affect001
#[test]
fn changed_public_signature_with_unacked_dependents_fires_affect001() {
    let fx = Fixture::new();
    fx.ack(&["src/lib.rs::base"]);
    fx.edit(
        "src/lib.rs",
        "pub fn base(x: u32) -> u32",
        "pub fn base(x: u64) -> u32",
    );
    let found = fx.findings();
    assert_eq!(ids(&found), ["DRIFT003", "AFFECT001"], "{found:?}");
    assert!(messages(&found, "AFFECT001")[0].contains("src/lib.rs::caller"));

    fx.ack(&["src/lib.rs::caller"]);
    assert_eq!(ids(&fx.findings()), ["DRIFT003"]);
}

#[test]
fn path_target_acks_every_symbol_and_all_reacks_tracked() {
    let fx = Fixture::new();
    let out = fx.ack(&["src/lib.rs"]);
    assert!(out.acked.len() >= 5, "{:?}", out.acked);
    assert!(out.acked.contains(&"src/lib.rs::caller".to_owned()));
    fx.edit(
        "src/lib.rs",
        "x + 1\n}\n\npub fn base",
        "x + 2\n}\n\npub fn base",
    );
    let all = ack(
        fx.root(),
        &[],
        true,
        None,
        gob_time::Clock::now(&gob_time::SystemClock),
    )
    .unwrap();
    assert!(
        all.acked.contains(&"src/lib.rs::plain".to_owned()),
        "{:?}",
        all.acked
    );
    assert!(!all.acked.contains(&"src/lib.rs::caller".to_owned()));
}

#[test]
fn unknown_target_and_empty_request_are_errors() {
    let fx = Fixture::new();
    assert!(
        ack(
            fx.root(),
            &["nope".to_owned()],
            false,
            None,
            gob_time::Clock::now(&gob_time::SystemClock)
        )
        .is_err()
    );
    assert!(
        ack(
            fx.root(),
            &[],
            false,
            None,
            gob_time::Clock::now(&gob_time::SystemClock)
        )
        .is_err()
    );
}

#[test]
fn evaluate_matches_check_and_is_served_from_cache_on_repeat() {
    let fx = Fixture::new();
    fx.ack(&["src/lib.rs::plain"]);
    fx.edit("src/lib.rs", "guide.md#greeting", "guide.md#greting");
    fx.edit("src/lib.rs", "pub fn plain(x: u32)", "pub fn plain(x: u64)");
    let inputs = Inputs::collect(fx.root()).unwrap();
    let direct = check(&inputs);
    let first = evaluate(fx.root(), &inputs);
    let second = evaluate(fx.root(), &inputs);
    assert!(!direct.is_empty());
    assert_eq!(direct, first);
    assert_eq!(first, second);
}

fn cli() -> gob_cli::Cli {
    register(gob_cli::Cli::new("frob", "0.0.0"))
}

fn run(fx: &Fixture, args: &[&str]) -> (i32, Value) {
    let mut full = vec!["--json"];
    full.extend_from_slice(args);
    let (code, out, err) = gob_cli::run_for_test(&cli(), &full, fx.root());
    let json = serde_json::from_str(&out).unwrap_or_else(|e| panic!("{e}: {out} {err}"));
    (code, json)
}

#[test]
fn verbs_ack_why_and_affects_work_end_to_end() {
    let fx = Fixture::new();
    let (code, v) = run(
        &fx,
        &[
            "ack",
            "src/lib.rs::greet",
            "--reason",
            "contract reviewed carefully",
        ],
    );
    assert_eq!(code, 0, "{v}");
    assert_eq!(v["data"]["acked"][0], "src/lib.rs::greet");
    assert!(v["data"]["commit"].is_string());

    let (code, v) = run(&fx, &["ack", "src/lib.rs::greet"]);
    assert_eq!(code, 0);
    assert_eq!(v["data"]["acked"].as_array().unwrap().len(), 0);

    fx.edit("src/lib.rs", "hello {name}", "hi {name}");
    let (code, v) = run(&fx, &["graph", "why", "src/lib.rs::greet"]);
    assert_eq!(code, 0, "{v}");
    let data = &v["data"];
    assert_eq!(data["bindings"][0]["target"], "docs/guide.md#greeting");
    assert_eq!(data["bindings"][0]["line"], 1);
    assert_eq!(data["ack"]["changed_facets"][0], "body");
    assert_eq!(data["findings"][0]["rule"], "DRIFT001");

    let (code, v) = run(&fx, &["graph", "affects", "base"]);
    assert_eq!(code, 0, "{v}");
    let listed = v["data"]["files"]["src/lib.rs"].to_string();
    assert!(listed.contains("src/lib.rs::caller"), "{listed}");

    let (code, _) = run(&fx, &["graph", "why", "no_such_symbol"]);
    assert_eq!(code, 2);
    let (code, _) = run(&fx, &["ack"]);
    assert_eq!(code, 2);

    let (code, v) = run(&fx, &["ack", "--dry-run", "src/lib.rs::plain"]);
    assert_eq!(code, 0, "{v}");
    assert_eq!(v["data"]["dry_run"], true);
}

// frob:tests crates/frob-ack/src/rules.rs::Drift001
#[test]
fn outer_attribute_change_on_an_acked_symbol_fires_drift001_on_attr() {
    let fx = Fixture::new();
    fx.ack(&["src/lib.rs::greet"]);
    fx.edit(
        "src/lib.rs",
        "pub fn greet(name: &str)",
        "#[inline]\npub fn greet(name: &str)",
    );
    let found = fx.findings();
    let msgs = messages(&found, "DRIFT001");
    assert!(msgs.iter().any(|m| m.contains("attr facet")), "{found:?}");
}

const V1_LOCK: &str = r#"version = 1

[entries."src/lib.rs::plain"]
sig = "00"
body = "00"
doc = "00"
acked_by = "Old <old@example.com>"
acked_at = "2026-10-01T00:00:00Z"

[entries."src/lib.rs::gone"]
sig = "00"
body = "00"
doc = "00"
acked_by = "Old <old@example.com>"
acked_at = "2026-10-01T00:00:00Z"
"#;

// frob:tests crates/frob-ack/src/rules.rs::Drift004
#[test]
fn version_one_lock_is_all_reattest_and_ack_all_under_scheme_two_clears_it() {
    let fx = Fixture::new();
    std::fs::write(fx.root().join("frob.lock"), V1_LOCK).unwrap();
    fx.commit_all("old lock");
    let found = fx.findings();
    assert_eq!(ids(&found), ["DRIFT004", "DRIFT004"], "{found:?}");
    let msgs = messages(&found, "DRIFT004");
    assert!(msgs.iter().any(|m| m.contains("src/lib.rs::plain")));
    assert!(
        msgs.iter().all(|m| m.contains("file version 1")),
        "{msgs:?}"
    );

    let t = vec!["src/lib.rs::plain".to_owned()];
    assert!(
        ack(
            fx.root(),
            &t,
            false,
            Some("reviewed the contract"),
            gob_time::Clock::now(&gob_time::SystemClock)
        )
        .is_err()
    );
    assert!(
        ack(
            fx.root(),
            &[],
            true,
            None,
            gob_time::Clock::now(&gob_time::SystemClock)
        )
        .is_err(),
        "migration needs a reason"
    );

    let out = ack(
        fx.root(),
        &[],
        true,
        Some("re-attest under digest scheme 2"),
        gob_time::Clock::now(&gob_time::SystemClock),
    )
    .unwrap();
    assert_eq!(out.acked, ["src/lib.rs::greet", "src/lib.rs::plain"]);
    assert_eq!(ids(&fx.findings()), Vec::<String>::new());
    let text = std::fs::read_to_string(fx.root().join("frob.lock")).unwrap();
    assert!(
        text.starts_with("version = 2\ndigest_scheme = 2\n"),
        "{text}"
    );
    assert!(
        !text.contains("gone"),
        "vanished entries are dropped: {text}"
    );
}

// frob:tests crates/frob-ack/src/rules.rs::Drift004
#[test]
fn scheme_one_lock_under_version_two_is_all_reattest() {
    let fx = Fixture::new();
    fx.ack(&["src/lib.rs::plain"]);
    let text = std::fs::read_to_string(fx.root().join("frob.lock")).unwrap();
    std::fs::write(
        fx.root().join("frob.lock"),
        text.replace("digest_scheme = 2", "digest_scheme = 1"),
    )
    .unwrap();
    fx.commit_all("scheme one lock");
    let found = fx.findings();
    assert_eq!(ids(&found), ["DRIFT004"], "{found:?}");
    assert!(messages(&found, "DRIFT004")[0].contains("digest scheme 1"));
    let out = ack(
        fx.root(),
        &[],
        true,
        Some("re-attest under scheme 2"),
        gob_time::Clock::now(&gob_time::SystemClock),
    )
    .unwrap();
    assert_eq!(out.acked, ["src/lib.rs::greet", "src/lib.rs::plain"]);
    assert_eq!(ids(&fx.findings()), Vec::<String>::new());
}

#[test]
fn lock_and_symbols_agree_on_the_digest_scheme() {
    assert_eq!(gob_lock::DIGEST_SCHEME, gob_symbols::DIGEST_SCHEME);
    assert_eq!(gob_symbols::DIGEST_SCHEME, 2);
}

// frob:tests crates/frob-ack/src/rules.rs::Drift001
#[test]
fn crlf_checkout_under_autocrlf_is_not_drift_but_a_real_edit_still_is() {
    let fx = Fixture::with_autocrlf("true");
    fx.ack(&["src/lib.rs::greet", "src/lib.rs::plain"]);
    assert_eq!(ids(&fx.findings()), Vec::<String>::new());

    fx.to_crlf("src/lib.rs");
    fx.to_crlf("docs/guide.md");
    assert_eq!(git(fx.root(), &["diff", "--stat"]), "");
    let found = fx.findings();
    assert_eq!(ids(&found), Vec::<String>::new(), "{found:?}");

    fx.edit("src/lib.rs", "hello {name}", "hi {name}");
    let found = fx.findings();
    assert_eq!(ids(&found), ["DRIFT001"], "{found:?}");
    assert!(messages(&found, "DRIFT001")[0].contains("body facet"));
}
