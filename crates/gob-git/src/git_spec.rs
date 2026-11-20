//! The one place a `git` [`Spec`] is built.
// frob:ticket 01M7X35W2WATD06TP58JC8MS7H

use std::path::Path;
use std::time::Duration;

use gob_exec::{Program, Spec};

/// A captured `git <args>` run in `cwd`, bounded by `timeout`, with no extra environment.
///
/// Every `git` spawn in the workspace is built here and run on a [`gob_exec::Runner`], so the
/// runner's spawn counter sees it and one spec shape (capture on, no env, an explicit timeout)
/// serves every caller. A caller that needs variables pushes them onto the returned spec's `env`.
pub fn git_spec<I, S>(cwd: impl AsRef<Path>, args: I, timeout: Duration) -> Spec
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    Spec {
        program: Program::Git,
        args: args.into_iter().map(|a| a.as_ref().to_owned()).collect(),
        cwd: Some(cwd.as_ref().to_path_buf()),
        env: Vec::new(),
        timeout,
        capture: true,
    }
}
