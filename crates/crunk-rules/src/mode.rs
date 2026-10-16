//! Modes: the colour contexts (light, dark, ...) every colour and contrast rule runs once per.
//!
//! crunk.md section 6: "contrast for declared pairs in every mode". [`modes`] yields
//! [`Mode::DEFAULT`] (the spec's palette as declared) followed by one mode per
//! `[palette.modes.<name>]` table (dark, colour-blind safe, ...), each the base palette with that
//! table's colours substituted.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use std::borrow::Cow;

use crunk_spec::DesignSpec;
use crunk_values::Color;

/// One colour context a rule is judged in.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Mode {
    /// The mode name, `default` for the spec's own palette.
    pub name: Cow<'static, str>,
}

impl Mode {
    /// The spec's palette as declared.
    pub const DEFAULT: Self = Self {
        name: Cow::Borrowed("default"),
    };

    /// True for [`Mode::DEFAULT`]; messages name any other mode and stay terse for this one.
    pub fn is_default(&self) -> bool {
        *self == Self::DEFAULT
    }

    /// The palette of this mode, `(name, colour)` in declaration order.
    pub fn palette<'a>(&self, spec: &'a DesignSpec) -> Vec<(&'a str, Color)> {
        let overlay = spec.palette_modes.get(self.name.as_ref());
        spec.palette
            .iter()
            .map(|(n, c)| {
                let colour = overlay.and_then(|o| o.get(n)).unwrap_or(c);
                (n.as_str(), *colour)
            })
            .collect()
    }

    /// `" in mode `name`"` for a non-default mode, empty for the default one.
    pub fn suffix(&self) -> String {
        if self.is_default() {
            String::new()
        } else {
            format!(" in mode `{}`", self.name)
        }
    }
}

/// Every mode the spec declares: the default mode, then each `[palette.modes.<name>]` in order.
pub fn modes(spec: &DesignSpec) -> Vec<Mode> {
    let declared = spec.palette_modes.keys().map(|name| Mode {
        name: Cow::Owned(name.clone()),
    });
    let all: Vec<Mode> = std::iter::once(Mode::DEFAULT).chain(declared).collect();
    tracing::debug!(modes = all.len(), "colour modes resolved");
    all
}
