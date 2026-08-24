import pytest
from core.mesh.e8_stream_server import E8TelemetryStreamer

@pytest.mark.asyncio
async def test_e8_streamer_snapshot_and_loop():
    streamer = E8TelemetryStreamer(node_id="TEST-STREAMER")
    
    payload = streamer.generate_snapshot_payload(T_eff=1.4)
    assert payload["node_id"] == "TEST-STREAMER"
    assert len(payload["tba_spectrum"]["species_masses"]) == 8
    assert len(payload["e8_highways"]["queue_depths_vector"]) == 240
    
    success = await streamer.stream_telemetry_loop(iterations=5, interval=0.0)
    assert success is True
