//! The non-kind words of the catalog: verbs, flags, built-in functions and fixed side relations
//! (grl-spec.md section 6).

// frob:ticket 01M3ZX7DMYNTWB3AP04CDMAECH
use super::FieldType;

/// An edge verb of the catalog.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Verb {
    /// The verb as written; multi-word verbs have single spaces.
    pub word: &'static str,
    /// The universal queries that answer it.
    pub query: &'static str,
    /// What the verb relates, in one line.
    pub summary: &'static str,
}

/// The edge verbs, sorted by word.
pub const VERBS: &[Verb] = &[
    Verb {
        word: "calls",
        query: "Q28",
        summary: "a call edge; Must, May or Unknown",
    },
    Verb {
        word: "extends",
        query: "Q28",
        summary: "a type extends or implements another",
    },
    Verb {
        word: "imports",
        query: "Q29",
        summary: "an import edge; Must, May or Unknown",
    },
    Verb {
        word: "instantiates",
        query: "Q28",
        summary: "a construction of a type",
    },
    Verb {
        word: "owned by",
        query: "Q32, Q36",
        summary: "the grimble node owning a unit",
    },
    Verb {
        word: "peer of",
        query: "Q27",
        summary: "same parent unit",
    },
    Verb {
        word: "references",
        query: "Q28",
        summary: "a reference to a declaration",
    },
    Verb {
        word: "resolves to",
        query: "Q20, Q21",
        summary: "One, Candidates or Unknown",
    },
    Verb {
        word: "tests",
        query: "Q35 plus frob:tests",
        summary: "a test linked to a callable",
    },
];

/// A word that follows `is`: a boolean field or a check.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Flag {
    /// The flag word.
    pub word: &'static str,
    /// The universal query that answers it, empty for a pure check.
    pub query: &'static str,
    /// Whether the answer can be Unknown.
    pub may_be_unknown: bool,
}

/// The flags, sorted by word.
pub const FLAGS: &[Flag] = &[
    Flag {
        word: "async",
        query: "Q07",
        may_be_unknown: false,
    },
    Flag {
        word: "exported",
        query: "Q33",
        may_be_unknown: true,
    },
    Flag {
        word: "public",
        query: "Q07",
        may_be_unknown: true,
    },
    Flag {
        word: "relative",
        query: "Q11",
        may_be_unknown: false,
    },
    Flag {
        word: "valid_glob",
        query: "",
        may_be_unknown: false,
    },
];

/// A built-in function with its result type.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Function {
    /// The function name.
    pub name: &'static str,
    /// The call as written, for the catalog page.
    pub signature: &'static str,
    /// What it returns (`Any` for a vocabulary).
    pub returns: FieldType,
}

/// The built-in functions, sorted by name.
pub const FUNCTIONS: &[Function] = &[
    Function {
        name: "glob",
        signature: "glob(s)",
        returns: FieldType::Glob,
    },
    Function {
        name: "resolve",
        signature: "resolve(path, from)",
        returns: FieldType::Str,
    },
    Function {
        name: "slug",
        signature: "slug(s)",
        returns: FieldType::Str,
    },
    Function {
        name: "valid_glob",
        signature: "valid_glob(s)",
        returns: FieldType::Bool,
    },
    Function {
        name: "vocab",
        signature: "vocab(NAME)",
        returns: FieldType::Any,
    },
];

impl Function {
    /// The result type's name on the catalog page.
    pub const fn ty_name(&self) -> &'static str {
        self.returns.name()
    }
}

/// One column of a side relation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Column {
    /// The column name.
    pub name: String,
    /// Its type.
    pub ty: FieldType,
}

/// A fixed side relation: rows supplied by a tool outside the code model.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SideRelation {
    /// The dotted name, such as `diff.changed`.
    pub name: &'static str,
    /// What the rule reads (the `reads` root it must declare).
    pub reads: &'static str,
    /// The component that supplies the rows.
    pub source: &'static str,
    /// The columns, by name and type.
    pub columns: &'static [(&'static str, FieldType)],
}

impl SideRelation {
    /// The columns as owned values.
    pub fn typed_columns(&self) -> Vec<Column> {
        self.columns
            .iter()
            .map(|(name, ty)| Column {
                name: (*name).to_owned(),
                ty: *ty,
            })
            .collect()
    }
}

/// The roots of side-relation paths; `config` is typed from the config schema instead.
pub const SIDE_ROOTS: &[&str] = &["config", "diff", "lease", "model"];

/// The fixed side relations, sorted by name.
pub const SIDE_RELATIONS: &[SideRelation] = &[
    SideRelation {
        name: "diff.added",
        reads: "diff",
        source: "gob-git",
        columns: &[
            ("path", FieldType::Str),
            ("line", FieldType::Int),
            ("text", FieldType::Str),
        ],
    },
    SideRelation {
        name: "diff.changed",
        reads: "diff",
        source: "gob-git",
        columns: &[("path", FieldType::Str), ("status", FieldType::Str)],
    },
    SideRelation {
        name: "lease.globs",
        reads: "lease",
        source: "frob-lease",
        columns: &[("glob", FieldType::Str)],
    },
    SideRelation {
        name: "lease.ticket",
        reads: "lease",
        source: "frob-lease",
        columns: &[("id", FieldType::Str), ("handle", FieldType::Str)],
    },
    SideRelation {
        name: "model.nodes",
        reads: "model",
        source: "grimble-model",
        columns: &[
            ("name", FieldType::Str),
            ("kind", FieldType::Str),
            ("path", FieldType::Str),
        ],
    },
    SideRelation {
        name: "model.selectors",
        reads: "model",
        source: "grimble-model",
        columns: &[("node", FieldType::Str), ("selector", FieldType::Str)],
    },
];

/// The fixed side relation called `name` (`diff.changed`).
pub fn side_relation(name: &str) -> Option<&'static SideRelation> {
    SIDE_RELATIONS.iter().find(|s| s.name == name)
}

/// The verb called `word`.
pub fn verb(word: &str) -> Option<&'static Verb> {
    VERBS.iter().find(|v| v.word == word)
}

/// The built-in function called `name`.
pub fn function(name: &str) -> Option<&'static Function> {
    FUNCTIONS.iter().find(|f| f.name == name)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tables_are_sorted_and_roots_cover_relations() {
        assert!(VERBS.windows(2).all(|w| w[0].word < w[1].word));
        assert!(FLAGS.windows(2).all(|w| w[0].word < w[1].word));
        assert!(FUNCTIONS.windows(2).all(|w| w[0].name < w[1].name));
        assert!(SIDE_RELATIONS.windows(2).all(|w| w[0].name < w[1].name));
        for s in SIDE_RELATIONS {
            assert!(SIDE_ROOTS.contains(&s.reads), "{}", s.name);
            assert!(s.name.starts_with(s.reads), "{}", s.name);
        }
    }

    #[test]
    fn lookups_find_words() {
        assert!(verb("owned by").is_some() && verb("owns").is_none());
        assert_eq!(function("slug").unwrap().returns, FieldType::Str);
        assert_eq!(side_relation("diff.changed").unwrap().reads, "diff");
    }
}
