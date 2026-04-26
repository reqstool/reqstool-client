# Copyright © LFV


from dataclasses import dataclass


@dataclass(frozen=True)
class ParsingConfig:
    include_line_numbers: bool = False
