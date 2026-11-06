//! DUP001 and DUP002: blocks of code copied three or more times (DUP001 exact, DUP002 renamed or same shape), found by token hashing (clone rungs R1-R3).
//!
//! Each supported source file becomes a language-agnostic token stream ([`crate::dup_lex`]). Every
//! window of `min_tokens` tokens is hashed three ways, one per rung:
//!
//! - **R1** the exact tokens;
//! - **R2** the tokens with identifiers alpha-renamed by first occurrence in the window, so a copy
//!   that only renamed variables still matches;
//! - **R3** the token shape: identifiers, numbers and strings abstracted to their kind.
//!
//! Windows that share a hash form a class; a class with at least `min_occurrences` disjoint
//! sites is a clone, and consecutive windows over the same sites merge into one block. A block
//! already reported by a stricter rung is not reported again by a looser one.

// frob:ticket 01M4D958QKMX7VHFJMRMAWDT22
// frob:ticket 01M5HMKRFRZYFQC6HVNPHC3Z2P
// frob:ticket 01M4P0SXCZQTRS8W10VXJ1W4P0
// frob:ticket 01M4P0SX8PWMV49CTPDX2SAP57

use std::collections::HashMap;
use std::path::Path;

use gob_rules::Severity;
use gob_symbols::SymbolGraph;

use crate::dup_index::{DupIndex, IndexError, RUNGS, Windows};
use crate::dup_lex::{Kind, Tok, tokens};
use crate::{DUP, DUP_INDEX, DUP_RENAMED, Verdict};

/// Tokens over the whole walk beyond which the pass is skipped, so a huge repo cannot stall a check.
const MAX_TOTAL_TOKENS: usize = 2_000_000;
/// Sites listed in a message before it says "and N more".
const LISTED_SITES: usize = 12;
/// Adapter language tags whose files are lexed.
const LANGUAGES: &[&str] = &["rust", "python", "typescript", "csharp"];

/// One position: (file index, token index of the window start).
type Site = (usize, usize);

/// How strictly two windows must agree to match.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Rung {
    /// R1: the same tokens.
    Exact,
    /// R2: the same tokens up to a consistent renaming of identifiers.
    Renamed,
    /// R3: the same token shape (identifiers and literals abstracted).
    Shape,
}

impl Rung {
    /// Every rung, strictest first; the position is the rung's slot in [`Windows`].
    const ALL: [Rung; RUNGS] = [Rung::Exact, Rung::Renamed, Rung::Shape];

    /// The short label used in anchors.
    fn label(self) -> &'static str {
        match self {
            Rung::Exact => "R1",
            Rung::Renamed => "R2",
            Rung::Shape => "R3",
        }
    }

    /// The rule that reports a block matched at this rung: `DUP001` for exact copies, `DUP002` otherwise.
    fn rule(self) -> &'static str {
        match self {
            Rung::Exact => DUP,
            Rung::Renamed | Rung::Shape => DUP_RENAMED,
        }
    }

    /// How the copies differ, for the message.
    fn describe(self) -> &'static str {
        match self {
            Rung::Exact => "identical",
            Rung::Renamed => "identical up to renamed identifiers",
            Rung::Shape => "identical in shape, differing in names and literals",
        }
    }
}

/// A reported block: `sites` all hold `len` tokens that match at `rung`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Clone {
    /// The strictest rung at which the sites match.
    pub rung: Rung,
    /// Tokens in the block.
    pub len: usize,
    /// Where each copy starts (file index, token index), in file then position order.
    pub sites: Vec<Site>,
    /// Hash of the first window, the block's stable identity.
    pub key: u128,
}

/// A 64-bit FNV-1a hash of `s`.
pub(crate) fn fnv(s: &str) -> u64 {
    s.bytes().fold(0xcbf2_9ce4_8422_2325, |h, b| {
        (h ^ u64::from(b)).wrapping_mul(0x0100_0000_01b3)
    })
}

