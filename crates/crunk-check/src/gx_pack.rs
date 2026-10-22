//! GX015-GX021: the game accessibility pack. Every rule reads the extended `[game]` table of
//! `crunk.toml` (profiles, devices, actions, colour-blind modes, subtitles) and, for the HUD
//! rules, the solved `design/scenes/*.scene.json` files (crunk.md sections 6 and 7).
//!
//! A rule fires only on a fact the declarations decide. When the data needed is absent (no
//! profile, no measured glyph height, an undeclared remap flag) the rule reports Unresolved with a
//! reason instead of guessing. The pack is silent when the project has no `[game]` table.
//!
//! The decisions are pure functions over the spec and the scene facts ([`decide`]); the
//! [`RepoGroup`] only turns each [`Verdict`] into a [`Finding`].

// frob:ticket 01M4CXSEFJEZDQFGESPKDEW049

use crunk_ingest::scene::{NodeKind, SceneNode};
use crunk_rules::scene_files::{SceneFacts, SceneFile, rect};
use crunk_spec::DesignSpec;
use crunk_spec::table::{GameConfig, GameProfile};
use gob_check::{RepoGroup, Snapshot};
use gob_rules::{Finding, Rule, RuleMeta, Severity, UnresolvedReason};
use gob_text::{FileId, FileInterner, Span, TextRange, TextSize};

use crate::Crunk;

/// The file spec-level findings anchor on.
const SPEC_FILE: &str = "crunk.toml";

/// Reference height the minimum text sizes are declared at.
const REFERENCE_HEIGHT: f32 = 1080.0;

/// Default console safe margin, percent of each edge (title-safe).
const CONSOLE_SAFE_PCT: f32 = 5.0;

/// Aspect ratios further apart than this fraction make a scale-based judgement unsound.
const ASPECT_TOLERANCE: f32 = 0.01;

/// Slack, in pixels, absorbing float rounding at the safe-area edge.
const EDGE_SLACK: f32 = 0.5;

/// Subtitle floor at 1080p when no profile is declared (the pc minimum).
const DEFAULT_SUBTITLE_FLOOR: u32 = 18;

/// A HUD element sits outside the profile's safe area.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "GX015",
    slug = "hud-safe-area",
    family = "GX",
    product = "crunk",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Gx015;

/// A text node is too small for the profile's viewing distance.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "GX016",
    slug = "text-size-at-distance",
    family = "GX",
    product = "crunk",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Gx016;

/// An action has no glyph for a supported input device.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "GX017",
    slug = "glyph-coverage",
    family = "GX",
    product = "crunk",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Gx017;

/// An action cannot be remapped.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "GX018",
    slug = "remap-coverage",
    family = "GX",
    product = "crunk",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Gx018;

/// A declared colour-blind mode is not a palette mode.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "GX019",
    slug = "colour-blind-mode",
    family = "GX",
    product = "crunk",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Gx019;

/// The subtitle settings are too small or lack a background or speaker labels.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "GX020",
    slug = "subtitle-options",
    family = "GX",
    product = "crunk",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Gx020;

/// A hold action has no non-hold alternative.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "GX021",
    slug = "hold-alternative",
    family = "GX",
    product = "crunk",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Gx021;

/// Where a verdict anchors: the spec file, or a node of a scene file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Anchor {
    /// `crunk.toml`, offset 0.
    Spec,
    /// A scene file by path and the byte offset of the node.
    Scene {
        /// Scene path relative to the project root.
        path: String,
        /// Byte offset of the node in the file.
        offset: usize,
    },
}

/// One decided result of a GX rule: a definite violation or an honest "cannot decide".
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Verdict {
    /// The rule id (`GX015`..`GX021`).
    pub rule: &'static str,
    /// Where the finding anchors.
    pub anchor: Anchor,
    /// The finding message.
    pub message: String,
    /// `Some(code)` when the rule could not decide and the finding is Unresolved.
    pub unresolved: Option<&'static str>,
}

impl Verdict {
    /// A definite violation.
    fn fire(rule: &'static str, anchor: Anchor, message: String) -> Self {
        Self {
            rule,
            anchor,
            message,
            unresolved: None,
        }
    }

    /// A case the data cannot decide, with the reason code.
    fn unresolved(rule: &'static str, anchor: Anchor, code: &'static str, message: String) -> Self {
        Self {
            rule,
            anchor,
            message,
            unresolved: Some(code),
        }
    }
}

/// Whether a scene file is a HUD: its stem is `hud` or ends in `.hud`, `-hud` or `_hud`.
fn is_hud(path: &str) -> bool {
    let name = path.rsplit('/').next().unwrap_or(path);
    let stem = name.strip_suffix(".scene.json").unwrap_or(name);
    stem == "hud" || [".hud", "-hud", "_hud"].iter().any(|s| stem.ends_with(s))
}

