"""Turn text into tokens. Comments start with `#` and run to end of line."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import Blocked

KEYWORDS = {
    "puddle",  # bind
    "leak",  # print
    "if",
    "else",
    "drain",  # iterate
    "valve",  # function
    "flush",  # return
    "splash",  # raise
    "true",
    "false",
    "nil",
    "and",
    "or",
    "not",
    # recognised so we can refuse it with a better message
    "while",
    "for",
}

TWO_CHAR = {"==", "!=", "<=", ">="}
ONE_CHAR = set("+-*/%(){}[],=<>:")


@dataclass(frozen=True)
class Token:
    kind: str  # "num", "str", "ident", "kw", "op", "eof"
    value: object
    line: int
    col: int

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return f"{self.kind}:{self.value!r}@{self.line}:{self.col}"


def lex(source: str) -> list[Token]:
    tokens: list[Token] = []
    line, col = 1, 1
    i, n = 0, len(source)

    def advance(k: int = 1) -> None:
        nonlocal i, col
        i += k
        col += k

    while i < n:
        ch = source[i]

        if ch == "\n":
            i += 1
            line += 1
            col = 1
            continue
        if ch in " \t\r":
            advance()
            continue
        if ch == "#":
            while i < n and source[i] != "\n":
                advance()
            continue

        start_line, start_col = line, col

        # numbers
        if ch.isdigit():
            j = i
            while j < n and source[j].isdigit():
                j += 1
            if j < n and source[j] == "." and j + 1 < n and source[j + 1].isdigit():
                j += 1
                while j < n and source[j].isdigit():
                    j += 1
                text = source[i:j]
                tokens.append(Token("num", float(text), start_line, start_col))
            else:
                text = source[i:j]
                tokens.append(Token("num", int(text), start_line, start_col))
            advance(j - i)
            continue

        # strings
        if ch in "\"'":
            quote = ch
            advance()
            buf: list[str] = []
            while True:
                if i >= n:
                    raise Blocked("unterminated string", start_line, start_col)
                c = source[i]
                if c == "\\":
                    if i + 1 >= n:
                        raise Blocked("unterminated escape", line, col)
                    esc = source[i + 1]
                    buf.append({"n": "\n", "t": "\t", "\\": "\\", quote: quote}.get(esc, esc))
                    advance(2)
                    continue
                if c == quote:
                    advance()
                    break
                buf.append(c)
                advance()
            tokens.append(Token("str", "".join(buf), start_line, start_col))
            continue

        # identifiers and keywords
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (source[j].isalnum() or source[j] == "_"):
                j += 1
            word = source[i:j]
            kind = "kw" if word in KEYWORDS else "ident"
            tokens.append(Token(kind, word, start_line, start_col))
            advance(j - i)
            continue

        # operators
        pair = source[i : i + 2]
        if pair in TWO_CHAR:
            tokens.append(Token("op", pair, start_line, start_col))
            advance(2)
            continue
        if ch in ONE_CHAR:
            tokens.append(Token("op", ch, start_line, start_col))
            advance()
            continue

        raise Blocked(f"unexpected character {ch!r}", start_line, start_col)

    tokens.append(Token("eof", None, line, col))
    return tokens
