//! PLAN006 reports a collected pair that no `verified_by ... for` covers.

// frob:ticket 01M69T6Q3J2RVWGTT4PM7YR6SS
use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;

const SRC: &str = r#"grimble = "2";
module m;

system s {
  actor customer : human;
  goal customer { attr dimension = action; buy; }
  step customer.lands;
  step system.flaky : { ok, bad };
  step system.confirm;
  step system.other : { ok, worse };

  scenario sc realizes customer.buy fails with { bad, worse } {
    customer.lands -> system.flaky -!> system.other -!> end ok;
  }

  scenario handled realizes customer.buy fails with { bad } {
    customer.lands -> system.flaky -!> system.confirm -> end ok;
    handle {
      bad -> end err(bad);
    }
  }
}
"#;

fn bind() -> Binding {
    let dir = tempfile::tempdir().expect("tempdir");
    let model = ModelFiles::new().with_file("model.grmb", SRC.as_bytes().to_vec());
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

// frob:tests crates/grimble-bind/src/plan.rs::findings
#[test]
fn each_uncovered_collected_pair_is_one_plan006_finding() {
    let b = bind();
    let hits: Vec<_> = b.findings.iter().filter(|f| f.rule == "PLAN006").collect();
    assert!(
        hits.iter().any(|f| f.message.contains("system.flaky.bad")
            && f.message.contains("propagates")
            && f.anchor.ends_with("scenario/s.sc")),
        "{hits:?}"
    );
    assert!(
        hits.iter()
            .any(|f| f.message.contains("system.other.worse")),
        "{hits:?}"
    );
    assert!(
        hits.iter()
            .any(|f| f.anchor.ends_with("scenario/s.handled") && f.message.contains("handle[bad]")),
        "{hits:?}"
    );
    assert_eq!(b.subjects.get("PLAN006"), Some(&3), "{:?}", b.subjects);
}

// frob:tests crates/grimble-bind/src/plan.rs::report
#[test]
fn plan006_is_listed_as_an_uncovered_arm_obligation() {
    let b = bind();
    assert!(
        b.plan
            .obligations
            .iter()
            .any(|o| o["rule"] == "PLAN006" && o["kind"] == "uncovered_arm"),
        "{:?}",
        b.plan.obligations
    );
}
