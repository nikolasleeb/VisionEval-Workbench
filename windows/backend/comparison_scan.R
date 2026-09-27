args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) stop("Usage: comparison_scan.R request.json output.json progress.json", call. = FALSE)
if (identical(tolower(Sys.getenv("VISIONEVAL_RUNTIME_ADAPTER", "")), "native")) {
  ve_home <- normalizePath(Sys.getenv("VE_HOME", ""), mustWork = TRUE)
  r_minor <- strsplit(R.version$minor, "\\.")[[1]][1]
  .libPaths(c(file.path(ve_home, "ve-lib", paste(R.version$major, r_minor, sep = ".")), .libPaths()))
}
suppressPackageStartupMessages(library(jsonlite))

request <- fromJSON(args[[1]], simplifyVector = FALSE)
output_path <- args[[2]]
progress_path <- args[[3]]
keys_by_table <- list(Household="HhId", Vehicle="VehId", Worker="WkrId", Azone="Azone", Bzone="Bzone", Marea="Marea")
key_cache <- new.env(parent=emptyenv(), hash=TRUE)
csv_cache <- new.env(parent=emptyenv())

write_progress <- function(done, total, table="", variable="", phase="scanning") {
  write_json(list(completed=done, total=total, table=table, variable=variable, phase=phase), progress_path, auto_unbox=TRUE, pretty=TRUE)
}

