# mypy_pytest_plugin.py
import logging
from collections.abc import Callable

from mypy.nodes import (
    CallExpr,
    Decorator,
    Expression,
    FuncDef,
    ListExpr,
    StrExpr,
)
from mypy.plugin import FunctionContext, Plugin
from mypy.types import AnyType, TypeOfAny
from mypy.types import Type as MypyType

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class PytestPlugin(Plugin):
    def get_function_hook(
        self, fullname: str
    ) -> Callable[[FunctionContext], MypyType] | None:
        def hook(ctx: FunctionContext) -> MypyType:
            # Check if the function has decorators
            if not isinstance(ctx.context, Decorator):
                return ctx.default_return_type

            decorator = ctx.context
            func_name = getattr(decorator.func, "name", "<unnamed>")
            logger.debug(f"Analyzing function: {func_name}")

            for dec in decorator.decorators:
                # Check if decorator is pytest.mark.parametrize
                if isinstance(dec, CallExpr):
                    callee_fullname = self.get_fullname(dec.callee)
                    logger.debug(f"Found decorator: {callee_fullname}")
                    if "pytest.mark.parametrize" in callee_fullname:
                        self.check_parametrize(decorator.func, dec, ctx)
            return ctx.default_return_type

        return hook

    def check_parametrize(
        self, func_def: FuncDef, dec: CallExpr, ctx: FunctionContext
    ) -> None:
        func_name = getattr(func_def, "name", "<unnamed>")
        logger.debug(
            f"Checking parametrize decorator on function: {func_name}"
        )

        if len(dec.args) < 2:
            logger.debug("Not enough arguments to parametrize decorator")
            return

        param_names_expr = dec.args[0]
        param_values_expr = dec.args[1]

        # Extract parameter names
        if isinstance(param_names_expr, StrExpr):
            param_names = [
                name.strip() for name in param_names_expr.value.split(",")
            ]
        else:
            logger.debug("Parameter names are not a string")
            return

        # Extract parameter values
        param_values: list[Expression] = []
        if isinstance(param_values_expr, ListExpr):
            param_values.extend(param_values_expr.items)
        else:
            logger.debug("Parameter values are not a list")
            return

        # Map parameter names to their types
        param_types: dict[str, MypyType] = {}
        for name in param_names:
            # Get the type annotation of the parameter
            for arg in func_def.arguments:
                if arg.variable.name == name:
                    if arg.variable.type is not None:
                        param_types[name] = arg.variable.type
                    else:
                        logger.debug(
                            f"No type annotation for parameter: {name}"
                        )
                        param_types[name] = AnyType(TypeOfAny.special_form)
                    break
            else:
                logger.debug(
                    f"Parameter '{name}' not found in function definition"
                )
                param_types[name] = AnyType(TypeOfAny.special_form)

        # Now check each parameter value against its expected type
        for value_expr in param_values:
            if isinstance(value_expr, ListExpr):
                # Handle cases where values are tuples
                for i, item in enumerate(value_expr.items):
                    if i >= len(param_names):
                        logger.debug(
                            f"Index {i} out of range for parameter names"
                        )
                        continue
                    param_name = param_names[i]
                    expected_type = param_types.get(
                        param_name, AnyType(TypeOfAny.special_form)
                    )
                    actual_type = ctx.api.expr_checker.accept(item)
                    if not ctx.api.expr_checker.check_subtype(
                        actual_type, expected_type, ctx.context, msg=None
                    ):
                        ctx.api.msg.fail(
                            f"Incompatible type for parameter '{param_name}': "
                            f"expected {expected_type}, got {actual_type}",
                            ctx.context,
                        )
                        logger.debug(
                            f"Type mismatch for '{param_name}': expected {expected_type}, got {actual_type}"
                        )
            else:
                # Single parameter
                param_name = param_names[0]
                expected_type = param_types.get(
                    param_name, AnyType(TypeOfAny.special_form)
                )
                actual_type = ctx.api.expr_checker.accept(value_expr)
                if not ctx.api.expr_checker.check_subtype(
                    actual_type, expected_type, ctx.context, msg=None
                ):
                    ctx.api.msg.fail(
                        f"Incompatible type for parameter '{param_name}': "
                        f"expected {expected_type}, got {actual_type}",
                        ctx.context,
                    )
                    logger.debug(
                        f"Type mismatch for '{param_name}': expected {expected_type}, got {actual_type}"
                    )

    def get_fullname(self, expr: Expression) -> str:
        """
        Helper method to get the fullname of an expression.
        """
        if hasattr(expr, "fullname") and expr.fullname:
            return expr.fullname
        if hasattr(expr, "name") and expr.name:
            return expr.name
        return ""


def plugin(version: str) -> type["PytestPlugin"]:
    assert version
    return PytestPlugin
