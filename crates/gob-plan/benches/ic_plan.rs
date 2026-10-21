//! Instruction-count benchmarks (gungraun, Valgrind callgrind) of the plan executor and the
//! source parser, compared against the base by `cargo dev bench-ic` on pull requests
//! (build-test-ci.md section 6). The wall-clock B1 bench stays on criterion.
// frob:ticket 01M47QVC49RXV29NCG3N9G1JSM
#![allow(missing_docs, reason = "gungraun macros generate undocumented items")]
#![allow(
    dead_code,
    reason = "the timing helpers belong to the wall-clock B1 bench"
)]

mod b1;

use std::hint::black_box;

use b1::{Case, Prepared, cases, fixture, prepare, run_plan};
use gungraun::{library_benchmark, library_benchmark_group, main};

const LINES: usize = 400;

// frob:waive DEAD001 reason="called by the gungraun main! macro, which the call graph cannot see"
/// Builds the plan of rule `id` and a fixture file it runs over, outside the measured region.
fn setup(id: &'static str) -> (Case, Prepared) {
    let case = cases()
        .expect("rules compile")
        .into_iter()
        .find(|c| c.id == id)
        .expect("known rule");
    let (lang, file) = if id == "DOC002" {
        ("markdown", fixture::markdown_file(0, LINES))
    } else {
        ("rust", fixture::rust_file(0, LINES))
    };
    (case, prepare(&file, lang).expect("fixture models"))
}

// frob:waive DEAD001 reason="called by the gungraun main! macro, which the call graph cannot see"
#[library_benchmark]
#[bench::todo001(args = ("TODO001"), setup = setup)]
#[bench::cov001(args = ("COV001"), setup = setup)]
#[bench::doc002(args = ("DOC002"), setup = setup)]
fn plan_executor((case, prepared): (Case, Prepared)) -> usize {
    black_box(run_plan(&case, &prepared).expect("plan runs").len())
}

// frob:waive DEAD001 reason="called by the gungraun main! macro, which the call graph cannot see"
#[library_benchmark]
#[bench::rust(fixture::rust_file(0, LINES))]
fn parse_rust(file: fixture::SourceFile) -> Prepared {
    black_box(prepare(&file, "rust").expect("fixture models"))
}

library_benchmark_group!(name = ic; benchmarks = plan_executor, parse_rust);

main!(library_benchmark_groups = ic);
