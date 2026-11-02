//! LAYER001: a `z-index` integer that is not one of the declared `[layers]` values (port of
//! `crunk/rules/_layers.py`). `auto` and non-integer values are exempt; a project that declares no
//! layers has no design law to judge against, so the rule is then inapplicable and reported.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::{examined_sheets, site_path};

/// Parse an integer the way Python `int()` does: optional sign, digits, single `_` between digits.
fn parse_int(raw: &str) -> Option<i64> {
    let (neg, digits) = match raw.as_bytes().first()? {
        b'-' => (true, &raw[1..]),
        b'+' => (false, &raw[1..]),
        _ => (false, raw),
    };
    let bytes = digits.as_bytes();
    let well_formed = !bytes.is_empty()
        && bytes[0] != b'_'
        && bytes[bytes.len() - 1] != b'_'
        && !digits.contains("__")
        && bytes.iter().all(|b| b.is_ascii_digit() || *b == b'_');
    if !well_formed {
        return None;
    }
    let clean: String = digits.chars().filter(|c| *c != '_').collect();
    let value = clean.parse::<i64>().ok()?;
    Some(if neg { -value } else { value })
}

/// A `z-index` integer outside the declared layer values.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "LAYER001",
    slug = "z-index-off-layers",
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
pub struct Layer001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Layer001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let mut declared: Vec<i64> = spec.layers.values().copied().collect();
        declared.sort_unstable();
        declared.dedup();
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            for decl in sheet.declarations.iter().filter(|d| d.prop == "z-index") {
                let raw = decl.value.trim();
                if raw.eq_ignore_ascii_case("auto") {
                    continue;
                }
                let Some(value) = parse_int(raw) else {
                    tracing::debug!(%path, line = decl.line, raw, "LAYER001: unparseable z-index skipped");
                    continue;
                };
                if declared.contains(&value) {
                    continue;
                }
                tracing::debug!(%path, line = decl.line, value, "LAYER001: undeclared z-index");
                out.fire_in(
                    &path,
                    decl.span.0,
                    format!("z-index {value} is not among declared layers {declared:?}"),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        if let Some(why) = missing_inputs(host) {
            return Some(why);
        }
        host.spec()
            .is_some_and(|spec| spec.layers.is_empty())
            .then(|| "no [layers] are declared".to_owned())
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Layer001 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}

#[cfg(test)]
mod tests {
    use super::parse_int;

    // frob:tests crates/crunk-rules/src/rules/layer001.rs::Layer001
    #[test]
    fn parse_int_accepts_python_digit_separators() {
        assert_eq!(parse_int("1_0"), Some(10));
        assert_eq!(parse_int("-1_000"), Some(-1000));
        assert_eq!(parse_int("+7"), Some(7));
        assert_eq!(parse_int("42"), Some(42));
    }

    // frob:tests crates/crunk-rules/src/rules/layer001.rs::Layer001
    #[test]
    fn parse_int_rejects_malformed_separators() {
        for bad in ["", "_1", "1_", "1__0", "-", "-_1", "1.5", "1e3", "a1"] {
            assert_eq!(parse_int(bad), None, "{bad}");
        }
    }
}
