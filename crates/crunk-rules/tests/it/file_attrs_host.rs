//! The file attributes the host stamps for GRL: component sheet, base sheet, outside file.

// frob:ticket 01M70VN3RSMK4QGY4XCNBAN5SY

use std::path::PathBuf;

use crunk_ingest::{Bucket, ProjectStyles, Stylesheet};
use crunk_rules::CrunkHost;
use crunk_rules::file_attrs::{StampedFile, host_stamped_files, stamp_styles};

struct Host(ProjectStyles);

impl CrunkHost for Host {
    fn styles(&self) -> Option<&ProjectStyles> {
        Some(&self.0)
    }
}

struct Bare;
impl CrunkHost for Bare {}

fn sheet(path: &str, bucket: Option<Bucket>, component: Option<&str>) -> Stylesheet {
    Stylesheet {
        path: PathBuf::from(path),
        bucket,
        component: component.map(str::to_owned),
        source: String::new(),
        declarations: vec![],
        class_selectors: vec![],
        custom_props: vec![],
        orphan_waivers: vec![],
        media_queries: vec![],
        utilities: vec![],
        dynamic_classes: vec![],
    }
}

fn attr<'a>(file: &'a StampedFile, name: &str) -> &'a str {
    file.attrs
        .iter()
        .find(|(n, _)| *n == name)
        .map(|(_, v)| v.as_str())
        .expect("attribute stamped")
}

fn styles() -> ProjectStyles {
    ProjectStyles {
        sheets: vec![
            sheet(
                "css/components/card.css",
                Some(Bucket::Components),
                Some("card"),
            ),
            sheet("css/base/reset.css", Some(Bucket::Base), None),
        ],
        ungoverned: vec![PathBuf::from("vendor/x.css")],
        ..Default::default()
    }
}

// frob:tests crates/crunk-rules/src/file_attrs.rs::stamp_styles
#[test]
fn a_component_sheet_carries_bucket_and_component() {
    let files = stamp_styles(&styles());
    assert_eq!(
        (
            attr(&files[0], "file.bucket"),
            attr(&files[0], "file.component"),
            attr(&files[0], "file.outside_css_root"),
        ),
        ("components", "card", "false")
    );
}

// frob:tests crates/crunk-rules/src/file_attrs.rs::stamp_styles
#[test]
fn a_base_sheet_has_a_bucket_and_no_component() {
    let files = stamp_styles(&styles());
    assert_eq!(
        (
            attr(&files[1], "file.bucket"),
            attr(&files[1], "file.component")
        ),
        ("base", "")
    );
}

// frob:tests crates/crunk-rules/src/file_attrs.rs::stamp_styles
#[test]
fn an_ungoverned_file_is_flagged_outside_css_root() {
    let files = stamp_styles(&styles());
    assert_eq!(attr(&files[2], "file.outside_css_root"), "true");
}

// frob:tests crates/crunk-rules/src/file_attrs.rs::host_stamped_files
#[test]
fn the_host_offers_the_stamped_files_of_its_styles() {
    assert_eq!(host_stamped_files(&Host(styles())).len(), 3);
}

// frob:tests crates/crunk-rules/src/file_attrs.rs::host_stamped_files
#[test]
fn a_host_without_styles_offers_no_files() {
    assert!(host_stamped_files(&Bare).is_empty());
}
