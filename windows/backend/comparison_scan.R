args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) stop("Usage: comparison_scan.R request.json output.json progress.json", call. = FALSE)
suppressPackageStartupMessages(library(jsonlite))

request <- fromJSON(args[[1]], simplifyVector = FALSE)
output_path <- args[[2]]
progress_path <- args[[3]]
keys_by_table <- list(Household="HhId", Vehicle="VehId", Worker="WkrId", Azone="Azone", Bzone="Bzone", Marea="Marea")
key_cache <- new.env(parent=emptyenv(), hash=TRUE)

write_progress <- function(done, total, table="", variable="", phase="scanning") {
  write_json(list(completed=done, total=total, table=table, variable=variable, phase=phase), progress_path, auto_unbox=TRUE, pretty=TRUE)
}

read_values <- function(root, year, table, variable) {
  path <- file.path(root, year, table, paste0(variable, ".Rda"))
  if (!file.exists(path)) return(NULL)
  env <- new.env(parent=emptyenv()); loaded <- load(path, envir=env); value <- env[[loaded[[1]]]]
  if (is.factor(value)) value <- as.character(value)
  if (is.list(value) && !is.data.frame(value)) return(NULL)
  as.vector(value)
}

keyed <- function(root, year, table, variable) {
  values <- read_values(root, year, table, variable)
  if (is.null(values)) stop(paste("Missing", table, variable))
  key_name <- keys_by_table[[table]]
  if (is.null(key_name)) {
    if (length(values) > 1) stop(paste(table, "has no safe stable key"))
    return(list(order=if(length(values)) "1" else character(), values=setNames(values, "1")))
  }
  cache_key <- paste(root, year, table, key_name, sep="\r")
  if (exists(cache_key, envir=key_cache, inherits=FALSE)) {
    keys <- get(cache_key, envir=key_cache, inherits=FALSE)
  } else {
    keys <- if (variable == key_name) values else read_values(root, year, table, key_name)
    if (!is.null(keys)) assign(cache_key, keys, envir=key_cache)
  }
  if (is.null(keys) || length(keys) != length(values)) stop("Key/value length mismatch")
  keys <- trimws(as.character(keys))
  if (any(!nzchar(keys)) || anyDuplicated(keys)) stop("Blank or duplicate stable key")
  list(order=keys, values=setNames(values, keys))
}

location_keys <- function(record, table, keys, field, selected) {
  if (!nzchar(field) || !length(selected)) return(keys)
  selected <- tolower(unlist(selected))
  location_field <- field
  lookup <- NULL
  if (field == "County") {
    az <- file.exists(file.path(record$path, request$year, table, "Azone.Rda")) || table == "Azone"
    bz <- file.exists(file.path(record$path, request$year, table, "Bzone.Rda")) || table == "Bzone"
    location_field <- if (az) "Azone" else if (bz) "Bzone" else ""
    if (!nzchar(location_field)) return(character())
    lookup <- record$county[[tolower(location_field)]]
  }
  locations <- tryCatch(keyed(record$path, request$year, table, location_field)$values, error=function(e) NULL)
  if (is.null(locations)) return(character())
  raw <- unname(locations[keys])
  labels <- as.character(raw)
  if (!is.null(lookup)) {
    lookup <- unlist(lookup, use.names=TRUE)
    labels <- unname(lookup[tolower(labels)])
  }
  keys[!is.na(labels) & tolower(labels) %in% selected]
}

summarize_pair <- function(reference, comparison, keys) {
  left <- unname(reference[keys]); right <- unname(comparison[keys])
  left_na <- is.na(left); right_na <- is.na(right); matched <- !left_na & !right_na
  if (is.numeric(reference) && is.numeric(comparison)) {
    changed <- xor(left_na, right_na) | (matched & round(left, 5) != round(right, 5))
    left_num <- as.numeric(left[matched]); right_num <- as.numeric(right[matched])
  } else {
    changed <- xor(left_na, right_na) | (matched & as.character(left) != as.character(right))
    left_num <- numeric(); right_num <- numeric()
  }
  delta <- right_num-left_num
  left_sum <- if(length(left_num)) sum(left_num) else NA_real_; right_sum <- if(length(right_num)) sum(right_num) else NA_real_
  list(rowsCompared=length(keys), rowsChanged=sum(changed), rowsIncreased=sum(delta>0), rowsDecreased=sum(delta<0),
       rowsUnchanged=sum(delta==0), netChange=if(length(delta)) sum(delta) else NA_real_,
       totalPercentChange=if(!is.na(left_sum) && left_sum != 0 && !is.na(right_sum)) (right_sum-left_sum)/left_sum*100 else NA_real_,
       rowsChangedPercent=if(length(keys)) sum(changed)/length(keys)*100 else NA_real_,
       averageRowPercentChange=if(any(left_num != 0)) mean((right_num[left_num != 0]-left_num[left_num != 0])/abs(left_num[left_num != 0])*100) else NA_real_)
}

results <- list(); skipped <- list(); total <- length(request$variables); write_progress(0, total, phase="loading_metadata")
for (i in seq_along(request$variables)) {
  item <- request$variables[[i]]; write_progress(i-1, total, item$table, item$name, "scanning")
  tryCatch({
    columns <- lapply(request$records, function(record) keyed(record$path, request$year, item$table, item$name))
    keys <- unique(unlist(lapply(columns, function(column) column$order), use.names=FALSE))
    if (nzchar(request$filterField) && length(request$filterValues)) {
      matched <- character()
      for (j in seq_along(request$records)) matched <- union(matched, location_keys(request$records[[j]], item$table, keys, request$filterField, request$filterValues))
      keys <- keys[keys %in% matched]
    }
    pairs <- list(); changed_rows <- 0
    for (j in 2:length(columns)) {
      pair <- summarize_pair(columns[[1]]$values, columns[[j]]$values, keys); pair$label <- request$records[[j]]$label
      pairs[[length(pairs)+1]] <- pair; changed_rows <- max(changed_rows, pair$rowsChanged)
    }
    if (changed_rows > 0) results[[length(results)+1]] <- list(table=item$table, variable=item$name, changedRows=changed_rows, totalRows=length(keys), percentRowsChanged=if(length(keys)) changed_rows/length(keys)*100 else 0, units=item$units, description=item$description, pairStats=pairs)
  }, error=function(error) skipped[[length(skipped)+1]] <<- list(table=item$table, variable=item$name, reason=conditionMessage(error)))
  write_progress(i, total, item$table, item$name, "scanning")
}
results <- results[order(vapply(results, function(x) -x$changedRows, numeric(1)))]
write_json(list(year=request$year, scanned=total, changedVariables=length(results), results=results, skipped=skipped,
                filterField=request$filterField, filterValues=request$filterValues), output_path, auto_unbox=TRUE, pretty=TRUE, na="null")
