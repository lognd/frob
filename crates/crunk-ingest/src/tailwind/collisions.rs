//! Theme keys that silently redefine a Tailwind default, and their waivers.
//!
//! Under `theme.extend` (and v4 `@theme`) a key that equals a default key replaces the default's
//! value: a spacing key `4` set to `4px` turns `p-4` from 1rem into 4px. The collision is a fact
//! of the ingest; whether it is a problem is for a rule. A `crunk:waive` comment on the key's
//! line or the line above acknowledges it (v1 T-0179: the only other way to silence it was
//! renaming every class).

// frob:ticket 01M43ARZ3VCNDX20C9BZZCCYHY

use crunk_tailwind::defaults::{
    V3_BORDER_RADIUS_KEYS, V3_COLOR_NAMES, V3_FONT_SIZE_KEYS, V3_SPACING_KEYS, V3_Z_INDEX_KEYS,
    V4_BORDER_RADIUS_KEYS, V4_COLOR_NAMES, V4_FONT_SIZE_KEYS, has_key, is_v4_spacing_key,
};
use serde::{Deserialize, Serialize};

/// The rule id a collision is waived under.
pub const COLLISION_RULE: &str = "TW006";

/// A theme key that redefines a Tailwind default key.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ThemeCollision {
    /// The Tailwind theme section (`spacing`, `borderRadius`, or the v4 namespace).
    pub section: String,
    /// The colliding key.
    pub key: String,
    /// The 1-based line of the key in the config (1 when unknown).
    pub line: u32,
    /// The reason of the `crunk:waive` that acknowledges it, if any (empty when no reason given).
    pub waived: Option<String>,
}

/// Whether `key` in v3 `section` is a Tailwind default key.
pub(crate) fn is_v3_default(section: &str, key: &str) -> bool {
    match section {
        "spacing" | "width" | "height" | "minWidth" | "minHeight" | "maxWidth" | "maxHeight" => {
            has_key(V3_SPACING_KEYS, key)
        }
        "borderRadius" => has_key(V3_BORDER_RADIUS_KEYS, key),
        "fontSize" => has_key(V3_FONT_SIZE_KEYS, key),
        "zIndex" => has_key(V3_Z_INDEX_KEYS, key),
        "colors" | "color" => has_key(V3_COLOR_NAMES, key),
        _ => false,
    }
}

/// Whether the v4 theme variable `--name` redefines a Tailwind 4 default.
pub(crate) fn is_v4_default(raw_name: &str) -> Option<(&'static str, String)> {
    let bare = raw_name.strip_prefix("--")?;
    let (namespace, key) = [
        ("spacing", "spacing-"),
        ("radius", "radius-"),
        ("text", "text-"),
        ("color", "color-"),
    ]
    .iter()
    .find_map(|(ns, prefix)| bare.strip_prefix(prefix).map(|k| (*ns, k.to_owned())))?;
    let hit = match namespace {
        "spacing" => is_v4_spacing_key(&key),
        "radius" => has_key(V4_BORDER_RADIUS_KEYS, &key),
        "text" => has_key(V4_FONT_SIZE_KEYS, &key),
        "color" => has_key(V4_COLOR_NAMES, &key),
        _ => false,
    };
    hit.then_some((namespace, key))
}

/// The reason of the `crunk:waive COLLISION_RULE` comment on `line` or the line above it.
pub(crate) fn waiver_for(source: &str, line: u32) -> Option<String> {
    let lines: Vec<&str> = source.lines().collect();
    let idx = usize::try_from(line).ok()?.checked_sub(1)?;
    let candidates = [Some(idx), idx.checked_sub(1)];
    for i in candidates.into_iter().flatten() {
        let Some(text) = lines.get(i) else {
            continue;
        };
        let Some(pos) = text.find("crunk:waive") else {
            continue;
        };
        let args = text[pos + "crunk:waive".len()..]
            .trim()
            .trim_end_matches("*/")
            .trim();
        let mut words = args.splitn(2, char::is_whitespace);
        if words.next() != Some(COLLISION_RULE) {
            continue;
        }
        let rest = words.next().unwrap_or_default();
        let reason = rest
            .split_once("reason=")
            .map(|(_, r)| r.trim().trim_matches(['"', '\'']).to_owned())
            .unwrap_or_default();
        return Some(reason);
    }
    None
}
