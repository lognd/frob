//! Tier-1 pack content interned into the registry (ticket HC9450N).

// frob:ticket 01M3ZX7JRYNHG0BHJ3ZHC9450N

use gob_ir::Answer;
use gob_ir::registry::{self, DetectorKind};
use gob_packs::tier1;

const ATOMS: &str = r#"
format = 1
[[atom]]
name = "t1alpha.send"
doc = "send"
aliases = ["t1alpha_tx"]
[[atom]]
name = "t1alpha.recv"
doc = "recv"
[[vocab]]
lang = "rust"
class = "t1alpha"
names = ["Alpha::send"]
[[detector]]
atoms = "*"
langs = ["rust"]
kind = "callee"
[[detector]]
atom = "t1alpha.send"
lang = "css"
kind = "impossible"
reason = "no sockets in css"
"#;

const TEMPLATES: &str = r#"
[[template]]
name = "generated"
atom = "t1alpha.send"
for = "lang(rust)"
reason = "generated stubs"
"#;

fn content(pack: &str, atoms: &str, tpl: Option<&str>) -> tier1::Content {
    tier1::parse(
        pack,
        "atoms.toml",
        atoms,
        tpl.map(|t| ("templates.toml", t)),
    )
    .unwrap()
}

// frob:tests crates/gob-packs/src/tier1/mod.rs::intern
#[test]
fn pack_content_answers_like_an_inventory_atom() {
    let c = content("alpha-pack", ATOMS, Some(TEMPLATES));
    tier1::intern(&c).unwrap();
    assert_eq!(registry::canonical("t1alpha_tx"), Some("t1alpha.send"));
    match registry::detectors("t1alpha.send", "rust") {
        Answer::Exact(k) => assert!(k.contains(&DetectorKind::Callee)),
        other => panic!("{other:?}"),
    }
    assert_eq!(
        registry::detectors("t1alpha.send", "css"),
        Answer::NotApplicable
    );
    assert!(matches!(
        registry::callee_vocab("rust", "t1alpha"),
        Answer::Exact(n) if n.contains("Alpha::send")
    ));
    assert!(
        registry::templates()
            .iter()
            .any(|t| t.pack == "alpha-pack" && t.atom == "t1alpha.send")
    );
}

// frob:tests crates/gob-packs/src/tier1/mod.rs::intern_all
#[test]
fn duplicate_atom_is_pack004_naming_both_packs() {
    let a = "[[atom]]\nname = \"t1dup.x\"\ndoc = \"d\"\n";
    tier1::intern(&content("first-pack", a, None)).unwrap();
    let e = tier1::intern(&content("second-pack", a, None)).unwrap_err();
    assert_eq!(e.code().as_str(), "PACK004");
    let m = e.to_string();
    assert!(m.contains("first-pack") && m.contains("second-pack"), "{m}");
}

#[test]
fn template_on_foreign_atom_is_pack005() {
    let t = "[[template]]\nname = \"x\"\natom = \"nope.y\"\nfor = \"lang(rust)\"\nreason = \"r\"\n";
    let e = tier1::parse("p", "atoms.toml", ATOMS, Some(("templates.toml", t))).unwrap_err();
    assert_eq!(e.code().as_str(), "PACK005");
}
