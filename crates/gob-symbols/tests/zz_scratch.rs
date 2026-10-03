//! scratch
use gob_cache::Cache;
use gob_symbols::build_graph;
use gob_walk::{WalkConfig, walk};
use std::path::Path;
#[test]
#[ignore = "scratch"]
fn scratch() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let walked = walk(&root, &WalkConfig::default()).unwrap();
    let g = build_graph(&root, &walked.files, &Cache::null());
    for want in std::env::var("SCR").unwrap().split(',') {
        let (f, l) = want.split_once(':').unwrap();
        let l: u32 = l.parse().unwrap();
        for e in g.edges_with_status() {
            if e.from.path().ends_with(f) && e.line == Some(l) {
                println!(
                    "{} -> {:?} {:?} q={:?} {:?} {}",
                    e.from,
                    e.to.as_ref().map(ToString::to_string),
                    e.status,
                    e.qualifier,
                    e.reason,
                    e.text.clone().unwrap_or_default()
                );
            }
        }
    }
}
