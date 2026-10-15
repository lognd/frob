//! Queries over ingested styles and the token set: `find`, `component`, `dupes`, `unused`,
//! `uses`, `color`, the `map` inventory and `explain`.
//!
//! Every query is a pure function of a [`Model`]; nothing reads the disk. Paths in rows are
//! relative to the project root and `/`-separated.

// frob:ticket 01M43ATCZXK3B3952GGEBT1ASJ

pub mod rows;

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use crunk_ingest::{Bucket, ProjectStyles, Stylesheet};
use crunk_tokens::naming::bare_name;
use crunk_tokens::{Token, TokenKind, TokenSet};
use crunk_values::Color;

pub use rows::{
    ColorRow, ComponentRow, DupeRow, ElementRow, ExplainRow, FindRow, MapData, MapEntry, MatchKind,
    NameKind, Site, UnusedRow,
};

/// The default `dupes` similarity threshold.
pub const DEFAULT_DUPE_THRESHOLD: f64 = 0.6;

/// How many close matches `explain` offers for an unknown token.
const SUGGESTIONS: usize = 5;

/// The data every query reads: ingested styles, the token set and the project root.
#[derive(Debug, Clone, Copy)]
pub struct Model<'a> {
    /// Every parsed sheet.
    pub styles: &'a ProjectStyles,
    /// The token set derived from the spec.
    pub tokens: &'a TokenSet,
    /// The project root paths are made relative to.
    pub root: &'a Path,
}

/// Round to two decimals, the precision the Python crunk printed.
fn round2(value: f64) -> f64 {
    (value * 100.0).round() / 100.0
}

impl<'a> Model<'a> {
    /// Build a model over `styles` and `tokens` rooted at `root`.
    pub fn new(styles: &'a ProjectStyles, tokens: &'a TokenSet, root: &'a Path) -> Self {
        Self {
            styles,
            tokens,
            root,
        }
    }

