args <- commandArgs(trailingOnly = TRUE)
command <- if (length(args)) args[[1]] else "help"
command_args <- if (length(args) > 1) args[-1] else character()
native <- identical(tolower(Sys.getenv("VISIONEVAL_RUNTIME_ADAPTER", "docker")), "native")
runtime <- normalizePath(Sys.getenv("VE_RUNTIME", "/workspace"), mustWork = FALSE)
home <- normalizePath(Sys.getenv("VE_HOME", "/opt/visioneval/source"), mustWork = TRUE)
dir.create(runtime, recursive = TRUE, showWarnings = FALSE)
Sys.setenv(VE_RUNTIME = runtime, VE_HOME = home)
library_path <- file.path(home, "ve-lib", paste(R.version$major, strsplit(R.version$minor, "\\.")[[1]][1], sep = "."))
if (native && !dir.exists(library_path)) {
  stop("VE_HOME does not contain the R ", paste(R.version$major, strsplit(R.version$minor, "\\.")[[1]][1], sep = "."), " library: ", library_path)
}
.libPaths(c(library_path, .libPaths()))
library(VEStart)
startVisionEval(ve.home = home, ve.runtime = runtime, overwrite = FALSE)
# RC6 normalizes model paths internally. Docker resolves its /workspace path from
# the filesystem root; native Windows uses paths relative to VE_RUNTIME so drive
# letters are never rewritten as relative directory names.
if (native) setwd(runtime) else setwd("/")

release_file <- Sys.getenv("VE_RELEASE_METADATA", if (native) file.path(home, "WORKBENCH-RELEASE") else "/opt/visioneval/RELEASE")

usage <- function(status = 0L) {
  cat(paste(
    paste("VisionEval Workbench", if (native) "native runtime" else "container runtime"), "", "Commands:",
    "  help", "  doctor", "  verify-capabilities", "  verify-model <model>", "  verify-upstream-release", "  verify-alignment-patch", "  list",
    "  install-sample [name]", "  run <model> [reset|save]", "  export <model>", "  shell", "",
    "Host workspace contract: /workspace/models, /workspace/runs, /workspace/exchange", sep = "\n"))
  quit(save = "no", status = status)
}

if (command == "verify-capabilities") {
  required <- list(VEStart = c("startVisionEval"), VEModel = c("openModel", "runModule"))
  missing <- character()
  for (package in names(required)) {
    namespace <- asNamespace(package)
    for (name in required[[package]]) {
      if (!exists(name, envir = namespace, inherits = FALSE)) missing <- c(missing, paste0(package, "::", name))
    }
  }
  for (entry in list(c("VETravelDemandMM", "CalculateHouseholdDvmt"), c("VETravelDemandMM", "CalculateAltModeTrips"))) {
    error <- visioneval:::checkModuleExists(entry[[2]], entry[[1]])
    if (length(error)) missing <- c(missing, paste0(entry[[1]], "::", entry[[2]], " (not registered)"))
  }
  if (length(missing)) stop("Missing required VisionEval capabilities: ", paste(missing, collapse = ", "))
  packages <- c("visioneval", "VEStart", "VEModel", "VETravelDemandMM")
  versions <- vapply(packages, function(package) if (requireNamespace(package, quietly = TRUE)) as.character(packageVersion(package)) else "missing", character(1))
  if (native) {
    expected_library <- normalizePath(library_path, winslash = "/", mustWork = TRUE)
    outside <- packages[vapply(packages, function(package) {
      package_path <- normalizePath(find.package(package), winslash = "/", mustWork = TRUE)
      !startsWith(tolower(package_path), paste0(tolower(expected_library), "/"))
    }, logical(1))]
    if (length(outside)) stop("VisionEval packages were loaded outside the selected VE_HOME R library: ", paste(outside, collapse = ", "))
  }
  cat("Native VisionEval capabilities: OK\n")
  framework_version <- versions[["VEStart"]]
  cat("WORKBENCH_RUNTIME_INFO|", paste0("VisionEval=", framework_version), "|R=", as.character(getRversion()), "|Packages=", paste(paste0(names(versions), "=", versions), collapse = ";"), "\n", sep = "")
  quit(save = "no", status = 0L)
}
if (command == "help") usage()

