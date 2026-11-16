//! Game artifacts under `design/game`: `hud/*.toml` (one HUD element per file), `input.toml`,
//! `ftue.toml`, `feedback.toml` and `gx-a11y.toml` (keyed to the Game Accessibility Guidelines).
//! Parsing is pure; [`load_game`] reads a project, reports each bad file as a located problem and
//! treats an absent file as nothing declared.

// frob:ticket 01M5XCZ1FM4GWNE4T7SQ905APV

use std::path::Path;

use serde::Deserialize;

use crate::qa::load_dir;
use crate::research::{ResearchError, ResearchProblem, parse_toml};

/// Directory holding HUD element files, relative to the project root.
pub const HUD_DIR: &str = "design/game/hud";
/// The input map file, relative to the project root.
pub const INPUT_FILE: &str = "design/game/input.toml";
/// The first-time-user-experience file, relative to the project root.
pub const FTUE_FILE: &str = "design/game/ftue.toml";
/// The feedback events file, relative to the project root.
pub const FEEDBACK_FILE: &str = "design/game/feedback.toml";
/// The guideline checklist file, relative to the project root.
pub const GX_FILE: &str = "design/game/gx-a11y.toml";

/// The guideline ids a `gx-a11y.toml` item may use (Game Accessibility Guidelines, by topic).
pub const GUIDELINE_IDS: [&str; 12] = [
    "subtitles",
    "remappable-controls",
    "colour-independence",
    "text-size",
    "difficulty-options",
    "hold-alternatives",
    "pause-anywhere",
    "audio-cues-visual",
    "contrast",
    "motion-reduction",
    "tutorial-skippable",
    "one-handed-play",
];

/// One HUD element (`design/game/hud/<id>.toml`) and the device profile it belongs to.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HudElement {
    /// The element's unique name.
    pub element: String,
    /// The device profile the element is laid out for.
    pub profile: String,
}

/// One input action and the devices it has a glyph for.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct InputAction {
    /// The action name.
    pub action: String,
    /// Devices that have a glyph for it.
    #[serde(default)]
    pub glyphs: Vec<String>,
}

/// The input map (`input.toml`).
#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct InputFile {
    /// Every action.
    #[serde(default)]
    pub actions: Vec<InputAction>,
}

/// How one mechanic is taught, or an explicit statement that it needs no teaching.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FtueEntry {
    /// The mechanic name.
    pub mechanic: String,
    /// The tutorial step that teaches it.
    #[serde(default)]
    pub step: Option<String>,
    /// True when the mechanic is deliberately not taught.
    #[serde(default)]
    pub none: bool,
}

/// The first-time-user-experience file (`ftue.toml`).
#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FtueFile {
    /// Every entry.
    #[serde(default)]
    pub entries: Vec<FtueEntry>,
}

/// One feedback event and the accessibility toggle that governs it.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FeedbackEvent {
    /// The event name.
    pub event: String,
    /// The accessibility toggle that can reduce or replace it.
    #[serde(default)]
    pub toggle: Option<String>,
}

/// The feedback events file (`feedback.toml`).
#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FeedbackFile {
    /// Every event.
    #[serde(default)]
    pub events: Vec<FeedbackEvent>,
}

/// One guideline checklist item.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GxItem {
    /// The guideline id, one of [`GUIDELINE_IDS`].
    pub id: String,
    /// True when the project claims to meet it.
    #[serde(default)]
    pub met: bool,
    /// What shows it is met.
    #[serde(default)]
    pub evidence: Option<String>,
}

/// The guideline checklist (`gx-a11y.toml`).
#[derive(Debug, Clone, Default, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GxFile {
    /// Every item.
    #[serde(default)]
    pub items: Vec<GxItem>,
}

/// Parse one HUD element file.
///
/// # Errors
/// [`ResearchError`] for invalid TOML or the wrong schema.
pub fn parse_hud(text: &str) -> Result<HudElement, ResearchError> {
    parse_toml(text)
}

/// Parse the input map.
///
/// # Errors
/// [`ResearchError`] for invalid TOML or the wrong schema.
pub fn parse_input(text: &str) -> Result<InputFile, ResearchError> {
    parse_toml(text)
}

/// Parse the FTUE file.
///
/// # Errors
/// [`ResearchError`] for invalid TOML or the wrong schema.
pub fn parse_ftue(text: &str) -> Result<FtueFile, ResearchError> {
    parse_toml(text)
}

/// Parse the feedback events file.
///
/// # Errors
/// [`ResearchError`] for invalid TOML or the wrong schema.
pub fn parse_feedback(text: &str) -> Result<FeedbackFile, ResearchError> {
    parse_toml(text)
}

/// Parse the guideline checklist; an id outside [`GUIDELINE_IDS`] is a schema error.
///
/// # Errors
/// [`ResearchError`] for invalid TOML, the wrong schema or an unknown guideline id.
pub fn parse_gx(text: &str) -> Result<GxFile, ResearchError> {
    let file: GxFile = parse_toml(text)?;
    match file
        .items
        .iter()
        .find(|i| !GUIDELINE_IDS.contains(&i.id.as_str()))
    {
        Some(bad) => Err(ResearchError {
            line: None,
            message: format!("unknown guideline id `{}`", bad.id),
        }),
        None => Ok(file),
    }
}

