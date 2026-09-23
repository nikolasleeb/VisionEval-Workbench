import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "public" / "hypercube-runtime-summary.js"


def estimate(payload):
    script = f"const api=require({json.dumps(str(SUMMARY))}); process.stdout.write(JSON.stringify(api.estimateEta({json.dumps(payload)})));"
    completed = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def elapsed(payload):
    script = f"const api=require({json.dumps(str(SUMMARY))}); process.stdout.write(JSON.stringify(api.elapsedRuntime({json.dumps(payload)})));"
    completed = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


class HypercubeRuntimeSummaryTests(unittest.TestCase):
    def test_uses_first_completed_case_as_provisional_estimate(self):
        result = estimate({"successfulDurationsMs": [5 * 60_000, 7 * 60_000], "waitingCount": 4, "concurrency": 2})
        self.assertTrue(result["measured"])
        self.assertEqual(result["perRunMs"], 6 * 60_000)
        self.assertEqual(result["remainingMs"], 12 * 60_000)

    def test_uses_observed_median_and_limits_history_to_25_cases(self):
        result = estimate({"successfulDurationsMs": [10 * 60_000] * 25 + [60 * 60_000], "waitingCount": 3, "concurrency": 2})
        self.assertTrue(result["measured"])
        self.assertEqual(result["sampleCount"], 25)
        self.assertEqual(result["perRunMs"], 10 * 60_000)
        self.assertEqual(result["remainingMs"], 20 * 60_000)

    def test_accounts_for_elapsed_active_cases_and_parallel_slots(self):
        result = estimate({"activeElapsedMs": [3 * 60_000] * 6, "waitingCount": 58, "concurrency": 6})
        self.assertEqual(result["remainingMs"], 118 * 60_000)
        self.assertEqual(result["slotCount"], 6)

    def test_preparing_cases_take_a_full_planned_slot(self):
        result = estimate({"preparingCount": 2, "waitingCount": 2, "concurrency": 2})
        self.assertEqual(result["remainingMs"], 22 * 60_000)

    def test_long_running_cases_keep_a_nonzero_remaining_estimate(self):
        result = estimate({"activeElapsedMs": [30 * 60_000], "concurrency": 1})
        self.assertEqual(result["remainingMs"], 60_000)

    def test_concurrency_reduces_estimated_wall_time(self):
        serial = estimate({"waitingCount": 8, "concurrency": 1})
        parallel = estimate({"waitingCount": 8, "concurrency": 4})
        self.assertEqual(serial["remainingMs"], 88 * 60_000)
        self.assertEqual(parallel["remainingMs"], 22 * 60_000)

    def test_preserves_queued_behind_batch_status(self):
        result = estimate({"waitingCount": 3, "concurrency": 2, "queuedBehind": True})
        self.assertTrue(result["queuedBehind"])
        self.assertEqual(result["remainingMs"], 22 * 60_000)

    def test_elapsed_advances_only_for_an_active_batch(self):
        result = elapsed({"nowMs": 10_000, "jobs": [{"id": "one", "batchId": "batch-a", "state": "running", "startedAt": "1970-01-01T00:00:01.000Z"}]})
        self.assertEqual(result["elapsedMs"], 9_000)
        self.assertEqual(result["activeBatches"], 1)

    def test_elapsed_freezes_at_latest_terminal_finish(self):
        result = elapsed({"nowMs": 50_000, "jobs": [
            {"id": "one", "batchId": "batch-a", "state": "succeeded", "startedAt": "1970-01-01T00:00:01.000Z", "finishedAt": "1970-01-01T00:00:05.000Z"},
            {"id": "two", "batchId": "batch-a", "state": "failed", "startedAt": "1970-01-01T00:00:02.000Z", "finishedAt": "1970-01-01T00:00:08.000Z"},
        ]})
        self.assertEqual(result["elapsedMs"], 7_000)
        self.assertEqual(result["activeBatches"], 0)

    def test_waiting_only_batches_do_not_add_elapsed_time(self):
        result = elapsed({"nowMs": 50_000, "jobs": [{"id": "one", "batchId": "batch-a", "state": "waiting", "createdAt": "1970-01-01T00:00:01.000Z"}]})
        self.assertEqual(result["elapsedMs"], 0)
        self.assertFalse(result["started"])

    def test_retry_batches_sum_runtime_without_idle_gap(self):
        result = elapsed({"nowMs": 100_000, "jobs": [
            {"id": "one", "batchId": "batch-a", "state": "succeeded", "startedAt": "1970-01-01T00:00:01.000Z", "finishedAt": "1970-01-01T00:00:11.000Z"},
            {"id": "retry", "batchId": "batch-b", "state": "stopped", "startedAt": "1970-01-01T00:01:01.000Z", "finishedAt": "1970-01-01T00:01:06.000Z"},
        ]})
        self.assertEqual(result["elapsedMs"], 15_000)
        self.assertEqual(result["startedBatches"], 2)


if __name__ == "__main__":
    unittest.main()
