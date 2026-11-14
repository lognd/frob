//! CAP001 for Python local aliases of a builtin or module callable (ticket 8B9HSHH, audit case
//! p03): `o = open` then `o(p)` resolves to the origin symbol. Unprovable forms are Unresolved.

// frob:ticket 01M6422ZCGB47DJWWY78B9HSHH

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

fn bind_files(files: &[(&str, &str)]) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    for (rel, text) in files {
        let p = dir.path().join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, text).unwrap();
    }
    let model = "grimble = \"2\";\nmodule m;\nnode a : trusted {\n  owns \"src/**\";\n}\n";
    std::fs::write(dir.path().join("design/model.grmb"), model).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let model = ModelFiles::new().with_file("design/model.grmb", model.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &model,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

/// (atom, certain) of every CAP001 finding, ungranted.
fn cap001(files: &[(&str, &str)]) -> Vec<(String, bool)> {
    let b = bind_files(files);
    let mut v: Vec<_> = b
        .findings
        .iter()
        .filter(|f| f.rule == "CAP001")
        .map(|f| {
            (
                f.anchor.trim_start_matches("cap/node/a/").to_owned(),
                f.reason.is_none(),
            )
        })
        .collect();
    v.sort();
    v.dedup();
    v
}

fn one(src: &str) -> Vec<(String, bool)> {
    cap001(&[("src/x.py", src)])
}

fn has(found: &[(String, bool)], atom: &str, certain: bool) -> bool {
    found.iter().any(|(a, c)| a == atom && *c == certain)
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p03_assignment_aliases_of_a_builtin_resolve_to_the_origin_symbol() {
    for src in [
        "def go(p):\n    o = open\n    return o(p)\n",
        "o = open\n\n\ndef go(p):\n    return o(p)\n",
        "def go(p):\n    o = w = open\n    return w(p)\n",
        "def go(p):\n    o: object = open\n    return o(p)\n",
        "def go(p):\n    o = open\n    q = o\n    return q(p)\n",
        "def go(p):\n    o, q = open, 1\n    return o(p)\n",
        "import builtins\n\n\ndef go(p):\n    o = builtins.open\n    return o(p)\n",
        "def go(p, f):\n    return list(map(open, f))\n",
        "def go(p, o=open):\n    return o(p)\n",
    ] {
        let f = one(src);
        assert!(has(&f, "fs.read", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p03_assignment_aliases_of_a_module_attribute_resolve_to_the_origin_symbol() {
    for src in [
        "import os\n\n\ndef go(c):\n    w = os.system\n    w(c)\n",
        "import os as o\n\n\ndef go(c):\n    w = o.system\n    w(c)\n",
        "from os import system\n\n\ndef go(c):\n    w = system\n    w(c)\n",
    ] {
        let f = one(src);
        assert!(has(&f, "process.spawn", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p03_a_repository_open_is_not_the_builtin() {
    let f = one("def open(p):\n    return p\n\n\ndef go(p):\n    o = open\n    return o(p)\n");
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p03_a_computed_builtin_lookup_is_unresolved_never_clean() {
    let f =
        one("import builtins\n\n\ndef go(p, n):\n    o = getattr(builtins, n)\n    return o(p)\n");
    assert!(
        !f.is_empty() && f.iter().all(|(_, certain)| !certain),
        "{f:?}"
    );
}
