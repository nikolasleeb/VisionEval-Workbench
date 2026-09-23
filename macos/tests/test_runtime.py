import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from unittest.mock import patch

from backend.workbench.runtime import AMD64_LOCAL_IMAGE, ARM64_LOCAL_IMAGE, COMPATIBILITY_PATCH, CURRENT_RELEASE_COMMIT, CURRENT_RELEASE_TAG, LEGACY_RUNTIME_PROFILE, LOCAL_IMAGE, PINNED_ARM64_RUNTIME_DIGEST, PINNED_ARM64_RUNTIME_REFERENCE, RuntimeManager, discover_native_installation, docker_platform, find_native_runtime, local_runtime_image, read_renviron
from backend.workbench.workspace import Workspace, WorkspaceError, write_json


class FakeRunner:
    def __init__(self, installed=True):
        self.calls = []
        self.installed = installed

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        if "inspect" in command and not self.installed:
            return subprocess.CompletedProcess(command, 1, "", "not found")
        if "image" in command and "inspect" in command and "--format" in command and "{{json .Config.Labels}}" in command:
            labels = {
                "org.opencontainers.image.version": "1.1.0-ve-40-rc7-arm64",
                "org.opencontainers.image.revision": "workbench-build-revision",
                "com.visioneval.upstream.release": CURRENT_RELEASE_TAG,
                "com.visioneval.upstream.revision": CURRENT_RELEASE_COMMIT,
                "com.visioneval.workbench.runtime-api": "1",
                "com.visioneval.workbench.compatibility-patch": "none",
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(labels), "")
        return subprocess.CompletedProcess(command, 0, "{}", "")


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.adapter_patch = patch.dict("os.environ", {"VISIONEVAL_RUNTIME_ADAPTER": "docker"})
        self.adapter_patch.start()
        self.platform_patch = patch("backend.workbench.runtime.platform.system", return_value="Linux")
        self.platform_patch.start()

    def tearDown(self):
        self.platform_patch.stop()
        self.adapter_patch.stop()

    @staticmethod
    def write_runnable_project(workspace, project_id, name):
        project_dir = workspace.projects / project_id
        project_dir.mkdir()
        write_json(project_dir / "project.json", {
            "id": project_id,
            "name": name,
            "template": {"id": "template-test", "fingerprint": "fixture"},
            "inputLibrary": {"id": "library-test"},
            "variations": [{"id": "scenario", "name": "Scenario", "overlays": []}],
            "runIds": [], "datastoreIds": [], "baseline": {"strategy": "fresh"},
        })
        _, project = workspace.project(project_id)
        result_path = workspace.models / f"fixture-baseline-{project_id}" / "Datastore"
        result_path.mkdir(parents=True)
        (result_path / "DatastoreListing.Rda").write_text("baseline", encoding="utf-8")
        input_fingerprint = workspace.scenario_input_fingerprint(project, "baseline")
        runtime_digest = "sha256:fixture"
        workspace.register_datastore({
            "id": f"fixture-baseline-{project_id}", "path": str(result_path), "projectId": project_id,
            "variationId": "", "role": "baseline", "verification": "verified",
            "inputStateFingerprint": input_fingerprint, "runtimeImageDigest": runtime_digest,
            "executionFingerprint": workspace.execution_fingerprint(input_fingerprint, runtime_digest),
        })

    def test_windows_forces_native_even_when_environment_requests_docker(self):
        with tempfile.TemporaryDirectory() as directory, patch("backend.workbench.runtime.platform.system", return_value="Windows"), patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            runtime = RuntimeManager(Workspace(directory), runner=FakeRunner())
            self.assertEqual(runtime.adapter, "native")
            self.assertEqual(runtime.max_active_runs, 1)

    def test_native_discovery_reads_separate_runtime_home_and_r_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "VE_Runtime"
            home = root / "VE_Home"
            rscript = root / "R-4.4.2" / "bin" / "Rscript.exe"
            runtime.mkdir(); (home / "ve-lib" / "4.4" / "VEStart").mkdir(parents=True)
            rscript.parent.mkdir(parents=True); rscript.touch()
            (runtime / ".Renviron").write_text(f'VE_RUNTIME="{runtime}"\nVE_HOME="{home}"\n', encoding="utf-8")
            (runtime / "r.version").write_text("4.4.2\n", encoding="utf-8")
            (runtime / "launch_R4.4.2.bat").write_text(f"set R_HOME_BASE={rscript.parents[1]}\n", encoding="utf-8")
            self.assertEqual(read_renviron(runtime)["VE_HOME"], str(home))
            with patch("backend.workbench.runtime.platform.system", return_value="Windows"), patch.dict("os.environ", {"RSCRIPT": ""}):
                discovered = discover_native_installation(str(runtime))
            self.assertEqual(Path(discovered["veRuntime"]), runtime.resolve())
            self.assertEqual(Path(discovered["veHome"]), home.resolve())
            self.assertEqual(Path(discovered["rscript"]), rscript)

    def test_workbench_release_marker_identifies_developer_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "VisionEval"
            runtime.mkdir()
            (runtime / "WORKBENCH-RELEASE").write_text("tag=VE-40-RC6\n", encoding="utf-8")
            with patch("backend.workbench.runtime.platform.system", return_value="Windows"):
                self.assertEqual(find_native_runtime(str(runtime)), runtime.resolve())

    def test_native_verification_reports_detected_versions(self):
        class NativeRunner:
            def __call__(self, command, **kwargs):
                output = ""
                if "verify-capabilities" in command:
                    output = "WORKBENCH_RUNTIME_INFO|VisionEval=4.0.0|R=4.4.2|Packages=visioneval=3.1.1;VEStart=4.0.0;VEModel=3.1.1"
                return subprocess.CompletedProcess(command, 0, output, "")

        with tempfile.TemporaryDirectory() as directory, patch("backend.workbench.runtime.platform.system", return_value="Windows"), patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            root = Path(directory)
            runtime_path = root / "VE_Runtime"; runtime_path.mkdir(); (runtime_path / ".Rprofile").touch()
            home = root / "VE_Home"; (home / "ve-lib" / "4.4").mkdir(parents=True)
            rscript = root / "Rscript.exe"; rscript.touch()
            manager = RuntimeManager(Workspace(root / "workspace"), runner=NativeRunner())
            manager.configure_native(str(runtime_path), str(home), str(rscript))
            result = manager.verify_runtime()
            self.assertEqual(result["runtimeVersion"], "VisionEval 4.0.0 / R 4.4.2")
            self.assertEqual(result["packageVersions"]["VEStart"], "4.0.0")
            self.assertEqual(result["veRuntime"], str(runtime_path.resolve()))

    def test_optional_memory_cap_uses_docker_argument_array(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"VISIONEVAL_MEMORY_GB": "6"}), patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            runtime = RuntimeManager(Workspace(directory), runner=FakeRunner())
            self.assertEqual(runtime._container_resource_args(), ["--memory", "6g"])

    def test_existing_local_image_is_selected_automatically(self):
        def image_runner(command, **kwargs):
            installed = command[-1] == LOCAL_IMAGE
            return subprocess.CompletedProcess(command, 0 if installed else 1, "{}" if installed else "", "")

        with tempfile.TemporaryDirectory() as directory, patch("backend.workbench.runtime.find_docker_executable", return_value="/docker"), patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            runtime = RuntimeManager(Workspace(directory), runner=image_runner)
            self.assertEqual(runtime.image, LOCAL_IMAGE)

    def test_status_uses_argument_arrays(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            runner = FakeRunner()
            runtime = RuntimeManager(workspace, runner=runner)
            result = runtime.docker_status()
            if result["installed"]:
                self.assertTrue(all(isinstance(call, list) for call in runner.calls))

    def test_verification_uses_profile_specific_alignment_checks(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None), patch("backend.workbench.runtime.find_docker_executable", return_value="/docker"), patch("backend.workbench.runtime.platform.machine", return_value="AMD64"):
            runner = FakeRunner()
            runtime = RuntimeManager(Workspace(directory), runner=runner)
            runtime.active_runtime_profile = {
                "runtimeApi": 1, "visionEvalVersion": CURRENT_RELEASE_TAG, "visionEvalCommit": CURRENT_RELEASE_COMMIT,
                "digest": PINNED_ARM64_RUNTIME_DIGEST, "reference": PINNED_ARM64_RUNTIME_REFERENCE,
                "platform": "macos", "architecture": "arm64", "compatibilityPatch": "none",
                "capabilities": ["doctor", "verify-upstream-release", "verify-household-id-alignment", "run", "export"],
                "verificationCommands": ["doctor", "verify-upstream-release", "verify-household-id-alignment"],
            }
            result = runtime.verify_runtime()
            docker_runs = [call for call in runner.calls if "run" in call]
            self.assertTrue(any(call[-1] == "doctor" for call in docker_runs))
            self.assertTrue(any(call[-1] == "verify-upstream-release" for call in docker_runs))
            self.assertTrue(any(call[-1] == "verify-household-id-alignment" for call in docker_runs))
            self.assertTrue(all(call[call.index("--platform") + 1] == "linux/amd64" for call in docker_runs))
            self.assertEqual(result["runtimeVersion"], "VisionEval VE-40-RC7 / R 4.5.1")
            self.assertEqual(result["revision"], CURRENT_RELEASE_COMMIT)
            self.assertEqual(result["compatibilityPatch"], "none")
            self.assertEqual(runtime.expected_digest, result["digest"])

    def test_verification_rejects_image_with_wrong_release_hash(self):
        class WrongImageRunner(FakeRunner):
            def __call__(self, command, **kwargs):
                if "image" in command and "inspect" in command and "--format" in command:
                    return subprocess.CompletedProcess(command, 0, json.dumps({
                        "com.visioneval.upstream.release": CURRENT_RELEASE_TAG,
                        "com.visioneval.upstream.revision": "wrong",
                    }), "")
                return super().__call__(command, **kwargs)

        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None), patch("backend.workbench.runtime.find_docker_executable", return_value="/docker"):
            runtime = RuntimeManager(Workspace(directory), runner=WrongImageRunner())
            with self.assertRaisesRegex(WorkspaceError, "provenance mismatch"):
                runtime.verify_runtime()

    def test_non_windows_environment_cannot_activate_native_adapter(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory, \
                patch.dict("os.environ", {"VISIONEVAL_RUNTIME_ADAPTER": "native", "VISIONEVAL_HOME": r"C:\\VisionEval"}), \
                patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            runtime = RuntimeManager(Workspace(directory), runner=FakeRunner())
            self.assertEqual(runtime.adapter, "docker")

    def test_host_platform_selects_architecture_specific_image(self):
        with patch("backend.workbench.runtime.platform.system", return_value="Windows"), patch("backend.workbench.runtime.platform.machine", return_value="AMD64"):
            self.assertEqual(docker_platform(), "linux/amd64")
            self.assertEqual(local_runtime_image(), AMD64_LOCAL_IMAGE)
        with patch("backend.workbench.runtime.platform.system", return_value="Darwin"), patch("backend.workbench.runtime.platform.machine", return_value="arm64"):
            self.assertEqual(docker_platform(), "linux/arm64")
            self.assertEqual(local_runtime_image(), ARM64_LOCAL_IMAGE)

    def test_apple_silicon_alias_matches_the_published_runtime_contract(self):
        self.assertEqual(
            ARM64_LOCAL_IMAGE,
            "local/visioneval:2.0.0-arm64",
        )
        self.assertEqual(
            PINNED_ARM64_RUNTIME_DIGEST,
            "sha256:f6dba706e39bc403ad08c8fb27c2a8d69d74875de096475df3ac8311e1c13791",
        )
        self.assertEqual(
            PINNED_ARM64_RUNTIME_REFERENCE,
            f"ghcr.io/nikolasleeb/visioneval-workbench-runtime@{PINNED_ARM64_RUNTIME_DIGEST}",
        )

    def test_managed_macos_install_pulls_pinned_digest_tags_and_verifies(self):
        class InstallRunner(FakeRunner):
            def __call__(self, command, **kwargs):
                self.calls.append(command)
                if "image" in command and "inspect" in command and "{{json .Config.Labels}}" in command:
                    labels = {
                        "com.visioneval.upstream.release": CURRENT_RELEASE_TAG,
                        "com.visioneval.upstream.revision": CURRENT_RELEASE_COMMIT,
                        "com.visioneval.workbench.compatibility-patch": "none",
                        "com.visioneval.workbench.runtime-api": "1",
                    }
                    return subprocess.CompletedProcess(command, 0, json.dumps(labels), "")
                if "image" in command and "inspect" in command and "RepoDigests" in " ".join(command):
                    return subprocess.CompletedProcess(command, 0, f"{PINNED_ARM64_RUNTIME_REFERENCE}\n", "")
                return subprocess.CompletedProcess(command, 0, "{}", "")

        with tempfile.TemporaryDirectory() as directory, \
                patch.object(RuntimeManager, "_dispatch_loop", return_value=None), \
                patch("backend.workbench.runtime.find_docker_executable", return_value="/docker"), \
                patch("backend.workbench.runtime.platform.system", return_value="Darwin"), \
                patch("backend.workbench.runtime.platform.machine", return_value="arm64"):
            runner = InstallRunner()
            runtime = RuntimeManager(Workspace(directory), runner=runner)
            result = runtime.install_or_update_runtime()
            self.assertIn(["/docker", "pull", "--platform", "linux/arm64", PINNED_ARM64_RUNTIME_REFERENCE], runner.calls)
            self.assertEqual(result["digest"], PINNED_ARM64_RUNTIME_DIGEST)
            self.assertEqual(result["source"], PINNED_ARM64_RUNTIME_REFERENCE)

    def test_managed_runtime_install_is_rejected_outside_apple_silicon_macos(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(RuntimeManager, "_dispatch_loop", return_value=None), \
                patch("backend.workbench.runtime.platform.system", return_value="Linux"):
            runtime = RuntimeManager(Workspace(directory), runner=FakeRunner())
            with self.assertRaisesRegex(WorkspaceError, "Apple Silicon macOS only"):
                runtime.install_or_update_runtime()

    def test_release_check_is_cached_and_advisory(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            runtime = RuntimeManager(Workspace(directory), runner=FakeRunner())
            runtime.release_check_supported = True
            runtime.release_check_enabled = True
            runtime._fetch_public_releases = lambda: [
                {"tag_name": "VE-40-RC8", "name": "RC8", "published_at": "2026-08-01T00:00:00Z", "html_url": "https://example.test/rc8"},
                {"tag_name": CURRENT_RELEASE_TAG},
            ]
            runtime._refresh_release_status()
            status = runtime.release_status()
            self.assertEqual(status["status"], "update_available")
            self.assertEqual(status["releasesBehind"], 1)
            self.assertTrue(status["advisoryOnly"])
            self.assertEqual(status["currentCommit"], CURRENT_RELEASE_COMMIT)

    def test_release_check_can_be_disabled_without_disabling_image_verification(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            workspace.update_settings({"checkVisionEvalUpdates": False})
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            self.assertFalse(runtime.release_check_enabled)
            self.assertEqual(runtime.release_status()["status"], "disabled")
            self.assertEqual(runtime.release_status()["currentCommit"], CURRENT_RELEASE_COMMIT)

    def test_interrupted_jobs_are_recovered_as_failed(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            job_dir = workspace.runs / "run-stale"
            job_dir.mkdir()
            write_json(job_dir / "job.json", {"id": "run-stale", "state": "running"})
            RuntimeManager(workspace, runner=FakeRunner())
            job = json.loads((job_dir / "job.json").read_text())
            self.assertEqual(job["state"], "failed")
            self.assertIn("ownership", job["message"])

    def test_log_chunks_are_offset_based(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(directory)
            job_dir = workspace.runs / "run-log"
            job_dir.mkdir()
            log = job_dir / "run.log"
            log.write_text("first\nsecond\n", encoding="utf-8")
            write_json(job_dir / "job.json", {"id": "run-log", "state": "succeeded", "logPath": str(log)})
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            first = runtime.log_chunk("run-log", 0)
            second = runtime.log_chunk("run-log", first["offset"])
            self.assertEqual(first["text"], "first\nsecond\n")
            self.assertEqual(second["text"], "")
            self.assertTrue(first["terminal"])

    def test_global_queue_is_persistent_reorderable_and_revision_guarded(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            for index, job_id in enumerate(("run-one", "run-two", "run-three"), 1):
                run_dir = workspace.runs / job_id
                run_dir.mkdir()
                write_json(run_dir / "job.json", {
                    "id": job_id, "state": "waiting", "createdAt": f"2026-01-01T00:00:0{index}Z",
                    "queuePosition": index, "queueRevision": 0, "logPath": str(run_dir / "run.log"),
                    "modelPath": str(workspace.models / job_id),
                })
                (run_dir / "run.log").touch()
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            queue = runtime.queue()
            self.assertEqual([item["id"] for item in queue["jobs"]], ["run-one", "run-two", "run-three"])
            reordered = runtime.reorder_queue(["run-three", "run-one", "run-two"], queue["revision"])
            self.assertEqual([item["id"] for item in reordered["jobs"]], ["run-three", "run-one", "run-two"])
            with self.assertRaises(WorkspaceError):
                runtime.reorder_queue(["run-one", "run-two", "run-three"], queue["revision"])
            restarted = RuntimeManager(workspace, runner=FakeRunner())
            self.assertEqual([item["id"] for item in restarted.queue()["jobs"]], ["run-three", "run-one", "run-two"])

    def test_queue_state_write_tolerates_workspace_teardown(self):
        temporary = tempfile.TemporaryDirectory()
        with patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            runtime = RuntimeManager(Workspace(temporary.name), runner=FakeRunner())
        temporary.cleanup()
        runtime._write_queue_state_locked(1, None)

    def test_mixed_mode_batches_wait_fifo_and_keep_their_own_mode(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            self.write_runnable_project(workspace, "project-one", "Project one")
            self.write_runnable_project(workspace, "project-two", "Project two")
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            validation = {"valid": True, "errors": [], "warnings": []}
            with patch.object(runtime, "validate_project", return_value=validation), patch.object(runtime, "image_digest", return_value="sha256:fixture"):
                first = runtime.create_batch("project-one", ["scenario"], False, "queued")
                second = runtime.create_batch("project-two", ["scenario"], False, "parallel")

            queue = runtime.queue()
            self.assertEqual(queue["modeLock"], "queued")
            self.assertEqual(queue["activeBatchId"], first["id"])
            self.assertEqual(queue["maxActive"], 1)
            self.assertEqual([job["projectId"] for job in queue["jobs"]], ["project-one", "project-two"])
            self.assertEqual(first["jobs"][0]["batchMode"], "queued")
            self.assertEqual(second["jobs"][0]["batchMode"], "parallel")

            first_job = first["jobs"][0]
            write_json(workspace.runs / first_job["id"] / "job.json", {**first_job, "state": "succeeded", "finishedAt": "2026-01-01T00:01:00Z"})
            next_queue = runtime.queue()
            self.assertEqual(next_queue["modeLock"], "parallel")
            self.assertEqual(next_queue["activeBatchId"], second["id"])
            self.assertEqual(next_queue["maxActive"], 2)

    def test_retention_mode_is_frozen_when_jobs_are_queued(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            self.write_runnable_project(workspace, "standard", "Standard")
            self.write_runnable_project(workspace, "hypercube", "Hypercube")
            project_path = workspace.projects / "hypercube" / "project.json"
            hypercube = json.loads(project_path.read_text(encoding="utf-8"))
            hypercube["projectType"] = "hypercube"
            hypercube["hypercubes"] = [{"id": "cube", "scenarioIds": ["scenario"], "axes": []}]
            write_json(project_path, hypercube)
            workspace.update_settings({"retainFullExports": False})
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            validation = {"valid": True, "errors": [], "warnings": []}
            with patch.object(runtime, "validate_project", return_value=validation), patch.object(runtime, "image_digest", return_value="sha256:fixture"):
                standard = runtime.create_batch("standard", ["scenario"], False, "queued")
            self.assertEqual(standard["jobs"][0]["resultRetentionMode"], "datastore_only")

            write_json(workspace.runs / standard["jobs"][0]["id"] / "job.json", {**standard["jobs"][0], "state": "succeeded", "finishedAt": "2026-01-01T00:01:00Z"})
            workspace.update_settings({"retainFullExports": True})
            with patch.object(runtime, "validate_project", return_value=validation), patch.object(runtime, "image_digest", return_value="sha256:fixture"):
                cube = runtime.create_batch("hypercube", ["scenario"], False, "queued")
            self.assertEqual(cube["jobs"][0]["resultRetentionMode"], "datastore_only")
            self.assertEqual(json.loads((workspace.runs / standard["jobs"][0]["id"] / "job.json").read_text())["resultRetentionMode"], "datastore_only")

    def test_parallel_mode_lock_is_shared_by_projects_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            self.write_runnable_project(workspace, "project-one", "Project one")
            self.write_runnable_project(workspace, "project-two", "Project two")
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            validation = {"valid": True, "errors": [], "warnings": []}
            with patch.object(runtime, "validate_project", return_value=validation), patch.object(runtime, "image_digest", return_value="sha256:fixture"):
                runtime.create_batch("project-one", ["scenario"], False, "parallel")
                runtime.create_batch("project-two", ["scenario"], False, "parallel")

            self.assertEqual(runtime.queue()["modeLock"], "parallel")
            self.assertEqual(runtime.queue()["maxActive"], 2)
            restarted = RuntimeManager(workspace, runner=FakeRunner())
            self.assertEqual(restarted.queue()["modeLock"], "parallel")

    def test_simultaneous_mixed_mode_submissions_create_two_atomic_batches(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            self.write_runnable_project(workspace, "project-queued", "Queued project")
            self.write_runnable_project(workspace, "project-parallel", "Parallel project")
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            barrier = threading.Barrier(2)
            results, errors = [], []

            def submit(project_id, mode):
                barrier.wait()
                try:
                    results.append(runtime.create_batch(project_id, ["scenario"], False, mode))
                except WorkspaceError as exc:
                    errors.append(str(exc))

            validation = {"valid": True, "errors": [], "warnings": []}
            with patch.object(runtime, "validate_project", return_value=validation), patch.object(runtime, "image_digest", return_value="sha256:fixture"):
                threads = [
                    threading.Thread(target=submit, args=("project-queued", "queued")),
                    threading.Thread(target=submit, args=("project-parallel", "parallel")),
                ]
                for thread in threads: thread.start()
                for thread in threads: thread.join()

            self.assertEqual(len(results), 2)
            self.assertEqual(errors, [])
            queue = runtime.queue()
            self.assertEqual(len(queue["jobs"]), 2)
            self.assertEqual({job["batchMode"] for job in queue["jobs"]}, {"queued", "parallel"})
            first_job = min(queue["jobs"], key=lambda item: item["queuePosition"])
            self.assertEqual(queue["activeBatchId"], first_job["batchId"])
            self.assertEqual(queue["modeLock"], first_job["batchMode"])

    def test_retry_preserves_original_mode_when_starting_a_new_backlog(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            self.write_runnable_project(workspace, "project-one", "Project one")
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            _, project = workspace.project("project-one")
            prior_result = workspace.models / "prior-scenario-result" / "Datastore"
            prior_result.mkdir(parents=True)
            (prior_result / "DatastoreListing.Rda").write_text("prior", encoding="utf-8")
            input_fingerprint = workspace.scenario_input_fingerprint(project, "scenario")
            workspace.register_datastore({
                "id": "prior-scenario-result", "path": str(prior_result), "projectId": "project-one",
                "variationId": "scenario", "role": "scenario", "verification": "verified",
                "inputStateFingerprint": input_fingerprint, "runtimeImageDigest": "sha256:fixture",
                "executionFingerprint": workspace.execution_fingerprint(input_fingerprint, "sha256:fixture"),
            })
            run_dir = workspace.runs / "failed-parallel"
            run_dir.mkdir()
            write_json(run_dir / "job.json", {
                "id": "failed-parallel", "state": "failed", "batchMode": "parallel",
                "projectId": "project-one", "variationId": "scenario", "variationName": "Scenario",
                "baseline": False, "createdAt": "2026-01-01T00:00:00Z",
            })
            validation = {"valid": True, "errors": [], "warnings": []}
            with patch.object(runtime, "validate_project", return_value=validation), patch.object(runtime, "image_digest", return_value="sha256:fixture"):
                retried = runtime.retry("failed-parallel")
            self.assertEqual(retried["batchMode"], "parallel")
            self.assertEqual(runtime.queue()["modeLock"], "parallel")

    def test_legacy_mixed_backlog_uses_oldest_unfinished_job_mode(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            for index, (job_id, mode) in enumerate((("oldest", "queued"), ("newer", "parallel")), 1):
                run_dir = workspace.runs / job_id
                run_dir.mkdir()
                write_json(run_dir / "job.json", {
                    "id": job_id,
                    "state": "waiting",
                    "batchMode": mode,
                    "createdAt": f"2026-01-01T00:00:0{index}Z",
                    "queuePosition": index,
                })
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            self.assertEqual(runtime.queue()["modeLock"], "queued")
            self.assertEqual(json.loads((workspace.runs / "queue.json").read_text())["modeLock"], "queued")

    def test_dispatcher_does_not_select_a_job_that_already_reserved_a_slot(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            waiting = []
            for index, job_id in enumerate(("run-one", "run-two"), 1):
                run_dir = workspace.runs / job_id
                run_dir.mkdir()
                job = {
                    "id": job_id,
                    "state": "waiting",
                    "batchId": "batch-parallel",
                    "createdAt": f"2026-01-01T00:00:0{index}Z",
                    "queuePosition": index,
                    "queueRevision": 0,
                }
                write_json(run_dir / "job.json", job)
                waiting.append(job)
            write_json(workspace.runs / "batch-parallel.json", {
                "id": "batch-parallel", "mode": "parallel", "jobIds": ["run-one", "run-two"]
            })
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            runtime.workers["run-one"] = threading.Thread()

            selected = runtime._next_waiting_job_locked(waiting)

            self.assertEqual(selected["id"], "run-two")

    def test_queued_batch_does_not_select_a_second_reserved_job(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            waiting = []
            for index, job_id in enumerate(("run-one", "run-two"), 1):
                run_dir = workspace.runs / job_id
                run_dir.mkdir()
                job = {
                    "id": job_id,
                    "state": "waiting",
                    "batchId": "batch-queued",
                    "createdAt": f"2026-01-01T00:00:0{index}Z",
                    "queuePosition": index,
                    "queueRevision": 0,
                }
                write_json(run_dir / "job.json", job)
                waiting.append(job)
            write_json(workspace.runs / "batch-queued.json", {
                "id": "batch-queued", "mode": "queued", "jobIds": ["run-one", "run-two"]
            })
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            runtime.workers["run-one"] = threading.Thread()

            selected = runtime._next_waiting_job_locked(waiting)

            self.assertIsNone(selected)

    def test_queued_batches_from_different_projects_share_one_active_slot(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            waiting = []
            for index, (job_id, batch_id, project_id) in enumerate((("run-one", "batch-one", "project-one"), ("run-two", "batch-two", "project-two")), 1):
                run_dir = workspace.runs / job_id
                run_dir.mkdir()
                job = {
                    "id": job_id, "state": "waiting", "batchId": batch_id, "batchMode": "queued",
                    "projectId": project_id, "createdAt": f"2026-01-01T00:00:0{index}Z", "queuePosition": index,
                }
                write_json(run_dir / "job.json", job)
                waiting.append(job)
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            runtime.workers["run-one"] = threading.Thread()
            self.assertIsNone(runtime._next_waiting_job_locked(waiting))

    def test_native_environment_still_allows_parallel_docker_batches(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None), patch.dict("os.environ", {"VISIONEVAL_RUNTIME_ADAPTER": "native"}):
            workspace = Workspace(directory)
            project_id = "project-native-queue"
            project_dir = workspace.projects / project_id
            project_dir.mkdir()
            write_json(project_dir / "project.json", {
                "id": project_id, "name": "Native queue", "template": {"id": "template-test", "fingerprint": "fixture"},
                "inputLibrary": {"id": "library-test"}, "variations": [{"id": "scenario", "name": "Scenario", "overlays": []}], "runIds": [],
            })
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            with patch.object(runtime, "validate_project", return_value={"valid": True, "errors": [], "warnings": []}), patch.object(runtime, "image_digest", return_value="sha256:fixture"):
                batch = runtime.create_batch(project_id, ["scenario"], True, "parallel")

            self.assertEqual(runtime.adapter, "docker")
            self.assertEqual(runtime.max_active_runs, 2)
            self.assertEqual(runtime.queue()["maxActive"], 2)
            self.assertEqual(batch["mode"], "parallel")
            self.assertTrue(all(job["batchMode"] == "parallel" for job in batch["jobs"]))

    def test_native_commands_use_the_prepared_absolute_model_path(self):
        source = (Path(__file__).parents[1] / "backend" / "workbench" / "runtime.py").read_text(encoding="utf-8")
        self.assertIn('_native_command("run", str(model_path))', source)
        self.assertIn('_native_command("export", str(model_path))', source)

    def test_job_level_queued_mode_is_enforced_before_batch_manifest_is_available(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            waiting = []
            for index, job_id in enumerate(("run-one", "run-two"), 1):
                run_dir = workspace.runs / job_id
                run_dir.mkdir()
                job = {
                    "id": job_id,
                    "state": "waiting",
                    "batchId": "batch-not-published",
                    "batchMode": "queued",
                    "createdAt": f"2026-01-01T00:00:0{index}Z",
                    "queuePosition": index,
                }
                write_json(run_dir / "job.json", job)
                waiting.append(job)
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            runtime.workers["run-one"] = threading.Thread()

            self.assertIsNone(runtime._next_waiting_job_locked(waiting))

    def test_remove_waiting_deletes_job_log_model_and_partial_datastore(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            run_dir = workspace.runs / "run-remove"
            run_dir.mkdir()
            model = workspace.models / "run-remove"
            (model / "results").mkdir(parents=True)
            (model / "results" / "partial.txt").write_text("partial", encoding="utf-8")
            write_json(run_dir / "job.json", {
                "id": "run-remove", "state": "waiting", "createdAt": "2026-01-01T00:00:00Z",
                "queuePosition": 1, "queueRevision": 0, "logPath": str(run_dir / "run.log"),
                "modelPath": str(model), "batchId": "batch-remove", "projectId": "missing-project",
            })
            (run_dir / "run.log").write_text("partial log", encoding="utf-8")
            write_json(workspace.runs / "batch-remove.json", {"id": "batch-remove", "jobIds": ["run-remove"]})
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            result = runtime.remove_waiting("run-remove")
            self.assertTrue(result["removed"])
            self.assertFalse(run_dir.exists())
            self.assertFalse(model.exists())
            self.assertFalse((workspace.runs / "batch-remove.json").exists())

    def test_create_batch_queues_only_the_explicit_selection(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            project_id = "project-selection"
            project_dir = workspace.projects / project_id
            project_dir.mkdir()
            write_json(project_dir / "project.json", {
                "id": project_id,
                "name": "Selection test",
                "template": {"id": "template-test", "name": "Test", "fingerprint": "fixture"},
                "inputLibrary": {"id": "library-test"},
                "variations": [
                    {"id": "variation-one", "name": "One", "overlays": []},
                    {"id": "variation-two", "name": "Two", "overlays": []},
                    {"id": "variation-three", "name": "Three", "overlays": []},
                    {"id": "variation-four", "name": "Four", "overlays": []},
                ],
                "runIds": [],
            })
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            with patch.object(runtime, "validate_project", return_value={"valid": True, "errors": [], "warnings": []}), patch.object(runtime, "image_digest", return_value="sha256:fixture"), patch.object(workspace, "current_result", side_effect=lambda _project, variation_id, _digest: {"id": "baseline"} if variation_id == "baseline" else None):
                batch = runtime.create_batch(project_id, ["variation-two", "variation-four"], False, "parallel")

            self.assertEqual([job["variationId"] for job in batch["jobs"]], ["variation-two", "variation-four"])
            self.assertEqual(len(runtime.queue()["jobs"]), 2)

    def test_create_batch_reuses_exact_results_unless_force_rerun_is_requested(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            project_id = "project-reuse"
            self.write_runnable_project(workspace, project_id, "Reuse test")
            _, project = workspace.project(project_id)
            runtime_digest = "sha256:fixture"
            for variation_id, role in (("baseline", "baseline"), ("scenario", "scenario")):
                result_path = workspace.models / f"result-{variation_id}" / "Datastore"
                result_path.mkdir(parents=True)
                (result_path / "DatastoreListing.Rda").write_text("result", encoding="utf-8")
                input_fingerprint = workspace.scenario_input_fingerprint(project, variation_id)
                workspace.register_datastore({
                    "id": f"datastore-{variation_id}", "path": str(result_path), "projectId": project_id,
                    "variationId": "" if role == "baseline" else variation_id, "role": role,
                    "verification": "verified", "inputStateFingerprint": input_fingerprint,
                    "runtimeImageDigest": runtime_digest,
                    "executionFingerprint": workspace.execution_fingerprint(input_fingerprint, runtime_digest),
                })
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            with patch.object(runtime, "validate_project", return_value={"valid": True, "errors": [], "warnings": []}), patch.object(runtime, "image_digest", return_value=runtime_digest):
                reused = runtime.create_batch(project_id, ["scenario"], True, "parallel")
                forced = runtime.create_batch(project_id, ["scenario"], True, "parallel", ["scenario"])
            self.assertEqual(reused["jobs"], [])
            self.assertEqual({item["variationId"] for item in reused["reusedResults"]}, {"baseline", "scenario"})
            self.assertEqual([item["variationId"] for item in forced["jobs"]], ["scenario"])
            self.assertEqual([item["variationId"] for item in forced["reusedResults"]], ["baseline"])

    def test_remove_history_deletes_record_and_log_but_preserves_completed_results(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            run_dir = workspace.runs / "run-complete"
            run_dir.mkdir()
            model = workspace.models / "run-complete"
            datastore = model / "results" / "Datastore"
            datastore.mkdir(parents=True)
            (datastore / "DatastoreListing.Rda").write_text("result", encoding="utf-8")
            write_json(run_dir / "job.json", {
                "id": "run-complete", "state": "succeeded", "projectId": "missing-project",
                "batchId": "batch-complete", "logPath": str(run_dir / "run.log"),
                "modelPath": str(model), "resultPath": str(datastore), "datastoreId": "datastore-complete",
            })
            (run_dir / "run.log").write_text("completed log", encoding="utf-8")
            write_json(workspace.runs / "batch-complete.json", {"id": "batch-complete", "jobIds": ["run-complete"]})
            runtime = RuntimeManager(workspace, runner=FakeRunner())

            result = runtime.remove_history("run-complete")

            self.assertTrue(result["removed"])
            self.assertTrue(result["resultsPreserved"])
            self.assertFalse(run_dir.exists())
            self.assertTrue(datastore.exists())
            self.assertFalse((workspace.runs / "batch-complete.json").exists())

    def test_remove_history_rejects_nonterminal_job(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            run_dir = workspace.runs / "run-waiting"
            run_dir.mkdir()
            write_json(run_dir / "job.json", {"id": "run-waiting", "state": "waiting", "queuePosition": 1})
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            with self.assertRaises(WorkspaceError):
                runtime.remove_history("run-waiting")

    def test_manual_history_clear_is_atomically_blocked_until_queue_is_idle(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            complete = workspace.runs / "run-complete"; complete.mkdir()
            waiting = workspace.runs / "run-waiting"; waiting.mkdir()
            write_json(complete / "job.json", {"id": "run-complete", "state": "succeeded"})
            write_json(waiting / "job.json", {"id": "run-waiting", "state": "waiting", "queuePosition": 1})
            runtime = RuntimeManager(workspace, runner=FakeRunner())

            impact = runtime.history_clear_impact()
            self.assertTrue(impact["blocked"])
            self.assertEqual(impact["unfinishedJobs"], 1)
            with self.assertRaisesRegex(WorkspaceError, "running and queued jobs finish"):
                runtime.clear_history(require_idle=True)
            self.assertTrue((complete / "job.json").is_file())

            queued = json.loads((waiting / "job.json").read_text(encoding="utf-8"))
            queued["state"] = "cancelled"
            write_json(waiting / "job.json", queued)
            result = runtime.clear_history(require_idle=True)
            self.assertEqual(result["removedJobs"], 2)
            self.assertTrue(result["resultsPreserved"])

    def test_stop_all_cancels_active_removes_waiting_and_preserves_completed_results(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            complete_run = workspace.runs / "run-complete"; complete_run.mkdir()
            complete_model = workspace.models / "run-complete"
            complete_datastore = complete_model / "results" / "Datastore"
            complete_datastore.mkdir(parents=True)
            (complete_datastore / "DatastoreListing.Rda").write_text("result", encoding="utf-8")
            write_json(complete_run / "job.json", {
                "id": "run-complete", "state": "succeeded", "modelPath": str(complete_model),
                "resultPath": str(complete_datastore), "datastoreId": "datastore-complete",
            })
            workspace.register_datastore({
                "id": "datastore-complete", "runId": "run-complete", "label": "Prior complete",
                "path": str(complete_datastore), "verification": "verified",
            })
            active_run = workspace.runs / "run-active"; active_run.mkdir()
            write_json(active_run / "job.json", {
                "id": "run-active", "state": "running", "containerName": "",
                "modelPath": str(workspace.models / "run-active"), "logPath": str(active_run / "run.log"),
            })
            waiting_run = workspace.runs / "run-waiting"; waiting_run.mkdir()
            waiting_model = workspace.models / "run-waiting"
            (waiting_model / "results").mkdir(parents=True)
            write_json(waiting_run / "job.json", {
                "id": "run-waiting", "state": "waiting", "queuePosition": 1,
                "modelPath": str(waiting_model), "logPath": str(waiting_run / "run.log"),
            })
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            job = json.loads((active_run / "job.json").read_text(encoding="utf-8")); job["state"] = "running"; write_json(active_run / "job.json", job)

            result = runtime.stop_all()

            self.assertEqual(result, {"stopped": 1, "removed": 1, "failures": []})
            self.assertEqual(runtime.job("run-active")["state"], "stopping")
            self.assertFalse(waiting_run.exists())
            self.assertFalse(waiting_model.exists())
            self.assertTrue(complete_datastore.exists())
            self.assertIn("datastore-complete", {item["id"] for item in workspace.catalog()["datastores"]})

    def test_stop_all_removes_queue_before_stopping_active_runs(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            active_run = workspace.runs / "run-active"; active_run.mkdir()
            waiting_run = workspace.runs / "run-waiting"; waiting_run.mkdir()
            waiting_model = workspace.models / "run-waiting"; waiting_model.mkdir(parents=True)
            write_json(active_run / "job.json", {
                "id": "run-active", "state": "running", "containerName": "",
                "modelPath": str(workspace.models / "run-active"), "logPath": str(active_run / "run.log"),
            })
            write_json(waiting_run / "job.json", {
                "id": "run-waiting", "state": "waiting", "queuePosition": 1,
                "modelPath": str(waiting_model), "logPath": str(waiting_run / "run.log"),
            })
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            job = json.loads((active_run / "job.json").read_text()); job["state"] = "running"; write_json(active_run / "job.json", job)
            original_cancel = runtime.cancel
            queue_was_empty = []

            def observed_cancel(job_id):
                queue_was_empty.append(not waiting_run.exists() and not runtime.queue()["jobs"])
                return original_cancel(job_id)

            with patch.object(runtime, "cancel", side_effect=observed_cancel):
                result = runtime.stop_all()

            self.assertEqual(result["removed"], 1)
            self.assertEqual(result["stopped"], 1)
            self.assertEqual(queue_was_empty, [True])

    def test_stop_all_barrier_rejects_new_batches(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            self.write_runnable_project(workspace, "project-one", "Project one")
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            runtime.stop_all_in_progress = True
            with patch.object(runtime, "validate_project", return_value={"valid": True, "errors": [], "warnings": []}), patch.object(runtime, "image_digest", return_value="sha256:fixture"):
                with self.assertRaisesRegex(WorkspaceError, "Stop All"):
                    runtime.create_batch("project-one", ["scenario"], False, "parallel")

    def test_shutdown_requires_confirmation_for_active_jobs(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            run_dir = workspace.runs / "run-active"; run_dir.mkdir()
            write_json(run_dir / "job.json", {"id":"run-active","state":"running","variationName":"Active scenario","containerName":"","logPath":str(run_dir/"run.log")})
            (run_dir / "run.log").touch()
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            # Recovery correctly makes an unverifiable stale container terminal; restore an
            # active manifest to exercise the explicit shutdown confirmation contract.
            job = json.loads((run_dir / "job.json").read_text()); job["state"]="running"; write_json(run_dir / "job.json", job)
            result = runtime.shutdown(False)
            self.assertTrue(result["requiresConfirmation"])
            self.assertEqual(result["jobs"][0]["id"], "run-active")

    def test_container_ownership_requires_workbench_and_job_labels(self):
        def runner(command, **kwargs):
            labels = {"com.visioneval.workbench":"true", "com.visioneval.job":"run-owned"}
            return subprocess.CompletedProcess(command, 0, json.dumps(labels), "")
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None), patch("backend.workbench.runtime.find_docker_executable", return_value="/docker"):
            runtime = RuntimeManager(Workspace(directory), runner=runner)
            self.assertTrue(runtime._container_owned({"id":"run-owned","containerName":"ve-run-owned"}))
            self.assertFalse(runtime._container_owned({"id":"run-other","containerName":"ve-run-other"}))

    def test_confirmed_docker_oom_has_human_readable_failure_metadata(self):
        failure = RuntimeManager._execution_failure(137, {"OOMKilled": True, "ExitCode": 137})
        fields = RuntimeManager._failure_fields(failure)
        self.assertEqual(fields["failureKind"], "memory")
        self.assertEqual(fields["exitCode"], 137)
        self.assertTrue(fields["oomKilled"])
        self.assertIn("ran out of available memory", fields["message"])
        self.assertNotIn("exited with code", fields["message"])
        self.assertIn("exited with code 137", fields["technicalDetail"])

    def test_exit_137_without_docker_oom_is_marked_as_interrupted(self):
        failure = RuntimeManager._execution_failure(137, {"OOMKilled": False, "ExitCode": 137})
        fields = RuntimeManager._failure_fields(failure)
        self.assertEqual(fields["failureKind"], "interrupted")
        self.assertFalse(fields["oomKilled"])
        self.assertIn("did not report an out-of-memory", fields["message"])

    def test_owned_container_state_is_inspected_then_removed(self):
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            if "inspect" in command and "{{json .Config.Labels}}" in command:
                return subprocess.CompletedProcess(command, 0, json.dumps({
                    "com.visioneval.workbench": "true", "com.visioneval.job": "run-owned",
                }), "")
            if "inspect" in command and "{{json .State}}" in command:
                return subprocess.CompletedProcess(command, 0, json.dumps({"OOMKilled": True, "ExitCode": 137}), "")
            return subprocess.CompletedProcess(command, 0, "", "")

        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None), patch("backend.workbench.runtime.find_docker_executable", return_value="/docker"):
            runtime = RuntimeManager(Workspace(directory), runner=runner)
            job = {"id": "run-owned", "containerName": "ve-run-owned"}
            self.assertTrue(runtime._container_state(job)["OOMKilled"])
            self.assertTrue(runtime._remove_owned_container(job))
        self.assertIn(["/docker", "rm", "-f", "ve-run-owned"], calls)

    def test_container_ownership_requires_current_execution_attempt(self):
        def runner(command, **kwargs):
            labels = {
                "com.visioneval.workbench": "true",
                "com.visioneval.job": "run-owned",
                "com.visioneval.workspace": "workspace-one",
                "com.visioneval.attempt": "attempt-one",
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(labels), "")
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None), patch("backend.workbench.runtime.find_docker_executable", return_value="/docker"):
            runtime = RuntimeManager(Workspace(directory), runner=runner)
            runtime.workspace_id = "workspace-one"
            self.assertTrue(runtime._container_owned({"id":"run-owned","containerName":"ve-run-owned","workspaceId":"workspace-one","executionAttempt":"attempt-one"}))
            self.assertFalse(runtime._container_owned({"id":"run-owned","containerName":"ve-run-owned","workspaceId":"workspace-one","executionAttempt":"attempt-two"}))

    def test_only_oldest_unfinished_batch_is_eligible(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            jobs = [
                {"id":"run-a1","batchId":"batch-a","batchMode":"parallel","state":"waiting","queuePosition":1,"createdAt":"2026-01-01"},
                {"id":"run-a2","batchId":"batch-a","batchMode":"parallel","state":"waiting","queuePosition":2,"createdAt":"2026-01-01"},
                {"id":"run-b1","batchId":"batch-b","batchMode":"queued","state":"waiting","queuePosition":3,"createdAt":"2026-01-02"},
            ]
            for job in jobs:
                run = workspace.runs / job["id"]
                run.mkdir()
                write_json(run / "job.json", job)
            self.assertTrue(runtime._eligible_locked(jobs[0]))
            self.assertTrue(runtime._eligible_locked(jobs[1]))
            self.assertFalse(runtime._eligible_locked(jobs[2]))
            self.assertEqual(runtime._mode_lock_locked(), "parallel")

    def test_scoped_hypercube_stop_preserves_other_projects(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(RuntimeManager, "_dispatch_loop", return_value=None):
            workspace = Workspace(directory)
            project_dir = workspace.projects / "cube"; project_dir.mkdir()
            write_json(project_dir / "project.json", {"id":"cube","name":"Cube","projectType":"hypercube","variations":[],"runIds":[],"datastoreIds":[]})
            other_dir = workspace.projects / "other"; other_dir.mkdir()
            write_json(other_dir / "project.json", {"id":"other","name":"Other","projectType":"standard","variations":[],"runIds":[],"datastoreIds":[]})
            for job_id, project_id, position in (("cube-waiting","cube",1),("other-waiting","other",2)):
                run = workspace.runs / job_id; run.mkdir()
                write_json(run / "job.json", {"id":job_id,"projectId":project_id,"state":"waiting","queuePosition":position,"modelPath":str(workspace.models/job_id),"logPath":str(run/"run.log")})
                (run / "run.log").touch()
            runtime = RuntimeManager(workspace, runner=FakeRunner())
            result = runtime.stop_project("cube")
            self.assertEqual(result["removed"], 1)
            self.assertFalse((workspace.runs / "cube-waiting").exists())
            self.assertTrue((workspace.runs / "other-waiting").exists())


if __name__ == "__main__":
    unittest.main()
