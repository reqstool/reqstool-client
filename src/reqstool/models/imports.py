# Copyright © LFV

from reqstool.location_resolver.location_resolver import LocationResolver


class ImportDataInterface(LocationResolver):
    pass


class GitImportData(ImportDataInterface):
    pass


class LocalImportData(ImportDataInterface):
    pass


class MavenImportData(ImportDataInterface):
    pass


class PypiImportData(ImportDataInterface):
    pass
