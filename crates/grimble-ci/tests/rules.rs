//! The CI and DK rule pages as an mdtest corpus, plus the acceptance and wiring tests.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use std::collections::BTreeMap;

use gob_rules::{Finding, Severity, UnresolvedReason};
use gob_text::FileInterner;
use grimble_ci::{CiConfig, CiFinding, CiInput, analyze};

/// Analyze an in-memory repository of `(path, text)` pairs.
fn run(repo: &[(&str, &str)], config: &CiConfig) -> grimble_ci::CiReport {
    let files: Vec<String> = repo.iter().map(|(p, _)| (*p).to_owned()).collect();
    let map: BTreeMap<&str, &str> = repo.iter().copied().collect();
    let read = |p: &str| map.get(p).map(|t| (*t).to_owned());
    analyze(&CiInput {
        files: &files,
        read: &read,
        config,
    })
}

/// The extra repository files an example's config words ask for.
fn extras(words: &str) -> Vec<(&'static str, String)> {
    let has = |w: &str| words.split_whitespace().any(|x| x == w);
    let value = |k: &str| {
        words
            .split_whitespace()
            .find_map(|x| x.strip_prefix(k).and_then(|v| v.strip_prefix('=')))
            .map(str::to_owned)
    };
    let mut out = Vec::new();
    if let Some(pin) = value("pin") {
        out.push((
            "rust-toolchain.toml",
            format!("[toolchain]\nchannel = \"{pin}\"\n"),
        ));
    }
    if has("cargo") || value("msrv").is_some() {
        let rv = value("msrv")
            .map(|v| format!("rust-version = \"{v}\"\n"))
            .unwrap_or_default();
        out.push((
            "Cargo.toml",
            format!("[package]\nname = \"x\"\nversion = \"0.1.0\"\n{rv}"),
        ));
    }
    if has("dependabot") {
        out.push((
            ".github/dependabot.yml",
            "version: 2\nupdates:\n  - package-ecosystem: cargo\n    directory: /\n  - package-ecosystem: github-actions\n    directory: /\n".to_owned(),
        ));
    }
    if has("dependabot-cargo-only") {
        out.push((
            ".github/dependabot.yml",
            "version: 2\nupdates:\n  - package-ecosystem: cargo\n    directory: /\n".to_owned(),
        ));
    }
    if has("renovate") {
        out.push(("renovate.json", "{}".to_owned()));
    }
    if has("owners-ok") {
        out.push(("CODEOWNERS", "/.github/ @org/maintainers\n".to_owned()));
    }
    if has("owners-missing") {
        out.push(("CODEOWNERS", "docs/ @org/docs\n".to_owned()));
    }
    out
}

/// Run one example and keep the findings of the page's rule.
fn runner(case: &gob_mdtest::Case) -> Vec<Finding> {
    // frob:tests crates/grimble-ci/src/lib.rs::analyze
    // frob:tests crates/grimble-ci/src/rules/ci001.rs::Ci001
    // frob:tests crates/grimble-ci/src/rules/ci002.rs::Ci002
    // frob:tests crates/grimble-ci/src/rules/ci003.rs::Ci003
    // frob:tests crates/grimble-ci/src/rules/ci004.rs::Ci004
    // frob:tests crates/grimble-ci/src/rules/ci005.rs::Ci005
    // frob:tests crates/grimble-ci/src/rules/ci006.rs::Ci006
    // frob:tests crates/grimble-ci/src/rules/ci007.rs::Ci007
    // frob:tests crates/grimble-ci/src/rules/ci008.rs::Ci008
    // frob:tests crates/grimble-ci/src/rules/ci009.rs::Ci009
    // frob:tests crates/grimble-ci/src/rules/ci010.rs::Ci010
    // frob:tests crates/grimble-ci/src/rules/ci011.rs::Ci011
    // frob:tests crates/grimble-ci/src/rules/ci012.rs::Ci012
    // frob:tests crates/grimble-ci/src/rules/dk001.rs::Dk001
    // frob:tests crates/grimble-ci/src/rules/dk002.rs::Dk002
    // frob:tests crates/grimble-ci/src/rules/dk003.rs::Dk003
    // frob:tests crates/grimble-ci/src/rules/dk004.rs::Dk004
    let words = case.config.as_deref().unwrap_or("");
    let has = |w: &str| words.split_whitespace().any(|x| x == w);
    let mut config = CiConfig {
        require_digest: has("require-digest"),
        ..CiConfig::default()
    };
    config.allow_tag_pins_for.extend(
        words
            .split_whitespace()
            .filter_map(|x| x.strip_prefix("allow-tag-pins="))
            .map(str::to_owned),
    );
    config.contexts.extend(
        words
            .split_whitespace()
            .filter_map(|x| x.strip_prefix("context="))
            .map(str::to_owned),
    );
    if let Some(host) = words
        .split_whitespace()
        .find_map(|x| x.strip_prefix("allow="))
    {
        config.allow_pipe_hosts.push(host.to_owned());
    }
    let extra = extras(words);
    let mut repo: Vec<(&str, &str)> = vec![(case.file_name.as_str(), case.text.as_str())];
    repo.extend(extra.iter().map(|(p, t)| (*p, t.as_str())));
    let mut files = FileInterner::new();
    run(&repo, &config)
        .findings
        .into_iter()
        .filter(|f| f.rule == case.rule.as_str())
        .filter_map(|f| f.into_finding(&mut files))
        .collect()
}

