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
            let found = diags(&src);
            assert!(found.is_empty(), "{}: {found:#?}", path.display());
        }
    }
}

#[test]
fn a_misspelt_kind_field_verb_and_knob_are_unknown_words() {
    let h = "lang rust\n  knob depth: int = 3 \"d\"";
    for (body, what) in [
        ("  find f: functoin\n  report f \"m\"", "kind"),
        (
            "  find f: function where f.nmae == \"a\"\n  report f \"m\"",
            "field",
        ),
        (
            "  find f: function find g: call where g clals f\n  report f \"m\"",
            "verb",
        ),
        (
            "  find f: function where f.line < knob.dpeth\n  report f \"m\"",
            "knob",
        ),
    ] {
        let d = diags(&rule(h, body));
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

#[test]
fn a_word_no_language_answers_is_grl018_but_universal_rules_are_not_checked() {
    assert_eq!(
        codes("lang [css, scss]", "  find t: test\n  report t \"m\""),
        [Code::Grl018]
    );
    assert!(codes("lang [css, rust]", "  find t: test\n  report t \"m\"").is_empty());
    assert!(codes("lang *", "  find t: test\n  report t \"m\"").is_empty());
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
        codes(h, "  find p: diff.chagned\n  report p \"{p}\""),
        [Code::Grl001]
    );
}