if (command == "doctor") {
  required <- c("VEStart", "VEModel", "VETravelDemandMM")
  missing <- setdiff(required, rownames(installed.packages()))
  release <- if (file.exists(release_file)) paste(readLines(release_file, warn = FALSE), collapse = "\n") else "release metadata missing"
  cat("VisionEval runtime: OK\nR:", R.version.string, "\nArchitecture:", R.version$arch, "\nVE_HOME:", home, "\nVE_RUNTIME:", runtime, "\nPackages:", paste(required, collapse = ", "), "\n", release, "\n")
  if (length(missing)) stop("Missing packages: ", paste(missing, collapse = ", "))
  quit(save = "no", status = 0L)
}

if (command == "verify-model") {
  if (!length(command_args) || !nzchar(command_args[[1]])) stop("A model directory is required")
  model_path <- normalizePath(command_args[[1]], mustWork = TRUE)
  script <- file.path(model_path, "scripts", "run_model.R")
  if (!file.exists(script)) stop("Model run script does not exist: ", script)
  text <- paste(readLines(script, warn = FALSE), collapse = "\n")
  pattern <- "runModule\\s*\\(\\s*['\"]([^'\"]+)['\"]\\s*,\\s*['\"]([^'\"]+)['\"]"
  matches <- regmatches(text, gregexpr(pattern, text, perl = TRUE))[[1]]
  if (!length(matches)) stop("No literal runModule calls were found in ", script)
  errors <- character()
  for (match in matches) {
    module <- sub(pattern, "\\1", match, perl = TRUE)
    package <- sub(pattern, "\\2", match, perl = TRUE)
    error <- tryCatch(visioneval:::checkModuleExists(module, package), error = conditionMessage)
    if (length(error)) errors <- c(errors, paste0(package, "::", module, ": ", paste(error, collapse = " ")))
  }
  if (length(errors)) stop("The selected VisionEval installation cannot run this model:\n", paste(unique(errors), collapse = "\n"))
  cat("Model module compatibility: OK (", length(matches), " calls checked)\n", sep = "")
  quit(save = "no", status = 0L)
}

if (command == "verify-upstream-release") {
  package_path <- find.package("VETravelDemandMM")
  namespace <- asNamespace("VETravelDemandMM")
  release <- readLines(release_file, warn = FALSE)
  do_predictions <- get("DoPredictions", namespace)
  function_text <- paste(deparse(body(do_predictions)), collapse = "\n")
  stopifnot(
    "merge_preds" %in% names(formals(do_predictions)),
    grepl("p_order", function_text, fixed = TRUE),
    grepl("Dataset_df[[id_name]]", function_text, fixed = TRUE),
    any(release == "tag=VE-40-RC6"),
    any(release == "commit=f7ef3389b5626daeba6c86eeda9d172a0f8cccc2")
  )
  cat("Active package:", package_path, "\nUpstream source: VisionEval/VisionEval-4 VE-40-RC6\nPinned upstream household-ordering implementation: present\n")
  quit(save = "no", status = 0L)
}

