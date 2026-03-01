# Copyright © LFV


import re
from enum import Enum

import jsonpickle
from packaging.version import Version
from reqstool_python_decorators.decorators.decorators import Requirements

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LOCATIONTYPES, LocationInterface
from reqstool.model_generators.combined_indexed_dataset_generator import CombinedIndexedDatasetGenerator
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.models.raw_datasets import CombinedRawDataset
from reqstool.models.requirements import CATEGORIES, SIGNIFANCETYPES, TYPES, VARIANTS
from reqstool.models.svcs import VERIFICATIONTYPES
from reqstool.models.test_data import TEST_RUN_STATUS


class UrnIdHandler(jsonpickle.handlers.BaseHandler):
    def flatten(self, obj, data) -> str:
        return str(UrnId.assure_urn_id(obj.urn, obj.id))


class RevisionHandler(jsonpickle.handlers.BaseHandler):
    def flatten(self, obj, data):
        version: Version = obj
        return {"major": version.major, "minor": version.minor, "patch": version.micro}


class JsonEnumHandler(jsonpickle.handlers.BaseHandler):
    def flatten(self, obj: Enum, data):
        return obj.value


@Requirements("REQ_030")
class GenerateJsonCommand:
    def __init__(self, location: LocationInterface, filter_data: bool):
        self.__initial_location: LocationInterface = location
        self.__filter_data: bool = filter_data
        self.result = self.__run()

    def __run(self) -> str:
        """Generates The imported models as raw JSON

        Returns:
            str: The imported models as raw JSON.
        """
        holder = ValidationErrorHolder()
        semantic_validator = SemanticValidator(validation_error_holder=holder)
        combined_raw_datasets: CombinedRawDataset = CombinedRawDatasetsGenerator(
            initial_location=self.__initial_location, semantic_validator=semantic_validator
        ).combined_raw_datasets

        cids = CombinedIndexedDatasetGenerator(
            _crd=combined_raw_datasets, _filtered=self.__filter_data
        ).combined_indexed_dataset

        # Register the custom handler for enumerations

        jsonpickle.handlers.registry.register(UrnId, UrnIdHandler)
        jsonpickle.handlers.registry.register(Version, RevisionHandler)
        jsonpickle.handlers.registry.register(CATEGORIES, JsonEnumHandler)
        jsonpickle.handlers.registry.register(LOCATIONTYPES, JsonEnumHandler)
        jsonpickle.handlers.registry.register(SIGNIFANCETYPES, JsonEnumHandler)
        jsonpickle.handlers.registry.register(TYPES, JsonEnumHandler)
        jsonpickle.handlers.registry.register(VARIANTS, JsonEnumHandler)
        jsonpickle.handlers.registry.register(VERIFICATIONTYPES, JsonEnumHandler)
        jsonpickle.handlers.registry.register(TEST_RUN_STATUS, JsonEnumHandler)

        json_data = jsonpickle.encode(cids, make_refs=False, keys=True, unpicklable=False)

        # Regular expression pattern to match the given format
        pattern = r'json://\\"(.*?)\\"'

        # Replacement using regex
        json_data = re.sub(pattern, r"\1", json_data)

        return json_data
