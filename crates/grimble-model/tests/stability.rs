//! Printer stability harness (build-test-ci.md section 6, D98): a printer must be a fixed point
//! and must preserve U, and a deliberately broken printer must fail with a shrunk example.

// frob:ticket 01M47QTX4X7FHCMZQE42JVWF8Y

use std::fmt::Write as _;

use grimble_model::dump::u_signature;
use grimble_model::fmt::format_file;
use grimble_model::fold::fold_file;
use grimble_model::parse::parse_file;
use proptest::prelude::*;
use proptest::test_runner::{Config, TestError, TestRunner};

/// A source with `n` nodes, the smallest model family that still varies in size.
fn source(n: usize) -> String {
    let mut nodes = String::new();
    for i in 0..n {
        let _ = writeln!(nodes, "node n{i} : trusted {{ kind component; }}");
    }
    format!("grimble = \"2\";\nmodule m;\n{nodes}")
}

/// Why a printer is unstable on `src`, or `None` when it is a fixed point preserving U.
fn instability(print: &dyn Fn(&str) -> String, src: &str) -> Option<String> {
    let once = print(src);
    let twice = print(&once);
    if once != twice {
        return Some(format!("print(print(x)) != print(x) for {src:?}"));
    }
    let sig =
        |t: &str| u_signature(&fold_file(&parse_file("s.grmb", t.as_bytes()), "").expect("fold"));
    (sig(src) != sig(&once)).then(|| format!("print changed U for {src:?}"))
}

/// The real `grimble fmt`.
fn real(src: &str) -> String {
    format_file(&parse_file("s.grmb", src.as_bytes())).expect("formats")
}

/// A broken printer: every pass appends one more comment line, so it never reaches a fixed point.
fn broken(src: &str) -> String {
    format!("{}// again\n", real(src))
}

// frob:tests grimble_model::fmt::format_file
#[test]
fn the_real_formatter_is_stable_over_generated_sizes() {
    let mut runner = TestRunner::new(Config::with_cases(64));
    let result = runner.run(&(1usize..8), |n| {
        let src = source(n);
        prop_assert_eq!(instability(&real, &src), None);
        Ok(())
    });
    assert!(result.is_ok(), "{result:?}");
}

// frob:tests grimble_model::fmt::format_file
#[test]
fn a_broken_printer_fails_with_a_shrunk_minimal_example() {
    let mut runner = TestRunner::new(Config::with_cases(64));
    let result = runner.run(&(1usize..8), |n| {
        let src = source(n);
        prop_assert_eq!(instability(&broken, &src), None);
        Ok(())
    });
    match result {
        Err(TestError::Fail(_, minimal)) => {
            assert_eq!(
                minimal, 1,
                "proptest shrinks the failure to the smallest model"
            );
        }
        other => panic!("the broken printer must fail the property, got {other:?}"),
    }
}
