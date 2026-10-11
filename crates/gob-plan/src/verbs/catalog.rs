//! `rule catalog`: print one catalog word, or list the words.

use crate::catalog::{FLAGS, KINDS, VERBS, kind};

/// One field of a kind.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct FieldInfo {
    /// The field name.
    pub name: String,
    /// Its type.
    pub ty: String,
    /// An example value as written in a rule.
    pub example: String,
    /// Whether the answer can be Unknown.
    pub may_be_unknown: bool,
}

/// What the catalog says about one word.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct Entry {
    /// `kind`, `verb` or `flag`.
    pub class: String,
    /// The word.
    pub word: String,
    /// The universal query that answers it.
    pub query: String,
    /// One-line meaning (empty for a flag).
    pub summary: String,
    /// Where a kind is answered (empty otherwise).
    pub languages: String,
    /// A kind's own fields.
    pub fields: Vec<FieldInfo>,
}

/// The answer to `rule catalog [WORD]`.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct CatalogResult {
    /// The entries: the one word asked for, or all of them.
    pub entries: Vec<Entry>,
    /// For an unknown word, the closest catalog word.
    pub did_you_mean: Option<String>,
}

fn entries() -> Vec<Entry> {
    let mut out = Vec::new();
    for k in KINDS {
        out.push(Entry {
            class: "kind".to_owned(),
            word: k.word.to_owned(),
            query: k.query.to_owned(),
            summary: k.summary.to_owned(),
            languages: k.answers.describe(),
            fields: k
                .fields
                .iter()
                .map(|f| FieldInfo {
                    name: f.name.to_owned(),
                    ty: format!("{:?}", f.ty).to_lowercase(),
                    example: f.example.to_owned(),
                    may_be_unknown: f.may_be_unknown,
                })
                .collect(),
        });
    }
    for v in VERBS {
        out.push(Entry {
            class: "verb".to_owned(),
            word: v.word.to_owned(),
            query: v.query.to_owned(),
            summary: v.summary.to_owned(),
            languages: String::new(),
            fields: Vec::new(),
        });
    }
    for f in FLAGS {
        out.push(Entry {
            class: "flag".to_owned(),
            word: f.word.to_owned(),
            query: f.query.to_owned(),
            summary: String::new(),
            languages: String::new(),
            fields: Vec::new(),
        });
    }
    out
}

/// Damerau distance (adjacent swaps count one) between two short words.
fn distance(a: &str, b: &str) -> usize {
    let (a, b): (Vec<char>, Vec<char>) = (a.chars().collect(), b.chars().collect());
    let mut d = vec![vec![0usize; b.len() + 1]; a.len() + 1];
    for (i, row) in d.iter_mut().enumerate() {
        row[0] = i;
    }
    for (j, cell) in d[0].iter_mut().enumerate() {
        *cell = j;
    }
    for i in 1..=a.len() {
        for j in 1..=b.len() {
            let cost = usize::from(a[i - 1] != b[j - 1]);
            d[i][j] = (d[i - 1][j] + 1)
                .min(d[i][j - 1] + 1)
                .min(d[i - 1][j - 1] + cost);
            if i > 1 && j > 1 && a[i - 1] == b[j - 2] && a[i - 2] == b[j - 1] {
                d[i][j] = d[i][j].min(d[i - 2][j - 2] + 1);
            }
        }
    }
    d[a.len()][b.len()]
}

/// Look up `word`, or list every word when it is `None`; an unknown word gets a suggestion.
pub fn lookup(word: Option<&str>) -> CatalogResult {
    let all = entries();
    let Some(w) = word else {
        return CatalogResult {
            entries: all,
            did_you_mean: None,
        };
    };
    let hits: Vec<Entry> = all.iter().filter(|e| e.word == w).cloned().collect();
    if !hits.is_empty() || kind(w).is_some() {
        return CatalogResult {
            entries: hits,
            did_you_mean: None,
        };
    }
    let limit = (w.len() / 3).max(1);
    let near = (w.len() >= 3)
        .then(|| {
            all.iter()
                .map(|e| (distance(w, &e.word), &e.word))
                .filter(|(d, _)| *d <= limit)
                .min()
        })
        .flatten()
        .map(|(_, c)| c.clone());
    CatalogResult {
        entries: Vec::new(),
        did_you_mean: near,
    }
}
