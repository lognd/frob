//! `frob.toml` is read from disk once per `FrobConfig::load`, and `[tickets]`/`[git]` have one parser (audit M13).

use frob_cli::config::FrobConfig;

const TOML: &str = "[tickets]\nref = \"refs/heads/trunk\"\nhandle_min_len = 9\nactor = \"bot\"\n\n[git]\ncas_retries = 3\n";

// frob:tests crates/frob/src/config.rs::FrobConfig::load
#[test]
fn loading_every_table_reads_frob_toml_once() {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("frob.toml"), TOML).expect("write");
    let before = gob_config::file_reads();
    let cfg = FrobConfig::load(dir.path()).expect("load");
    assert_eq!(gob_config::file_reads() - before, 1, "one read per load");
    assert_eq!(cfg.tickets.handle_min_len, 9);
}
