//! Snapshot and contract tests for gob-diagnostics.
#![allow(missing_docs)]

use gob_diagnostics::{
    ColorChoice, Envelope, ExitCode, FindingRecord, MemorySources, Refusal, RefusalClass, Report,
    RequiredMarks, RequiredReason, TextOptions, UnresolvedPolicy, envelope_schema, fail_on,
    render_json, render_text, render_text_marked,
};
use gob_rules::{Finding, Fix, FixKind, Registry, Severity};
use gob_text::{FileId, FileInterner, SourceText, Span, TextRange};

struct Fixture {
    sources: MemorySources,
    findings: Vec<Finding>,
}

fn range(a: u32, b: u32) -> TextRange {
    TextRange::new(a.into(), b.into())
}

fn fixture() -> Fixture {
    let mut files = FileInterner::new();
    let a: FileId = files.intern("src/a.rs");
    let b: FileId = files.intern("src/b.rs");
    let mut sources = MemorySources::new();
    sources.insert(
        a,
        "src/a.rs",
        SourceText::new("fn main() {\n    bad_call();\n}\n").unwrap(),
    );
    sources.insert(b, "src/b.rs", SourceText::new("let x = 1;\n").unwrap());
    let r = |s: &str| s.parse().unwrap();
    let findings = vec![
        Finding::new(
            r("COV006"),
            Severity::Warn,
            Some(Span::new(b, range(4, 5))),
            "unused x",
            "src/b.rs",
        ),
        Finding::new(
            r("DOC001"),
            Severity::Error,
            Some(Span::new(a, range(16, 24))),
            "bad call",
            "src/a.rs",
        )
        .with_fix(Fix {
            kind: FixKind::Manual,
            title: "remove call".into(),
            edits: vec![],
        }),
        Finding::new(
            r("DOC002"),
            Severity::Advisory,
            Some(Span::new(a, range(0, 2))),
            "style note",
            "src/a.rs",
        ),
        Finding::new(
            r("TOOL001"),
            Severity::Unresolved,
            None,
            "tool missing",
            "repo",
        ),
    ];
    Fixture { sources, findings }
}

fn records(fx: &Fixture) -> Vec<FindingRecord> {
    fx.findings
        .iter()
        .map(|f| FindingRecord::from_finding(f, &fx.sources, Registry::global()))
        .collect()
}

#[test]
fn text_plain_snapshot() {
    let fx = fixture();
    let report = Report {
        findings: &fx.findings,
        sources: &fx.sources,
    };
    let out = render_text(
        &report,
        &TextOptions {
            color: ColorChoice::Never,
            snippets: true,
        },
    );
    insta::assert_snapshot!(out);
}

#[test]
fn text_color_snapshot() {
    let fx = fixture();
    let report = Report {
        findings: &fx.findings,
        sources: &fx.sources,
    };
    let out = render_text(
        &report,
        &TextOptions {
            color: ColorChoice::Always,
            snippets: false,
        },
    );
    assert!(out.contains('\u{1b}'));
    insta::assert_snapshot!(out.replace('\u{1b}', "<ESC>"));
}

#[test]
fn json_success_snapshot() {
    let fx = fixture();
    let env = Envelope::success(serde_json::json!({"n": 4}), records(&fx));
    let out = render_json(&env);
    assert!(out.ends_with('\n'));
    assert!(out.contains("\"schema_version\":1"));
    insta::assert_snapshot!(out);
}

#[test]
fn json_refusal_snapshot() {
    let r = Refusal::new(
        "E-LEASE-HELD",
        RefusalClass::GuardRetryByWaiting,
        "held by bot",
    )
    .with_remedy("frob ticket start T-1 --wait 60");
    let env: Envelope<()> = Envelope::failure((&r).into());
    insta::assert_snapshot!(render_json(&env));
    assert_eq!(r.to_string(), "E-LEASE-HELD: held by bot");
}

#[test]
fn fail_on_threshold() {
    let fx = fixture();
    let none = RequiredMarks::new();
    let gate = |f: &[Finding], t: Severity| fail_on(f, Some(t), UnresolvedPolicy::Required, &none);
    assert_eq!(gate(&fx.findings, Severity::Error), ExitCode::Negative);
    assert_eq!(gate(&fx.findings[..1], Severity::Error), ExitCode::Ok);
    assert_eq!(gate(&fx.findings[..1], Severity::Warn), ExitCode::Negative);
    assert_eq!(gate(&[], Severity::Advisory), ExitCode::Ok);
    // Unresolved never fails through the severity threshold.
    assert_eq!(gate(&fx.findings[3..], Severity::Unresolved), ExitCode::Ok);
}

fn reasons() -> Vec<RequiredReason> {
    vec![
        RequiredReason::SiblingMissing {
            product: "crunk".into(),
        },
        RequiredReason::AnnotationRequired {
            code: "opaque-fn".into(),
            public_surface: true,
        },
        RequiredReason::ZeroSubjects {
            rule: "COV001".into(),
        },
    ]
}

