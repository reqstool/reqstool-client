# Copyright © LFV


from reqstool.locations.local_location import LocalLocation
from reqstool_python_decorators.decorators.decorators import SVCs


@SVCs("SVC_SOURCE_0002")
def test_local_location(resource_funcname_rootdir_w_path):
    PATH = "/tmp/somepath"

    local_location = LocalLocation(path=PATH)

    assert local_location.path == PATH
