//! Markdown corpus harness: fenced blocks as rule tests with positive controls.
//!
//! A markdown file is a suite; fenced blocks whose info string carries
//! `expect=fire|clean` are cases. See `FORMAT.md` in the crate root for the
//! full grammar; in brief:
//!
//! - info string: `lang rule=ID expect=fire|clean [config="toml"] [file=name]`
//! - suite default rule: `<!-- mdtest: rule=ID -->`
//! - markers `// error: ID`, `# warn: ID`, `<!-- error: ID -->` assert a
//!   finding on that exact line of the block.
//! - positive controls: each rule named in a file needs one fire and one
//!   clean block, else the file fails with [`MissingControl`].
//!
//! # The `mdtest!` macro
//!
//! `mdtest!(dir = "tests/mdtest", runner = my_fn)` expands to ONE `#[test]`
//! per invocation (named `mdtest_corpus` by default, or `name = ident`).
//! That test walks the directory at run time, prints one `ok`/`FAIL` line
//! per file in its panic message, and fails if any file fails. Chosen over
//! per-file tests because it needs no build script or compile-time
//! discovery; use several invocations (with `name`) for several corpora.
//!
//! ```ignore
//! fn my_runner(case: &gob_mdtest::Case) -> Vec<gob_rules::Finding> { vec![] }
//! gob_mdtest::mdtest!(dir = "tests/mdtest", runner = my_runner);
//! ```

mod parse;
mod run;

pub use parse::{Block, Expect, Marker, ParseError, parse_suite};
pub use run::{
    Case, CaseReport, FileReport, Missing, MissingControl, Report, Runner, run_dir, run_file,
};

/// Crate manifest directory: the run-time `CARGO_MANIFEST_DIR` cargo sets, else `compile_time`.
///
/// Shared target dirs reuse test binaries across worktrees, so the compile-time
/// value may name a removed checkout.
#[must_use]
pub fn manifest_dir(compile_time: &str) -> std::path::PathBuf {
    std::env::var_os("CARGO_MANIFEST_DIR").map_or_else(
        || std::path::PathBuf::from(compile_time),
        std::path::PathBuf::from,
    )
}

/// Generate a `#[test]` running every markdown file under `dir` (relative to the crate).
#[macro_export]
macro_rules! mdtest {
    (dir = $dir:expr, runner = $runner:expr $(,)?) => {
        $crate::mdtest!(name = mdtest_corpus, dir = $dir, runner = $runner);
    };
    (name = $name:ident, dir = $dir:expr, runner = $runner:expr $(,)?) => {
        #[test]
        fn $name() {
            let dir = $crate::manifest_dir(env!("CARGO_MANIFEST_DIR")).join($dir);
            let report = $crate::run_dir(&dir, &$crate::Runner::new($runner));
            assert!(
                !report.files.is_empty(),
                "no markdown files under {}",
                dir.display()
            );
            assert!(
                report.passed(),
                "mdtest corpus failed:\n{}",
                report.render()
            );
        }
    };
}