gob_mdtest::mdtest!(dir = "src/rules", runner = runner);

const BARE: &str = "name: ci\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n";

#[test]
fn missing_permissions_and_timeout_fire_with_the_remedy() {
    // frob:tests crates/grimble-ci/src/lib.rs::analyze
    let report = run(&[(".github/workflows/ci.yml", BARE)], &CiConfig::default());
    let of = |id: &str| {
        report
            .findings
            .iter()
            .find(|f| f.rule == id)
            .map(|f| f.message.clone())
    };
    assert!(
        of("CI002").is_some_and(|m| m.contains("contents: read")),
        "{:?}",
        report.findings
    );
    assert!(
        of("CI005").is_some_and(|m| m.contains("timeout-minutes")),
        "{:?}",
        report.findings
    );
}

#[test]
fn no_files_makes_every_rule_not_applicable() {
    // frob:tests crates/grimble-ci/src/lib.rs::analyze
    let report = run(&[("README.md", "hi")], &CiConfig::default());
    assert!(report.findings.is_empty());
    assert_eq!(report.not_applicable.len(), 16);
}

#[test]
fn unparsable_workflow_is_unresolved() {
    // frob:tests crates/grimble-ci/src/lib.rs::analyze
    let report = run(
        &[(".github/workflows/ci.yml", "on: [\n  :")],
        &CiConfig::default(),
    );
    let f: &CiFinding = report.findings.first().expect("a verdict");
    assert_eq!(f.severity, Severity::Unresolved);
    assert!(matches!(f.reason, Some(UnresolvedReason::ParseFailed)));
}

/// Rule ids of every finding in a one-file run.
fn ids(body: &str, cfg: &CiConfig) -> Vec<String> {
    run(&[(".github/workflows/ci.yml", body)], cfg)
        .findings
        .iter()
        .map(|f| f.rule.to_owned())
        .collect()
}

#[test]
fn supply_rules_survive_odd_yaml() {
    // frob:tests crates/grimble-ci/src/supply.rs::check
    let cfg = CiConfig::default();
    for body in [
        "",
        "on: push\n",
        "on: push\njobs:\n",
        "on: push\njobs:\n  a:\n    steps: 3\n",
        "on: push\njobs:\n  a:\n    steps:\n      - 7\n      - run: 5\n      - uses: ''\n",
        "on: push\njobs:\n  a:\n    steps:\n      - run: echo ${{ github.event.issue.title\n",
    ] {
        let found = ids(body, &cfg);
        assert!(!found.iter().any(|r| r == "CI001"), "{body:?}");
    }
}

#[test]
fn pinned_ref_honours_case_digest_and_allowlist() {
    // frob:tests crates/grimble-ci/src/supply.rs::check
    let sha = "A".repeat(40);
    let pinned = format!("on: push\njobs:\n  a:\n    steps:\n      - uses: x/y@{sha}\n");
    assert!(
        !ids(&pinned, &CiConfig::default())
            .iter()
            .any(|r| r == "CI001")
    );
    let digest = "on: push\njobs:\n  a:\n    steps:\n      - uses: docker://alpine@sha256:abc\n";
    assert!(
        !ids(digest, &CiConfig::default())
            .iter()
            .any(|r| r == "CI001")
    );
    let tag = "on: push\njobs:\n  a:\n    steps:\n      - uses: acme/y@v1\n";
    assert!(ids(tag, &CiConfig::default()).iter().any(|r| r == "CI001"));
    let cfg = CiConfig {
        allow_tag_pins_for: vec!["acme".to_owned()],
        ..CiConfig::default()
    };
    assert!(!ids(tag, &cfg).iter().any(|r| r == "CI001"));
}

#[test]
fn unterminated_expression_does_not_panic_ci007() {
    // frob:tests crates/grimble-ci/src/supply.rs::check
    let body =
        "on: push\njobs:\n  a:\n    steps:\n      - run: echo ${{ github.event.issue.title\n";
    let _ = ids(body, &CiConfig::default());
}

/// A host with fixed subject counts.
struct Fixed;

impl grimble_ci::host::CiHost for Fixed {
    fn ci_subjects_of(&self, id: &str) -> usize {
        id.len()
    }
}

