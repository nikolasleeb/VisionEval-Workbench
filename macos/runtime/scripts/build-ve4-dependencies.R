options(repos = c(CRAN = "https://cloud.r-project.org"))

bootstrap <- file.path(getwd(), "VE-Bootstrap.R")
if (!file.exists(bootstrap)) stop("Official VE-Bootstrap.R was not found")
source(bootstrap)

# Resolve and install the external dependency set in a dedicated Docker layer.
# VisionEval package assembly then remains quick to retry without changing the
# pinned upstream source or dependency resolution semantics.
builder_environment <- as.environment("ve.builder")
build_function <- get("ve.build", envir = builder_environment)
build_private <- environment(build_function)
get("ve.build.config", envir = builder_environment)()
package_descriptions <- get("ve.get.targets", envir = build_private)("")
get("ve.load.dependencies", envir = build_private)(package_descriptions)
