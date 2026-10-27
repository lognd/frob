//! The shared lcov model: parse, normalise paths, merge and render, so every language reports through one format.

// frob:ticket 01M5XD3T31J311PC2KD9Q1N24Q

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::Path;

use gob_path::RelPath;

/// Hit and found counts of one file.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct FileCov {
    /// Highest hit count per line number.
    pub lines: BTreeMap<u64, u64>,
    /// Whether each (line, block, branch) was taken at least once.
    pub branches: BTreeMap<(u64, u64, u64), bool>,
}

/// Summed hit and found counts of a report.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct Totals {
    /// Lines executed at least once.
    pub lines_hit: u64,
    /// Lines instrumented.
    pub lines_found: u64,
    /// Branches taken at least once.
    pub branches_hit: u64,
    /// Branches instrumented.
    pub branches_found: u64,
}

/// A normalised lcov report: coverage per repository-relative, forward-slash file path.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct Lcov {
    /// Per-file coverage, keyed by the path the COV004 globs match.
    pub files: BTreeMap<String, FileCov>,
}

/// The path `sf` as the repo-relative, forward-slash path the globs match.
#[must_use]
pub fn normalize(sf: &str, root: &Path) -> String {
    let flat = sf.replace('\\', "/");
    let path = Path::new(&flat);
    let rebased = if path.is_absolute() {
        RelPath::from_host(root, path)
            .ok()
            .map(|r| r.as_str().to_owned())
    } else {
        None
    };
    let rel = rebased.unwrap_or(flat);
    rel.strip_prefix('.')
        .and_then(|r| r.strip_prefix('/'))
        .unwrap_or(&rel)
        .to_owned()
}

/// Parse the `DA:<line>,<hits>[,<checksum>]` payload into `(line, hits)`.
fn parse_da(payload: &str) -> Option<(u64, u64)> {
    let mut it = payload.split(',');
    let line = it.next()?.trim().parse().ok()?;
    let hits = it.next()?.trim().parse().ok()?;
    Some((line, hits))
}

/// Parse the `BRDA:<line>,<block>,<branch>,<taken>` payload into its key and whether it was taken.
fn parse_brda(payload: &str) -> Option<((u64, u64, u64), bool)> {
    let f: Vec<&str> = payload.split(',').map(str::trim).collect();
    let [line, block, branch, taken] = f.as_slice() else {
        return None;
    };
    let key = (
        line.parse().ok()?,
        block.parse().ok()?,
        branch.parse().ok()?,
    );
    Some((key, taken.parse::<u64>().is_ok_and(|t| t > 0)))
}

impl Lcov {
    /// Parse lcov `text`, rebasing every `SF:` onto `root`; unrecognised or malformed records are skipped.
    #[must_use]
    pub fn parse(text: &str, root: &Path) -> Self {
        let mut out = Self::default();
        let mut current: Option<String> = None;
        for raw in text.lines() {
            let line = raw.trim();
            if let Some(sf) = line.strip_prefix("SF:") {
                current = Some(normalize(sf, root));
                continue;
            }
            if line == "end_of_record" {
                current = None;
                continue;
            }
            let Some(file) = current.as_ref() else {
                continue;
            };
            if let Some(da) = line.strip_prefix("DA:") {
                if let Some((n, hits)) = parse_da(da) {
                    let slot = out
                        .files
                        .entry(file.clone())
                        .or_default()
                        .lines
                        .entry(n)
                        .or_default();
                    *slot = (*slot).max(hits);
                } else {
                    tracing::debug!(record = line, "skipping malformed DA record");
                }
            } else if let Some(br) = line.strip_prefix("BRDA:") {
                if let Some((key, hit)) = parse_brda(br) {
                    *out.files
                        .entry(file.clone())
                        .or_default()
                        .branches
                        .entry(key)
                        .or_default() |= hit;
                } else {
                    tracing::debug!(record = line, "skipping malformed BRDA record");
                }
            }
        }
        out
    }

    /// Fold `other` in: the highest line hit count and any taken branch win, so merging is idempotent.
    pub fn merge(&mut self, other: &Self) {
        for (path, cov) in &other.files {
            let mine = self.files.entry(path.clone()).or_default();
            for (n, hits) in &cov.lines {
                let slot = mine.lines.entry(*n).or_default();
                *slot = (*slot).max(*hits);
            }
            for (key, taken) in &cov.branches {
                *mine.branches.entry(*key).or_default() |= *taken;
            }
        }
        tracing::debug!(files = self.files.len(), "lcov reports merged");
    }

