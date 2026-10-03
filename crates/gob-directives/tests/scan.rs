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

#[test]
fn binds_to_fn_two_lines_later() {
    let text = format!("// frob:ticket {ID}\n\nfn target() {{}}\n");
    assert_eq!(bound("src/a.rs", &text), [sym("src/a.rs::target")]);
}

#[test]
fn binds_to_adjacent_fn_and_doc_comment_form() {
    let text = format!("/// frob:ticket {ID}\nfn target() {{}}\n");
    assert_eq!(bound("src/a.rs", &text), [sym("src/a.rs::target")]);
}

#[test]
fn three_lines_away_is_not_following() {
    let text = format!("// frob:ticket {ID}\n\n\nfn target() {{}}\n");
    assert_eq!(bound("src/a.rs", &text), [Binding::File]);
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
    assert!(f.message.contains("frob ticket expand"));
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
