//! `preview`: a terminal sheet of the design spec (palette, scales, stacks, layers).
//!
//! Plain text by default; with `--color always` the palette rows carry a truecolor swatch.
//! `NO_COLOR` wins over `--color always`, so a set `NO_COLOR` never prints an escape code.

// frob:ticket 01M43ATD7ZGTNCY5036AYEJR7P

use crunk_spec::DesignSpec;
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;

/// Widest bar a scale row draws, in `#` characters.
const BAR_WIDTH: f64 = 40.0;
/// Column width of a row label.
const LABEL_WIDTH: usize = 24;

/// Print the design spec as a terminal sheet.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "preview",
    product = "crunk",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct Preview;

/// One titled block of the sheet.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct Section {
    /// `palette`, `spacing`, `font sizes`, `radii`, `stacks` or `layers`.
    pub name: String,
    /// The rows, uncolored.
    pub rows: Vec<String>,
}

/// Output of `preview`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct PreviewData {
    /// The sheet's sections in print order.
    pub sections: Vec<Section>,
}

impl Command for Preview {
    type Data = PreviewData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd
    }

    fn from_matches(_m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<PreviewData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let spec = crunk_spec::load_spec(&root).map_err(|e| {
            tracing::info!(error = %e, "preview: spec did not load");
            Refusal::new(
                "E-SPEC",
                RefusalClass::GuardNeedsAction,
                format!("crunk.toml is not a valid design spec: {e}"),
            )
            .with_remedy("fix crunk.toml as described, then rerun")
        })?;
        let color = ctx.color == gob_diagnostics::ColorChoice::Always
            && std::env::var_os("NO_COLOR").is_none();
        tracing::debug!(color, "preview: rendering");
        let rendered = render(&spec, color);
        let data = PreviewData {
            sections: sections(&spec),
        };
        Ok(Payload::new(data).with_rendered(rendered))
    }
}

/// Format a px value without a trailing `.0`.
fn num(v: f64) -> String {
    if v.fract() == 0.0 {
        format!("{v:.0}")
    } else {
        format!("{v}")
    }
}

/// Bar length for `v` against the largest step: at least one `#`, at most 40.
fn bar(v: f64, max: f64) -> usize {
    if max <= 0.0 {
        return 1;
    }
    let n = (v / max * BAR_WIDTH).round_ties_even();
    // Clamped to 1..=40 first, so the conversion cannot truncate or go negative.
    #[expect(clippy::cast_possible_truncation, clippy::cast_sign_loss)]
    let n = n.clamp(1.0, BAR_WIDTH) as usize;
    n
}

fn scale_rows(values: &[f64]) -> Vec<String> {
    let max = values.iter().copied().fold(0.0_f64, f64::max);
    values
        .iter()
        .map(|&v| format!("{:>8}px  {}", num(v), "#".repeat(bar(v, max))))
        .collect()
}

/// The `(r, g, b)` bytes of a `#rrggbb[aa]` string.
fn channels(hex: &str) -> (u8, u8, u8) {
    let byte = |i: usize| {
        hex.get(i..i + 2)
            .and_then(|s| u8::from_str_radix(s, 16).ok())
            .unwrap_or(0)
    };
    (byte(1), byte(3), byte(5))
}

fn palette_rows(spec: &DesignSpec, color: bool) -> Vec<String> {
    spec.palette
        .iter()
        .map(|(name, c)| {
            let hex = c.to_hex();
            let swatch = if color {
                let (r, g, b) = channels(&hex);
                format!("    \x1b[48;2;{r};{g};{b}m    \x1b[0m")
            } else {
                "  ".to_owned()
            };
            format!("  {name:<LABEL_WIDTH$} {hex}{swatch}")
        })
        .collect()
}

fn stack_rows(spec: &DesignSpec) -> Vec<String> {
    spec.typography
        .stacks
        .iter()
        .map(|(name, members)| format!("  {name:<LABEL_WIDTH$} {}", members.join(", ")))
        .collect()
}

fn layer_rows(spec: &DesignSpec) -> Vec<String> {
    spec.layers
        .iter()
        .map(|(name, z)| format!("  {name:<LABEL_WIDTH$} {z}"))
        .collect()
}

/// Every section as `(name, rows)` with palette rows colored per `color`.
fn blocks(spec: &DesignSpec, color: bool) -> Vec<(&'static str, Vec<String>)> {
    vec![
        ("palette", palette_rows(spec, color)),
        ("spacing", scale_rows(&spec.scales.spacing)),
        ("font sizes", scale_rows(&spec.scales.font_sizes)),
        ("radii", scale_rows(&spec.scales.radii)),
        ("stacks", stack_rows(spec)),
        ("layers", layer_rows(spec)),
    ]
}

fn sections(spec: &DesignSpec) -> Vec<Section> {
    blocks(spec, false)
        .into_iter()
        .map(|(name, rows)| Section {
            name: name.to_owned(),
            rows,
        })
        .collect()
}

/// The sheet as output lines: blank-line separated sections, `(empty)` for a bare one.
#[must_use]
pub fn render(spec: &DesignSpec, color: bool) -> Vec<String> {
    let mut out = Vec::new();
    for (i, (name, rows)) in blocks(spec, color).into_iter().enumerate() {
        if i > 0 {
            out.push(String::new());
        }
        out.push(name.to_owned());
        if rows.is_empty() {
            out.push("  (empty)".to_owned());
        } else {
            out.extend(rows);
        }
    }
    out
}
