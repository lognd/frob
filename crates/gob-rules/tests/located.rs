//! A repo rule's located emissions: `fire_in` and `unresolved_in` carry the file, and
//! `into_located_finding` interns it as the span's file and the fingerprint anchor.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use gob_rules::{Applies, Emitted, FixKind, Out, Polarity, RuleDecl, RuleDef, Scope, Severity};
use gob_text::FileInterner;

struct Probe;

static DEF: RuleDef = RuleDef {
    id: "TST001",
    slug: "probe",
    family: "TST",
    severity: Severity::Warn,
    polarity: Polarity::Pplus,
    must_measure: false,
    scope: Scope::Repo,
    fix: FixKind::Manual,
    applies: Applies::Project,
    version: 1,
    since: "0.532.0",
    doc: "",
    file: "located.rs",
    line: 1,
};

impl RuleDecl for Probe {
    const DEF: &'static RuleDef = &DEF;
}

// frob:tests crates/gob-rules/src/decl.rs::Out
#[test]
fn located_emissions_carry_their_path_and_plain_ones_do_not() {
    let mut sink = Vec::new();
    let mut out = Out::<Probe>::new(&mut sink);
    out.fire_in("styles/a.css", 7, "here");
    out.unresolved_in("styles/b.css", 3, "maybe");
    out.note("somewhere");
    assert_eq!(sink[0].path.as_deref(), Some("styles/a.css"));
    assert_eq!(sink[0].offset, Some(7));
    assert!(!sink[0].unresolved);
    assert_eq!(sink[1].path.as_deref(), Some("styles/b.css"));
    assert!(sink[1].unresolved);
    assert_eq!(sink[2].path, None);
}

// frob:tests crates/gob-rules/src/decl.rs::Emitted
#[test]
fn a_located_emission_becomes_a_finding_in_its_file() {
    let mut files = FileInterner::new();
    let located = Emitted {
        rule: "TST001",
        offset: Some(7),
        path: Some("styles/a.css".to_owned()),
        message: "here".to_owned(),
        unresolved: false,
    };
    let finding = located.clone().into_located_finding(Probe::DEF, &mut files);
    let span = finding.span.expect("located");
    assert_eq!(span.file, files.intern("styles/a.css"));
    assert_eq!(span.range.start().to_usize(), 7);
    let spanless = Emitted {
        path: None,
        offset: None,
        ..located
    }
    .into_located_finding(Probe::DEF, &mut files);
    assert!(spanless.span.is_none());
    assert_eq!(spanless.severity, Severity::Warn);
}
