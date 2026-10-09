//! `frob:describes` in markdown: parsed, bound to the enclosing section, no DSL001.

mod common;

use gob_directives::frob::Describes;
use gob_directives::{Binding, Directive};

// frob:tests crates/gob-directives/src/frob.rs::Describes
#[test]
fn describes_parses_in_markdown_and_binds_to_the_enclosing_heading() {
    let text = "# Guide\n\n<!-- frob:describes src/x.py::Sym -->\nBody.\n";
    let r = common::scan("docs/g.md", text);
    assert!(r.findings.is_empty(), "{:?}", r.findings);
    assert_eq!(r.directives.len(), 1);
    let d = &r.directives[0];
    assert_eq!(
        (d.namespace.as_str(), d.verb.as_str()),
        ("frob", "describes")
    );
    let parsed = Describes::parse_args(&d.args).expect("well formed");
    assert_eq!(parsed.symbol.0.to_string(), "src/x.py::Sym");
    assert_eq!(d.bound, Binding::Symbol("docs/g.md#guide".parse().unwrap()));
}

// frob:tests crates/gob-directives/src/frob.rs::Describes
#[test]
fn describes_rejects_an_anchor_argument() {
    let r = common::scan("docs/g.md", "<!-- frob:describes docs/a.md#h -->\n");
    assert_eq!(r.findings.len(), 1, "{:?}", r.findings);
}
