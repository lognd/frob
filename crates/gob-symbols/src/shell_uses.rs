//! Command-word resolution for shell scripts: `curl`, `wget`, `nc`, `rm`, `cat`, `env`, `eval`,
//! `bash -c`, resolved to the command a script actually runs.
//!
//! A path is `sh.` plus the command name (`sh.rm`). Resolution is over tree-sitter nodes:
//!
//! - an alias (`alias r=rm`) is followed to its target word, so `r -rf x` is `sh.rm`;
//! - a function the file defines (`rm() { ...; }`) shadows the command of that name, so a call to
//!   it names nothing;
//! - an absolute path in a standard bin directory (`/bin/rm`) is the command of that basename;
//! - the wrappers `env`, `command`, `exec`, `nohup`, `sudo`, `xargs`, `time`, `builtin` are
//!   reported and the command they run is resolved too;
//! - an expansion in command position (`$c`, `$c"m"`, `$(f)`) is emitted computed: the command is
//!   not known without running the script, so the consumer reports it Unresolved;
//! - `eval` is the command `sh.eval`, computed when its argument holds an expansion;
//! - strings, heredocs and comments are never command nodes, so text inside them names nothing.
//!
//! Not modelled: variables holding a command name (`c=rm; $c` is computed, never followed),
//! functions defined in a sourced file, `PATH` rewrites and `command_not_found` handlers.

// frob:ticket 01M64VBRKZE3BBSQNX21PKHMPA

use std::collections::BTreeMap;

use tree_sitter::Node;

use crate::canon::PathUse;

/// Deepest alias chain followed (`alias a=b; alias b=rm`).
const MAX_ALIAS_DEPTH: usize = 6;

/// Commands that run another command named by their first non-option word.
const WRAPPERS: &[&str] = &[
    "env", "command", "exec", "nohup", "sudo", "xargs", "time", "builtin",
];

/// Directories whose commands resolve by basename.
const BIN_DIRS: &[&str] = &[
    "/bin/",
    "/usr/bin/",
    "/usr/local/bin/",
    "/sbin/",
    "/usr/sbin/",
];

/// Shells whose `-c` argument is a script run by name.
const SHELLS: &[&str] = &["bash", "sh", "zsh", "dash", "ksh"];

/// Per-file facts gathered before commands are resolved.
struct Cx<'s> {
    src: &'s str,
    funcs: Vec<String>,
    aliases: BTreeMap<String, String>,
    out: Vec<PathUse>,
}

/// Scans a parsed shell script for command uses, in document order.
pub(crate) fn scan(src: &str, root: Node<'_>) -> Vec<PathUse> {
    let mut cx = Cx {
        src,
        funcs: Vec::new(),
        aliases: BTreeMap::new(),
        out: Vec::new(),
    };
    cx.collect(root);
    tracing::debug!(
        funcs = cx.funcs.len(),
        aliases = cx.aliases.len(),
        "shell: definitions bound"
    );
    cx.visit(root);
    cx.out
}

