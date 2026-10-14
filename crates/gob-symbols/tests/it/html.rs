//! The HTML adapter end to end: markup elements and attributes through the shared `gob_ir::markup`
//! queries, inline style declarations, script and style region islands, partial parses and the
//! capability matrix row (language-engines.md sections 2 and 3, D96, D101).

// frob:ticket 01M47QKT10CG0RSF784EEYTQ0J

use std::fmt::Write as _;

use gob_ir::const_value::{ConstValue, Value};
use gob_ir::{Model, Operator, Universal, markup, style};
use gob_symbols::{ParseStatus, adapter_for_path, fidelity_report, fold_file};
use gob_walk::{Digest, FileEntry, LanguageHint};

fn entry(path: &str, text: &str) -> FileEntry {
    FileEntry {
        path: path.to_owned(),
        size: text.len() as u64,
        digest: Digest::of(text.as_bytes()),
        language: LanguageHint::from_path(path),
    }
}

fn fold(src: &str) -> gob_symbols::Folded {
    fold_file(&entry("site/index.html", src), src).expect("fold")
}

fn model_of(src: &str) -> (Model, gob_symbols::Folded) {
    let folded = fold(src);
    (
        Model::new(folded.term.clone(), folded.scopes.clone()),
        folded,
    )
}

fn show_value(v: &ConstValue) -> String {
    match v {
        ConstValue::Known(Value::Str(s)) => format!("{s:?}"),
        ConstValue::Known(Value::Bool(b)) => b.to_string(),
        ConstValue::Unknown => "?".to_owned(),
        other => format!("{other:?}"),
    }
}

/// One line per element: tag, kind, attributes with their `const_value`, then children.
fn render_markup(model: &Model) -> String {
    let mut out = String::new();
    for e in markup::elements(model) {
        let attrs: Vec<String> = e
            .attributes
            .iter()
            .map(|a| match &a.name {
                Some(n) => format!("{n}={}", show_value(&markup::attribute_value(model, a))),
                None => "...spread".to_owned(),
            })
            .collect();
        let kids: Vec<String> = e
            .children
            .iter()
            .map(|c| match c {
                markup::Child::Text(t) => format!("text:{t:?}"),
                markup::Child::Element(_) => "element".to_owned(),
                markup::Child::Expr(_) => "expr".to_owned(),
            })
            .collect();
        let _ = writeln!(
            out,
            "{} {:?} [{}] ({})",
            e.tag.as_deref().unwrap_or("?"),
            e.kind,
            attrs.join(" "),
            kids.join(" ")
        );
    }
    out
}

const PAGE: &str = r#"<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Home &amp; away</title>
  <!-- a comment -->
  <style>.card { color: var(--ink); }</style>
</head>
<BODY class="page  dark" data-x='1'>
  <a href="/x?a=1&amp;b=2" target=_blank DISABLED>Go <b>now</b></a>
  <input type="text" value="">
  <my-card>hi</my-card>
  <script type="module">import './a.js';</script>
</BODY>
</html>
"#;