/// The percent of each edge kept clear in `profile` (declared, else 5 for a console, else 0).
fn safe_pct(profile: &GameProfile) -> f32 {
    match (profile.safe_area_pct, profile.kind.as_str()) {
        (Some(p), _) => px(p),
        (None, "console") => CONSOLE_SAFE_PCT,
        (None, _) => 0.0,
    }
}

/// The minimum text height at 1080p for `profile`: declared, else the kind default; `None` for
/// a mobile profile that declares none.
fn min_text_1080(profile: &GameProfile) -> Option<u32> {
    profile.min_text_px.or(match profile.kind.as_str() {
        "console" => Some(26),
        "pc" => Some(18),
        _ => None,
    })
}

/// Whether the scene's aspect ratio matches the profile's within [`ASPECT_TOLERANCE`].
fn same_aspect(file: &SceneFile, profile: &GameProfile) -> bool {
    let scene = file.scene.viewport.width / file.scene.viewport.height;
    let screen = px(profile.width) / px(profile.height);
    ((scene - screen) / screen).abs() <= ASPECT_TOLERANCE
}

/// GX015: HUD content outside the safe area of each profile.
fn hud_safe_area(game: &GameConfig, scenes: &SceneFacts) -> Vec<Verdict> {
    let huds: Vec<&SceneFile> = scenes.files.iter().filter(|f| is_hud(&f.path)).collect();
    if huds.is_empty() {
        return Vec::new();
    }
    if game.profiles.is_empty() {
        tracing::debug!("GX015: HUD scenes but no profile");
        return vec![Verdict::unresolved(
            "GX015",
            Anchor::Spec,
            "no-profiles",
            "the project has a HUD scene but `[game]` declares no `[[game.profile]]`; GX015 cannot tell which safe area applies".to_owned(),
        )];
    }
    let mut out = Vec::new();
    for file in huds {
        for profile in &game.profiles {
            if !same_aspect(file, profile) {
                tracing::debug!(scene = %file.path, profile = %profile.id, "GX015: aspect mismatch");
                out.push(Verdict::unresolved(
                    "GX015",
                    Anchor::Scene { path: file.path.clone(), offset: 0 },
                    "aspect-mismatch",
                    format!(
                        "the scene viewport and profile `{}` differ in aspect ratio; GX015 cannot scale the HUD to it",
                        profile.id
                    ),
                ));
                continue;
            }
            out.extend(outside_safe_area(file, profile));
        }
    }
    out
}

/// The content nodes of `file` that leave the safe area of `profile`.
fn outside_safe_area(file: &SceneFile, profile: &GameProfile) -> Vec<Verdict> {
    let sx = px(profile.width) / file.solve.viewport_width;
    let sy = px(profile.height) / file.solve.viewport_height;
    let (w, h) = (px(profile.width), px(profile.height));
    let pct = safe_pct(profile) / 100.0;
    let (left, top, right, bottom) = (w * pct, h * pct, w * (1.0 - pct), h * (1.0 - pct));
    let mut out = Vec::new();
    for node in file.solve.nodes.iter().filter(|n| file.is_content(n)) {
        let (x, y, nw, nh) = rect(node);
        let (x0, y0, x1, y1) = (x * sx, y * sy, (x + nw) * sx, (y + nh) * sy);
        if x0 < left - EDGE_SLACK
            || y0 < top - EDGE_SLACK
            || x1 > right + EDGE_SLACK
            || y1 > bottom + EDGE_SLACK
        {
            tracing::debug!(node = %node.id, profile = %profile.id, "GX015: outside safe area");
            out.push(Verdict::fire(
                "GX015",
                Anchor::Scene {
                    path: file.path.clone(),
                    offset: file.offset_of(&node.id),
                },
                format!(
                    "HUD node `{}` leaves the {}% safe area of profile `{}`",
                    node.id,
                    pct * 100.0,
                    profile.id
                ),
            ));
        }
    }
    out
}

/// Every text node of the scene tree rooted at `node`, preorder.
fn text_nodes<'a>(node: &'a SceneNode, out: &mut Vec<&'a SceneNode>) {
    if node.kind == NodeKind::Text && node.text.is_some() {
        out.push(node);
    }
    for child in &node.children {
        text_nodes(child, out);
    }
}

