//! Phase 2 exit, end to end: a hullbreach project's palette drives the Tailwind, CSS, USS and C#
//! exports, and a stress-fail literal that differs from `ThrustRed` is reported as drift (naming
//! `ThrustRed`, exit 1) until the generated files are reconciled (exit 0).
//!
//! Findings, not design/tokens: the exporters render `crunk.toml` only, so the authored
//! `design/tokens/hullbreach.toml` (which holds the stress-fail literal) feeds the TOKEN lints
//! and not the exports. The fixture documents that split; follow-up ticket ~K4DJXGN.

// frob:ticket 01M5XCVZK2S3FYG8KPS7YXEHNJ

use std::path::Path;

use gob_cli::run_for_test;
use serde_json::Value;

/// The `ThrustRed` literal in `crunk.toml`'s palette.
const THRUST_RED: &str = "#e63326";

fn copy_tree(from: &Path, to: &Path) {
    std::fs::create_dir_all(to).expect("mkdir");
    for entry in std::fs::read_dir(from).expect("read fixture dir") {
        let entry = entry.expect("dir entry");
        let dest = to.join(entry.file_name());
        if entry.file_type().expect("file type").is_dir() {
            copy_tree(&entry.path(), &dest);
        } else {
            std::fs::copy(entry.path(), dest).expect("copy fixture file");
        }
    }
}

/// A fresh copy of the hullbreach fixture project.
fn project() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let fixture = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/hullbreach_tokens");
    copy_tree(&fixture, dir.path());
    dir
}

fn crunk(dir: &Path, args: &[&str]) -> (i32, String, String) {
    run_for_test(&crunk::cli(), args, dir)
}

fn json(out: &str) -> Value {
    serde_json::from_str(out).unwrap_or_else(|e| panic!("not json ({e}): {out}"))
}

/// The rendered text of one export target.
fn exported(dir: &Path, target: &str) -> String {
    let (code, out, err) = crunk(dir, &["export", target, "--json"]);
    assert_eq!(code, 0, "export {target}: {out} {err}");
    json(&out)["data"]["content"]
        .as_str()
        .unwrap_or_else(|| panic!("export {target} has no content"))
        .to_owned()
}

/// The stress-fail literal the authored `design/tokens` file declares.
fn stress_fail_literal(dir: &Path) -> String {
    let text = std::fs::read_to_string(dir.join("design/tokens/hullbreach.toml")).expect("read");
    let line = text
        .lines()
        .find(|l| l.starts_with("stress-fail"))
        .expect("stress-fail line");
    line.split('"').nth(1).expect("quoted literal").to_owned()
}

/// The EXPORT002 findings of `crunk check`, as one string each.
fn parity_findings(dir: &Path) -> Vec<String> {
    let (_, out, _) = crunk(dir, &["check", "--json"]);
    json(&out)["data"]["findings"]
        .as_array()
        .expect("findings")
        .iter()
        .filter(|f| f["rule"] == "EXPORT002")
        .map(Value::to_string)
        .collect()
}

// frob:tests crates/crunk/src/export.rs::ExportCss
// frob:tests crates/crunk/src/export.rs::ExportTailwind
// frob:tests crates/crunk/src/export.rs::ExportUss
// frob:tests crates/crunk/src/export.rs::ExportCsharp
#[test]
fn e2e_tokens_hullbreach_palette_drives_every_export() {
    let dir = project();
    let p = dir.path();
    assert!(exported(p, "css").contains("--color-thrustred: #e63326;"));
    assert!(exported(p, "uss").contains("--color-thrustred: #e63326;"));
    assert!(exported(p, "tailwind").contains("\"ThrustRed\": \"var(--color-thrustred)\""));
    assert!(exported(p, "csharp").contains("ColorThrustred = new CrunkColor(0.9019608f"));
}

// frob:tests crates/crunk/src/tokens.rs::Tokens
#[test]
fn e2e_tokens_hullbreach_stress_fail_drift_names_thrustred_until_reconciled() {
    let dir = project();
    let p = dir.path();
    let stress = stress_fail_literal(p);
    assert_ne!(
        stress, THRUST_RED,
        "the fixture must carry a differing literal"
    );

    let (code, out, err) = crunk(p, &["tokens", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    assert!(p.join("styles/tokens.css").is_file());
    assert!(p.join("tailwind.tokens.json").is_file());
    let (code, out, _) = crunk(p, &["tokens", "--check", "--json"]);
    assert_eq!(code, 0, "freshly generated files are clean: {out}");
    assert!(parity_findings(p).is_empty(), "no parity drift when fresh");

    // The web side takes the stress-fail literal where the HUD's ThrustRed belongs.
    let css = p.join("styles/tokens.css");
    let text = std::fs::read_to_string(&css).expect("read css");
    assert!(text.contains(THRUST_RED));
    std::fs::write(&css, text.replace(THRUST_RED, &stress)).expect("write css");

    let (code, out, _) = crunk(p, &["tokens", "--check", "--json"]);
    assert_eq!(code, 1, "{out}");
    assert_eq!(json(&out)["data"]["status"], "drifted");

    let found = parity_findings(p);
    assert!(!found.is_empty(), "EXPORT002 must fire");
    assert!(
        found.iter().all(|f| f.contains("--color-thrustred")),
        "every parity finding names ThrustRed: {found:?}"
    );
    assert!(found.iter().any(|f| f.contains(&stress)), "{found:?}");

    // Reconcile: regenerate from crunk.toml.
    let (code, out, err) = crunk(p, &["tokens", "--json"]);
    assert_eq!(code, 0, "{out} {err}");
    let (code, out, _) = crunk(p, &["tokens", "--check", "--json"]);
    assert_eq!(code, 0, "{out}");
    assert!(parity_findings(p).is_empty(), "drift resolved");
}
