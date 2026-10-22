//! Heading-tree sections, multi-file cases, inherited toml config and `[mdtest] languages`.
// frob:ticket 01M48PC09SX0KFAM4B3V88AAXW

use gob_mdtest::{Case, Runner, parse_suite, run_file};
use gob_rules::{Finding, Severity};
use gob_text::{FileInterner, Span, TextRange, TextSize};

/// A one-line finding at the start of `file` (interned in an order unlike the case's).
fn at(case: &Case, ids: &mut FileInterner, file: &str, rule: &str) -> Finding {
    let id = ids.intern(file);
    let span = Span::new(id, TextRange::at(TextSize::new(0), TextSize::new(1)));
    Finding::new(
        rule.parse().unwrap(),
        Severity::Error,
        Some(span),
        "found",
        &case.file_name,
    )
}

/// LNK001: a markdown link to a file that is not a file of the case; `broken` lines of rust files.
fn links(case: &Case) -> Vec<Finding> {
    let mut ids = FileInterner::new();
    ids.intern("zzz-first-so-ids-differ");
    let mut out = Vec::new();
    for f in &case.files {
        for (n, line) in f.text.lines().enumerate() {
            let broken = if f.language == "rust" {
                line.contains("broken")
            } else {
                line.split("](")
                    .skip(1)
                    .filter_map(|r| r.split(')').next())
                    .any(|t| !case.files.iter().any(|g| g.file_name == t))
            };
            if broken {
                let mut finding = at(case, &mut ids, &f.file_name, "LNK001");
                if let Some(span) = finding.span.as_mut() {
                    let off = f.text.lines().take(n).map(|l| l.len() + 1).sum::<usize>();
                    span.range = TextRange::at(
                        TextSize::try_from(off).unwrap(),
                        TextSize::try_from(line.len()).unwrap(),
                    );
                }
                out.push(finding);
            }
        }
    }
    case.attribute(&mut out, |id| ids.path(id));
    out
}

/// CFG001: fires on line one when the merged config says `strict = true`.
fn config(case: &Case) -> Vec<Finding> {
    let strict = case.config.as_deref().is_some_and(|c| {
        c.parse::<toml::Table>()
            .unwrap()
            .get("strict")
            .and_then(toml::Value::as_bool)
            == Some(true)
    });
    if !strict {
        return Vec::new();
    }
    let mut ids = FileInterner::new();
    let mut out = vec![at(case, &mut ids, &case.file_name, "CFG001")];
    case.attribute(&mut out, |id| ids.path(id));
    out
}

/// Path of a corpus under `tests/mdtest_sections`.
fn corpus(name: &str) -> std::path::PathBuf {
    gob_mdtest::manifest_dir(env!("CARGO_MANIFEST_DIR"))
        .join("tests/mdtest_sections")
        .join(name)
}

/// Parse `md` and return the error message.
fn err(md: &str) -> String {
    parse_suite(md).unwrap_err().message
}

// frob:tests Block.matrix_cells
// frob:tests parse_suite
#[test]
fn cross_file_link_corpus_passes() {
    let r = run_file(&corpus("xfile.md"), &Runner::new(links));
    assert!(r.passed(), "{}", r.render_failures());
    assert_eq!(r.cases.len(), 3);
}

// frob:tests parse_suite
#[test]
fn inherited_config_corpus_passes() {
    let r = run_file(&corpus("config.md"), &Runner::new(config));
    assert!(r.passed(), "{}", r.render_failures());
    assert_eq!(r.cases.len(), 3);
}

// frob:tests parse_suite
#[test]
fn config_merges_through_three_levels_and_siblings_stay_isolated() {
    let md = std::fs::read_to_string(corpus("config.md")).unwrap();
    let blocks = parse_suite(&md).unwrap();
    let cfg = |i: usize| -> toml::Table { blocks[i].config.as_deref().unwrap().parse().unwrap() };
    assert_eq!(cfg(0)["strict"].as_bool(), Some(true));
    assert_eq!(cfg(0)["level"].as_integer(), Some(1));
    assert_eq!(cfg(1)["strict"].as_bool(), Some(false));
    assert_eq!(cfg(1)["level"].as_integer(), Some(1));
    assert_eq!(cfg(2)["strict"].as_bool(), Some(false));
}

