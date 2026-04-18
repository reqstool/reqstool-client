# Copyright © LFV


import re

from lark import Transformer, v_args

from reqstool.common.models.urn_id import UrnId
from reqstool.expression_languages.generic_el_transformer import GenericELTransformer


class ELToSQLCompiler(Transformer):
    """Compiles a Lark EL parse tree into a SQL WHERE clause with parameters."""

    def __init__(self, urn: str) -> None:
        super().__init__(True)
        self._urn = urn

    def start(self, args) -> tuple[str, list]:
        return args[0]

    @v_args(inline=True)
    def op_and(self, left, right) -> tuple[str, list]:
        left_sql, left_params = left
        right_sql, right_params = right
        return f"({left_sql} AND {right_sql})", left_params + right_params

    @v_args(inline=True)
    def op_or(self, left, right) -> tuple[str, list]:
        left_sql, left_params = left
        right_sql, right_params = right
        return f"({left_sql} OR {right_sql})", left_params + right_params

    @v_args(inline=True)
    def op_not(self, operand) -> tuple[str, list]:
        sql, params = operand
        return f"(NOT {sql})", params

    @v_args(inline=True)
    def comp_id_equals(self, items) -> tuple[str, list]:
        urn_ids: list[UrnId] = items
        placeholders = ", ".join(["(?, ?)" for _ in urn_ids])
        params = []
        for uid in urn_ids:
            params.extend([uid.urn, uid.id])
        return f"((urn, id) IN (VALUES {placeholders}))", params

    @v_args(inline=True)
    def comp_id_not_equals(self, items) -> tuple[str, list]:
        urn_ids: list[UrnId] = items
        placeholders = ", ".join(["(?, ?)" for _ in urn_ids])
        params = []
        for uid in urn_ids:
            params.extend([uid.urn, uid.id])
        return f"((urn, id) NOT IN (VALUES {placeholders}))", params

    @v_args(inline=True)
    def comp_id_regex_equals(self, pattern_str: str) -> tuple[str, list]:
        return "(regexp(?, urn || ':' || id))", [pattern_str]

    def parenthesis(self, operands) -> tuple[str, list]:
        return operands[0]

    def value(self, item) -> UrnId:
        return UrnId.assure_urn_id(urn=self._urn, id=item[0])

    def value_list(self, items) -> list[UrnId]:
        return items

    @v_args(inline=True)
    def regex(self, regexp) -> str:
        return regexp[1:-1]

    def STRING(self, token) -> str:
        return token[1:-1].replace('\\"', '"').replace("\\'", "'")

    @staticmethod
    def compile(expression: str, urn: str) -> tuple[str, list]:
        tree = GenericELTransformer.parse_el(expression)
        compiler = ELToSQLCompiler(urn=urn)
        return compiler.transform(tree)


def regexp_function(pattern: str, value: str) -> bool:
    """SQLite REGEXP function implementation."""
    try:
        return bool(re.search(pattern, value))
    except re.error:
        return False
