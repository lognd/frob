use std::path::PathBuf;

struct RepoPath(String);

impl RepoPath {
    fn child(&self, name: &str) -> RepoPath {
        RepoPath(format!("{}/{}", self.0, name))
    }
}

fn join(base: PathBuf, name: &str) -> PathBuf {
    base.join(name)
}
