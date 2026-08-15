import json
import tempfile
import unittest
from pathlib import Path

from backend.workbench.dependencies import DependencyService
from backend.workbench.workspace import Workspace, WorkspaceError, write_json


class DependencyTests(unittest.TestCase):
    def test_builtin_catalog_does_not_claim_execution_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root / "workspace")
            catalog = root / "catalog.json"
            write_json(catalog, {"visionEvalVersion": "4.0", "modules": {
                "Example::Second": {"id": "Example::Second", "package": "Example", "name": "Second", "Inp": [], "Get": [{"table": "Azone", "name": "Result"}], "Set": []},
                "Example::First": {"id": "Example::First", "package": "Example", "name": "First", "Inp": [{"file": "input.csv", "table": "Azone", "name": "Value"}], "Get": [], "Set": [{"table": "Azone", "name": "Result"}]},
            }})
            service = DependencyService(workspace, catalog)
            graph = service.graph("__builtin_module_catalog__", mode="catalog")
            self.assertEqual(graph["graphMode"], "catalog")
            self.assertFalse(graph["executionOrderAvailable"])
            self.assertIn("actual execution order", graph["notice"])
            self.assertEqual(graph["template"]["name"], "VisionEval module catalog")
            result = next(node for node in graph["nodes"] if node["id"] == "catalog:Azone/Result")
            self.assertEqual(result["kind"], "variable")
            self.assertTrue(result["storedOutput"])
            self.assertTrue(result["intermediary"])
            focused = service.graph("__builtin_module_catalog__", "file:input.csv", mode="catalog")
            self.assertEqual(focused["focusView"]["kind"], "file")
            self.assertIn("catalog:Azone/Result", {node["id"] for node in focused["nodes"]})

    def test_template_graph_connects_input_through_nearest_set_get_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root / "workspace")
            template_id = "template-test"
            template = workspace.templates / template_id
            (template / "scripts").mkdir(parents=True)
            (template / "inputs").mkdir()
            (template / "defs").mkdir()
            (template / "scripts" / "run_model.R").write_text(
                'runModule("Producer", "TestPkg")\nrunModule("Consumer", "TestPkg")\nrunModule("Custom", "CustomPkg")\nrunModule("Unknown", "CustomPkg")\n',
                encoding="utf-8",
            )
            (template / "inputs" / "policy.csv").write_text("Geo,Year,Policy\nA,2045,1\n", encoding="utf-8")
            (template / "inputs" / "policy2.csv").write_text("Geo,Year,Modifier\nA,2045,2\n", encoding="utf-8")
            (template / "inputs" / "unused.csv").write_text("Geo,Year,Unused\nA,2045,1\n", encoding="utf-8")
            (template / "defs" / "units.csv").write_text("Type,Units\nnumber,MODEL_UNIT\n", encoding="utf-8")
            (template / "defs" / "module_specifications.csv").write_text(
                "package,module,section,table,group,name,file,units,type,description\n"
                "CustomPkg,Custom,Get,Result,Year,Output,,OUT,number,Custom consumer\n",
                encoding="utf-8",
            )
            write_json(template / "workbench_template.json", {
                "id": template_id, "name": "Test model", "fingerprint": "fingerprint",
            })
            catalog = root / "catalog.json"
            write_json(catalog, {"visionEvalVersion": "3.1.1", "modules": {
                "TestPkg::Producer": {
                    "Inp": [
                        {"file": "policy.csv", "table": "PolicyTable", "name": "Policy", "type": "number", "units": "SPEC_UNIT", "description": "Policy input"},
                        {"file": "policy2.csv", "table": "PolicyTable", "name": "Modifier", "type": "number", "units": "SPEC_UNIT", "description": "Second input"},
                    ],
                    "Get": [
                        {"table": "PolicyTable", "name": "Policy", "units": "SPEC_UNIT"},
                        {"table": "Source", "name": "Existing", "units": "COUNT"},
                    ],
                    "Set": [{"table": "Store", "name": "Middle", "units": "MID", "description": "Intermediate"}],
                },
                "TestPkg::Consumer": {
                    "Inp": [],
                    "Get": [{"table": "Store", "name": "Middle", "units": "MID"}],
                    "Set": [{"table": "Result", "name": "Output", "units": "OUT", "description": "Result output"}],
                },
            }})
            graph = DependencyService(workspace, catalog).graph(template_id)
            self.assertEqual(graph["graphMode"], "execution")
            self.assertTrue(graph["executionOrderAvailable"])
            by_id = {item["id"]: item for item in graph["nodes"]}
            self.assertTrue(by_id["file:policy.csv"]["active"])
            self.assertFalse(by_id["file:unused.csv"]["active"])
            self.assertEqual(by_id["input:policy.csv:Policy"]["units"], "MODEL_UNIT")
            self.assertIn("executing module declares SPEC_UNIT", by_id["input:policy.csv:Policy"]["unitWarning"])
            middle = next(item for item in graph["nodes"] if item.get("variableId") == "Store/Middle")
            output = next(item for item in graph["nodes"] if item.get("variableId") == "Result/Output")
            self.assertTrue(middle["intermediary"])
            self.assertTrue(output["storedOutput"])
            self.assertEqual(graph["unknownModules"], ["CustomPkg::Unknown"])
            self.assertTrue(by_id["module:CustomPkg::Custom"]["supported"])
            focused = DependencyService(workspace, catalog).graph(template_id, "file:policy.csv")
            focused_ids = {item["id"] for item in focused["nodes"]}
            self.assertIn(middle["id"], focused_ids)
            self.assertNotIn(output["id"], focused_ids)
            self.assertEqual(focused["counts"]["modules"], 1)
            next_step = DependencyService(workspace, catalog).graph(template_id, middle["id"], view="consumers")
            self.assertIn("module:TestPkg::Consumer", {item["id"] for item in next_step["nodes"]})
            module_id = "module:TestPkg::Producer"
            path = DependencyService(workspace, catalog).graph(template_id, module_id, "path", "file:policy.csv")
            self.assertEqual(path["focusView"]["roleCounts"], {
                "sourceFiles": 1, "fileColumns": 1, "priorValues": 0, "modules": 1, "valuesWritten": 1,
                "directEffectValues": 0, "producingModules": 0, "selectedValues": 0, "consumerModules": 0,
            })
            self.assertEqual({node["id"] for node in path["nodes"] if node.get("viewRole") == "source-file"}, {"file:policy.csv"})

            context = DependencyService(workspace, catalog).graph(template_id, module_id, "context", "file:policy.csv")
            self.assertEqual(context["focusView"]["roleCounts"], {
                "sourceFiles": 2, "fileColumns": 2, "priorValues": 1, "modules": 1, "valuesWritten": 1,
                "directEffectValues": 0, "producingModules": 0, "selectedValues": 0, "consumerModules": 0,
            })
            context_ids = {node["id"] for node in context["nodes"]}
            self.assertIn("file:policy2.csv", context_ids)
            self.assertNotIn("source:PolicyTable/Policy", context_ids)
            self.assertIn("source:Source/Existing", context_ids)
            with self.assertRaisesRegex(WorkspaceError, "not connected"):
                DependencyService(workspace, catalog).graph(template_id, module_id, "path", "file:unused.csv")

            compatibility = DependencyService(workspace, catalog).graph(template_id, module_id)
            self.assertEqual(compatibility["focusView"]["scope"], "context")
            self.assertEqual(graph["layout"]["version"], 4)
            self.assertEqual(context["layout"]["version"], 4)
            self.assertEqual([group["label"] for group in context["layout"]["groups"]], ["File columns", "Values from earlier steps"])
            existing = next(node for node in context["nodes"] if node["id"] == "source:Source/Existing")
            self.assertEqual(existing["upstreamSource"], {"type": "existing", "label": "Loaded earlier — source not declared"})

            consumer = DependencyService(workspace, catalog).graph(template_id, "module:TestPkg::Consumer", "context")
            prior = next(node for node in consumer["nodes"] if node.get("viewRole") == "prior-value")
            self.assertEqual(prior["upstreamSource"], {
                "type": "module", "moduleId": "module:TestPkg::Producer", "order": 1,
                "label": "Producer", "package": "TestPkg",
            })
            self.assertIn(b"From 1. Producer", DependencyService(workspace, catalog).svg(template_id, "module:TestPkg::Consumer", "context"))

            produced = DependencyService(workspace, catalog).graph(template_id, middle["id"])
            self.assertEqual(produced["focusView"]["kind"], "value")
            self.assertEqual(produced["focusView"]["view"], "production")
            self.assertEqual({node["id"] for node in produced["nodes"] if node.get("viewRole") == "producer-module"}, {"module:TestPkg::Producer"})
            self.assertEqual({node["id"] for node in produced["nodes"] if node.get("viewRole") == "selected-value"}, {middle["id"]})
            self.assertNotIn(output["id"], {node["id"] for node in produced["nodes"]})
            self.assertEqual([item["value"] for item in produced["focusView"]["metrics"]], [2, 2, 1, 1, 1])

            used = DependencyService(workspace, catalog).graph(template_id, middle["id"], view="consumers")
            self.assertEqual(used["focusView"]["view"], "consumers")
            self.assertEqual({node["id"] for node in used["nodes"] if node.get("viewRole") == "consumer-module"}, {"module:TestPkg::Consumer"})
            self.assertNotIn("module:TestPkg::Producer", {node["id"] for node in used["nodes"]})

            framework = DependencyService(workspace, catalog).graph(template_id, "source:Source/Existing")
            self.assertEqual(framework["focusView"]["view"], "consumers")
            self.assertFalse(framework["focusView"]["navigation"]["canShowProduction"])
            with self.assertRaisesRegex(WorkspaceError, "production or consumers"):
                DependencyService(workspace, catalog).graph(template_id, middle["id"], view="everything")
            self.assertEqual(set(graph["layout"]["nodes"]), {item["id"] for item in graph["nodes"]})
            self.assertTrue(all(position["x"] >= 0 and position["y"] >= 0 for position in graph["layout"]["nodes"].values()))
            repeated = DependencyService(workspace, catalog).graph(template_id)
            self.assertEqual(graph["layout"], repeated["layout"])
            overview_svg = DependencyService(workspace, catalog).svg(template_id)
            overview_pdf = DependencyService(workspace, catalog).pdf(template_id)
            overview_html = DependencyService(workspace, catalog).html(template_id)
            self.assertIn(b"Execution sequence", overview_svg)
            self.assertNotIn(b"policy.csv", overview_svg)
            self.assertTrue(overview_pdf.startswith(b"%PDF-1.4"))
            self.assertNotIn(b"page 2 of", overview_pdf)
            self.assertTrue(overview_html.startswith(b"<!doctype html>"))
            self.assertIn(b"<svg", overview_html)
            self.assertIn(b"Execution overview", overview_html)
            self.assertNotIn(b"policy.csv", overview_html)
            svg = DependencyService(workspace, catalog).svg(template_id, module_id, "path", "file:policy.csv")
            pdf = DependencyService(workspace, catalog).pdf(template_id, module_id, "path", "file:policy.csv")
            html_export = DependencyService(workspace, catalog).html(template_id, module_id, "path", "file:policy.csv")
            self.assertTrue(svg.startswith(b'<svg xmlns="http://www.w3.org/2000/svg"'))
            self.assertIn(b"policy.csv", svg)
            self.assertTrue(pdf.startswith(b"%PDF-1.4"))
            self.assertIn(b"dependency graph", pdf)
            self.assertTrue(html_export.startswith(b"<!doctype html>"))
            self.assertIn(b"policy.csv", html_export)


if __name__ == "__main__":
    unittest.main()
