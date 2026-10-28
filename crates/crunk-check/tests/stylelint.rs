//! A `[[check.tool]]` stylelint stage through `crunk check`: findings carry crunk ids and are Advisory.

// frob:ticket 01M4D95VS2KPK91REEZ8KA74BB

use std::path::Path;

use crunk_check::{CheckOptions, run};
use gob_rules::Severity;

const STYLELINT: &str = include_str!("../../gob-check/tests/fixtures/stylelint.json");

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

// frob:tests crates/gob-check/src/tool_parse.rs::parse_stylelint
#[test]
fn a_stylelint_stage_yields_advisory_findings_under_crunk_ids() {
    let dir = tempfile::tempdir().expect("tempdir");
    let spec = crunk_spec::presets::preset("default").expect("default preset");
    let stage = "\n[[check.tool]]\nname = \"stylelint\"\ncommand = \"sh\"\nargs = [\"fake.sh\"]\nparser = \"stylelint-json\"\nversion_args = [\"-c\", \"echo stylelint 16.1.0\"]\n";
    write(dir.path(), "crunk.toml", &format!("{spec}{stage}"));
    write(dir.path(), "fixture.json", STYLELINT);
    write(dir.path(), "fake.sh", "cat fixture.json\nexit 2\n");
    write(
        dir.path(),
        "app.css",
        &format!(".a {{ color: red; }}\n{}", "/* padding */\n".repeat(20)),
    );
    let got = run(dir.path(), &CheckOptions::default()).expect("run");
    let mut found: Vec<(String, Severity)> = got
        .report
        .findings
        .iter()
        .map(|f| (f.rule.to_string(), f.severity))
        .filter(|(id, _)| id.starts_with("WCSS") || id.starts_with("TOOL"))
        .collect();
    found.sort();
    assert_eq!(
        found,
        [
            ("TOOL002".to_owned(), Severity::Error),
            ("WCSS002".to_owned(), Severity::Error),
            ("WCSS003".to_owned(), Severity::Error),
        ]
    );
}
