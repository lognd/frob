//! Pack detector rows beyond `callee` (ticket 01M5XNNJHXH8FFQ9JHJP21FHB9): an `attribute` row makes
//! a Rust unsafe block a use, an `import` row makes `import ctypes` a use, and a GRL `pattern` row
//! makes `subprocess.run(.., shell=True)` a use, each with a firing and a clean example.

// frob:ticket 01M5XNNJHXH8FFQ9JHJP21FHB9

use std::collections::BTreeSet;

use grimble_bind::{BindInput, Binding};
use grimble_model::{ModelFiles, PackDetector, PackDetectorKind, PackPin};

fn row(atom: &str, lang: &str, kind: PackDetectorKind, patterns: &[&str]) -> PackDetector {
    PackDetector {
        atom: atom.to_owned(),
        lang: lang.to_owned(),
        kind,
        names: BTreeSet::new(),
        patterns: patterns.iter().map(|s| (*s).to_owned()).collect(),
    }
}

fn bind(file: (&str, &str), detectors: Vec<PackDetector>) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(dir.path().join("design")).unwrap();
    let p = dir.path().join(file.0);
    std::fs::create_dir_all(p.parent().unwrap()).unwrap();
    std::fs::write(p, file.1).unwrap();
    let model = "grimble = \"2\";\nmodule m;\npack \"local/t\";\nnode a : trusted {\n  owns \"src/**\";\n}\n";
    std::fs::write(dir.path().join("design/model.grmb"), model).unwrap();
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let mut mf = ModelFiles::new().with_file("design/model.grmb", model.as_bytes().to_vec());
    mf.packs.insert(
        "local/t".to_owned(),
        PackPin {
            version: "1.0.0".to_owned(),
            atoms: detectors.iter().map(|d| d.atom.clone()).collect(),
            detectors,
            ..PackPin::default()
        },
    );
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &mf,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

/// True when a CAP001 finding names `atom` as an observed use.
fn fires(b: &Binding, atom: &str) -> bool {
    b.findings
        .iter()
        .any(|f| f.rule == "CAP001" && f.anchor.ends_with(&format!("/{atom}")))
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn attribute_row_makes_rust_unsafe_blocks_a_use() {
    let d = || vec![row("unsafe.block", "rust", PackDetectorKind::Attribute, &["unsafe { $$$A }"])];
    let hot = bind(("src/a.rs", "pub fn f() { unsafe { g(); } }\n"), d());
    assert!(fires(&hot, "unsafe.block"), "{:?}", hot.findings);
    let clean = bind(("src/a.rs", "pub fn f() { g(); }\n"), d());
    assert!(!fires(&clean, "unsafe.block"), "{:?}", clean.findings);
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn import_row_makes_python_ctypes_a_use() {
    let d = || vec![row("ffi.load", "python", PackDetectorKind::Import, &["ctypes"])];
    let hot = bind(("src/a.py", "import ctypes\n"), d());
    assert!(fires(&hot, "ffi.load"), "{:?}", hot.findings);
    let clean = bind(("src/a.py", "import os\n"), d());
    assert!(!fires(&clean, "ffi.load"), "{:?}", clean.findings);
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn pattern_row_makes_shell_true_a_distinct_use() {
    let d = || {
        vec![row(
            "process.spawn.shell",
            "python",
            PackDetectorKind::Pattern,
            &["subprocess.run($$$A, shell=True)"],
        )]
    };
    let hot = bind(("src/a.py", "import subprocess\nsubprocess.run(c, shell=True)\n"), d());
    assert!(fires(&hot, "process.spawn.shell"), "{:?}", hot.findings);
    let clean = bind(("src/a.py", "import subprocess\nsubprocess.run(c)\n"), d());
    assert!(!fires(&clean, "process.spawn.shell"), "{:?}", clean.findings);
}
