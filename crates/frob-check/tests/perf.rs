//! The check's timing and cache contract, on a small fixture repository.
//!
//! Function lives here, performance lives in the `full_check` bench: this test asserts that
//! stages are timed and that a second run hits the cache, on a fixture that checks in well under
//! a second. The cold and warm wall time of this whole repository (the 2 s warm budget of
//! architecture.md section 9, and `PERF001` under `[perf] enforce`) is measured by the
//! `full_check` bench in release, where a regression fails with a number instead of a slow test.

use std::path::Path;

use frob_check::{CheckOptions, run};

fn write(root: &Path, path: &str, text: &str) {
    let full = root.join(path);
    std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
    std::fs::write(full, text).expect("write");
}

/// A repository tree with a few source and doc files, enough to exercise every timed stage.
fn fixture() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    for i in 0..8 {
        write(
            dir.path(),
            &format!("src/m{i}.rs"),
            &format!("//! Module {i}.\n\n/// Item {i}.\npub fn item_{i}() -> u32 {{ {i} }}\n"),
        );
    }
    write(
        dir.path(),
        "README.md",
        "# Fixture\n\nSee [the code](src/m0.rs).\n",
    );
    dir
}

// frob:ticket 01M3ZFT5KZBX5H4FBJTCX0T4TP
// frob:ticket 01M41ZSW6DZMBE5QWNGB6VY10G
#[test]
fn warm_run_on_a_fixture_times_its_stages_and_hits_the_cache() {
    let dir = fixture();
    let opts = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    let started = std::time::Instant::now();
    let cold = run(dir.path(), &opts).expect("cold run populates the cache");
    assert_eq!(cold.stats.cached_hits(), 0, "a cold run has nothing cached");
    let warm = run(dir.path(), &opts).expect("warm run");
    eprintln!("cold and warm fixture runs took {:?}", started.elapsed());
    for s in &warm.timing.stages {
        eprintln!("stage {:<18} {:>6} ms", s.name, s.ms);
    }
    assert!(!warm.timing.stages.is_empty(), "stages are timed");
    assert!(warm.stats.cached_hits() > 0, "warm run uses the cache");
}
