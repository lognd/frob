//! A repo rule's located emissions: `fire_in` and `unresolved_in` carry the file, and
//! `into_located_finding` interns it as the span's file and the fingerprint anchor.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use gob_rules::{
    Applies, Emitted, FileCx, FileRule, Finding, FixKind, Out, Polarity, RelayRule, RepoRule,
    RuleDecl, RuleDef, Scope, Severity,
};
use gob_text::FileInterner;

struct Probe;

static DEF: RuleDef = RuleDef {
    id: "TST001",
    slug: "probe",
    family: "TST",
    severity: Severity::Error,
    gates: None,
    nature: gob_rules::Nature::Exact,
    polarity: Polarity::Pplus,
    must_measure: false,
    needs: gob_rules::Needs::Structural,
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
        end: None,
        path: Some("styles/a.css".to_owned()),
        message: "here".to_owned(),
        unresolved: false,
        fix: None,
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
    assert_eq!(spanless.severity, Severity::Error);
}

// frob:tests crates/gob-rules/src/decl.rs::Out
#[test]
fn range_emissions_keep_their_end_and_anchor_a_ranged_span() {
    let mut files = FileInterner::new();
    let mut sink = Vec::new();
    let mut out = Out::<Probe>::new(&mut sink);
    out.fire_range_in("a.md", 4, 9, "span");
    out.unresolved_range(2, 5, "maybe");
    assert_eq!(sink[0].end, Some(9));
    assert!(sink[1].unresolved);
    let finding = sink.remove(0).into_located_finding(Probe::DEF, &mut files);
    let range = finding.span.expect("located").range;
    assert_eq!((range.start().to_usize(), range.end().to_usize()), (4, 9));
}

struct Filey;

impl RuleDecl for Filey {
    const DEF: &'static RuleDef = &DEF;
}

impl FileRule<()> for Filey {
    fn check(&self, _cx: &FileCx<'_, ()>, _out: &mut Out<'_, Self>) {}
}

impl RepoRule<()> for Probe {
    fn check(&self, _host: &(), _out: &mut Out<'_, Self>) {}
}

struct Relay;

impl RuleDecl for Relay {
    const DEF: &'static RuleDef = &DEF;
}

impl RelayRule<()> for Relay {
    fn relay(&self, _host: &(), _files: &mut FileInterner) -> Vec<Finding> {
        Vec::new()
    }
}

// frob:tests crates/gob-rules/src/decl.rs::Out.fire_range
// frob:tests crates/gob-rules/src/decl.rs::Out.unresolved
// frob:tests crates/gob-rules/src/decl.rs::Out.unresolved_range_in
#[test]
fn every_emission_form_records_its_location_and_unresolved_flag() {
    let mut sink = Vec::new();
    let mut out = Out::<Probe>::new(&mut sink);
    out.fire_range(1, 4, "ranged");
    out.unresolved("cannot decide");
    out.unresolved_range_in("a.md", 2, 6, "maybe ranged");
    assert_eq!(
        (sink[0].offset, sink[0].end, sink[0].unresolved),
        (Some(1), Some(4), false)
    );
    assert_eq!(
        (sink[1].offset, sink[1].path.as_deref(), sink[1].unresolved),
        (None, None, true)
    );
    assert_eq!(sink[2].path.as_deref(), Some("a.md"));
    assert_eq!(
        (sink[2].offset, sink[2].end, sink[2].unresolved),
        (Some(2), Some(6), true)
    );
}

// frob:tests crates/gob-rules/src/decl.rs::FileRule.inapplicable
// frob:tests crates/gob-rules/src/decl.rs::FileRule.side_input
// frob:tests crates/gob-rules/src/decl.rs::FileRule.side_input_needs_text
// frob:tests crates/gob-rules/src/decl.rs::RepoRule.inapplicable
// frob:tests crates/gob-rules/src/decl.rs::RepoRule.examined
// frob:tests crates/gob-rules/src/decl.rs::RelayRule.inapplicable
// frob:tests crates/gob-rules/src/decl.rs::RelayRule.examined
#[test]
fn rule_trait_defaults_apply_everywhere_and_measure_nothing() {
    assert_eq!(FileRule::<()>::inapplicable(&Filey, &()), None);
    assert_eq!(FileRule::<()>::side_input(&Filey, &(), "a.md", "text"), "");
    assert!(!FileRule::<()>::side_input_needs_text(&Filey));
    assert_eq!(RepoRule::<()>::inapplicable(&Probe, &()), None);
    assert_eq!(RepoRule::<()>::examined(&Probe, &()), None);
    assert_eq!(RelayRule::<()>::inapplicable(&Relay, &()), None);
    assert_eq!(RelayRule::<()>::examined(&Relay, &()), None);
}

// frob:tests crates/gob-rules/src/index.rs::BoundRule.file
#[test]
fn binding_a_file_rule_keeps_its_declaration() {
    let bound = gob_rules::BoundRule::<()>::file(Filey);
    assert_eq!(bound.def.id, DEF.id);
}
