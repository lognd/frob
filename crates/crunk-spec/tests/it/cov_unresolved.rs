//! Direct calls to small public methods whose names are shared with other types.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use crunk_spec::phase::Phase;
use crunk_spec::table::{GameConfig, ReviewConfig};

// frob:tests crates/crunk-spec/src/phase.rs::Phase.as_str
#[test]
fn phase_spells_itself_in_lowercase() {
    assert_eq!(Phase::as_str(Phase::Discovery), "discovery");
    assert_eq!(Phase::as_str(Phase::Live), "live");
}

// frob:tests crates/crunk-spec/src/table.rs::ReviewConfig.is_default
#[test]
fn a_default_review_table_reports_itself_default() {
    assert!(ReviewConfig::is_default(&ReviewConfig::default()));
}

// frob:tests crates/crunk-spec/src/table.rs::GameConfig.missing
#[test]
fn a_default_game_table_lacks_every_coverage_key() {
    assert!(!GameConfig::missing(&GameConfig::default()).is_empty());
}
