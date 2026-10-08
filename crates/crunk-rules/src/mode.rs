//! Modes: the colour contexts (light, dark, ...) every colour and contrast rule runs once per.
//!
//! crunk.md section 6: "contrast for declared pairs in every mode". The spec declares one palette
//! today, so [`modes`] yields the single [`Mode::DEFAULT`]; the rules already loop over it, and the
//! colour-blind and theme modes of phase 2 add entries here and nowhere else.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use crunk_spec::DesignSpec;
use crunk_values::Color;

/// One colour context a rule is judged in.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Mode {
    /// The mode name, `default` for the spec's own palette.
    pub name: &'static str,
}

impl Mode {
    /// The spec's palette as declared.
    pub const DEFAULT: Self = Self { name: "default" };

    /// True for [`Mode::DEFAULT`]; messages name any other mode and stay terse for this one.
    pub fn is_default(self) -> bool {
        self == Self::DEFAULT
    }

    /// The palette of this mode, `(name, colour)` in declaration order.
    pub fn palette(self, spec: &DesignSpec) -> Vec<(&str, Color)> {
        spec.palette.iter().map(|(n, c)| (n.as_str(), *c)).collect()
    }

    /// `" in mode `name`"` for a non-default mode, empty for the default one.
    pub fn suffix(self) -> String {
        if self.is_default() {
            String::new()
        } else {
            format!(" in mode `{}`", self.name)
        }
    }
}

/// Every mode the spec declares; the default mode only, until phase 2.
pub fn modes(_spec: &DesignSpec) -> Vec<Mode> {
    vec![Mode::DEFAULT]
}
