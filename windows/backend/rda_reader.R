args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("Usage: Rscript rda_reader.R <file.Rda> [--metadata]", call. = FALSE)
metadata_mode <- "--metadata" %in% args
if (identical(args[[1]], "--csv")) {
  home <- Sys.getenv("VE_HOME", "")
  minor <- strsplit(R.version$minor, "\\.")[[1]][1]
  .libPaths(c(file.path(home, "ve-lib", paste(R.version$major, minor, sep=".")), .libPaths()))
  variable <- args[[2]]
  parts <- lapply(args[-c(1,2)], function(path) {
    columns <- names(data.table::fread(path, nrows=0, showProgress=FALSE))
    ids <- intersect(columns, c("HhId", "VehId", "WkrId", "Azone", "Bzone", "Marea"))
    selected <- intersect(columns, c("Scenario", "Global", "Year", ids, variable))
    data.table::fread(path, select=selected, colClasses=list(character=ids), showProgress=FALSE)
  })
  data <- Reduce(function(left, right) {
    join <- intersect(c("Scenario", "Global", "Year", "HhId", "VehId", "WkrId", "Azone", "Bzone", "Marea"), intersect(names(left), names(right)))
    if (!length(join)) stop("CSV partitions have no shared identity columns")
    extra <- setdiff(names(right), names(left))
    merge(left, right[, c(join, extra), with=FALSE], by=join, all=TRUE, sort=FALSE)
  }, parts)
  if (!variable %in% names(data)) stop("Variable is absent from CSV export: ", variable)
  values <- data[[variable]]
  cat(jsonlite::toJSON(list(values=values), auto_unbox=FALSE, na="null", digits=NA))
  quit(status=0)
}

json_escape <- function(x) {
  x <- gsub("\\\\", "\\\\\\\\", x)
  x <- gsub("\"", "\\\\\"", x)
  x <- gsub("\n", "\\\\n", x)
  x <- gsub("\r", "\\\\r", x)
  x <- gsub("\t", "\\\\t", x)
  x
}

json_value <- function(x) {
  if (length(x) == 0 || is.na(x)) return("null")
  if (is.numeric(x) || is.integer(x)) {
    if (is.finite(x)) return(as.character(x))
    return("null")
  }
  if (is.logical(x)) return(ifelse(x, "true", "false"))
  paste0("\"", json_escape(as.character(x)), "\"")
}

env <- new.env(parent = emptyenv())
loaded <- load(args[[1]], envir = env)
name <- loaded[[1]]
x <- env[[name]]
if (metadata_mode) {
  field <- function(a, key) {
    if (is.list(a) && !is.null(a[[key]]) && length(a[[key]]) > 0) return(as.character(a[[key]][[1]]))
    NA_character_
  }
  attrs <- x$attributes
  entries <- character()
  for (i in seq_along(attrs)) {
    a <- attrs[[i]]
    table <- field(a, "TABLE")
    variable <- field(a, "NAME")
    if (is.na(table) || is.na(variable)) next
    key <- paste0(table, "/", variable)
    entries <- c(entries, paste0(json_value(key), ":{",
      "\"table\":", json_value(table), ",",
      "\"name\":", json_value(variable), ",",
      "\"type\":", json_value(field(a, "TYPE")), ",",
      "\"units\":", json_value(field(a, "UNITS")), ",",
      "\"description\":", json_value(field(a, "DESCRIPTION")), ",",
      "\"module\":", json_value(field(a, "MODULE")), "}"))
  }
  cat(paste0("{", paste(entries, collapse = ","), "}"))
  quit(status = 0)
}
if (is.factor(x)) x <- as.character(x)
values <- if (is.list(x) && !is.data.frame(x)) c() else as.vector(x)
cat(paste0(
  "{\"object\":", json_value(name),
  ",\"class\":", json_value(paste(class(x), collapse = ",")),
  ",\"length\":", length(values),
  ",\"values\":[", paste(vapply(values, json_value, character(1)), collapse = ","), "]}"
))
