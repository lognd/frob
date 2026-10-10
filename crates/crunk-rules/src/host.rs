//! The host trait crunk's `#[rule]` declarations evaluate against.

// frob:ticket 01M43ATASM383KB9130JY79XVV
// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use crunk_ingest::ProjectStyles;
use crunk_spec::DesignSpec;

use crate::tailwind::TailwindFacts;

/// What a crunk rule may ask of its product: the validated design spec and the ingested styles.
///
/// Both default to `None` (no valid `crunk.toml`, nothing ingested), which is what a rule that
/// reads only a file's text sees. A rule that needs either returns a reason from `inapplicable`
/// when it is absent, so the pipeline counts the skip instead of reporting a clean pass.
pub trait CrunkHost {
    /// The validated `crunk.toml`, when the project has a usable one.
    fn spec(&self) -> Option<&DesignSpec> {
        None
    }

    /// Every ingested stylesheet and JSX source of the project, when ingest ran.
    fn styles(&self) -> Option<&ProjectStyles> {
        None
    }

    /// The Tailwind theme and compiled utilities, when the pipeline collected them (the TW rules'
    /// side input).
    fn tailwind(&self) -> Option<&TailwindFacts> {
        None
    }
}

/// Why a rule that reads the spec and the ingested styles cannot run on `host`, if it cannot.
pub fn missing_inputs<H: CrunkHost + ?Sized>(host: &H) -> Option<String> {
    if host.spec().is_none() {
        return Some("no valid crunk.toml".to_owned());
    }
    if host.styles().is_none() {
        return Some("no stylesheets were ingested".to_owned());
    }
    None
}
