//! Scanner behaviour: binding rules, reorientation, records, rules and schema.

mod common;

use gob_directives::frob::{Accept, Defer, Doc, Tests, Ticket, Todo};
use gob_directives::{Binding, Directive, ScanConfig, all_directives};
use gob_rules::Registry;

const ID: &str = "01J9QKX3M8Z4T7N2V5B6C0D1E2";

fn bound(path: &str, text: &str) -> Vec<Binding> {
    let r = common::scan(path, text);
    assert!(
        r.findings.is_empty(),
        "unexpected findings: {:?}",
        r.findings
    );
    r.directives.into_iter().map(|d| d.bound).collect()
}

fn sym(s: &str) -> Binding {
    Binding::Symbol(s.parse().unwrap())
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
// frob:tests crates/gob-directives/src/bind.rs::bind
#[test]
fn blank_line_ends_the_directive_block() {
    let text = format!("// frob:ticket {ID}\n\nfn target() {{}}\n");
    assert_eq!(bound("src/a.rs", &text), [Binding::File]);
}

#[test]
fn binds_to_adjacent_fn_and_doc_comment_form() {
    let text = format!("/// frob:ticket {ID}\nfn target() {{}}\n");
    assert_eq!(bound("src/a.rs", &text), [sym("src/a.rs::target")]);
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
// frob:tests crates/gob-directives/src/bind.rs::bind
#[test]
fn two_blank_lines_also_end_the_block() {
    let text = format!("// frob:ticket {ID}\n\n\nfn target() {{}}\n");
    assert_eq!(bound("src/a.rs", &text), [Binding::File]);
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
// frob:tests crates/gob-directives/src/bind.rs::bind
#[test]
fn two_stacked_tests_directives_all_bind() {
    let text = "#[cfg(test)]\nmod tests {\n    // frob:tests src/a.rs::foo\n    // frob:tests src/a.rs::bar\n    #[test]\n    fn works() {}\n}\n";
    assert_eq!(
        bound("src/a.rs", text),
        [sym("src/a.rs::foo"), sym("src/a.rs::bar")]
    );
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
// frob:tests crates/gob-directives/src/bind.rs::bind
#[test]
fn three_stacked_tests_directives_all_bind() {
    let text = "fn foo() {}\n\n// frob:tests src/a.rs::foo\n// frob:tests src/a.rs::foo2\n// frob:tests src/a.rs::foo3\n#[test]\nfn works() {}\n";
    let r = common::scan("src/a.rs", text);
    assert!(r.findings.is_empty(), "{:?}", r.findings);
    let got: Vec<_> = r.directives.iter().map(|d| d.bound.clone()).collect();
    assert_eq!(
        got,
        [
            sym("src/a.rs::foo"),
            sym("src/a.rs::foo2"),
            sym("src/a.rs::foo3")
        ]
    );
    assert!(r.directives.iter().all(|d| {
        d.source
            .as_ref()
            .is_some_and(|s| s.to_string() == "src/a.rs::works")
    }));
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
// frob:tests crates/gob-directives/src/bind.rs::block_limit
#[test]
fn stacked_directives_mixed_with_comments_docs_and_attributes_bind() {
    let text = format!(
        "// frob:ticket {ID}\n// ordinary note\n/// docs\n#[inline]\n#[allow(\n    dead_code,\n)]\n// frob:invariant sorted\n/// more docs\nfn target() {{}}\n"
    );
    assert_eq!(
        bound("src/a.rs", &text),
        [sym("src/a.rs::target"), sym("src/a.rs::target")]
    );
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
// frob:tests crates/gob-directives/src/bind.rs::block_limit
#[test]
fn stacked_directives_in_a_block_comment_and_below_it_bind() {
    let text = format!(
        "/*\n * frob:ticket {ID}\n * frob:invariant sorted\n */\n#[test]\nfn target() {{}}\n"
    );
    assert_eq!(
        bound("src/a.rs", &text),
        [sym("src/a.rs::target"), sym("src/a.rs::target")]
    );
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
// frob:tests crates/gob-directives/src/bind.rs::bind
#[test]
fn markdown_stacked_comments_bind_to_the_same_heading() {
    let text = format!(
        "# One\n\n<!-- frob:ticket {ID} -->\n<!-- frob:doc docs/x.md#sec -->\n<!-- note -->\n<!-- frob:ticket {ID} -->\n## Two\n"
    );
    let one = Binding::Symbol("docs/a.md#one".parse().unwrap());
    assert_eq!(bound("docs/a.md", &text), [one.clone(), one.clone(), one]);
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
// frob:tests crates/gob-directives/src/scan.rs::Scanner.record
#[test]
fn tests_directive_separated_by_a_blank_line_is_not_attached() {
    let text = "fn foo() {}\n\n// frob:tests src/a.rs::foo\n\n#[test]\nfn works() {}\n";
    let r = common::scan("src/a.rs", text);
    assert!(r.directives.is_empty(), "{:?}", r.directives);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule.as_str(), "PARSE001");
    assert_eq!(r.findings[0].message, gob_directives::NOT_ATTACHED);
    assert!(r.findings[0].message.contains("not attached to an item"));
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
// frob:tests crates/gob-directives/src/scan.rs::Scanner.record
#[test]
fn tests_directive_at_the_end_of_a_file_is_not_attached() {
    let text = "fn foo() {}\n// frob:tests src/a.rs::foo\n";
    let r = common::scan("src/a.rs", text);
    assert!(r.directives.is_empty());
    assert_eq!(r.findings[0].message, gob_directives::NOT_ATTACHED);
}

#[test]
fn enclosing_symbol_when_nothing_follows() {
    let text =
        format!("fn outer() {{\n    let a = 1;\n    // frob:ticket {ID}\n    let b = 2;\n}}\n");
    assert_eq!(bound("src/a.rs", &text), [sym("src/a.rs::outer")]);
}

#[test]
fn innermost_enclosing_wins() {
    let text = format!(
        "mod m {{\n    fn inner() {{\n        let a = 1;\n\n\n\n        // frob:ticket {ID}\n    }}\n}}\n"
    );
    assert_eq!(bound("src/a.rs", &text), [sym("src/a.rs::m.inner")]);
}

#[test]
fn file_level_when_no_symbols() {
    let text = format!("// frob:ticket {ID}\n");
    assert_eq!(bound("src/a.rs", &text), [Binding::File]);
}

#[test]
fn inner_doc_binds_to_container_not_next_item() {
    let text = format!("//! frob:ticket {ID}\n\nfn first() {{}}\n");
    assert_eq!(bound("src/a.rs", &text), [Binding::File]);
}

#[test]
fn markdown_binds_to_preceding_heading() {
    let text = format!("# One\n\n<!-- frob:ticket {ID} -->\n\n## Two\n\ntext\n");
    assert_eq!(
        bound("docs/a.md", &text),
        [Binding::Symbol("docs/a.md#one".parse().unwrap())]
    );
}

#[test]
fn markdown_before_first_heading_is_file() {
    let text = format!("<!-- frob:ticket {ID} -->\n\n# One\n");
    assert_eq!(bound("docs/a.md", &text), [Binding::File]);
}

#[test]
fn toml_hash_comment_is_file_bound() {
    let r = common::scan("frob.toml", "# frob:invariant sorted\nkey = 1\n");
    assert_eq!(r.directives.len(), 1);
    assert_eq!(r.directives[0].bound, Binding::File);
}

#[test]
fn tests_reorients_to_target_inside_test_item() {
    let text = "fn foo() {}\n\n#[test]\nfn works() {\n    // frob:tests src/a.rs::foo\n}\n";
    let r = common::scan("src/a.rs", text);
    assert!(r.findings.is_empty());
    let d = &r.directives[0];
    assert_eq!(d.bound, sym("src/a.rs::foo"));
    assert_eq!(d.source.as_ref().unwrap().to_string(), "src/a.rs::works");
}

#[test]
fn tests_inside_module_tests_reorients() {
    let text =
        "fn foo() {}\n\nmod tests {\n    // frob:tests src/a.rs::foo\n    fn helper() {}\n}\n";
    let r = common::scan("src/a.rs", text);
    let d = &r.directives[0];
    assert_eq!(d.bound, sym("src/a.rs::foo"));
    assert_eq!(
        d.source.as_ref().unwrap().to_string(),
        "src/a.rs::tests.helper"
    );
}

#[test]
fn tests_outside_a_test_item_does_not_reorient() {
    let text = "// frob:tests src/a.rs::foo\nfn prod() {}\n";
    let r = common::scan("src/a.rs", text);
    let d = &r.directives[0];
    assert_eq!(d.bound, sym("src/a.rs::prod"));
    assert!(d.source.is_none());
}

#[test]
fn tests_with_bad_target_in_test_item_is_parse001() {
    let text = "#[test]\nfn works() {\n    // frob:tests src/a.rs::\n}\n";
    let r = common::scan("src/a.rs", text);
    assert_eq!(r.findings.len(), 1);
    assert_eq!(r.findings[0].rule.as_str(), "PARSE001");
    assert!(r.findings[0].message.contains("not a symref"));
}

#[test]
fn record_span_covers_directive_text() {
    let text = format!("fn a() {{}}\n// frob:ticket {ID}\n");
    let r = common::scan("src/a.rs", &text);
    let range = r.directives[0].span.range;
    let (s, e) = (
        u32::from(range.start()) as usize,
        u32::from(range.end()) as usize,
    );
    assert_eq!(&text[s..e], format!("frob:ticket {ID}"));
}

#[test]
fn typed_args_round_trip() {
    let text = format!(
        "// frob:accept COV006 because=\"a b\" until=2027-01-01\n// frob:defer COV006 because=x ticket={ID}\n// frob:todo {ID} do the thing\n// frob:doc docs/x.md#sec\n// frob:tests src/a.rs::f kind=unit\nfn f() {{}}\n"
    );
    let r = common::scan("src/a.rs", &text);
    assert!(r.findings.is_empty(), "{:?}", r.findings);
    let by = |v: &str| r.directives.iter().find(|d| d.verb == v).unwrap();
    let a = Accept::parse_args(&by("accept").args).unwrap();
    assert_eq!(
        (a.rule.as_str(), a.because.as_str(), a.until.as_deref()),
        ("COV006", "a b", Some("2027-01-01"))
    );
    let d = Defer::parse_args(&by("defer").args).unwrap();
    assert_eq!(d.ticket, ID);
    let t = Todo::parse_args(&by("todo").args).unwrap();
    assert_eq!(t.note, ["do", "the", "thing"]);
    assert_eq!(
        Doc::parse_args(&by("doc").args)
            .unwrap()
            .target
            .0
            .to_string(),
        "docs/x.md#sec"
    );
    assert_eq!(
        Tests::parse_args(&by("tests").args)
            .unwrap()
            .kind
            .as_deref(),
        Some("unit")
    );
    assert_eq!(Ticket::NAMESPACE, "frob");
}

#[test]
fn dsl001_suggests_close_verb_and_points_at_it() {
    let r = common::scan("src/a.rs", "// frob:tickt x\nfn a() {}\n");
    let f = &r.findings[0];
    assert_eq!(f.rule.as_str(), "DSL001");
    assert!(
        f.message.contains("did you mean `frob:ticket`"),
        "{}",
        f.message
    );
    assert_eq!(u32::from(f.span.unwrap().range.start()), 8);
    assert!(r.directives.is_empty());
}

#[test]
fn dsl002_names_the_remedy_and_has_no_fix() {
    let r = common::scan("src/a.rs", "// frob:ticket 3M8Z4T7\nfn a() {}\n");
    let f = &r.findings[0];
    assert_eq!(f.rule.as_str(), "DSL002");
    assert!(f.message.contains("frob ticket show"));
    assert!(f.fix.is_none());
    assert!(r.directives.is_empty());
}

#[test]
fn parse001_points_at_the_exact_token() {
    let text = "// frob:accept COV006 color=red because=x\n";
    let r = common::scan("src/a.rs", text);
    let f = &r.findings[0];
    assert_eq!(f.rule.as_str(), "PARSE001");
    let range = f.span.unwrap().range;
    assert_eq!(
        &text[u32::from(range.start()) as usize..u32::from(range.end()) as usize],
        "color"
    );
}

#[test]
fn unhonoured_namespaces_are_ignored_and_honoured_ones_all_unknown() {
    let r = common::scan("src/a.rs", "// grimble:binds a\n// crunk:nonsense\n");
    assert!(r.findings.is_empty() && r.directives.is_empty());
    let cfg = ScanConfig {
        namespaces: vec!["grimble".into()],
        product: "grimble".into(),
    };
    let r = common::scan_with(&cfg, "src/a.rs", "// grimble:bind a\n");
    assert_eq!(r.findings[0].rule.as_str(), "DSL001");
    assert!(r.findings[0].message.contains("grimble:binds"));
}

#[test]
fn block_comment_lines_are_scanned_individually() {
    let text = format!("/*\n * frob:ticket {ID}\n * frob:invariant sorted\n */\nfn a() {{}}\n");
    let r = common::scan("src/a.rs", &text);
    assert_eq!(r.directives.len(), 2);
}

#[test]
fn rules_are_registered_with_d32_identity() {
    let reg = Registry::global();
    for (id, slug) in [
        ("PARSE001", "malformed-directive"),
        ("DSL001", "unknown-directive-verb"),
        ("DSL002", "abbreviated-ticket-id"),
    ] {
        let m = reg.by_id(id).unwrap();
        assert_eq!((m.slug, m.product), (slug, "frob"));
    }
}

#[test]
fn registry_lists_every_verb_with_schemas() {
    let verbs: Vec<String> = all_directives()
        .map(gob_directives::DirectiveMeta::qualified)
        .collect();
    assert_eq!(
        verbs,
        [
            "frob:accept",
            "frob:calls",
            "frob:core",
            "frob:defer",
            "frob:describes",
            "frob:dispatcher",
            "frob:doc",
            "frob:effects",
            "frob:honest",
            "frob:hook",
            "frob:idempotent",
            "frob:invariant",
            "frob:pure",
            "frob:shell",
            "frob:tests",
            "frob:ticket",
            "frob:todo",
            "frob:trusted",
            "grimble:binds"
        ]
        .map(String::from)
    );
    let accept = all_directives().find(|m| m.verb == "accept").unwrap();
    let schema = serde_json::to_value(accept.json_schema()).unwrap();
    assert_eq!(schema["properties"]["because"]["type"], "string");
    assert_eq!(schema["required"], serde_json::json!(["rule", "because"]));
    let todo = all_directives().find(|m| m.verb == "todo").unwrap();
    let schema = serde_json::to_value(todo.json_schema()).unwrap();
    assert_eq!(schema["properties"]["note"]["type"], "array");
    let effects = all_directives().find(|m| m.verb == "effects").unwrap();
    let schema = serde_json::to_value(effects.json_schema()).unwrap();
    assert_eq!(schema["properties"]["set"]["type"], "array");
}

#[test]
fn dsl001_suggests_the_new_claim_verbs() {
    for (typo, want) in [
        ("effect", "effects"),
        ("dispatch", "dispatcher"),
        ("idempotant", "idempotent"),
        ("trust", "trusted"),
        ("call", "calls"),
    ] {
        let r = common::scan("src/a.rs", &format!("// frob:{typo} x\n"));
        assert_eq!(r.findings[0].rule.as_str(), "DSL001", "{typo}");
        assert!(
            r.findings[0]
                .message
                .contains(&format!("did you mean `frob:{want}`")),
            "{typo}: {}",
            r.findings[0].message
        );
    }
}

#[test]
fn effects_record_carries_the_parsed_atom_set() {
    use gob_directives::{EffectAtom, EffectBase, effects_claim};
    let r = common::scan(
        "src/a.rs",
        "// frob:effects reads(src/x.rs::X) writes(src/y.rs::Y)\nfn a() {}\n",
    );
    assert!(r.findings.is_empty(), "{:?}", r.findings);
    let claim = effects_claim(&r.directives[0]).unwrap().unwrap();
    assert_eq!(claim.alias, None);
    let EffectBase::Atoms(atoms) = claim.set.base else {
        panic!("expected atoms");
    };
    assert!(matches!(atoms[0], EffectAtom::Reads(_)));
    assert!(matches!(atoms[1], EffectAtom::Writes(_)));
}

#[test]
fn aliases_yield_the_same_claim_as_the_long_form() {
    use gob_directives::{EffectAlias, effects_claim};
    let text = "// frob:pure\nfn a() {}\n// frob:honest\nfn b() {}\n// frob:effects none\nfn c() {}\n// frob:effects honest\nfn d() {}\n// frob:core\nfn e() {}\n";
    let r = common::scan("src/a.rs", text);
    assert!(r.findings.is_empty(), "{:?}", r.findings);
    let claims: Vec<_> = r
        .directives
        .iter()
        .filter_map(|d| effects_claim(d).map(Result::unwrap))
        .collect();
    assert_eq!(claims.len(), 4);
    assert_eq!(claims[0].set, claims[2].set);
    assert_eq!(claims[1].set, claims[3].set);
    assert_eq!(claims[0].alias, Some(EffectAlias::Pure));
    assert_eq!(claims[1].alias, Some(EffectAlias::Honest));
    assert_eq!(claims[2].alias, None);
}

#[test]
fn effect_set_errors_point_inside_the_token() {
    let text = "// frob:effects clock reads(src/a.rs::x teleport\n";
    let r = common::scan("src/a.rs", text);
    assert_eq!(r.findings[0].rule.as_str(), "PARSE001");
    let range = r.findings[0].span.unwrap().range;
    let bad = &text[range.to_usize_range()];
    assert_eq!(bad, "reads(src/a.rs::x");
}

#[test]
fn directives_config_defaults_and_scan_config() {
    use gob_directives::DirectivesConfig;
    let cfg = DirectivesConfig::default();
    assert_eq!(cfg.namespaces, ["frob", "grimble", "crunk"]);
    let scan = ScanConfig::from_config(&cfg, "grimble");
    assert_eq!(scan.namespaces, cfg.namespaces);
    assert_eq!(scan.product, "grimble");
}

#[test]
fn claim_verbs_are_registered_and_documented() {
    let verbs: Vec<_> = gob_directives::all_directives()
        .filter(|m| m.namespace == "frob")
        .map(|m| m.verb)
        .collect();
    for v in [
        "effects",
        "pure",
        "honest",
        "core",
        "shell",
        "hook",
        "dispatcher",
        "idempotent",
        "trusted",
        "calls",
    ] {
        assert!(verbs.contains(&v), "{v} missing from the registry");
    }
}

// frob:tests crates/gob-directives/src/grimble.rs::Binds
#[test]
fn grimble_binds_is_registered_and_read_only_when_the_namespace_is_honoured() {
    use gob_directives::grimble::Binds;
    let meta = all_directives()
        .find(|m| m.namespace == "grimble" && m.verb == "binds")
        .expect("grimble:binds is registered");
    assert_eq!(meta.qualified(), "grimble:binds");
    let _ = std::any::type_name::<Binds>();
    // The default scanner honours only `frob`, so a grimble directive is ignored.
    let r = common::scan("src/a.rs", "// grimble:binds design:node/a\nfn f() {}\n");
    assert!(r.directives.is_empty() && r.findings.is_empty());
}

// frob:ticket 01M3ZZXAZ39410AVYQSRSYVF9C
/// Directive count of a markdown document at `docs/a.md`.
fn md_count(text: &str) -> usize {
    let r = common::scan("docs/a.md", text);
    assert!(r.findings.is_empty(), "{:?}", r.findings);
    r.directives.len()
}

// frob:tests crates/gob-directives/src/comments.rs::segments
#[test]
fn markdown_inline_code_span_directive_is_text() {
    assert_eq!(
        md_count("# T\n\nsyntax: `<!-- frob:invariant x -->` here\n"),
        0
    );
}

// frob:tests crates/gob-directives/src/comments.rs::segments
#[test]
fn markdown_double_backtick_span_with_inner_backtick_is_text() {
    assert_eq!(md_count("# T\n\n`` a ` <!-- frob:invariant x --> ``\n"), 0);
}

// frob:tests crates/gob-directives/src/comments.rs::segments
#[test]
fn markdown_directive_right_after_code_span_counts() {
    assert_eq!(md_count("# T\n\n`code`<!-- frob:invariant x -->\n"), 1);
}

// frob:tests crates/gob-directives/src/comments.rs::segments
#[test]
fn markdown_code_span_over_line_break_is_text() {
    assert_eq!(md_count("# T\n\n`a\nx <!-- frob:invariant x --> b` c\n"), 0);
}

// frob:tests crates/gob-directives/src/comments.rs::segments
#[test]
fn markdown_escaped_backtick_does_not_open_a_span() {
    assert_eq!(md_count("# T\n\n\\`a <!-- frob:invariant x --> b`\n"), 1);
}

// frob:tests crates/gob-directives/src/comments.rs::segments
#[test]
fn markdown_fenced_block_directive_still_text() {
    assert_eq!(md_count("# T\n\n```\n<!-- frob:invariant x -->\n```\n"), 0);
}

// frob:tests crates/gob-directives/src/comments.rs::segments
#[test]
fn markdown_real_directive_beside_code_span_text_is_found() {
    let t = "# T\n\n`<!-- frob:invariant a -->`\n\n<!-- frob:invariant b -->\n";
    assert_eq!(md_count(t), 1);
}

// frob:tests crates/gob-directives/src/comments.rs::segments
#[test]
fn markdown_comment_opening_a_line_is_an_html_block_not_span_content() {
    // CommonMark: `<!--` at a line start interrupts the paragraph, so the
    // backtick never closes and the comment is a real directive.
    assert_eq!(md_count("# T\n\n`a\n<!-- frob:invariant x --> b` c\n"), 1);
}

// frob:ticket 01M40H2JYVEHBZD62WV8Z6EXFW
// frob:tests crates/gob-directives/src/scan.rs::Scanner.record
#[test]
fn tests_directive_naming_nothing_still_binds_so_test001_judges_the_symref() {
    let text = "// frob:tests src/a.rs::missing\n#[test]\nfn works() {}\n";
    let r = common::scan("src/a.rs", text);
    assert!(r.findings.is_empty(), "{:?}", r.findings);
    assert_eq!(r.directives.len(), 1);
    assert_eq!(r.directives[0].bound, sym("src/a.rs::missing"));
    assert!(r.directives[0].source.is_some());
}

const YAML_ACCEPT: &str = "# frob:accept CI006 because=\"gated by the plan job on a push run\"";

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
// frob:tests crates/gob-directives/src/bind.rs::bind
#[test]
fn yaml_accept_binds_to_the_key_on_the_next_line() {
    let text = format!("name: ci\n{YAML_ACCEPT}\non:\n  push:\n    branches: [main]\n");
    assert_eq!(
        bound(".github/workflows/dev.yml", &text),
        [sym(".github/workflows/dev.yml::on")]
    );
}

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
// frob:tests crates/gob-directives/src/bind.rs::bind
#[test]
fn yaml_stacked_comments_bind_to_the_same_key() {
    let text = format!("{YAML_ACCEPT}\n# note\n{YAML_ACCEPT}\non: push\n");
    let on = sym("ci.yml::on");
    assert_eq!(bound("ci.yml", &text), [on.clone(), on]);
}

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
// frob:tests crates/gob-directives/src/bind.rs::bind
#[test]
fn yaml_blank_line_gap_does_not_attach_to_the_next_key() {
    let text = format!("name: ci\n{YAML_ACCEPT}\n\non: push\n");
    assert_eq!(bound("ci.yml", &text), [Binding::File]);
}

// frob:ticket 01M418CXCED7DEBX4WV2PM2R2K
// frob:tests crates/gob-directives/src/bind.rs::bind
#[test]
fn yaml_trailing_comment_binds_to_its_own_key() {
    let text = "on: # frob:accept CI006 because=\"gated by the plan job on a push run\"\n  push:\n";
    assert_eq!(bound("ci.yml", text), [sym("ci.yml::on")]);
}

// frob:ticket 01M43KP0RXKB1DJA8KGJTV288R
// frob:tests crates/gob-directives/src/comments.rs::segments
#[test]
fn markdown_prose_and_front_matter_mentioning_waive_are_not_directives() {
    let waive = "frob:waive DOC006 reason=\"x\"";
    // Plain prose and an unquoted mention are text.
    assert_eq!(md_count(&format!("# T\n\nwe write {waive} in prose\n")), 0);
    // TOML and YAML front matter, including an HTML comment quoted in a string or a comment.
    for fence in ["+++", "---"] {
        let text =
            format!("{fence}\nbody = \"- <!-- {waive} -->\"\n# <!-- {waive} -->\n{fence}\n\n# T\n");
        assert_eq!(md_count(&text), 0, "front matter fenced by {fence}");
    }
    // A real HTML comment after the front matter is still a directive.
    let live = "+++\nk = 1\n+++\n\n# T\n\n<!-- frob:invariant x -->\n";
    assert_eq!(md_count(live), 1);
}
