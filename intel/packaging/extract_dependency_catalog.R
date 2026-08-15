args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) stop("Usage: Rscript extract_dependency_catalog.R <VisionEval source> <output.csv>")

source_root <- normalizePath(args[[1]], mustWork = TRUE)
output <- args[[2]]
files <- list.files(file.path(source_root, "sources", "modules"), pattern = "Specifications\\.rda$", recursive = TRUE, full.names = TRUE)
modules_root <- normalizePath(file.path(source_root, "sources", "modules"), mustWork = TRUE)

flatten <- function(value) {
  if (is.null(value)) return(character())
  as.character(unlist(value, recursive = TRUE, use.names = FALSE))
}

rows <- list()
index <- 1L
for (file in files) {
  relative <- substring(normalizePath(file), nchar(modules_root) + 2L)
  package <- strsplit(relative, "/", fixed = TRUE)[[1]][[1]]
  module <- sub("Specifications\\.rda$", "", basename(file))
  env <- new.env(parent = emptyenv())
  loaded <- load(file, envir = env)
  spec <- env[[if (paste0(module, "Specifications") %in% loaded) paste0(module, "Specifications") else loaded[[1]]]]
  for (section in c("Inp", "Get", "Set")) {
    items <- spec[[section]]
    if (is.null(items)) next
    for (item in items) {
      names_out <- flatten(item$NAME)
      if (!length(names_out)) next
      descriptions <- flatten(item$DESCRIPTION)
      if (!length(descriptions)) descriptions <- ""
      descriptions <- rep(descriptions, length.out = length(names_out))
      for (i in seq_along(names_out)) {
        rows[[index]] <- data.frame(
          package = package,
          module = module,
          section = section,
          table = paste(flatten(item$TABLE), collapse = "|"),
          group = paste(flatten(item$GROUP), collapse = "|"),
          name = names_out[[i]],
          file = paste(flatten(item$FILE), collapse = "|"),
          units = paste(flatten(item$UNITS), collapse = "|"),
          type = paste(flatten(item$TYPE), collapse = "|"),
          description = descriptions[[i]],
          stringsAsFactors = FALSE
        )
        index <- index + 1L
      }
    }
  }
}

result <- if (length(rows)) unique(do.call(rbind, rows)) else data.frame()
write.csv(result, output, row.names = FALSE, na = "")
cat(sprintf("Extracted %d declarations from %d module specifications.\n", nrow(result), length(files)))
