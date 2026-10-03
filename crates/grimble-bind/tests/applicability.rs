//! SYS001, SYS002, SYS004 (no node, owns row or checkable clause), SYS003, SYS008, SYS009, SYS010 and SYS011 examine their subjects when the model has them
//! and report `NotApplicable` (with a reason, never zero subjects) when it does not.

// frob:ticket 01M404FZ1G52F6QMYYGS3AFCP4
// frob:ticket 01M405B09EW2M0NDNTXKHXV2X7

use std::path::Path;

use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const RULES: [&str; 5] = ["SYS003", "SYS008", "SYS009", "SYS010", "SYS011"];

/// A model with only nodes: no operand, flow, claim, vmodel or lock entry.
const PLAIN: &str = "grimble = \"2\";\nmodule m;\n\nnode a : trusted { owns \"src/**\"; }\nnode d : trusted { owns \"design/**\"; }\n";

fn bind(files: &[(&str, &str)]) -> Binding {
    let dir = tempfile::tempdir().unwrap();
    for (rel, text) in files {
        let p = dir.path().join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, text).unwrap();
    }
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let mut model = ModelFiles::new();
    for f in &walked.files {
        if Path::new(&f.path).extension().is_some_and(|e| e == "grmb") {
            model = model.with_file(&f.path, std::fs::read(dir.path().join(&f.path)).unwrap());
        }
    }
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &model,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
    })
}

fn fired(b: &Binding, rule: &str) -> bool {
    b.findings.iter().any(|f| f.rule == rule)
}

fn examined(b: &Binding, rule: &str) -> usize {
    b.subjects.get(rule).copied().unwrap_or(0)
}

// frob:tests crates/grimble-bind/src/lib.rs::bind
#[test]
fn a_model_without_such_entities_is_not_applicable_not_zero_subjects() {
    let b = bind(&[
        ("design/m.grmb", PLAIN),
        ("src/lib.rs", "pub fn run() {}\n"),
    ]);
    for rule in RULES {
        assert!(
            b.not_applicable.contains_key(rule),
            "{rule} must be NotApplicable"
        );
        assert!(
            !b.not_applicable[rule].is_empty(),
            "{rule} carries a reason"
        );
        assert!(
            !b.subjects.contains_key(rule),
            "{rule} reports no subject count"
        );
        assert!(!fired(&b, rule));
    }
}

// frob:tests crates/grimble-bind/src/lib.rs::bind
#[test]
fn a_repository_with_no_entity_at_all_is_not_applicable() {
    let b = bind(&[("src/lib.rs", "pub fn run() {}\n")]);
    for rule in RULES {
        assert!(b.not_applicable.contains_key(rule), "{rule}");
    }
}

// frob:tests crates/grimble-bind/src/rules.rs::evaluate
#[test]
fn sys003_examines_operands_and_fires_on_a_dangling_one() {
    let b = bind(&[
        ("design/m.grmb", PLAIN),
        (
            "src/lib.rs",
            "// grimble:binds design:node/nope\npub fn one() {}\n",
        ),
    ]);
    assert!(examined(&b, "SYS003") >= 1);
    assert!(fired(&b, "SYS003"));
    assert!(!b.not_applicable.contains_key("SYS003"));
}

// frob:tests crates/grimble-bind/src/rules.rs::evaluate
#[test]
fn sys003_examines_a_singleton_clause_and_is_clean_on_a_good_one() {
    let model = format!(
        "{PLAIN}\nvmodel r {{ kind artifact; level requirements; ref \"docs/s.md#intro\"; }}\n"
    );
    let b = bind(&[
        ("design/m.grmb", &model),
        ("docs/s.md", "# Intro\n\ntext\n"),
    ]);
    assert!(examined(&b, "SYS003") >= 1);
    assert!(!fired(&b, "SYS003"));
}

