//! Corpus tests: PARSE001, DSL001 and DSL002 with firing and clean controls.

mod common;

use gob_mdtest::Case;
use gob_rules::Finding;

/// Run the default scanner over one corpus block.
fn runner(case: &Case) -> Vec<Finding> {
    common::scan(&case.file_name, &case.text).findings
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);
