//! Checks over the game artifacts: every mechanic needs an FTUE entry or an explicit none, every
//! feedback event needs a known accessibility toggle, a guideline marked met needs evidence, every
//! input action needs a glyph per declared device and every HUD element must sit in a declared
//! profile. A load problem is a located schema finding; absent files are silent.

// frob:ticket 01M5XCZ1FM4GWNE4T7SQ905APV

use std::collections::BTreeSet;

use crunk_spec::game_files::GameSet;

/// What a game-artifact finding is about.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum GxFileIssue {
    /// A game file is malformed, names an unknown guideline or repeats a name.
    Schema,
    /// A mechanic has no FTUE entry and no explicit none.
    NoFtue,
    /// A feedback event names no accessibility toggle.
    NoToggle,
    /// A guideline is marked met with no evidence.
    NoEvidence,
    /// A device has no glyph for some input actions.
    NoGlyph,
    /// A HUD element or feedback toggle references something not declared.
    Unresolved,
}

/// One game-artifact finding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GxFileFinding {
    /// What kind of finding.
    pub issue: GxFileIssue,
    /// The file it is about.
    pub path: String,
    /// The 1-based line, when known.
    pub line: Option<usize>,
    /// The human message.
    pub message: String,
}

/// The project facts the checks compare the artifacts against.
#[derive(Debug, Clone, Default)]
pub struct GxFileContext {
    /// Every declared input device.
    pub devices: BTreeSet<String>,
    /// Every declared HUD device profile.
    pub profiles: BTreeSet<String>,
    /// Every declared mechanic.
    pub mechanics: BTreeSet<String>,
    /// Every declared accessibility toggle.
    pub toggles: BTreeSet<String>,
}

/// A finding without a line.
fn finding(issue: GxFileIssue, path: &str, message: String) -> GxFileFinding {
    GxFileFinding {
        issue,
        path: path.to_owned(),
        line: None,
        message,
    }
}

/// Run every game-artifact check. Findings come in load problems, ftue, feedback, gx, input, hud order.
#[must_use]
pub fn check_gx_files(set: &GameSet, ctx: &GxFileContext) -> Vec<GxFileFinding> {
    use crunk_spec::game_files as gf;
    let mut out: Vec<GxFileFinding> = set
        .problems
        .iter()
        .map(|p| GxFileFinding {
            issue: GxFileIssue::Schema,
            path: p.path.clone(),
            line: p.line,
            message: p.message.clone(),
        })
        .collect();
    if let Some(ftue) = &set.ftue {
        for m in &ctx.mechanics {
            if !ftue.entries.iter().any(|e| e.mechanic == *m) {
                out.push(finding(
                    GxFileIssue::NoFtue,
                    gf::FTUE_FILE,
                    format!("mechanic `{m}` has no ftue entry and no explicit none"),
                ));
            }
        }
    }
    for e in set.feedback.iter().flat_map(|f| &f.events) {
        match &e.toggle {
            None => out.push(finding(
                GxFileIssue::NoToggle,
                gf::FEEDBACK_FILE,
                format!("feedback event `{}` has no accessibility toggle", e.event),
            )),
            Some(t) if !ctx.toggles.contains(t) => out.push(finding(
                GxFileIssue::Unresolved,
                gf::FEEDBACK_FILE,
                format!("feedback event `{}` toggle `{t}` is not declared", e.event),
            )),
            Some(_) => {}
        }
    }
    for i in set.gx.iter().flat_map(|g| &g.items) {
        if i.met && i.evidence.is_none() {
            out.push(finding(
                GxFileIssue::NoEvidence,
                gf::GX_FILE,
                format!("guideline `{}` is marked met with no evidence", i.id),
            ));
        }
    }
    if let Some(input) = &set.input {
        for device in &ctx.devices {
            let missing: Vec<&str> = input
                .actions
                .iter()
                .filter(|a| !a.glyphs.contains(device))
                .map(|a| a.action.as_str())
                .collect();
            if !missing.is_empty() {
                out.push(finding(
                    GxFileIssue::NoGlyph,
                    gf::INPUT_FILE,
                    format!("device `{device}` has no glyph for {}", missing.join(", ")),
                ));
            }
        }
    }
    for (path, h) in &set.hud {
        if !ctx.profiles.contains(&h.profile) {
            out.push(finding(
                GxFileIssue::Unresolved,
                path,
                format!(
                    "hud element `{}` is in undeclared profile `{}`",
                    h.element, h.profile
                ),
            ));
        }
    }
    tracing::debug!(findings = out.len(), "game file checks done");
    out
}