/// GX016: text below the minimum size of each profile, or not measurable.
fn text_size(game: &GameConfig, scenes: &SceneFacts) -> Vec<Verdict> {
    let mut out = Vec::new();
    for profile in &game.profiles {
        let Some(min_1080) = min_text_1080(profile) else {
            if !scenes.files.is_empty() {
                out.push(Verdict::unresolved(
                    "GX016",
                    Anchor::Spec,
                    "no-minimum-for-kind",
                    format!(
                        "profile `{}` is `{}` and declares no `min_text_px`; GX016 knows no minimum for it",
                        profile.id, profile.kind
                    ),
                ));
            }
            continue;
        };
        let min = px(min_1080) * px(profile.height) / REFERENCE_HEIGHT;
        for file in &scenes.files {
            let scale = px(profile.height) / file.scene.viewport.height;
            let mut nodes = Vec::new();
            text_nodes(&file.scene.root, &mut nodes);
            for node in nodes {
                let Some(run) = &node.text else { continue };
                let anchor = Anchor::Scene {
                    path: file.path.clone(),
                    offset: file.offset_of(&node.id),
                };
                let size = run.font_size * scale;
                if size < min {
                    out.push(Verdict::fire(
                        "GX016",
                        anchor,
                        format!(
                            "text `{}` is {size:.1}px on profile `{}`, below the {min:.1}px minimum",
                            node.id, profile.id
                        ),
                    ));
                } else if let Some(pct) = game.glyph_height_pct {
                    let glyph = size * px(pct) / 100.0;
                    if glyph < min {
                        out.push(Verdict::fire(
                            "GX016",
                            anchor,
                            format!(
                                "text `{}` has {glyph:.1}px glyphs on profile `{}`, below the {min:.1}px minimum",
                                node.id, profile.id
                            ),
                        ));
                    }
                } else {
                    out.push(Verdict::unresolved(
                        "GX016",
                        anchor,
                        "glyph-height-unmeasured",
                        format!(
                            "text `{}` passes on font size but `[game] glyph_height_pct` is not declared, so the drawn glyph height is unknown",
                            node.id
                        ),
                    ));
                }
            }
        }
    }
    out
}

/// GX017: actions lacking a glyph for a declared device.
fn glyphs(game: &GameConfig) -> Vec<Verdict> {
    if game.actions.is_empty() {
        return Vec::new();
    }
    if game.devices.is_empty() {
        return vec![Verdict::unresolved(
            "GX017",
            Anchor::Spec,
            "no-devices",
            "`[game]` declares actions but no `devices`; GX017 cannot tell which glyphs are needed"
                .to_owned(),
        )];
    }
    let mut out = Vec::new();
    for action in &game.actions {
        for device in game.devices.iter().filter(|d| !action.glyphs.contains(d)) {
            out.push(Verdict::fire(
                "GX017",
                Anchor::Spec,
                format!("action `{}` has no glyph for device `{device}`", action.id),
            ));
        }
    }
    out
}

/// GX018: actions that cannot be remapped, or whose remap flag is undeclared.
fn remap(game: &GameConfig) -> Vec<Verdict> {
    game.actions
        .iter()
        .filter_map(|a| match a.remappable {
            Some(true) => None,
            Some(false) => Some(Verdict::fire(
                "GX018",
                Anchor::Spec,
                format!("action `{}` is not remappable", a.id),
            )),
            None => Some(Verdict::unresolved(
                "GX018",
                Anchor::Spec,
                "remap-undeclared",
                format!("action `{}` does not declare `remappable`", a.id),
            )),
        })
        .collect()
}

/// GX019: declared colour-blind modes that are not palette modes.
fn colour_blind(game: &GameConfig, spec: &DesignSpec) -> Vec<Verdict> {
    if game.colour_blind_modes.is_empty() {
        return vec![Verdict::unresolved(
            "GX019",
            Anchor::Spec,
            "colour-blind-modes-undeclared",
            "`[game]` declares no `colour_blind_modes`; GX019 cannot tell which palette modes are expected".to_owned(),
        )];
    }
    game.colour_blind_modes
        .iter()
        .filter(|m| !spec.palette_modes.contains_key(m.as_str()))
        .map(|m| {
            Verdict::fire(
                "GX019",
                Anchor::Spec,
                format!("colour-blind mode `{m}` has no `[palette.modes.{m}]` table"),
            )
        })
        .collect()
}

