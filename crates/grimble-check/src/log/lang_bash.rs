//! The Bash scanner: `echo`, `printf` (not `-v`), the std-stream redirections (`>&2`, `2>&1`,
//! `>/dev/stderr`, `/dev/fd/N`), user wrapper functions, with captured output (command
//! substitution, pipelines, file redirects) and own functions shadowing.

// frob:ticket 01M63G1MW58WP8VBQ7T6NKDAMD

use std::collections::BTreeSet;

use tree_sitter::Node;

use super::catalogue::Args;
use super::engine::{Binding, FileScan, State, kids};

/// Atom ids the scanner reports itself.
const PRINTF: &str = "sh.printf";
const STDERR_REDIRECT: &str = "sh.stderr-redirect";
const STDOUT_REDIRECT: &str = "sh.stdout-redirect";
const FD_WRITE: &str = "sh.fd-write";
const DIE: &str = "sh.die";

/// Whether the stdout of the command being visited is captured, piped or redirected.
#[derive(Clone, Copy)]
struct Cx {
    captured: bool,
}

/// What one redirection does, as far as output is concerned.
#[derive(Debug, PartialEq, Eq)]
enum Redirect {
    /// Writes to stderr (`>&2`, `1>&2`, `>/dev/stderr`).
    ToStderr,
    /// Names stdout (`>&1`, `>/dev/stdout`).
    ToStdout,
    /// Merges stderr into stdout (`2>&1`).
    Merge,
    /// A numbered std descriptor path (`/dev/fd/2`).
    FdPath,
    /// Sends stdout to a file or /dev/null.
    ToFile,
    /// Duplicates onto a descriptor chosen at run time (`>&$fd`, `>/dev/fd/$n`).
    Dynamic,
    /// Anything else (input redirects, other descriptors).
    Other,
}

/// Functions defined so far whose body produced output (call sites are wrapper atoms).
struct Walk {
    wrappers: BTreeSet<String>,
}

/// Scan one parsed shell script.
pub fn scan(mut st: State<'_>, root: Node<'_>) -> FileScan {
    bind_functions(&mut st, root);
    let mut w = Walk {
        wrappers: BTreeSet::new(),
    };
    w.visit(&mut st, root, Cx { captured: false });
    tracing::debug!(file = %st.ctx.path, hits = st.hits.len(), "bash scan done");
    st.finish()
}

/// Bind every function the script defines so a user `echo` shadows the builtin.
fn bind_functions(st: &mut State<'_>, n: Node<'_>) {
    if n.kind() == "function_definition"
        && let Some(name) = n.child_by_field_name("name")
    {
        let name = st.txt(name).to_owned();
        st.bind(&name, Binding::Opaque);
    }
    for c in kids(n) {
        bind_functions(st, c);
    }
}

/// Classify the text of one `file_redirect`.
fn classify(text: &str) -> Redirect {
    let t = text.trim();
    let digits = t.chars().take_while(char::is_ascii_digit).count();
    let (fd, rest) = t.split_at(digits);
    let (amp_both, rest) = match rest.strip_prefix("&>") {
        Some(r) => (true, r.trim_start_matches('>')),
        None => (false, rest),
    };
    let (dup, dest) = if amp_both {
        (false, rest)
    } else if let Some(r) = rest.strip_prefix(">&") {
        (true, r)
    } else if let Some(r) = rest
        .strip_prefix(">>")
        .or_else(|| rest.strip_prefix(">|"))
        .or_else(|| rest.strip_prefix('>'))
    {
        (false, r)
    } else {
        return Redirect::Other;
    };
    let dest = dest.trim().trim_matches(['"', '\'']);
    let to_fd1 = amp_both || fd.is_empty() || fd == "1";
    let std_fd_dir = dest.starts_with("/dev/fd/") || dest.starts_with("/proc/self/fd/");
    if dest.contains('$') && to_fd1 && (dup || std_fd_dir) {
        return Redirect::Dynamic;
    }
    if dup {
        return match (fd, dest) {
            ("2", "1") => Redirect::Merge,
            ("" | "1", "1") => Redirect::ToStdout,
            ("" | "1", "2") => Redirect::ToStderr,
            _ => Redirect::Other,
        };
    }
    match dest {
        "/dev/stderr" if to_fd1 => Redirect::ToStderr,
        "/dev/stdout" | "/dev/tty" | "/dev/console" | "/dev/fd/1" | "/proc/self/fd/1" if to_fd1 => {
            Redirect::ToStdout
        }
        "/dev/fd/2" | "/proc/self/fd/2" if to_fd1 => Redirect::FdPath,
        _ if to_fd1 && !dest.is_empty() => Redirect::ToFile,
        _ => Redirect::Other,
    }
}

