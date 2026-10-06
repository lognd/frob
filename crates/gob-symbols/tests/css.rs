//! The CSS adapter end to end: declarations with selector and at-rule chains, custom properties linked to
//! `var()` uses, and syntax errors confined to their file (language-engines.md sections 2 and 3, D96, D100).

// frob:ticket 01M43ARY26XF7A4MSRAZ8V73JM

use gob_ir::{Location, Model, NodeId, Resolution, Status, style};
use gob_symbols::{ParseStatus, adapter_for_path, extract_file, fidelity_report, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

fn model_of(src: &str) -> Model {
    let folded = fold_file(&entry("site.css", src), src).expect("fold");
    Model::new(folded.term, folded.scopes)
}

/// The names of the style rules and at-rules enclosing `node`, outermost first.
fn chain(model: &Model, node: NodeId) -> Vec<String> {
    let term = model.term();
    let mut out: Vec<String> = term
        .ancestors(node)
        .into_iter()
        .filter(|&a| {
            style::style_rules(model).iter().any(|r| r.node == a)
                || style::at_rules(model).iter().any(|r| r.node == a)
        })
        .map(|a| {
            let at = style::at_rules(model).into_iter().find(|r| r.node == a);
            match at {
                Some(r) => format!("@{} {}", r.name, r.prelude),
                None => term.node(a).name().unwrap_or_default().to_owned(),
            }
        })
        .collect();
    out.reverse();
    out
}

fn span_text<'s>(model: &Model, node: NodeId, src: &'s str) -> &'s str {
    match model.term().node(node).location() {
        Location::Text { range, .. } => {
            &src[u32::from(range.start()) as usize..u32::from(range.end()) as usize]
        }
        other => panic!("declaration without a text span: {other:?}"),
    }
}

#[test]
// frob:tests crates/gob-symbols/src/css/mod.rs::declaration
fn nested_media_declarations_report_property_value_selector_chain_and_span() {
    let src = "\
.top { margin: 0 auto; }
@media (min-width: 600px) {
  .a, .b > i {
    color: red !important;
    .inner { padding: 1px 2px; }
  }
  @supports (display: grid) {
    .c { display: grid; }
  }
}
";
    let model = model_of(src);
    let decls = style::declarations(&model);
    let got: Vec<(String, String, bool, Vec<String>)> = decls
        .iter()
        .map(|d| {
            (
                d.property.clone(),
                d.raw.clone(),
                d.important,
                chain(&model, d.node),
            )
        })
        .collect();
    let at_media = "@media (min-width: 600px)".to_owned();
    let at_sup = "@supports (display: grid)".to_owned();
    assert_eq!(
        got,
        [
            ("margin".into(), "0 auto".into(), false, vec![".top".into()]),
            (
                "color".into(),
                "red".into(),
                true,
                vec![at_media.clone(), ".a, .b > i".into()]
            ),
            (
                "padding".into(),
                "1px 2px".into(),
                false,
                vec![at_media.clone(), ".a, .b > i".into(), ".inner".into()]
            ),
            (
                "display".into(),
                "grid".into(),
                false,
                vec![at_media, at_sup, ".c".into()]
            ),
        ]
    );
    assert_eq!(
        span_text(&model, decls[1].node, src),
        "color: red !important;"
    );
    assert_eq!(decls[0].values.len(), 2);
    assert!(decls.iter().all(|d| d.owner.is_some()));
}

