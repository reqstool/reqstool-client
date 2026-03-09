# Copyright © LFV

from reqstool.location_resolver.location_resolver import LocationResolver


class ImplementationDataInterface(LocationResolver):
    pass


class GitImplData(ImplementationDataInterface):
    pass


class LocalImplData(ImplementationDataInterface):
    pass


class MavenImplData(ImplementationDataInterface):
    pass


class PypiImplData(ImplementationDataInterface):
    pass
