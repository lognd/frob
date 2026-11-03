//! Direct tests of `doctor::report` (frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5).

// frob:tests crates/grimble/src/doctor.rs::report
#[test]
fn report_lists_the_languages_and_config_of_an_empty_repository() {
    let dir = tempfile::tempdir().expect("tempdir");
    let payload = grimble::doctor::report(dir.path()).expect("doctor succeeds");
    assert!(!payload.data.languages.is_empty());
    assert!(!payload.data.config.status.is_empty());
}
