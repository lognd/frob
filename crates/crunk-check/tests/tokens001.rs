//! TOKENS001 and the Tailwind facts through `crunk check`: a stale generated tokens file is a
//! finding, `[lint]` silences it, and the TW rules run over the collected facts.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use std::path::Path;

use crunk_check::{CheckOptions, run};

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

fn spec() -> &'static str {
    crunk_spec::presets::preset("default").expect("default preset")
}

fn project(spec_text: &str) -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    write(dir.path(), "crunk.toml", spec_text);
    write(dir.path(), "styles/base/a.css", ".a { margin: 0; }\n");
    write(dir.path(), "styles/tokens.css", ":root {}\n");
    dir
}

// frob:tests crates/crunk-rules/src/rules/tokens001.rs::Tokens001
#[test]
fn a_stale_tokens_file_is_a_finding_that_lint_can_silence() {
    let dir = project(spec());
    let report = run(dir.path(), &CheckOptions::default())
        .expect("run")
        .report;
    let drift: Vec<_> = report
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "TOKENS001")
        .collect();
    assert_eq!(drift.len(), 1, "{:?}", report.findings);
    assert_eq!(
        drift[0].message,
        "tokens file drifted; run `crunk tokens` to regenerate"
    );
    let off = project(&spec().replace("[lint]", "[lint]\nTOKENS001 = \"off\""));
    let report = run(off.path(), &CheckOptions::default())
        .expect("run")
        .report;
    assert!(
        report
            .findings
            .iter()
            .all(|f| f.rule.as_str() != "TOKENS001")
    );
}

// frob:tests crates/crunk-check/src/tailwind.rs::collect
#[test]
fn utilities_are_judged_over_the_collected_tailwind_facts() {
    let dir = project(&format!("{}\n[jsx]\nglobs = [\"src/**/*\"]\n", spec()));
    write(
        dir.path(),
        "src/A.tsx",
        "export const A = () => <div className=\"p-[13px]\" />;\n",
    );
    let run = run(dir.path(), &CheckOptions::default()).expect("run");
    let rules: Vec<_> = run
        .report
        .findings
        .iter()
        .map(|f| f.rule.as_str())
        .collect();
    // Without node and an install the utility is Unresolved; with them it is off the scale.
    assert!(rules.contains(&"TW001"), "{rules:?}");
}
