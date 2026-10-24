//! Repository paths (`RelPath`), host-path bridges and display paths (`Shown`).
//!
//! frob:ticket 01M41S1KC8PQFTVDETMARHP82G
//! See `docs/design/paths.md` sections 1 and 4. The bridge logic is written once over a
//! [`PathStyle`] with the `typed-path` crate so Windows paths are testable on any host.

mod error;
mod relpath;
mod shown;
mod style;

pub use error::PathError;
pub use relpath::RelPath;
pub use shown::{Shown, exact_text, forward_slashes};
pub use style::{PathStyle, validate_component};