#[test]
// frob:tests crates/gob-symbols/src/html/mod.rs::element
fn html_elements_answer_the_markup_queries_with_expected_snapshot() {
    let (model, folded) = model_of(PAGE);
    assert_eq!(folded.file.parse_status, ParseStatus::Complete);
    assert_eq!(folded.file.language, "html");
    insta::assert_snapshot!(render_markup(&model), @r#"
    meta Intrinsic [charset="utf-8"] ()
    title Intrinsic [] (text:"Home & away")
    style Intrinsic [] (expr)
    head Intrinsic [] (element element element)
    b Intrinsic [] (text:"now")
    a Intrinsic [href="/x?a=1&b=2" target="_blank" disabled=true] (text:"Go" element)
    input Intrinsic [type="text" value=""] ()
    my-card Intrinsic [] (text:"hi")
    script Intrinsic [type="module"] (expr)
    body Intrinsic [class="page  dark" data-x="1"] (element element element element)
    html Intrinsic [lang="en"] (element element)
    "#);
}

#[test]
// frob:tests crates/gob-symbols/src/html/mod.rs::island
fn script_and_style_elements_are_region_islands_with_language_tags() {
    let src = "<style>a{color:red}</style><script>var x = 1;</script>\
<script type=\"module\">import 'a';</script><script lang=\"ts\">let y: number;</script>\
<script type=\"application/ld+json\">{\"a\":1}</script><script type=\"text/template\"><p></p></script>\
<script src=\"x.js\"></script>";
    let folded = fold(src);
    let t = &folded.term;
    let regions: Vec<(String, String)> = t
        .ids()
        .filter_map(|id| match t.operator(id) {
            Operator::Universal(Universal::Region { kind }) => {
                let body = match t.operator(t.node(id).children()[0]) {
                    Operator::Universal(Universal::Lit { lexeme, .. }) => lexeme.clone(),
                    other => panic!("island body: {other:?}"),
                };
                Some((kind.clone(), body))
            }
            _ => None,
        })
        .collect();
    let kinds: Vec<&str> = regions.iter().map(|(k, _)| k.as_str()).collect();
    assert_eq!(kinds, ["css", "js", "js", "ts", "json", "data"]);
    assert_eq!(regions[0].1, "a{color:red}");
    assert_eq!(regions[1].1, "var x = 1;");
    // A script with only `src` has no body, hence no island.
    assert_eq!(regions.len(), 6);
}

#[test]
// frob:tests crates/gob-symbols/src/html/mod.rs::inline_style
fn inline_style_attributes_lower_to_declarations() {
    let src = "<div style=\"Color: red; margin:0 auto !important; border: 1px solid var(--line);--gap: 4px; bad\" id=a></div>";
    let (model, _) = model_of(src);
    let got: Vec<(String, String, bool, usize)> = style::declarations(&model)
        .iter()
        .map(|d| {
            (
                d.property.clone(),
                d.raw.clone(),
                d.important,
                d.values.len(),
            )
        })
        .collect();
    assert_eq!(
        got,
        [
            ("color".to_owned(), "red".to_owned(), false, 1),
            ("margin".to_owned(), "0 auto".to_owned(), true, 2),
            (
                "border".to_owned(),
                "1px solid var(--line)".to_owned(),
                false,
                3
            ),
            ("--gap".to_owned(), "4px".to_owned(), false, 1),
        ]
    );
    let vars = style::var_refs(&model);
    assert_eq!(vars.len(), 1);
    assert_eq!(vars[0].name, "--line");
    let el = &markup::elements(&model)[0];
    assert!(el.attribute("style").is_some());
    assert_eq!(
        markup::attribute_value(&model, el.attribute("id").expect("id")),
        ConstValue::Known(Value::Str("a".into()))
    );
}

#[test]
// frob:tests crates/gob-symbols/src/html/mod.rs::attribute
fn class_tokens_read_the_class_attribute() {
    let (model, _) = model_of("<p class=\"a  b c\"></p>");
    let el = &markup::elements(&model)[0];
    let tokens = markup::element_class_tokens(&model, el);
    let got: Vec<&str> = tokens.must().collect();
    assert_eq!(got, ["a", "b", "c"]);
    assert!(tokens.is_complete());
}

#[test]
// frob:tests crates/gob-symbols/src/html/mod.rs::fold_tree
fn syntax_errors_are_a_partial_parse() {
    let folded = fold("<div><p>ok</p></span><b>x</b></div>");
    assert!(matches!(
        folded.file.parse_status,
        ParseStatus::Partial { .. }
    ));
    let (model, _) = model_of("<div><p>ok</p></span><b>x</b></div>");
    let tags: Vec<_> = markup::elements(&model)
        .into_iter()
        .filter_map(|e| e.tag)
        .collect();
    assert_eq!(tags, ["p", "b", "div"]);
}

#[test]
// frob:tests crates/gob-symbols/src/html/mod.rs::HtmlAdapter
fn the_capability_matrix_has_an_html_row() {
    assert_eq!(
        adapter_for_path("a/Index.HTM").map(gob_symbols::Adapter::language),
        Some("html")
    );
    assert_eq!(
        adapter_for_path("a/index.html").map(gob_symbols::Adapter::language),
        Some("html")
    );
    let report = fidelity_report();
    let row = report
        .iter()
        .find(|r| r.language == "html")
        .expect("html row");
    assert_eq!(row.extensions, ["html", "htm"]);
    assert!(
        row.identity.contains("tree-sitter-html@0.23.2"),
        "{}",
        row.identity
    );
    assert!(!row.capabilities.is_empty());
}
