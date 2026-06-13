# Copyright © LFV

import os

from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.location_resolver.location_resolver import LocationResolver
from reqstool.locations.local_location import LocalLocation


@SVCs("SVC_SOURCE_0001")
def test_make_available_on_localdisk_materializes_local_source(tmp_path, local_testdata_resources_rootdir_w_path):
    """SOURCE_0001: the resolved source is made available on local disk before parsing."""
    src_path = local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101")
    dst_path = tmp_path / "materialized"
    dst_path.mkdir()

    resolver = LocationResolver(current_unresolved=LocalLocation(path=src_path))
    result = resolver.make_available_on_localdisk(dst_path=str(dst_path))

    assert os.path.isfile(os.path.join(result, "requirements.yml"))
