# Copyright © LFV

import re
from typing import List, Tuple

from lark import Transformer, v_args

from reqstool.common.models.urn_id import UrnId
from reqstool.expression_languages.generic_el import GenericELTransformer


class ELToSQLCompiler(Transformer):
    """Compiles a Lark EL parse tree into a SQL WHERE clause with parameters."""

    def __init__(self, urn: str) -> None:
        super().__init__(True)
        self._urn = urn

    def start(self, args) -> Tuple[str, List]:
        return args[0]

    @v_args(inline=True)
    def op_and(self, left, right) -> Tuple[str, List]:
        left_sql, left_params = left
        right_sql, right_params = right
        return f"({left_sql} AND {right_sql})", left_params + right_params

    @v_args(inline=True)
    def op_or(self, left, right) -> Tuple[str, List]:
        left_sql, left_params = left
        right_sql, right_params = right
        return f"({left_sql} OR {right_sql})", left_params + right_params

    @v_args(inline=True)
    def op_not(self, operand) -> Tuple[str, List]:
        sql, params = operand
        return f"(NOT {sql})", params

    @v_args(inline=True)
    def comp_id_equals(self, items) -> Tuple[str, List]:
        urn_ids: List[UrnId] = items
        placeholders = ", ".join(["(?, ?)" for _ in urn_ids])
        params = []
        for uid in urn_ids:
            params.extend([uid.urn, uid.id])
        return f"((urn, id) IN (VALUES {placeholders}))", params

    @v_args(inline=True)
    def comp_id_not_equals(self, items) -> Tuple[str, List]:
        urn_ids: List[UrnId] = items
        placeholders = ", ".join(["(?, ?)" for _ in urn_ids])
        params = []
        for uid in urn_ids:
            params.extend([uid.urn, uid.id])
        return f"((urn, id) NOT IN (VALUES {placeholders}))", params

    @v_args(inline=True)
    def comp_id_regex_equals(self, pattern_str: str) -> Tuple[str, List]:
        return "(regexp(?, urn || ':' || id))", [pattern_str]

    def parenthesis(self, operands) -> Tuple[str, List]:
        return operands[0]

    def value(self, item) -> UrnId:
        return UrnId.assure_urn_id(urn=self._urn, id=item[0])

    def value_list(self, items) -> List[UrnId]:
        return items

    @v_args(inline=True)
    def regex(self, regexp) -> str:
        return regexp[1:-1]

    def STRING(self, token) -> str:
        return token[1:-1].replace('\\"', '"').replace("\\'", "'")

    @staticmethod
    def compile(expression: str, urn: str) -> Tuple[str, List]:
        tree = GenericELTransformer.parse_el(expression)
        compiler = ELToSQLCompiler(urn=urn)
        return compiler.transform(tree)


def regexp_function(pattern: str, value: str) -> bool:
    """SQLite REGEXP function implementation."""
    return bool(re.search(pattern, value))
