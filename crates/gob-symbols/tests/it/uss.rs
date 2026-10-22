//! Unity UI Toolkit files end to end: USS and TSS fold as CSS (custom properties, `-unity-` properties,
//! `var()` references with fallbacks, selectors, spans) and UXML folds as case-preserving markup
//! (crunk.md section 7, language-engines.md D96).

// frob:ticket 01M4CXSBNCE06J78BM0P23V9XV

use gob_ir::{AttrValue, Location, Model, NodeId, Status, markup, style};
use gob_symbols::{ParseStatus, adapter_for_path, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

fn fold(path: &str, src: &str) -> gob_symbols::Folded {
    fold_file(&entry(path, src), src).expect("fold")
}

fn model_of(path: &str, src: &str) -> Model {
    let f = fold(path, src);
    Model::new(f.term, f.scopes)
}

fn span_text<'s>(model: &Model, node: NodeId, src: &'s str) -> &'s str {
    match model.term().node(node).location() {
        Location::Text { range, .. } => {
            &src[u32::from(range.start()) as usize..u32::from(range.end()) as usize]
        }
        other => panic!("node without a text span: {other:?}"),
    }
}

const USS: &str = "\
:root {
  --accent: #3a7bd5;
  --pad: 4px;
}
.btn.primary {
  -unity-font-style: bold;
  -unity-text-align: middle-center;
  color: var(--accent, var(--fallback));
  padding: var(--pad);
}
Label#title > .row { -unity-font: resource(\"Fonts/Main\"); width: var(--w,); }
";

#[test]
// frob:tests crates/gob-symbols/src/css/mod.rs::declaration
// frob:tests crates/gob-symbols/src/css/tokens.rs::tokens
fn uss_custom_and_unity_properties_and_var_refs_are_facts_with_spans() {
    let model = model_of("ui/Main.uss", USS);

    // Custom properties are definitions with spans.
    let defs = style::custom_properties(&model);
    assert_eq!(
        defs.iter().map(|d| d.name.as_str()).collect::<Vec<_>>(),
        ["--accent", "--pad"]
    );
    assert_eq!(span_text(&model, defs[0].node, USS), "--accent: #3a7bd5;");

    // -unity- properties are declarations flagged as USS-only; others are not.
    let decls = style::declarations(&model);
    let unity: Vec<(&str, &str)> = decls
        .iter()
        .filter(|d| {
            model.term().node(d.node).attrs().get("style.unity") == Some(&AttrValue::Bool(true))
        })
        .map(|d| (d.property.as_str(), d.raw.as_str()))
        .collect();
    assert_eq!(
        unity,
        [
            ("-unity-font-style", "bold"),
            ("-unity-text-align", "middle-center"),
            ("-unity-font", "resource(\"Fonts/Main\")"),
        ]
    );
    let color = decls.iter().find(|d| d.property == "color").expect("color");
    assert_eq!(
        span_text(&model, color.node, USS),
        "color: var(--accent, var(--fallback));"
    );

    // var() references, fallbacks included, are May refs; the empty fallback `var(--w,)` still names --w.
    let refs = style::var_refs(&model);
    assert!(refs.iter().all(|r| r.status == Status::May));
    assert_eq!(
        refs.iter().map(|r| r.name.as_str()).collect::<Vec<_>>(),
        ["--accent", "--fallback", "--pad", "--w"]
    );

    // Selectors are rules named by their text, with class selectors as nodes.
    let rules: Vec<String> = style::style_rules(&model)
        .iter()
        .map(|r| r.selector.clone())
        .collect();
    assert_eq!(rules, [":root", ".btn.primary", "Label#title > .row"]);
}

#[test]
// frob:tests crates/gob-symbols/src/css/mod.rs::is_unity_property
fn only_the_unity_prefix_marks_a_property_and_case_is_ignored() {
    let src = ".a { -UNITY-font: x; unity-font: y; --unity-x: z; color: red; }";
    let model = model_of("a.uss", src);
    let flagged: Vec<String> = style::declarations(&model)
        .into_iter()
        .filter(|d| {
            model.term().node(d.node).attrs().get("style.unity") == Some(&AttrValue::Bool(true))
        })
        .map(|d| d.property)
        .collect();
    assert_eq!(flagged, ["-UNITY-font"]);
}

#[test]
// frob:tests crates/gob-symbols/src/css/mod.rs::at_rule
fn tss_import_is_an_at_rule_and_the_registry_claims_uss_tss_uxml() {
    let src = "@import url(\"project:/Assets/UI/Base.uss\");\n.a { color: red; }\n";
    let model = model_of("Theme.tss", src);
    let ats = style::at_rules(&model);
    assert_eq!(ats.len(), 1);
    assert_eq!(ats[0].name, "import");
    assert_eq!(style::declarations(&model).len(), 1);
    assert_eq!(adapter_for_path("a/b.USS").expect("uss").language(), "css");
    assert_eq!(adapter_for_path("t.tss").expect("tss").language(), "css");
    assert_eq!(adapter_for_path("v.uxml").expect("uxml").language(), "html");
}

#[test]
// frob:tests crates/gob-symbols/src/css/mod.rs::fold_tree
fn malformed_uss_is_a_partial_parse_and_still_yields_the_good_rules() {
    let src = ".ok { color: red; }\n.bad { -unity-font: ; color: }\n.also { --x: 1px; }\n";
    let f = fold("bad.uss", src);
    assert!(matches!(f.file.parse_status, ParseStatus::Partial { .. }));
    let model = Model::new(f.term, f.scopes);
    assert!(
        style::declarations(&model)
            .iter()
            .any(|d| d.property == "color")
    );
    assert_eq!(style::custom_properties(&model).len(), 1);
}

#[test]
// frob:tests crates/gob-symbols/src/html/mod.rs::element
fn uxml_keeps_the_case_of_element_and_attribute_names() {
    let src = "<ui:UXML xmlns:ui=\"UnityEngine.UIElements\">\n  <ui:Label name=\"Title\" text=\"Hi\" class=\"a b\"/>\n</ui:UXML>\n";
    let model = model_of("Main.uxml", src);
    let els = markup::elements(&model);
    let mut tags: Vec<&str> = els.iter().filter_map(|e| e.tag.as_deref()).collect();
    tags.sort_unstable();
    assert_eq!(tags, ["ui:Label", "ui:UXML"]);
    let label = els
        .iter()
        .find(|e| e.tag.as_deref() == Some("ui:Label"))
        .expect("label");
    assert!(label.attribute("name").is_some());
    assert!(label.attribute("text").is_some());
}
