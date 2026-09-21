args <- commandArgs(trailingOnly=TRUE)
if (length(args) < 3) stop("Usage: hypercube_summary.R request.json output.json progress.json", call.=FALSE)
suppressPackageStartupMessages(library(jsonlite))
request <- fromJSON(args[[1]], simplifyVector=FALSE)
output_path <- args[[2]]; progress_path <- args[[3]]
micro_tables <- c("Household", "Vehicle", "Worker")

write_progress <- function(completed,total,table="",case_name="",phase="indexing",bytes=0,summaries=0) {
  write_json(list(completed=completed,total=total,table=table,current=case_name,phase=phase,
                  bytesRead=bytes,summariesWritten=summaries,heartbeatAt=format(Sys.time(),tz="UTC",usetz=TRUE)),
             progress_path,auto_unbox=TRUE,pretty=TRUE)
}
read_column <- function(root,year,table,name) {
  path <- file.path(root,year,table,paste0(name,".Rda")); if(!file.exists(path)) return(NULL)
  bytes <<- bytes + file.info(path)$size
  env <- new.env(parent=emptyenv()); loaded <- load(path,envir=env); value <- env[[loaded[[1]]]]
  if(is.factor(value)) value <- as.character(value)
  if(is.list(value) && !is.data.frame(value)) return(NULL)
  as.vector(value)
}
keyed_numeric <- function(value,keys) {
  if(is.null(value)||is.null(keys)||length(value)!=length(keys)) return(NULL)
  numeric_value <- suppressWarnings(as.numeric(value)); labels <- as.character(keys)
  valid <- is.finite(numeric_value)&!is.na(labels)&nzchar(labels)
  if(!any(valid)) return(NULL)
  # Duplicate keys are unexpected, but collapsing them makes discovery robust
  # to imperfect Datastore tables without misaligning rows.
  tapply(numeric_value[valid],labels[valid],mean)
}
aggregate_value <- function(value,method) {
  if(is.null(value) || !(is.numeric(value)||is.integer(value))) return(NA_real_)
  value <- as.numeric(value); value <- value[is.finite(value)]; if(!length(value)) return(NA_real_)
  if(method=="sum") sum(value) else if(method=="median") median(value) else if(method=="min") min(value) else if(method=="max") max(value) else mean(value)
}
percent_change <- function(left,right) {
  if(is.na(left)||is.na(right)||left==0) return(NA_real_)
  (right-left)/abs(left)*100
}

tables <- request$tables; cases <- request$cases; total <- sum(vapply(tables,function(item) length(cases),numeric(1)))
done <- 0; bytes <- 0; summaries <- 0; results <- list(); scenario_results <- list(); skipped <- list()
write_progress(0,total,phase="loading baseline")
for(table_record in tables) {
  table <- table_record$table; variables <- table_record$variables; baseline_root <- request$baseline$path
  stable <- !(table %in% micro_tables); key_name <- table_record$key
  baseline_keys <- if(stable && nzchar(key_name)) read_column(baseline_root,request$year,table,key_name) else NULL
  baseline_columns <- list(); accumulators <- list()
  for(variable in variables) {
    name <- variable$name; column <- read_column(baseline_root,request$year,table,name)
    baseline_columns[[name]] <- column
    baseline_value <- aggregate_value(column,variable$aggregation)
    accumulators[[name]] <- list(table=table,variable=name,units=variable$units,description=variable$description,
      largestOverallShift=0,largestTypicalRowShift=NA_real_,broadestChange=NA_real_,largestExtremeChange=NA_real_,availableCases=0,totalCases=length(cases),baselineValue=baseline_value)
    accumulators[[name]]$cells <- list()
  }
  for(case in cases) {
    case_keys <- if(stable && nzchar(key_name)) read_column(case$path,request$year,table,key_name) else NULL
    for(variable in variables) {
      name <- variable$name; left <- baseline_columns[[name]]; right <- read_column(case$path,request$year,table,name)
      if(is.null(left)||is.null(right)||!(is.numeric(left)||is.integer(left))||!(is.numeric(right)||is.integer(right))) next
      left_value <- aggregate_value(left,variable$aggregation); right_value <- aggregate_value(right,variable$aggregation); shift <- percent_change(left_value,right_value)
      item <- accumulators[[name]]
      typical <- NA_real_; breadth <- NA_real_; extreme <- NA_real_
      if(!is.na(shift)){item$largestOverallShift <- max(item$largestOverallShift,abs(shift));item$availableCases <- item$availableCases+1}
      if(stable && !is.null(baseline_keys) && !is.null(case_keys)) {
        left_map <- keyed_numeric(left,baseline_keys); right_map <- keyed_numeric(right,case_keys)
        if(!is.null(left_map)&&!is.null(right_map)) {
        common <- intersect(names(left_map),names(right_map)); a <- left_map[common]; b <- right_map[common]; valid <- is.finite(a)&is.finite(b);a<-a[valid];b<-b[valid]
        if(length(a)){changed <- round(a,5)!=round(b,5); denom<-abs(a)+abs(b);symmetric<-ifelse(denom>0,200*abs(b-a)/denom,0);typical<-mean(symmetric);breadth<-mean(changed)*100;extreme<-max(abs(b-a));item$largestTypicalRowShift<-max(c(item$largestTypicalRowShift,typical),na.rm=TRUE);item$broadestChange<-max(c(item$broadestChange,breadth),na.rm=TRUE);item$largestExtremeChange<-max(c(item$largestExtremeChange,extreme),na.rm=TRUE)}
        }
      }
      item$cells[[length(item$cells)+1]] <- list(variationId=case$id,name=case$name,caseIndex=case$caseIndex,values=case$values,scenarioValue=right_value,referenceValue=left_value,absoluteChange=right_value-left_value,percentChange=shift,typicalRowChange=typical,breadth=breadth,extremeRowChange=extreme,aggregation=variable$aggregation)
      accumulators[[name]] <- item
    }
    done <- done+1;summaries <- summaries+length(variables)
    write_progress(done,total,table,case$name,"indexing case table",bytes,summaries)
  }
  for(name in names(accumulators)) {item<-accumulators[[name]];if(item$availableCases>0){scenario_results[[length(scenario_results)+1]]<-list(table=item$table,variable=item$variable,cells=item$cells);if(item$largestOverallShift>0)results[[length(results)+1]]<-item}}
  write_json(list(projectId=request$projectId,year=request$year,sourceFingerprint=request$sourceFingerprint,datastoreFingerprint=request$datastoreFingerprint,results=results,scenarioOutputs=scenario_results,skipped=skipped,scanned=summaries,partial=done<total),output_path,auto_unbox=TRUE,pretty=TRUE,na="null",digits=NA)
}
results <- results[order(vapply(results,function(item)-item$largestOverallShift,numeric(1)))]
write_json(list(projectId=request$projectId,year=request$year,sourceFingerprint=request$sourceFingerprint,datastoreFingerprint=request$datastoreFingerprint,results=results,scenarioOutputs=scenario_results,skipped=skipped,scanned=summaries,generatedAt=format(Sys.time(),tz="UTC",usetz=TRUE)),output_path,auto_unbox=TRUE,pretty=TRUE,na="null",digits=NA)
write_progress(total,total,phase="complete",bytes=bytes,summaries=summaries)
