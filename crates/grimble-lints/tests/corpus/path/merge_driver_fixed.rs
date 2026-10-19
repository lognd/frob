use std::path::Path;
use std::process::Command;

fn install(repo: &Path, exe: &Path) {
    Command::new("git").arg("config").arg(exe).current_dir(repo);
}
