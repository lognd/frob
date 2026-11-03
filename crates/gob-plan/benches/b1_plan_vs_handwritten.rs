//! Benchmark B1 (docs/design/shared/packs-and-plugins.md section 6): the plan executor against handwritten Rust on
//! TODO001, COV001 and DOC002 over the 100k-line fixture.
//!
//! Findings are compared first; then each file is timed both ways and the median per-file ratio
//! of each rule is held to 1.3x. Exits non-zero when a ratio is over budget or findings differ.
#![allow(missing_docs, reason = "criterion macros generate undocumented items")]
#![allow(
    clippy::print_stdout,
    clippy::print_stderr,
    reason = "a benchmark binary reports its result table on stdout/stderr"
)]

mod b1;

use std::process::ExitCode;

use b1::{
    BenchError, Case, LIMIT, Prepared, cases, check_equal, fixture, gate, median, prepare, ratios,
    run_plan,
};
use criterion::Criterion;

const RUST_FILES: usize = 80;
const RUST_LINES: usize = 1000;
const MD_FILES: usize = 40;
const MD_LINES: usize = 500;
const REPS: u32 = 7;

fn prepared(files: &[fixture::SourceFile], lang: &str) -> Result<Vec<Prepared>, BenchError> {
    files.iter().map(|f| prepare(f, lang)).collect()
}

/// The prepared files a case runs over: markdown for DOC002, Rust otherwise.
fn files_of<'a>(c: &Case, rust: &'a [Prepared], md: &'a [Prepared]) -> &'a [Prepared] {
    if c.id == "DOC002" { md } else { rust }
}

/// Assert, per case, that the plan and handwritten checks find the same things.
fn assert_equal(cases: &[Case], rust: &[Prepared], md: &[Prepared]) -> Result<(), BenchError> {
    for case in cases {
        let found: usize = files_of(case, rust, md)
            .iter()
            .map(|p| check_equal(case, p))
            .sum::<Result<usize, _>>()?;
        println!("{}: findings equal ({found} total)", case.id);
    }
    Ok(())
}

/// Time the plan against the handwritten check for every case.
fn bench_cases(cases: &[Case], rust: &[Prepared], md: &[Prepared]) {
    let mut c = Criterion::default().sample_size(10).configure_from_args();
    for case in cases {
        let files = files_of(case, rust, md);
        let mut g = c.benchmark_group(format!("b1/{}", case.id));
        g.bench_function("plan", |b| {
            b.iter(|| {
                files
                    .iter()
                    .map(|p| run_plan(case, p).map(|f| f.len()))
                    .sum::<Result<usize, _>>()
            });
        });
        g.bench_function("handwritten", |b| {
            b.iter(|| files.iter().map(|p| (case.hand)(p).len()).sum::<usize>());
        });
        g.finish();
    }
    c.final_summary();
}

/// Gate each case's per-file plan/handwritten ratio against [`LIMIT`].
fn gate_ratios(cases: &[Case], rust: &[Prepared], md: &[Prepared]) -> Result<(), BenchError> {
    let mut over: Option<BenchError> = None;
    for case in cases {
        let r = ratios(case, files_of(case, rust, md), REPS)?;
        let (med, worst) = (median(&r), r.iter().copied().fold(0.0, f64::max));
        println!(
            "{}: per-file ratio median {med:.2}x worst {worst:.2}x (limit {LIMIT:.2}x)",
            case.id
        );
        if let Err(e) = gate(case.id, med, LIMIT) {
            over.get_or_insert(e);
        }
    }
    over.map_or(Ok(()), Err)
}

fn run() -> Result<(), BenchError> {
    let cases = cases()?;
    let (rust, md) = fixture::corpus(RUST_FILES, RUST_LINES, MD_FILES, MD_LINES);
    let lines: usize = rust.iter().chain(&md).map(|f| f.text.lines().count()).sum();
    let (rust, md) = (prepared(&rust, "rust")?, prepared(&md, "markdown")?);
    println!(
        "B1 fixture: {lines} lines in {} files",
        rust.len() + md.len()
    );
    assert_equal(&cases, &rust, &md)?;
    bench_cases(&cases, &rust, &md);
    gate_ratios(&cases, &rust, &md)
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("B1 failed: {e}");
            ExitCode::FAILURE
        }
    }
}