/// GX020: subtitle size below the strictest profile floor, or background / speaker labels off.
fn subtitles(game: &GameConfig) -> Vec<Verdict> {
    let Some(sub) = &game.subtitles else {
        if game.coverage.iter().any(|c| c == "subtitle_format") {
            return vec![Verdict::unresolved(
                "GX020",
                Anchor::Spec,
                "subtitles-undeclared",
                "`[game]` covers `subtitle_format` but has no `[game.subtitles]` table".to_owned(),
            )];
        }
        return Vec::new();
    };
    let floor = game
        .profiles
        .iter()
        .filter_map(min_text_1080)
        .max()
        .unwrap_or(DEFAULT_SUBTITLE_FLOOR);
    let mut out = Vec::new();
    if let Some(size) = sub.size_px.filter(|s| *s < floor) {
        out.push(Verdict::fire(
            "GX020",
            Anchor::Spec,
            format!("subtitle size {size}px is below the {floor}px floor at 1080p"),
        ));
    }
    if sub.background == Some(false) {
        out.push(Verdict::fire(
            "GX020",
            Anchor::Spec,
            "subtitles offer no background".to_owned(),
        ));
    }
    if sub.speaker_labels == Some(false) {
        out.push(Verdict::fire(
            "GX020",
            Anchor::Spec,
            "subtitles show no speaker labels".to_owned(),
        ));
    }
    out
}

/// GX021: hold actions without an alternative, or with an undeclared hold flag.
fn hold(game: &GameConfig) -> Vec<Verdict> {
    game.actions
        .iter()
        .filter_map(|a| match (a.hold, &a.hold_alternative) {
            (Some(true), None) => Some(Verdict::fire(
                "GX021",
                Anchor::Spec,
                format!("hold action `{}` has no `hold_alternative`", a.id),
            )),
            (None, _) => Some(Verdict::unresolved(
                "GX021",
                Anchor::Spec,
                "hold-undeclared",
                format!("action `{}` does not declare `hold`", a.id),
            )),
            _ => None,
        })
        .collect()
}

/// Every verdict of the pack for `spec` and `scenes`; empty without a `[game]` table.
pub fn decide(spec: &DesignSpec, scenes: Option<&SceneFacts>) -> Vec<Verdict> {
    let Some(game) = &spec.game else {
        tracing::debug!("GX pack: no [game] table, silent");
        return Vec::new();
    };
    let empty = SceneFacts::default();
    let scenes = scenes.unwrap_or(&empty);
    let mut out = hud_safe_area(game, scenes);
    out.extend(text_size(game, scenes));
    out.extend(glyphs(game));
    out.extend(remap(game));
    out.extend(colour_blind(game, spec));
    out.extend(subtitles(game));
    out.extend(hold(game));
    tracing::info!(verdicts = out.len(), "GX pack decided");
    out
}

/// Turn one verdict into a finding, interning its file.
fn to_finding(v: &Verdict, files: &mut FileInterner) -> Option<Finding> {
    let id = [
        &Gx015 as &dyn Rule,
        &Gx016,
        &Gx017,
        &Gx018,
        &Gx019,
        &Gx020,
        &Gx021,
    ]
    .iter()
    .map(|r| r.meta())
    .find(|m| m.id == v.rule)?
    .rule_id()
    .ok()?;
    let (path, offset): (&str, usize) = match &v.anchor {
        Anchor::Spec => (SPEC_FILE, 0),
        Anchor::Scene { path, offset } => (path, *offset),
    };
    let file: FileId = files.intern(path);
    let at = TextSize::from(u32::try_from(offset).unwrap_or(0));
    let span = Some(Span::new(file, TextRange::at(at, TextSize::from(0))));
    Some(match v.unresolved {
        None => Finding::new(id, Severity::Error, span, v.message.clone(), path),
        Some(code) => Finding::new(id, Severity::Unresolved, span, v.message.clone(), path)
            .with_reason(UnresolvedReason::from_code(code)),
    })
}

/// The metadata of every GX pack rule.
fn metas() -> Vec<&'static RuleMeta> {
    vec![
        Gx015.meta(),
        Gx016.meta(),
        Gx017.meta(),
        Gx018.meta(),
        Gx019.meta(),
        Gx020.meta(),
        Gx021.meta(),
    ]
}

/// The repo group that emits GX015-GX021.
pub fn group() -> RepoGroup<Crunk> {
    RepoGroup::new(
        "repo:gx",
        metas(),
        |snap: &Snapshot<Crunk>, files: &mut FileInterner| {
            let Some(spec) = &snap.inputs.spec else {
                return Vec::new();
            };
            decide(spec, snap.inputs.scenes.as_ref())
                .iter()
                .filter_map(|v| to_finding(v, files))
                .collect()
        },
    )
    .counting(|snap| {
        let Some(game) = snap.inputs.spec.as_ref().and_then(|s| s.game.as_ref()) else {
            return Vec::new();
        };
        vec![
            ("GX017", game.actions.len()),
            ("GX018", game.actions.len()),
            ("GX021", game.actions.len()),
            ("GX019", game.colour_blind_modes.len()),
        ]
    })
}

/// A pixel count as a float; pixel counts are far below the 2^24 where `f32` loses integers.
#[allow(clippy::cast_precision_loss)]
fn px(value: u32) -> f32 {
    value as f32
}
