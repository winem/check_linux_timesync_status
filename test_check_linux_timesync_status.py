#!/usr/bin/env python3
import io
import sys
import types
import unittest
from unittest import mock

import check_linux_timesync_status as mod


class TestDetectTimesyncDaemon(unittest.TestCase):
    def test_detect_chronyc_preferred(self):
        # chronyc available, timedatectl irrelevant
        with mock.patch.object(mod, "checkCommandAvailability", side_effect=lambda c: c == "chronyc"):
            self.assertEqual(mod.detectTimesyncDaemon(), "chronyc")

    def test_detect_timesyncd_fallback(self):
        def _avail(cmd):
            if cmd == "chronyc":
                return False
            if cmd == "timedatectl":
                return True
            return False

        with mock.patch.object(mod, "checkCommandAvailability", side_effect=_avail):
            self.assertEqual(mod.detectTimesyncDaemon(), "systemd-timesyncd")

    def test_detect_unknown_when_none_available(self):
        with mock.patch.object(mod, "checkCommandAvailability", return_value=False):
            self.assertEqual(mod.detectTimesyncDaemon(), "UNKNOWN")


class TestCheckCommandAvailability(unittest.TestCase):
    @mock.patch("check_linux_timesync_status.shutil.which")
    def test_command_available(self, mock_which):
        mock_which.return_value = "/usr/bin/chronyc"
        self.assertTrue(mod.checkCommandAvailability("chronyc"))
        mock_which.assert_called_once_with("chronyc")

    @mock.patch("check_linux_timesync_status.shutil.which")
    def test_command_unavailable(self, mock_which):
        mock_which.return_value = None
        self.assertFalse(mod.checkCommandAvailability("chronyc"))
        mock_which.assert_called_once_with("chronyc")


class TestTimedatectlStatus(unittest.TestCase):
    @mock.patch("check_linux_timesync_status.subprocess.Popen")
    def test_timedatectl_status_synced(self, mock_popen):
        td_output = """               Local time: Fri 2024-01-01 12:00:00 CET
           NTP synchronized: yes
     System clock synchronized: yes
"""
        # Simulate Popen with stdout as a bytes stream
        proc = types.SimpleNamespace(stdout=io.BytesIO(td_output.encode("utf-8")))
        mock_popen.return_value = proc

        result = mod.timedatectlStatus()
        self.assertEqual(result["service"]["state"], 0)
        self.assertIn("in sync", result["service"]["msg"])
        self.assertIn("leap_status", result["perfd"])
        self.assertEqual(result["perfd"]["leap_status"]["value"], 0)

    @mock.patch("check_linux_timesync_status.subprocess.Popen")
    def test_timedatectl_status_not_synced(self, mock_popen):
        td_output = """               Local time: Fri 2024-01-01 12:00:00 CET
           NTP synchronized: no
     System clock synchronized: no
"""
        proc = types.SimpleNamespace(stdout=io.BytesIO(td_output.encode("utf-8")))
        mock_popen.return_value = proc

        result = mod.timedatectlStatus()
        self.assertEqual(result["service"]["state"], 2)
        self.assertIn("not in sync", result["service"]["msg"])
        self.assertEqual(result["perfd"]["leap_status"]["value"], 2)


