from __future__ import annotations

import ast
import types
from dataclasses import dataclass
from functools import reduce
from typing import Any, Callable

from ...utils import InnerError, log, log_do

Guard = Callable[[types.FrameType], bool]

# NOTE(SigureMo): [How to write Stringify Guard?]
# 1. we should capture free variables manually, the string cannot capture free
#    variables automatically.
# 2. Be aware that the comparison logic before and after stringify may be different.
# 3. we should compute as much as possible at "compile time" and encode the
#    computation in the Guard string, rather than passing it to runtime to minimize
#    runtime overhead.


@dataclass
class StringifyExpression:
    expr: str
    free_vars: dict[str, Any]

    def __post_init__(self):
        self.check_expr(self.expr)

    def check_expr(self, expr: str):
        try:
            ast.parse(expr)
        except SyntaxError as e:
            raise InnerError(f"Invalid expression: {expr}") from e

    def __and__(self, other: StringifyExpression) -> StringifyExpression:
        return StringifyExpression(
            " and ".join([self.expr, other.expr]),
            union_free_vars(self.free_vars, other.free_vars),
        )


def union_free_vars(*free_vars: dict[str, Any]):
    return {k: v for d in free_vars for k, v in d.items()}


def make_guard(stringify_guards: list[StringifyExpression]) -> Guard:
    num_guards = len(stringify_guards)
    if not num_guards:
        guard = lambda frame: True
        guard.expr = "lambda frame: True"
        return guard

    union_guard_expr = reduce(lambda x, y: x & y, stringify_guards)
    guard_string = f"lambda frame: {union_guard_expr.expr}"
    guard = eval(
        guard_string,
        union_guard_expr.free_vars,
    )
    log(3, f"[Guard]: {guard_string}\n")
    guard.expr = guard_string
    assert callable(guard), "guard must be callable."

    return guard


def object_equal_stringify_guard(self) -> StringifyExpression:
    assert (
        self.tracker.is_traceable()
    ), "Cannot make guard from a non-traceable variable."

    frame_value_tracer = self.tracker.trace_value_from_frame()
    log_do(
        4,
        lambda: print(
            f"[Guard]: guard_fn for {self}, tracker={self.tracker.__class__.__name__}, value={frame_value_tracer.expr}"
        ),
    )
    obj_free_var_name = f"__{self.id}"
    return StringifyExpression(
        f"{frame_value_tracer.expr} == {obj_free_var_name}",
        union_free_vars(
            frame_value_tracer.free_vars,
            {obj_free_var_name: self.get_value()},
        ),
    )
