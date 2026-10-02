//! Glob strings: `PATH [ "::" QUALNAME ]` (grmb-spec 6.2).

// frob:ticket 01M3Z713RETBN30XBC6CK11FBF

use crate::specificity::Specificity;

/// Why a glob string was rejected, with the byte offset inside the string content.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GlobError {
    /// Byte offset into the glob text where the problem starts.
    pub offset: usize,
    /// Human-readable reason.
    pub message: String,
}

fn err<T>(offset: usize, message: &str) -> Result<T, GlobError> {
    Err(GlobError {
        offset,
        message: message.to_owned(),
    })
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum Tok {
    Lit(char),
    One,
    Star,
    Class {
        negated: bool,
        items: Vec<(char, char)>,
    },
}

impl Tok {
    fn accepts(&self, c: char) -> bool {
        match self {
            Self::Lit(l) => *l == c,
            Self::One => true,
            Self::Star => false,
            Self::Class { negated, items } => {
                items.iter().any(|&(lo, hi)| lo <= c && c <= hi) != *negated
            }
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum Seg {
    AnyDepth,
    Pat(Vec<Tok>),
}

fn seg_match(toks: &[Tok], text: &[char]) -> bool {
    match toks.split_first() {
        None => text.is_empty(),
        Some((Tok::Star, rest)) => (0..=text.len()).any(|k| seg_match(rest, &text[k..])),
        Some((t, rest)) => {
            text.first().is_some_and(|&c| t.accepts(c)) && seg_match(rest, &text[1..])
        }
    }
}

fn segs_match(pat: &[Seg], segs: &[&str]) -> bool {
    match pat.split_first() {
        None => segs.is_empty(),
        Some((Seg::AnyDepth, rest)) => (0..=segs.len()).any(|k| segs_match(rest, &segs[k..])),
        Some((Seg::Pat(p), rest)) => segs.split_first().is_some_and(|(s, tail)| {
            let chars: Vec<char> = s.chars().collect();
            seg_match(p, &chars) && segs_match(rest, tail)
        }),
    }
}

/// Compiles one segment; `path_mode` enables `?` and `[...]` (a qualname has only `*`).
fn compile_seg(s: &str, off: usize, path_mode: bool) -> Result<Vec<Tok>, GlobError> {
    let chars: Vec<(usize, char)> = s.char_indices().collect();
    let mut toks = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let (pos, c) = chars[i];
        match c {
            '*' => {
                if !matches!(toks.last(), Some(Tok::Star)) {
                    toks.push(Tok::Star);
                }
            }
            '?' if path_mode => toks.push(Tok::One),
            '[' if path_mode => {
                let mut j = i + 1;
                let negated = matches!(chars.get(j), Some((_, '!' | '^')));
                if negated {
                    j += 1;
                }
                let mut items = Vec::new();
                loop {
                    let Some(&(_, c1)) = chars.get(j) else {
                        return err(off + pos, "unclosed character class");
                    };
                    if c1 == ']' && !items.is_empty() {
                        break;
                    }
                    let is_range = matches!(chars.get(j + 1), Some((_, '-')))
                        && matches!(chars.get(j + 2), Some((_, c3)) if *c3 != ']');
                    if is_range {
                        let hi = chars[j + 2].1;
                        if hi < c1 {
                            return err(off + chars[j].0, "reversed range in character class");
                        }
                        items.push((c1, hi));
                        j += 3;
                    } else {
                        items.push((c1, c1));
                        j += 1;
                    }
                }
                i = j;
                toks.push(Tok::Class { negated, items });
            }
            c => toks.push(Tok::Lit(c)),
        }
        i += 1;
    }
    Ok(toks)
}

/// Checks `{}` balance; returns the error offset when unbalanced.
fn check_braces(s: &str) -> Result<(), GlobError> {
    let mut open: Vec<usize> = Vec::new();
    for (i, c) in s.char_indices() {
        match c {
            '{' => open.push(i),
            '}' if open.pop().is_none() => return err(i, "unmatched `}`"),
            _ => {}
        }
    }
    match open.first() {
        Some(&i) => err(i, "unclosed `{`"),
        None => Ok(()),
    }
}

/// Expands `{a,b}` alternation (nesting allowed); the input is brace-balanced.
fn expand(s: &str) -> Vec<String> {
    let Some(a) = s.find('{') else {
        return vec![s.to_owned()];
    };
    let mut depth = 0usize;
    let mut close = a;
    let mut cuts = vec![a];
    for (i, c) in s[a..].char_indices() {
        match c {
            '{' => depth += 1,
            '}' => {
                depth -= 1;
                if depth == 0 {
                    close = a + i;
                    break;
                }
            }
            ',' if depth == 1 => cuts.push(a + i),
            _ => {}
        }
    }
    cuts.push(close);
    let (prefix, suffix) = (&s[..a], &s[close + 1..]);
    let mut out = Vec::new();
    for w in cuts.windows(2) {
        out.extend(expand(&format!("{prefix}{}{suffix}", &s[w[0] + 1..w[1]])));
    }
    out
}

/// Splits on `/` outside braces.
fn raw_segments(s: &str) -> Vec<&str> {
    let (mut depth, mut start, mut out) = (0i32, 0usize, Vec::new());
    for (i, c) in s.char_indices() {
        match c {
            '{' => depth += 1,
            '}' => depth -= 1,
            '/' if depth == 0 => {
                out.push(&s[start..i]);
                start = i + 1;
            }
            _ => {}
        }
    }
    out.push(&s[start..]);
    out
}

/// Splits a qualname on `.` outside brackets, returning `(offset, text)` pairs.
fn qual_segments(s: &str) -> Vec<(usize, &str)> {
    let (mut depth, mut start, mut out) = (0i32, 0usize, Vec::new());
    for (i, c) in s.char_indices() {
        match c {
            '[' => depth += 1,
            ']' => depth -= 1,
            '.' if depth == 0 => {
                out.push((start, &s[start..i]));
                start = i + 1;
            }
            _ => {}
        }
    }
    out.push((start, &s[start..]));
    out
}

fn is_wild(seg: &str) -> bool {
    seg.contains(['*', '?', '[', '{'])
}

/// A parsed glob string: a PATH pattern and an optional QUALNAME pattern.
///
/// ```
/// use gob_walk::Glob;
/// let g = Glob::parse("crates/*/src/**::Type.*").unwrap();
/// assert!(g.matches_path("crates/a/src/x/y.rs"));
/// assert!(g.matches_qual(&["Type", "run"]));
/// assert!(!g.matches_qual(&["Type"]));
/// ```
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Glob {
    path: String,
    qual: Option<String>,
    alts: Vec<Vec<Seg>>,
    qual_pat: Vec<Seg>,
    spec: Specificity,
    literal: bool,
}

impl Glob {
    /// Parses glob text (already unescaped); errors carry offsets into `text`.
    ///
    /// # Errors
    ///
    /// Returns a [`GlobError`] for an empty PATH, a leading `/`, a `..` segment, an empty
    /// segment, unbalanced braces or classes, or an empty QUALNAME (MDL009).
    pub fn parse(text: &str) -> Result<Self, GlobError> {
        let (path, qual, qual_off) = match text.find("::") {
            Some(i) => (&text[..i], Some(&text[i + 2..]), i + 2),
            None => (text, None, 0),
        };
        if path.is_empty() {
            return err(0, "empty PATH");
        }
        if path.starts_with('/') {
            return err(0, "PATH must be repository-relative (no leading `/`)");
        }
        check_braces(path)?;
        let dir = path.ends_with('/');
        let body = path.strip_suffix('/').unwrap_or(path);
        let raw = raw_segments(body);
        let mut off = 0;
        for seg in &raw {
            if seg.is_empty() {
                return err(off, "empty path segment");
            }
            if *seg == ".." {
                return err(off, "`..` is not allowed in a PATH");
            }
            compile_seg(seg, off, true)?;
            off += seg.len() + 1;
        }
        let mut alts = Vec::new();
        for alt in expand(body) {
            let mut segs = Vec::new();
            for s in alt.split('/') {
                segs.push(if s == "**" {
                    Seg::AnyDepth
                } else {
                    Seg::Pat(compile_seg(s, 0, true)?)
                });
            }
            if dir {
                segs.push(Seg::AnyDepth);
            }
            alts.push(segs);
        }
        let mut qual_pat = Vec::new();
        let mut literal_qual = 0;
        if let Some(q) = qual {
            if q.is_empty() {
                return err(qual_off, "empty QUALNAME after `::`");
            }
            for (o, seg) in qual_segments(q) {
                if seg.is_empty() {
                    return err(qual_off + o, "empty qualname segment");
                }
                if seg == "**" {
                    qual_pat.push(Seg::AnyDepth);
                } else {
                    qual_pat.push(Seg::Pat(compile_seg(seg, 0, false)?));
                    if !seg.contains('*') {
                        literal_qual += 1;
                    }
                }
            }
        }
        let double = i32::try_from(raw.iter().filter(|s| **s == "**").count() + usize::from(dir))
            .unwrap_or(i32::MAX);
        let wild = i32::try_from(raw.iter().filter(|s| **s != "**" && is_wild(s)).count())
            .unwrap_or(i32::MAX);
        let literal_segments =
            i32::try_from(raw.iter().filter(|s| !is_wild(s)).count()).unwrap_or(i32::MAX);
        let path_wild = dir || raw.iter().any(|s| is_wild(s));
        let level = if qual.is_some() {
            3
        } else if path_wild {
            1
        } else {
            2
        };
        let literal = !path_wild && qual.is_none_or(|q| !q.contains('*'));
        Ok(Self {
            path: path.to_owned(),
            qual: qual.map(str::to_owned),
            alts,
            qual_pat,
            spec: Specificity::new([level, literal_segments, -double, -wild, literal_qual, 0]),
            literal,
        })
    }

    /// The PATH pattern text.
    pub fn path(&self) -> &str {
        &self.path
    }

    /// The QUALNAME pattern text, if the glob has `::`.
    pub fn qual(&self) -> Option<&str> {
        self.qual.as_deref()
    }

    /// The QUALNAME segments as written (for a literal glob these are the exact segments).
    pub fn qual_segments(&self) -> Vec<&str> {
        self.qual
            .as_deref()
            .map(|q| qual_segments(q).into_iter().map(|(_, s)| s).collect())
            .unwrap_or_default()
    }

    /// The full glob text, `PATH` or `PATH::QUALNAME`.
    pub fn text(&self) -> String {
        match &self.qual {
            Some(q) => format!("{}::{q}", self.path),
            None => self.path.clone(),
        }
    }

    /// Whether the glob has no wildcard anywhere (a LITERAL selector candidate).
    pub fn is_literal(&self) -> bool {
        self.literal
    }

    /// The specificity of this glob alone (predicate count zero).
    pub fn specificity(&self) -> Specificity {
        self.spec
    }

    /// Whether the PATH pattern matches the repository-relative `path`.
    pub fn matches_path(&self, path: &str) -> bool {
        let segs: Vec<&str> = path.split('/').collect();
        self.alts.iter().any(|a| segs_match(a, &segs))
    }

    /// Whether the QUALNAME pattern matches the qualname segments `segs` (true without `::`).
    pub fn matches_qual<S: AsRef<str>>(&self, segs: &[S]) -> bool {
        if self.qual.is_none() {
            return true;
        }
        let segs: Vec<&str> = segs.iter().map(AsRef::as_ref).collect();
        segs_match(&self.qual_pat, &segs)
    }
}

/// Matches `text` against a single-segment wildcard pattern (`*`, `?`, `[...]`).
///
/// ```
/// assert!(gob_walk::wildcard_match("pu*", "public"));
/// assert!(!gob_walk::wildcard_match("pu?", "public"));
/// ```
pub fn wildcard_match(pattern: &str, text: &str) -> bool {
    compile_seg(pattern, 0, true).is_ok_and(|toks| {
        let chars: Vec<char> = text.chars().collect();
        seg_match(&toks, &chars)
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn path_cases() -> Vec<(&'static str, &'static str, bool)> {
        vec![
            ("crates/frob/**", "crates/frob/src/lib.rs", true),
            ("crates/frob/**", "crates/frob", true),
            ("crates/frob/**", "crates/frob-check/src/lib.rs", false),
            ("crates/frob/", "crates/frob/a/b.rs", true),
            ("crates/frob-*/**", "crates/frob-check/x.rs", true),
            ("crates/*/src/**", "crates/a/src/x/y.rs", true),
            ("crates/*/src/**", "crates/a/b/src/y.rs", false),
            ("src/*/mod.rs", "src/x/mod.rs", true),
            ("src/*/mod.rs", "src/x/y/mod.rs", false),
            ("**/mod.rs", "mod.rs", true),
            ("**/mod.rs", "a/b/mod.rs", true),
            ("a/**/b", "a/b", true),
            ("a/**/b", "a/x/y/b", true),
            ("file?.rs", "file1.rs", true),
            ("file?.rs", "file.rs", false),
            ("[a-c].rs", "b.rs", true),
            ("[a-c].rs", "d.rs", false),
            ("[!a].rs", "b.rs", true),
            ("{a,b}/x.rs", "b/x.rs", true),
            ("{a,b}/x.rs", "c/x.rs", false),
            ("src/{a,b/c}.rs", "src/b/c.rs", true),
            ("*.{rs,toml}", "Cargo.toml", true),
            ("src/lib.rs", "src/lib.rs", true),
            ("src/lib.rs", "src/lib.rs.bak", false),
        ]
    }

    #[test]
    fn path_matching_table() {
        for (pat, path, want) in path_cases() {
            let g = Glob::parse(pat).unwrap();
            assert_eq!(g.matches_path(path), want, "{pat} vs {path}");
        }
    }

    #[test]
    fn qual_matching_table() {
        let cases: [(&str, &[&str], bool); 7] = [
            ("a.rs::run", &["run"], true),
            ("a.rs::run", &["x", "run"], false),
            ("a.rs::*", &["x"], true),
            ("a.rs::*", &["x", "y"], false),
            ("a.rs::**", &[], true),
            ("a.rs::Type[Trait].method", &["Type[Trait]", "method"], true),
            ("a.rs::Type.get_*", &["Type", "get_one"], true),
        ];
        for (pat, segs, want) in cases {
            assert_eq!(Glob::parse(pat).unwrap().matches_qual(segs), want, "{pat}");
        }
    }

    #[test]
    fn specificity_follows_the_spec_examples() {
        let s = |t: &str| Glob::parse(t).unwrap().specificity().components();
        assert_eq!(s("src/**"), [1, 1, -1, 0, 0, 0]);
        assert_eq!(s("src/*/mod.rs"), [1, 2, 0, -1, 0, 0]);
        assert_eq!(s("crates/frob-check/src/lib.rs"), [2, 4, 0, 0, 0, 0]);
        assert_eq!(s("crates/frob-check/src/lib.rs::run"), [3, 4, 0, 0, 1, 0]);
        assert_eq!(s("crates/frob/"), [1, 2, -1, 0, 0, 0]);
        assert_eq!(s("a.rs::Type.*"), [3, 1, 0, 0, 1, 0]);
    }

    #[test]
    fn literal_detection() {
        assert!(Glob::parse("a/b.rs").unwrap().is_literal());
        assert!(Glob::parse("a/b.rs::T.run").unwrap().is_literal());
        assert!(!Glob::parse("a/*.rs").unwrap().is_literal());
        assert!(!Glob::parse("a/b.rs::T.*").unwrap().is_literal());
        assert!(!Glob::parse("a/").unwrap().is_literal());
    }

    #[test]
    fn rejections_carry_offsets() {
        let cases: [(&str, usize, &str); 8] = [
            ("", 0, "empty PATH"),
            ("::x", 0, "empty PATH"),
            ("/abs", 0, "leading"),
            ("a/../b", 2, ".."),
            ("a//b", 2, "empty path segment"),
            ("a/{b", 2, "unclosed `{`"),
            ("a.rs::", 6, "empty QUALNAME"),
            ("a.rs::x..y", 8, "empty qualname segment"),
        ];
        for (text, offset, needle) in cases {
            let e = Glob::parse(text).unwrap_err();
            assert_eq!(e.offset, offset, "{text}: {e:?}");
            assert!(e.message.contains(needle), "{text}: {e:?}");
        }
        assert!(Glob::parse("a[bc").is_err());
    }

    #[test]
    fn wildcard_text_matching() {
        assert!(wildcard_match("*", ""));
        assert!(wildcard_match("a*c", "abbbc"));
        assert!(!wildcard_match("a*c", "abbb"));
    }
}