class TestChronycSources(unittest.TestCase):
    def _fake_chronyc_sources(self):
        # status, ?, host; simplified CSV-like rows as returned by chronyc -c sources
        return [
            ["^", "?", "host1"],
            ["^", "+", "host2"],
            ["^", "*", "host3"],
            ["^", "~", "host4"],
        ]

    @mock.patch.object(mod, "chronycMonitor")
    def test_sources_resource_aggregates_correctly(self, mock_chronyc_monitor):
        mock_chronyc_monitor.return_value = self._fake_chronyc_sources()

        out = mod.chronycSources("sources")
        svc = out["service"]
        perfd = out["perfd"]

        self.assertEqual(svc["name"], "NTP Sources Status")
        self.assertEqual(svc["state"], 0)
        self.assertEqual(perfd["configured_sources"]["value"], 4)
        self.assertEqual(perfd["available_sources"]["value"], 2)   # '+' and '*'
        self.assertEqual(perfd["synchronized_sources"]["value"], 1)  # '*'
        self.assertEqual(perfd["unreliable_sources"]["value"], 1)    # '~'

    @mock.patch.object(mod, "chronycMonitor")
    def test_falseticker_resource(self, mock_chronyc_monitor):
        # Two falsetickers with status 'x'
        mock_chronyc_monitor.return_value = [
            ["^", "x", "host1"],
            ["^", "x", "host2"],
            ["^", "+", "host3"],
        ]
        out = mod.chronycSources("falseticker")
        svc = out["service"]
        perfd = out["perfd"]

        self.assertEqual(svc["name"], "NTP Falseticker Status")
        self.assertEqual(svc["state"], 1)
        self.assertEqual(perfd["falseticker_sources"]["value"], 2)
        self.assertEqual(perfd["configured_sources"]["value"], 3)


class TestChronycTracking(unittest.TestCase):
    @mock.patch.object(mod, "chronycMonitor")
    def test_tracking_in_sync(self, mock_chronyc_monitor):
        # Construct a fake tracking row with:
        # index 4: system_time, index 10: root_delay, index 11: root_dispersion, index 13: leap_status text
        row = [None] * 14
        row[4] = "0.1"
        row[10] = "0.2"
        row[11] = "0.3"
        row[13] = "Normal"
        mock_chronyc_monitor.return_value = [row]

        out = mod.chronycTracking()
        self.assertEqual(out["service"]["state"], 0)
        self.assertIn("in sync", out["service"]["msg"])
        self.assertIn("max_estimated_error", out["perfd"])
        self.assertIsInstance(out["perfd"]["max_estimated_error"]["value"], float)

    @mock.patch.object(mod, "chronycMonitor")
    def test_tracking_not_in_sync(self, mock_chronyc_monitor):
        row = [None] * 14
        row[4] = "0.1"
        row[10] = "0.2"
        row[11] = "0.3"
        row[13] = "Not Normal"
        mock_chronyc_monitor.return_value = [row]

        out = mod.chronycTracking()
        self.assertEqual(out["service"]["state"], 2)
        self.assertIn("not in sync", out["service"]["msg"])


class TestResultToIcinga(unittest.TestCase):
    @mock.patch.object(mod.sys, "exit")
    def test_result_to_icinga_ok_with_perfdata(self, mock_exit):
        svc_result = {
            "service": {
                "name": "NTP Sources Status",
                "state": 0,
                "msg": "all good",
            },
            "perfd": {
                "available_sources": {
                    "value": 3,
                    "max": 5,
                    "warn": 2,
                    "crit": 1,
                }
            },
        }

        with mock.patch.object(mod, "print") as m_print:
            mod.resultToIcinga(svc_result)

        # Validate printed line format
        printed = m_print.call_args[0][0]
        self.assertTrue(printed.startswith("NTP SOURCES STATUS OK - all good |"))
        self.assertIn("available_sources=3", printed)
        mock_exit.assert_called_once_with(0)

    @mock.patch.object(mod.sys, "exit")
    def test_result_to_icinga_invalid_state_falls_back_to_unknown(self, mock_exit):
        svc_result = {
            "service": {
                "name": "Some Check",
                "state": 99,  # invalid
                "msg": "Invalid check state (99) received.",
            },
            "perfd": {},
        }

        with mock.patch.object(mod, "print") as m_print:
            mod.resultToIcinga(svc_result)

        printed = m_print.call_args[0][0]
        self.assertIn("UNKNOWN", printed)
        mock_exit.assert_called_once_with(3)


if __name__ == "__main__":
    unittest.main()
