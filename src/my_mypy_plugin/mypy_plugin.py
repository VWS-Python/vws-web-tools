from __future__ import annotations

from collections.abc import Callable

from mypy.nodes import (
    ARG_NAMED,
    ARG_NAMED_OPT,
    ARG_OPT,
    ARG_POS,
    ArgKind,
)
from mypy.plugin import FunctionSigContext, Plugin
from mypy.types import CallableType


class KeywordOnlyPlugin(Plugin):
    def get_function_signature_hook(
        self, fullname: str
    ) -> Callable[[FunctionSigContext], CallableType] | None:
        """
        Transform the function signature to use keyword-only arguments.
        """

        def transform_function_signature(
            ctx: FunctionSigContext,
        ) -> CallableType:
            original_sig: CallableType = ctx.default_signature
            new_arg_kinds: list[ArgKind] = []

            for kind in original_sig.arg_kinds:
                if kind == ARG_POS:
                    new_arg_kinds.append(ARG_NAMED)
                elif kind == ARG_OPT:
                    new_arg_kinds.append(ARG_NAMED_OPT)
                else:
                    new_arg_kinds.append(kind)

            return original_sig.copy_modified(arg_kinds=new_arg_kinds)

        return transform_function_signature


def plugin(version: str) -> type[KeywordOnlyPlugin]:
    return KeywordOnlyPlugin
