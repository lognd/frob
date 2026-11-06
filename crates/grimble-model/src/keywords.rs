//! The keyword table (grmb-spec 2.6): the single source for the parser and the editor grammar.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3

/// Reserved words, in every position.
pub const KEYWORDS: &[&str] = &[
    "accept",
    "age",
    "allocates",
    "alias",
    "as",
    "assumed",
    "at",
    "attests",
    "attr",
    "blocked_by",
    "bound",
    "boundary",
    "claim",
    "clearance",
    "condition",
    "consumer",
    "contract",
    "declassify",
    "decides",
    "defer",
    "digest",
    "endorse",
    "evidence",
    "excuse",
    "excuses",
    "extend",
    "fanout",
    "flow",
    "for",
    "growth",
    "hotfix",
    "include",
    "kind",
    "label",
    "latency",
    "level",
    "manual",
    "may",
    "module",
    "namespace",
    "node",
    "never",
    "noflow",
    "of",
    "on",
    "owns",
    "pack",
    "part",
    "producer",
    "proof",
    "provides",
    "rate",
    "reach",
    "ref",
    "refines",
    "renamed_from",
    "runnable",
    "satisfies",
    "shape",
    "size",
    "supersedes",
    "surface",
    "template",
    "tests",
    "transport",
    "utilization",
    "verifies",
    "version",
    "versioning",
    "via",
    "vmodel",
    "when",
];

/// True when `word` is reserved.
pub fn is_keyword(word: &str) -> bool {
    KEYWORDS.contains(&word)
}

/// Item heads of the planning layer, recognized at item position only (grmb-spec 2.6; `use` is the file include).
pub const PLANNING_ITEM_WORDS: &[&str] = &[
    "system", "actor", "goal", "step", "scenario", "impl", "page", "use",
];

/// Body words of the planning layer, recognized inside planning items only (grmb-spec 2.6).
pub const PLANNING_BODY_WORDS: &[&str] = &[
    "_",
    "ambient",
    "chain",
    "closed",
    "else",
    "end",
    "entry",
    "err",
    "escalate",
    "exclusive",
    "fails",
    "from",
    "handle",
    "idempotent",
    "in",
    "max",
    "non_goal",
    "ok",
    "one_of",
    "open",
    "page",
    "realizes",
    "requires",
    "restart",
    "retry",
    "sorry",
    "system",
    "terminate",
    "unknown",
    "verified_by",
    "with",
    "within",
];

/// True when `word` is a contextual planning word (item head or body word); plain identifier elsewhere.
pub fn is_planning_word(word: &str) -> bool {
    PLANNING_ITEM_WORDS.contains(&word) || PLANNING_BODY_WORDS.contains(&word)
}

/// True when `word` is in any class of the 2.6 table; a pack kind equal to one is refused (MDL031).
pub fn is_table_word(word: &str) -> bool {
    is_keyword(word) || is_planning_word(word)
}
