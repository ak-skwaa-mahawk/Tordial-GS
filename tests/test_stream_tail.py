"""Unit tests for live telemetry stream utility."""

from unittest.mock import patch, MagicMock
from core.mesh.mesh_stream_tail import stream_listener

@patch("socket.socket")
def test_stream_listener_bind_error(mock_socket):
    mock_inst = MagicMock()
    mock_inst.bind.side_effect = OSError("Address already in use")
    mock_socket.return_value = mock_inst

    # Should gracefully catch error and exit without unhandled exception
    stream_listener(18888)
    mock_inst.bind.assert_called_once()
