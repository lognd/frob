//! Instruction-count benchmarks (gungraun, Valgrind callgrind) of the full check on a small fixture
//! repository, cold (no derived cache) and warm (cache filled by a prior run), compared against the
//! base by `cargo dev bench-ic` on pull requests. The real-repository timing stays in `full_check`.
// frob:ticket 01M5FA5EHT4NSJZP7JVFCZTVFB
#![allow(missing_docs, reason = "gungraun macros generate undocumented items")]

use std::hint::black_box;
use std::path::Path;

use frob_check::{CheckOptions, run};
use gungraun::{library_benchmark, library_benchmark_group, main};

/// Number of source files in the fixture; small so a run stays fast and deterministic.
const FILES: usize = 6;

/// Options that keep the run hermetic: no telemetry, no external tool stages.
fn options() -> CheckOptions {
    CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    }
}

/// Writes the fixture repository under `root`.
fn write_fixture(root: &Path) {
    std::fs::write(root.join("frob.toml"), "[tickets]\n").expect("write frob.toml");
    for i in 0..FILES {
        let text = format!("/// Doc {i}.\npub fn item_{i}(x: u32) -> u32 {{\n    x + {i}\n}}\n");
        std::fs::write(root.join(format!("mod_{i}.rs")), text).expect("write source");
    }
}

/// A fixture repository with no cache, outside the measured region.
fn ic_cold() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    write_fixture(dir.path());
    dir
}

/// A fixture repository whose cache a prior run has filled, outside the measured region.
fn ic_warm() -> tempfile::TempDir {
    let dir = ic_cold();
    run(dir.path(), &options()).expect("priming run");
    dir
}

#[library_benchmark]
#[bench::cold(setup = ic_cold)]
fn check_cold(dir: tempfile::TempDir) -> usize {
    black_box(
        run(dir.path(), &options())
            .expect("cold run")
            .findings
            .len(),
    )
}

#[library_benchmark]
#[bench::warm(setup = ic_warm)]
fn check_warm(dir: tempfile::TempDir) -> usize {
    black_box(
        run(dir.path(), &options())
            .expect("warm run")
            .findings
            .len(),
    )
}

library_benchmark_group!(name = ic; benchmarks = check_cold, check_warm);

main!(library_benchmark_groups = ic);
