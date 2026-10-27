//! Per-element mapping of resolved CSS declarations to one taffy [`Style`].

// frob:ticket 01M5XCWXYNXW0RW8VRDQPY31M6

use taffy::style_helpers::{TaffyGridLine, TaffyGridSpan};
use taffy::{
    AlignContent, AlignItems, BoxSizing, Dimension, Display, FlexDirection, FlexWrap, GridAutoFlow,
    GridPlacement, GridTemplateComponent, GridTemplateRepetition, LengthPercentage,
    LengthPercentageAuto, MaxTrackSizingFunction, MinTrackSizingFunction, Position, Rect,
    RepetitionCount, Size, Style, TrackSizingFunction,
};

use super::error::{FindingKind, StyleError, StyleFinding};
use super::tokens::{TokenMap, VarError, resolve_vars};
use super::value::{Len, expand_box, parse_len, parse_num, split_commas, split_top};

/// Which element a declaration list belongs to, for error and finding text.
#[derive(Debug, Clone, Copy)]
pub struct ElementRef<'a> {
    /// The element's `data-id`.
    pub data_id: &'a str,
    /// 1-based line of its start tag.
    pub line: u32,
}

/// Whether the parent gives each axis a definite size (decides percent-size handling).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ParentCtx {
    /// The parent's content width is definite.
    pub width_definite: bool,
    /// The parent's content height is definite.
    pub height_definite: bool,
}

impl ParentCtx {
    /// A parent with both axes definite (a fixed-size viewport root).
    pub const DEFINITE: Self = Self {
        width_definite: true,
        height_definite: true,
    };
}

/// The result of mapping one element's declarations.
#[derive(Debug, Clone)]
pub struct MappedStyle {
    /// The taffy style.
    pub style: Style,
    /// Non-fatal problems found on the way.
    pub findings: Vec<StyleFinding>,
    /// `display:none` was set: the node is removed from layout.
    pub hidden: bool,
    /// The definiteness this element's own children see.
    pub child_ctx: ParentCtx,
}

/// Map `(property, value)` declarations (document order, later wins) to a taffy style.
///
/// # Errors
/// An undefined token, a token cycle or an unsupported/malformed value, each naming the element.
pub fn map_declarations(
    el: ElementRef<'_>,
    decls: &[(String, String)],
    tokens: &TokenMap,
    parent: ParentCtx,
) -> Result<MappedStyle, StyleError> {
    let mut m = Mapper::new(el);
    for (prop, raw) in decls {
        let prop = prop.trim().to_ascii_lowercase();
        let resolved = resolve_vars(tokens, raw).map_err(|e| m.var_error(&prop, e))?;
        let value = strip_important(&resolved).to_ascii_lowercase();
        tracing::trace!(element = el.data_id, %prop, %value, "mapping declaration");
        m.apply(&prop, &value)?;
    }
    Ok(m.finish(parent))
}

fn strip_important(v: &str) -> &str {
    let v = v.trim();
    v.strip_suffix("!important").map_or(v, str::trim)
}

#[derive(Clone, Copy)]
enum Side {
    Top,
    Right,
    Bottom,
    Left,
}

const SIDES: [Side; 4] = [Side::Top, Side::Right, Side::Bottom, Side::Left];

fn side_mut<T>(r: &mut Rect<T>, s: Side) -> &mut T {
    match s {
        Side::Top => &mut r.top,
        Side::Right => &mut r.right,
        Side::Bottom => &mut r.bottom,
        Side::Left => &mut r.left,
    }
}

/// Layout properties recognised but not mapped yet; they produce a finding.
const UNMAPPED: &[&str] = &[
    "grid-template-areas",
    "grid-template",
    "grid",
    "grid-area",
    "order",
    "place-items",
    "place-content",
    "place-self",
];

struct Mapper<'a> {
    el: ElementRef<'a>,
    style: Style,
    findings: Vec<StyleFinding>,
    hidden: bool,
    size: [Len; 2],
    min: [Len; 2],
    max: [Len; 2],
}

