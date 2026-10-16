//! A remedy as data: product, verb path, flags and placeholder arguments, rendered to text on demand.
// frob:ticket 01M4118NGH127F6DGVGS4GVE49

use schemars::JsonSchema;
use serde::Serialize;

/// A runnable command a refusal points at, kept structured so tests and agents can check it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct RemedyCommand {
    /// Binary that runs the command, such as `frob`.
    pub product: String,
    /// Verb path words, such as `["lease", "widen"]`.
    pub verb: Vec<String>,
    /// Long flag names without the leading `--`, each with an optional value.
    pub flags: Vec<RemedyFlag>,
    /// Positional arguments or `<placeholders>`, in order.
    pub args: Vec<String>,
}

/// One long flag of a [`RemedyCommand`] and its value, when it takes one.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, JsonSchema)]
pub struct RemedyFlag {
    /// Flag name without the leading `--`.
    pub name: String,
    /// Value or `<placeholder>`; `None` for a switch.
    pub value: Option<String>,
}

impl RemedyCommand {
    /// Start a command for `product` at the space-separated verb path `verb`.
    pub fn new(product: &str, verb: &str) -> Self {
        Self {
            product: product.to_owned(),
            verb: verb.split_whitespace().map(str::to_owned).collect(),
            flags: Vec::new(),
            args: Vec::new(),
        }
    }

    /// Append a positional argument or placeholder.
    #[must_use]
    pub fn arg(mut self, arg: impl Into<String>) -> Self {
        self.args.push(arg.into());
        self
    }

    /// Append a switch flag such as `--force`.
    #[must_use]
    pub fn switch(mut self, name: &str) -> Self {
        self.flags.push(RemedyFlag {
            name: name.to_owned(),
            value: None,
        });
        self
    }

    /// Append a flag with a value such as `--reason <why>`.
    #[must_use]
    pub fn flag(mut self, name: &str, value: impl Into<String>) -> Self {
        self.flags.push(RemedyFlag {
            name: name.to_owned(),
            value: Some(value.into()),
        });
        self
    }

    /// The verb path joined by single spaces, the key of the CLI registry.
    pub fn verb_path(&self) -> String {
        self.verb.join(" ")
    }

    /// The command as the text a person would paste: `product verb args --flag value`.
    pub fn render(&self) -> String {
        let mut out = self.product.clone();
        for w in self.verb.iter().chain(&self.args) {
            out.push(' ');
            out.push_str(w);
        }
        for f in &self.flags {
            out.push_str(" --");
            out.push_str(&f.name);
            if let Some(v) = &f.value {
                out.push(' ');
                out.push_str(v);
            }
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Given a command with args, a switch and a valued flag, when rendered, then it reads as one shell line.
    #[test]
    fn renders_as_a_shell_line() {
        let c = RemedyCommand::new("frob", "requeue")
            .arg("<t>")
            .flag("reason", "<why>")
            .switch("force");
        assert_eq!(c.render(), "frob requeue <t> --reason <why> --force");
        assert_eq!(c.verb_path(), "requeue");
    }
}
