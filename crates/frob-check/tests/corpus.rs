//! Markdown corpora run through the whole check: `GRL016` blocks are `.grl` files, `CI*` blocks are bound-linter output.

// frob:ticket 01M3ZX7H37B9GKN45MPD6ZNBTY
// frob:ticket 01M4YBK7YTVNC16GHFFK4JKY97

use frob_check::{CheckOptions, run};
use gob_mdtest::Case;
use gob_rules::Finding;

/// Check the block as a repository holding only its file and return the findings.
fn grl_runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let path = dir.path().join(&case.file_name);
    std::fs::create_dir_all(path.parent().expect("file has a parent")).expect("mkdir");
    std::fs::write(&path, &case.text).expect("write block");
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    tracing::debug!(file = %case.file_name, "GRL016 corpus block");
    run(dir.path(), &opts).expect("check runs").findings
}

/// Run the block as the output of a fake zizmor (or actionlint for `CI014`) and keep the rule's findings.
fn ci_runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    let write = |path: &str, text: &str| {
        let full = root.join(path);
        std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        std::fs::write(full, text).expect("write");
    };
    let workflow = format!("name: ci\n{}", "# padding line for offsets\n".repeat(30));
    write(".github/workflows/ci.yml", &workflow);
    write(".github/workflows/bad.yml", &workflow);
    write("fixture.json", &case.text);
    write("fake.sh", "cat fixture.json\n");
    let parser = if case.rule.as_str() == "CI014" {
        "actionlint-json"
    } else {
        "zizmor-json-v1"
    };
    write(
        "frob.toml",
        &format!(
            "[[check.tool]]\nname = \"fake\"\ncommand = \"sh\"\nargs = [\"fake.sh\"]\nparser = \"{parser}\"\nversion_args = [\"-c\", \"echo faketool 1.2.3\"]\n"
        ),
    );
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: false,
        only: vec!["TOOL".to_owned(), "CI".to_owned()],
        ..CheckOptions::default()
    };
    tracing::debug!(rule = %case.rule, "CI corpus block");
    run(root, &opts)
        .expect("check runs")
        .findings
        .into_iter()
        .filter(|f| f.rule.as_str() == case.rule.as_str())
        .collect()
}

/// Route a block to the runner for its rule family.
fn runner(case: &Case) -> Vec<Finding> {
    if case.rule.as_str().starts_with("CI") {
        ci_runner(case)
    } else {
        grl_runner(case)
    }
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);