impl Cx<'_> {
    fn text(&self, n: Node<'_>) -> &str {
        &self.src[n.start_byte()..n.end_byte()]
    }

    /// The command name node followed by the argument nodes of a `command`.
    fn words(cmd: Node<'_>) -> Vec<Node<'_>> {
        let mut cur = cmd.walk();
        cmd.named_children(&mut cur)
            .filter(|c| {
                !matches!(
                    c.kind(),
                    "variable_assignment"
                        | "file_redirect"
                        | "heredoc_redirect"
                        | "herestring_redirect"
                        | "comment"
                )
            })
            .collect()
    }

    /// The text of a word when it is one plain literal (quotes removed), else `None`.
    fn literal(&self, n: Node<'_>) -> Option<String> {
        match n.kind() {
            "command_name" => self.literal(n.named_child(0)?),
            "word" | "number" => Some(self.text(n).to_owned()),
            "raw_string" => {
                let t = self.text(n);
                Some(t.get(1..t.len().checked_sub(1)?)?.to_owned())
            }
            "string" => {
                let mut cur = n.walk();
                let mut out = String::new();
                for c in n.named_children(&mut cur) {
                    if c.kind() != "string_content" {
                        return None;
                    }
                    out.push_str(self.text(c));
                }
                Some(out)
            }
            "concatenation" => {
                let mut cur = n.walk();
                let mut out = String::new();
                for c in n.named_children(&mut cur) {
                    out.push_str(&self.literal(c)?);
                }
                Some(out)
            }
            _ => None,
        }
    }

    /// Records function definitions and `alias n=v` words.
    fn collect(&mut self, n: Node<'_>) {
        match n.kind() {
            "function_definition" => {
                if let Some(name) = n.child_by_field_name("name") {
                    self.funcs.push(self.text(name).to_owned());
                }
            }
            "command" => {
                let words = Self::words(n);
                if words.first().and_then(|w| self.literal(*w)).as_deref() == Some("alias") {
                    for w in &words[1..] {
                        let Some(spec) = self.literal(*w) else {
                            continue;
                        };
                        if let Some((k, v)) = spec.split_once('=') {
                            let target = v.split_whitespace().next().unwrap_or("");
                            self.aliases.insert(k.to_owned(), target.to_owned());
                        }
                    }
                }
            }
            _ => {}
        }
        let mut cur = n.walk();
        for c in n.children(&mut cur) {
            self.collect(c);
        }
    }

    /// Visits every command node, including those inside substitutions and function bodies.
    fn visit(&mut self, n: Node<'_>) {
        if n.kind() == "command" {
            let words = Self::words(n);
            self.resolve(&words);
        }
        let mut cur = n.walk();
        for c in n.children(&mut cur) {
            self.visit(c);
        }
    }

    /// Follows aliases, then strips a standard bin directory; `None` when a function shadows it
    /// or the word is a path to some other file.
    fn canon(&self, name: &str) -> Option<String> {
        let mut cur = name.to_owned();
        for _ in 0..MAX_ALIAS_DEPTH {
            match self.aliases.get(&cur) {
                Some(next) if next != &cur => next.clone_into(&mut cur),
                _ => break,
            }
        }
        if self.funcs.contains(&cur) {
            tracing::trace!(name, "shell: function shadows command");
            return None;
        }
        if let Some(base) = BIN_DIRS.iter().find_map(|d| cur.strip_prefix(d)) {
            return Some(base.to_owned());
        }
        (!cur.contains('/') && !cur.is_empty()).then_some(cur)
    }

    fn emit(&mut self, at: Node<'_>, path: String, computed: bool) {
        let spelled = self.text(at).to_owned();
        self.out.push(PathUse {
            offset: at.start_byte(),
            line: u32::try_from(at.start_position().row + 1).unwrap_or(u32::MAX),
            spelled,
            path,
            call: true,
            dynamic: computed,
            external_root: false,
            computed,
            wildcards: Vec::new(),
            maybe: false,
        });
    }

    /// Resolves the command word `words[0]` and, for a wrapper, the command it runs.
    fn resolve(&mut self, words: &[Node<'_>]) {
        let Some(&head) = words.first() else { return };
        let Some(name) = self.literal(head) else {
            tracing::debug!(
                at = head.start_byte(),
                "shell: expansion in command position"
            );
            self.emit(head, String::new(), true);
            return;
        };
        let Some(cmd) = self.canon(&name) else { return };
        let args = &words[1..];
        let any_dynamic = args.iter().any(|a| self.literal(*a).is_none());
        let computed = (cmd == "eval" && any_dynamic)
            || (SHELLS.contains(&cmd.as_str()) && self.dynamic_script(args));
        self.emit(head, format!("sh.{cmd}"), computed);
        if WRAPPERS.contains(&cmd.as_str()) {
            let next = args.iter().position(|a| {
                self.literal(*a)
                    .is_none_or(|l| !l.starts_with('-') && !l.contains('='))
            });
            if let Some(i) = next {
                self.resolve(&args[i..]);
            }
        }
    }

    /// True when the argument after `-c` is not a plain literal.
    fn dynamic_script(&self, args: &[Node<'_>]) -> bool {
        let flag = args
            .iter()
            .position(|a| self.literal(*a).as_deref() == Some("-c"));
        flag.and_then(|i| args.get(i + 1))
            .is_some_and(|a| self.literal(*a).is_none())
    }
}

#[cfg(test)]
mod tests {
    use crate::canon::{PathUse, path_uses};

    fn uses(src: &str) -> Vec<PathUse> {
        path_uses("shell", src)
    }

    fn paths(src: &str) -> Vec<String> {
        uses(src).into_iter().map(|u| u.path).collect()
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn plain_commands_resolve_to_sh_paths() {
        let p = paths("curl -s u | tee o\nwget u\nnc h 1\ncat f\nenv\n");
        for want in ["sh.curl", "sh.tee", "sh.wget", "sh.nc", "sh.cat", "sh.env"] {
            assert!(p.contains(&want.to_owned()), "{want} in {p:?}");
        }
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn alias_resolves_to_its_target() {
        let u = uses("alias r=rm\nr -rf x\n");
        assert!(u.iter().any(|u| u.path == "sh.rm" && !u.computed), "{u:?}");
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn function_shadows_the_command() {
        let p = paths("rm() { echo hi; }\nrm -rf x\n");
        assert!(!p.contains(&"sh.rm".to_owned()), "{p:?}");
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn expansion_in_command_position_is_computed() {
        let u = uses("c=r\n$c\"m\" -rf x\n");
        assert!(u.iter().any(|u| u.computed && u.path.is_empty()), "{u:?}");
        let u = uses("eval \"$1\"\n");
        assert!(u.iter().any(|u| u.computed && u.path == "sh.eval"), "{u:?}");
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn wrappers_and_shell_dash_c_resolve() {
        let p = paths("env FOO=1 rm x\n/bin/cat f\nbash -c 'ls'\n");
        for want in ["sh.env", "sh.rm", "sh.cat", "sh.bash"] {
            assert!(p.contains(&want.to_owned()), "{want} in {p:?}");
        }
        let u = uses("bash -c \"$x\"\n");
        assert!(u.iter().any(|u| u.path == "sh.bash" && u.computed), "{u:?}");
    }

    // frob:tests crates/gob-symbols/src/canon.rs::path_uses
    #[test]
    fn strings_and_comments_name_nothing() {
        let p = paths("echo \"rm -rf /\"\n# curl x\n");
        assert!(!p.contains(&"sh.rm".to_owned()), "{p:?}");
        assert!(!p.contains(&"sh.curl".to_owned()), "{p:?}");
    }
}
