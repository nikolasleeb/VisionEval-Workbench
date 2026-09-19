args <- commandArgs(trailingOnly = TRUE)
command <- if (length(args)) args[[1]] else "help"
command_args <- if (length(args) > 1) args[-1] else character()
runtime <- normalizePath(Sys.getenv("VE_RUNTIME", "/workspace"), mustWork = FALSE)
home <- normalizePath(Sys.getenv("VE_HOME", "/opt/visioneval/source"), mustWork = TRUE)
dir.create(runtime, recursive = TRUE, showWarnings = FALSE)
Sys.setenv(VE_RUNTIME = runtime, VE_HOME = home)
library_path <- file.path(home, "ve-lib", paste(R.version$major, strsplit(R.version$minor, "\\.")[[1]][1], sep = "."))
.libPaths(c(library_path, .libPaths()))
library(VEStart)
startVisionEval(ve.home = home, ve.runtime = runtime, overwrite = FALSE)
# VisionEval normalizes absolute model paths to ./workspace/... internally. Resolve those
# from the filesystem root rather than from /workspace/workspace.
setwd("/")

usage <- function(status = 0L) {
  cat(paste(
    "VisionEval Workbench VE-40-RC7 ARM64 runtime", "", "Commands:",
    "  help", "  doctor", "  verify-upstream-release", "  verify-household-id-alignment", "  list",
    "  install-sample [name]", "  run <model> [reset|save]", "  export <model>", "  shell", "",
    "Host workspace contract: /workspace/models, /workspace/runs, /workspace/exchange", sep = "\n"))
  quit(save = "no", status = status)
}
if (command == "help") usage()

if (command == "doctor") {
  required <- c("VEStart", "VEModel", "VETravelDemandMM")
  missing <- setdiff(required, rownames(installed.packages()))
  release <- if (file.exists("/opt/visioneval/RELEASE")) paste(readLines("/opt/visioneval/RELEASE", warn = FALSE), collapse = "\n") else "release metadata missing"
  cat("VisionEval runtime: OK\nRelease: VE-40-RC7\nR:", R.version.string, "\nArchitecture:", R.version$arch, "\nRuntime:", runtime, "\nPackages:", paste(required, collapse = ", "), "\n", release, "\n")
  if (length(missing)) stop("Missing packages: ", paste(missing, collapse = ", "))
  quit(save = "no", status = 0L)
}

if (command == "verify-upstream-release") {
  package_path <- find.package("VETravelDemandMM")
  namespace <- asNamespace("VETravelDemandMM")
  release <- readLines("/opt/visioneval/RELEASE", warn = FALSE)
  do_predictions <- get("DoPredictions", namespace)
  function_text <- paste(deparse(body(do_predictions)), collapse = "\n")
  stopifnot(
    "merge_preds" %in% names(formals(do_predictions)),
    grepl("alignPredictionRows", function_text, fixed = TRUE),
    grepl("Dataset_df[[id_name]]", function_text, fixed = TRUE),
    any(release == "tag=VE-40-RC7"),
    any(release == "commit=7852dc58fad460ff279f5eebf4dd55fe191470ad"),
    any(release == "runtime_api=1")
  )
  cat("Active package:", package_path, "\nUpstream source: VisionEval/VisionEval-4 VE-40-RC7\nOfficial full-household-ID ordering implementation: present\n")
  quit(save = "no", status = 0L)
}

if (command == "verify-household-id-alignment") {
  package_path <- find.package("VETravelDemandMM")
  namespace <- asNamespace("VETravelDemandMM")
  release <- readLines("/opt/visioneval/RELEASE", warn = FALSE)
  align <- get("alignPredictionRows", namespace)
  align_text <- paste(deparse(body(align)), collapse = "\n")
  stopifnot(
    any(release == "compatibility_patch=none"),
    any(release == "household_id_alignment=official-upstream"),
    grepl("match(DatasetIds_, PredictionIds_)", align_text, fixed = TRUE),
    grepl("anyDuplicated", align_text, fixed = TRUE)
  )

  household_ids <- c("51001-1", "51003-1", "51001-2", "51003-2")
  predictions <- data.frame(
    id = c("51003-1", "51001-2", "51003-2", "51001-1"),
    y = c(30, 20, 40, 10),
    stringsAsFactors = FALSE
  )
  aligned <- align(predictions, household_ids)
  stopifnot(
    identical(as.character(aligned$id), household_ids),
    identical(as.numeric(aligned$y), c(10, 30, 20, 40))
  )

  nonnumeric_ids <- c("Azone-A/HH-alpha", "Azone-B/HH-alpha", "Azone-A/HH-beta", "Azone-B/HH-beta")
  nonnumeric_predictions <- data.frame(
    id = c("Azone-B/HH-beta", "Azone-A/HH-alpha", "Azone-B/HH-alpha", "Azone-A/HH-beta"),
    y = c(4, 1, 2, 3),
    stringsAsFactors = FALSE
  )
  nonnumeric_aligned <- align(nonnumeric_predictions, nonnumeric_ids)
  stopifnot(
    identical(as.character(nonnumeric_aligned$id), nonnumeric_ids),
    identical(as.numeric(nonnumeric_aligned$y), c(1, 2, 3, 4))
  )

  expect_error <- function(expression) {
    message <- tryCatch({ force(expression); "" }, error = conditionMessage)
    if (!nzchar(message)) stop("Expected the official alignment helper to reject invalid household identities")
  }
  expect_error(align(predictions[-1, ], household_ids))
  duplicate_predictions <- predictions
  duplicate_predictions$id[[2]] <- duplicate_predictions$id[[1]]
  expect_error(align(duplicate_predictions, household_ids))

  cat("Active package:", package_path, "\nOfficial RC7 complete household-ID alignment: verified\n")
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
  model_path <- if (grepl("^/", model_name)) model_name else file.path(runtime, "models", model_name)
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