if (command == "verify-alignment-patch") {
  package_path <- find.package("VETravelDemandMM")
  namespace <- asNamespace("VETravelDemandMM")
  release <- readLines(release_file, warn = FALSE)
  patch_id <- "2026-08-03-composite-household-id-alignment"
  align <- get("AlignPredictions", namespace)
  household_text <- paste(deparse(body(get("CalculateHouseholdDvmt", namespace))), collapse = "\n")
  alt_mode_text <- paste(deparse(body(get("CalculateAltModeTrips", namespace))), collapse = "\n")
  stopifnot(
    identical(packageDescription("VETravelDemandMM")[["VEAlignmentPatch"]], patch_id),
    any(release == paste0("compatibility_patch=", patch_id)),
    any(release == "compatibility_patch_status=unofficial"),
    any(release == "compatibility_patch_target=VETravelDemandMM::DoPredictions"),
    grepl("AlignPredictions", household_text, fixed = TRUE),
    grepl("AlignPredictions", alt_mode_text, fixed = TRUE),
    grepl("merge_preds = FALSE", household_text, fixed = TRUE),
    grepl("merge_preds = FALSE", alt_mode_text, fixed = TRUE)
  )

  household_ids <- c("Charles City County-1", "Charles City County-2", "Chesterfield County-1", "Chesterfield County-2")
  predictions <- data.frame(
    id = c("Chesterfield County-1", "Charles City County-2", "Chesterfield County-2", "Charles City County-1"),
    y = c(30, 20, 40, 10),
    stringsAsFactors = FALSE
  )
  stopifnot(identical(align(predictions, household_ids), c(10, 20, 30, 40)))

  expect_error <- function(expression, pattern) {
    message <- tryCatch({ force(expression); "" }, error = conditionMessage)
    if (!grepl(pattern, message, fixed = TRUE)) stop("Expected alignment error containing: ", pattern)
  }
  expect_error(align(predictions[-1, ], household_ids), "missing for 1 household IDs")
  duplicate_predictions <- predictions
  duplicate_predictions$id[[2]] <- duplicate_predictions$id[[1]]
  expect_error(align(duplicate_predictions, household_ids), "duplicate household IDs")
  non_finite_predictions <- predictions
  non_finite_predictions$y[[1]] <- Inf
  expect_error(align(non_finite_predictions, household_ids), "non-finite values")

  cat("Active package:", package_path, "\nCompatibility patch:", patch_id, "\nComposite household-ID alignment: verified\n")
  quit(save = "no", status = 0L)
}

if (command == "list") {
  cat("Installed models:\n")
  model_dirs <- list.dirs(file.path(runtime, "models"), full.names = FALSE, recursive = FALSE)
  if (length(model_dirs)) cat(paste0("  ", model_dirs, collapse = "\n"), "\n") else cat("  (none)\n")
  cat("\nAvailable templates:\n")
  print(installModel("", confirm = FALSE))
  quit(save = "no", status = 0L)
}

if (command == "install-sample") {
  model_name <- if (length(command_args) && nzchar(command_args[[1]])) command_args[[1]] else "VERSPM-MM-Sample"
  installModel("VERSPM", variant = "mm", modelPath = model_name, confirm = FALSE, overwrite = FALSE)
  cat("Installed multimodal sample as", model_name, "\n")
  quit(save = "no", status = 0L)
}

if (command %in% c("run", "export")) {
  if (!length(command_args) || !nzchar(command_args[[1]])) { cat("A model name is required.\n\n"); usage(2L) }
  model_name <- command_args[[1]]
  model_path <- if (grepl("^/", model_name) || grepl("^[A-Za-z]:[/\\\\]", model_name)) model_name else if (native) file.path("models", model_name) else file.path(runtime, "models", model_name)
  if (!dir.exists(model_path)) stop("Model directory does not exist: ", model_path)
  model <- openModel(model_path)
  if (command == "run") {
    mode <- if (length(command_args) > 1) command_args[[2]] else NULL
    if (is.null(mode)) model$run() else model$run(mode)
    cat("Model run finished:", model_name, "\n")
  } else {
    results <- model$results(); results$export(); cat("Model export finished:", model_name, "\n")
  }
  quit(save = "no", status = 0L)
}

if (command == "shell") {
  cat("VisionEval loaded. Runtime:", runtime, "\n")
  if (!interactive()) system2("R", c("--no-save", "--no-restore"))
  quit(save = "no", status = 0L)
}
cat("Unknown command:", command, "\n\n"); usage(2L)
