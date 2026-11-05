//! A model mixing vmodel and planning entities reports each root cause once, and the
//! `verified_by ... for` arm coverage names exactly the uncovered arms (grmb-spec 8.3, 13.3).

// frob:ticket 01M4FDBERB4M7E9RG2HD4J3YZ2
use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

/// Bind a model-only repository holding `src` as `model.grmb`.
fn bind(src: &str) -> Binding {
    let dir = tempfile::tempdir().expect("tempdir");
    let model = ModelFiles::new().with_file("model.grmb", src.as_bytes().to_vec());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &[],
        model: &model,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

fn rules(b: &Binding) -> Vec<(&'static str, &str)> {
    b.findings.iter().map(|f| (f.rule, f.message.as_str())).collect()
}

const ARMS: &str = r#"grimble = "2";
module m;
system s {
  actor customer : human;
  goal customer { attr dimension = action; buy; }
  step customer.lands;
  step system.pay : { ok, declined, timeout };
  scenario sc realizes customer.buy fails with { declined, timeout } {
    customer.lands -> system.pay -!> end ok;
    verified_by "tests/pay.rs::ok_path" for system.pay.ok;
  }
}
"#;

// frob:tests crates/grimble-bind/src/plan.rs::findings
#[test]
fn plan006_names_only_the_arms_without_evidence() {
    let b = bind(ARMS);
    let hits: Vec<_> = b.findings.iter().filter(|f| f.rule == "PLAN006").collect();
    assert_eq!(hits.len(), 2, "{:?}", rules(&b));
    assert!(hits.iter().any(|f| f.message.contains("system.pay.declined")));
    assert!(hits.iter().any(|f| f.message.contains("system.pay.timeout")));
    assert!(!hits.iter().any(|f| f.message.contains("system.pay.ok")));
}

// frob:tests crates/grimble-bind/src/plan.rs::findings
#[test]
fn an_orphan_goal_leaf_among_vmodel_entities_is_one_plan001_finding() {
    let src = r#"grimble = "2";
module m;
vmodel req { kind requirement; level system; }
vmodel des { kind design; level system; satisfies req; }
system s {
  actor customer : human;
  goal customer { attr dimension = action; buy; }
}
"#;
    let b = bind(src);
    let rs = rules(&b);
    assert_eq!(rs.len(), 1, "{rs:?}");
    assert_eq!(rs[0].0, "PLAN001", "{rs:?}");
}