// frob:tests crates/grimble-bind/src/rules.rs::evaluate
#[test]
fn sys009_examines_a_flow_end_and_fires_on_an_unbound_one() {
    let model = format!(
        "{PLAIN}\nnode b : trusted {{ owns \"dst/**\"; }}\nflow f : a -> b {{ producer \"src/lib.rs::send\"; consumer \"dst/lib.rs::absent\"; }}\n"
    );
    let b = bind(&[
        ("design/m.grmb", &model),
        ("src/lib.rs", "pub fn send() {}\n"),
        ("dst/lib.rs", "pub fn recv() {}\n"),
    ]);
    assert_eq!(examined(&b, "SYS009"), 2);
    assert!(
        examined(&b, "SYS003") >= 1,
        "a flow end clause is a SYS003 subject"
    );
    assert!(fired(&b, "SYS009"));
    assert!(!b.not_applicable.contains_key("SYS009"));
}

// frob:tests crates/grimble-bind/src/rules.rs::evaluate
#[test]
fn sys010_examines_a_claim_and_fires_without_evidence() {
    let model = format!(
        "{PLAIN}\nclaim c {{ noflow a -> d; proof L2; evidence tests \"src/lib.rs::run\"; }}\n"
    );
    let b = bind(&[
        ("design/m.grmb", &model),
        ("src/lib.rs", "pub fn run() {}\n"),
    ]);
    assert_eq!(examined(&b, "SYS010"), 1);
    assert!(fired(&b, "SYS010"));
    assert!(!b.not_applicable.contains_key("SYS010"));
}

// frob:tests crates/grimble-bind/src/rules.rs::evaluate
#[test]
fn sys011_examines_a_vmodel_link_and_fires_when_it_is_broken() {
    let model = format!(
        "{PLAIN}\nvmodel t {{ kind test; level customer_test; runnable \"tests/t.rs::absent\"; }}\n"
    );
    let b = bind(&[
        ("design/m.grmb", &model),
        ("tests/t.rs", "#[test]\nfn it_works() {}\n"),
    ]);
    assert_eq!(examined(&b, "SYS011"), 1);
    assert!(fired(&b, "SYS011"));
    assert!(!b.not_applicable.contains_key("SYS011"));
}

const OWNERSHIP: [&str; 3] = ["SYS001", "SYS002", "SYS004"];

// frob:tests crates/grimble-bind/src/rules.rs::sys004_inapplicable
#[test]
fn no_model_entity_makes_sys001_sys002_sys004_not_applicable() {
    for files in [
        vec![("src/lib.rs", "pub fn run() {}\n")],
        vec![
            ("design/m.grmb", "grimble = \"2\";\nmodule m;\n"),
            ("src/lib.rs", "pub fn run() {}\n"),
        ],
    ] {
        let b = bind(&files);
        for rule in OWNERSHIP {
            let why = b.not_applicable.get(rule);
            assert!(why.is_some_and(|w| !w.is_empty()), "{rule} needs a reason");
            assert!(
                !b.subjects.contains_key(rule),
                "{rule} has no subject count"
            );
            assert!(!fired(&b, rule));
        }
    }
}

// frob:tests crates/grimble-bind/src/rules.rs::sys004_inapplicable
#[test]
fn a_model_with_nodes_examines_ownership_subjects() {
    let model = format!("{PLAIN}node t : trusted {{ owns \"src/**\"; }}\n");
    let b = bind(&[
        ("design/m.grmb", &model),
        ("src/lib.rs", "pub fn run() {}\n"),
        ("docs/loose.txt", "x\n"),
    ]);
    for rule in OWNERSHIP {
        assert!(!b.not_applicable.contains_key(rule), "{rule} applies");
        assert!(examined(&b, rule) >= 1, "{rule} examines subjects");
    }
    assert!(fired(&b, "SYS001"), "an unowned file is a real finding");
    assert!(fired(&b, "SYS002"), "two nodes own src/** equally");
}

// frob:tests crates/grimble-bind/src/rules.rs::sys001_inapplicable
#[test]
fn a_model_with_only_a_flow_has_no_node_to_own_files() {
    let model = "grimble = \"2\";\nmodule m;\n\nnode a : external { }\nnode b : external { }\nflow f : a -> b { }\n";
    let b = bind(&[
        ("design/m.grmb", model),
        ("src/lib.rs", "pub fn run() {}\n"),
    ]);
    assert!(
        !b.not_applicable.contains_key("SYS004"),
        "a flow is checked for code"
    );
    assert!(examined(&b, "SYS004") >= 1);
}
