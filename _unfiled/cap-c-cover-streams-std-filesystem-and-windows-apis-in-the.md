+++
id = "01M681KE15QSX4PAR9ARG5JRPP"
title = "CAP C++: cover streams, std::filesystem and Windows APIs in the vocabulary"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-31T03:56:07Z"
updated = "2026-10-31T03:56:07Z"
scope = ["crates/gob-symbols/src/c_uses.rs"]

[[acceptance]]
text = "fstream and iostream file opens, std::filesystem operations and common Win32 process, file and net calls map to capabilities with tests."
bound = false
+++

The C/C++ libc table does not cover C++ streams, std::filesystem or Windows APIs. (found while working ~S1VG0FG)
