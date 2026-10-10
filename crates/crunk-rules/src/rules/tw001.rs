//! TW001: an arbitrary-value Tailwind utility (`bg-[#282828]`, `p-[13px]`, `z-[99]`) judged on
//! the CSS Tailwind itself compiles it to (port of `crunk/rules/_tailwind.py` `tw001`): a `z-index`
//! against the declared layers (only when layers are declared), a colour against the palette, a
//! governed length family against its scale (off the scale by construction when the compiled value
//! is not px-comparable). A utility Tailwind could not answer for is Unresolved; one it reports as
//! not Tailwind syntax has no CSS to judge and is exempt.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use crunk_spec::DesignSpec;
use crunk_spec::naming::color_token;
use crunk_tailwind::runtime::ClassDeclaration;
use crunk_values::{Color, Length, LengthKind};
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::color::Palette;
use crate::host::CrunkHost;
use crate::scales::off_scale;
use crate::sheets::{examined_sheets, line_offset, site_path};
use crate::tailwind::{
    ClassState, LENGTH_PREFIXES, ZINDEX_PREFIXES, arbitrary_prefix, missing_facts, scale_and_token,
    unresolved_message,
};

/// An arbitrary-value utility whose compiled CSS is off the palette, the scales or the layers.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TW001",
    slug = "arbitrary-value-off-design",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Tw001;

fn zindex_message(spec: &DesignSpec, utility: &str, decls: &[ClassDeclaration]) -> Option<String> {
    let value = decls
        .iter()
        .find(|d| d.property == "z-index")
        .and_then(|d| d.value.parse::<i64>().ok())?;
    let mut declared: Vec<i64> = spec.layers.values().copied().collect();
    declared.sort_unstable();
    if declared.contains(&value) {
        return None;
    }
    Some(format!(
        "arbitrary value '{utility}' is z-index {value}, not among declared layers {declared:?}"
    ))
}

fn color_message(spec: &DesignSpec, utility: &str, color: Color) -> Option<String> {
    let palette = Palette::new(spec.palette.iter().map(|(n, c)| (n.as_str(), *c)).collect());
    if palette.conforms(color) {
        return None;
    }
    let (name, distance) = palette.nearest(color)?;
    let token = color_token(&spec.tokens, name);
    Some(format!(
        "arbitrary value '{utility}' is not a palette color; nearest is {token} (distance {distance:.2})"
    ))
}

fn length_message(
    spec: &DesignSpec,
    utility: &str,
    prefix: &str,
    decls: &[ClassDeclaration],
) -> Option<String> {
    let candidates: Vec<&ClassDeclaration> = decls
        .iter()
        .filter(|d| !d.property.ends_with("color"))
        .collect();
    for decl in &candidates {
        let Ok(length) = Length::parse(&decl.value, spec.project.root_font_size) else {
            continue;
        };
        if !matches!(length.kind, LengthKind::Px | LengthKind::Rem) {
            continue;
        }
        let (scale, _) = scale_and_token(spec, prefix, 0.0);
        let off = off_scale(&length, &scale, spec.lint.fix_tolerance)?;
        let token = |step: f64| scale_and_token(spec, prefix, step).1;
        return Some(format!(
            "arbitrary value '{utility}' is off the scale; between var({}) and var({})",
            token(off.lower),
            token(off.upper)
        ));
    }
    (!candidates.is_empty()).then(|| {
        format!(
            "arbitrary value '{utility}' uses a unit that cannot be compared to the px scale; '{prefix}' is a governed scale family"
        )
    })
}

fn judge(
    spec: &DesignSpec,
    utility: &str,
    prefix: &str,
    decls: &[ClassDeclaration],
) -> Option<String> {
    if ZINDEX_PREFIXES.contains(&prefix) {
        return zindex_message(spec, utility, decls);
    }
    if let Some(color) = decls.iter().find_map(|d| Color::parse(&d.value).ok()) {
        return color_message(spec, utility, color);
    }
    if !LENGTH_PREFIXES.contains(&prefix) {
        return None;
    }
    length_message(spec, utility, prefix, decls)
}

impl<P: ?Sized + CrunkHost> RepoRule<P> for Tw001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles), Some(facts)) = (host.spec(), host.styles(), host.tailwind())
        else {
            return;
        };
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for utility in &sheet.utilities {
                let Some(prefix) = arbitrary_prefix(&utility.name) else {
                    continue;
                };
                if ZINDEX_PREFIXES.contains(&prefix) && spec.layers.is_empty() {
                    continue;
                }
                let offset = line_offset(&sheet.source, utility.line);
                match facts.class(&utility.name) {
                    ClassState::Unresolved(why) => {
                        out.unresolved_in(&path, offset, unresolved_message(&utility.name, why));
                    }
                    ClassState::Invalid => {}
                    ClassState::Valid(decls) => {
                        if let Some(message) = judge(spec, &utility.name, prefix, decls) {
                            tracing::debug!(%path, line = utility.line, name = %utility.name, "TW001: off-design arbitrary value");
                            out.fire_in(&path, offset, message);
                        }
                    }
                }
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_facts(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Tw001 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
