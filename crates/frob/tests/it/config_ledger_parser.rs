//! `[tickets]`/`[git]` have exactly one parser, owned by `frob-ledger` (audit M13).

use frob_cli::config::FrobConfig;

const TOML: &str = "[tickets]\nref = \"refs/heads/trunk\"\nhandle_min_len = 9\nactor = \"bot\"\n\n[git]\ncas_retries = 3\n";

// frob:tests crates/frob-ledger/src/config.rs::load_ledger_config
#[test]
fn the_ledger_parser_in_frob_ledger_owns_tickets_and_git() {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("frob.toml"), TOML).expect("write");
    let via_cli = FrobConfig::load(dir.path()).expect("load").ledger();
    let via_ledger = frob_ledger::config::load_ledger_config(dir.path()).expect("ledger");
    assert_eq!(via_cli.ref_name, via_ledger.ref_name);
    assert_eq!(via_cli.cas_retries, 3);
    assert_eq!(via_ledger.cas_retries, 3);
    assert_eq!(via_ledger.handle_min_len, 9);
    assert_eq!(via_ledger.actor.as_deref(), Some("bot"));
}