    /// `path` relative to the root, `/`-separated.
    #[expect(
        clippy::disallowed_methods,
        reason = "confinement allow list: path-to-text conversion pending migration to gob-path"
    )]
    pub fn relative(&self, path: &Path) -> String {
        path.strip_prefix(self.root)
            .unwrap_or(path)
            .to_string_lossy()
            .replace('\\', "/")
    }

    /// Every `var(--name)` reference site of `name` (with `--`), sorted.
    fn var_sites(&self, name: &str) -> Vec<Site> {
        let mut sites: Vec<Site> = self
            .styles
            .sheets
            .iter()
            .flat_map(|sheet| {
                sheet
                    .declarations
                    .iter()
                    .filter(move |d| d.var_refs.iter().any(|r| r.name == name))
                    .map(move |d| Site {
                        path: self.relative(&sheet.path),
                        line: d.line,
                    })
            })
            .collect();
        sites.sort();
        sites.dedup();
        sites
    }

    /// Utilities (one per use, as written) whose class resolves to the token called `bare`.
    fn utility_matches(&self, bare: &str) -> Vec<&str> {
        let suffix = format!("-{bare}");
        self.styles
            .sheets
            .iter()
            .flat_map(|s| s.utilities.iter())
            .map(|u| u.name.as_str())
            .filter(|name| name.split('/').next().unwrap_or(name).ends_with(&suffix))
            .collect()
    }

    /// Distinct utilities (as written) whose class resolves to the token called `bare`.
    fn token_utilities(&self, bare: &str) -> Vec<String> {
        let found: BTreeSet<&str> = self.utility_matches(bare).into_iter().collect();
        found.into_iter().map(str::to_owned).collect()
    }

    /// Utility uses of the class called `name`.
    fn class_uses(&self, name: &str) -> usize {
        self.styles
            .sheets
            .iter()
            .flat_map(|s| s.utilities.iter())
            .filter(|u| u.name == name)
            .count()
    }

    /// Reference count for a token: `var()` sites plus matching utility uses.
    fn token_uses(&self, token: &Token) -> usize {
        self.var_sites(&token.name).len() + self.utility_matches(bare_name(&token.name)).len()
    }

    /// Names matching `query` (token or class), exact before prefix before substring, then by
    /// use count descending.
    pub fn find(&self, query: &str) -> Vec<FindRow> {
        let needle = bare_name(query.trim())
            .trim_start_matches('.')
            .to_lowercase();
        if needle.is_empty() {
            return Vec::new();
        }
        let mut rows = Vec::new();
        let mut push = |name: String, shown: String, kind: NameKind, uses: usize| {
            let lower = name.to_lowercase();
            let matched = if lower == needle {
                MatchKind::Exact
            } else if lower.starts_with(&needle) {
                MatchKind::Prefix
            } else if lower.contains(&needle) {
                MatchKind::Substring
            } else {
                return;
            };
            rows.push(FindRow {
                name: shown,
                kind,
                matched,
                uses,
            });
        };
        for token in self.tokens.iter() {
            let bare = bare_name(&token.name).to_owned();
            push(
                bare,
                token.name.clone(),
                NameKind::Token,
                self.token_uses(token),
            );
        }
        let classes: BTreeSet<&str> = self
            .styles
            .sheets
            .iter()
            .flat_map(|s| s.class_selectors.iter())
            .map(|c| c.name.as_str())
            .collect();
        for class in classes {
            push(
                class.to_owned(),
                class.to_owned(),
                NameKind::Class,
                self.class_uses(class),
            );
        }
        rows.sort_by(|a, b| {
            (a.matched as u8)
                .cmp(&(b.matched as u8))
                .then(b.uses.cmp(&a.uses))
                .then_with(|| a.name.cmp(&b.name))
        });
        tracing::debug!(query, hits = rows.len(), "query find");
        rows
    }

    /// The BEM structure of component `name`, or `None` when no sheet owns it.
    pub fn component(&self, name: &str) -> Option<ComponentRow> {
        let sheets: Vec<&Stylesheet> = self
            .styles
            .sheets
            .iter()
            .filter(|s| s.component.as_deref() == Some(name))
            .collect();
        if sheets.is_empty() {
            tracing::debug!(name, "query component: unknown");
            return None;
        }
        let element_prefix = format!("{name}__");
        let modifier_prefix = format!("{name}--");
        let mut modifiers = BTreeSet::new();
        let mut elements: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
        for class in sheets.iter().flat_map(|s| s.class_selectors.iter()) {
            if let Some(m) = class.name.strip_prefix(&modifier_prefix) {
                modifiers.insert(m.to_owned());
            } else if let Some(rest) = class.name.strip_prefix(&element_prefix) {
                let (element, modifier) = match rest.split_once("--") {
                    Some((e, m)) => (e, Some(m)),
                    None => (rest, None),
                };
                let entry = elements.entry(element.to_owned()).or_default();
                if let Some(m) = modifier {
                    entry.insert(m.to_owned());
                }
            }
        }
        Some(ComponentRow {
            name: name.to_owned(),
            paths: sheets.iter().map(|s| self.relative(&s.path)).collect(),
            modifiers: modifiers.into_iter().collect(),
            elements: elements
                .into_iter()
                .map(|(name, mods)| ElementRow {
                    name,
                    modifiers: mods.into_iter().collect(),
                })
                .collect(),
            declarations: sheets.iter().map(|s| s.declarations.len()).sum(),
        })
    }

    /// Sheet pairs whose shared `(property, value)` pairs reach `threshold` of the smaller sheet.
    pub fn dupes(&self, threshold: f64) -> Vec<DupeRow> {
        let sets: Vec<(String, BTreeSet<(&str, &str)>)> = self
            .styles
            .sheets
            .iter()
            .filter(|s| s.bucket != Some(Bucket::Tokens))
            .map(|s| {
                let set = s
                    .declarations
                    .iter()
                    .map(|d| (d.prop.as_str(), d.value.as_str()))
                    .collect();
                (self.relative(&s.path), set)
            })
            .filter(|(_, set): &(String, BTreeSet<_>)| !set.is_empty())
            .collect();
        let mut rows = Vec::new();
        for (i, (path_a, a)) in sets.iter().enumerate() {
            for (path_b, b) in &sets[i + 1..] {
                let shared = a.intersection(b).count();
                #[allow(clippy::cast_precision_loss, reason = "set sizes of one stylesheet")]
                let score = shared as f64 / a.len().min(b.len()) as f64;
                if shared > 0 && score >= threshold {
                    let (first, second) = if path_a <= path_b {
                        (path_a, path_b)
                    } else {
                        (path_b, path_a)
                    };
                    rows.push(DupeRow {
                        a: first.clone(),
                        b: second.clone(),
                        score: round2(score),
                        shared,
                    });
                }
            }
        }
        rows.sort_by(|x, y| {
            y.score
                .total_cmp(&x.score)
                .then_with(|| (&x.a, &x.b).cmp(&(&y.a, &y.b)))
        });
        tracing::debug!(threshold, pairs = rows.len(), "query dupes");
        rows
    }

    /// Tokens no `var()` and no utility references, sorted by name.
    pub fn unused(&self) -> Vec<UnusedRow> {
        let mut rows: Vec<UnusedRow> = self
            .tokens
            .iter()
            .filter(|t| self.token_uses(t) == 0)
            .map(|t| UnusedRow {
                name: t.name.clone(),
            })
            .collect();
        rows.sort_by(|a, b| a.name.cmp(&b.name));
        tracing::debug!(count = rows.len(), "query unused");
        rows
    }

    /// Every `var()` site of token `name` (with or without `--`), sorted.
    pub fn uses(&self, name: &str) -> Vec<Site> {
        self.var_sites(&format!("--{}", bare_name(name.trim())))
    }

    /// Palette colors by distance to `value`; `None` when `value` is not a color.
    pub fn color(&self, value: &str) -> Option<Vec<ColorRow>> {
        let text = value.trim();
        let wanted = Color::parse(text)
            .or_else(|_| Color::parse(&format!("#{text}")))
            .ok()?;
        let mut rows: Vec<ColorRow> = self
            .tokens
            .of_kind(TokenKind::Color)
            .filter_map(|token| {
                let css = token.value.css()?;
                let color = Color::parse(&css).ok()?;
                let distance = wanted.distance(color);
                let same_rgb = distance == 0.0;
                let same_alpha = (wanted.a - color.a).abs() < 1e-9;
                Some(ColorRow {
                    name: token.key.clone(),
                    value: css,
                    distance: round2(distance),
                    exact: same_rgb && same_alpha,
                    alpha_variant: same_rgb && !same_alpha,
                })
            })
            .collect();
        rows.sort_by(|a, b| {
            a.distance
                .total_cmp(&b.distance)
                .then_with(|| a.name.cmp(&b.name))
        });
        tracing::debug!(value, palette = rows.len(), "query color");
        Some(rows)
    }

    /// The inventory of every bucket (canonical order) plus the strays.
    pub fn map(&self) -> MapData {
        const ORDER: [Bucket; 7] = [
            Bucket::Base,
            Bucket::Components,
            Bucket::Layouts,
            Bucket::Utilities,
            Bucket::Entry,
            Bucket::Jsx,
            Bucket::Tokens,
        ];
        let buckets = ORDER
            .iter()
            .map(|bucket| {
                let mut entries: Vec<MapEntry> = self
                    .styles
                    .sheets
                    .iter()
                    .filter(|s| s.bucket == Some(*bucket))
                    .map(|s| self.map_entry(*bucket, s))
                    .collect();
                entries.sort_by(|a, b| a.path.cmp(&b.path));
                (bucket.as_str().to_owned(), entries)
            })
            .collect();
        let mut strays: Vec<String> = self
            .styles
            .strays
            .iter()
            .map(|p| self.relative(p))
            .collect();
        strays.sort();
        MapData {
            buckets: rows::indexed::Buckets(buckets),
            strays,
        }
    }

    /// One inventory entry for `sheet` in `bucket`.
    fn map_entry(&self, bucket: Bucket, sheet: &Stylesheet) -> MapEntry {
        let jsx = bucket == Bucket::Jsx;
        MapEntry {
            path: self.relative(&sheet.path),
            component: sheet.component.clone(),
            classes: (!jsx).then_some(sheet.class_selectors.len()),
            declarations: jsx.then_some(sheet.declarations.len()),
            utilities: jsx.then_some(sheet.utilities.len()),
        }
    }

    /// Everything that touches token `name` (with or without `--`), or the close matches.
    ///
    /// # Errors
    ///
    /// Returns up to five close-match names when `name` is not an exported token.
    pub fn explain(
        &self,
        name: &str,
        defined_in: Option<&Path>,
    ) -> Result<ExplainRow, Vec<String>> {
        let wanted = format!("--{}", bare_name(name.trim()));
        let Some(token) = self.tokens.get(&wanted) else {
            let close = close_matches(
                bare_name(&wanted),
                self.tokens.iter().map(|t| bare_name(&t.name)),
            );
            tracing::info!(name, suggestions = close.len(), "explain: unknown token");
            return Err(close);
        };
        Ok(ExplainRow {
            name: token.name.clone(),
            value: token.value.css(),
            group: kind_word(token.kind).to_owned(),
            defined_in: defined_in.map(|p| self.relative(p)),
            sites: self.var_sites(&token.name),
            utilities: self.token_utilities(bare_name(&token.name)),
        })
    }
}

