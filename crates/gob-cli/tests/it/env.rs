//! `Env` layers overrides over the process environment.

// frob:tests crates/gob-cli/src/env.rs::Env.is_process
#[test]
fn a_fresh_process_env_has_no_overrides_and_with_or_without_adds_one() {
    let plain = gob_cli::Env::process();
    assert!(plain.is_process(), "no name is overridden or hidden");
    assert!(
        !plain.clone().with("FROB_TEST_KEY", "1").is_process(),
        "an override makes the env non-process"
    );
    assert!(
        !plain.without("FROB_TEST_KEY").is_process(),
        "hiding a name makes the env non-process"
    );
}
