args <- commandArgs(trailingOnly = TRUE)
source_root <- if (length(args)) args[[1]] else "/opt/visioneval/source"
package_root <- file.path(source_root, "sources", "optional", "VETravelDemandMM")

if (!dir.exists(package_root)) {
  stop("VETravelDemandMM source was not found at ", package_root)
}

read_text <- function(path) paste(readLines(path, warn = FALSE), collapse = "\n")
write_text <- function(path, value) writeLines(strsplit(value, "\n", fixed = TRUE)[[1]], path, useBytes = TRUE)
replace_once <- function(value, old, new, label) {
  count <- lengths(regmatches(value, gregexpr(old, value, fixed = TRUE)))
  if (count != 1L) stop("Expected exactly one ", label, " match; found ", count)
  sub(old, new, value, fixed = TRUE)
}

align_source <- c(
  "# Workbench compatibility helper for VisionEval VE-40-RC6.",
  "# Align predictions with the datastore's complete, original household IDs.",
  "AlignPredictions <- function(Preds_df, HouseholdIds_) {",
  "  if (!\"id\" %in% names(Preds_df)) stop(\"Prediction results do not contain an id field.\", call. = FALSE)",
  "  if (!\"y\" %in% names(Preds_df)) stop(\"Prediction results do not contain a y field.\", call. = FALSE)",
  "  HouseholdIds_ <- as.character(HouseholdIds_)",
  "  PredictionIds_ <- as.character(Preds_df$id)",
  "  if (anyNA(HouseholdIds_) || any(!nzchar(HouseholdIds_))) stop(\"Household IDs contain missing or blank values.\", call. = FALSE)",
  "  if (anyDuplicated(HouseholdIds_)) stop(\"Household IDs contain duplicate values.\", call. = FALSE)",
  "  if (anyNA(PredictionIds_) || any(!nzchar(PredictionIds_))) stop(\"Prediction results contain missing or blank household IDs.\", call. = FALSE)",
  "  if (anyDuplicated(PredictionIds_)) stop(\"Prediction results contain duplicate household IDs.\", call. = FALSE)",
  "  MissingIds_ <- HouseholdIds_[!HouseholdIds_ %in% PredictionIds_]",
  "  if (length(MissingIds_)) stop(\"Predictions are missing for \", length(MissingIds_), \" household IDs.\", call. = FALSE)",
  "  UnexpectedIds_ <- PredictionIds_[!PredictionIds_ %in% HouseholdIds_]",
  "  if (length(UnexpectedIds_)) stop(\"Prediction results contain \", length(UnexpectedIds_), \" unexpected household IDs.\", call. = FALSE)",
  "  Aligned_ <- Preds_df$y[match(HouseholdIds_, PredictionIds_)]",
  "  if (length(Aligned_) != length(HouseholdIds_)) stop(\"Aligned prediction length does not match household count.\", call. = FALSE)",
  "  if (any(!is.finite(Aligned_))) stop(\"Aligned predictions contain missing or non-finite values.\", call. = FALSE)",
  "  Aligned_",
  "}"
)
writeLines(align_source, file.path(package_root, "R", "AlignPredictions.R"), useBytes = TRUE)

description_path <- file.path(package_root, "DESCRIPTION")
description <- read_text(description_path)
if (!grepl("VEAlignmentPatch:", description, fixed = TRUE)) {
  description <- replace_once(
    description,
    "Version: 3.1.1",
    paste("Version: 3.1.1", "VEAlignmentPatch: 2026-08-03-composite-household-id-alignment", sep = "\n"),
    "DESCRIPTION version"
  )
}
description <- replace_once(
  description,
  "Collate:\n    VETravelDemandMM.R",
  "Collate:\n    VETravelDemandMM.R\n    AlignPredictions.R",
  "DESCRIPTION Collate"
)
write_text(description_path, description)

household_path <- file.path(package_root, "R", "CalculateHouseholdDvmt.R")
household <- read_text(household_path)
household <- replace_once(
  household,
  "dataset_name, id_name, y_name, SegmentCol_vc)",
  "dataset_name, id_name, y_name, SegmentCol_vc, merge_preds=FALSE)",
  "household prediction call"
)
household <- replace_once(
  household,
  "  #Apply the 95th percentile model\n  #-------------------------------\n  D_df$Dvmt <- Preds[[\"y\"]]\n  D_df$DvmtSq <- Preds[[\"y\"]] ^ 2\n  D_df$DvmtCu <- Preds[[\"y\"]] ^ 3",
  "  Dvmt_Hh <- AlignPredictions(Preds, D_df$HhId)\n\n  #Apply the 95th percentile model\n  #-------------------------------\n  D_df$Dvmt <- Dvmt_Hh\n  D_df$DvmtSq <- Dvmt_Hh ^ 2\n  D_df$DvmtCu <- Dvmt_Hh ^ 3",
  "household aligned values"
)
household <- replace_once(household, "      Dvmt = Preds[[\"y\"]],", "      Dvmt = Dvmt_Hh,", "household output")
write_text(household_path, household)

alt_path <- file.path(package_root, "R", "CalculateAltModeTrips.R")
alt <- read_text(alt_path)
plain_call <- "dataset_name, id_name, y_name, SegmentCol_vc)"
plain_count <- lengths(regmatches(alt, gregexpr(plain_call, alt, fixed = TRUE)))
if (plain_count != 3L) stop("Expected three AltMode prediction calls; found ", plain_count)
alt <- gsub(plain_call, "dataset_name, id_name, y_name, SegmentCol_vc, merge_preds=FALSE)", alt, fixed = TRUE)
alt <- replace_once(alt, "Out_ls$Year$Household$WalkPMT <- Preds[[\"y\"]]", "Out_ls$Year$Household$WalkPMT <- AlignPredictions(Preds, D_df$HhId)", "WalkPMT output")
alt <- replace_once(alt, "Out_ls$Year$Household$BikePMT <- Preds[[\"y\"]]", "Out_ls$Year$Household$BikePMT <- AlignPredictions(Preds, D_df$HhId)", "BikePMT output")
alt <- replace_once(alt, "Out_ls$Year$Household$TransitPMT <- Preds[[\"y\"]]", "Out_ls$Year$Household$TransitPMT <- AlignPredictions(Preds, D_df$HhId)", "TransitPMT output")
for (mode in c("Walk", "Bike", "Transit")) {
  alt <- replace_once(
    alt,
    paste0("  Out_ls$Year$Household$", mode, "Trips       <- (Preds %>% filter(Step==1) %>% pull(y)) *365\n  Out_ls$Year$Household$", mode, "AvgTripDist <- Preds %>% filter(Step==2) %>% pull(y)"),
    paste0("  ", mode, "TripPreds_df <- Preds %>% filter(Step==1)\n  ", mode, "DistPreds_df <- Preds %>% filter(Step==2)\n  Out_ls$Year$Household$", mode, "Trips <- AlignPredictions(", mode, "TripPreds_df, D_df$HhId) * 365\n  Out_ls$Year$Household$", mode, "AvgTripDist <- AlignPredictions(", mode, "DistPreds_df, D_df$HhId)"),
    paste0(mode, " TFL outputs")
  )
}
write_text(alt_path, alt)

cat("Applied VETravelDemandMM composite household-ID alignment patch.\n")
