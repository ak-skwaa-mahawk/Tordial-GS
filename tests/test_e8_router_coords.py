"""Unit tests for coordinate injection in E8GeodesicRouter."""

from unittest.mock import patch
from core.mesh.e8_router import E8GeodesicRouter
from core.mesh.e8_polytope import get_root_vector

@patch("core.mesh.cloud_offload.CloudOffloadEngine.put_state")
@patch("core.mesh.gemini_bridge.GeminiBridge.query")
def test_evaluate_vector_contains_coords(mock_query, mock_put):
    mock_query.return_value = {
        "success": True,
        "content": "STATUS: ROUTE_STABLE\nAll roots within nominal envelope.",
        "model": "gemini-3.5-flash-lite"
    }
    mock_put.return_value = {"success": True, "target": "mock_target"}

    router = E8GeodesicRouter()
    res = router.evaluate_vector(root_index=12, phase_drift=0.0, lyapunov=-6.992)

    assert res["success"] is True
    assert "root_coords" in res
    assert res["root_coords"] == get_root_vector(12)
    assert len(res["root_coords"]) == 8
