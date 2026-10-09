//! COLOR001-002 and CONTRAST001 through `crunk check`: the end-to-end behaviours the rule pages'
//! corpus (`crunk-rules/src/rules/*.md`) cannot express (the pipeline's ingest, exceptions, `[lint]`).

// frob:ticket 01M48FXB2PXX2FBXFKCFWSQYH1
// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use std::path::Path;

use crunk_check::{CheckOptions, run};

/// The default preset as `crunk.toml`.
fn spec() -> &'static str {
    crunk_spec::presets::preset("default").expect("default preset")
}

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// Run crunk over one source file of a fresh repository holding the default preset; ORG001 and TOKENS001 are
/// left out because the fixture sheets sit directly under `css_root` and no tokens file is generated, which is not what these tests judge.
fn findings_of(spec_text: &str, rel: &str, source: &str) -> Vec<gob_rules::Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "crunk.toml", spec_text);
    write(dir.path(), rel, source);
    run(dir.path(), &CheckOptions::default())
        .expect("run")
        .report
        .findings
        .into_iter()
        .filter(|f| !matches!(f.rule.as_str(), "ORG001" | "TOKENS001"))
        .collect()
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn the_message_names_the_nearest_palette_token_and_the_distance() {
    let f = findings_of(spec(), "styles/a.css", ".a { color: #1b1b1b; }\n");
    assert_eq!(f.len(), 1, "{f:?}");
    assert!(
        f[0].message.contains("nearest is --color-ink (distance"),
        "{}",
        f[0].message
    );
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn off_in_lint_silences_the_rule() {
    let off = format!(
        "{}\n",
        spec().replace("[lint]", "[lint]\nCOLOR001 = \"off\"")
    );
    assert!(findings_of(&off, "styles/a.css", ".a { color: #ff0000; }\n").is_empty());
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn without_a_valid_spec_the_rule_does_not_apply() {
    assert!(findings_of("", "styles/a.css", ".a { color: #ff0000; }\n").is_empty());
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn the_finding_is_located_at_the_literal_and_a_waiver_silences_it() {
    let f = findings_of(spec(), "styles/a.css", ".a {\n  color: #1b1b1b;\n}\n");
    assert_eq!(f.len(), 1, "{f:?}");
    assert!(f[0].span.is_some(), "COLOR001 is located: {:?}", f[0]);
    let waived = ".a {\n  color: #1b1b1b; /* crunk:waive COLOR001 reason=\"legacy\" */\n}\n";
    assert!(findings_of(spec(), "styles/a.css", waived).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
#[test]
fn a_jsx_style_prop_is_ingested_when_jsx_globs_are_set() {
    let spec_text = format!("{}\n[jsx]\nglobs = [\"src/**/*\"]\n", spec());
    let src = "export const A = () => <b style={{ color: \"#123456\" }} />;\n";
    let f = findings_of(&spec_text, "src/A.tsx", src);
    assert_eq!(f.len(), 1, "{f:?}");
    assert_eq!(f[0].rule.as_str(), "COLOR001");
}

// frob:tests crates/crunk-rules/src/rules/color002.rs::Color002
#[test]
fn an_undefined_token_with_the_generated_sheet_present_fires_and_without_it_is_unresolved() {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "crunk.toml", spec());
    write(
        dir.path(),
        "styles/a.css",
        ".a { color: var(--color-nope); }\n",
    );
    let unresolved = run(dir.path(), &CheckOptions::default())
        .expect("run")
        .report
        .findings;
    let hit = unresolved
        .iter()
        .find(|f| f.rule.as_str() == "COLOR002")
        .expect("COLOR002");
    assert_eq!(hit.severity, gob_rules::Severity::Unresolved, "{hit:?}");
    write(dir.path(), "styles/tokens.css", ":root {}\n");
    let fired = run(dir.path(), &CheckOptions::default())
        .expect("run")
        .report
        .findings;
    let hit = fired
        .iter()
        .find(|f| f.rule.as_str() == "COLOR002")
        .expect("COLOR002");
    assert_eq!(hit.severity, gob_rules::Severity::Error, "{hit:?}");
}

// frob:tests crates/crunk-rules/src/rules/contrast001.rs::Contrast001
#[test]
fn a_failing_role_pair_is_reported_at_the_spec() {
    let bad = spec()
        .replace("ink = \"#1a1a1a\"", "ink = \"#999999\"")
        .replace("paper = \"#fafaf7\"", "paper = \"#ffffff\"");
    let f = findings_of(&bad, "styles/a.css", ".a { padding: 0; }\n");
    let hit = f
        .iter()
        .find(|f| f.rule.as_str() == "CONTRAST001")
        .expect("CONTRAST001");
    assert!(
        hit.message.contains("is below the 4.5 floor"),
        "{}",
        hit.message
    );
}
