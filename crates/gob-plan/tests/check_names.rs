//! Behaviour of the name and type checks beyond the goldens (grl-spec.md sections 7.1 and 10).

use gob_plan::check::{Code, Diagnostic, check_file};
use gob_plan::grl::parse;
use gob_text::FileInterner;

/// A rule around `body` (clauses) with the headers `header`.
fn rule(header: &str, body: &str) -> String {
    format!(
        "rule NOPE999 \"t\" {{\n  {header}\n{body}\n  example fire \"\"\"\n    x\n  \"\"\"\n  example clean \"\"\"\n    y\n  \"\"\"\n  explain \"\"\"\n    e\n\n    ## Remedy\n    r\n  \"\"\"\n}}\n"
    )
}

/// `word` with its first two letters swapped: a typo that no spell checker has to tolerate in the source.
fn typo(word: &str) -> String {
    let mut c: Vec<char> = word.chars().collect();
    c.swap(0, 1);
    c.into_iter().collect()
}

fn diags(src: &str) -> Vec<Diagnostic> {
    let parsed = parse(FileInterner::new().intern("t.grl"), src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    check_file(&parsed.file)
}

fn codes(header: &str, body: &str) -> Vec<Code> {
    diags(&rule(header, body))
        .iter()
        .filter_map(|d| d.code)
        .collect()
}

// frob:tests crates/gob-plan/src/check/mod.rs::compile_report
// frob:tests crates/gob-plan/src/check/mod.rs::check_file
// frob:tests crates/gob-plan/src/check/mod.rs::Diagnostic.new
// frob:tests crates/gob-plan/src/check/mod.rs::Diagnostic.with_help
// frob:tests crates/gob-plan/src/check/mod.rs::Diagnostic.with_note
// frob:tests crates/gob-plan/src/check/mod.rs::Diagnostic.with_secondary
// frob:tests crates/gob-plan/src/check/mod.rs::Code.as_str
// frob:tests crates/gob-plan/src/check/mod.rs::Code.severity
// frob:tests crates/gob-plan/src/check/render.rs::render
#[test]
fn compile_report_prints_a_golden_shape_for_a_unknown_kind() {
    let src = rule(
        "lang rust",
        &format!("  find f: {}\n  report f \"m\"", typo("function")),
    );
    let out = gob_plan::check::compile_report("rules/x.grl", &src);
    assert!(out.starts_with("error[GRL001]: unknown kind `"), "{out}");
    assert!(out.contains("= help: did you mean `function`?"), "{out}");
    assert!(
        out.ends_with("error: aborting due to 1 previous error\n"),
        "{out}"
    );
    let d = &diags(&src)[0];
    assert_eq!(d.code.map(Code::as_str), Some("GRL001"));
    assert_eq!(Code::Grl013.severity(), gob_plan::check::Severity::Warning);
}

// frob:tests crates/gob-plan/src/check/mod.rs::Diagnostic.syntax
#[test]
fn a_syntax_error_renders_without_a_code() {
    let out = gob_plan::check::compile_report("rules/x.grl", "rule NOPE999 \"t\" {");
    assert!(out.starts_with("error: "), "{out}");
    assert!(!out.contains("grimble explain"), "{out}");
}

// frob:ticket 01M3ZX7DYR7PR1PBCZ7E8Q56WW
#[test]
fn the_fixture_rules_of_the_spec_check_clean() {
    let dir = format!(
        "{}/src/grl/parse/tests/fixtures",
        env!("CARGO_MANIFEST_DIR")
    );
    for entry in std::fs::read_dir(dir).expect("fixtures") {
        let path = entry.expect("entry").path();
        if path.extension().is_some_and(|e| e == "grl") {
            let src = std::fs::read_to_string(&path).expect("read");
            // The spec's abbreviated rules omit the universal third example (GRL011); every
            // other code must stay silent.
            let found: Vec<_> = diags(&src)
                .into_iter()
                .filter(|d| !(d.code == Some(Code::Grl011) && d.message.contains("notapplicable")))
                .collect();
            assert!(found.is_empty(), "{}: {found:#?}", path.display());
        }
    }
}

#[test]
fn a_misspelt_kind_field_verb_and_knob_are_unknown_words() {
    let h = "lang rust\n  knob depth: int = 3 \"d\"";
    for (body, what) in [
        (
            format!("  find f: {}\n  report f \"m\"", typo("function")),
            "kind",
        ),
        (
            format!(
                "  find f: function where f.{} == \"a\"\n  report f \"m\"",
                typo("name")
            ),
            "field",
        ),
        (
            format!(
                "  find f: function find g: call where g {} f\n  report f \"m\"",
                typo("calls")
            ),
            "verb",
        ),
        (
            format!(
                "  find f: function where f.line < knob.{}\n  report f \"m\"",
                typo("depth")
            ),
            "knob",
        ),
    ] {
        let d = diags(&rule(h, &body));
        assert_eq!(d.len(), 1, "{what}: {d:#?}");
        assert_eq!(d[0].code, Some(Code::Grl001), "{what}");
        assert!(
            d[0].helps.iter().any(|x| x.starts_with("did you mean")),
            "{what}: {:?}",
            d[0].helps
        );
    }
}

#[test]
fn a_variable_used_inside_not_is_grl003_but_a_typo_of_a_variable_is_grl001() {
    let h = "lang rust";
    assert_eq!(
        codes(
            h,
            "  find f: function\n  where not f calls g\n  report f \"m\""
        ),
        [Code::Grl003]
    );
    assert_eq!(
        codes(
            h,
            "  find fun: function\n  where not fun calls fnu\n  report fun \"m\""
        ),
        [Code::Grl001]
    );
    assert_eq!(
        codes(h, "  find f: function\n  where f calls g\n  report f \"m\""),
        [Code::Grl001]
    );
    assert_eq!(
        codes(
            h,
            "  find f: function\n  unresolved when f calls g because \"r\"\n  report f \"m\""
        ),
        [Code::Grl003]
    );
}

#[test]
fn binding_rules_for_quantifiers_and_defs() {
    let h = "lang rust";
    // A quantifier head is visible only inside it, so siblings may reuse the name.
    assert!(codes(h, "  find f: function\n  where any { some t: test where t calls f, some t: test where t tests f }\n  report f \"m\"").is_empty());
    // Rebinding an outer name inside `no` is GRL004.
    assert_eq!(
        codes(
            h,
            "  find f: function\n  where no f: test where f tests f\n  report f \"m\""
        ),
        [Code::Grl004]
    );
    // A def sees only its parameters.
    assert_eq!(
        codes(
            h,
            "  find f: function\n  def d(x) = x calls f\n  report f \"m\""
        ),
        [Code::Grl001]
    );
    // A `some` witness may be named in the report; a `no` head may not.
    assert!(
        codes(
            h,
            "  find f: function\n  where some c: call where c inside f\n  report f \"{c.name}\""
        )
        .is_empty()
    );
    assert_eq!(
        codes(
            h,
            "  find f: function\n  where no c: call where c inside f\n  report f \"{c.name}\""
        ),
        [Code::Grl001]
    );
}

#[test]
fn type_mismatches_are_grl005() {
    let h = "lang rust\n  knob g: glob = \"a*\" \"g\"";
    for body in [
        "  find f: function where f.line == \"3\"\n  report f \"m\"",
        "  find f: function where f.name > 3\n  report f \"m\"",
        "  find f: function where f.name ~ knob.g\n  report f \"m\"",
        "  find f: function where f.name matches /a/\n  report f \"m\"",
        "  find f: function where f.line in 3\n  report f \"m\"",
        "  find f: function where f.name + 1 > 2\n  report f \"m\"",
    ] {
        assert_eq!(codes(h, body), [Code::Grl005], "{body}");
    }
    assert!(codes(h, "  find f: function where f.line >= 3 and f.name matches knob.g and f.line in 1..9\n  report f \"m\"").is_empty());
}

#[test]
fn unused_quantifier_heads_are_not_warned_but_unused_finds_are() {
    let h = "lang rust";
    assert!(
        codes(
            h,
            "  find f: function\n  where no t: test\n  report f \"m\""
        )
        .is_empty()
    );
    assert_eq!(
        codes(h, "  find f: function\n  find c: comment\n  report f \"m\""),
        [Code::Grl013]
    );
}

#[test]
fn certainly_is_only_allowed_in_positive_positions() {
    let h = "lang rust";
    assert!(
        codes(
            h,
            "  find f: function\n  find g: function\n  where f certainly calls g\n  report f \"m\""
        )
        .is_empty()
    );
    assert!(codes(h, "  find f: function\n  find g: function\n  where not not f possibly calls g\n  report f \"m\"").is_empty());
    assert_eq!(
        codes(
            h,
            "  find f: function\n  where no t: test where t possibly tests f\n  report f \"m\""
        ),
        [Code::Grl017]
    );
}

// frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
#[test]
fn certainly_in_a_def_body_is_negative_when_the_call_is_under_not() {
    let h = "lang rust";
    let def = "  def d(a, b) = a certainly calls b\n";
    let find = "  find f: function\n  find g: function\n";
    let src = |w: &str| format!("{def}{find}  where {w}\n  report f \"m\"");
    assert_eq!(codes(h, &src("not d(f, g)")), [Code::Grl017]);
    assert_eq!(codes(h, &src("no t: test where d(t, g)")), [Code::Grl017]);
    assert!(codes(h, &src("d(f, g)")).is_empty());
    assert!(codes(h, &src("not not d(f, g)")).is_empty());
    // A negation inside the def is reported once, at the def, and a double negation cancels.
    let inner = "  def e(a, b) = not a possibly calls b\n";
    let body = format!("{inner}{find}  where e(f, g)\n  report f \"m\"");
    assert_eq!(codes(h, &body), [Code::Grl017]);
    let body = format!("{inner}{find}  where not e(f, g)\n  report f \"m\"");
    assert_eq!(codes(h, &body), [Code::Grl017]);
    // Two calls under `not` report the one certainly span once.
    assert_eq!(
        codes(h, &src("not d(f, g) and not d(g, f)")),
        [Code::Grl017]
    );
    // A def that calls another def carries the negation through.
    let chain =
        format!("{def}  def e(a, b) = d(a, b)\n{find}  where not e(f, g)\n  report f \"m\"");
    assert_eq!(codes(h, &chain), [Code::Grl017]);
}

// frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
#[test]
fn certainly_in_a_count_body_is_negative_under_a_lower_bound_comparison() {
    let h = "lang rust";
    let src = |w: &str| format!("  find f: function\n  where {w}\n  report f \"m\"");
    let c = "count(g: function where f certainly calls g)";
    for op in ["<", "<=", "==", "!="] {
        assert_eq!(
            codes(h, &src(&format!("{c} {op} 2"))),
            [Code::Grl017],
            "{op}"
        );
    }
    for op in [">", ">="] {
        assert!(codes(h, &src(&format!("{c} {op} 2"))).is_empty(), "{op}");
    }
    // The count on the right mirrors, and a subtrahend is negative.
    assert_eq!(codes(h, &src(&format!("2 > {c}"))), [Code::Grl017]);
    assert!(codes(h, &src(&format!("2 < {c}"))).is_empty());
    let d = "count(g: function where f possibly calls g)";
    assert_eq!(codes(h, &src(&format!("1 + 3 - {d} > 0"))), [Code::Grl017]);
    assert!(codes(h, &src(&format!("{d} - 1 > 0"))).is_empty());
}

// frob:ticket 01M4E0BVMZHYZYC7PHEA0YWS08
#[test]
fn certainly_in_an_earlier_report_when_is_negative() {
    let h = "lang rust";
    let find = "  find f: function\n  find g: function\n  where f calls g\n";
    let early = "  report f \"a\" when f certainly calls g\n  report f \"b\"";
    assert_eq!(codes(h, &format!("{find}{early}")), [Code::Grl017]);
    let last = "  report f \"b\"\n  report f \"a\" when f certainly calls g";
    assert!(codes(h, &format!("{find}{last}")).is_empty());
    let only = "  report f \"a\" when f possibly calls g";
    assert!(codes(h, &format!("{find}{only}")).is_empty());
}

#[test]
fn a_word_no_language_answers_is_grl018_but_universal_rules_are_not_checked() {
    assert_eq!(
        codes("lang [css, scss]", "  find t: test\n  report t \"m\""),
        [Code::Grl018]
    );
    assert!(codes("lang [css, rust]", "  find t: test\n  report t \"m\"").is_empty());
    assert!(!codes("lang *", "  find t: test\n  report t \"m\"").contains(&Code::Grl018));
    assert!(codes("lang css", "  find e: style_rule\n  report e \"m\"").is_empty());
    assert_eq!(
        codes("lang rust", "  find e: element\n  report e \"m\""),
        [Code::Grl018]
    );
}

#[test]
fn side_relations_are_checked() {
    let h = "lang -\n  needs diff, lease";
    assert!(
        codes(
            h,
            "  find p: diff.changed\n  where not p matches lease.globs\n  report p \"{p}\""
        )
        .is_empty()
    );
    assert_eq!(
        codes(
            h,
            &format!("  find p: diff.{}\n  report p \"{{p}}\"", typo("changed"))
        ),
        [Code::Grl001]
    );
}