impl<'a> Mapper<'a> {
    fn new(el: ElementRef<'a>) -> Self {
        let style = Style {
            display: Display::Block,
            box_sizing: BoxSizing::ContentBox,
            ..Style::default()
        };
        Self {
            el,
            style,
            findings: Vec::new(),
            hidden: false,
            size: [Len::Auto; 2],
            min: [Len::Auto; 2],
            max: [Len::Auto; 2],
        }
    }

    fn var_error(&self, prop: &str, e: VarError) -> StyleError {
        let (element, line, property) = (self.el.data_id.to_owned(), self.el.line, prop.to_owned());
        match e {
            VarError::Undefined(token) => StyleError::UndefinedToken {
                element,
                line,
                property,
                token,
            },
            VarError::Cycle(token) => StyleError::TokenCycle {
                element,
                line,
                property,
                token,
            },
            VarError::Malformed(reason) => StyleError::BadValue {
                element,
                line,
                property,
                value: String::new(),
                reason,
            },
        }
    }

    fn bad(&self, prop: &str, value: &str, reason: impl Into<String>) -> StyleError {
        StyleError::BadValue {
            element: self.el.data_id.to_owned(),
            line: self.el.line,
            property: prop.to_owned(),
            value: value.to_owned(),
            reason: reason.into(),
        }
    }

    fn find(&mut self, kind: FindingKind, prop: &str, message: String) {
        tracing::debug!(element = self.el.data_id, line = self.el.line, %prop, ?kind, %message, "style finding");
        self.findings.push(StyleFinding {
            kind,
            element: self.el.data_id.to_owned(),
            line: self.el.line,
            property: prop.to_owned(),
            message,
        });
    }

    fn len(&self, prop: &str, value: &str, tok: &str) -> Result<Len, StyleError> {
        parse_len(tok).map_err(|r| self.bad(prop, value, r))
    }

    /// Clamp a negative length to zero, recording a finding.
    fn nonneg(&mut self, prop: &str, l: Len) -> Len {
        if l.is_negative() {
            self.find(
                FindingKind::NegativeValue,
                prop,
                format!("negative `{prop}` clamped to 0"),
            );
            Len::Px(0.0)
        } else {
            l
        }
    }

    fn lp(&self, prop: &str, value: &str, l: Len) -> Result<LengthPercentage, StyleError> {
        match l {
            Len::Px(v) => Ok(LengthPercentage::length(v)),
            Len::Pct(v) => Ok(LengthPercentage::percent(v)),
            Len::Auto => Err(self.bad(prop, value, "`auto` is not allowed here")),
        }
    }

