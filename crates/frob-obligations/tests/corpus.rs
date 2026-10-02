//! Markdown corpora: one file per rule under `tests/mdtest/`, each with fire and clean blocks.

mod common;

use frob_obligations::InvariantsConfig;
use gob_mdtest::Case;
use gob_rules::Finding;

/// Files every case tree gets, so links and imports have something to resolve to.
const SIDE_FILES: &[(&str, &str)] = &[("exists.md", "# Present heading\n")];

/// Evaluate one corpus block in a fresh tree with the shared ledger; `{{OPEN}}` and `{{DONE}}` become live ticket ids.
fn runner(case: &Case) -> Vec<Finding> {
    let dir = tempfile::tempdir().expect("tempdir");
    let fixture = common::shared_tickets();
    let text = case
        .text
        .replace("{{OPEN}}", &fixture.open)
        .replace("{{DONE}}", &fixture.done);
    common::write_tree(dir.path(), SIDE_FILES);
    common::write_tree(dir.path(), &[(case.file_name.as_str(), text.as_str())]);
    if let Some(cfg) = &case.config {
        common::write_tree(
            dir.path(),
            &[("frob.toml", &format!("[invariants]\n{cfg}\n"))],
        );
    }
    let config = InvariantsConfig::load(dir.path()).expect("config");
    common::evaluate_tree(dir.path(), Some(&fixture.ledger), &config, None).findings
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);
