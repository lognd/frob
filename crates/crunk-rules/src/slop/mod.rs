//! What the SLOP rules share (crunk.md section 6, `notes/research/deslop-research-2026-10-08.md`):
//! the decision gate, the Tailwind default accent stops, an emoji test, and a small markup scanner
//! over JSX sources. All of it is T0: text and declarations only, no render.

// frob:ticket 01M4CXT4Z45GR5QE71B10FRR8N

use crunk_ingest::{Bucket, ProjectStyles, Stylesheet};
use crunk_spec::DesignSpec;
use crunk_values::Color;

/// Distance (`deltaE_OK` times 100, the scale COLOR001 reports) under which a colour is "the
/// default": 2 is the research's 0.02 OKLCH threshold.
pub const DEFAULT_ACCENT_DISTANCE: f64 = 2.0;

/// True when `[decisions]` declares `key`: the unchosen-default rules are then silent.
pub fn decided(spec: &DesignSpec, key: &str) -> bool {
    let declared = spec.decided(key);
    if declared {
        tracing::debug!(key, "SLOP: a declared decision silences the rule");
    }
    declared
}

/// Every non-tokens sheet of the project (the generated tokens sheet restates the palette).
pub fn judged_sheets(styles: &ProjectStyles) -> impl Iterator<Item = &Stylesheet> {
    styles
        .sheets
        .iter()
        .filter(|s| !crate::sheets::is_tokens_sheet(s))
}

/// Every JSX or TSX source sheet, whose `source` is markup the text rules read.
pub fn markup_sheets(styles: &ProjectStyles) -> impl Iterator<Item = &Stylesheet> {
    styles
        .sheets
        .iter()
        .filter(|s| s.bucket == Some(Bucket::Jsx))
}

/// The Tailwind indigo, violet and purple 400-700 stops, the default "AI accent" (SLOP001).
pub fn default_accent_stops() -> Vec<(&'static str, Color)> {
    crunk_tailwind::defaults::V3_COLOR_HEXES
        .iter()
        .filter(|(name, _)| {
            let Some((hue, step)) = name.split_once('-') else {
                return false;
            };
            matches!(hue, "indigo" | "violet" | "purple")
                && matches!(step, "400" | "500" | "600" | "700")
        })
        .filter_map(|(name, hex)| Color::parse(hex).ok().map(|c| (*name, c)))
        .collect()
}

/// The default accent stop `color` sits on, if any.
pub fn default_accent_of(color: Color, stops: &[(&'static str, Color)]) -> Option<&'static str> {
    if !color.is_opaque() {
        return None;
    }
    stops.iter().find_map(|(name, stop)| {
        (color.delta_e_ok(*stop) * crate::color::DELTA_SCALE < DEFAULT_ACCENT_DISTANCE)
            .then_some(*name)
    })
}

/// True for a pictographic emoji (the `Extended_Pictographic` blocks that appear as bullets and icons).
pub fn is_emoji(c: char) -> bool {
    matches!(
        u32::from(c),
        0x1F000..=0x1FAFF | 0x2600..=0x27BF | 0x2B50 | 0x2B55 | 0x2B1B | 0x2B1C | 0x2934 | 0x2935
    )
}

/// The first character of `text`, reading a leading numeric character reference (`&#x1F680;`,
/// `&#128640;`) or CSS escape (`\1F680`) as the character it names.
pub fn leading_char(text: &str) -> Option<char> {
    let text = text.trim_start();
    if let Some(rest) = text.strip_prefix("&#") {
        let (digits, radix) = match rest.strip_prefix(['x', 'X']) {
            Some(hex) => (hex, 16),
            None => (rest, 10),
        };
        let end = digits.find(';')?;
        return u32::from_str_radix(&digits[..end], radix)
            .ok()
            .and_then(char::from_u32);
    }
    if let Some(rest) = text.strip_prefix('\\') {
        let end = rest
            .find(|c: char| !c.is_ascii_hexdigit())
            .unwrap_or(rest.len());
        if end > 0 {
            return u32::from_str_radix(&rest[..end], 16)
                .ok()
                .and_then(char::from_u32);
        }
    }
    text.chars().next()
}

/// One markup tag found by [`tags`].
#[derive(Debug, Clone, Copy)]
pub struct Tag<'a> {
    /// Byte offset of the `<`.
    pub start: usize,
    /// Byte offset just past the `>`.
    pub end: usize,
    /// Lowercased element name (`div`, `h1`; a component keeps its case lowered too).
    pub name: &'a str,
    /// True for `</name>`.
    pub closing: bool,
    /// The raw attribute text between the name and the `>`.
    pub attrs: &'a str,
}

/// The tags of `source` in order. Braced expressions and quoted attribute values are skipped, so a
/// `>` inside `{...}` or `"..."` does not end a tag; text that is not a tag (a comparison) is ignored.
pub fn tags(source: &str) -> Vec<Tag<'_>> {
    let bytes = source.as_bytes();
    let mut found = Vec::new();
    let mut at = 0;
    while at < bytes.len() {
        if bytes[at] != b'<' {
            at += 1;
            continue;
        }
        let closing = bytes.get(at + 1) == Some(&b'/');
        let name_start = at + 1 + usize::from(closing);
        let name_len = source[name_start..]
            .bytes()
            .take_while(|b| b.is_ascii_alphanumeric() || *b == b'.' || *b == b'-')
            .count();
        if name_len == 0 || !bytes[name_start].is_ascii_alphabetic() {
            at += 1;
            continue;
        }
        let mut depth = 0usize;
        let mut quote = 0u8;
        let mut end = None;
        for (i, &b) in bytes.iter().enumerate().skip(name_start + name_len) {
            match b {
                b'"' | b'\'' if depth == 0 => {
                    quote = if quote == b {
                        0
                    } else if quote == 0 {
                        b
                    } else {
                        quote
                    };
                }
                _ if quote != 0 => {}
                b'{' => depth += 1,
                b'}' => depth = depth.saturating_sub(1),
                b'>' if depth == 0 => {
                    end = Some(i + 1);
                    break;
                }
                b'<' if depth == 0 => break,
                _ => {}
            }
        }
        let Some(end) = end else {
            at += 1;
            continue;
        };
        found.push(Tag {
            start: at,
            end,
            name: &source[name_start..name_start + name_len],
            closing,
            attrs: &source[name_start + name_len..end - 1],
        });
        at = end;
    }
    found
}

/// The literal text between `tag` and the next tag or braced expression, trimmed, with the byte
/// offset where it starts; `None` when there is none.
pub fn text_after<'a>(source: &'a str, tag: &Tag<'_>) -> Option<(usize, &'a str)> {
    let rest = &source[tag.end..];
    let stop = rest.find(['<', '{']).unwrap_or(rest.len());
    let raw = &rest[..stop];
    let text = raw.trim();
    (!text.is_empty()).then(|| (tag.end + (raw.len() - raw.trim_start().len()), text))
}

/// A lowercase name test that tolerates the JSX `class`/`className` split: true when the tag's
/// attribute text contains any of `needles` (lowercased compare).
pub fn attrs_mention(tag: &Tag<'_>, needles: &[&str]) -> bool {
    let attrs = tag.attrs.to_lowercase();
    needles.iter().any(|n| attrs.contains(n))
}
