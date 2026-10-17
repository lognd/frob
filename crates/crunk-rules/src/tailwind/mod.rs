//! What TW001-005 share: which utility roots take a spacing, size, radius, font-size or colour
//! value, the reading of an arbitrary value (`p-[13px]`, `bg-[#fff]`) and the utility sites of a
//! project.
//!
//! No Tailwind runtime runs here: only arbitrary values are judged, because a named value
//! (`p-4`) resolves through the project's theme, which the token export already keeps on the
//! scales. The candidate parser is [`crunk_tailwind::parse_candidate`].

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_ingest::ProjectStyles;
use crunk_spec::DesignSpec;
use crunk_tailwind::{Candidate, UtilityValue, parse_candidate};
use crunk_values::{Color, Length};

use crate::org::line_offset;
use crate::sheets::{is_tokens_sheet, site_path};

/// Which scale an arbitrary length is judged against.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScaleKind {
    /// `[scales] spacing`: padding, margin, gap, inset.
    Spacing,
    /// `[scales] font_sizes`: `text-[..]`.
    FontSize,
    /// `[scales] radii`: `rounded-[..]`.
    Radius,
    /// `[scales] sizes` (spacing when empty): width and height utilities.
    Size,
}

impl ScaleKind {
    /// The scale's name in `[scales]`, for messages.
    pub fn name(self) -> &'static str {
        match self {
            Self::Spacing => "spacing",
            Self::FontSize => "font_sizes",
            Self::Radius => "radii",
            Self::Size => "sizes",
        }
    }

    /// The allowed px steps of this scale in `spec`.
    pub fn steps(self, spec: &DesignSpec) -> &[f64] {
        let scales = &spec.scales;
        match self {
            Self::Spacing => &scales.spacing,
            Self::FontSize => &scales.font_sizes,
            Self::Radius => &scales.radii,
            Self::Size if scales.sizes.is_empty() => &scales.spacing,
            Self::Size => &scales.sizes,
        }
    }
}

/// True when `px` is one of `steps`.
pub fn on_scale(px: f64, steps: &[f64]) -> bool {
    steps.iter().any(|s| (s - px).abs() < 1e-6)
}

const SPACING: &[&str] = &[
    "p", "px", "py", "pt", "pr", "pb", "pl", "ps", "pe", "m", "mx", "my", "mt", "mr", "mb", "ml",
    "ms", "me", "gap", "gap-x", "gap-y", "space-x", "space-y", "inset", "inset-x", "inset-y",
    "top", "right", "bottom", "left", "start", "end",
];
const SIZE: &[&str] = &["w", "h", "size", "min-w", "min-h", "max-w", "max-h"];
const RADIUS: &[&str] = &[
    "rounded",
    "rounded-t",
    "rounded-r",
    "rounded-b",
    "rounded-l",
    "rounded-s",
    "rounded-e",
    "rounded-tl",
    "rounded-tr",
    "rounded-br",
    "rounded-bl",
    "rounded-ss",
    "rounded-se",
    "rounded-es",
    "rounded-ee",
];
const COLOR: &[&str] = &[
    "bg",
    "text",
    "border",
    "border-t",
    "border-r",
    "border-b",
    "border-l",
    "border-x",
    "border-y",
    "fill",
    "stroke",
    "ring",
    "outline",
    "divide",
    "accent",
    "caret",
    "decoration",
    "from",
    "via",
    "to",
];

/// The scale a length-valued utility root is judged against, `None` for a root that takes none.
pub fn scale_kind(root: &str) -> Option<ScaleKind> {
    if SPACING.contains(&root) {
        Some(ScaleKind::Spacing)
    } else if SIZE.contains(&root) {
        Some(ScaleKind::Size)
    } else if RADIUS.contains(&root) {
        Some(ScaleKind::Radius)
    } else if root == "text" {
        Some(ScaleKind::FontSize)
    } else {
        None
    }
}

/// True when `root` can take a colour value.
pub fn takes_color(root: &str) -> bool {
    COLOR.contains(&root)
}

/// An arbitrary value read for what it spells.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Arbitrary {
    /// A length with a known px value, judged against `kind`.
    Length {
        /// The scale the utility root takes.
        kind: ScaleKind,
        /// The length in px.
        px: f64,
    },
    /// A colour literal.
    Color(Color),
}

