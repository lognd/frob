//! The generated pages of the ticket branch (`navigation.md` section 3), one renderer per module.
// frob:ticket 01M3ZX868H7TQ34ZDPXY13NRRG

pub mod by_id;
pub mod code_readme; // frob:ticket 01M3ZX87403VR4YVK4QMJ7KPBV
pub mod epic; // frob:ticket 01M3ZX860YGPCJE6ETPJADMNFE
pub mod glossary; // frob:ticket 01M3ZX86CE8WDE9PJHNS90ZNMR
pub mod good_first; // frob:ticket 01M3ZX87QPD21PCSSSAJHVK7HJ
pub mod guide; // frob:ticket 01M3ZX86G8HFRDA78PBVFSTJNW
pub mod indexes; // frob:ticket 01M3ZX864QGR220FTRGCDPXYZD
pub mod readme; // frob:ticket 01M3ZX860YGPCJE6ETPJADMNFE

use crate::reindex::Generator;

/// Every renderer `ticket reindex` and the TICK007 replay run, in order.
pub const GENERATORS: &[Generator] = &[
    by_id::render,
    readme::render,
    epic::render,
    glossary::render,
    indexes::render,
    guide::render,
    good_first::render,
];
