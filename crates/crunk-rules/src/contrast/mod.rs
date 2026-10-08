//! Contrast judgments shared by CONTRAST001 and the later contrast rules (port of
//! `crunk/rules/_contrast.py`): the WCAG 2.2 ratio is the gate.
//!
//! APCA is advisory and opt-in through `contrast_model` (crunk.md section 6); the spec does not
//! declare that key yet, so only the WCAG ratio is measured here.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use crunk_spec::DesignSpec;

use crate::mode::Mode;

/// One declared role pair measured in one mode.
#[derive(Debug, Clone, PartialEq)]
pub struct Measured {
    /// The role name from `[palette.roles]`.
    pub role: String,
    /// Palette name of the foreground.
    pub foreground: String,
    /// Palette name of the background.
    pub background: String,
    /// The WCAG 2.x contrast ratio of the pair.
    pub ratio: f64,
    /// The role's own floor (4.5 by default, lower for the large-text exception).
    pub floor: f64,
}

impl Measured {
    /// True when the ratio is below the role's floor.
    pub fn fails(&self) -> bool {
        self.ratio < self.floor
    }
}

/// Every `[palette.roles]` pair measured in `mode`, in declaration order.
///
/// A role naming a palette entry the mode lacks is skipped with a warning: the spec validates
/// role names at load, so it only happens for a mode palette that omits an entry.
pub fn measure_roles(spec: &DesignSpec, mode: Mode) -> Vec<Measured> {
    let palette = mode.palette(spec);
    let colour = |name: &str| palette.iter().find(|(n, _)| *n == name).map(|(_, c)| *c);
    spec.roles
        .iter()
        .filter_map(|(role, pair)| {
            let (Some(fg), Some(bg)) = (colour(&pair.foreground), colour(&pair.background)) else {
                tracing::warn!(role, mode = mode.name, "role names a colour the mode lacks");
                return None;
            };
            Some(Measured {
                role: role.clone(),
                foreground: pair.foreground.clone(),
                background: pair.background.clone(),
                ratio: fg.contrast_ratio(bg),
                floor: pair.floor,
            })
        })
        .collect()
}
