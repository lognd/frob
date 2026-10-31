//! CAP001 for Python wildcard imports (ticket G68NRS1, audit case p02): a bare name bound by
//! `from m import *` resolves to its origin symbol, so `from subprocess import *` then `run(..)`
//! is a process spawn. Unprovable origins are reported unresolved, never passed silently.

// frob:ticket 01M6422Z8JGE789ZHW4G68NRS1

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
fn p02_wildcard_import_of_a_capability_module_resolves_the_bare_name() {
    for src in [
        "from subprocess import *\n\n\ndef go():\n    run(['ls'])\n",
        "from os import *\n\n\ndef go(c):\n    system(c)\n",
        "from subprocess import *\n\n\ndef go():\n    return list(map(run, [['ls']]))\n",
    ] {
        let f = one(src);
        assert!(has(&f, "process.spawn", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p02_a_local_definition_or_parameter_shadows_the_wildcard_name() {
    for src in [
        "from subprocess import *\n\n\ndef run(x):\n    return x\n\n\ndef go():\n    run(1)\n",
        "from subprocess import *\n\n\ndef go(run):\n    run(1)\n",
        "from subprocess import *\n\nrun = print\n\n\ndef go():\n    run(1)\n",
    ] {
        let f = one(src);
        assert!(f.is_empty(), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p02_names_a_module_does_not_provide_report_nothing() {
    let f = one("from subprocess import *\n\n\ndef go():\n    other(helper())\n");
    assert!(f.is_empty(), "{f:?}");
    let f = one("# from subprocess import *\ndef go():\n    run(['ls'])\n");
    assert!(f.is_empty(), "{f:?}");
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p02_unknown_relative_and_multiple_wildcards_are_unresolved_never_clean() {
    for src in [
        "from nowhere import *\n\n\ndef go():\n    run(['ls'])\n",
        "from .missing import *\n\n\ndef go():\n    run(['ls'])\n",
        "from subprocess import *\nfrom os import *\n\n\ndef go():\n    run(['ls'])\n",
    ] {
        let f = one(src);
        assert!(has(&f, "process.spawn/receiver", false), "{src}: {f:?}");
        assert!(!has(&f, "process.spawn", true), "{src}: {f:?}");
    }
}

// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn p02_repository_wildcard_module_honours_all_and_its_own_definitions() {
    // `__all__` leaves `run` out: the wildcard cannot supply it, the stdlib wildcard does
    let f = cap001(&[
        (
            "src/x.py",
            "from helpers import *\nfrom subprocess import *\n\n\ndef go():\n    run(['ls'])\n",
        ),
        (
            "helpers.py",
            "__all__ = ['other']\n\n\ndef other():\n    pass\n",
        ),
    ]);
    assert!(has(&f, "process.spawn", true), "{f:?}");
    // the repository module defines `run` itself: a repository item, not the subprocess one
    let f = cap001(&[
        (
            "src/x.py",
            "from helpers import *\n\n\ndef go():\n    run(['ls'])\n",
        ),
        ("helpers.py", "def run(x):\n    return x\n"),
    ]);
    assert!(f.is_empty(), "{f:?}");
    // a repository module that may re-export the name leaves it unproven
    let f = cap001(&[
        (
            "src/x.py",
            "from helpers import *\n\n\ndef go():\n    run(['ls'])\n",
        ),
        ("helpers.py", "from subprocess import run\n"),
    ]);
    assert!(has(&f, "process.spawn/receiver", false), "{f:?}");
}
