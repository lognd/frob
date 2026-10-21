//! Example `model` inputs: the `node` and `cell` kinds and the `owned by` relation, backed by the
//! model an example declares (grl-spec.md section 6).

// frob:ticket 01M5ETB7SWJPH7EVK97WHEVEHY

use gob_plan::examples::{RunError, install_model_reader, run_example};
use gob_plan::grl::parse;
use gob_text::FileInterner;

/// A rule whose cells are the unexcused, ungranted uses of an atom.
const CELLS: &str = r#"rule CEL001 "cells" {
  lang *
  polarity P+  severity error  scope repo  rollup file
  needs model

  find c: cell where c.observed and not c.granted and not c.excused
  report c "uses {c.atom} without a grant"
  example fire rust {
    model """node n { owns "src/**"; }"""
    file "src/a.rs" """
      fn a() {}
      fn serve() { std::net::TcpListener::bind("0.0.0.0:0"); }   //~ error
    """
  }
  example clean rust {
    model """node n { owns "src/**"; may net.listen; }"""
    file "src/a.rs" """
      fn serve() { std::net::TcpListener::bind("0.0.0.0:0"); }
    """
  }
  example clean rust {
    model """node n { owns "src/**"; may net; }"""
    file "src/a.rs" """
      fn serve() { std::net::TcpListener::bind("0.0.0.0:0"); }
    """
  }
  example clean rust {
    model """node n { owns "src/**"; excuses net.listen because="legacy"; }"""
    file "src/a.rs" """
      fn serve() { std::net::TcpListener::bind("0.0.0.0:0"); }
    """
  }
  example clean rust {
    model """node n { owns "docs/**"; }"""
    file "src/a.rs" """
      fn serve() { std::net::TcpListener::bind("0.0.0.0:0"); }
    """
  }
  example clean rust {
    model """node n { owns "src/**"; }"""
    file "src/a.rs" """
      fn quiet() {}
    """
  }
  explain """
    Test rule.
    ## Remedy
    None.
  """
}
"#;

/// An unowned-file rule over the `node` kind and `owned by`.
const OWNED: &str = r#"rule OWN001 "unowned" {
  lang *
  polarity P-  severity warn  scope repo  rollup directory
  needs model

  find a: artifact
  where some u: unit where u inside a and some n: node where u owned by n
  report a "no node owns any part of {a.path}"
  example fire python {
    model """node app { owns "src/app/**"; }"""
    file "scripts/legacy.py" """
      def f(): pass                  #~ warn
    """
  }
  example clean python {
    model """node app { owns "src/app/**"; }"""
    file "src/app/a.py" """
      def f(): pass
    """
  }
  example fire python {
    model """node app { }"""
    file "src/app/a.py" """
      def f(): pass                  #~ warn
    """
  }
  example clean python {
    model """node a { owns "lib/**"; } node b { owns "src/**"; }"""
    file "src/app/a.py" """
      def f(): pass
    """
  }
  example clean python {
    model """node app { owns "[s]rc/**"; }"""
    file "src/a.py" """
      def f(): pass
    """
  }
  example fire python {
    model """node app { owns "src/app/**"; }"""
    file "src/app.py" """
      def f(): pass                  #~ warn
    """
  }
  example fire python {
    model """node app { owns "src/app"; }"""
    file "src/a.py" """
      def f(): pass                  #~ warn
    """
  }
  example clean python {
    model """node app { owns "src/**"; }"""
    file "src/a/b/c.py" """
      def f(): pass
    """
  }
  explain """
    Test rule.
    ## Remedy
    None.
  """
}
"#;

fn results(src: &str) -> Vec<Result<bool, RunError>> {
    install_model_reader(grimble_check::example_model::read_example_model);
    let parsed = parse(FileInterner::new().intern("rules/T.grl"), src);
    assert!(parsed.is_ok(), "{:?}", parsed.errors);
    let rule = &parsed.file.rules[0];
    rule.examples
        .iter()
        .map(|e| run_example(rule, e).map(|r| r.passed))
        .collect()
}

fn all_pass(src: &str) {
    for (i, r) in results(src).into_iter().enumerate() {
        assert!(matches!(r, Ok(true)), "example {i}: {r:?}");
    }
}

// frob:tests crates/gob-plan/src/examples/cells.rs::cell_table
#[test]
fn cells_fire_for_ungranted_atoms_and_clear_when_granted_covered_excused_or_unowned() {
    all_pass(CELLS);
}

// frob:tests crates/gob-plan/src/examples/side.rs::add_cells
#[test]
fn a_cell_rule_with_no_model_input_is_refused_not_silently_clean() {
    let src = CELLS.replace(
        "model \"\"\"node n { owns \"src/**\"; }\"\"\"\n    file \"src/a.rs\" \"\"\"\n      fn a() {}",
        "file \"src/a.rs\" \"\"\"\n      fn a() {}",
    );
    let first = results(&src).remove(0);
    assert!(first.is_err(), "{first:?}");
}

// frob:tests crates/gob-plan/src/examples/side.rs::side_data
#[test]
fn node_and_owned_by_follow_the_model_selectors() {
    all_pass(OWNED);
}

// frob:tests crates/gob-plan/src/examples/side.rs::model_tables
#[test]
fn an_unparsable_model_is_a_model_error() {
    let src = OWNED.replace(
        "model \"\"\"node app { owns \"src/app/**\"; }\"\"\"",
        "model \"\"\"node {{{\"\"\"",
    );
    let first = results(&src).remove(0);
    assert!(matches!(first, Err(RunError::Model(_))), "{first:?}");
}

// frob:tests crates/gob-plan/src/exec/core/rowkind.rs::owners
#[test]
fn an_unreadable_owns_glob_is_a_refusal_not_a_match() {
    let src = OWNED.replace(
        "model \"\"\"node app { owns \"src/app/**\"; }\"\"\"",
        "model \"\"\"node app { owns \"src/[\"; }\"\"\"",
    );
    let first = results(&src).remove(0);
    assert!(first.is_err(), "{first:?}");
}
