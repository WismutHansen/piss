"""Recursive descent, in one direction only."""

from __future__ import annotations

from . import nodes as n
from .errors import Blocked, Uphill
from .lexer import Token, lex

PRECEDENCE = [
    ("or",),
    ("and",),
    ("==", "!="),
    ("<", "<=", ">", ">="),
    ("+", "-"),
    ("*", "/", "%"),
]


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # --- helpers ---------------------------------------------------------

    @property
    def cur(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, ahead: int = 1) -> Token:
        idx = min(self.pos + ahead, len(self.tokens) - 1)
        return self.tokens[idx]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.kind != "eof":
            self.pos += 1
        return tok

    def check(self, kind: str, value: object = None) -> bool:
        tok = self.cur
        if tok.kind != kind:
            return False
        return value is None or tok.value == value

    def match(self, kind: str, value: object = None) -> Token | None:
        if self.check(kind, value):
            return self.advance()
        return None

    def expect(self, kind: str, value: object = None) -> Token:
        tok = self.match(kind, value)
        if tok is None:
            want = f"{kind} {value!r}" if value is not None else kind
            got = f"{self.cur.kind} {self.cur.value!r}"
            raise Blocked(f"expected {want}, found {got}", self.cur.line, self.cur.col)
        return tok

    def skip_separators(self) -> None:
        while self.check("op", ";") or self.check("op", ","):
            # commas are only separators at statement level, not in calls/lists,
            # so be careful: this helper is used between statements only.
            self.advance()

    # --- entry -----------------------------------------------------------

    def parse_program(self) -> n.Program:
        body: list[n.Node] = []
        while not self.check("eof"):
            if self.match("op", ";"):
                continue
            body.append(self.statement())
        return n.Program(body)

    # --- statements ------------------------------------------------------

    def statement(self) -> n.Node:
        tok = self.cur

        if tok.kind == "kw" and tok.value == "while":
            raise Uphill(
                "water does not flow uphill: there is no `while`. Use `drain`.",
                tok.line,
                tok.col,
            )
        if tok.kind == "kw" and tok.value == "for":
            raise Uphill(
                "there is no `for`. Use `drain <iterable> name { ... }`.",
                tok.line,
                tok.col,
            )

        if tok.kind == "kw":
            if tok.value == "puddle":
                self.advance()
                name = self.expect("ident").value
                self.expect("op", "=")
                return n.Puddle(str(name), self.expression(), tok.line)
            if tok.value == "leak":
                self.advance()
                return n.Leak(self.expression(), tok.line)
            if tok.value == "if":
                return self.if_statement()
            if tok.value == "drain":
                self.advance()
                iterable = self.expression()
                var = self.expect("ident").value
                body = self.block()
                return n.Drain(str(var), iterable, body, tok.line)
            if tok.value == "valve":
                self.advance()
                name = self.expect("ident").value
                self.expect("op", "(")
                params: list[str] = []
                if not self.check("op", ")"):
                    while True:
                        params.append(str(self.expect("ident").value))
                        if not self.match("op", ","):
                            break
                self.expect("op", ")")
                body = self.block()
                return n.Valve(str(name), params, body, tok.line)
            if tok.value == "flush":
                self.advance()
                if self.check("op", "}") or self.check("eof") or self.check("op", ";"):
                    return n.Flush(None, tok.line)
                return n.Flush(self.expression(), tok.line)
            if tok.value == "splash":
                self.advance()
                if self.check("op", "}") or self.check("eof") or self.check("op", ";"):
                    return n.Splash(None, tok.line)
                return n.Splash(self.expression(), tok.line)

        # assignment or a bare expression
        if tok.kind == "ident" and self.peek().kind == "op" and self.peek().value == "=":
            self.advance()
            self.advance()
            return n.Assign(str(tok.value), self.expression(), tok.line)

        return n.ExprStmt(self.expression(), tok.line)

    def if_statement(self) -> n.If:
        tok = self.expect("kw", "if")
        cond = self.expression()
        then = self.block()
        otherwise = None
        if self.match("kw", "else"):
            if self.check("kw", "if"):
                otherwise = [self.if_statement()]
            else:
                otherwise = self.block()
        return n.If(cond, then, otherwise, tok.line)

    def block(self) -> list[n.Node]:
        self.expect("op", "{")
        body: list[n.Node] = []
        while not self.check("op", "}"):
            if self.check("eof"):
                raise Blocked("unterminated block", self.cur.line, self.cur.col)
            if self.match("op", ";"):
                continue
            body.append(self.statement())
        self.expect("op", "}")
        return body

    # --- expressions -----------------------------------------------------

    def expression(self, level: int = 0) -> n.Node:
        if level >= len(PRECEDENCE):
            return self.unary()
        left = self.expression(level + 1)
        while True:
            ops = PRECEDENCE[level]
            matched = None
            for op in ops:
                if self.check("op", op) or (
                    self.cur.kind == "kw" and self.cur.value == op
                ):
                    matched = op
                    break
            if matched is None:
                return left
            tok = self.advance()
            right = self.expression(level + 1)
            left = n.Binary(matched, left, right, tok.line)

    def unary(self) -> n.Node:
        if self.check("op", "-") or self.check("kw", "not"):
            tok = self.advance()
            op = "-" if tok.value == "-" else "not"
            return n.Unary(op, self.unary(), tok.line)
        return self.call()

    def call(self) -> n.Node:
        expr = self.primary()
        while self.check("op", "("):
            tok = self.advance()
            args: list[n.Node] = []
            if not self.check("op", ")"):
                while True:
                    args.append(self.expression())
                    if not self.match("op", ","):
                        break
            self.expect("op", ")")
            expr = n.Call(expr, args, tok.line)
        return expr

    def primary(self) -> n.Node:
        tok = self.cur
        if tok.kind == "num":
            self.advance()
            return n.Literal(tok.value, tok.line)
        if tok.kind == "str":
            self.advance()
            return n.Literal(tok.value, tok.line)
        if tok.kind == "kw" and tok.value in {"true", "false"}:
            self.advance()
            return n.Literal(tok.value == "true", tok.line)
        if tok.kind == "kw" and tok.value == "nil":
            self.advance()
            return n.Literal(None, tok.line)
        if tok.kind == "ident":
            self.advance()
            return n.Name(str(tok.value), tok.line)
        if tok.kind == "op" and tok.value == "(":
            self.advance()
            expr = self.expression()
            self.expect("op", ")")
            return expr
        if tok.kind == "op" and tok.value == "[":
            self.advance()
            items: list[n.Node] = []
            if not self.check("op", "]"):
                while True:
                    items.append(self.expression())
                    if not self.match("op", ","):
                        break
            self.expect("op", "]")
            return n.ListLiteral(items, tok.line)
        raise Blocked(
            f"unexpected {tok.kind} {tok.value!r}", tok.line, tok.col
        )


def parse(source: str) -> n.Program:
    return Parser(lex(source)).parse_program()
