# Explore Inputs and Dependencies

Explore has two subtabs: **Input File Library** and **Dependencies**.

![Explore tab with an empty, privacy-safe demonstration workspace](images/explore.png)

## Input File Library

On a fresh install, Workbench shows built-in VisionEval input metadata so you can browse common input files before installing any package. After a package is installed, choose its InputLibrary for the model-specific file list and authoritative package details. Select a CSV file to see:

- The file's purpose and geography level.
- Field names, descriptions, data types, and display units.
- The metadata source and unresolved warnings.
- Longer explanations when a guide package is available.
- A link to view the file in Dependencies.

Built-in metadata is useful for orientation, but installed packages provide the actual model/InputLibrary files, package-specific fields, and explanation guides used by projects.

Check the selected model's documentation whenever its files or modules have been customized.

## Dependencies

Choose a dependency source before exploring dependencies. Workbench derives the network from an installed or imported model template when one is available. If no template is installed, a completed run may provide enough model context for a dependency source; otherwise run a scenario or install/import a model template first.

The network opens as a compact, ordered overview of the executed modules. Drag its background to pan, scroll or pinch to zoom, and use **−**, **+**, **100%**, or **Fit** for precise control. The minimap shows which part of the model is visible. Search centers an overview node; press Return to focus any matching input, table, file, module, or package.

You can focus by input file, input field, executed module, datastore intermediary, or stored output. File and field focus answer “what reads this selection directly?” and separate the selected source, modules using it, and values those modules write. When you click a module, Workbench keeps the **Selected path** first. Use **Full module context** to add every other file column and earlier model value the module reads. Breadcrumbs preserve each step you follow.

Focused module lanes describe roles in the selected operation: **Source files**, **Values read** (separated into file columns and prior model values), **Selected module**, and **Values written**. A value stored elsewhere in the model appears under prior model values when it is being read here. Values written counts only direct outputs of the selected module. Equivalent file-input and datastore-read declarations are displayed once.

Modules chosen directly from the toolbar or search open in full module context. Modules reached from a file or field offer both scopes. **Show Full Model** returns to the ordered overview.

Intermediaries and stored outputs open in **How produced**. This view shows the selected value’s one exact producing step: the producer’s direct files, columns, and earlier values, the producing module, and only the selected value. Select an earlier value to continue tracing upstream without opening hundreds of nodes at once. **Where used** shows only later modules that directly read the selected value; the producing module is never mixed into that list. Framework values with no declared producer open in **Where used** and state that their source was not declared.

Use **SVG** to save a single infinitely scalable canvas. **PDF** creates a vector document; large full-model graphs are tiled across readable landscape pages while focused paths normally fit on one page.

In the full overview, colors and labels distinguish:

- Scenario inputs.
- Executed modules.
- Datastore values/intermediaries.
- Stored outputs.
- Unresolved custom modules.

An input file may be installed but unused by the selected model. Workbench labels it **Not used by this model's execution path** instead of creating a relationship.

## Reading the network correctly

A path means an executed module declares that it reads the input or datastore value and a downstream producer/consumer relationship exists. It does not measure sensitivity, prove causation, or guarantee a numerical result change.

In a focused module view, **Values from earlier steps** are datastore values the selected module reads. When the graph knows the producing step, the value is labeled **From _number_. _ModuleName_**. Values without a preceding declared `Set` are labeled **Loaded earlier — source not declared**; Workbench does not invent a producer for framework-initialized values. These labels describe model execution lineage and do not require the user to change scenario inputs.

After running scenarios, Compare provides observed evidence about which outputs actually changed.

For implementation details, module source, and the broader VisionEval project, see the [official VisionEval User Guide](https://visioneval.github.io/docs/) and [official VisionEval repository](https://github.com/VisionEval/VisionEval).
