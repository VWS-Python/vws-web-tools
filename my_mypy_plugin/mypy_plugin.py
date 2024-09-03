"""mypy plugin to find positional uses where keyword arguments are allowed."""

from collections.abc import Callable

from mypy.nodes import (
    ARG_POS,
    ArgKind,
    CallExpr,
    FuncDef,
    NameExpr,
    SymbolTableNode,
)
from mypy.plugin import FunctionContext, Plugin
from mypy.types import CallableType, Type


class _KeywordOnlyArgumentsPlugin(Plugin):
    def get_function_hook(
        self, fullname: str
    ) -> Callable[[FunctionContext], Type] | None:
        """Return the hook for function definitions."""
        assert fullname
        return _keyword_only_argument_checker


def _keyword_only_argument_checker(ctx: FunctionContext) -> Type:
    # Ensure the function being called is a defined function
    if not isinstance(ctx.context, CallExpr):
        return ctx.default_return_type

    call_expr: CallExpr = ctx.context
    if not isinstance(call_expr.callee, NameExpr):
        return ctx.default_return_type

    # Attempt to lookup the callee in the symbol table
    try:
        callee_node: SymbolTableNode | None = ctx.api.lookup_qualified(
            call_expr.callee.name
        )
    except KeyError:
        return ctx.default_return_type

    if not callee_node or not isinstance(callee_node.node, FuncDef):
        return ctx.default_return_type

    # Get the callable type and ensure it's not None
    func_def: FuncDef = callee_node.node
    callable_type: CallableType | Type | None = func_def.type

    # If the type is not resolved, return the default return type
    if callable_type is None or not isinstance(callable_type, CallableType):
        return ctx.default_return_type

    # Check the arguments passed
    arg_kinds: list[ArgKind] = callable_type.arg_kinds
    arg_names: list[str | None] = callable_type.arg_names

    for i, (arg_kind, arg_name) in enumerate(
        zip(arg_kinds, arg_names, strict=False)
    ):
        if arg_kind == ARG_POS and arg_name is None:
            # Skip positional-only arguments
            continue

        # Check if the argument was passed positionally
        if i < len(call_expr.args) and call_expr.arg_kinds[i] == ARG_POS:
            ctx.api.fail(
                msg=(
                    f"Argument '{arg_name}' should be passed as a "
                    "keyword argument"
                ),
                ctx=call_expr.args[i],
            )

    return ctx.default_return_type


def plugin(version: str) -> type[Plugin]:
    """Return the plugin class."""
    assert version
    return _KeywordOnlyArgumentsPlugin