read_values <- function(root, year, table, variable) {
  record <- Filter(function(item) identical(item$path, root), request$records)[[1]]
  files <- record$csvTables[[paste(year, table, sep="/")]]
  if (length(files)) {
    token <- paste(root, year, table, sep="\r")
    if (!exists(token, csv_cache, inherits=FALSE)) {
      # Keep only the current table across selected results, not the whole run.
      current <- paste(year, table, sep="/")
      if (!identical(csv_cache$current, current)) {
        rm(list=ls(csv_cache), envir=csv_cache); csv_cache$current <- current
      }
      parts <- lapply(files, function(file) {
        columns <- names(data.table::fread(file, nrows=0, showProgress=FALSE))
        ids <- intersect(columns, unlist(keys_by_table))
        data.table::fread(file, colClasses=list(character=ids), showProgress=FALSE)
      })
      data <- if (length(parts) == 1L) parts[[1]] else Reduce(function(left, right) {
        join <- intersect(c("Scenario", "Global", "Year", keys_by_table[[table]]), intersect(names(left), names(right)))
        if (!length(join)) stop("CSV partitions have no shared identity columns")
        extra <- setdiff(names(right), names(left))
        merge(left, right[, c(join, extra), with=FALSE], by=join, all=TRUE, sort=FALSE)
      }, parts)
      assign(token, data, csv_cache)
    }
    data <- get(token, csv_cache)
    if (!variable %in% names(data)) return(NULL)
    return(data[[variable]])
  }
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
  if (table == "Region") {
    if (length(values) > 1) stop("Region has multiple rows but no stable key")
    return(list(order=if(length(values)) "Region" else character(), values=setNames(values, "Region")))
  }
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

summary_values <- function(values) {
  numbers <- if (is.numeric(values)) values[is.finite(values)] else numeric()
  if (length(numbers)) {
    q <- quantile(numbers, c(0, .25, .5, .75, 1), names=FALSE)
    return(list(kind="numeric", count=length(values), recordCount=length(values), numericCount=length(numbers),
                missingCount=length(values)-length(numbers), sum=sum(numbers), mean=mean(numbers),
                min=q[1], q1=q[2], median=q[3], q3=q[4], max=q[5]))
  }
  present <- as.character(values[!is.na(values)])
  labels <- unique(present); counts <- tabulate(match(present, labels), nbins=length(labels))
  order <- order(-counts, labels); labels <- labels[order]; counts <- counts[order]
  categories <- lapply(head(seq_along(labels), 50), function(i) list(label=labels[i], count=counts[i], share=counts[i]/length(present)*100))
  top <- lapply(head(seq_along(labels), 10), function(i) list(label=labels[i], count=counts[i]))
  list(kind="categorical", count=length(values), recordCount=length(values), numericCount=0,
       missingCount=length(values)-length(present), categories=categories, topCategories=top,
       distinctCategories=length(labels), categoriesTruncated=length(labels)>50,
       distribution=list(labels=labels, counts=counts))
}
public_summary <- function(summary) { summary$distribution <- NULL; summary }
percent <- function(left, right) {
  if (is.null(left) || is.null(right)) return(NULL)
  if (left == 0) return(if (right == 0) 0 else NULL)
  (right-left)/abs(left)*100
}

results <- list(); summaries_all <- list(); skipped <- list(); total <- length(request$variables); write_progress(0, total, phase="loading_metadata")
for (i in seq_along(request$variables)) {
  item <- request$variables[[i]]; write_progress(i-1, total, item$table, item$name, "scanning")
  tryCatch({
    if (item$table %in% c("Household", "Vehicle", "Worker")) {
      # Synthetic row IDs do not identify the same people across runs.
      summaries <- lapply(request$records, function(record) {
        values <- read_values(record$path, request$year, item$table, item$name)
        if (is.null(values)) stop(paste("Missing", item$table, item$name))
        if (nzchar(request$filterField) && length(request$filterValues)) {
          keys <- trimws(as.character(read_values(record$path, request$year, item$table, keys_by_table[[item$table]])))
          if (length(keys) != length(values)) stop("Key/value length mismatch")
          allowed <- location_keys(record, item$table, keys, request$filterField, request$filterValues)
          values <- values[keys %in% allowed]
        }
        summary_values(values)
      })
      base <- summaries[[1]]; changed <- FALSE; pairs <- list()
      for (j in seq.int(2, length(summaries))) {
        other <- summaries[[j]]
        measures <- c("recordCount", "numericCount", "missingCount", "sum", "mean")
        for (measure in measures) {
          left <- base[[measure]]; right <- other[[measure]]
          if (!is.null(left) && !is.null(right) && left != right) changed <- TRUE
        }
        # Compare the full compact distribution internally, but never serialize
        # millions of per-category objects into scan results.
        if (!identical(base$distribution, other$distribution)) changed <- TRUE
        pairs[[length(pairs)+1]] <- list(label=request$records[[j]]$label,
          rowsCompared=NULL, matchedRows=NULL, unmatchedRows=NULL, rowsChanged=NULL,
          rowsIncreased=NULL, rowsDecreased=NULL, rowsUnchanged=NULL,
          netChange=if (!is.null(base$sum) && !is.null(other$sum)) other$sum-base$sum else NULL,
          totalPercentChange=percent(base$sum, other$sum), rowsChangedPercent=NULL,
          averageRowPercentChange=NULL, reference=public_summary(base), comparison=public_summary(other), identitySemantics="run_local_synthetic")
      }
      if (changed) {
        rows <- max(vapply(summaries, function(x) x$recordCount, numeric(1)))
        results[[length(results)+1]] <- list(table=item$table, variable=item$name, changedRows=1,
          totalRows=rows, percentRowsChanged=if(rows) 100/rows else 0, units=item$units,
          description=item$description, pairStats=pairs,
          totalPercentChanges=lapply(pairs, function(pair) list(label=pair$label, value=pair$totalPercentChange)))
      }
      summaries_all[[length(summaries_all)+1]] <- list(table=item$table, variable=item$name,
        reference=public_summary(base), comparisons=lapply(summaries[-1], public_summary), totalRows=max(vapply(summaries, function(x) x$recordCount, numeric(1))),
        changedRows=if(changed) 1 else 0)
    } else {
    columns <- lapply(request$records, function(record) keyed(record$path, request$year, item$table, item$name))
    keys <- unique(unlist(lapply(columns, function(column) column$order), use.names=FALSE))
    if (nzchar(request$filterField) && length(request$filterValues)) {
      matched <- character()
      for (j in seq_along(request$records)) matched <- union(matched, location_keys(request$records[[j]], item$table, keys, request$filterField, request$filterValues))
      keys <- keys[keys %in% matched]
    }
    pairs <- list(); changed_flags <- rep(FALSE, length(keys))
    for (j in 2:length(columns)) {
      pair <- summarize_pair(columns[[1]]$values, columns[[j]]$values, keys); pair$label <- request$records[[j]]$label
      pairs[[length(pairs)+1]] <- pair
      left <- unname(columns[[1]]$values[keys]); right <- unname(columns[[j]]$values[keys])
      matched <- !is.na(left) & !is.na(right)
      different <- if (is.numeric(left) && is.numeric(right)) round(left,5) != round(right,5) else as.character(left) != as.character(right)
      flags <- xor(is.na(left), is.na(right)) | (matched & different); flags[is.na(flags)] <- FALSE
      changed_flags <- changed_flags | flags
    }
    changed_rows <- sum(changed_flags)
    summaries_all[[length(summaries_all)+1]] <- list(table=item$table, variable=item$name,
      reference=public_summary(summary_values(unname(columns[[1]]$values[keys]))),
      comparisons=lapply(columns[-1], function(column) public_summary(summary_values(unname(column$values[keys])))),
      totalRows=length(keys), changedRows=changed_rows)
    if (changed_rows > 0) results[[length(results)+1]] <- list(table=item$table, variable=item$name, changedRows=changed_rows, totalRows=length(keys), percentRowsChanged=if(length(keys)) changed_rows/length(keys)*100 else 0, units=item$units, description=item$description, pairStats=pairs)
    }
  }, error=function(error) skipped[[length(skipped)+1]] <<- list(table=item$table, variable=item$name, reason=conditionMessage(error)))
  write_progress(i, total, item$table, item$name, "scanning")
}
write_progress(total, total, phase="finalizing")
results <- results[order(vapply(results, function(x) -x$changedRows, numeric(1)))]
write_json(list(summaryVersion=1, summaries=summaries_all, year=request$year, scanned=total, changedVariables=length(results), results=results, skipped=skipped,
                filterField=request$filterField, filterValues=request$filterValues), output_path, auto_unbox=TRUE, pretty=TRUE, na="null", digits=NA)
