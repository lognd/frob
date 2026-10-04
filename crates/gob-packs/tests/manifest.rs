//! Acceptance and robustness tests for the pack manifest.

use gob_packs::{Manifest, PackCode, PackError, check_unique, load};
use proptest::prelude::*;

const EXAMPLE: &str = r#"
[pack]
name = "py-safety"
version = "1.2.0"
families = ["PYS"]
needs = { grimble = ">=2.0", u = "1" }

[provides]
atoms = "atoms.toml"
templates = "templates.toml"
rules = ["rules/*.grl"]
wasm = []
adapters = []

[effects]
"#;

fn with_family(name: &str, fam: &str) -> String {
    format!("[pack]\nname = \"{name}\"\nversion = \"1.0.0\"\nfamilies = [\"{fam}\"]\n")
}

// frob:tests crates/gob-packs/src/manifest.rs::Manifest.parse
#[test]
fn example_manifest_loads_typed() {
    let m = Manifest::parse("pack.toml", EXAMPLE).unwrap();
    assert_eq!(m.pack.name, "py-safety");
    assert_eq!(m.pack.version, "1.2.0");
    assert_eq!(m.pack.families, ["PYS"]);
    assert_eq!(m.pack.needs["grimble"], ">=2.0");
    assert_eq!(m.pack.needs["u"], "1");
    assert_eq!(m.provides.atoms.as_deref(), Some("atoms.toml"));
    assert_eq!(m.provides.rules, ["rules/*.grl"]);
    assert!(m.provides.wasm.is_empty() && m.provides.adapters.is_empty());
    assert!(m.effects.is_empty());
}

// frob:tests crates/gob-packs/src/manifest.rs::check_unique
#[test]
fn duplicate_family_is_pack004_naming_both() {
    let a = Manifest::parse("a/pack.toml", &with_family("one", "PYS")).unwrap();
    let b = Manifest::parse("b/pack.toml", &with_family("two", "PYS")).unwrap();
    let err = check_unique(&[("a/pack.toml", &a), ("b/pack.toml", &b)]).unwrap_err();
    assert_eq!(err.code(), PackCode::Pack004);
    let s = err.to_string();
    assert!(
        s.contains("PYS") && s.contains("a/pack.toml") && s.contains("b/pack.toml"),
        "{s}"
    );
}

// frob:tests crates/gob-packs/src/manifest.rs::check_unique
#[test]
fn duplicate_name_is_pack004() {
    let a = Manifest::parse("a.toml", &with_family("same", "AA")).unwrap();
    let b = Manifest::parse("b.toml", &with_family("same", "BB")).unwrap();
    assert!(matches!(
        check_unique(&[("a.toml", &a), ("b.toml", &b)]),
        Err(PackError::DuplicateName { .. })
    ));
}

// frob:tests crates/gob-packs/src/manifest.rs::Manifest.parse
#[test]
fn unknown_key_is_pack005_naming_file_key_line() {
    for text in [
        "[pack]\nname = \"x\"\nversion = \"1.0.0\"\ncolour = \"red\"\n",
        "[pack]\nname = \"x\"\nversion = \"1.0.0\"\n[bogus]\n",
        "[pack]\nname = \"x\"\nversion = \"1.0.0\"\n[provides]\nrulez = []\n",
    ] {
        let err = Manifest::parse("p/pack.toml", text).unwrap_err();
        assert_eq!(err.code(), PackCode::Pack005);
        let s = err.to_string();
        assert!(s.contains("p/pack.toml"), "{s}");
    }
    let err = Manifest::parse(
        "p/pack.toml",
        "[pack]\nname = \"x\"\nversion = \"1.0.0\"\ncolour = \"red\"\n",
    )
    .unwrap_err();
    match err {
        PackError::Malformed { key, line, .. } => {
            assert_eq!(key, "colour");
            assert_eq!(line, Some(4));
        }
        other => panic!("{other}"),
    }
}