    fn apply(&mut self, prop: &str, value: &str) -> Result<(), StyleError> {
        let toks = split_top(value);
        match prop {
            "display" => self.display(prop, value)?,
            "position" => {
                self.style.position = match value {
                    "static" => Position::Static,
                    "relative" => Position::Relative,
                    "absolute" => Position::Absolute,
                    _ => {
                        return Err(self.bad(prop, value, "expected static, relative or absolute"));
                    }
                }
            }
            "top" | "right" | "bottom" | "left" => {
                let l = self.single_len(prop, value, &toks)?;
                let side = side_of(prop);
                *side_mut(&mut self.style.inset, side) = lpa(l);
            }
            "inset" => {
                for (s, l) in SIDES.into_iter().zip(self.box_lens(prop, value, &toks)?) {
                    *side_mut(&mut self.style.inset, s) = lpa(l);
                }
            }
            "width" | "height" | "min-width" | "min-height" | "max-width" | "max-height" => {
                self.sizing(prop, value, &toks)?;
            }
            "margin" => {
                for (s, l) in SIDES.into_iter().zip(self.box_lens(prop, value, &toks)?) {
                    *side_mut(&mut self.style.margin, s) = lpa(l);
                }
            }
            "margin-top" | "margin-right" | "margin-bottom" | "margin-left" => {
                let l = self.single_len(prop, value, &toks)?;
                *side_mut(&mut self.style.margin, side_of(&prop[7..])) = lpa(l);
            }
            "padding" => {
                for (s, l) in SIDES.into_iter().zip(self.box_lens(prop, value, &toks)?) {
                    self.set_padding(prop, value, s, l)?;
                }
            }
            "padding-top" | "padding-right" | "padding-bottom" | "padding-left" => {
                let l = self.single_len(prop, value, &toks)?;
                self.set_padding(prop, value, side_of(&prop[8..]), l)?;
            }
            "border" | "border-top" | "border-right" | "border-bottom" | "border-left" => {
                let w = Self::border_shorthand(&toks);
                let sides: Vec<Side> = if prop == "border" {
                    SIDES.to_vec()
                } else {
                    vec![side_of(&prop[7..])]
                };
                for s in sides {
                    self.set_border(prop, value, s, w)?;
                }
            }
            "border-width" => {
                for (s, l) in SIDES.into_iter().zip(self.box_lens(prop, value, &toks)?) {
                    self.set_border(prop, value, s, l)?;
                }
            }
            "border-top-width"
            | "border-right-width"
            | "border-bottom-width"
            | "border-left-width" => {
                let l = self.single_len(prop, value, &toks)?;
                let side = side_of(&prop[7..prop.len() - 6]);
                self.set_border(prop, value, side, l)?;
            }
            "gap" | "row-gap" | "column-gap" | "grid-gap" | "grid-row-gap" | "grid-column-gap" => {
                self.gap(prop, value, &toks)?;
            }
            _ => return self.apply_flex_grid(prop, value, &toks),
        }
        Ok(())
    }

    /// Flex, alignment, aspect-ratio and grid properties.
    fn apply_flex_grid(
        &mut self,
        prop: &str,
        value: &str,
        toks: &[&str],
    ) -> Result<(), StyleError> {
        match prop {
            "flex-direction" => {
                self.style.flex_direction = match value {
                    "row" => FlexDirection::Row,
                    "row-reverse" => FlexDirection::RowReverse,
                    "column" => FlexDirection::Column,
                    "column-reverse" => FlexDirection::ColumnReverse,
                    _ => return Err(self.bad(prop, value, "unknown flex-direction")),
                }
            }
            "flex-wrap" => self.style.flex_wrap = self.wrap(prop, value)?,
            "flex-flow" => {
                for t in toks {
                    match *t {
                        "row" | "row-reverse" | "column" | "column-reverse" => {
                            self.apply("flex-direction", t)?;
                        }
                        _ => self.style.flex_wrap = self.wrap(prop, t)?,
                    }
                }
            }
            "flex" => self.flex(prop, value, toks)?,
            "flex-grow" | "flex-shrink" => {
                let n = self.factor(prop, value)?;
                if prop == "flex-grow" {
                    self.style.flex_grow = n;
                } else {
                    self.style.flex_shrink = n;
                }
            }
            "flex-basis" => {
                let l = self.single_len(prop, value, toks)?;
                let l = if l.is_negative() { Len::Auto } else { l };
                self.style.flex_basis = dim(l);
            }
            "align-items" => self.style.align_items = self.align_items(prop, value)?,
            "justify-items" => self.style.justify_items = self.align_items(prop, value)?,
            "align-self" | "justify-self" => {
                let v = if value == "auto" {
                    None
                } else {
                    Some(self.align_items(prop, value)?)
                };
                if prop == "align-self" {
                    self.style.align_self = v;
                } else {
                    self.style.justify_self = v;
                }
            }
            "align-content" => self.style.align_content = self.align_content(prop, value)?,
            "justify-content" => {
                self.style.justify_content = self.align_content(prop, value)?;
            }
            "aspect-ratio" => self.style.aspect_ratio = self.aspect(prop, value)?,
            "box-sizing" => {
                self.style.box_sizing = match value {
                    "border-box" => BoxSizing::BorderBox,
                    "content-box" => BoxSizing::ContentBox,
                    _ => return Err(self.bad(prop, value, "expected border-box or content-box")),
                }
            }
            "grid-template-columns" => {
                self.style.grid_template_columns =
                    self.template(prop, value)?.into_iter().collect();
            }
            "grid-template-rows" => {
                self.style.grid_template_rows = self.template(prop, value)?.into_iter().collect();
            }
            "grid-auto-columns" => {
                self.style.grid_auto_columns = self.auto_tracks(prop, value)?.into_iter().collect();
            }
            "grid-auto-rows" => {
                self.style.grid_auto_rows = self.auto_tracks(prop, value)?.into_iter().collect();
            }
            "grid-auto-flow" => self.style.grid_auto_flow = self.auto_flow(prop, value)?,
            "grid-column" | "grid-row" | "grid-column-start" | "grid-column-end"
            | "grid-row-start" | "grid-row-end" => self.placement(prop, value)?,
            p if UNMAPPED.contains(&p) => self.find(
                FindingKind::UnmappedProperty,
                p,
                format!("`{p}` is not mapped to the solver yet"),
            ),
            p => tracing::debug!(
                element = self.el.data_id,
                property = p,
                "non-layout property ignored"
            ),
        }
        Ok(())
    }