/// Cumulative count of non-keyword identifiers: `out[i]` counts those before token `i`.
fn ident_prefix(toks: &[Tok<'_>]) -> Vec<usize> {
    let mut out = Vec::with_capacity(toks.len() + 1);
    let mut n = 0;
    out.push(0);
    for t in toks {
        n += usize::from(t.kind == Kind::Ident);
        out.push(n);
    }
    out
}

/// The hash of one window at `rung`.
fn window_key(window: &[Tok<'_>], rung: Rung, names: &mut Vec<&'static str>) -> u128 {
    // `names` is only a scratch buffer of renamed identifiers; stored as indexes below.
    names.clear();
    let mut local: Vec<&str> = Vec::new();
    let (mut a, mut b) = (0_u64, 0x9e37_79b9_7f4a_7c15_u64);
    for t in window {
        let v = match (rung, t.kind) {
            (Rung::Renamed, Kind::Ident) => {
                let idx = local.iter().position(|n| *n == t.text).unwrap_or_else(|| {
                    local.push(t.text);
                    local.len() - 1
                });
                0x1000_0000_0000_0000 + idx as u64
            }
            (Rung::Shape, Kind::Ident) => 0x2000_0000_0000_0001,
            (Rung::Shape, Kind::Number | Kind::Str) => 0x2000_0000_0000_0002,
            _ => fnv(t.text),
        };
        a = (a.rotate_left(5) ^ v).wrapping_mul(0x517c_c1b7_2722_0a95);
        b = (b ^ v).wrapping_mul(0x0100_0000_01b3).rotate_left(17);
    }
    (u128::from(a) << 64) | u128::from(b)
}

/// The hash of every window of `m` tokens in `toks`, one list per rung (empty when too short).
pub(crate) fn window_keys(toks: &[Tok<'_>], m: usize) -> Windows {
    let mut scratch = Vec::new();
    std::array::from_fn(|r| {
        if m == 0 || toks.len() < m {
            return Vec::new();
        }
        (0..=toks.len() - m)
            .map(|p| window_key(&toks[p..p + m], Rung::ALL[r], &mut scratch))
            .collect()
    })
}

/// The classes of windows at `rung` with enough disjoint sites, in first-site order.
fn classes_of(
    prefixes: &[Vec<usize>],
    keys: &[Windows],
    rung: Rung,
    m: usize,
    occ: usize,
) -> Vec<(u128, Vec<Site>)> {
    let slot = Rung::ALL.iter().position(|r| *r == rung).unwrap_or(0);
    let mut groups: HashMap<u128, Vec<Site>> = HashMap::new();
    for (f, file_keys) in keys.iter().enumerate() {
        for (p, &key) in file_keys[slot].iter().enumerate() {
            if prefixes[f][p + m] - prefixes[f][p] < m / 5 {
                continue;
            }
            let sites = groups.entry(key).or_default();
            // Disjoint sites only: a periodic block must not match itself.
            if sites.last().is_none_or(|&(lf, lp)| lf != f || lp + m <= p) {
                sites.push((f, p));
            }
        }
    }
    let mut classes: Vec<_> = groups.into_iter().filter(|(_, s)| s.len() >= occ).collect();
    classes.sort_by_key(|(_, s)| s[0]);
    classes
}

/// True when every site of `next` is the matching site of `cur` shifted by one token.
fn shifted_by_one(cur: &[Site], next: &[Site]) -> bool {
    cur.len() == next.len()
        && cur
            .iter()
            .zip(next)
            .all(|(c, n)| n.0 == c.0 && n.1 == c.1 + 1)
}

/// True when growing the block to `len` tokens would make two sites of one file overlap.
fn would_overlap(sites: &[Site], len: usize) -> bool {
    sites
        .windows(2)
        .any(|w| w[0].0 == w[1].0 && w[0].1 + len > w[1].1)
}

/// The clone blocks over `files`, windows of `m` tokens, reported from `occ` disjoint copies.
#[cfg(test)]
pub(crate) fn find_clones(files: &[Vec<Tok<'_>>], m: usize, occ: usize) -> Vec<Clone> {
    let keys: Vec<Windows> = files.iter().map(|t| window_keys(t, m)).collect();
    find_clones_keyed(files, &keys, m, occ)
}

/// [`find_clones`] over window hashes already computed (`keys[file]`, from [`window_keys`] or the index).
pub(crate) fn find_clones_keyed(
    files: &[Vec<Tok<'_>>],
    keys: &[Windows],
    m: usize,
    occ: usize,
) -> Vec<Clone> {
    let mut found = Vec::new();
    if m == 0 || occ < 2 {
        return found;
    }
    let prefixes: Vec<Vec<usize>> = files.iter().map(|t| ident_prefix(t)).collect();
    let mut covered: Vec<Vec<bool>> = files.iter().map(|t| vec![false; t.len()]).collect();
    for rung in Rung::ALL {
        let classes = classes_of(&prefixes, keys, rung, m, occ);
        let at: HashMap<Site, usize> = classes
            .iter()
            .enumerate()
            .flat_map(|(i, (_, s))| s.iter().map(move |&site| (site, i)))
            .collect();
        for (ci, (key, sites)) in classes.iter().enumerate() {
            if sites.iter().all(|&(f, p)| covered[f][p]) {
                continue;
            }
            let (mut len, mut cur) = (m, ci);
            while let Some(&next) = at.get(&(sites[0].0, classes[cur].1[0].1 + 1)) {
                if !shifted_by_one(&classes[cur].1, &classes[next].1)
                    || would_overlap(sites, len + 1)
                {
                    break;
                }
                len += 1;
                cur = next;
            }
            for &(f, p) in sites {
                covered[f][p..p + len].iter_mut().for_each(|c| *c = true);
            }
            tracing::debug!(
                rung = rung.label(),
                len,
                copies = sites.len(),
                "DUP001 clone block"
            );
            found.push(Clone {
                rung,
                len,
                sites: sites.clone(),
                key: *key,
            });
        }
    }
    found
}

/// True for the files whose language is lexed and that are not tests.
fn wanted(path: &str, language: &str) -> bool {
    LANGUAGES.contains(&language) && !grimble_bind::eval::is_test_unit(path)
}

/// Findings for blocks of `min_tokens` tokens copied at least `min_occurrences` times, and the files examined.
///
/// A `min_tokens` of 0 or a `min_occurrences` below 2 finds nothing (see [`find_clones`]).
pub(crate) fn check(
    graph: &SymbolGraph,
    read: &dyn Fn(&str) -> Option<String>,
    min_tokens: usize,
    min_occurrences: usize,
    index: Option<&Path>,
) -> (Vec<Verdict>, usize) {
    let mut paths: Vec<(&str, bool)> = Vec::new();
    for (path, info) in graph.files() {
        if wanted(path, &info.language) {
            paths.push((path, info.language == "python"));
        }
    }
    let mut texts: Vec<(&str, bool, String)> = Vec::new();
    for (path, hash_style) in paths {
        if let Some(text) = read(path) {
            texts.push((path, hash_style, text));
        } else {
            tracing::warn!(path, "DUP001 skipped an unreadable file");
        }
    }
    let files: Vec<Vec<Tok<'_>>> = texts.iter().map(|(_, h, t)| tokens(t, *h)).collect();
    let total: usize = files.iter().map(Vec::len).sum();
    if total > MAX_TOTAL_TOKENS {
        tracing::warn!(
            total,
            MAX_TOTAL_TOKENS,
            "DUP001 skipped: too many tokens in the walk"
        );
        return (Vec::new(), texts.len());
    }
    let index = index.filter(|_| min_tokens > 0 && min_occurrences >= 2);
    let keys = match window_keys_for(&texts, &files, min_tokens, index) {
        Ok(keys) => keys,
        Err(err) => {
            tracing::error!(%err, "DUP003 clone index unusable; DUP001 not evaluated");
            return (vec![index_failure(&err, &texts)], texts.len());
        }
    };
    let findings = find_clones_keyed(&files, &keys, min_tokens, min_occurrences)
        .into_iter()
        .map(|c| finding(&c, &texts, &files))
        .collect();
    (findings, texts.len())
}

/// The window hashes of every file, through the shared index when `index` names a directory.
fn window_keys_for(
    texts: &[(&str, bool, String)],
    files: &[Vec<Tok<'_>>],
    m: usize,
    index: Option<&Path>,
) -> Result<Vec<Windows>, IndexError> {
    let Some(dir) = index.filter(|_| m > 0) else {
        return Ok(files.iter().map(|t| window_keys(t, m)).collect());
    };
    let store = DupIndex::open(dir)?;
    texts
        .iter()
        .zip(files)
        .map(|((_, hash_style, text), toks)| {
            store.windows(text, *hash_style, m, || window_keys(toks, m))
        })
        .collect()
}

/// The `DUP003` finding for an unusable index, anchored at the first examined file.
fn index_failure(err: &IndexError, texts: &[(&str, bool, String)]) -> Verdict {
    Verdict::fire(
        DUP_INDEX,
        Severity::Error,
        (texts.first().map_or("", |t| t.0), (0, 0)),
        err.to_string(),
        "index".to_owned(),
    )
}

/// The finding for one clone block, anchored at its first copy and naming every copy.
fn finding(c: &Clone, texts: &[(&str, bool, String)], files: &[Vec<Tok<'_>>]) -> Verdict {
    let place = |&(f, p): &Site| format!("{}:{}", texts[f].0, files[f][p].line);
    let mut listed: Vec<String> = c.sites.iter().take(LISTED_SITES).map(place).collect();
    if c.sites.len() > LISTED_SITES {
        listed.push(format!("and {} more", c.sites.len() - LISTED_SITES));
    }
    let (f, p) = c.sites[0];
    let range = (files[f][p].start, files[f][p + c.len - 1].end);
    Verdict::fire(
        c.rung.rule(),
        Severity::Error,
        (texts[f].0, range),
        format!(
            "{} copies of a {}-token block, {}: {}",
            c.sites.len(),
            c.len,
            c.rung.describe(),
            listed.join(", ")
        ),
        format!("{}:{:032x}", c.rung.label(), c.key),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Lex `srcs` as brace-style files.
    fn lex<'a>(srcs: &[&'a str]) -> Vec<Vec<Tok<'a>>> {
        srcs.iter().map(|s| tokens(s, false)).collect()
    }

    const BLOCK: &str = "a1 = b1 + c1 * d1;\na2 = b2 + c2 * d2;\na3 = b3 + c3 * d3;\n";

    // frob:tests crates/grimble-arch/src/dup.rs::find_clones
    #[test]
    fn exact_copies_merge_into_one_block() {
        let files = lex(&[BLOCK, BLOCK, BLOCK]);
        let found = find_clones(&files, 10, 3);
        assert_eq!(found.len(), 1, "{found:?}");
        assert_eq!(found[0].rung, Rung::Exact);
        assert_eq!(found[0].len, 24);
        assert_eq!(found[0].sites, [(0, 0), (1, 0), (2, 0)]);
    }

    // frob:tests crates/grimble-arch/src/dup.rs::find_clones
    #[test]
    fn renamed_copies_match_at_r2_and_a_changed_literal_at_r3() {
        let renamed = BLOCK.replace('1', "7").replace('2', "8");
        let files = lex(&[BLOCK, &renamed, BLOCK]);
        let found = find_clones(&files, 10, 3);
        assert!(
            found
                .iter()
                .all(|c| c.rung != Rung::Exact || c.sites.len() == 2)
        );
        assert!(
            found
                .iter()
                .any(|c| c.rung == Rung::Renamed && c.sites.len() == 3),
            "{found:?}"
        );
    }

    // frob:tests crates/grimble-arch/src/dup.rs::find_clones
    #[test]
    fn renamed_copies_match_at_r2_and_a_changed_literal_at_r3_part_2() {
        let shaped = "x = y + 1;\nx = y + 2;\nx = y + 3;\nx = y + 4;\n";
        let other = "p = q + 9;\np = q + 8;\np = q + 7;\np = q + 6;\n";
        let third = "m = n + 5;\nm = n + 5;\nm = n + 5;\nm = n + 5;\n";
        let files = lex(&[shaped, other, third]);
        let found = find_clones(&files, 10, 3);
        assert!(found.iter().any(|c| c.rung == Rung::Shape), "{found:?}");
    }

    // frob:tests crates/grimble-arch/src/dup.rs::find_clones
    #[test]
    fn a_block_is_not_reported_again_at_a_looser_rung() {
        let files = lex(&[BLOCK, BLOCK, BLOCK]);
        let found = find_clones(&files, 10, 3);
        assert!(found.iter().all(|c| c.rung == Rung::Exact), "{found:?}");
    }

    // frob:tests crates/grimble-arch/src/dup.rs::find_clones
    #[test]
    fn a_periodic_block_does_not_match_itself_and_two_copies_are_quiet() {
        let files = lex(&[BLOCK, BLOCK]);
        assert!(find_clones(&files, 10, 3).is_empty());
        let periodic = "a = b + c;\n".repeat(8);
        let files = lex(&[&periodic]);
        let found = find_clones(&files, 20, 3);
        for c in &found {
            for w in c.sites.windows(2) {
                assert!(w[0].1 + c.len <= w[1].1, "{c:?}");
            }
        }
    }

    // frob:tests crates/grimble-arch/src/dup.rs::find_clones
    #[test]
    fn degenerate_parameters_find_nothing() {
        let files = lex(&[BLOCK, BLOCK, BLOCK]);
        assert!(find_clones(&files, 0, 3).is_empty());
        assert!(find_clones(&files, 10, 1).is_empty());
        assert!(find_clones(&files, 500, 3).is_empty());
        assert!(find_clones(&[], 10, 3).is_empty());
    }
}
