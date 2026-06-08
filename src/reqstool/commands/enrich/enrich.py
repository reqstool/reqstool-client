# Copyright © LFV

from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.enrichment.enricher import EnrichmentConfig, enrich_text
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.storage.pipeline import build_database
from reqstool.storage.requirements_repository import RequirementsRepository


@Requirements("ENRICH_0001", "ENRICH_0002")
class EnrichCommand:
    def __init__(self, location: LocationInterface, input_content: str, config: EnrichmentConfig):
        self.__initial_location: LocationInterface = location
        self.__input_content: str = input_content
        self.__config: EnrichmentConfig = config
        self.result: str = self.__run()

    def __run(self) -> str:
        with build_database(
            location=self.__initial_location,
            semantic_validator=SemanticValidator(validation_error_holder=ValidationErrorHolder()),
        ) as (db, _):
            repo = RequirementsRepository(db)
            requirements = repo.get_all_requirements()
            svcs = repo.get_all_svcs()
            mvrs = repo.get_all_mvrs()
        return enrich_text(self.__input_content, requirements, svcs, mvrs, self.__config)