/// The kebab-case family word for a token kind.
pub fn kind_word(kind: TokenKind) -> &'static str {
    match kind {
        TokenKind::Color => "color",
        TokenKind::ColorChannels => "color-channels",
        TokenKind::Space => "space",
        TokenKind::FontSize => "font-size",
        TokenKind::Radius => "radius",
        TokenKind::Size => "size",
        TokenKind::Layer => "layer",
        TokenKind::FontFamily => "font-family",
        TokenKind::Custom => "custom",
        _ => "other",
    }
}

/// Up to `SUGGESTIONS` candidates near `wanted`: substrings first, then by edit distance.
pub fn close_matches<'a>(wanted: &str, candidates: impl Iterator<Item = &'a str>) -> Vec<String> {
    let wanted = wanted.to_lowercase();
    let limit = (wanted.len() / 3).max(2);
    let mut scored: Vec<(usize, &str)> = candidates
        .filter_map(|c| {
            let lower = c.to_lowercase();
            let distance = edit_distance(&wanted, &lower);
            if lower.contains(&wanted) || wanted.contains(&lower) {
                Some((0, c))
            } else if distance <= limit {
                Some((distance, c))
            } else {
                None
            }
        })
        .collect();
    scored.sort_unstable();
    scored
        .into_iter()
        .take(SUGGESTIONS)
        .map(|(_, c)| c.to_owned())
        .collect()
}

/// Levenshtein distance between `a` and `b`.
fn edit_distance(a: &str, b: &str) -> usize {
    let b: Vec<char> = b.chars().collect();
    let mut prev: Vec<usize> = (0..=b.len()).collect();
    for (i, ca) in a.chars().enumerate() {
        let mut cur = vec![i + 1];
        for (j, cb) in b.iter().enumerate() {
            let cost = usize::from(ca != *cb);
            cur.push((prev[j] + cost).min(prev[j + 1] + 1).min(cur[j] + 1));
        }
        prev = cur;
    }
    prev[b.len()]
}
