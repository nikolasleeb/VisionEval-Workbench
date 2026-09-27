suppressPackageStartupMessages(library(jsonlite))
root <- "/fixture"
for (run in c("reference","comparison")) {
  for (table in c("Azone","Household")) dir.create(file.path(root,run,"2045",table),recursive=TRUE,showWarnings=FALSE)
  store <- function(table,name,value) save(value,file=file.path(root,run,"2045",table,paste0(name,".Rda")))
  store("Azone","Azone",c("001","002"))
  store("Azone","Same",c(10,20))
  store("Azone","Changed",if(run=="reference") c(10,20) else c(15,25))
  store("Household","HhId",if(run=="reference") c("a","b") else c("b","a"))
  store("Household","Value",if(run=="reference") c(10,20) else c(20,10))
}
request <- list(year="2045",filterField="",filterValues=list(),
  records=lapply(c("reference","comparison"),function(run) list(id=run,label=run,path=file.path(root,run),county=list())),
  variables=lapply(c("Same","Changed","Value"),function(name) list(table=if(name=="Value") "Household" else "Azone",name=name,units="",description="")))
write_json(request,file.path(root,"request.json"),auto_unbox=TRUE)
system2("Rscript",c("/audit/comparison_scan.R",file.path(root,"request.json"),file.path(root,"output.json"),file.path(root,"progress.json")))
result <- fromJSON(file.path(root,"output.json"),simplifyVector=FALSE)
stopifnot(result$scannerVersion==4, result$summaryVersion==1, length(result$summaries)==3,
          length(result$results)==1, length(result$skipped)==0,
          result$summaries[[3]]$pairStats[[1]]$rowsChanged==0,
          result$summaries[[2]]$pairStats[[1]]$comparison$sum==40)
cat("Real Docker scanner fixtures passed: unchanged summaries, leading-zero keys, synthetic ID reorder, numeric totals.\n")
