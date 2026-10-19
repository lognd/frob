//! One integration-test binary per crate (audit M17): fewer links, one process pool.
// frob:ticket 01M4CTE9W9QH6SBZSJ3E0E8M28
#![expect(
    clippy::disallowed_methods,
    reason = "confinement allow list: path-to-text conversion pending migration to gob-path"
)]
mod attestation;
mod board;
mod check_verb;
mod cli;
mod close_guards;
mod common;
mod config_ledger_parser;
mod config_reads;
mod cycle;
mod deprecated_aliases;
mod doc_commands;
mod e2e_init_loop;
mod envelope_invariant;
mod first_run;
mod fragment;
mod gc;
mod init_adopt;
mod land_config;
mod lease_heartbeat;
mod lease_widen;
mod merge_driver_branch;
mod merge_driver_path;
mod milestone;
mod pm_config;
mod pm_wiring;
mod profile;
mod redact;
mod release;
mod release_cut;
mod release_status;
mod shared_files;
mod sibling_discovery;
mod terminal_lease;
mod ticket;
mod ticket_branch;
mod ticket_code_readme;
mod ticket_migrate;
mod ticket_misfiled;
mod ticket_moves;
mod ticket_path_refs;
mod ticket_reindex;
mod ticket_replay;
mod ticket_scrub;
mod ticket_trunk_notice;
mod ticket_unsynced;
mod ticket_url;
mod tour;
mod triage;
mod trust;
mod wiring;
mod work_unplanned;
