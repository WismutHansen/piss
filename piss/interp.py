"""The runtime.

One semantic rule is enforced here that no other toy language has: bindings
evaporate. A binding that is not read within `decay` statements is stale water,
and reading it is a fault. Use it or lose it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import nodes as n
from .errors import Burst, Evaporated, Splash


@dataclass
class Binding:
    value: Any
    touched: int


class Env:
    def __init__(self, parent: "Env | None" = None):
        self.vars: dict[str, Binding] = {}
        self.parent = parent

    def define(self, name: str, value: Any, clock: int) -> None:
        self.vars[name] = Binding(value, clock)

    def get(self, name: str, clock: int, decay: int) -> Any:
        env: Env | None = self
        while env is not None:
            if name in env.vars:
                binding = env.vars[name]
                if decay > 0 and clock - binding.touched > decay:
                    raise Evaporated(name, binding.touched, clock, decay)
                binding.touched = clock  # re-wet on use
                return binding.value
            env = env.parent
        raise Burst(f"`{name}` is not in a puddle (never bound)")

    def assign(self, name: str, value: Any, clock: int) -> None:
        env: Env | None = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = Binding(value, clock)
                return
            env = env.parent
        raise Burst(f"cannot assign to `{name}`: it was never bound")


class Return(Exception):
    def __init__(self, value: Any):
        self.value = value


@dataclass
class Valve:
    name: str
    params: list[str]
    body: list[n.Node]
    closure: Env


BUILTINS: dict[str, Callable[["Interpreter", list[Any]], Any]] = {}


def builtin(name: str):
    def register(fn):
        BUILTINS[name] = fn
        return fn

    return register


@builtin("len")
def _len(interp, args):
    _arity("len", args, 1)
    value = args[0]
    if isinstance(value, (str, list)):
        return len(value)
    raise Burst(f"len() wants a string or a list, got {type(value).__name__}")


@builtin("str")
def _str(interp, args):
    _arity("str", args, 1)
    return interp.stringify(args[0])


@builtin("num")
def _num(interp, args):
    _arity("num", args, 1)
    value = args[0]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                raise Burst(f"num() cannot read {value!r}") from None
    raise Burst(f"num() wants a number or a numeric string, got {type(value).__name__}")


@builtin("range")
def _range(interp, args):
    if len(args) == 1:
        start, stop = 0, args[0]
    elif len(args) == 2:
        start, stop = args
    else:
        raise Burst("range() takes one or two arguments")
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in (start, stop)):
        raise Burst("range() wants integers")
    return list(range(start, stop))


@builtin("push")
def _push(interp, args):
    _arity("push", args, 2)
    target, value = args
    if not isinstance(target, list):
        raise Burst("push() wants a list")
    target.append(value)
    return target


def _arity(name: str, args: list[Any], expected: int) -> None:
    if len(args) != expected:
        raise Burst(f"{name}() takes {expected} argument(s), got {len(args)}")


class Interpreter:
    def __init__(self, decay: int = 6, out=None):
        self.decay = decay
        self.clock = 0
        self.globals = Env()
        self.out = out
        self.output: list[str] = []

    # --- output ----------------------------------------------------------

    def emit(self, text: str) -> None:
        self.output.append(text)
        if self.out is not None:
            self.out.write(text + "\n")

    def stringify(self, value: Any) -> str:
        if value is None:
            return "nil"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if isinstance(value, list):
            return "[" + ", ".join(self.stringify(v) for v in value) + "]"
        if isinstance(value, Valve):
            return f"<valve {value.name}>"
        if callable(value):
            return "<builtin>"
        return str(value)

    # --- entry -----------------------------------------------------------

    def run(self, program: n.Program) -> Any:
        try:
            self.exec_block(program.body, self.globals)
        except Return as ret:
            return ret.value
        except Splash as splash:
            raise splash
        return None

    # --- statements ------------------------------------------------------

    def exec_block(self, body: list[n.Node], env: Env) -> None:
        for stmt in body:
            self.clock += 1
            self.exec_stmt(stmt, env)

    def exec_stmt(self, stmt: n.Node, env: Env) -> None:
        if isinstance(stmt, n.Puddle):
            env.define(stmt.name, self.eval(stmt.value, env), self.clock)
            return

        if isinstance(stmt, n.Assign):
            env.assign(stmt.name, self.eval(stmt.value, env), self.clock)
            return

        if isinstance(stmt, n.Leak):
            self.emit(self.stringify(self.eval(stmt.value, env)))
            return

        if isinstance(stmt, n.ExprStmt):
            self.eval(stmt.expr, env)
            return

        if isinstance(stmt, n.If):
            if self.truthy(self.eval(stmt.cond, env)):
                self.exec_block(stmt.then, Env(env))
            elif stmt.otherwise is not None:
                self.exec_block(stmt.otherwise, Env(env))
            return

        if isinstance(stmt, n.Drain):
            iterable = self.eval(stmt.iterable, env)
            if isinstance(iterable, str):
                items: list[Any] = list(iterable)
            elif isinstance(iterable, list):
                items = list(iterable)
            else:
                raise Burst(
                    f"drain wants something to pour out, got {type(iterable).__name__}"
                )
            for item in items:
                local = Env(env)
                local.define(stmt.var, item, self.clock)
                self.exec_block(stmt.body, local)
            return

        if isinstance(stmt, n.Valve):
            env.define(stmt.name, Valve(stmt.name, stmt.params, stmt.body, env), self.clock)
            return

        if isinstance(stmt, n.Flush):
            value = None if stmt.value is None else self.eval(stmt.value, env)
            raise Return(value)

        if isinstance(stmt, n.Splash):
            value = None if stmt.value is None else self.eval(stmt.value, env)
            raise Splash(value)

        raise Burst(f"cannot execute {type(stmt).__name__}")

    # --- expressions -----------------------------------------------------

    def eval(self, expr: n.Node, env: Env) -> Any:
        if isinstance(expr, n.Literal):
            return expr.value

        if isinstance(expr, n.ListLiteral):
            return [self.eval(item, env) for item in expr.items]

        if isinstance(expr, n.Name):
            try:
                return env.get(expr.name, self.clock, self.decay)
            except Burst:
                if expr.name in BUILTINS:
                    return BUILTINS[expr.name]
                raise

        if isinstance(expr, n.Unary):
            value = self.eval(expr.operand, env)
            if expr.op == "-":
                if not _is_number(value):
                    raise Burst(f"cannot negate {type(value).__name__}")
                return -value
            return not self.truthy(value)

        if isinstance(expr, n.Binary):
            return self.binary(expr, env)

        if isinstance(expr, n.Call):
            callee = self.eval(expr.callee, env)
            args = [self.eval(arg, env) for arg in expr.args]
            return self.call(callee, args)

        raise Burst(f"cannot evaluate {type(expr).__name__}")

    def binary(self, expr: n.Binary, env: Env) -> Any:
        op = expr.op

        if op == "and":
            left = self.eval(expr.left, env)
            if not self.truthy(left):
                return left
            return self.eval(expr.right, env)
        if op == "or":
            left = self.eval(expr.left, env)
            if self.truthy(left):
                return left
            return self.eval(expr.right, env)

        left = self.eval(expr.left, env)
        right = self.eval(expr.right, env)

        if op == "==":
            return left == right
        if op == "!=":
            return left != right

        if op in {"<", "<=", ">", ">="}:
            if _is_number(left) and _is_number(right):
                pass
            elif isinstance(left, str) and isinstance(right, str):
                pass
            else:
                raise Burst(f"cannot compare {type(left).__name__} and {type(right).__name__}")
            return {
                "<": left < right,
                "<=": left <= right,
                ">": left > right,
                ">=": left >= right,
            }[op]

        if op == "+":
            if _is_number(left) and _is_number(right):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            raise Burst(f"cannot add {type(left).__name__} and {type(right).__name__}")

        if not (_is_number(left) and _is_number(right)):
            raise Burst(f"cannot {op} {type(left).__name__} and {type(right).__name__}")

        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise Burst("division by zero: the pipe burst")
            return left / right
        if op == "%":
            if right == 0:
                raise Burst("modulo by zero: the pipe burst")
            return left % right

        raise Burst(f"unknown operator {op}")

    def call(self, callee: Any, args: list[Any]) -> Any:
        if callable(callee) and not isinstance(callee, Valve):
            return callee(self, args)
        if isinstance(callee, Valve):
            if len(args) != len(callee.params):
                raise Burst(
                    f"valve {callee.name} takes {len(callee.params)} argument(s), got {len(args)}"
                )
            local = Env(callee.closure)
            for name, value in zip(callee.params, args):
                local.define(name, value, self.clock)
            try:
                self.exec_block(callee.body, local)
            except Return as ret:
                return ret.value
            return None
        raise Burst(f"{type(callee).__name__} is not callable")

    # --- misc ------------------------------------------------------------

    @staticmethod
    def truthy(value: Any) -> bool:
        if value is None or value is False:
            return False
        if value is True:
            return True
        if _is_number(value):
            return value != 0
        if isinstance(value, (str, list)):
            return len(value) > 0
        return True


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
