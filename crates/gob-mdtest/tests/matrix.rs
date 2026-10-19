//! The language matrix: derived expectations, contradiction, completeness, parity.

// frob:ticket 01M48Q4DMNMQEYQNWPK42DZ0RZ

use gob_mdtest::coverage::Allowlist;
use gob_mdtest::matrix::{Derived, MatrixGap, analyze_matrix};
use gob_mdtest::parse_suite;

/// A fake derivation: opaque text is `Unresolved`, binary is `NotApplicable`, the rest `Examine`.
#[allow(clippy::unnecessary_wraps)] // the Deriver signature returns Option
fn derive(_rule: &str, cell: &str) -> Option<Derived> {
    Some(match cell {
        "text" => Derived::Unresolved,
        "binary" => Derived::NotApplicable,
        _ => Derived::Examine,
    })
}

fn suite(body: &str) -> Vec<gob_mdtest::Block> {
    parse_suite(&format!("<!-- mdtest: rule=TODO001 -->\n{body}")).expect("suite parses")
}

fn block(cell: &str, expect: &str, extra: &str) -> String {
    format!("```rust expect={expect} cell={cell} {extra}\nfn a() {{}}\n```\n")
}

fn full() -> String {
    [
        "rust",
        "python",
        "typescript",
        "csharp",
        "markdown",
        "island",
    ]
    .iter()
    .map(|c| block(c, "clean", ""))
    .chain([
        block("text", "unresolved", ""),
        block("binary", "notapplicable", ""),
    ])
    .collect()
}

fn gap(cell: &str, ticket: &str) -> MatrixGap {
    MatrixGap {
        product: "frob".into(),
        rule: "TODO001".into(),
        cell: cell.into(),
        ticket: ticket.into(),
    }
}

fn run(body: &str, gaps: Vec<MatrixGap>) -> gob_mdtest::matrix::MatrixReport {
    let list = Allowlist {
        gap: vec![],
        matrix_gap: gaps,
    };
    analyze_matrix(
        "frob",
        &["TODO001".to_owned()],
        &suite(body),
        &derive,
        &list,
    )
}

// frob:tests crates/gob-mdtest/src/matrix.rs::analyze_matrix
#[test]
fn a_complete_matrix_passes() {
    let r = run(&full(), vec![]);
    assert!(r.passed(), "{}", r.render());
}

// frob:tests crates/gob-mdtest/src/matrix.rs::analyze_matrix
// frob:tests crates/gob-mdtest/src/matrix.rs::Derived.admits
#[test]
fn a_hand_written_expectation_contradicting_the_derived_one_fails() {
    let body = full().replace("expect=unresolved cell=text", "expect=clean cell=text");
    let r = run(&body, vec![]);
    assert_eq!(r.contradictions.len(), 1, "{}", r.render());
    assert!(r.contradictions[0].contains("cell=text"));
}

// frob:tests crates/gob-mdtest/src/matrix.rs::analyze_matrix
#[test]
fn a_missing_cell_fails_unless_allowlisted_with_a_ticket() {
    let body = full().replace("cell=csharp", "cell=rust");
    let r = run(&body, vec![]);
    assert_eq!(r.missing, vec![("TODO001".to_owned(), "csharp".to_owned())]);
    assert!(
        r.render().contains("TODO001: no `cell=csharp` block"),
        "{}",
        r.render()
    );
    let r = run(&body, vec![gap("csharp", "~ABCDEFG")]);
    assert!(r.passed(), "{}", r.render());
    let r = run(&body, vec![gap("csharp", "soon")]);
    assert_eq!(r.bad_ticket.len(), 1);
}

// frob:tests crates/gob-mdtest/src/matrix.rs::analyze_matrix
#[test]
fn an_allowlist_entry_for_a_filled_cell_is_stale() {
    let r = run(&full(), vec![gap("rust", "~ABCDEFG")]);
    assert_eq!(r.stale, vec!["TODO001 cell=rust".to_owned()]);
}

// frob:tests crates/gob-mdtest/src/matrix.rs::analyze_matrix
#[test]
fn parity_groups_must_agree_across_examined_cells() {
    let body = full()
        .replace("expect=clean cell=rust ", "expect=fire cell=rust parity=p")
        .replace(
            "expect=clean cell=python ",
            "expect=clean cell=python parity=p",
        );
    let r = run(&body, vec![]);
    assert_eq!(r.parity.len(), 1, "{}", r.render());
}

// frob:tests crates/gob-mdtest/src/parse.rs::parse_suite
#[test]
fn an_unknown_cell_is_a_parse_error() {
    let e = parse_suite(&format!(
        "<!-- mdtest: rule=TODO001 -->\n{}",
        block("cobol", "clean", "")
    ))
    .expect_err("unknown cell");
    assert!(e.message.contains("cell must be one of"));
}
