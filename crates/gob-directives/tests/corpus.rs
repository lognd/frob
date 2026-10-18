//! Corpus tests: PARSE001 and DSL001 to DSL003 with firing and clean controls.

use crate::common;

use gob_directives::ScanConfig;
use gob_mdtest::Case;
use gob_rules::Finding;

/// Run a `frob` plus `grimble` scanner over one corpus block.
fn runner(case: &Case) -> Vec<Finding> {
    let config = ScanConfig {
        namespaces: vec!["frob".to_owned(), "grimble".to_owned()],
        product: "frob".to_owned(),
    };
    common::scan_with(&config, &case.file_name, &case.text).findings
}

gob_mdtest::mdtest!(dir = "tests/mdtest", runner = runner);