    fn display(&mut self, prop: &str, value: &str) -> Result<(), StyleError> {
        self.hidden = value == "none";
        self.style.display = match value {
            "block" => Display::Block,
            "flex" => Display::Flex,
            "grid" => Display::Grid,
            "none" => Display::None,
            _ => return Err(self.bad(prop, value, "expected block, flex, grid or none")),
        };
        Ok(())
    }

    fn single_len(&self, prop: &str, value: &str, toks: &[&str]) -> Result<Len, StyleError> {
        match toks {
            [t] => self.len(prop, value, t),
            _ => Err(self.bad(prop, value, "expected exactly one value")),
        }
    }

    fn box_lens(&self, prop: &str, value: &str, toks: &[&str]) -> Result<[Len; 4], StyleError> {
        let lens = toks
            .iter()
            .map(|t| self.len(prop, value, t))
            .collect::<Result<Vec<_>, _>>()?;
        expand_box(&lens).ok_or_else(|| self.bad(prop, value, "expected 1 to 4 values"))
    }

    fn set_padding(&mut self, prop: &str, value: &str, s: Side, l: Len) -> Result<(), StyleError> {
        let l = self.nonneg(prop, l);
        *side_mut(&mut self.style.padding, s) = self.lp(prop, value, l)?;
        Ok(())
    }

    fn set_border(&mut self, prop: &str, value: &str, s: Side, l: Len) -> Result<(), StyleError> {
        let l = self.nonneg(prop, l);
        *side_mut(&mut self.style.border, s) = self.lp(prop, value, l)?;
        Ok(())
    }

    /// The width a `border` shorthand implies (`medium` is 3px when a style is given).
    fn border_shorthand(toks: &[&str]) -> Len {
        if let Some(l) = toks.iter().find_map(|t| parse_len(t).ok()) {
            return l;
        }
        if toks
            .iter()
            .any(|t| matches!(*t, "solid" | "dashed" | "dotted" | "double"))
        {
            return Len::Px(3.0);
        }
        Len::Px(0.0)
    }

    fn gap(&mut self, prop: &str, value: &str, toks: &[&str]) -> Result<(), StyleError> {
        let parse = |this: &mut Self, t: &str| -> Result<LengthPercentage, StyleError> {
            let l = if t == "normal" {
                Len::Px(0.0)
            } else {
                this.len(prop, value, t)?
            };
            let l = this.nonneg(prop, l);
            this.lp(prop, value, l)
        };
        match (prop, toks) {
            ("row-gap" | "grid-row-gap", [t]) => self.style.gap.height = parse(self, t)?,
            ("column-gap" | "grid-column-gap", [t]) => self.style.gap.width = parse(self, t)?,
            ("gap" | "grid-gap", [t]) => {
                let g = parse(self, t)?;
                self.style.gap = Size {
                    width: g,
                    height: g,
                };
            }
            ("gap" | "grid-gap", [r, c]) => {
                self.style.gap.height = parse(self, r)?;
                self.style.gap.width = parse(self, c)?;
            }
            _ => return Err(self.bad(prop, value, "wrong number of values")),
        }
        Ok(())
    }

