//! CAP001 for Python names whose origin is decided across modules or by several bindings
//! (ticket 01M6422ZN7HKF98JDAP7XKRQQ2, audit cases p09, p10, p26, p28): a re-export under an alias
//! in another repository module, a name rebound after its definition, a `try`/`except ImportError`
//! fallback and a conditionally shadowed import all resolve to every possible origin symbol. A name
//! with more than one possible binding is reported unresolved, never passed silently.

// frob:ticket 01M6422ZN7HKF98JDAP7XKRQQ2

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

const HELPERS: &str = "from subprocess import run as r\n";

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p09_cap_reexport_under_an_alias_resolves_through_the_repository_module() {
    for src in [
        "from helpers import r\n\n\ndef go():\n    r(['ls'])\n",
        "import helpers\n\n\ndef go():\n    helpers.r(['ls'])\n",
        "from helpers import r as spawn\n\n\ndef go():\n    spawn(['ls'])\n",
        "from .helpers import r\n\n\ndef go():\n    r(['ls'])\n",
        "from . import helpers\n\n\ndef go():\n    helpers.r(['ls'])\n",
    ] {
        let f = cap001(&[("src/helpers.py", HELPERS), ("src/x.py", src)]);
        assert!(has(&f, "process.spawn", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p09_cap_a_chain_of_reexports_and_a_package_resolve() {
    let f = cap001(&[
        ("src/helpers.py", HELPERS),
        ("src/mid.py", "from helpers import r as q\n"),
        (
            "src/x.py",
            "from mid import q\n\n\ndef go():\n    q(['ls'])\n",
        ),
    ]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
    let f = cap001(&[
        ("src/pkg/__init__.py", "from subprocess import run as r\n"),
        (
            "src/x.py",
            "from pkg import r\n\n\ndef go():\n    r(['ls'])\n",
        ),
    ]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p09_cap_a_name_the_repository_module_defines_is_not_a_capability() {
    let f = cap001(&[
        ("src/helpers.py", "def r(x):\n    return x\n"),
        (
            "src/x.py",
            "from helpers import r\n\n\ndef go():\n    r(['ls'])\n",
        ),
    ]);
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p09_cap_a_module_that_may_define_the_name_leaves_it_unproven() {
    let f = cap001(&[
        (
            "src/helpers.py",
            "from subprocess import run as r\nimport os\nif os.name == 'nt':\n    def r(x):\n        return x\n",
        ),
        (
            "src/x.py",
            "from helpers import r\n\n\ndef go():\n    r(['ls'])\n",
        ),
    ]);
    assert!(has(&f, "process.spawn/receiver", false), "{f:?}");
    assert!(!has(&f, "process.spawn", true), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p09_cap_a_reexport_cycle_terminates_and_unrelated_modules_stay_clean() {
    let f = cap001(&[
        ("src/a.py", "from b import r\n"),
        ("src/b.py", "from a import r\n"),
        ("src/x.py", "from a import r\n\n\ndef go():\n    r(1)\n"),
    ]);
    assert!(f.is_empty(), "{f:?}");
    let f = cap001(&[
        ("src/helpers.py", "def r(x):\n    return x\n"),
        (
            "src/x.py",
            "import helpers\n\n\ndef go():\n    helpers.r(1)\n",
        ),
    ]);
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p10_cap_an_import_after_a_definition_or_assignment_is_reported_unresolved() {
    for src in [
        "def run(x):\n    return x\n\n\nfrom subprocess import run\n\n\ndef go():\n    run(['ls'])\n",
        "run = print\nfrom subprocess import run\n\n\ndef go():\n    run(['ls'])\n",
        "from subprocess import run\n\n\ndef run(x):\n    return x\n\n\ndef go():\n    run(['ls'])\n",
        "from subprocess import run\nrun = print\n\n\ndef go():\n    run(['ls'])\n",
    ] {
        let f = one(src);
        assert!(has(&f, "process.spawn/receiver", false), "{src}: {f:?}");
        assert!(!has(&f, "process.spawn", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p10_cap_parameters_and_function_locals_still_shadow_an_import() {
    for src in [
        "from subprocess import run\n\n\ndef go(run):\n    run(1)\n",
        "from subprocess import run\n\n\ndef go():\n    run = print\n    run(1)\n",
    ] {
        let f = one(src);
        assert!(f.is_empty(), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p26_cap_a_conditional_shadow_of_an_import_is_reported_unresolved() {
    for src in [
        "import sys\nfrom subprocess import run\nif sys.platform == 'win32':\n    def run(x):\n        return x\n\n\ndef go():\n    run(['ls'])\n",
        "import sys\nfrom subprocess import run\nif sys.argv:\n    run = print\n\n\ndef go():\n    run(['ls'])\n",
        "import os\nif os.name == 'nt':\n    import ntpath as p\nelse:\n    import posixpath as p\nfrom subprocess import run\nif os.environ.get('X'):\n    class run:\n        pass\n\n\ndef go():\n    run(['ls'])\n",
    ] {
        let f = one(src);
        assert!(has(&f, "process.spawn/receiver", false), "{src}: {f:?}");
        assert!(!has(&f, "process.spawn", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p28_cap_a_try_except_import_reports_every_origin() {
    for src in [
        "try:\n    from subprocess import run\nexcept ImportError:\n    run = None\n\n\ndef go():\n    run(['ls'])\n",
        "try:\n    from shim import run\nexcept ImportError:\n    from subprocess import run\n\n\ndef go():\n    run(['ls'])\n",
        "try:\n    import subprocess as sp\nexcept ImportError:\n    import shim as sp\n\n\ndef go():\n    sp.run(['ls'])\n",
    ] {
        let f = one(src);
        assert!(has(&f, "process.spawn/receiver", false), "{src}: {f:?}");
        assert!(!has(&f, "process.spawn", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p28_cap_agreeing_fallback_imports_stay_certain() {
    let f = one(
        "try:\n    from subprocess import run\nexcept ImportError:\n    from subprocess import run\n\n\ndef go():\n    run(['ls'])\n",
    );
    assert!(has(&f, "process.spawn", true), "{f:?}");
}
