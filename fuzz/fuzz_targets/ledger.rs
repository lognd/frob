//! Fuzz ledger event decoding and the fold: no panic, and decoded events round-trip.
// frob:ticket 01M47QV3BRRZZSMJ5Q79N8G5S2
#![no_main]

use frob_ledger::event::Event;
use frob_ledger::fold::fold;
use frob_ledger::id::{EventId, TicketId};
use libfuzzer_sys::fuzz_target;

fuzz_target!(|text: &str| {
    let id = EventId::mint();
    let Ok(event) = Event::parse(id, text) else {
        return;
    };
    if let Ok(printed) = event.to_toml() {
        let again = Event::parse(id, &printed).expect("printed event must re-parse");
        assert_eq!(event, again, "event TOML must round-trip");
    }
    let _ = fold(TicketId::mint(), &[event]);
});
