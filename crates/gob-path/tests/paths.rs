//! Property tests for the host bridges in both path styles, run on any host.
// frob:ticket 01M41S1KC8PQFTVDETMARHP82G

use gob_path::{PathError, PathStyle, RelPath, Shown, exact_text, validate_component};
use proptest::prelude::*;
use std::path::Path;

fn name() -> impl Strategy<Value = String> {
    "[A-Za-z0-9_-][A-Za-z0-9_-]{0,6}(\\.[a-z]{1,3})?"
        .prop_filter("reserved", |n| validate_component(n).is_ok() && n != ".git")
}

// frob:accept PATH001 because="path-style properties are tested on literal Windows and Unix paths from any host"
fn win_root() -> impl Strategy<Value = String> {
    prop_oneof![
        Just(r"C:\work\repo".to_owned()),
        Just(r"D:/mixed/Repo".to_owned()),
        Just(r"\\server\share\repo".to_owned()),
        Just(r"c:\".to_owned()),
    ]
}

// frob:tests prop_windows_roundtrip
#[test]
fn prop_windows_roundtrip() {
    proptest!(|(root in win_root(), names in prop::collection::vec(name(), 1..5), upper in any::<bool>())| {
        let rel = RelPath::new(names.join("/")).unwrap();
        let full = rel.to_host_style(PathStyle::Windows, &root);
        let probe = if upper { root.to_uppercase() } else { root.clone() };
        let got = RelPath::from_host_style(PathStyle::Windows, &probe, &full).unwrap();
        prop_assert_eq!(&got, &rel);
        prop_assert!(!got.as_str().contains('\\'));
        prop_assert_eq!(got.to_host_style(PathStyle::Windows, &root), full);});
}

// frob:tests prop_unix_roundtrip
#[test]
fn prop_unix_roundtrip() {
    proptest!(|(names in prop::collection::vec(name(), 1..5), root in prop_oneof![Just("/".to_owned()), Just("/a/b".to_owned())])| {
        let rel = RelPath::new(names.join("/")).unwrap();
        let full = rel.to_host_style(PathStyle::Unix, &root);
        let got = RelPath::from_host_style(PathStyle::Unix, &root, &full).unwrap();
        prop_assert_eq!(&got, &rel);
        prop_assert_eq!(got.to_host_style(PathStyle::Unix, &root), full);
        let host = rel.to_host(Path::new("/r"));
        if cfg!(unix) { prop_assert_eq!(RelPath::from_host(Path::new("/r"), &host).ok(), Some(rel)); }});
}

// frob:tests prop_invalid_component_refused
#[test]
fn prop_invalid_component_refused() {
    proptest!(|(bad in prop_oneof![
        Just("con".to_owned()), Just("NUL.txt".to_owned()), Just("com1".to_owned()), Just("a:b".to_owned()),
        Just("x?".to_owned()), Just("dir.".to_owned()), Just("sp ".to_owned()), Just("a|b".to_owned()),
    ])| {
        match RelPath::from_host_style(PathStyle::Unix, "/r", &format!("/r/ok/{bad}")) {
            Err(PathError::BadComponent { component, platform, .. }) => {
                prop_assert_eq!(component, bad);
                prop_assert_eq!(platform, "windows");
            }
            other => prop_assert!(false, "{:?}", other),
        }});
}

// frob:tests outside_and_dotdot_refused
#[test]
// frob:accept PATH001 because="path-style properties are tested on literal Windows and Unix paths from any host"
fn outside_and_dotdot_refused() {
    for (s, r, p) in [
        (PathStyle::Windows, r"C:\a", r"D:\a\b"),
        (PathStyle::Windows, r"C:\a", r"C:\a"),
        (PathStyle::Windows, r"C:\a", r"C:\a\..\b"),
        (PathStyle::Windows, r"C:\a", r"C:\ab\c"),
        (PathStyle::Unix, "/a", "/ab/c"),
        (PathStyle::Unix, "/a", "/a/../b"),
    ] {
        assert!(
            matches!(
                RelPath::from_host_style(s, r, p),
                Err(PathError::Outside { .. })
            ),
            "{r} {p}"
        );
    }
    assert!(RelPath::from_host_style(PathStyle::Unix, "/a", r"/a/b\c").is_err());
}

// frob:tests shown_scrubs_home
#[test]
// frob:accept PATH001 because="path-style properties are tested on literal Windows and Unix paths from any host"
fn shown_scrubs_home() {
    let home = Path::new("/home/u");
    assert_eq!(
        Shown::with_home(Path::new("/home/u/p/x"), Some(home)).as_str(),
        "~/p/x"
    );
    assert_eq!(
        Shown::with_home(Path::new("/home/u"), Some(home)).as_str(),
        "~"
    );
    assert_eq!(
        Shown::with_home(Path::new("/home/ux/p"), Some(home)).as_str(),
        "/home/ux/p"
    );
}

// frob:tests exact_text
#[test]
// frob:accept PATH001 because="path-style properties are tested on literal Windows and Unix paths from any host"
fn exact_text_is_verbatim_or_none() {
    assert_eq!(exact_text(Path::new("/a/b")), Some("/a/b"));
    assert_eq!(exact_text(Path::new("")), Some(""));
    assert_eq!(exact_text(Path::new("a/")), Some("a/"));
    assert_eq!(exact_text(std::ffi::OsStr::new("name")), Some("name"));
    assert_eq!(exact_text(Path::new("C:\\x\\y")), Some("C:\\x\\y"));
}

// frob:tests exact_text
#[cfg(unix)]
#[test]
fn exact_text_refuses_non_unicode() {
    use std::os::unix::ffi::OsStrExt;
    let bad = std::ffi::OsStr::from_bytes(b"a/\xff");
    assert_eq!(exact_text(bad), None);
}

// frob:ticket 01M5PC8KZJ95RRS27B5DV06D9X
// frob:tests crates/gob-path/src/shown.rs::forward_slashes
#[test]
fn forward_slashes_turns_backslashes_into_slashes() {
    assert_eq!(
        gob_path::forward_slashes(Path::new("a\\b/c")),
        "a/b/c".to_owned()
    );
}
