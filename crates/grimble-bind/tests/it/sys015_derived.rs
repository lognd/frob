//! SYS015 over owner-derived nodes: an impl with no `in node` sits in the node that owns the
//! code its realization selects, and a core -> adc step pair needs a flow.

// frob:ticket 01M4FDBHWDCX31YDY4ZHDTTYWR

use grimble_bind::{BindFinding, BindInput, Binding};
use grimble_model::ModelFiles;

const MODEL: &str = r#"grimble = "2";
module fw;

system thermostat {
  actor tick : timer;
  actor temp_sensor : device { node adc; }
  goal tick as job { control_loop; }

  step tick.fires;
  step temp_sensor.signals_sample;
  step system.computes_duty;

  scenario control_loop realizes tick.control_loop {
    tick.fires -> temp_sensor.signals_sample -> system.computes_duty -> end ok;
  }

  impl tick.fires for * { isr = "fw/src/timer.rs::tim2_irq"; }
  impl temp_sensor.signals_sample for * { isr = "fw/src/adc.rs::adc_irq"; }
  impl system.computes_duty for control_loop {
    handler = "fw/src/control.rs::compute_duty";
    in node core;
  }
}

node adc  : trusted { owns "fw/src/adc.rs"; }
node core : trusted { owns "fw/src/control.rs"; owns "fw/src/timer.rs"; }
flow f_adc_core : adc -> core { label Internal; }
"#;

fn bind(extra: &str) -> Binding {
    bind_model(MODEL, extra)
}

fn bind_model(model: &str, extra: &str) -> Binding {
    let dir = tempfile::tempdir().expect("tempdir");
    let fw = dir.path().join("fw/src");
    std::fs::create_dir_all(&fw).unwrap();
    std::fs::write(fw.join("timer.rs"), "pub fn tim2_irq() {}\n").unwrap();
    std::fs::write(fw.join("adc.rs"), "pub fn adc_irq() {}\n").unwrap();
    std::fs::write(fw.join("control.rs"), "pub fn compute_duty() {}\n").unwrap();
    let text = format!("{model}{extra}");
    let walked = gob_walk::walk(dir.path(), &gob_walk::WalkConfig::default()).unwrap();
    let files = ModelFiles::new().with_file("design/fw.grmb", text.into_bytes());
    grimble_bind::bind(&BindInput {
        root: dir.path(),
        entries: &walked.files,
        model: &files,
        modeled: &[],
        strict: false,
        rename_min_tokens: 12,
        ledger_dir: "tickets",
    })
}

fn sys015(b: &Binding) -> Vec<&BindFinding> {
    b.findings.iter().filter(|f| f.rule == "SYS015").collect()
}

// frob:tests crates/grimble-bind/src/behaviour.rs::lift
#[test]
fn a_derived_core_to_adc_pair_without_a_flow_fires_once() {
    let b = bind("");
    let fired: Vec<_> = sys015(&b)
        .into_iter()
        .filter(|f| f.reason.is_none())
        .collect();
    assert_eq!(fired.len(), 1, "{:?}", sys015(&b));
    assert!(
        fired[0].message.contains("tick.fires"),
        "{}",
        fired[0].message
    );
    assert!(
        fired[0].message.contains("node core"),
        "{}",
        fired[0].message
    );
}

// frob:tests crates/grimble-bind/src/behaviour.rs::lift
#[test]
fn declaring_the_core_to_adc_flow_clears_it() {
    let b = bind("flow f_core_adc : core -> adc { label Internal; }\n");
    let fired: Vec<_> = sys015(&b)
        .into_iter()
        .filter(|f| f.reason.is_none())
        .collect();
    assert!(fired.is_empty(), "{fired:?}");
}

// frob:tests crates/grimble-bind/src/behaviour.rs::lift
#[test]
fn a_step_use_with_an_unknown_node_is_unresolved_never_clean() {
    let model = MODEL.replace(" owns \"fw/src/timer.rs\";", "");
    let b = bind_model(&model, "");
    let all = sys015(&b);
    assert!(
        !all.is_empty(),
        "an undecidable node must be reported, not clean"
    );
    assert!(all.iter().all(|f| f.reason.is_some()), "{all:?}");
}
