//! Scenario `plan.error_set` and `plan.collected` reflect the collected step errors.

// frob:ticket 01M69AXEF0DZH0X55C8DJEDY70
use grimble_bind::{BindInput, Binding};
use grimble_model::ModelFiles;
use serde_json::Value;

const SRC: &str = r#"grimble = "2";
module m;

system s {
  actor customer : human;
  goal customer as action { buy; }

  step customer.pays -> { ok, declined(reason), timeout };
  step customer.lands;
  step system.reserve -> { ok, out_of_stock };
  step system.confirm;
  step system.flaky -> { ok, bad };

  scenario inner realizes customer.buy {
    customer.lands -> end ok;
  }

  scenario checkout realizes customer.buy fails with { out_of_stock, timeout } {
    include inner
      -> system.reserve
      -!> customer.pays => {
        declined -> retry customer.pays max 3 else end err(timeout);
        ok -> system.confirm -> end ok;
        _ -> end ok;
      }
    handle {
      out_of_stock -> end err(out_of_stock);
    }
  }

  scenario inferred {
    customer.lands -> system.flaky -!> end err(bad);
  }

  scenario propagates fails with { bad } {
    customer.lands -> system.flaky -!> end ok;
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

fn plan(b: &Binding, name: &str) -> Value {
    let key = format!("scenario/s.{name}");
    let key = b
        .plan
        .fields
        .keys()
        .find(|k| k.ends_with(&key))
        .unwrap_or_else(|| panic!("no {key} in {:?}", b.plan.fields.keys().collect::<Vec<_>>()))
        .clone();
    b.plan.fields[&key]["plan"].clone()
}

// frob:tests grimble_bind::plan::report
#[test]
fn declared_fails_with_is_the_error_set() {
    let p = plan(&bind(), "propagates");
    assert_eq!(p["error_set"], serde_json::json!(["bad"]));
    let c = p["collected"].as_array().unwrap();
    assert_eq!(c.len(), 1, "{p}");
    assert_eq!(c[0]["variant"], "bad");
    assert!(c[0]["handled_by"].is_null());
}

// frob:tests grimble_bind::plan::report
#[test]
fn undeclared_error_set_is_inferred_from_end_err() {
    let p = plan(&bind(), "inferred");
    assert_eq!(p["error_set"], serde_json::json!(["bad"]));
}

// frob:tests grimble_bind::plan::report
#[test]
fn collected_pairs_name_their_handling_arm() {
    let p = plan(&bind(), "checkout");
    let c = p["collected"].as_array().unwrap();
    assert_eq!(c.len(), 1, "{p}");
    assert_eq!(c[0]["step"], "step/s.system.reserve");
    assert_eq!(c[0]["variant"], "out_of_stock");
    assert_eq!(
        c[0]["handled_by"],
        "scenario/s.checkout/handle[out_of_stock]"
    );
}