#[test]
fn unresolved_policy_matrix() {
    let fx = fixture();
    let unresolved = &fx.findings[3..];
    let unmarked = RequiredMarks::new();
    for reason in reasons() {
        let mut marked = RequiredMarks::new();
        marked.insert(&unresolved[0], reason.clone());
        for (policy, with_mark, without) in [
            (UnresolvedPolicy::Required, ExitCode::Negative, ExitCode::Ok),
            (UnresolvedPolicy::Never, ExitCode::Ok, ExitCode::Ok),
            (
                UnresolvedPolicy::All,
                ExitCode::Negative,
                ExitCode::Negative,
            ),
        ] {
            assert_eq!(
                fail_on(unresolved, None, policy, &marked),
                with_mark,
                "{policy:?} {reason}"
            );
            assert_eq!(
                fail_on(unresolved, None, policy, &unmarked),
                without,
                "{policy:?} unmarked"
            );
        }
    }
}

#[test]
fn unresolved_policy_composes_with_the_threshold() {
    let fx = fixture();
    let none = RequiredMarks::new();
    // An Error fails even under `never`; the threshold disabled and a pass otherwise.
    assert_eq!(
        fail_on(
            &fx.findings,
            Some(Severity::Error),
            UnresolvedPolicy::Never,
            &none
        ),
        ExitCode::Negative
    );
    assert_eq!(
        fail_on(&fx.findings[..3], None, UnresolvedPolicy::All, &none),
        ExitCode::Ok
    );
    // A mark on a non-Unresolved finding does not matter.
    let mut marks = RequiredMarks::new();
    marks.insert(&fx.findings[0], reasons().remove(0));
    assert_eq!(
        fail_on(&fx.findings[..1], None, UnresolvedPolicy::Required, &marks),
        ExitCode::Ok
    );
}

#[test]
fn required_reason_serializes_tagged_and_summary_counts_required() {
    let fx = fixture();
    let reason = RequiredReason::SiblingMissing {
        product: "crunk".into(),
    };
    let rec = FindingRecord::from_finding(&fx.findings[3], &fx.sources, Registry::global())
        .with_required(Some(reason.clone()));
    let json = serde_json::to_value(&rec).unwrap();
    assert_eq!(
        json["required"],
        serde_json::json!({"kind": "sibling_missing", "product": "crunk"})
    );
    let mut marks = RequiredMarks::new();
    marks.insert(&fx.findings[3], reason);
    let report = Report {
        findings: &fx.findings,
        sources: &fx.sources,
    };
    let opts = TextOptions {
        color: ColorChoice::Never,
        snippets: false,
    };
    let out = render_text_marked(&report, &opts, &marks);
    assert!(out.contains("required: sibling-missing: crunk"), "{out}");
    assert!(out.contains("1 unresolved (1 required)"), "{out}");
    assert!(render_text(&report, &opts).contains("1 unresolved (0 required)"));
}

#[test]
fn exit_code_table() {
    let table = [
        (RefusalClass::DomainNegative, 1, false),
        (RefusalClass::UsageError, 2, false),
        (RefusalClass::GuardRetryByWaiting, 3, true),
        (RefusalClass::GuardNeedsAction, 3, false),
        (RefusalClass::Timeout, 3, true),
        (RefusalClass::Internal, 4, false),
    ];
    assert_eq!(table.len(), RefusalClass::ALL.len());
    for (class, code, retry) in table {
        assert_eq!(i32::from(class.exit_code()), code, "{class:?}");
        assert_eq!(class.retryable(), retry, "{class:?}");
        assert!(!class.doc().is_empty());
        let r = Refusal::new("E-X", class, "m");
        assert_eq!(r.exit_code(), class.exit_code());
        assert_eq!(gob_diagnostics::EnvelopeError::from(&r).retryable, retry);
    }
    assert_eq!(i32::from(ExitCode::Ok), 0);
}

#[test]
fn schema_has_envelope_fields() {
    let schema = envelope_schema();
    let props = schema["properties"].as_object().unwrap();
    let names: Vec<&str> = props.keys().map(String::as_str).collect();
    for k in [
        "ok",
        "data",
        "findings",
        "warnings",
        "error",
        "schema_version",
    ] {
        assert!(names.contains(&k), "missing {k}");
    }
}

#[test]
fn slug_resolves_from_registry() {
    use gob_rules::{RuleMeta, Scope, Tier};
    static META: RuleMeta = RuleMeta {
        id: "DOC001",
        slug: "bad-call",
        family: "DOC",
        product: "frob",
        severity: Severity::Error,
        summary: "s",
        explanation: "e",
        tier: Tier::Universal,
        scope: Scope::File,
        fix: FixKind::Manual,
        polarity: gob_rules::Polarity::Pplus,
        must_measure: false,
        version: 1,
        since: "0.0.0",
        module: "t",
    };
    let fx = fixture();
    let reg = Registry::from_metas([&META]);
    let rec = FindingRecord::from_finding(&fx.findings[1], &fx.sources, &reg);
    assert_eq!(rec.slug.as_deref(), Some("bad-call"));
}