impl Walk {
    fn visit(&mut self, st: &mut State<'_>, n: Node<'_>, cx: Cx) {
        match n.kind() {
            "comment" | "heredoc_body" | "string" | "raw_string" | "ansi_c_string" => {
                // substitutions inside strings still run (captured)
                if n.kind() == "string" {
                    for c in kids(n) {
                        self.visit(st, c, Cx { captured: true });
                    }
                }
            }
            "function_definition" => {
                let before = st.hits.len();
                st.push();
                for c in kids(n) {
                    if c.kind() != "word" {
                        self.visit(st, c, Cx { captured: false });
                    }
                }
                st.pop();
                if st.hits.len() > before
                    && let Some(name) = n.child_by_field_name("name")
                {
                    let name = st.txt(name).to_owned();
                    tracing::debug!(func = %name, "shell function wraps direct output");
                    self.wrappers.insert(name);
                }
            }
            "command_substitution" | "process_substitution" => {
                for c in kids(n) {
                    self.visit(st, c, Cx { captured: true });
                }
            }
            "pipeline" => {
                let parts = kids(n);
                let last = parts.len().saturating_sub(1);
                for (i, c) in parts.into_iter().enumerate() {
                    let inner = Cx {
                        captured: cx.captured || i != last,
                    };
                    self.visit(st, c, inner);
                }
            }
            "redirected_statement" => self.redirected(st, n, cx),
            "command" => self.command(st, n, cx, &[]),
            _ => {
                for c in kids(n) {
                    self.visit(st, c, cx);
                }
            }
        }
    }

    /// A statement with redirections: report std-stream targets, then visit the body captured
    /// when stdout is redirected.
    fn redirected(&mut self, st: &mut State<'_>, n: Node<'_>, cx: Cx) {
        let redirects: Vec<Node<'_>> = kids(n)
            .into_iter()
            .filter(|c| c.kind() == "file_redirect")
            .collect();
        let body = n.child_by_field_name("body");
        match body {
            Some(b) if b.kind() == "command" => self.command(st, b, cx, &redirects),
            Some(b) => {
                let inner = Self::report(st, &redirects, cx, false);
                self.visit(st, b, inner);
            }
            None => {}
        }
        for c in kids(n) {
            if !matches!(c.kind(), "file_redirect") && Some(c.id()) != body.map(|b| b.id()) {
                self.visit(st, c, cx);
            }
        }
    }

    /// Report the std-stream redirections of `redirects`; the returned context says whether the
    /// command's stdout is redirected away from the terminal.
    fn report(st: &mut State<'_>, redirects: &[Node<'_>], cx: Cx, is_exec: bool) -> Cx {
        let kinds: Vec<(Node<'_>, Redirect)> = redirects
            .iter()
            .map(|r| (*r, classify(st.txt(*r))))
            .collect();
        let fd1_away = kinds.iter().any(|(_, k)| {
            matches!(
                k,
                Redirect::ToStderr | Redirect::ToStdout | Redirect::FdPath | Redirect::ToFile
            )
        });
        let to_file = kinds.iter().any(|(_, k)| *k == Redirect::ToFile);
        if !is_exec {
            for (r, k) in &kinds {
                let text = st.txt(*r).trim().to_owned();
                if *k == Redirect::Dynamic {
                    st.unres(*r, "redirect to a descriptor chosen at run time");
                }
                let atom = match k {
                    Redirect::ToStderr => Some(STDERR_REDIRECT),
                    Redirect::ToStdout if !cx.captured => Some(STDOUT_REDIRECT),
                    Redirect::Merge if !cx.captured && !to_file => Some(STDERR_REDIRECT),
                    Redirect::FdPath => Some(FD_WRITE),
                    _ => None,
                };
                if let Some(atom) = atom {
                    st.hit_atom(*r, atom, &[text]);
                }
            }
        }
        Cx {
            captured: cx.captured || fd1_away || to_file,
        }
    }

    /// One simple command: resolve its name, report output, then walk its arguments.
    fn command(&mut self, st: &mut State<'_>, n: Node<'_>, cx: Cx, outer: &[Node<'_>]) {
        let name_node = n.child_by_field_name("name");
        let name = name_node.map(|c| st.txt(c).to_owned()).unwrap_or_default();
        let own: Vec<Node<'_>> = kids(n)
            .into_iter()
            .filter(|c| c.kind() == "file_redirect")
            .collect();
        let all: Vec<Node<'_>> = outer.iter().copied().chain(own).collect();
        let inner = Self::report(st, &all, cx, name == "exec");
        let plain = !name.is_empty()
            && name
                .chars()
                .all(|c| c.is_alphanumeric() || matches!(c, '_' | '-' | '.' | ':'));
        if plain && !inner.captured {
            let args: Vec<&str> = kids(n)
                .into_iter()
                .filter(|c| Some(c.id()) != name_node.map(|x| x.id()) && c.kind() == "word")
                .map(|c| st.txt(c))
                .collect();
            let path = vec![name.clone()];
            match st.lookup(&name) {
                Some(Binding::Opaque) => {
                    if self.wrappers.contains(&name) {
                        st.hit_atom(n, DIE, &path);
                    }
                }
                _ if name == "logger" => st.note(&path),
                _ if name == "printf" => {
                    if !args.contains(&"-v") {
                        st.hit_atom(n, PRINTF, &path);
                    }
                }
                _ => {
                    st.hit_call(n, &path, &Args::default());
                }
            }
        } else if plain && name == "logger" {
            st.note(&[name]);
        }
        for c in kids(n) {
            if Some(c.id()) != name_node.map(|x| x.id()) && c.kind() != "file_redirect" {
                self.visit(st, c, inner);
            }
        }
    }
}
