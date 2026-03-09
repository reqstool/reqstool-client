from typing import List

from pydantic import BaseModel


class ValidationError(BaseModel):
    msg: str


class ValidationErrorHolder:
    errors = []

    def __init__(self) -> None:
        self.errors = []

    def add_error(self, error: ValidationError):
        self.errors.append(error)

    def add_errors(self, errors: List[ValidationError]):
        for error in errors:
            self.add_error(error=error)

    def get_errors(self) -> List[ValidationError]:
        return self.errors

    def get_no_of_errors(self) -> int:
        return len(self.errors)
