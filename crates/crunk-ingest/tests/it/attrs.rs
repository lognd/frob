//! Tests for the file attributes stamped from ingest (bucket, component, outside `css_root`).

// frob:ticket 01M70RNZ00HMGWP284A0ZD14NZ

use crate::common;

use common::synthetic;
use crunk_ingest::{
    FILE_BUCKET_ATTR, FILE_COMPONENT_ATTR, OUTSIDE_CSS_ROOT_ATTR, ingest_tree, outside_attrs,
    sheet_attrs,
};
use gob_cache::Cache;

const CSS: &str = ".a { margin: 3px; }\n";

fn get<'a>(attrs: &'a [(&'static str, String)], name: &str) -> &'a str {
    attrs.iter().find(|(n, _)| *n == name).unwrap().1.as_str()
}

fn attrs_of(files: &[(&str, &str)], file: &str) -> Vec<(&'static str, String)> {
    let (_dir, spec) = synthetic(files);
    let got = ingest_tree(&spec, &Cache::null()).unwrap();
    let sheet = got
        .styles
        .sheets
        .iter()
        .find(|s| s.path.ends_with(file))
        .unwrap();
    sheet_attrs(sheet)
}

// frob:tests crates/crunk-ingest/src/attrs.rs::sheet_attrs
#[test]
fn a_component_sheet_stamps_its_bucket() {
    let attrs = attrs_of(&[("styles/components/card.css", CSS)], "card.css");
    assert_eq!(get(&attrs, FILE_BUCKET_ATTR), "components");
}

// frob:tests crates/crunk-ingest/src/attrs.rs::sheet_attrs
#[test]
fn a_component_sheet_stamps_its_stem_as_component() {
    let attrs = attrs_of(&[("styles/components/card.css", CSS)], "card.css");
    assert_eq!(get(&attrs, FILE_COMPONENT_ATTR), "card");
}

// frob:tests crates/crunk-ingest/src/attrs.rs::sheet_attrs
#[test]
fn a_base_sheet_stamps_an_empty_component() {
    let attrs = attrs_of(&[("styles/base/a.css", CSS)], "a.css");
    assert_eq!(get(&attrs, FILE_COMPONENT_ATTR), "");
}

// frob:tests crates/crunk-ingest/src/attrs.rs::sheet_attrs
#[test]
fn a_stray_sheet_under_css_root_stamps_an_empty_bucket() {
    let attrs = attrs_of(&[("styles/loose/a.css", CSS)], "a.css");
    assert_eq!(get(&attrs, FILE_BUCKET_ATTR), "");
}

// frob:tests crates/crunk-ingest/src/attrs.rs::sheet_attrs
#[test]
fn a_sheet_under_css_root_is_not_outside() {
    let attrs = attrs_of(&[("styles/base/a.css", CSS)], "a.css");
    assert_eq!(get(&attrs, OUTSIDE_CSS_ROOT_ATTR), "false");
}

// frob:tests crates/crunk-ingest/src/attrs.rs::outside_attrs
#[test]
fn an_ungoverned_file_is_outside_css_root() {
    assert_eq!(get(&outside_attrs(), OUTSIDE_CSS_ROOT_ATTR), "true");
}

// frob:tests crates/crunk-ingest/src/attrs.rs::outside_attrs
#[test]
fn an_ungoverned_file_has_no_bucket_or_component() {
    let attrs = outside_attrs();
    assert_eq!(get(&attrs, FILE_BUCKET_ATTR), "");
    assert_eq!(get(&attrs, FILE_COMPONENT_ATTR), "");
}