    fn sizing(&mut self, prop: &str, value: &str, toks: &[&str]) -> Result<(), StyleError> {
        let l = match (value, prop.starts_with("max-")) {
            ("none", true) => Len::Auto,
            _ => self.single_len(prop, value, toks)?,
        };
        let l = if l.is_negative() {
            self.find(
                FindingKind::NegativeValue,
                prop,
                format!("negative `{prop}` treated as auto"),
            );
            Len::Auto
        } else {
            l
        };
        let axis = usize::from(prop.ends_with("height"));
        if prop.starts_with("min-") {
            self.min[axis] = l;
        } else if prop.starts_with("max-") {
            self.max[axis] = l;
        } else {
            self.size[axis] = l;
        }
        Ok(())
    }

    fn wrap(&self, prop: &str, value: &str) -> Result<FlexWrap, StyleError> {
        match value {
            "nowrap" => Ok(FlexWrap::NoWrap),
            "wrap" => Ok(FlexWrap::Wrap),
            "wrap-reverse" => Ok(FlexWrap::WrapReverse),
            _ => Err(self.bad(prop, value, "expected nowrap, wrap or wrap-reverse")),
        }
    }

    fn factor(&mut self, prop: &str, tok: &str) -> Result<f32, StyleError> {
        let n = parse_num(tok).ok_or_else(|| self.bad(prop, tok, "expected a number"))?;
        if n < 0.0 {
            self.find(
                FindingKind::NegativeValue,
                prop,
                format!("negative `{prop}` clamped to 0"),
            );
            return Ok(0.0);
        }
        Ok(n)
    }

    fn flex(&mut self, prop: &str, value: &str, toks: &[&str]) -> Result<(), StyleError> {
        let (grow, shrink, basis) = match toks {
            ["none"] => (0.0, 0.0, Dimension::auto()),
            ["auto"] => (1.0, 1.0, Dimension::auto()),
            ["initial"] => (0.0, 1.0, Dimension::auto()),
            _ => {
                let (mut grow, mut shrink, mut basis) = (None, None, None);
                for t in toks {
                    let bare = parse_num(t).is_some();
                    if bare && grow.is_none() {
                        grow = Some(self.factor(prop, t)?);
                    } else if bare && shrink.is_none() && basis.is_none() {
                        shrink = Some(self.factor(prop, t)?);
                    } else if basis.is_none() {
                        let l = self.len(prop, value, t)?;
                        basis = Some(dim(if l.is_negative() { Len::Auto } else { l }));
                    } else {
                        return Err(self.bad(prop, value, "too many values"));
                    }
                }
                if toks.is_empty() {
                    return Err(self.bad(prop, value, "empty value"));
                }
                (
                    grow.unwrap_or(1.0),
                    shrink.unwrap_or(1.0),
                    basis.unwrap_or(Dimension::percent(0.0)),
                )
            }
        };
        self.style.flex_grow = grow;
        self.style.flex_shrink = shrink;
        self.style.flex_basis = basis;
        Ok(())
    }

    fn align_items(&self, prop: &str, value: &str) -> Result<AlignItems, StyleError> {
        Ok(match value {
            "normal" => AlignItems::NORMAL,
            "start" => AlignItems::START,
            "end" => AlignItems::END,
            "flex-start" => AlignItems::FLEX_START,
            "flex-end" => AlignItems::FLEX_END,
            "self-start" => AlignItems::SELF_START,
            "self-end" => AlignItems::SELF_END,
            "center" => AlignItems::CENTER,
            "baseline" => AlignItems::BASELINE,
            "stretch" => AlignItems::STRETCH,
            _ => return Err(self.bad(prop, value, "unknown alignment keyword")),
        })
    }