#[test]
fn host_binds_and_converts() {
    // frob:tests crates/grimble-ci/src/rules/mod.rs::bind
    // frob:tests crates/grimble-ci/src/host.rs::CiHost.ci_subjects_of
    // frob:tests crates/grimble-arch/src/finding.rs::ArchFinding.into_finding
    assert_eq!(grimble_ci::rules::bind::<Fixed>().len(), 16);
    assert_eq!(grimble_ci::host::CiHost::ci_subjects_of(&Fixed, "CI002"), 5);
    let report = run(&[(".github/workflows/ci.yml", BARE)], &CiConfig::default());
    let mut files = FileInterner::new();
    let converted: Vec<_> = report
        .findings
        .into_iter()
        .filter_map(|f| f.into_finding(&mut files))
        .collect();
    assert!(converted.iter().any(|f| f.rule.as_str() == "CI002"));
}

/// A one-job workflow whose single step runs `script` (indented under a literal block).
fn verb_workflow(script: &str, extra_step_keys: &str) -> String {
    let body: String = script.lines().fold(String::new(), |mut acc, l| {
        acc.push_str("          ");
        acc.push_str(l);
        acc.push('\n');
        acc
    });
    format!(
        "name: ci\non: push\npermissions:\n  contents: read\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - {extra_step_keys}run: |\n{body}"
    )
}

/// The `frob` verb paths CI012 reports for `script`, with dependabot present so only verbs show.
fn bad_verbs(script: &str, extra_step_keys: &str) -> Vec<String> {
    let wf = verb_workflow(script, extra_step_keys);
    let dependabot =
        "version: 2\nupdates:\n  - package-ecosystem: github-actions\n    directory: /\n";
    run(
        &[
            (".github/workflows/ci.yml", wf.as_str()),
            (".github/dependabot.yml", dependabot),
        ],
        &CiConfig::default(),
    )
    .findings
    .into_iter()
    .filter(|f| f.rule == "CI012")
    .filter_map(|f| f.anchor.split_once(":verb:").map(|(_, v)| v.to_owned()))
    .collect()
}

#[test]
fn unknown_frob_verb_fires() {
    // frob:tests crates/grimble-ci/src/lib.rs::analyze
    assert_eq!(bad_verbs("frob chek\n", ""), ["chek"]);
    assert_eq!(
        bad_verbs("frob ticket frobnicate T-1\n", ""),
        ["ticket frobnicate"]
    );
    let found = run(
        &[(
            ".github/workflows/ci.yml",
            verb_workflow("frob chek\n", "").as_str(),
        )],
        &CiConfig::default(),
    );
    let hit = found
        .findings
        .iter()
        .find(|f| f.anchor.contains(":verb:"))
        .expect("a verb finding");
    assert!(hit.message.contains("`check`"), "{}", hit.message);
}

#[test]
fn known_frob_verbs_stay_quiet() {
    // frob:tests crates/grimble-ci/src/lib.rs::analyze
    let script = "frob check --ticket T-1\nfrob ticket show T-1\nfrob lease list\nfrob work T-1\nfrob land T-1 --wait 3\nfrob help whatever\nfrob\nfrob --help\nfrob -V\n";
    assert_eq!(bad_verbs(script, ""), Vec::<String>::new());
}

#[test]
fn frob_verb_scan_handles_shell_shapes() {
    // frob:tests crates/grimble-ci/src/lib.rs::analyze
    // Judged: pipelines, env prefixes, wrappers, control flow, paths, globals, continuations.
    for (script, want) in [
        ("echo hi | frob nope", "nope"),
        ("true && frob nope", "nope"),
        ("FOO=1 BAR='a b' frob nope", "nope"),
        ("sudo -E env X=1 frob nope", "nope"),
        ("if ! frob nope; then echo; fi", "nope"),
        ("x=$(frob nope)", "nope"),
        ("./target/release/frob nope", "nope"),
        ("frob --format json --cwd sub nope", "nope"),
        ("frob \\\n  ticket \\\n  nope", "ticket nope"),
        ("frob 'nope'", "nope"),
        ("frob ticket nope # trailing", "ticket nope"),
    ] {
        assert_eq!(bad_verbs(script, ""), [want], "{script:?}");
    }
    // Not judged: comments, quoted text, arguments, heredoc bodies, interpolation, flags only.
    for script in [
        "# frob nope",
        "echo \"frob nope\"",
        "echo 'run frob nope'",
        "git add frob nope",
        "cat <<'EOF'\nfrob nope\nEOF",
        "frob ${{ matrix.verb }}",
        "frob \"$VERB\" now",
        "frob ticket ${{ matrix.sub }}",
        "frob ticket --cwd x show",
        "frob --json",
        "frob nope --help",
        "${{ env.BIN }} nope",
        "for t in frob grimble; do cp $t out; done",
        "cargo run -p frob -- nope",
        "command -v frob",
    ] {
        assert_eq!(bad_verbs(script, ""), Vec::<String>::new(), "{script:?}");
    }
    // Another shell is not read; repeats collapse to one finding.
    assert_eq!(
        bad_verbs("frob nope", "shell: python\n        "),
        Vec::<String>::new()
    );
    assert_eq!(bad_verbs("frob nope\nfrob nope", ""), ["nope"]);
}
