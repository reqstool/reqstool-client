# Copyright © LFV

import re
from typing import Generic, TypeVar

from lark import Lark, ParseTree, Transformer, v_args

from reqstool.common.dataclasses.urn_id import UrnId

T = TypeVar("T")


class GenericELTransformer(
    Transformer,
    Generic[T],
):
    _data: T
    _urn: str

    _GRAMMAR = """
    start: expr

    ?expr: expr "or" expr         -> op_or
        | expr "and" expr         -> op_and
        | "not" expr              -> op_not
        | term

    term: "ids ==" value_list   -> comp_id_equals
        | "ids !=" value_list   -> comp_id_not_equals
        | "ids ==" regex        -> comp_id_regex_equals
        | "(" expr ")"          -> parenthesis

    value_list: value ("," value)* -> value_list

    value: STRING

    regex: REGEXP_STRING

    REGEXP_STRING: "/" _STRING_ESC_INNER "/"

    %import common._STRING_ESC_INNER -> _STRING_ESC_INNER
    %import common.ESCAPED_STRING    -> STRING
    %import common.WS
    %ignore WS
    """

    def __init__(
        self,
        urn: str,
        data: T,
    ) -> None:
        super().__init__(True)
        self._urn = urn
        self._data = data

    def start(self, args) -> bool:
        return args[0]

    @v_args(inline=True)
    def op_and(self, operand_l, operand_r) -> bool:
        return operand_l and operand_r

    @v_args(inline=True)
    def op_or(self, operand_l, operand_r) -> bool:
        return operand_l or operand_r

    @v_args(inline=True)
    def op_not(self, operand) -> bool:
        return not operand

    @v_args(inline=True)
    def comp_id_equals(self, items) -> bool:
        return self._data.id in items

    @v_args(inline=True)
    def comp_id_not_equals(self, items) -> bool:
        return self._data.id not in items

    @v_args(inline=True)
    def comp_id_regex_equals(self, regexp: re.Pattern) -> bool:
        return bool(regexp.match(str(self._data.id)))

    def parenthesis(self, operands) -> bool:
        return operands[0]

    def value(self, item) -> UrnId:
        urnid_item = UrnId.assure_urn_id(urn=self._urn, id=item[0])
        return urnid_item

    def value_list(self, items) -> list:
        return items

    @v_args(inline=True)
    def regex(self, regexp) -> re.Pattern:
        return re.compile(regexp[1:-1])

    def STRING(self, token) -> str:
        return token[1:-1].replace('\\"', '"').replace("\\'", "'")

    @staticmethod
    def parse_el(expression_language: str) -> ParseTree:
        parser = Lark(GenericELTransformer._GRAMMAR, parser="lalr")

        tree = parser.parse(expression_language)

        return tree
