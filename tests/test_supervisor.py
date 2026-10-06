"""Unit test for sovereign mesh process supervisor."""

from core.mesh.mesh_supervisor import get_pids

def test_get_pids_nonexistent():
    pids = get_pids("nonexistent_supervisor_proc_xyz_99")
    assert isinstance(pids, list)
    assert len(pids) == 0

def test_get_pids_discovery():
    # Discover running python processes
    pids = get_pids("python3")
    assert isinstance(pids, list)
    assert len(pids) > 0
