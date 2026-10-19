//! Typed hook registry (ticket BNG3E2K).

// frob:ticket 01M3ZX7JN8RWAKDVYK0BNG3E2K

use gob_packs::hooks::{Hook, Implementation, PackHooks, Registry};

fn pack(name: &str, caps: &[&str], imps: Vec<Implementation>) -> PackHooks {
    PackHooks {
        file: format!("{name}/pack.toml"),
        name: name.to_owned(),
        capabilities: caps.iter().map(|c| (*c).to_owned()).collect(),
        implementations: imps,
        config_tables: vec![],
    }
}

fn imp(hook: &str, version: u32, sig: &str, priority: i32) -> Implementation {
    Implementation {
        hook: hook.to_owned(),
        version,
        signature: sig.to_owned(),
        priority,
    }
}

// frob:tests register
#[test]
fn unknown_hook_is_pack005_with_reason() {
    let mut r = Registry::new();
    let e = r
        .register(&pack("a", &[], vec![imp("around", 1, "around(x)", 0)]))
        .unwrap_err();
    assert_eq!(e.code().as_str(), "PACK005");
    assert!(e.to_string().contains("unknown hook `around`"), "{e}");
}

// frob:tests register
#[test]
fn wrong_signature_version_and_capability_are_pack005_with_reason() {
    let mut r = Registry::new();
    let e = r
        .register(&pack(
            "a",
            &[],
            vec![imp("check_file", 1, "check_file(path) -> findings", 0)],
        ))
        .unwrap_err();
    assert!(
        e.to_string()
            .contains("expected `check_file(file)->findings`"),
        "{e}"
    );
    let e = r
        .register(&pack(
            "a",
            &[],
            vec![imp("check_file", 2, "check_file(file)->findings", 0)],
        ))
        .unwrap_err();
    assert!(e.to_string().contains("no version 2"), "{e}");
    let e = r
        .register(&pack(
            "a",
            &[],
            vec![imp("check_repo", 1, "check_repo(graph) -> findings", 0)],
        ))
        .unwrap_err();
    assert!(e.to_string().contains("requires capability `graph`"), "{e}");
    assert!(r.ordered(Hook::CheckRepo).is_empty());
}

// frob:tests ordered
#[test]
fn equal_priority_ties_break_by_pack_name_on_every_run() {
    for order in [["zeta", "alpha", "mid"], ["mid", "zeta", "alpha"]] {
        let mut r = Registry::new();
        for n in order {
            r.register(&pack(
                n,
                &[],
                vec![imp("check_file", 1, "check_file(file) -> findings", 5)],
            ))
            .unwrap();
        }
        r.register(&pack(
            "late",
            &[],
            vec![imp("check_file", 1, "check_file(file)->findings", 9)],
        ))
        .unwrap();
        r.register(&pack(
            "zfirst",
            &[],
            vec![imp("check_file", 1, "check_file(file)->findings", -1)],
        ))
        .unwrap();
        let names: Vec<&str> = r
            .ordered(Hook::CheckFile)
            .iter()
            .map(|e| e.pack.as_str())
            .collect();
        assert_eq!(names, ["zfirst", "alpha", "mid", "zeta", "late"]);
    }
}

// frob:tests config_tables
#[test]
fn config_tables_are_collected_sorted() {
    let mut r = Registry::new();
    let mut p = pack("b", &[], vec![imp("config_tables", 1, "config_tables", 0)]);
    p.config_tables = vec!["packs.b.knob".into(), "packs.b.alpha".into()];
    r.register(&p).unwrap();
    assert_eq!(
        r.config_tables(),
        [("packs.b.alpha", "b"), ("packs.b.knob", "b")]
    );
}
