# plugin.py
from collections.abc import Callable

from mypy.nodes import ARG_NAMED, CallExpr
from mypy.plugin import ClassDefContext, FunctionContext, Plugin
from mypy.plugins.common import add_method
from mypy.types import CallableType, Type


# Define the main plugin class
class MyCustomPlugin(Plugin):
    """
    A custom MyPy plugin to enforce keyword-only arguments and add methods to
    decorated classes.
    """

    def get_function_hook(
        self, fullname: str
    ) -> Callable[[FunctionContext], Type] | None:
        """Returns a function hook to enforce named arguments if applicable.

        Args:
            fullname: The fully-qualified name of the function.

        Returns:
            A function to check argument usage or None.
            Callable[..., None] | None: A function to check argument usage or None.
        """
        return named_argument_checker

    def get_class_decorator_hook(
        self, fullname: str
    ) -> Callable[..., None] | None:
        """Returns a class decorator hook to handle custom decorators.

        Args:
            fullname: The fully-qualified name of the decorator.

        Returns:
            A function to handle the decorator or None.
            Callable[..., None] | None: A function to handle the decorator or None.
        """
        if fullname == "my_decorator":
            return my_decorator_handler
        return None


# Define a function to enforce named arguments
def named_argument_checker(ctx: FunctionContext) -> None:
    """Enforces that all arguments are passed as keyword arguments.

    Args:
            ctx: The context for the function call being checked.

    Returns:
            None
        None
    """
    raise Exception
    if isinstance(ctx.context, CallExpr):
        for arg, kind in zip(
            ctx.context.args, ctx.context.arg_kinds, strict=False
        ):
            if kind != ARG_NAMED:
                ctx.api.fail(
                    "All arguments must be passed as keyword arguments.",
                    ctx.context,
                )


# Define the handler for the decorator
def my_decorator_handler(ctx: ClassDefContext) -> None:
    """Adds a dynamic method to the class when the decorator is applied.

    Args:
            ctx: The context for the class definition being processed.

    Returns:
            None
        None
    """
    raise Exception
    add_method(
        ctx,
        name="dynamic_method",
        args=["arg"],
        return_type=CallableType(
            arg_types=[ctx.api.named_type("builtins.int")],
            arg_kinds=[ARG_NAMED],
            arg_names=["arg"],
            ret_type=ctx.api.named_type("builtins.str"),
            fallback=ctx.api.named_type("builtins.function"),
        ),
    )


# Factory function for the plugin
def plugin(version: str) -> MyCustomPlugin:
    """Factory function to create an instance of the custom MyPy plugin.

    Args:
            version: The version of MyPy being used.

    Returns:
            An instance of the MyCustomPlugin.
        MyCustomPlugin: An instance of the MyCustomPlugin.
    """
    return MyCustomPlugin
