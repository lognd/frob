//! `grimble check` registers the binding rules and fills the document's `bindings`.

// frob:ticket 01M3Z71450ZE377RBK3EG1XSWC

use std::path::Path;

use grimble_check::{CheckOptions, run, sibling_document};

fn write(dir: &Path, rel: &str, text: &str) {
    let path = dir.join(rel);
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn the_document_carries_bindings_and_sys_findings() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\n\nnode a : trusted { owns \"src/**\"; owns \"src/gone.rs::x\"; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    write(dir.path(), "docs/loose.txt", "x\n");
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let findings: Vec<String> = doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .map(|f| f["rule"].as_str().unwrap().to_owned())
        .collect();
    assert!(findings.contains(&"SYS001".to_owned()), "{findings:?}");
    let bindings = doc["bindings"].as_array().unwrap();
    assert!(bindings.iter().any(|b| b["entity"] == "node/a"
        && b["identity"] == "src/lib.rs::run"
        && b["status"] == "must"
        && b["rank"] == 2));
    let rules = doc["rules"].as_array().unwrap();
    assert!(rules.iter().any(|r| r["rule"] == "SYS001"));
}

// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn no_model_means_no_binding_rows() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    assert!(doc["bindings"].as_array().unwrap().is_empty());
    assert!(
        doc["findings"]
            .as_array()
            .unwrap()
            .iter()
            .all(|f| !f["rule"].as_str().unwrap().starts_with("SYS"))
    );
}

// frob:ticket 01M403Q1W4PMWRM8GXPRS10WX7
// frob:tests crates/grimble-check/src/bind_cache.rs::BindSummary
#[test]
fn a_warm_run_reuses_the_binding_and_an_edit_rebuilds_it() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\n\nnode a : trusted { owns \"src/**\"; }\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    let cold = run(dir.path(), &CheckOptions::default()).unwrap();
    assert!(!cold.bind_cached, "the first run builds the binding");
    let warm = run(dir.path(), &CheckOptions::default()).unwrap();
    assert!(
        warm.bind_cached,
        "an unchanged repository reuses the binding"
    );
    let strip = |r: &grimble_check::GrimbleRun| {
        let mut d = sibling_document(r);
        d.as_object_mut().unwrap().remove("timing");
        d
    };
    assert_eq!(strip(&cold), strip(&warm), "warm output equals cold output");
    write(
        dir.path(),
        "src/lib.rs",
        "pub fn run() {}\npub fn more() {}\n",
    );
    let edited = run(dir.path(), &CheckOptions::default()).unwrap();
    assert!(!edited.bind_cached, "an edit rebuilds the binding");
}

// frob:tests crates/grimble-check/src/bind_cache.rs::BindSummary
#[test]
fn a_summary_survives_its_encoding() {
    use grimble_bind::BindFinding;
    use grimble_check::bind_cache::BindSummary;
    let mut s = BindSummary::default();
    s.bindings.push(serde_json::json!({"entity": "node/a"}));
    s.findings.push(BindFinding {
        rule: "SYS001",
        severity: gob_rules::Severity::Warn,
        file: Some("src/a.rs".to_owned()),
        range: Some((1, 4)),
        message: "m".to_owned(),
        reason: Some(grimble_bind::Reason::MayOnlyOwner),
        anchor: "a".to_owned(),
    });
    s.subjects.insert("SYS003", 7);
    s.not_applicable.insert("SYS009", "no flow".to_owned());
    assert_eq!(BindSummary::decode(&s.encode()), Some(s));
    assert_eq!(BindSummary::decode(b"{}"), None);
}

// frob:ticket 01M404FZ1G52F6QMYYGS3AFCP4
// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn rules_without_subjects_are_not_applicable_and_never_zero_subject_rows() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\n\nnode a : trusted { owns \"src/**\"; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let na = ["SYS003", "SYS008", "SYS009", "SYS010", "SYS011"];
    let grmb = doc["fidelity"]
        .as_array()
        .unwrap()
        .iter()
        .find(|f| f["language"] == "grmb")
        .unwrap();
    let listed: Vec<&str> = grmb["not_applicable_rules"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_str().unwrap())
        .collect();
    for rule in na {
        assert!(
            listed.contains(&rule),
            "{rule} in not_applicable_rules: {listed:?}"
        );
        assert!(r.not_applicable.contains_key(rule));
    }
    for row in doc["rules"].as_array().unwrap() {
        let rule = row["rule"].as_str().unwrap();
        assert!(!na.contains(&rule), "{rule} must not appear as a rule row");
        let measured = row["subjects_examined"].as_u64().unwrap() > 0
            || row["findings"].as_u64().unwrap() > 0
            || row["unresolved"].as_u64().unwrap() > 0;
        assert!(measured, "{rule} reported zero subjects");
    }
}

