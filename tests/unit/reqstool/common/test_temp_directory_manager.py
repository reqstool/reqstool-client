from reqstool.common.utils import TempDirectoryManager


def test_get_suffix_path_returns_unique_paths():
    with TempDirectoryManager() as mgr:
        p1 = mgr.get_suffix_path("test")
        p2 = mgr.get_suffix_path("test")
        assert p1 != p2
        assert p1.exists()
        assert p2.exists()


def test_cleanup_removes_directory():
    mgr = TempDirectoryManager()
    path = mgr.get_path()
    assert path.exists()
    mgr.cleanup()
    assert not path.exists()


def test_context_manager_cleans_up():
    with TempDirectoryManager() as mgr:
        path = mgr.get_path()
        assert path.exists()
    assert not path.exists()


def test_two_instances_are_independent():
    with TempDirectoryManager() as mgr1:
        with TempDirectoryManager() as mgr2:
            assert mgr1.get_path() != mgr2.get_path()
