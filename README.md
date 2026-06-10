# FROB

These are tools that I use in my development workflow. There is a number of subtools under the `frob`
name.

---
## `init` -- A project templater

Running `uvx frob init list` will list the registered project types. Some examples are `python-library` and
`python-tool`. This is also not limited to a single language: there are templates for Python, C++, C, AVR assembly,
and as many types of projects as I feel like supporting.

---
## `cycle` -- A dependency cycle checker

For whatever reason, I cannot find a good cycle detector that works. This cycle checker will tell you
the dependencies and clearly lay out all of the dependency cycles as specifically as it can manage.
For instance, it will be able to tell you what files include what. It also will give suggestions on 
how to reorganize your projects to move the dependencies in such a way that you don't create a cycle by
accident (by grouping a simple primitive with something that includes something that uses that primitive).
If that's not possible, it will give you decoupling tips on how to refactor, whether that be trying its
best to detect if you can change a C++ class into an opaque type and so forth.

---
## `stub` -- A stub generator for AI context and faster checking/updating loop

A lot of times you don't need the whole source file to type-check or provide context for an LLM. By using
`stub`, you can extract only the function of note, converting all other classes and functions (including
the other functions within the same class) into typed stubs or basic header includes. This also has the
added benefit of forcing decoupled logic.

