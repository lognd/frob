//! A command-provider evidence record never holds an absolute home path at capture time (~6V3WPZD).

// frob:ticket 01M4K55NZMZWBGMZ6PP6V3WPZD

use std::path::Path;

use frob_evidence::provider::{Capture, build_record};
use frob_evidence::record::{EvidenceRecord, Provider};
use frob_evidence::scrub::PathScrub;
use frob_evidence::{EvidenceTable, NonPassing};
use frob_ledger::privacy::find_home_path;

/// A capture whose transcript, test names and failed names all carry `text`.
fn capture(text: &str) -> Capture {
    Capture {
        exit_code: Some(1),
        passed: false,
        measured: true,
        tests: vec![format!("t at {text}")],
        failed_tests: vec![format!("t at {text}")],
        non_passing: NonPassing::default(),
        transcript: text.to_owned(),
    }
}

/// Build a record for `text` (also the ref) under `scrub`, using a throwaway repository.
fn record(scrub: &PathScrub, text: &str) -> EvidenceRecord {
    let dir = tempfile::tempdir().expect("tempdir");
    let repo = gob_git::Repo::init(dir.path()).expect("init");
    let store =
        frob_evidence::store::BlobStore::open(&EvidenceTable::default(), &repo).expect("store");
    build_record(
        &store,
        scrub,
        Provider::Command,
        text,
        &capture(text),
        &[1],
        frob_ledger::model::Stamp::from_unix(1_800_000_000),
    )
    .expect("record")
}

/// Every text field of `rec`, as the event would carry it.
fn fields(rec: &EvidenceRecord) -> String {
    format!(
        "{}\n{}\n{}\n{}\n{}",
        rec.reference,
        rec.inline.clone().unwrap_or_default(),
        rec.tests.join("\n"),
        rec.failed_tests.join("\n"),
        rec.uri.clone().unwrap_or_default()
    )
}

fn assert_clean(rec: &EvidenceRecord) {
    let all = fields(rec);
    assert!(
        find_home_path(all.as_bytes()).is_none(),
        "home path survived capture: {all}"
    );
}

fn scrub(home: Option<&str>) -> PathScrub {
    PathScrub::with_home(
        Path::new("/srv/app"),
        Path::new("/srv/app-wt/T1"),
        home.map(Path::new),
    )
    .sweeping_foreign_homes()
}

// frob:tests crates/frob-evidence/src/scrub.rs::PathScrub.new
// frob:tests crates/frob-evidence/src/provider.rs::build_record
#[test]
fn capture_never_holds_home_path_in_any_field() {
    let text = "ran /home/logan/bin/x then /home/logan/y and /home/logan2/z; err C:\\Users\\bo\\p";
    let rec = record(&scrub(Some("/home/logan/")), text);
    assert_clean(&rec);
    let all = fields(&rec);
    assert!(all.contains("~/bin/x") && all.contains("~/y"), "{all}");
    assert!(
        all.contains("~other/z"),
        "a prefix-sharing home is another user: {all}"
    );
}

// frob:tests crates/frob-evidence/src/scrub.rs::PathScrub.sweeping_foreign_homes
#[test]
fn capture_clears_home_paths_when_home_is_unset() {
    let rec = record(&scrub(None), "cat /home/logan/a /Users/ann/b /root/c");
    assert_clean(&rec);
}

#[test]
fn capture_clears_windows_style_home() {
    let rec = record(
        &scrub(Some("C:\\Users\\bo")),
        "C:\\Users\\bo\\x C:/Users/bo/y C:\\\\Users\\\\bo\\\\z",
    );
    assert_clean(&rec);
}

#[test]
fn capture_keeps_non_ascii_output_clean() {
    let rec = record(
        &scrub(Some("/home/logan")),
        "caf\u{e9} \u{fffd} /home/logan/\u{e9}",
    );
    assert_clean(&rec);
}
