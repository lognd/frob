//! Scene dialect parsing and SCENE001.

// frob:ticket 01M4CXRDTCFVJ4VPZKAJ22BXS0

use crunk_scene::{
    ElementKind, SceneError, parse_scene_bytes, parse_scene_html, unsupported_properties,
};

fn flagged(html: &str) -> Vec<String> {
    let doc = parse_scene_html(html).expect("parses");
    unsupported_properties(&doc)
        .into_iter()
        .map(|f| f.property)
        .collect()
}

// frob:tests unsupported_properties
#[test]
fn unsupported_property_is_named() {
    let doc = parse_scene_html("<div data-id=\"a\" style=\"display:flex; float:left\"></div>")
        .expect("parses");
    let found = unsupported_properties(&doc);
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].property, "float");
    assert!(found[0].message.contains("float"));
    assert_eq!(found[0].line, 1);
}

// frob:tests unsupported_properties
#[test]
fn supported_properties_are_clean() {
    assert!(
        flagged("<div style=\"display:grid; gap:4px; padding:2px; aspect-ratio:1\"></div>")
            .is_empty()
    );
}

// frob:tests unsupported_properties
#[test]
fn shorthand_is_judged_by_its_name() {
    assert_eq!(
        flagged("<div style=\"background:red; padding:1px 2px\"></div>"),
        ["background"]
    );
}

// frob:tests unsupported_properties
#[test]
fn vendor_prefix_is_flagged() {
    assert_eq!(
        flagged("<div style=\"-webkit-box-shadow:none\"></div>"),
        ["-webkit-box-shadow"]
    );
}

// frob:tests unsupported_properties
#[test]
fn custom_property_is_allowed() {
    assert!(flagged("<style>:root{--space-4:16px}.a{padding:var(--space-4)}</style>").is_empty());
}

// frob:tests unsupported_properties
#[test]
fn at_rule_contents_are_checked() {
    let doc =
        parse_scene_html("<style>@media (min-width:1px){.a{float:left}}</style>").expect("parses");
    assert_eq!(unsupported_properties(&doc)[0].property, "float");
    assert_eq!(doc.at_rules, ["media"]);
}

// frob:tests parse_scene_html
#[test]
fn unknown_tag_is_classified() {
    let doc = parse_scene_html("<blink data-id=\"x\"></blink><div></div>").expect("parses");
    assert_eq!(doc.elements[0].kind, ElementKind::Unknown);
    assert_eq!(doc.elements[1].kind, ElementKind::Html);
}

// frob:tests SceneDoc.duplicate_data_ids
#[test]
fn duplicate_data_ids_are_reported() {
    let doc =
        parse_scene_html("<div data-id=\"a\"></div><p data-id=\"a\"></p><p data-id=\"b\"></p>")
            .expect("parses");
    assert_eq!(doc.duplicate_data_ids(), ["a"]);
}

// frob:tests parse_scene_html
#[test]
fn nested_components_keep_case_and_parent() {
    let doc = parse_scene_html(
        "<Card data-id=\"c\">\n  <Button data-id=\"b\" variant=\"primary\"></Button>\n</Card>",
    )
    .expect("parses");
    assert_eq!(doc.components().count(), 2);
    assert_eq!(doc.elements[0].tag, "Card");
    assert_eq!(doc.elements[1].tag, "Button");
    assert_eq!(doc.elements[1].parent, Some(0));
    assert_eq!(doc.elements[1].data_id.as_deref(), Some("b"));
    assert_eq!(doc.elements[1].line, 2);
    assert_eq!(
        doc.elements[1].attributes,
        [("variant".to_owned(), "primary".to_owned())]
    );
}

// frob:tests parse_scene_html
#[test]
fn empty_input_is_an_empty_scene() {
    assert!(parse_scene_html("").expect("parses").elements.is_empty());
    assert!(
        parse_scene_html("  \n\t ")
            .expect("parses")
            .declarations
            .is_empty()
    );
}

// frob:tests parse_scene_bytes
#[test]
fn non_utf8_is_an_error() {
    assert_eq!(
        parse_scene_bytes(b"<div>\xff</div>"),
        Err(SceneError::NotUtf8 { offset: 5 })
    );
    assert!(parse_scene_bytes(b"<div></div>").is_ok());
}

// frob:tests unsupported_properties
#[test]
fn odd_whitespace_and_comments() {
    let html = "<!-- c -->\r\n<style>\r\n\t/* x */ .a {\r\n\u{a0}float : left ;\r\n}</style>";
    let doc = parse_scene_html(html).expect("parses");
    let found = unsupported_properties(&doc);
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].property, "float");
    assert_eq!(found[0].line, 4);
}

// frob:tests unsupported_properties
#[test]
fn style_block_and_inline_both_checked() {
    assert_eq!(
        flagged("<style>.a{float:left}</style><div style=\"clear:both\"></div>"),
        ["float", "clear"]
    );
}

// frob:ticket 01M4CXR96GDDX460SZZVAAWD0R
// frob:tests parse_scene_html
#[test]
fn element_text_keeps_own_runs_and_skips_style_bodies() {
    let doc = parse_scene_html(
        "<style>.a { color: red }</style><div data-id=\"a\">  Hello\n   world <b>bold</b></div><p data-id=\"e\">   </p>",
    )
    .expect("parses");
    let a = doc
        .elements
        .iter()
        .find(|e| e.data_id.as_deref() == Some("a"))
        .expect("a");
    assert_eq!(a.text, ["Hello world"]);
    let b = doc.elements.iter().find(|e| e.tag == "b").expect("b");
    assert_eq!(b.text, ["bold"]);
    let e = doc
        .elements
        .iter()
        .find(|e| e.data_id.as_deref() == Some("e"))
        .expect("e");
    assert!(e.text.is_empty());
    let style = doc
        .elements
        .iter()
        .find(|e| e.tag == "style")
        .expect("style");
    assert!(style.text.is_empty());
}
