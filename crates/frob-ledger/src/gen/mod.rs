//! The generated pages of the ticket branch (`navigation.md` section 3), one renderer per module.
// frob:ticket 01M3ZX868H7TQ34ZDPXY13NRRG

pub mod by_id;
pub mod glossary; // frob:ticket 01M3ZX86CE8WDE9PJHNS90ZNMR

use crate::reindex::Generator;

/// Every renderer `ticket reindex` and the TICK007 replay run, in order.
pub const GENERATORS: &[Generator] = &[by_id::render, glossary::render];
