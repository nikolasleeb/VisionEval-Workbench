FROM rocker/r-ver:4.5.1 AS builder

ARG DEBIAN_FRONTEND=noninteractive
ARG VISIONEVAL_REPOSITORY=https://github.com/VisionEval/VisionEval-4.git
ARG VISIONEVAL_REF=VE-40-RC6
ARG VISIONEVAL_COMMIT=f7ef3389b5626daeba6c86eeda9d172a0f8cccc2

RUN sed -i 's|http://ports.ubuntu.com|https://ports.ubuntu.com|g' /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true \
    && apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates cmake git libbz2-dev libcurl4-openssl-dev \
    libfontconfig1-dev libfreetype6-dev libfribidi-dev libgdal-dev libgeos-dev \
    libgit2-dev libglpk-dev libharfbuzz-dev libhdf5-dev libicu-dev libjpeg-dev \
    liblzma-dev libpng-dev libproj-dev libsqlite3-dev libssl-dev libtiff-dev \
    libudunits2-dev libuv1-dev libxml2-dev make pkg-config tcl8.6 tk8.6 zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/visioneval
RUN git clone --branch "${VISIONEVAL_REF}" --depth 1 "${VISIONEVAL_REPOSITORY}" source \
    && cd source \
    && test "$(git rev-parse HEAD)" = "${VISIONEVAL_COMMIT}"

ENV VE_HOME=/opt/visioneval/source \
    VE_SOURCE=/opt/visioneval/source/sources \
    VE_BUILD=/opt/visioneval/build \
    VE_RUNTIME=/opt/visioneval/runtime \
    MAKEFLAGS=-j1
WORKDIR /opt/visioneval/source
COPY scripts/build-ve4-dependencies.R /opt/visioneval/build-ve4-dependencies.R
RUN Rscript --vanilla /opt/visioneval/build-ve4-dependencies.R

COPY scripts/apply-planrva-alignment-patch.R /opt/visioneval/apply-planrva-alignment-patch.R
RUN Rscript --vanilla /opt/visioneval/apply-planrva-alignment-patch.R /opt/visioneval/source

COPY scripts/build-ve4.R /opt/visioneval/build-ve4.R
RUN Rscript --vanilla /opt/visioneval/build-ve4.R \
    && test -d /opt/visioneval/source/ve-lib/4.5 \
    && printf '%s\n' \
      'repository=https://github.com/VisionEval/VisionEval-4' \
      'tag=VE-40-RC6' \
      'commit=f7ef3389b5626daeba6c86eeda9d172a0f8cccc2' \
      'r_version=4.5.1' \
      'distribution=unofficial-workbench-runtime' \
      'compatibility_patch=2026-08-03-composite-household-id-alignment' \
      'compatibility_patch_status=unofficial' \
      'compatibility_patch_target=VETravelDemandMM::DoPredictions' \
      > /opt/visioneval/RELEASE

FROM rocker/r-ver:4.5.1
ARG DEBIAN_FRONTEND=noninteractive
ARG VISIONEVAL_COMMIT=f7ef3389b5626daeba6c86eeda9d172a0f8cccc2
ARG WORKBENCH_VERSION=1.0.0
ARG BUILD_REVISION=local
LABEL org.opencontainers.image.title="VisionEval Workbench Runtime" \
      org.opencontainers.image.description="Unofficial Workbench runtime built from official VisionEval VE-40-RC6 with a Workbench PlanRVA composite household-ID compatibility patch" \
      org.opencontainers.image.source="https://github.com/nikolasleeb/VisionEval-Workbench" \
      org.opencontainers.image.url="https://github.com/nikolasleeb/VisionEval-Workbench" \
      org.opencontainers.image.documentation="https://github.com/nikolasleeb/VisionEval-Workbench/blob/main/macos/docs/user-macos/setup.md" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${WORKBENCH_VERSION}-ve-40-rc6-planrva-arm64" \
      org.opencontainers.image.revision="${BUILD_REVISION}" \
      org.opencontainers.image.architecture="arm64" \
      com.visioneval.upstream.repository="https://github.com/VisionEval/VisionEval-4" \
      com.visioneval.upstream.release="VE-40-RC6" \
      com.visioneval.upstream.revision="${VISIONEVAL_COMMIT}" \
      com.visioneval.workbench.compatibility-patch="2026-08-03-composite-household-id-alignment" \
      com.visioneval.workbench.compatibility-patch-status="unofficial" \
      com.visioneval.workbench.compatibility-patch-target="VETravelDemandMM::DoPredictions" \
      com.visioneval.workbench.compatibility-patch-description="Restores prediction ordering for composite household identifiers used by the PlanRVA multimodal model"
RUN sed -i 's|http://ports.ubuntu.com|https://ports.ubuntu.com|g' /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true \
    && apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libcurl4-openssl-dev libgdal-dev libgeos-dev libgit2-dev \
    libglpk-dev libhdf5-dev libicu-dev libjpeg-dev libpng-dev libproj-dev \
    libsqlite3-dev libssl-dev libtiff-dev libudunits2-dev libuv1-dev libxml2-dev \
    tcl8.6 tk8.6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/visioneval/source /opt/visioneval/source
COPY --from=builder /opt/visioneval/RELEASE /opt/visioneval/RELEASE
COPY NOTICE /opt/visioneval/WORKBENCH-NOTICE
COPY scripts/ve-cli.R /opt/visioneval/ve-cli.R
COPY scripts/entrypoint.sh /usr/local/bin/visioneval
RUN chmod +x /usr/local/bin/visioneval \
    && mkdir -p /workspace/models /workspace/runs /workspace/exchange/inbox /workspace/exchange/outbox
ENV VE_HOME=/opt/visioneval/source \
    VE_RUNTIME=/workspace \
    R_LIBS_USER=/opt/visioneval/source/ve-lib/4.5
WORKDIR /
VOLUME ["/workspace"]
ENTRYPOINT ["/usr/local/bin/visioneval"]
CMD ["help"]