// frob:tests crates/gob-packs/src/manifest.rs::Manifest.parse
#[test]
fn bounds_and_shapes_are_refused() {
    let bad = [
        "[pack]\nname = \"Bad_Name\"\nversion = \"1.0.0\"\n",
        "[pack]\nname = \"x\"\nversion = \"^1.0\"\n",
        "[pack]\nname = \"x\"\nversion = \"1.0.0\"\nfamilies = [\"pys\"]\n",
        "[pack]\nname = \"x\"\nversion = \"1.0.0\"\nfamilies = [\"PYS\", \"PYS\"]\n",
        "[pack]\nname = \"x\"\nversion = \"1.0.0\"\n[provides]\nrules = [\"../x\"]\n",
        "[pack]\nname = \"x\"\nversion = \"1.0.0\"\n[provides]\nrules = [\"/etc\"]\n",
        "[pack]\nname = \"x\"\nversion = \"1.0.0\"\n# caf\u{e9}\n",
        "[pack]\nname = \"x\"\n",
        "",
        "[effects]\nfs = \"yes\"\n",
    ];
    for t in bad {
        let e = Manifest::parse("m", t).unwrap_err();
        assert_eq!(e.code(), PackCode::Pack005, "{t}");
    }
    let huge = format!(
        "[pack]\nname = \"x\"\nversion = \"1.0.0\"\n# {}\n",
        "a".repeat(70_000)
    );
    assert!(Manifest::parse("m", &huge).is_err());
    let many = format!(
        "[pack]\nname = \"x\"\nversion = \"1.0.0\"\n[provides]\nrules = [{}]\n",
        vec!["\"a\""; 300].join(",")
    );
    assert!(Manifest::parse("m", &many).is_err());
}

// frob:tests crates/gob-packs/src/manifest.rs::load
#[test]
fn load_reads_a_file_and_refuses_oversize_or_binary() {
    let dir = tempfile::tempdir().unwrap();
    let ok = dir.path().join("pack.toml");
    std::fs::write(&ok, EXAMPLE).unwrap();
    assert_eq!(load(&ok).unwrap().pack.name, "py-safety");
    let big = dir.path().join("big.toml");
    std::fs::write(&big, vec![b'#'; 200_000]).unwrap();
    assert_eq!(load(&big).unwrap_err().code(), PackCode::Pack005);
    let bin = dir.path().join("bin.toml");
    std::fs::write(&bin, [0xff, 0xfe, 0x00]).unwrap();
    assert_eq!(load(&bin).unwrap_err().code(), PackCode::Pack005);
    assert_eq!(
        load(&dir.path().join("missing")).unwrap_err().code(),
        PackCode::Pack005
    );
}

proptest! {
    #[test]
    fn arbitrary_text_never_panics(text in "\\PC{0,400}") {
        let _ = Manifest::parse("p", &text);
    }

    #[test]
    fn arbitrary_toml_shaped_text_never_panics(
        name in "[ -~]{0,50}", ver in "[ -~]{0,30}", fam in "[ -~]{0,12}", path in "[ -~]{0,40}",
    ) {
        let esc = |s: &str| s.replace('\\', "\\\\").replace('"', "\\\"");
        let text = format!(
            "[pack]\nname = \"{}\"\nversion = \"{}\"\nfamilies = [\"{}\"]\n[provides]\nrules = [\"{}\"]\n",
            esc(&name), esc(&ver), esc(&fam), esc(&path)
        );
        if let Ok(m) = Manifest::parse("p", &text) {
            prop_assert!(m.pack.name.len() <= 40);
            prop_assert!(!m.provides.rules.iter().any(|r| r.contains("..")));
        }
    }

    #[test]
    fn arbitrary_bytes_load_never_panics(bytes in proptest::collection::vec(any::<u8>(), 0..300)) {
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join("pack.toml");
        std::fs::write(&p, &bytes).unwrap();
        let _ = load(&p);
    }
}

// frob:tests crates/gob-packs/src/error.rs::PackCode.as_str
// frob:tests crates/gob-packs/src/error.rs::PackError.code
#[test]
fn codes_print_their_stable_ids() {
    assert_eq!(PackCode::Pack004.as_str(), "PACK004");
    assert_eq!(PackCode::Pack005.as_str(), "PACK005");
    let e = Manifest::parse("f", "").unwrap_err();
    assert_eq!(e.code().as_str(), "PACK005");
}
