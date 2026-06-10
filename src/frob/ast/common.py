from typing import Protocol, NewType
from pathlib import Path

from tree_sitter import Language, Parser, Node

ModuleTag = NewType("ModuleTag", str)
ClassTag = NewType("ClassTag", str)
FunctionTag = NewType("FunctionTag", str)


class UsableByCycle(Protocol):
    def get_imports(self, mod_tag: ModuleTag) -> list[ModuleTag]:
        """
        Return the modules imported/included by mod_tag.
        ModuleTag values are file paths relative to the scan root.
        """
        ...


class UsableByStub(Protocol):
    def get_classes(self, mod_tag: ModuleTag) -> list[ClassTag]: ...
    def get_all_functions(self, mod_tag: ModuleTag) -> list[FunctionTag]: ...
    def get_class_functions(self, class_tag: ClassTag) -> list[FunctionTag]: ...


class StubEmitter(Protocol):
    def emit(
        self,
        source: bytes,
        target: str,
        *,
        tree: "object",
    ) -> str:
        """
        Return source text with every non-target function/method body replaced
        by a stub, and the target body kept verbatim.
        """
        ...


def make_parser(language: Language) -> Parser:
    return Parser(language)


def text(node: Node) -> str:
    return node.text.decode() if node.text else ""


def child_by_field(node: Node, field: str) -> Node | None:
    return node.child_by_field_name(field)
