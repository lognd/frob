//! Benchmark B2 (plugins.md section 6.6): a rule compiled in against the same rule as a cached
//! disk plan, over the 100k-line fixture.
//!
//! The two runs' JSON findings are compared first; then each rule is timed both ways with the
//! plan cache warm and the disk-over-compiled ratio is held to 1.3x. Exits non-zero when a ratio
//! is over budget or the JSON differs.
#![allow(missing_docs, reason = "bench harness")]
#![allow(
    clippy::print_stdout,
    clippy::print_stderr,
    reason = "a benchmark binary reports its results on stdout/stderr"
)]

mod b2;

use std::process::ExitCode;

use b2::{
    BenchError, LIMIT, cases, compiled_plan, disk_plan, findings_json, fixture, gate, pair,
    prepare, ratio,
};

const RUST_FILES: usize = 80;
const RUST_LINES: usize = 1000;
const MD_FILES: usize = 40;
const MD_LINES: usize = 500;
const REPS: u32 = 9;

fn run() -> Result<(), BenchError> {
    let cases = cases()?;
    let (rust, md) = fixture::corpus(RUST_FILES, RUST_LINES, MD_FILES, MD_LINES);
    let mut over: Option<BenchError> = None;
    for case in &cases {
        let (files, lang) = if case.id == "DOC002" {
            (&md, "markdown")
        } else {
            (&rust, "rust")
        };
        let prepared = files
            .iter()
            .map(|f| prepare(f, lang))
            .collect::<Result<Vec<_>, _>>()?;
        let p = pair(case)?;
        let compiled = findings_json(case, &compiled_plan(&p)?, &prepared)?;
        let disk = findings_json(case, &disk_plan(&p)?, &prepared)?;
        if compiled != disk {
            return Err(BenchError::Rule(
                case.id,
                "disk and compiled-in JSON differ".into(),
            ));
        }
        println!(
            "{}: JSON identical ({} bytes)",
            case.id,
            compiled.to_string().len()
        );
        let r = ratio(case, &p, &prepared, REPS);
        println!(
            "{}: disk/compiled-in ratio {r:.3}x (limit {LIMIT:.2}x)",
            case.id
        );
        if let Err(e) = gate(case.id, r, LIMIT) {
            over.get_or_insert(e);
        }
    }
    over.map_or(Ok(()), Err)
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("B2 failed: {e}");
            ExitCode::FAILURE
        }
    }
}