    /// The report as deterministic lcov text: files and records in sorted order with `LF/LH/BRF/BRH` totals.
    #[must_use]
    pub fn render(&self) -> String {
        let mut out = String::new();
        for (path, cov) in &self.files {
            let _ = writeln!(out, "SF:{path}");
            for (n, hits) in &cov.lines {
                let _ = writeln!(out, "DA:{n},{hits}");
            }
            let _ = writeln!(out, "LF:{}", cov.lines.len());
            let _ = writeln!(out, "LH:{}", cov.lines.values().filter(|h| **h > 0).count());
            for ((line, block, branch), taken) in &cov.branches {
                let _ = writeln!(out, "BRDA:{line},{block},{branch},{}", u8::from(*taken));
            }
            let _ = writeln!(out, "BRF:{}", cov.branches.len());
            let _ = writeln!(out, "BRH:{}", cov.branches.values().filter(|t| **t).count());
            out.push_str("end_of_record\n");
        }
        out
    }

    /// Summed line and branch counts over every file.
    #[must_use]
    pub fn totals(&self) -> Totals {
        let mut t = Totals::default();
        for cov in self.files.values() {
            t.lines_found += cov.lines.len() as u64;
            t.lines_hit += cov.lines.values().filter(|h| **h > 0).count() as u64;
            t.branches_found += cov.branches.len() as u64;
            t.branches_hit += cov.branches.values().filter(|b| **b).count() as u64;
        }
        t
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const ROOT: &str = "/repo";

    fn parse(text: &str) -> Lcov {
        Lcov::parse(text, Path::new(ROOT))
    }

    // frob:tests Lcov.parse
    #[test]
    fn normalises_absolute_backslash_and_dot_paths() {
        let l = parse(
            "SF:/repo/src/a.rs\nDA:1,1\nend_of_record\nSF:.\\src\\b.rs\nDA:2,0\nend_of_record\nSF:./src/c.rs\nDA:3,1\nend_of_record\n",
        );
        let keys: Vec<&str> = l.files.keys().map(String::as_str).collect();
        assert_eq!(keys, ["src/a.rs", "src/b.rs", "src/c.rs"]);
    }

    // frob:tests Lcov.merge
    #[test]
    fn merge_takes_highest_hits_and_any_taken_branch_and_is_idempotent() {
        let mut a = parse("SF:x.rs\nDA:1,0\nDA:2,5\nBRDA:1,0,0,0\nend_of_record\n");
        let b = parse("SF:x.rs\nDA:1,3\nDA:2,1\nBRDA:1,0,0,2\nSF:y.rs\nDA:9,1\nend_of_record\n");
        a.merge(&b);
        let once = a.clone();
        a.merge(&b);
        assert_eq!(a, once);
        assert_eq!(a.files["x.rs"].lines[&1], 3);
        assert_eq!(a.files["x.rs"].lines[&2], 5);
        assert!(a.files["x.rs"].branches[&(1, 0, 0)]);
        assert!(a.files.contains_key("y.rs"));
    }

    // frob:tests Lcov.render
    #[test]
    fn render_round_trips_and_is_sorted() {
        let l = parse("SF:b.rs\nDA:2,1\nSF:a.rs\nDA:1,0\nBRDA:1,0,0,1\nend_of_record\n");
        let text = l.render();
        assert!(text.find("SF:a.rs").unwrap() < text.find("SF:b.rs").unwrap());
        assert_eq!(parse(&text), l);
        assert!(text.contains("LF:1\nLH:0\n"));
    }

    // frob:tests Lcov.totals
    #[test]
    fn totals_count_hit_and_found() {
        let l = parse("SF:a.rs\nDA:1,1\nDA:2,0\nBRDA:1,0,0,1\nBRDA:1,0,1,0\nend_of_record\n");
        assert_eq!(
            l.totals(),
            Totals {
                lines_hit: 1,
                lines_found: 2,
                branches_hit: 1,
                branches_found: 2
            }
        );
    }

    #[test]
    fn malformed_records_are_skipped() {
        let l = parse("SF:a.rs\nDA:x,1\nBRDA:1,2\nDA:4,1\nend_of_record\n");
        assert_eq!(l.files["a.rs"].lines.len(), 1);
    }
}
