args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 6) stop("Usage: comparison_cache_extract.R <root> <year> <table> <key-or-dash> <output> <variable...>", call.=FALSE)

root <- args[[1]]; year <- args[[2]]; table <- args[[3]]; key_name <- args[[4]]; output <- args[[5]]
variables <- args[6:length(args)]
dir.create(output, recursive=TRUE, showWarnings=FALSE)

read_values <- function(name) {
  path <- file.path(root, year, table, paste0(name, ".Rda"))
  if (!file.exists(path)) stop(paste("Missing", table, name), call.=FALSE)
  env <- new.env(parent=emptyenv()); loaded <- load(path, envir=env); value <- env[[loaded[[1]]]]
  if (is.factor(value)) value <- as.character(value)
  if (is.list(value) && !is.data.frame(value)) stop(paste(table, name, "is not a scalar column"), call.=FALSE)
  as.vector(value)
}

first <- read_values(variables[[1]])
if (key_name == "-") {
  if (length(first) > 1) stop(paste(table, "has no safe stable key"), call.=FALSE)
  keys <- if (length(first)) "1" else character()
} else if (table == "Region") {
  if (length(first) > 1) stop("Region has multiple rows but no stable key", call.=FALSE)
  keys <- if (length(first)) "Region" else character()
} else {
  keys <- trimws(as.character(read_values(key_name)))
  if (any(!nzchar(keys))) stop("Blank stable key", call.=FALSE)
  if (anyDuplicated(keys)) stop("Duplicate stable key", call.=FALSE)
}

write.table(data.frame(row_index=seq_along(keys)-1L, entity_key=keys, stringsAsFactors=FALSE),
            file.path(output, "keys.tsv"), sep="\t", quote=TRUE, row.names=FALSE, na="")

skipped <- data.frame(variable=character(), reason=character(), stringsAsFactors=FALSE)
for (i in seq_along(variables)) {
  value <- if (i == 1) first else read_values(variables[[i]])
  if (length(value) != length(keys)) {
    skipped <- rbind(skipped, data.frame(
      variable=variables[[i]],
      reason=paste0(table, "/", variables[[i]], " cannot be aligned safely: ", length(value),
                    " values for ", length(keys), " ", key_name, " keys"),
      stringsAsFactors=FALSE
    ))
    next
  }
  numeric_kind <- is.numeric(value) || is.integer(value)
  null <- is.na(value) | (numeric_kind & !is.finite(value))
  numeric_value <- if (numeric_kind) as.numeric(value) else rep(NA_real_, length(value))
  text_value <- if (numeric_kind) rep(NA_character_, length(value)) else as.character(value)
  compare_value <- if (numeric_kind) round(numeric_value, 5) else rep(NA_real_, length(value))
  frame <- data.frame(row_index=seq_along(value)-1L, is_null=as.integer(null), numeric_value=numeric_value,
                      text_value=text_value, compare_value=compare_value, stringsAsFactors=FALSE)
  write.table(frame, file.path(output, paste0("column_", i, ".tsv")), sep="\t", quote=TRUE,
              row.names=FALSE, na="")
  writeLines(if (numeric_kind) "numeric" else "categorical", file.path(output, paste0("column_", i, ".kind")))
}

write.table(skipped, file.path(output, "skipped.tsv"), sep="\t", quote=TRUE,
            row.names=FALSE, na="")