/// Everything loaded from a project's game artifacts.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct GameSet {
    /// HUD elements with their paths, sorted by path.
    pub hud: Vec<(String, HudElement)>,
    /// The input map, when the file exists.
    pub input: Option<InputFile>,
    /// The FTUE entries, when the file exists.
    pub ftue: Option<FtueFile>,
    /// The feedback events, when the file exists.
    pub feedback: Option<FeedbackFile>,
    /// The guideline checklist, when the file exists.
    pub gx: Option<GxFile>,
    /// Files that were unreadable, invalid or repeated a name.
    pub problems: Vec<ResearchProblem>,
}

impl GameSet {
    /// True when no game artifact file exists (problems aside).
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.hud.is_empty()
            && self.input.is_none()
            && self.ftue.is_none()
            && self.feedback.is_none()
            && self.gx.is_none()
    }
}

/// Read and parse one optional file; a missing file is `None`, a bad one is a recorded problem.
fn read_one<T>(
    root: &Path,
    rel: &str,
    parse: fn(&str) -> Result<T, ResearchError>,
    problems: &mut Vec<ResearchProblem>,
) -> Option<T> {
    let text = std::fs::read_to_string(root.join(rel)).ok()?;
    parse(&text)
        .map_err(|e| {
            tracing::warn!(rel, message = %e.message, "game file rejected");
            problems.push(ResearchProblem {
                path: rel.to_owned(),
                line: e.line,
                message: e.message,
            });
        })
        .ok()
}

/// Read every game artifact under `root`. Missing files contribute nothing; a bad file becomes a
/// [`ResearchProblem`] and a repeated HUD element name is refused.
#[must_use]
pub fn load_game(root: &Path) -> GameSet {
    let mut set = GameSet::default();
    set.hud = load_dir(
        root,
        HUD_DIR,
        parse_hud,
        |h| &h.element,
        "element",
        &mut set.problems,
    );
    set.input = read_one(root, INPUT_FILE, parse_input, &mut set.problems);
    set.ftue = read_one(root, FTUE_FILE, parse_ftue, &mut set.problems);
    set.feedback = read_one(root, FEEDBACK_FILE, parse_feedback, &mut set.problems);
    set.gx = read_one(root, GX_FILE, parse_gx, &mut set.problems);
    tracing::debug!(
        hud = set.hud.len(),
        problems = set.problems.len(),
        "loaded game files"
    );
    set
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-spec/src/game_files.rs::parse_hud
    #[test]
    fn hud_parses() {
        let h = parse_hud("element = \"health\"\nprofile = \"tv\"\n").expect("ok");
        assert_eq!(h.profile, "tv");
    }

    // frob:tests crates/crunk-spec/src/game_files.rs::parse_input
    #[test]
    fn input_parses() {
        let f = parse_input("[[actions]]\naction = \"jump\"\nglyphs = [\"pad\"]\n").expect("ok");
        assert_eq!(f.actions[0].glyphs, ["pad"]);
    }

    // frob:tests crates/crunk-spec/src/game_files.rs::parse_ftue
    #[test]
    fn ftue_parses() {
        let f = parse_ftue("[[entries]]\nmechanic = \"dash\"\nnone = true\n").expect("ok");
        assert!(f.entries[0].none);
    }

    // frob:tests crates/crunk-spec/src/game_files.rs::parse_feedback
    #[test]
    fn feedback_parses() {
        let f = parse_feedback("[[events]]\nevent = \"hit\"\ntoggle = \"no-shake\"\n").expect("ok");
        assert_eq!(f.events[0].toggle.as_deref(), Some("no-shake"));
    }

    // frob:tests crates/crunk-spec/src/game_files.rs::parse_gx
    #[test]
    fn gx_parses() {
        let f = parse_gx("[[items]]\nid = \"subtitles\"\nmet = true\n").expect("ok");
        assert!(f.items[0].met);
    }

    // frob:tests crates/crunk-spec/src/game_files.rs::parse_gx
    #[test]
    fn unknown_guideline_id_is_rejected() {
        let e = parse_gx("[[items]]\nid = \"nope\"\n").expect_err("bad");
        assert!(e.message.contains("nope"));
    }

    // frob:tests crates/crunk-spec/src/game_files.rs::load_game
    #[test]
    fn load_tolerates_empty_and_reports_bad_files() {
        let dir = tempfile::tempdir().expect("tmp");
        assert!(load_game(dir.path()).is_empty());
        let game = dir.path().join("design/game");
        std::fs::create_dir_all(&game).expect("mk");
        std::fs::write(game.join("gx-a11y.toml"), "[[items]]\nid = \"nope\"\n").expect("w");
        std::fs::write(game.join("ftue.toml"), "[[entries]]\nmechanic = \"a\"\n").expect("w");
        let set = load_game(dir.path());
        assert_eq!(set.problems.len(), 1);
        assert!(set.ftue.is_some());
    }
}
