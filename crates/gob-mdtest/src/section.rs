// frob:ticket 01M48PC09SX0KFAM4B3V88AAXW
//! The heading tree of a suite: sections, inherited toml config and the test-or-group rule.
//!
//! A section is either a *test* (it directly holds case blocks) or a *group* (only its
//! descendants do), never both. A `toml` fence configures its section and every descendant,
//! a child overriding its parent key by key (the ty mdtest model).

use crate::parse::ParseError;

/// One heading of the suite (or the implicit root before the first heading).
#[derive(Debug)]
struct Section {
    /// Enclosing section; `None` only for the root.
    parent: Option<usize>,
    /// Heading level 1..=6; 0 for the root.
    level: usize,
    /// Heading text.
    title: String,
    /// Parsed toml config fences in document order, with the fence line.
    toml: Vec<toml::Table>,
    /// Fence line of the first case block directly under this section.
    first_head: Option<usize>,
}

/// The heading tree built while scanning a suite.
#[derive(Debug)]
pub(crate) struct Tree {
    /// All sections; index 0 is the root.
    sections: Vec<Section>,
    /// Open sections from the root down to the current one.
    stack: Vec<usize>,
}

/// What a section's toml chain resolves to for one case.
#[derive(Debug, Default, PartialEq, Eq)]
pub(crate) struct Settings {
    /// Config text handed to the runner, if any.
    pub config: Option<String>,
    /// `[mdtest] languages`: extra matrix cells the case fills.
    pub languages: Vec<String>,
}

/// Recursively merge `over` into `base`: tables merge, every other value is replaced.
pub(crate) fn merge(base: &mut toml::Table, over: toml::Table) {
    for (k, v) in over {
        match (base.get_mut(&k), v) {
            (Some(toml::Value::Table(b)), toml::Value::Table(o)) => merge(b, o),
            (_, v) => {
                base.insert(k, v);
            }
        }
    }
}

/// Validate a section's `[mdtest]` table and return its `languages`.
fn mdtest_languages(table: &toml::Table) -> Result<Vec<String>, String> {
    let Some(m) = table.get("mdtest") else {
        return Ok(Vec::new());
    };
    let m = m.as_table().ok_or("[mdtest] must be a table")?;
    if let Some(k) = m.keys().find(|k| *k != "languages") {
        return Err(format!("unknown [mdtest] key `{k}` (only `languages`)"));
    }
    let Some(list) = m.get("languages") else {
        return Ok(Vec::new());
    };
    let items = list
        .as_array()
        .ok_or("[mdtest] languages must be an array of strings")?;
    let mut out = Vec::new();
    for item in items {
        let s = item
            .as_str()
            .ok_or("[mdtest] languages must be an array of strings")?;
        if !crate::matrix::CELLS.contains(&s) {
            return Err(format!(
                "[mdtest] languages entry must be one of {}, got `{s}`",
                crate::matrix::CELLS.join(", ")
            ));
        }
        if !out.iter().any(|o| o == s) {
            out.push(s.to_owned());
        }
    }
    Ok(out)
}

impl Tree {
    /// A tree holding only the root section.
    pub(crate) fn new() -> Self {
        Self {
            sections: vec![Section {
                parent: None,
                level: 0,
                title: String::new(),
                toml: Vec::new(),
                first_head: None,
            }],
            stack: vec![0],
        }
    }

    /// Open a heading of `level`; it closes every open section of the same or deeper level.
    pub(crate) fn open(&mut self, level: usize, title: &str) {
        while self
            .stack
            .last()
            .is_some_and(|&s| self.sections[s].level >= level && s != 0)
        {
            self.stack.pop();
        }
        let parent = self.current();
        self.sections.push(Section {
            parent: Some(parent),
            level,
            title: title.trim().to_owned(),
            toml: Vec::new(),
            first_head: None,
        });
        self.stack.push(self.sections.len() - 1);
        tracing::debug!(level, title, "section opened");
    }

    /// The innermost open section.
    pub(crate) fn current(&self) -> usize {
        self.stack.last().copied().unwrap_or(0)
    }

    /// Heading titles from the outermost down to `id`, joined by ` / `.
    pub(crate) fn path(&self, id: usize) -> String {
        let mut parts = Vec::new();
        let mut at = Some(id);
        while let Some(i) = at {
            if i != 0 {
                parts.push(self.sections[i].title.as_str());
            }
            at = self.sections[i].parent;
        }
        parts.reverse();
        parts.join(" / ")
    }

    /// Note a case block at `line` directly under `id`.
    pub(crate) fn add_head(&mut self, id: usize, line: usize) {
        self.sections[id].first_head.get_or_insert(line);
    }

    /// Attach a toml config fence to `id`.
    ///
    /// # Errors
    ///
    /// A malformed `[mdtest]` table.
    pub(crate) fn add_toml(
        &mut self,
        id: usize,
        line: usize,
        table: toml::Table,
    ) -> Result<(), ParseError> {
        mdtest_languages(&table).map_err(|message| ParseError { line, message })?;
        self.sections[id].toml.push(table);
        tracing::debug!(line, section = %self.path(id), "toml config fence");
        Ok(())
    }

    /// Enforce "a section is a test or a group, never both".
    ///
    /// # Errors
    ///
    /// A section that holds case blocks and also has a descendant section holding case blocks.
    pub(crate) fn check_groups(&self) -> Result<(), ParseError> {
        for (id, s) in self.sections.iter().enumerate() {
            let (Some(line), true) = (s.first_head, id != 0) else {
                continue;
            };
            let mut up = s.parent;
            while let Some(p) = up.filter(|p| *p != 0) {
                if self.sections[p].first_head.is_some() {
                    return Err(ParseError {
                        line,
                        message: format!(
                            "section `{}` holds cases and is also a group: its descendant `{}` holds cases too",
                            self.path(p),
                            self.path(id)
                        ),
                    });
                }
                up = self.sections[p].parent;
            }
        }
        Ok(())
    }

    /// Resolve the config of `id` (root to leaf, child overriding parent) plus an inline `config=`.
    ///
    /// # Errors
    ///
    /// An inline config that is not valid toml while section config is in force.
    pub(crate) fn settings(&self, id: usize, inline: Option<&str>) -> Result<Settings, String> {
        let mut chain = Vec::new();
        let mut at = Some(id);
        while let Some(i) = at {
            chain.push(i);
            at = self.sections[i].parent;
        }
        chain.reverse();
        let tables: Vec<&toml::Table> = chain
            .iter()
            .flat_map(|&i| self.sections[i].toml.iter())
            .collect();
        if tables.is_empty() {
            return Ok(Settings {
                config: inline.map(str::to_owned),
                languages: Vec::new(),
            });
        }
        let mut merged = toml::Table::new();
        for t in tables {
            merge(&mut merged, t.clone());
        }
        let languages = mdtest_languages(&merged)?;
        merged.remove("mdtest");
        if let Some(raw) = inline {
            let over: toml::Table = raw
                .parse()
                .map_err(|e| format!("inline config= is not valid toml: {e}"))?;
            merge(&mut merged, over);
        }
        let config = if merged.is_empty() {
            None
        } else {
            Some(toml::to_string(&merged).map_err(|e| format!("cannot render config: {e}"))?)
        };
        Ok(Settings { config, languages })
    }
}
