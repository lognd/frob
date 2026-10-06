//! The facts a framework adapter answers: detections, routes and entrypoints (language-engines.md section 4).

// frob:ticket 01M47QKVBB5G9N1QZP3AVXTRHX

use std::fmt;

pub use gob_ir::Status;

/// A framework found in one workspace member.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Detection {
    /// The framework's registry name (`react-router`, `nextjs`).
    pub framework: &'static str,
    /// Repo-relative path of the member's `package.json`.
    pub member: String,
    /// Repo-relative directory of the member (empty at the repository root).
    pub dir: String,
    /// Why it was detected, one line per matching detector (`dependency next`).
    pub evidence: Vec<String>,
}

/// The HTTP method a route answers.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Method {
    /// `GET` (a page render or a loader).
    Get,
    /// `POST`.
    Post,
    /// `PUT`.
    Put,
    /// `PATCH`.
    Patch,
    /// `DELETE`.
    Delete,
    /// `HEAD`.
    Head,
    /// `OPTIONS`.
    Options,
    /// Any method (a handler that dispatches itself, or an export that could not be read).
    Any,
}

impl Method {
    /// The method named by an exported handler `name` (`GET`, `POST`, ...), if it is one.
    pub fn from_export(name: &str) -> Option<Self> {
        Some(match name {
            "GET" => Self::Get,
            "POST" => Self::Post,
            "PUT" => Self::Put,
            "PATCH" => Self::Patch,
            "DELETE" => Self::Delete,
            "HEAD" => Self::Head,
            "OPTIONS" => Self::Options,
            _ => return None,
        })
    }

    /// The upper-case name (`ANY` for [`Method::Any`]).
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Get => "GET",
            Self::Post => "POST",
            Self::Put => "PUT",
            Self::Patch => "PATCH",
            Self::Delete => "DELETE",
            Self::Head => "HEAD",
            Self::Options => "OPTIONS",
            Self::Any => "ANY",
        }
    }
}

/// One route of a repository: a path pattern answered by a handler or a page.
///
/// A pattern uses `:name` for a dynamic segment, `:name+` for a catch-all and `:name*` for an optional
/// catch-all, and always starts with `/`. `pattern` is `None` exactly when the path is not statically known;
/// the route is then reported with status [`Status::Unknown`], never omitted.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Route {
    /// The registry name of the framework that declares it.
    pub framework: &'static str,
    /// Repo-relative path of the owning member's `package.json`.
    pub member: String,
    /// The path pattern, or `None` when it is not statically known.
    pub pattern: Option<String>,
    /// The method it answers.
    pub method: Method,
    /// The symref of the handler unit (a route handler, loader or action), when there is one.
    pub handler: Option<String>,
    /// The page component: a symref when it resolves, else the name as written.
    pub component: Option<String>,
    /// The layouts around it, outermost first, each a symref when it resolves else the name as written.
    pub layouts: Vec<String>,
    /// `Must` when the route is proven, `May` when it is conditional or one of several paths, `Unknown` when
    /// its path is not statically known.
    pub status: Status,
    /// Repo-relative path of the file that declares the route.
    pub file: String,
    /// One-based line of the declaration.
    pub line: u32,
    /// True when the page sits behind a `"use client"` boundary (Next.js).
    pub client: bool,
}

impl fmt::Display for Route {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{} {} [{:?}] {}:{}",
            self.method.as_str(),
            self.pattern.as_deref().unwrap_or("?"),
            self.status,
            self.file,
            self.line
        )?;
        if let Some(h) = &self.handler {
            write!(f, " handler={h}")?;
        }
        if let Some(c) = &self.component {
            write!(f, " component={c}")?;
        }
        if !self.layouts.is_empty() {
            write!(f, " layouts={}", self.layouts.join(">"))?;
        }
        if self.client {
            f.write_str(" client")?;
        }
        Ok(())
    }
}

/// What kind of entry into the application an [`Entrypoint`] is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum EntrypointKind {
    /// A page file.
    Page,
    /// A route handler file (an API route).
    Handler,
    /// A middleware file.
    Middleware,
    /// A file that registers a client-side router.
    Router,
}

/// A file the framework itself starts executing (Q-table `entrypoints`).
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Entrypoint {
    /// The registry name of the framework.
    pub framework: &'static str,
    /// Repo-relative path of the owning member's `package.json`.
    pub member: String,
    /// What kind of entry it is.
    pub kind: EntrypointKind,
    /// Repo-relative path of the file.
    pub file: String,
}

/// What one framework adapter found in one member.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct Discovery {
    /// The routes.
    pub routes: Vec<Route>,
    /// The entrypoints.
    pub entrypoints: Vec<Entrypoint>,
}

/// A file or manifest the analysis could not read or parse; its facts are missing, not absent.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Problem {
    /// Repo-relative path.
    pub path: String,
    /// Why.
    pub reason: String,
}

/// Everything [`crate::analyze`] found in a repository.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct Analysis {
    /// The frameworks found, per member.
    pub detections: Vec<Detection>,
    /// Every route, sorted.
    pub routes: Vec<Route>,
    /// Every entrypoint, sorted.
    pub entrypoints: Vec<Entrypoint>,
    /// Manifests and sources that could not be read.
    pub problems: Vec<Problem>,
}