/// Read the arbitrary value of `candidate` (`p-[13px]`, `bg-[#fff]`, `text-[length:12px]`).
///
/// `None` for anything not statically a length or colour: a named value, a `var()`, a `calc()`,
/// a percentage, a utility root that takes neither, or a type hint naming something else.
pub fn arbitrary(candidate: &Candidate, root_font_size: f64) -> Option<Arbitrary> {
    let UtilityValue::Arbitrary { hint, content } = candidate.value.as_ref()? else {
        return None;
    };
    let text = content.replace('_', " ");
    let root = candidate.utility.as_str();
    let as_length = |kind: ScaleKind| {
        let px = Length::parse(&text, root_font_size).ok()?.px?;
        Some(Arbitrary::Length { kind, px })
    };
    let as_color = || Color::parse(&text).ok().map(Arbitrary::Color);
    match hint.as_deref() {
        Some("length") => as_length(scale_kind(root)?),
        Some("color") => takes_color(root).then(as_color).flatten(),
        Some(_) => None,
        None => scale_kind(root)
            .and_then(as_length)
            .or_else(|| takes_color(root).then(as_color).flatten()),
    }
}

/// One utility token of the project, parsed.
#[derive(Debug)]
pub struct Site<'a> {
    /// Project-relative path of the source holding the token.
    pub path: String,
    /// Byte offset of the start of the token's line.
    pub offset: usize,
    /// The 1-based line.
    pub line: u32,
    /// The variant prefixes as written, outermost first.
    pub variants: &'a [String],
    /// The parsed utility.
    pub candidate: Candidate,
}

/// Every statically known utility token of the non-tokens sources; a token the candidate parser
/// rejects is skipped (it is not a Tailwind utility).
pub fn sites<'a>(spec: &DesignSpec, styles: &'a ProjectStyles) -> Vec<Site<'a>> {
    let mut out = Vec::new();
    for sheet in styles.sheets.iter().filter(|s| !is_tokens_sheet(s)) {
        let path = site_path(spec, &sheet.path);
        for utility in &sheet.utilities {
            match parse_candidate(&utility.name) {
                Ok(candidate) => out.push(Site {
                    path: path.clone(),
                    offset: line_offset(&sheet.source, utility.line),
                    line: utility.line,
                    variants: &utility.variants,
                    candidate,
                }),
                Err(err) => {
                    tracing::debug!(%path, name = %utility.name, %err, "tailwind: token is not a utility candidate");
                }
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn read(raw: &str) -> Option<Arbitrary> {
        arbitrary(&parse_candidate(raw).expect("candidate"), 16.0)
    }

    // frob:tests crates/crunk-rules/src/tailwind/mod.rs::arbitrary
    #[test]
    fn arbitrary_lengths_and_colors_are_read_by_root() {
        assert_eq!(
            read("p-[13px]"),
            Some(Arbitrary::Length {
                kind: ScaleKind::Spacing,
                px: 13.0
            })
        );
        assert_eq!(
            read("text-[1rem]"),
            Some(Arbitrary::Length {
                kind: ScaleKind::FontSize,
                px: 16.0
            })
        );
        assert!(matches!(read("bg-[#ff0000]"), Some(Arbitrary::Color(_))));
        assert!(matches!(read("text-[#ff0000]"), Some(Arbitrary::Color(_))));
    }

    // frob:tests crates/crunk-rules/src/tailwind/mod.rs::arbitrary
    #[test]
    fn named_dynamic_and_foreign_values_are_not_read() {
        for raw in [
            "p-4",
            "p-[calc(1px+2px)]",
            "w-[50%]",
            "p-[var(--x)]",
            "p-[color:red]",
            "z-[13px]",
            "bg-[url(x.png)]",
        ] {
            assert_eq!(read(raw), None, "{raw}");
        }
    }

    // frob:tests crates/crunk-rules/src/tailwind/mod.rs::on_scale
    #[test]
    fn scale_membership_is_exact_in_px() {
        assert!(on_scale(16.0, &[0.0, 16.0]));
        assert!(!on_scale(13.0, &[0.0, 16.0]));
    }
}
