//! `Env` layers overrides over the process environment.

// frob:ticket 01M7TJ8WDCE6AZPP9AGQRV4RWY

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

// frob:tests crates/gob-cli/src/env.rs::Env.with
// frob:tests crates/gob-cli/src/env.rs::Env.get
#[test]
fn with_overrides_a_name_that_get_then_reads() {
    let env = gob_cli::Env::process().with("FROB_TEST_ENV_SET", "value");
    assert_eq!(env.get("FROB_TEST_ENV_SET").as_deref(), Some("value"));
    assert_eq!(env.get("FROB_TEST_ENV_NEVER_SET_ANYWHERE"), None);
}

// frob:tests crates/gob-cli/src/env.rs::Env.is_set_nonempty
#[test]
fn an_empty_override_is_set_but_not_nonempty() {
    let env = gob_cli::Env::process()
        .with("FROB_TEST_ENV_FULL", "1")
        .with("FROB_TEST_ENV_EMPTY", "");
    assert!(env.is_set_nonempty("FROB_TEST_ENV_FULL"));
    assert!(!env.is_set_nonempty("FROB_TEST_ENV_EMPTY"));
    assert!(!env.is_set_nonempty("FROB_TEST_ENV_NEVER_SET_ANYWHERE"));
}

// frob:tests crates/gob-cli/src/env.rs::Env.path
#[test]
fn path_reads_the_override_and_is_empty_when_hidden() {
    let set = gob_cli::Env::process().with("PATH", "/some/bin");
    assert_eq!(set.path(), std::ffi::OsString::from("/some/bin"));
    assert!(gob_cli::Env::process().without("PATH").path().is_empty());
}
