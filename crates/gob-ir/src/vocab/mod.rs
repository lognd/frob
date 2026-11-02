//! Finding vocabulary shared by the evaluator and the rule layer: ids, severities, findings and
//! the unresolved reasons. Lives in gob-ir (layer 4) so gob-rules (layer 5) re-exports it and the
//! edge points down (boundaries.md 6.1).

pub mod finding;
pub mod id;
pub mod nature;
pub mod required;
pub mod severity;
pub mod unresolved;
