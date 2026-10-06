//! The `#[rule]` declaration and `FileRule<P: Host>` evaluation of the example `Todo001`
//! (~N88H9SY, D107).

#[path = "rule_attr/todo001.rs"]
mod todo001;

use gob_rules::caps::{Capability, Fidelity};
use gob_rules::{Applies, FileCx, FileRule, Out, Polarity, RuleDecl, Scope, Severity, run_file};
use todo001::Todo001;

/// The host trait the example rule evaluates against (stands in for `ObligationHost`).
pub trait ObligationHost {
    /// Byte offsets and text of every comment in `text`.
    fn comments<'t>(&self, text: &'t str) -> Vec<(usize, &'t str)>;
    /// True when the comment at `offset` is owned by a `frob:todo` directive.
    fn owned_by_todo(&self, text: &str, offset: usize) -> bool;
}

/// A line-comment host: `//` comments, owned when `frob:todo` follows on the line.
struct Demo;

impl ObligationHost for Demo {
    fn comments<'t>(&self, text: &'t str) -> Vec<(usize, &'t str)> {
        text.match_indices("//")
            .map(|(i, _)| (i, text[i..].lines().next().unwrap_or("")))
            .collect()
    }
    fn owned_by_todo(&self, text: &str, offset: usize) -> bool {
        text[offset..]
            .lines()
            .next()
            .is_some_and(|l| l.contains("frob:todo"))
    }
}

#[test]
fn def_carries_every_declared_field() {
    let d = Todo001::DEF;
    assert_eq!(
        (d.id, d.slug, d.family, d.version, d.since),
        ("TODO001", "bare-work-marker", "TODO", 1, "0.1.0")
    );
    assert_eq!(
        (d.severity, d.polarity, d.scope),
        (Severity::Error, Polarity::Pplus, Scope::File)
    );
    assert!(!d.must_measure);
    assert_eq!(
        d.applies,
        Applies::Universal {
            needs: &[Capability::Comments],
            min_fidelity: Fidelity::F1
        }
    );
}

#[test]
fn def_records_file_and_line() {
    let d = Todo001::DEF;
    assert!(d.file.ends_with("todo001.rs"), "file was {}", d.file);
    let src = std::fs::read_to_string(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/tests/rule_attr/todo001.rs"
    ))
    .expect("fixture exists");
    let attr_line = src
        .lines()
        .position(|l| l.starts_with("#[rule("))
        .expect("attribute present")
        + 1;
    assert_eq!(d.line as usize, attr_line);
}

#[test]
fn doc_is_the_colocated_page() {
    let md = std::fs::read_to_string(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/tests/rule_attr/todo001.md"
    ))
    .expect("page exists");
    assert_eq!(Todo001::DEF.doc, md);
}

#[test]
fn fires_on_bare_marker_and_stamps_its_id() {
    let found = run_file(&Todo001, &Demo, "// TODO fix\nfn f() {}\n");
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].rule, "TODO001");
}

#[test]
fn clean_when_owned_by_directive() {
    assert!(run_file(&Todo001, &Demo, "// TODO fix frob:todo 01ABC\n").is_empty());
}

#[test]
fn rule_evaluates_through_a_trait_object_host() {
    let dynhost: &dyn ObligationHost = &Demo;
    let mut found = Vec::new();
    FileRule::check(
        &Todo001,
        &FileCx {
            host: dynhost,
            text: "// TODO x",
        },
        &mut Out::new(&mut found),
    );
    assert_eq!(found.len(), 1);
}