    fn align_content(&self, prop: &str, value: &str) -> Result<AlignContent, StyleError> {
        Ok(match value {
            "normal" => AlignContent::NORMAL,
            "start" => AlignContent::START,
            "end" => AlignContent::END,
            "flex-start" => AlignContent::FLEX_START,
            "flex-end" => AlignContent::FLEX_END,
            "center" => AlignContent::CENTER,
            "stretch" => AlignContent::STRETCH,
            "space-between" => AlignContent::SPACE_BETWEEN,
            "space-around" => AlignContent::SPACE_AROUND,
            "space-evenly" => AlignContent::SPACE_EVENLY,
            _ => return Err(self.bad(prop, value, "unknown content-distribution keyword")),
        })
    }

    fn aspect(&self, prop: &str, value: &str) -> Result<Option<f32>, StyleError> {
        let v = value.strip_prefix("auto").map_or(value, str::trim);
        if v.is_empty() {
            return Ok(None);
        }
        let parts: Vec<&str> = v.split('/').map(str::trim).collect();
        let nums: Option<Vec<f32>> = parts.iter().map(|p| parse_num(p)).collect();
        match nums.as_deref() {
            Some([a]) if *a > 0.0 => Ok(Some(*a)),
            Some([a, b]) if *a > 0.0 && *b > 0.0 => Ok(Some(a / b)),
            _ => Err(self.bad(
                prop,
                value,
                "expected `auto`, `<n>` or `<w> / <h>` (positive)",
            )),
        }
    }

    fn auto_flow(&self, prop: &str, value: &str) -> Result<GridAutoFlow, StyleError> {
        Ok(match value {
            "row" => GridAutoFlow::Row,
            "column" => GridAutoFlow::Column,
            "row dense" | "dense row" | "dense" => GridAutoFlow::RowDense,
            "column dense" | "dense column" => GridAutoFlow::ColumnDense,
            _ => return Err(self.bad(prop, value, "unknown grid-auto-flow")),
        })
    }

    fn track_min(
        &self,
        prop: &str,
        value: &str,
        t: &str,
    ) -> Result<MinTrackSizingFunction, StyleError> {
        Ok(match t {
            "auto" => MinTrackSizingFunction::auto(),
            "min-content" => MinTrackSizingFunction::min_content(),
            "max-content" => MinTrackSizingFunction::max_content(),
            _ => match self.track_len(prop, value, t)? {
                Len::Px(v) => MinTrackSizingFunction::length(v),
                Len::Pct(v) => MinTrackSizingFunction::percent(v),
                Len::Auto => MinTrackSizingFunction::auto(),
            },
        })
    }

    fn track_max(
        &self,
        prop: &str,
        value: &str,
        t: &str,
    ) -> Result<MaxTrackSizingFunction, StyleError> {
        if let Some(n) = t.strip_suffix("fr") {
            return match parse_num(n) {
                Some(v) if v >= 0.0 => Ok(MaxTrackSizingFunction::fr(v)),
                _ => Err(self.bad(prop, value, format!("`{t}` is not a valid fr track"))),
            };
        }
        if let Some(inner) = t
            .strip_prefix("fit-content(")
            .and_then(|r| r.strip_suffix(')'))
        {
            return match self.track_len(prop, value, inner.trim())? {
                Len::Px(v) => Ok(MaxTrackSizingFunction::fit_content_px(v)),
                Len::Pct(v) => Ok(MaxTrackSizingFunction::fit_content_percent(v)),
                Len::Auto => Err(self.bad(prop, value, "fit-content needs a length")),
            };
        }
        Ok(match t {
            "auto" => MaxTrackSizingFunction::auto(),
            "min-content" => MaxTrackSizingFunction::min_content(),
            "max-content" => MaxTrackSizingFunction::max_content(),
            _ => match self.track_len(prop, value, t)? {
                Len::Px(v) => MaxTrackSizingFunction::length(v),
                Len::Pct(v) => MaxTrackSizingFunction::percent(v),
                Len::Auto => MaxTrackSizingFunction::auto(),
            },
        })
    }