#[test]
// frob:tests crates/gob-symbols/src/css/mod.rs::cascade_scopes
fn var_uses_link_to_custom_property_definitions_and_undefined_ones_do_not() {
    let src = ":root { --x: #fff; --y: var(--x); }\n.a { color: var(--x); border-color: var(--nope, red); }\n.b { --x: #000; }\n";
    let model = model_of(src);
    let defs = style::custom_properties(&model);
    assert_eq!(
        defs.iter().map(|d| d.name.as_str()).collect::<Vec<_>>(),
        ["--x", "--y", "--x"]
    );
    assert_eq!(defs[0].raw, "#fff");
    let refs = style::var_refs(&model);
    assert_eq!(refs.len(), 3);
    assert!(refs.iter().all(|r| r.status == Status::May));
    let scopes = model.scopes();
    // `--x` has two definitions: a May set holding both.
    let x_use = refs.iter().find(|r| r.name == "--x").expect("--x use");
    let Resolution::May(set) = model.resolve_node(x_use.node) else {
        panic!("a defined var() resolves at May");
    };
    let def_nodes: Vec<NodeId> = set
        .iter()
        .flat_map(|&d| scopes.decl(d).nodes.clone())
        .collect();
    assert_eq!(def_nodes, vec![defs[0].node, defs[2].node]);
    // `--nope` has no definition, hence no definition edge.
    let nope = refs.iter().find(|r| r.name == "--nope").expect("--nope");
    assert_eq!(model.resolve_node(nope.node), Resolution::Unknown);
}

#[test]
// frob:tests crates/gob-symbols/src/css/mod.rs::hole
fn a_syntax_error_is_a_partial_parse_and_other_files_are_unaffected() {
    let bad = "a { color: ;; { \n";
    let good = "a { color: red; }\n";
    let bad_f = extract_file(&entry("bad.css", bad), bad);
    let good_f = extract_file(&entry("good.css", good), good);
    assert!(
        matches!(bad_f.parse_status, ParseStatus::Partial { holes } if holes > 0),
        "{:?}",
        bad_f.parse_status
    );
    assert_eq!(good_f.parse_status, ParseStatus::Complete);
    assert_eq!(good_f.language, "css");
}

#[test]
// frob:tests crates/gob-symbols/src/registry.rs::adapter_for
fn the_registry_claims_css_files_and_reports_the_adapter() {
    assert_eq!(
        adapter_for_path("web/Site.CSS").map(gob_symbols::Adapter::language),
        Some("css")
    );
    assert!(fidelity_report().iter().any(|r| r.language == "css"));
}

#[test]
// frob:tests crates/gob-symbols/src/css/mod.rs::at_rule
fn at_rules_carry_name_and_prelude_and_keyframes_are_rules() {
    let src = "@import url(\"a.css\") screen;\n@layer base, theme;\n@font-face { font-family: X; }\n@keyframes spin { from { opacity: 0; } 50% { opacity: .5; } }\n";
    let model = model_of(src);
    let got: Vec<(String, String)> = style::at_rules(&model)
        .into_iter()
        .map(|a| (a.name, a.prelude))
        .collect();
    assert_eq!(
        got,
        [
            ("import".to_owned(), "url(\"a.css\") screen".to_owned()),
            ("layer".to_owned(), "base, theme".to_owned()),
            ("font-face".to_owned(), String::new()),
            ("keyframes".to_owned(), "spin".to_owned()),
        ]
    );
    let rules: Vec<String> = style::style_rules(&model)
        .into_iter()
        .map(|r| r.selector)
        .collect();
    assert_eq!(rules, ["from", "50%"]);
    assert_eq!(style::declarations(&model).len(), 3);
}

#[test]
// frob:tests crates/gob-symbols/src/css/mod.rs::fold_tree
fn the_cached_payload_round_trips() {
    let src = "a { color: red; }\n@media print { .b, .c > i { --x: 1; } }\n";
    let fs = extract_file(&entry("a.css", src), src);
    let bytes = postcard::to_allocvec(&fs).expect("encode");
    let back: gob_symbols::FileSymbols = postcard::from_bytes(&bytes).expect("decode");
    assert_eq!(back.path, fs.path);
    assert_eq!(back.symbols.len(), fs.symbols.len());
    let names: Vec<String> = back.symbols.iter().map(|s| s.symref.to_string()).collect();
    assert_eq!(
        names,
        [
            "a.css::a",
            "a.css::media",
            "a.css::media.[.b,_.c_>_i]",
            "a.css::media.[.b,_.c_>_i].--x"
        ]
    );
}
