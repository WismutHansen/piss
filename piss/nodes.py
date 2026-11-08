"""The abstract syntax tree. Deliberately small."""

from __future__ import annotations

from dataclasses import dataclass, field


class Node:
    line: int = 0


# --- expressions ---------------------------------------------------------


@dataclass
class Literal(Node):
    value: object
    line: int = 0


@dataclass
class ListLiteral(Node):
    items: list[Node] = field(default_factory=list)
    line: int = 0


@dataclass
class Name(Node):
    name: str
    line: int = 0


@dataclass
class Unary(Node):
    op: str
    operand: Node
    line: int = 0


@dataclass
class Binary(Node):
    op: str
    left: Node
    right: Node
    line: int = 0


@dataclass
class Call(Node):
    callee: Node
    args: list[Node] = field(default_factory=list)
    line: int = 0


# --- statements ----------------------------------------------------------


@dataclass
class Puddle(Node):  # let
    name: str
    value: Node
    line: int = 0


@dataclass
class Assign(Node):
    name: str
    value: Node
    line: int = 0


@dataclass
class Leak(Node):  # print
    value: Node
    line: int = 0


@dataclass
class ExprStmt(Node):
    expr: Node
    line: int = 0


@dataclass
class If(Node):
    cond: Node
    then: list[Node]
    otherwise: list[Node] | None = None
    line: int = 0


@dataclass
class Drain(Node):  # for x in iterable { ... }
    var: str
    iterable: Node
    body: list[Node] = field(default_factory=list)
    line: int = 0


@dataclass
class Valve(Node):  # fn
    name: str
    params: list[str]
    body: list[Node]
    line: int = 0


@dataclass
class Flush(Node):  # return
    value: Node | None = None
    line: int = 0


@dataclass
class Splash(Node):  # raise
    value: Node | None = None
    line: int = 0


@dataclass
class Program(Node):
    body: list[Node] = field(default_factory=list)
    line: int = 0
