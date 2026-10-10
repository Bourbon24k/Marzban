import json
import os
import tempfile
import unittest
from unittest.mock import patch

import importlib.util
from pathlib import Path
_spec = importlib.util.spec_from_file_location("yuku_native_metadata", Path(__file__).resolve().parents[1] / "app/subscription/native_metadata.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
metadata_for_host = _module.metadata_for_host


class NativeMetadataTests(unittest.TestCase):
    def test_display_name_never_assigns_lte_role(self):
        with patch.dict(os.environ, {}, clear=True):
            result = metadata_for_host({"id": 41, "remark": "Germany LTE", "auto_select": 2})
        self.assertEqual(result["networkRole"], "unknown")
        self.assertEqual(result["hostID"], "41")

    def test_explicit_mapping_supplies_role_and_coordinates(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as stream:
            json.dump({"41": {"networkRole": "lte", "countryCode": "DE", "latitude": 51.0, "longitude": 10.0}}, stream)
            stream.flush()
            with patch.dict(os.environ, {"YUKU_CLIENT_METADATA_PATH": stream.name}):
                result = metadata_for_host({"id": 41, "auto_select": 2})
        self.assertEqual(result, {"schemaVersion": 1, "kind": "server", "hostID": "41", "networkRole": "lte", "autoSelectGroup": 2, "countryCode": "DE", "latitude": 51.0, "longitude": 10.0})

    def test_invalid_mapping_disables_role_without_breaking_subscription(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as stream:
            stream.write('{"41":{"networkRole":"maybe","latitude":999,"longitude":0}}')
            stream.flush()
            with patch.dict(os.environ, {"YUKU_CLIENT_METADATA_PATH": stream.name}):
                result = metadata_for_host({"id": 41, "auto_select": 0})
        self.assertEqual(result["networkRole"], "unknown")
        self.assertNotIn("latitude", result)
        self.assertEqual(result["autoSelectGroup"], 0)

    def test_missing_file_and_host_id_are_safe(self):
        with patch.dict(os.environ, {"YUKU_CLIENT_METADATA_PATH": "/missing/yuku.json"}):
            self.assertEqual(metadata_for_host({"id": 2})["networkRole"], "unknown")
            self.assertIsNone(metadata_for_host({}))

    def test_mapping_reloads_after_operator_edit(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as stream:
            json.dump({"41": {"networkRole": "normal"}}, stream)
            stream.flush()
            with patch.dict(os.environ, {"YUKU_CLIENT_METADATA_PATH": stream.name}):
                self.assertEqual(metadata_for_host({"id": 41})["networkRole"], "normal")
                stream.seek(0)
                stream.truncate()
                json.dump({"41": {"networkRole": "lte"}}, stream)
                stream.flush()
                self.assertEqual(metadata_for_host({"id": 41})["networkRole"], "lte")


if __name__ == "__main__":
    unittest.main()
