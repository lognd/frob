//! Outcome classes (testing.md 1): unresolved, notapplicable, subject accounting, certified clean.

use gob_mdtest::{Case, Runner, run_file};
use gob_rules::{Finding, RequiredReason, RuleReport, Severity, UnresolvedReason};
use gob_text::{FileInterner, Span, TextRange, TextSize};

/// A directive-driven rule: `@subjects T E`, `@na WHY`, `@error`, `@unresolved CODE` lines.
fn directed(case: &Case) -> RuleReport {
    let file = FileInterner::new().intern(&case.file_name);
    let (mut total, mut examined, mut na) = (0, 0, None);
    let mut findings = Vec::new();
    let mut off = 0usize;
    for line in case.text.split_inclusive('\n') {
        let span = Span::new(
            file,
            TextRange::at(
                TextSize::try_from(off).unwrap(),
                TextSize::try_from(line.len()).unwrap(),
            ),
        );
        let mut words = line.split_whitespace();
        match words.next() {
            Some("@subjects") => {
                total = words.next().unwrap().parse().unwrap();
                examined = words.next().unwrap().parse().unwrap();
            }
            Some("@na") => na = Some(words.collect::<Vec<_>>().join(" ")),
            Some("@error") => findings.push(Finding::new(
                case.rule.clone(),
                Severity::Error,
                Some(span),
                "bad",
                &case.file_name,
            )),
            Some("@required") => findings.push(
                Finding::new(
                    case.rule.clone(),
                    Severity::Unresolved,
                    None,
                    "cannot decide",
                    &case.file_name,
                )
                .with_reason(UnresolvedReason::from_code(words.next().unwrap()))
                .with_required(RequiredReason::SiblingMissing {
                    product: "p".to_owned(),
                }),
            ),
            Some("@unresolved") => findings.push(
                Finding::new(
                    case.rule.clone(),
                    Severity::Unresolved,
                    Some(span),
                    "cannot decide",
                    &case.file_name,
                )
                .with_reason(UnresolvedReason::from_code(words.next().unwrap())),
            ),
            _ => {}
        }
        off += line.len();
    }
    RuleReport::new(case.rule.clone(), total, examined, na, findings)
}

/// Run one suite body (header supplied) and return whether every case and control passed.
fn passes(name: &str, body: &str) -> Result<(), String> {
    let dir = std::env::temp_dir().join(format!("gob-mdtest-out-{}-{name}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("s.md");
    let control = "```txt rule=MDT001 expect=fire\n@error\n```\n```txt rule=MDT001 expect=clean\n@subjects 1 1\n```\n";
    std::fs::write(
        &path,
        format!("<!-- mdtest: rule=MDT001 -->\n{control}{body}"),
    )
    .unwrap();
    let r = run_file(&path, &Runner::new(directed));
    std::fs::remove_dir_all(&dir).ok();
    if r.passed() {
        Ok(())
    } else {
        Err(r.render_failures())
    }
}

// frob:tests crates/gob-mdtest/src/run.rs::check
// frob:tests crates/gob-mdtest/src/run.rs::CaseOutput.into_result
#[test]
fn a_rule_that_examines_nothing_fails_clean() {
    let e = passes("empty", "```txt expect=clean\n@subjects 0 0\n```\n").unwrap_err();
    assert!(e.contains("examined 0"), "{e}");
    assert!(passes("one", "```txt expect=clean\n@subjects 2 1\n```\n").is_ok());
    let e = passes(
        "exact",
        "```txt expect=clean subjects=3\n@subjects 3 2\n```\n",
    )
    .unwrap_err();
    assert!(e.contains("subjects=3"), "{e}");
    assert!(
        passes(
            "ge",
            "```txt expect=clean subjects>=2\n@subjects 3 2\n```\n"
        )
        .is_ok()
    );
}

// frob:tests crates/gob-mdtest/src/run.rs::check
#[test]
fn unresolved_only_fails_fire_and_error_fails_unresolved() {
    let e = passes("uf", "```txt expect=fire\n@unresolved hole\n```\n").unwrap_err();
    assert!(e.contains("not Unresolved"), "{e}");
    assert!(passes("rf", "```txt expect=fire\n@required hole\n```\n").is_ok());
    let e = passes(
        "eu",
        "```txt expect=unresolved\n@error\n@unresolved hole\n```\n",
    )
    .unwrap_err();
    assert!(e.contains("only Unresolved"), "{e}");
    assert!(passes("ok", "```txt expect=unresolved\n@unresolved hole\n```\n").is_ok());
    let e = passes("none", "```txt expect=unresolved\n@subjects 1 1\n```\n").unwrap_err();
    assert!(e.contains("got none"), "{e}");
}

// frob:tests crates/gob-mdtest/src/run.rs::check
#[test]
fn a_wrong_reason_code_fails() {
    assert!(
        passes(
            "r1",
            "```txt expect=unresolved reason=hole\n@unresolved hole\n```\n"
        )
        .is_ok()
    );
    let e = passes(
        "r2",
        "```txt expect=unresolved reason=partial\n@unresolved hole\n```\n",
    )
    .unwrap_err();
    assert!(e.contains("reason `partial`"), "{e}");
    let e = passes(
        "r3",
        "```txt expect=unresolved\n@unresolved hole // unresolved[partial]:\n```\n",
    );
    assert!(e.is_err());
}

// frob:tests crates/gob-mdtest/src/run.rs::check
#[test]
fn not_applicable_fails_clean_and_passes_notapplicable() {
    let e = passes(
        "na1",
        "```txt expect=clean\n@subjects 1 1\n@na binary\n```\n",
    )
    .unwrap_err();
    assert!(e.contains("NotApplicable"), "{e}");
    assert!(passes("na2", "```txt expect=notapplicable\n@na binary file\n```\n").is_ok());
    assert!(
        passes(
            "na3",
            "```txt expect=notapplicable reason=binary\n@na binary file\n```\n"
        )
        .is_ok()
    );
    let e = passes(
        "na4",
        "```txt expect=notapplicable reason=text\n@na binary file\n```\n",
    )
    .unwrap_err();
    assert!(e.contains("reason `text`"), "{e}");
    let e = passes("na5", "```txt expect=notapplicable\n@subjects 1 1\n```\n").unwrap_err();
    assert!(e.contains("it applied"), "{e}");
}

#[test]
fn modifiers_are_validated() {
    let e = passes("m1", "```txt expect=fire known-gap=~ABC1234\n@error\n```\n").unwrap_err();
    assert!(e.contains("known-gap"), "{e}");
    assert!(
        passes(
            "m2",
            "```txt expect=unresolved known-gap=~ABC1234\n@unresolved hole\n```\n"
        )
        .is_ok()
    );
    assert!(
        passes(
            "m3",
            "```txt expect=clean fixed fidelity=F2 parse=ok\n@subjects 1 1\n```\n"
        )
        .is_ok()
    );
}

/// FORMAT.md documents the outcome vocabulary.
#[test]
fn format_documents_the_vocabulary() {
    let doc = std::fs::read_to_string(concat!(env!("CARGO_MANIFEST_DIR"), "/FORMAT.md")).unwrap();
    for word in [
        "expect=fire|clean|unresolved|notapplicable",
        "subjects>=N",
        "known-gap=~TICKET",
        "fixed",
        "certified clean",
        "reason=",
    ] {
        assert!(doc.contains(word), "FORMAT.md lacks `{word}`");
    }
}