// frob:tests parse_suite
#[test]
fn section_that_is_test_and_group_is_a_parse_error() {
    let md = "# A\n\n```text expect=clean rule=MDT001\nx\n```\n\n## B\n\n```text expect=clean rule=MDT001\ny\n```\n";
    let m = err(md);
    assert!(m.contains("also a group"), "{m}");
}

// frob:tests parse_suite
#[test]
fn several_cases_directly_under_one_heading_stay_separate() {
    let md = "# A\n\n```text expect=clean rule=MDT001\nx\n```\n\n```text expect=fire rule=MDT001\ny // error: MDT001\n```\n";
    assert_eq!(parse_suite(md).unwrap().len(), 2);
}

// frob:tests parse_suite
#[test]
fn empty_sections_and_level_skips_are_fine() {
    let md = "# A\n\n## Empty\n\n# B\n\n### Skipped\n\n```text expect=clean rule=MDT001\nx\n```\n";
    let b = parse_suite(md).unwrap();
    assert_eq!(b.len(), 1);
    assert_eq!(b[0].section, "B / Skipped");
}

// frob:tests parse_suite
#[test]
fn duplicate_file_names_are_rejected() {
    let md = "# A\n\n```text expect=clean rule=MDT001\nx\n```\n\n```text file=a\n1\n```\n\n```text file=a\n2\n```\n";
    assert!(err(md).contains("duplicate file="));
}

// frob:tests parse_suite
#[test]
fn extra_files_need_exactly_one_case_block() {
    let none = "# A\n\n```text file=a\n1\n```\n";
    assert!(err(none).contains("no case block"));
    let two = "# A\n\n```text expect=clean rule=MDT001\nx\n```\n\n```text expect=clean rule=MDT001\ny\n```\n\n```text file=a\n1\n```\n";
    assert!(err(two).contains("ambiguous"));
}

// frob:tests parse_suite
#[test]
fn invalid_toml_and_unknown_mdtest_keys_are_rejected() {
    assert!(parse_suite("# A\n\n```toml\na = = 1\n```\n").is_err());
    assert!(parse_suite("# A\n\n```toml\n[mdtest]\nbogus = 1\n```\n").is_err());
    assert!(parse_suite("# A\n\n```toml\n[mdtest]\nlanguages = [\"klingon\"]\n```\n").is_err());
}

// frob:tests parse_suite
#[test]
fn same_language_continuation_merges_into_the_case() {
    let md = "# A\n\n```text expect=clean rule=MDT001\nx\n```\n\n```text\ny\n```\n";
    let b = parse_suite(md).unwrap();
    assert_eq!(b.len(), 1);
    assert!(b[0].text.contains('x') && b[0].text.contains('y'));
}

// frob:tests Block.matrix_cells
// frob:tests parse_suite
#[test]
fn mixed_languages_keep_their_own_fidelity_and_languages_select_cells() {
    let md = "# A\n\n```toml\n[mdtest]\nlanguages = [\"rust\", \"python\"]\n```\n\n```markdown expect=clean rule=MDT001 fidelity=F3\nx\n```\n\n```rust file=a.rs fidelity=F1\nfn a() {}\n```\n";
    let b = &parse_suite(md).unwrap()[0];
    assert_eq!(b.fidelity.as_deref(), Some("F3"));
    assert_eq!(b.files.len(), 1);
    assert_eq!(b.files[0].language, "rust");
    assert_eq!(b.files[0].fidelity.as_deref(), Some("F1"));
    assert_eq!(b.matrix_cells(), vec!["rust", "python"]);
}
