//! Gap cells may name a ticket; the page renders it as `Gap (~ID)`.

// frob:ticket 01M5GM4B049PYVSS1CVA1XEKJS

use gob_caps::{Capability, GAP_TICKETS, Lang, Precision, gap_ticket, precision};

#[test]
// frob:tests crates/gob-caps/src/capability.rs::Precision.cell_with_ticket
fn a_gap_with_a_ticket_renders_it() {
    assert_eq!(
        Precision::None.cell_with_ticket(Some("~A1XEKJS")),
        "Gap (~A1XEKJS)"
    );
    assert_eq!(Precision::None.cell_with_ticket(None), "Gap");
    assert_eq!(
        Precision::Syntactic.cell_with_ticket(Some("~A1XEKJS")),
        "Implemented"
    );
}

#[test]
// frob:tests crates/gob-caps/src/matrix.rs::gap_ticket
fn named_tickets_sit_on_gap_cells_and_others_are_bare() {
    for g in GAP_TICKETS {
        assert_eq!(precision(g.lang, g.cap), Precision::None);
        assert_eq!(gap_ticket(g.lang, g.cap), Some(g.ticket));
    }
    assert_eq!(gap_ticket(Lang::Rust, Capability::ResolveRef), None);
    assert_eq!(gap_ticket(Lang::Go, Capability::ResolveRef), None);
}
