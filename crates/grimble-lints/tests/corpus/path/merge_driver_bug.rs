use std::path::Path;
use std::process::Command;

fn install(repo: &Path, exe: &Path) {
    let driver = format!("{} merge %O %A %B", exe.display());
    Command::new("git").arg("config").arg(driver).current_dir(repo);
}