// frob:ticket 01M404FZ1G52F6QMYYGS3AFCP4
// frob:tests crates/grimble-check/src/sibling.rs::sibling_document
#[test]
fn an_applicable_rule_wired_to_no_subject_stays_a_zero_subject_row() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    // Every fact is present: a flow end, a claim above L1, a vmodel ref and a lock entry.
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\n\nnode a : trusted { owns \"src/**\"; }\nnode d : trusted { owns \"design/**\"; owns \"docs/**\"; }\nflow f : a -> d { producer \"src/lib.rs::run\"; }\nclaim c { noflow a -> d; proof L2; evidence tests \"src/lib.rs::run\"; }\nvmodel r { kind artifact; level requirements; ref \"docs/s.md#intro\"; }\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    write(dir.path(), "docs/s.md", "# Intro\n");
    let mut r = run(dir.path(), &CheckOptions::default()).unwrap();
    for rule in ["SYS003", "SYS009", "SYS010", "SYS011"] {
        assert!(!r.not_applicable.contains_key(rule), "{rule} applies here");
    }
    // Simulate the wiring bug: the rules receive no subject although their facts exist.
    for rule in ["SYS003", "SYS009", "SYS010", "SYS011"] {
        r.report.subjects_examined.insert(rule.to_owned(), 0);
    }
    r.report
        .findings
        .retain(|f| !["SYS003", "SYS009", "SYS010", "SYS011"].contains(&f.rule.as_str()));
    let doc = sibling_document(&r);
    let rows = doc["rules"].as_array().unwrap();
    for rule in ["SYS003", "SYS009", "SYS010", "SYS011"] {
        let row = rows.iter().find(|x| x["rule"] == rule).unwrap_or_else(|| {
            panic!("{rule} must stay a rule row so frob warns of zero subjects")
        });
        assert_eq!(row["subjects_examined"], 0);
        assert_eq!(row["findings"], 0);
        assert_eq!(row["unresolved"], 0);
    }
    let grmb = doc["fidelity"]
        .as_array()
        .unwrap()
        .iter()
        .find(|f| f["language"] == "grmb")
        .unwrap();
    assert!(!grmb["not_applicable_rules"].to_string().contains("SYS009"));
}

// frob:ticket 01M405B09EW2M0NDNTXKHXV2X7
// frob:tests crates/grimble-check/src/product.rs::Grimble
#[test]
fn a_repository_with_no_model_entity_lists_the_ownership_rules_not_applicable() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let na = ["SYS001", "SYS002", "SYS004"];
    let grmb = doc["fidelity"]
        .as_array()
        .unwrap()
        .iter()
        .find(|f| f["language"] == "grmb")
        .unwrap();
    let listed = grmb["not_applicable_rules"].to_string();
    for rule in na {
        assert!(listed.contains(rule), "{rule} in {listed}");
        assert!(r.not_applicable.get(rule).is_some_and(|w| !w.is_empty()));
    }
    for row in doc["rules"].as_array().unwrap() {
        let rule = row["rule"].as_str().unwrap();
        assert!(!na.contains(&rule), "{rule} must not be a rule row");
    }
}

