//! CAP001 for Python identifiers spelled in a non-NFKC form (ticket 7VYCFGM, audit case p27):
//! the interpreter normalises identifiers to NFKC, so a fullwidth or ligature spelling names the
//! same symbol. Non-Python languages are not normalised.

// frob:ticket 01M6422ZYR690QV4JF17VYCFGM

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
fn p04_fullwidth_module_and_builtin_spellings_resolve_to_the_origin_symbol() {
    // `\u{ff4f}\u{ff53}` is fullwidth `os`; `\u{ff4f}\u{ff50}\u{ff45}\u{ff4e}` is fullwidth `open`.
    for (src, atom) in [
        (
            "import \u{ff4f}\u{ff53}\n\n\ndef go(c):\n    \u{ff4f}\u{ff53}.system(c)\n",
            "process.spawn",
        ),
        (
            "import os\n\n\ndef go(c):\n    os.\u{ff53}ystem(c)\n",
            "process.spawn",
        ),
        (
            "from os import \u{ff53}ystem\n\n\ndef go(c):\n    system(c)\n",
            "process.spawn",
        ),
        (
            "def go(p):\n    return \u{ff4f}\u{ff50}\u{ff45}\u{ff4e}(p)\n",
            "fs.read",
        ),
        (
            "def go(p):\n    o = \u{ff4f}\u{ff50}\u{ff45}\u{ff4e}\n    return o(p)\n",
            "fs.read",
        ),
    ] {
        let f = one(src);
        assert!(has(&f, atom, true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p04_a_normalised_local_definition_shadows_the_builtin() {
    let f = one("def open(p):\n    return p\n\n\ndef go(p):\n    return \u{ff4f}pen(p)\n");
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p04_ascii_look_alike_in_a_string_is_not_normalised() {
    let f = one("def go(p):\n    return \"\u{ff4f}pen\"\n");
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p04_non_python_languages_are_not_normalised() {
    // JavaScript identifiers are not NFKC-folded: fullwidth `require` is a different name.
    let f = cap001(&[(
        "src/x.js",
        "const \u{ff53} = require('child_process');\nfunction go(c) { \u{ff52}equire('child_process').exec(c); }\n",
    )]);
    assert!(!has(&f, "process.spawn", true), "{f:?}");
}