    fn track_len(&self, prop: &str, value: &str, t: &str) -> Result<Len, StyleError> {
        let l = self.len(prop, value, t)?;
        if l.is_negative() {
            return Err(self.bad(prop, value, "track sizes cannot be negative"));
        }
        Ok(l)
    }

    fn track(&self, prop: &str, value: &str, t: &str) -> Result<TrackSizingFunction, StyleError> {
        if t.starts_with('[') {
            return Err(self.bad(prop, value, "named grid lines are not supported"));
        }
        if let Some(inner) = t.strip_prefix("minmax(").and_then(|r| r.strip_suffix(')')) {
            return match split_commas(inner).as_slice() {
                [a, b] => Ok(TrackSizingFunction {
                    min: self.track_min(prop, value, a)?,
                    max: self.track_max(prop, value, b)?,
                }),
                _ => Err(self.bad(prop, value, "minmax() takes two arguments")),
            };
        }
        if t.ends_with("fr") || t.starts_with("fit-content(") {
            return Ok(TrackSizingFunction {
                min: MinTrackSizingFunction::auto(),
                max: self.track_max(prop, value, t)?,
            });
        }
        Ok(TrackSizingFunction {
            min: self.track_min(prop, value, t)?,
            max: self.track_max(prop, value, t)?,
        })
    }

    fn auto_tracks(&self, prop: &str, value: &str) -> Result<Vec<TrackSizingFunction>, StyleError> {
        split_top(value)
            .into_iter()
            .map(|t| self.track(prop, value, t))
            .collect()
    }

    fn template(
        &self,
        prop: &str,
        value: &str,
    ) -> Result<Vec<GridTemplateComponent<String>>, StyleError> {
        if value == "none" {
            return Ok(Vec::new());
        }
        let mut out = Vec::new();
        for t in split_top(value) {
            if let Some(inner) = t.strip_prefix("repeat(").and_then(|r| r.strip_suffix(')')) {
                let args = split_commas(inner);
                let [count, list] = args.as_slice() else {
                    return Err(self.bad(prop, value, "repeat() takes a count and a track list"));
                };
                let count = match *count {
                    "auto-fill" => RepetitionCount::AutoFill,
                    "auto-fit" => RepetitionCount::AutoFit,
                    n => match n.parse::<u16>() {
                        Ok(c) if c >= 1 => RepetitionCount::Count(c),
                        _ => {
                            return Err(self.bad(
                                prop,
                                value,
                                "repeat count must be a positive integer",
                            ));
                        }
                    },
                };
                let tracks = self.auto_tracks(prop, list)?;
                if tracks.is_empty() {
                    return Err(self.bad(prop, value, "repeat() needs at least one track"));
                }
                out.push(GridTemplateComponent::Repeat(GridTemplateRepetition {
                    count,
                    tracks,
                    line_names: Vec::new(),
                }));
            } else {
                out.push(GridTemplateComponent::Single(self.track(prop, value, t)?));
            }
        }
        Ok(out)
    }

    fn one_placement(
        &self,
        prop: &str,
        value: &str,
        part: &str,
    ) -> Result<GridPlacement, StyleError> {
        let part = part.trim();
        if part == "auto" {
            return Ok(GridPlacement::Auto);
        }
        let words = split_top(part);
        match words.as_slice() {
            ["span", n] | [n, "span"] => match n.parse::<u16>() {
                Ok(s) if s >= 1 => Ok(GridPlacement::from_span(s)),
                _ => Err(self.bad(prop, value, "span must be a positive integer")),
            },
            [n] => match n.parse::<i16>() {
                Ok(l) if l != 0 => Ok(GridPlacement::from_line_index(l)),
                _ => Err(self.bad(
                    prop,
                    value,
                    "line must be a non-zero integer (named lines unsupported)",
                )),
            },
            _ => Err(self.bad(prop, value, "expected `auto`, `<line>` or `span <n>`")),
        }
    }