// frob:ticket 01M405B09EW2M0NDNTXKHXV2X7
// frob:ticket 01M41H9Y7TTWDN6DAQ5C06R6B7
// frob:tests crates/grimble-check/src/sibling.rs::sibling_document
#[test]
fn ownership_rules_wired_to_no_subject_stay_zero_subject_rows() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\n\nnode a : trusted { owns \"src/**\"; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    let mut r = run(dir.path(), &CheckOptions::default()).unwrap();
    let rules = ["SYS001", "SYS002", "SYS004"];
    for rule in rules {
        assert!(!r.not_applicable.contains_key(rule), "{rule} applies here");
        r.report.subjects_examined.insert(rule.to_owned(), 0);
    }
    r.report
        .findings
        .retain(|f| !rules.contains(&f.rule.as_str()));
    let doc = sibling_document(&r);
    let rows = doc["rules"].as_array().unwrap();
    for rule in rules {
        let row = rows
            .iter()
            .find(|x| x["rule"] == rule)
            .unwrap_or_else(|| panic!("{rule} must stay a rule row"));
        assert_eq!(row["subjects_examined"], 0);
        assert_eq!(row["findings"], 0);
    }
    let grmb = doc["fidelity"]
        .as_array()
        .unwrap()
        .iter()
        .find(|f| f["language"] == "grmb")
        .unwrap();
    assert!(!grmb["not_applicable_rules"].to_string().contains("SYS001"));
}

// frob:tests crates/grimble-check/src/config.rs::ledger_dir
#[test]
fn the_configured_ledger_dir_is_frob_owned_and_nothing_else_moves() {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(dir.path(), "frob.toml", "[tickets]\ndir = \"work/items\"\n");
    write(
        dir.path(),
        "design/m.grmb",
        "grimble = \"2\";\nmodule m;\n\nnode a : trusted { owns \"src/**\"; }\nnode d : trusted { owns \"design/**\"; }\n",
    );
    write(dir.path(), "src/lib.rs", "pub fn run() {}\n");
    write(dir.path(), "work/items/01ABC/ticket.md", "x\n");
    write(dir.path(), "tickets/01ABC/ticket.md", "x\n");
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    let doc = sibling_document(&r);
    let anchors: Vec<String> = doc["findings"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["rule"] == "SYS001")
        .map(|f| f["message"].as_str().unwrap().to_owned())
        .collect();
    assert_eq!(anchors.len(), 2, "{anchors:?}");
    assert!(
        anchors.iter().any(|m| m.contains("`tickets/")),
        "{anchors:?}"
    );
    assert!(
        !anchors.iter().any(|m| m.contains("work/items")),
        "{anchors:?}"
    );
}

const CAP_SRC: &str = "import subprocess\n\ndef go():\n    subprocess.run([\"ls\"])\n";

fn cap_run(node_body: &str) -> serde_json::Value {
    let dir = tempfile::tempdir().unwrap();
    write(
        dir.path(),
        "grimble.toml",
        "[grimble]\nmodels = [\"design/m.grmb\"]\n",
    );
    write(
        dir.path(),
        "design/m.grmb",
        &format!(
            "grimble = \"2\";\nmodule m;\nnode a : trusted {{\n  owns \"src/**\";\n{node_body}}}\n"
        ),
    );
    write(dir.path(), "src/x.py", CAP_SRC);
    let r = run(dir.path(), &CheckOptions::default()).unwrap();
    sibling_document(&r)
}

fn rule_ids(doc: &serde_json::Value, key: &str) -> Vec<String> {
    doc[key]
        .as_array()
        .unwrap()
        .iter()
        .map(|f| f["rule"].as_str().unwrap().to_owned())
        .collect()
}

// frob:ticket 01M4FGXX1F6W7Z1K22NFSW5067
// frob:tests crates/grimble-bind/src/caps.rs::evaluate
#[test]
fn cap_rules_are_listed_fire_and_are_writable_in_accept() {
    let doc = cap_run("");
    let rules = rule_ids(&doc, "rules");
    assert!(rules.contains(&"CAP001".to_owned()) && rules.contains(&"CAP002".to_owned()));
    assert!(rule_ids(&doc, "findings").contains(&"CAP001".to_owned()));

    let doc = cap_run(
        "  may fs.write;\n  accept CAP001 because=\"audited\";\n  accept CAP002 because=\"reserved\";\n",
    );
    let findings = rule_ids(&doc, "findings");
    assert!(!findings.contains(&"MDL013".to_owned()), "{findings:?}");
    assert!(!findings.contains(&"CAP001".to_owned()), "{findings:?}");
    assert!(!findings.contains(&"CAP002".to_owned()), "{findings:?}");
    assert_eq!(
        rule_ids(&doc, "exceptions").len(),
        2,
        "{}",
        doc["exceptions"]
    );
}
