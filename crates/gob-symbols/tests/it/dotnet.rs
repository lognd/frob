//! The .NET project model end to end: solutions, project references, ownership and malformed projects.

// frob:ticket 01M44YQW33GJMXQ8PQBECEBCQ1

use std::path::Path;

use gob_symbols::{Assignment, CrateDeps, DotnetProjects};

fn write(root: &Path, files: &[(&str, &str)]) {
    for (path, text) in files {
        let full = root.join(path);
        std::fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        std::fs::write(full, text).expect("write");
    }
}

const SLN: &str = "Microsoft Visual Studio Solution File, Format Version 12.00\n\
Project(\"{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}\") = \"App\", \"src\\App\\App.csproj\", \"{1}\"\nEndProject\n\
Project(\"{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}\") = \"Lib\", \"src\\Lib\\Lib.csproj\", \"{2}\"\nEndProject\n\
Project(\"{2150E333-8FDC-42A3-9474-D2E70F8ED6FD}\") = \"Docs\", \"Docs\", \"{3}\"\nEndProject\n";

const APP: &str = "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup><ProjectReference Include=\"..\\Lib\\Lib.csproj\" /></ItemGroup></Project>";
const LIB: &str = "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><AssemblyName>Acme.Lib</AssemblyName></PropertyGroup></Project>";

fn two_projects(root: &Path) {
    write(
        root,
        &[
            ("My.sln", SLN),
            ("src/App/App.csproj", APP),
            ("src/App/Program.cs", "class P {}"),
            ("src/App/obj/Debug/Gen.cs", "class G {}"),
            ("src/Lib/Lib.csproj", LIB),
            ("src/Lib/Thing.cs", "class T {}"),
        ],
    );
}

// frob:tests crates/gob-symbols/src/crates.rs::CrateDeps.transitive_deps
#[test]
fn each_project_is_a_package_and_a_reference_is_an_edge() {
    let dir = tempfile::tempdir().expect("tempdir");
    two_projects(dir.path());
    let mut deps = CrateDeps::new(dir.path());
    assert_eq!(
        deps.solution_packages("My.sln"),
        ["src/App/App.csproj", "src/Lib/Lib.csproj"]
    );
    assert_eq!(
        deps.crate_of("src/App/Program.cs").as_deref(),
        Some("src/App/App.csproj")
    );
    assert_eq!(
        deps.crate_of("src/Lib/Thing.cs").as_deref(),
        Some("src/Lib/Lib.csproj")
    );
    assert_eq!(
        deps.transitive_deps("src/App/App.csproj"),
        ["src/Lib/Lib.csproj"]
    );
    assert!(deps.file_can_reach("src/App/Program.cs", "src/Lib/Thing.cs"));
    assert!(!deps.file_can_reach("src/Lib/Thing.cs", "src/App/Program.cs"));
    assert_eq!(
        deps.extern_crates("src/App/App.csproj"),
        [
            ("Acme.Lib".to_owned(), "src/Lib/Lib.csproj".to_owned()),
            ("App".to_owned(), "src/App/App.csproj".to_owned())
        ]
    );
    assert!(
        deps.implicit_usings_of("src/App/Program.cs")
            .contains(&"System.Linq".to_owned())
    );
}

// frob:tests crates/gob-symbols/src/dotnet.rs::DotnetProjects.assign
#[test]
fn build_outputs_are_ignored_and_the_nearest_project_wins() {
    let dir = tempfile::tempdir().expect("tempdir");
    two_projects(dir.path());
    write(
        dir.path(),
        &[
            ("src/App/Tools/Tools.csproj", LIB),
            ("src/App/Tools/T.cs", ""),
        ],
    );
    let mut p = DotnetProjects::new(dir.path());
    assert_eq!(p.assign("src/App/obj/Debug/Gen.cs"), Assignment::Ignored);
    assert_eq!(
        p.assign("src/App/Tools/T.cs"),
        Assignment::Project("src/App/Tools/Tools.csproj".to_owned())
    );
    assert_eq!(p.assign("elsewhere/X.cs"), Assignment::None);
}

// frob:tests crates/gob-symbols/src/dotnet.rs::DotnetProjects.malformed
#[test]
fn a_malformed_project_is_reported_and_unresolved_not_skipped() {
    let dir = tempfile::tempdir().expect("tempdir");
    two_projects(dir.path());
    write(
        dir.path(),
        &[
            ("src/Bad/Bad.csproj", "<Project><ItemGroup></Project>"),
            ("src/Bad/B.cs", "class B {}"),
        ],
    );
    let mut deps = CrateDeps::new(dir.path());
    let found = deps.malformed_projects(&["src/App/App.csproj", "src/Bad/Bad.csproj"]);
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].path, "src/Bad/Bad.csproj");
    assert!(found[0].reason.contains("line 1"), "{}", found[0].reason);
    // The project still owns its files, and reach into or out of it is never ruled out.
    assert_eq!(
        deps.crate_of("src/Bad/B.cs").as_deref(),
        Some("src/Bad/Bad.csproj")
    );
    assert!(deps.file_can_reach("src/Bad/B.cs", "src/Lib/Thing.cs"));
    assert!(deps.file_can_reach("src/Lib/Thing.cs", "src/Bad/B.cs"));
}