    fn placement(&mut self, prop: &str, value: &str) -> Result<(), StyleError> {
        let parts: Vec<&str> = value.split('/').collect();
        let (start, end) = match parts.as_slice() {
            [s] => (self.one_placement(prop, value, s)?, GridPlacement::Auto),
            [s, e] => (
                self.one_placement(prop, value, s)?,
                self.one_placement(prop, value, e)?,
            ),
            _ => return Err(self.bad(prop, value, "expected `<start> / <end>`")),
        };
        let col = prop.contains("column");
        let line = if col {
            &mut self.style.grid_column
        } else {
            &mut self.style.grid_row
        };
        if prop.ends_with("-start") {
            line.start = start;
        } else if prop.ends_with("-end") {
            line.start = line.start.clone();
            line.end = start;
        } else {
            line.start = start;
            line.end = end;
        }
        Ok(())
    }

    /// Apply the cross-property rules and fold the tracked sizes into the style.
    fn finish(mut self, parent: ParentCtx) -> MappedStyle {
        let definite = [parent.width_definite, parent.height_definite];
        let names = [
            ["width", "min-width", "max-width"],
            ["height", "min-height", "max-height"],
        ];
        for axis in 0..2 {
            for (slot, name) in [
                (0, names[axis][0]),
                (1, names[axis][1]),
                (2, names[axis][2]),
            ] {
                let l = match slot {
                    0 => self.size[axis],
                    1 => self.min[axis],
                    _ => self.max[axis],
                };
                if matches!(l, Len::Pct(_)) && !definite[axis] {
                    self.find(
                        FindingKind::PercentUnderIndefiniteParent,
                        name,
                        format!("percentage `{name}` under an indefinite parent treated as auto"),
                    );
                    match slot {
                        0 => self.size[axis] = Len::Auto,
                        1 => self.min[axis] = Len::Auto,
                        _ => self.max[axis] = Len::Auto,
                    }
                }
            }
            match (self.min[axis], self.max[axis]) {
                (Len::Px(a), Len::Px(b)) | (Len::Pct(a), Len::Pct(b)) if a > b => {
                    let name = names[axis][2];
                    self.find(
                        FindingKind::MinExceedsMax,
                        name,
                        format!("`{name}` is below its minimum; the minimum wins"),
                    );
                    self.max[axis] = self.min[axis];
                }
                _ => {}
            }
        }
        if self.style.aspect_ratio.is_some()
            && self.size[0] != Len::Auto
            && self.size[1] != Len::Auto
        {
            self.style.aspect_ratio = None;
            self.find(
                FindingKind::AspectRatioIgnored,
                "aspect-ratio",
                "aspect-ratio ignored because both width and height are set".to_owned(),
            );
        }
        self.style.size = Size {
            width: dim(self.size[0]),
            height: dim(self.size[1]),
        };
        self.style.min_size = Size {
            width: lpa(self.min[0]),
            height: lpa(self.min[1]),
        };
        self.style.max_size = Size {
            width: lpa(self.max[0]),
            height: lpa(self.max[1]),
        };
        let in_flow = self.style.position != Position::Absolute;
        let child_ctx = ParentCtx {
            width_definite: matches!(self.size[0], Len::Px(_) | Len::Pct(_))
                || (self.size[0] == Len::Auto && in_flow && parent.width_definite),
            height_definite: matches!(self.size[1], Len::Px(_) | Len::Pct(_)),
        };
        MappedStyle {
            style: self.style,
            findings: self.findings,
            hidden: self.hidden,
            child_ctx,
        }
    }
}

fn side_of(name: &str) -> Side {
    match name {
        "top" => Side::Top,
        "right" => Side::Right,
        "bottom" => Side::Bottom,
        _ => Side::Left,
    }
}

fn dim(l: Len) -> Dimension {
    match l {
        Len::Auto => Dimension::auto(),
        Len::Px(v) => Dimension::length(v),
        Len::Pct(v) => Dimension::percent(v),
    }
}

fn lpa(l: Len) -> LengthPercentageAuto {
    match l {
        Len::Auto => LengthPercentageAuto::auto(),
        Len::Px(v) => LengthPercentageAuto::length(v),
        Len::Pct(v) => LengthPercentageAuto::percent(v),
    }
}
