import unittest

from backend.workbench.server import send_json


class _Headers:
    def write(self, _payload):
        raise BrokenPipeError(32, "Broken pipe")


class _DisconnectedHandler:
    def __init__(self):
        self.wfile = _Headers()

    def send_response(self, _status):
        pass

    def send_header(self, _name, _value):
        pass

    def end_headers(self):
        pass


class ServerTransportTests(unittest.TestCase):
    def test_disconnected_webview_does_not_turn_completed_operation_into_app_error(self):
        send_json(_DisconnectedHandler(), {"ok": True})


if __name__ == "__main__":
    unittest.main()
