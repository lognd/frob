//! The extraction regression: the pipeline reports exactly the findings the pre-extraction
//! `frob check` reported on two fixture trees (ticket 01M3Z713NBP986Q2ZDHKKR84AW).
//!
//! The snapshots in `tests/snapshots/` were recorded from the pre-extraction pipeline
//! before it was deleted. Re-record deliberately with `FROB_BLESS=1 cargo test -p
//! frob-check --test equivalence`; a diff otherwise means behaviour changed.

use std::fmt::Write as _;
use std::path::Path;

use frob_check::{CheckOptions, CheckReport, run};

/// The upper-case work marker, assembled so this file does not carry one.
fn marker() -> String {
    ["TO", "DO"].concat()
}

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

/// Directives and paths that would trip the repository's own gate, assembled at run time.
fn proc_ref() -> String {
    ["std::", "process::Command::new(\"ls\");"].concat()
}

/// Fixture A: marker, undocumented item, broken links, a vetted and a rejected accept, a
/// dangling `frob:tests`, an invariant document nothing upholds, a forbidden import, a
/// process reference.
fn fixture_a(root: &Path) {
    write(
        root,
        "frob.toml",
        "[invariants]\nforbid_imports = [{ from = \"src/inner/**\", to = \"crate::outer\", reason = \"inner never imports outer\" }]\n",
    );
    write(
        root,
        "src/lib.rs",
        &format!(
            "//! Library.\n// {m}: handle the empty case\npub fn undocumented() {{}}\n\n/* frob:accept COV001 because=\"temporary hack for now\" */\n/// Documented.\npub fn accepted() {{}}\n\n/* frob:tests tests::missing */\n/// Bound to nothing.\npub fn dangling() {{}}\n",
            m = marker()
        ),
    );
    write(
        root,
        "src/inner/mod.rs",
        &format!(
            "//! Inner.\nuse crate::outer::thing;\n\n/// Spawns.\npub fn spawn() {{\n    {}\n}}\n",
            proc_ref()
        ),
    );
    write(
        root,
        "README.md",
        "# Fixture\n\nSee [code](src/lib.rs), [gone](src/gone.rs) and [anchor](NOTES.md#nowhere).\n",
    );
    write(root, "NOTES.md", "# Notes\n\n## Real heading\n\nText.\n");
    write(root, "invariants/never-orphan.md", "# Never orphan\n\nBody.\n");
}

/// Fixture B: a tested and an untested public function, a test reaching through a helper,
/// nested modules, a TOML file with a directive, a `[check] exclude`.
fn fixture_b(root: &Path) {
    write(
        root,
        "frob.toml",
        "[check]\nexclude = [\"vendor/\"]\nfail_on = \"warn\"\n",
    );
    write(
        root,
        "Cargo.toml",
        "# frob:accept DOC002 because=\"manifest carries no links to check here\"\n[package]\nname = \"fx\"\n",
    );
    write(
        root,
        "src/lib.rs",
        "//! Crate.\n/// Reached by a test.\npub fn covered() { helper(); }\n\nfn helper() {}\n\n/// Reached by nothing.\npub fn lonely() {}\n\n/// Undocumented siblings follow.\npub mod nested;\n",
    );
    write(
        root,
        "src/nested.rs",
        "pub fn undocumented_nested() {}\n\n/// Documented.\npub fn documented_nested() {}\n",
    );
    write(
        root,
        "tests/it.rs",
        "#[test]\nfn reaches_covered() {\n    fx::covered();\n}\n",
    );
    write(
        root,
        "vendor/big.rs",
        "pub fn excluded_from_everything() {}\n",
    );
    write(root, "docs/guide.md", "# Guide\n\n[up](../README.md)\n");
}

/// One line per finding and per suppressed finding, in the report's order.
fn render(report: &CheckReport) -> String {
    let mut out = String::new();
    let place = |f: &gob_rules::Finding| match f.span {
        Some(s) => format!(
            "{}@{}-{}",
            report.files.path(s.file).unwrap_or("?"),
            u32::from(s.range.start()),
            u32::from(s.range.end())
        ),
        None => "-".to_owned(),
    };
    for f in &report.findings {
        writeln!(
            out,
            "{:?} {} {} {} | {}",
            f.severity,
            f.rule,
            place(f),
            f.fingerprint,
            f.message
        )
        .expect("write to string");
    }
    for (f, ex) in &report.suppressed {
        writeln!(
            out,
            "suppressed {} {} by {:?} | {}",
            f.rule,
            place(f),
            ex.kind,
            ex.reason
        )
        .expect("write to string");
    }
    writeln!(out, "exit {:?}", report.exit_code()).expect("write to string");
    out
}

fn check_snapshot(name: &str, build: fn(&Path)) {
    let dir = tempfile::tempdir().expect("tempdir");
    build(dir.path());
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    let cold = render(&run(dir.path(), &opts).expect("cold run"));
    let warm = render(&run(dir.path(), &opts).expect("warm run"));
    assert_eq!(cold, warm, "cold and warm runs match");
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/snapshots")
        .join(format!("{name}.txt"));
    if std::env::var_os("FROB_BLESS").is_some() {
        std::fs::write(&path, &cold).expect("write snapshot");
        return;
    }
    let want = std::fs::read_to_string(&path).expect("snapshot present; record with FROB_BLESS=1");
    assert_eq!(cold, want, "findings differ from {}", path.display());
}

// frob:tests crates/frob-check/src/pipeline.rs::run
#[test]
fn fixture_a_matches_the_recorded_findings() {
    check_snapshot("fixture_a", fixture_a);
}

// frob:tests crates/frob-check/src/pipeline.rs::run
#[test]
fn fixture_b_matches_the_recorded_findings() {
    check_snapshot("fixture_b", fixture_b);
}
