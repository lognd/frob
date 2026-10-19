//! The host trait crunk's `#[rule]` declarations evaluate against.

// frob:ticket 01M43ATASM383KB9130JY79XVV
// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use crunk_ingest::ProjectStyles;
use crunk_spec::DesignSpec;

use crate::review::ReviewFacts;
use crate::scene_files::SceneFacts;
use crate::tailwind::TailwindFacts;
use crate::token_files::TokenFacts;

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

    // frob:ticket 01M4CXR0EQH7WHQSNXCGKXE3V8
    /// The authored `design/tokens/*.toml` files, when the pipeline loaded them (the TOKEN rules'
    /// input).
    fn tokens(&self) -> Option<&TokenFacts> {
        None
    }

    // frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62
    /// The authored `design/scenes/*.scene.json` files, solved (the LAYOUT and RESP rules' input).
    fn scenes(&self) -> Option<&SceneFacts> {
        None
    }

    // frob:ticket 01M4CXSM408E7A05DWKENDB7V4
    /// The judged human reviews, when the pipeline gathered them (HUMAN001 and HUMAN002's input).
    fn reviews(&self) -> Option<&ReviewFacts> {
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

/// Why a TOKEN rule cannot run on `host`, if it cannot: no valid spec, or no authored token files.
pub fn missing_token_inputs<H: CrunkHost + ?Sized>(host: &H) -> Option<String> {
    if host.spec().is_none() {
        return Some("no valid crunk.toml".to_owned());
    }
    match host.tokens() {
        Some(facts) if !facts.files.is_empty() => None,
        _ => Some("no design/tokens/*.toml files".to_owned()),
    }
}

/// Why a TOKEN rule that also reads the stylesheets cannot run on `host`, if it cannot.
pub fn missing_token_style_inputs<H: CrunkHost + ?Sized>(host: &H) -> Option<String> {
    missing_token_inputs(host).or_else(|| {
        host.styles()
            .is_none()
            .then(|| "no stylesheets were ingested".to_owned())
    })
}

/// How many authored token files `host` carries (the TOKEN rules' subject count).
pub fn token_subjects<H: CrunkHost + ?Sized>(host: &H) -> usize {
    host.tokens().map_or(0, |facts| facts.files.len())
}

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62
/// Why a LAYOUT or RESP rule cannot run on `host`, if it cannot: no valid spec, or no solved
/// scene files.
pub fn missing_scene_inputs<H: CrunkHost + ?Sized>(host: &H) -> Option<String> {
    if host.spec().is_none() {
        return Some("no valid crunk.toml".to_owned());
    }
    match host.scenes() {
        Some(facts) if !facts.files.is_empty() => None,
        _ => Some("no design/scenes/*.scene.json files".to_owned()),
    }
}

/// How many solved scene files `host` carries (the LAYOUT and RESP rules' subject count).
pub fn scene_subjects<H: CrunkHost + ?Sized>(host: &H) -> usize {
    host.scenes().map_or(0, |facts| facts.files.len())
}
