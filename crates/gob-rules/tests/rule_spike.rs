//! Spike (~9R52NCF): the `#[rule]` declaration and `FileRule<P: Host>` evaluation of `Todo001`.

use gob_rules::rule_spike::caps::{Capability, Fidelity};
use gob_rules::rule_spike::{
    Applies, FileCx, FileRule, Out, Polarity, Rule, Scope, Severity, Todo001, run_file,
    todo001_demo_host,
};

#[test]
fn def_carries_every_declared_field() {
    let d = Todo001::DEF;
    assert_eq!(
        (d.id, d.slug, d.version, d.since),
        ("TODO001", "bare-work-marker", 1, "0.1.0")
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
fn doc_is_the_colocated_page() {
    let md = std::fs::read_to_string(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/src/rule_spike/todo001.md"
    ))
    .expect("page exists");
    assert_eq!(Todo001::DEF.doc, md);
}

#[test]
fn fires_on_bare_marker_and_stamps_its_id() {
    let host = todo001_demo_host();
    let found = run_file(&Todo001, &host, "// TODO fix\nfn f() {}\n");
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].rule, "TODO001");
}

#[test]
fn clean_when_owned_by_directive() {
    let host = todo001_demo_host();
    assert!(run_file(&Todo001, &host, "// TODO fix frob:todo 01ABC\n").is_empty());
}

#[test]
fn rule_evaluates_through_a_trait_object_host() {
    let host = todo001_demo_host();
    let dynhost: &dyn gob_rules::rule_spike::ObligationHost = &host;
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
