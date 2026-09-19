function syncWorkbenchViewport() {
  const visualHeight = window.visualViewport?.height || window.innerHeight || document.documentElement.clientHeight;
  // visualViewport.height is already expressed in CSS pixels after browser/app
  // zoom. Dividing it by scale a second time makes dialogs unnecessarily tall
  // or short on Windows display scaling changes.
  const height = Math.max(320, Math.floor(visualHeight));
  document.documentElement.style.setProperty('--workbench-viewport-height', `${height}px`);
}
syncWorkbenchViewport();
window.visualViewport?.addEventListener('resize', syncWorkbenchViewport);
window.visualViewport?.addEventListener('scroll', syncWorkbenchViewport);
window.addEventListener('resize', syncWorkbenchViewport);

const state = {
  data: null,
  updateNotificationKey: "",
  selectedProject: null,
  csv: null,
  selectedJob: null,
  logSource: null,
  comparisonIds: [],
  variables: [],
  lastComparison: null,
  editorVariationId: "",
  editorFileName: "",
  editorMode: "file",
  editorBaselineRows: [],
  editorOriginalRows: [],
  editorUndo: [],
  editorRedo: [],
  editorPendingOperations: [],
  editorSavedOperations: [],
  editorManualEdit: false,
  batchFiles: {},
  batchBaselineFiles: {},
  batchSelectedFiles: new Set(),
  batchSelectedColumns: new Map(),
  batchScenarioId: "",
  batchSessionGeneration: 0,
  batchSessionOwner: "",
  batchColumnsRequestId: 0,
  editorGeography: null,
  batchGeographies: {},
  editorDirty: false,
  noteAutosave: {
    scenario: {timer:null, inFlight:null, dirty:false, revision:0, context:"", value:""},
    file: {timer:null, inFlight:null, dirty:false, revision:0, context:"", value:""},
  },
  editorSelectedLocations: new Set(),
  batchSelectedLocations: new Set(),
  editorMixedScopes: [],
  editorScopeUnavailable: false,
  batchMixedScopes: [],
  batchDraftGeographyType: "",
  batchDraftScopeUnavailable: false,
  logFollowTail: true,
  review: null,
  reviewedScenarioIds: [],
  reviewHypercubeId: "",
  reviewExpandedScenarioIds: new Set(),
  activePrimaryPage: "explorePage",
  activeExploreSubpage: "exploreLibraryPage",
  activeCreateSubpage: "createSetup",
  activeCompareSubpage: "loadData",
  primaryPageScroll: new Map([["explorePage", {left:0,top:0}], ["createPage", {left:0,top:0}], ["runPage", {left:0,top:0}], ["comparePage", {left:0,top:0}]]),
  pageNavigationToken: 0,
  expandedProjectIds: new Set(),
  projectScenarioSelections: new Map(),
  hypercubeAxes: [],
  hypercubeProjectId: "",
  hypercubeAxisSequence: 0,
  hypercubeFiles: new Map(),
  hypercubePreview: null,
  hypercubeSelectedLocations: new Set(),
  hypercubeLocationSearch: "",
  hypercubeLocationPopoverOpen: false,
  hypercubeOperationId: "",
  hypercubeSafetyAcknowledged: false,
  hypercubeDirty: false,
  hypercubeSavedRevision: "",
  hypercubeSavedComplete: false,
  hypercubePreviewRevision: "",
  hypercubePreviewToken: "",
  hypercubeHydratedProjectId: "",
  hypercubeScopeDraft: {year:null,geographyType:"all"},
  hypercubeFileLoadSequence: 0,
  hypercubeAutosave: {timer:null,inFlight:null,changeRevision:0,lastError:""},
  hypercubeResourceReport: null,
  hypercubeResourceReportPromise: null,
  compareActivity: null,
  compareActivityTimer: null,
  compareActivityCollapseTimer: null,
  copyOperationId: "",
  logBuffers: {},
  logOffsets: {},
  logUnread: new Set(),
  compareOffset: 0,
  compareFilterField: "",
  compareFilterValues: new Set(),
  scanFilterField: "",
  scanFilterValues: new Set(),
  scanGeoOptions: [],
  scanGeoMessage: "",
  compareLocationSearch: "",
  scanLocationSearch: "",
  exportFilterField: "",
  exportFilterValues: new Set(),
  exportLocationSearch: "",
  fullExportVariableKeys: new Set(),
  fullExportVariableQuery: "",
  compareLocationDirty: false,
  comparisonScan: null,
  comparisonScanOperationId: "",
  comparisonOperationId: "",
  comparisonExportOperationId: "",
  comparisonScanId: "",
  comparisonScanScope: "all",
  compareResultMode: "comparison",
  compareController: null,
  dashboardPayload: null,
  dashboardGeoOptions: [],
  dashboardGeoMessage: "",
  dashboardFilterField: "",
  dashboardFilterValues: new Set(),
  dashboardLocationSearch: "",
  dashboardDirty: true,
  dashboardInputSignature: "",
  dashboardVariablesExpanded: true,
  dashboardVariableQuery: "",
  mapOptions: [],
  mapPayload: null,
  mapDirty: true,
  mapInputSignature: "",
  comparisonMapData: null,
  comparisonMapPackageId: "",
  comparisonMapScene: null,
  comparisonMapView: null,
  comparisonMapSelectedFeature: null,
  comparisonMapPointerMoved: false,
  comparisonMapMode: "2d",
  comparisonMap3dCapability: "loading",
  comparisonMap3dCapabilityMessage: "Loading the bundled 3D renderer.",
  comparisonMap3d: null,
  comparisonMap3dMarkers: [],
  comparisonMap3dScene: null,
  comparisonMapDensity: null,
  comparisonMapDensitySignature: "",
  comparisonMapDensityOperationId: "",
  comparisonMapOptionsCache: new Map(),
  comparisonMapOptionsInflight: new Map(),
  comparisonMapOptionsController: null,
  comparisonMapOptionsRequest: "",
  runHistoryHidden: false,
  pendingProjectSetup: null,
  changedVariableQuery: "",
  changedVariableSort: {column:"output", direction:"original"},
  exploreLibraryId: "",
  exploreFiles: [],
  exploreSelectedFile: "",
  exploreDetail: null,
  exploreExplanationId: "",
  regionBuilderPackages: null,
  regionBuilderPackageId: "",
  regionBuilderReference: null,
  regionBuilderPreview: null,
  regionBuilderPreviewError: "",
  regionBuilderSources: null,
  regionBuilderRegions: null,
  regionBuilderSourceLibraryId: "",
  regionBuilderRegionId: "",
  regionBuilderGeographyMode: "official",
  regionBuilderGeographyOptions: null,
  regionBuilderGeographyKey: "",
  regionBuilderSelectedBzones: new Set(),
  regionBuilderDraftBzones: new Set(),
  regionBuilderDraftInitialized: false,
  regionBuilderGeographyQuery: "",
  regionBuilderGeographyView: {x: 0, y: 0, width: 1000, height: 620},
  regionBuilderGeographyPan: null,
  regionBuilderGeographyFrame: null,
  regionBuilderIdentityKey: "",
  regionBuilderIdentityDrafts: {official: null, custom: null},
  packageInstallButton: null,
  packageInstallRegionBuilder: false,
  regionMapData: null,
  regionMapKey: "",
  regionMapView: null,
  regionMapSelectedRegionId: "",
  regionMapScene: null,
  regionMapSelectedFeature: null,
  regionMapPointerMoved: false,
  regionMapLoadState: "idle",
  regionMapLoadError: "",
  regionMapLoadPromise: null,
  dependencyFullGraph: null,
  dependencyGraph: null,
  dependencyTemplateId: "",
  dependencyOriginId: "",
  dependencyScope: "",
  dependencyView: "",
  dependencyNavigation: [],
  dependencyViewport: { scale: 1, x: 0, y: 0, drag: null, fitPending: true, highlighted: "" },
  dependencyDisplayLayout: null,
  queueRevision: 0,
  draggedJobId: "",
  stopAllPending: false,
  desktop: null,
  onboardingShown: false,
  runtimeSetupPhase: "idle",
  runtimeSetupMessage: "",
  jobStateSnapshot: null,
  runSelectionProjectId: "",
  runSelectedVariationIds: new Set(),
  runForceRerunIds: new Set(),
  runBaselineSelected: false,
  pendingJobActions: new Set(),
  consoleBatchId: "",
  lastActiveConsoleJob: "",
  lastActiveConsoleByBatch: {},
  consoleAutoFollowJob: "",
  consoleManualSelection: false,
  comparisonMap3dDefaultCamera: null,
  comparisonMap3dElevationDirection: "all",
};

const $ = (id) => document.getElementById(id);
const EDITOR_DRAFT_STORAGE_KEY = "visioneval-editor-drafts-v1";
const EDITOR_DRAFT_VERSION = 1;
const MIXED_EDITOR_VALUE = "__mixed__";

function readEditorDraftStore() {
  try {
    const parsed = JSON.parse(localStorage.getItem(EDITOR_DRAFT_STORAGE_KEY) || "{}");
    return parsed?.version === EDITOR_DRAFT_VERSION && parsed.entries && typeof parsed.entries === "object" ? parsed : {version:EDITOR_DRAFT_VERSION,entries:{}};
  } catch (_) { return {version:EDITOR_DRAFT_VERSION,entries:{}}; }
}
function writeEditorDraftStore(store) {
  try { localStorage.setItem(EDITOR_DRAFT_STORAGE_KEY, JSON.stringify(store)); } catch (_) { /* Draft persistence must never block editing. */ }
}
function editorDraftKey(mode, projectId = state.selectedProject?.id || "", scenarioId = state.editorVariationId || "", filename = "") {
  return [mode, projectId, scenarioId, mode === "file" ? filename : ""].map((part) => encodeURIComponent(part)).join("|");
}
function loadEditorDraft(mode, filename = "") {
  const draft = readEditorDraftStore().entries[editorDraftKey(mode, state.selectedProject?.id, state.editorVariationId, filename)];
  return draft?.version === EDITOR_DRAFT_VERSION ? structuredClone(draft) : null;
}
function storeEditorDraft(mode, draft, filename = "") {
  if (!state.selectedProject?.id || !state.editorVariationId) return;
  const store = readEditorDraftStore();
  store.entries[editorDraftKey(mode, state.selectedProject.id, state.editorVariationId, filename)] = {...structuredClone(draft),version:EDITOR_DRAFT_VERSION,projectId:state.selectedProject.id,scenarioId:state.editorVariationId,mode,filename:mode === "file" ? filename : ""};
  writeEditorDraftStore(store);
}
function removeEditorDrafts({projectId = "", scenarioId = "", filename = ""} = {}) {
  const store = readEditorDraftStore(); let changed = false;
  Object.entries(store.entries).forEach(([key,draft]) => {
    if (projectId && draft.projectId !== projectId) return;
    if (scenarioId && draft.scenarioId !== scenarioId) return;
    if (filename && draft.mode === "batch") {
      draft.files = (draft.files || []).filter((item) => item !== filename);
      if (draft.columns) delete draft.columns[filename];
      changed = true; return;
    }
    if (filename && !(draft.mode === "file" && draft.filename === filename)) return;
    delete store.entries[key]; changed = true;
  });
  if (changed) writeEditorDraftStore(store);
}
function pruneEditorDrafts() {
  if (!state.data) return;
  const projects = [...(state.data.projects || []), ...(state.data.archivedProjects || [])], scenarios = new Map(projects.map((project) => [project.id,new Set((project.variations || []).map((scenario) => scenario.id))]));
  const store = readEditorDraftStore(); let changed = false;
  Object.entries(store.entries).forEach(([key,draft]) => {
    if (!scenarios.get(draft.projectId)?.has(draft.scenarioId)) { delete store.entries[key]; changed = true; }
  });
  if (changed) writeEditorDraftStore(store);
}
const shortcutDefinitions = Object.freeze({
  "new-scenario": {mac: "⌘N", other: "Ctrl+N", ariaMac: "Meta+N", ariaOther: "Control+N"},
  "new-file": {mac: "⇧⌘N", other: "Ctrl+Shift+N", ariaMac: "Meta+Shift+N", ariaOther: "Control+Shift+N"},
  "batch-change": {mac: "⌥⌘B", other: "Ctrl+Alt+B", ariaMac: "Meta+Alt+B", ariaOther: "Control+Alt+B"},
  save: {mac: "⌘S", other: "Ctrl+S", ariaMac: "Meta+S", ariaOther: "Control+S"},
  "run-selected": {mac: "⇧⌘R", other: "Ctrl+Shift+R", ariaMac: "Meta+Shift+R", ariaOther: "Control+Shift+R"},
  "stop-selected": {mac: "⌘.", other: "Ctrl+.", ariaMac: "Meta+.", ariaOther: "Control+."},
  "primary-tabs": {mac: "⌘1–4", other: "Ctrl+1–4", ariaMac: "Meta+1", ariaOther: "Control+1"},
  refresh: {mac: "⌘R", other: "Ctrl+R", ariaMac: "Meta+R", ariaOther: "Control+R"},
  settings: {mac: "⌘,", other: "Ctrl+,", ariaMac: "Meta+,", ariaOther: "Control+,"},
});

function frontendPlatform() {
  if (state.desktop?.platform) return state.desktop.platform;
  return /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent) ? "macos" : "windows";
}

function renderPlatformShortcuts() {
  const mac = frontendPlatform() === "macos";
  document.querySelectorAll("[data-shortcut]").forEach((node) => {
    const definition = shortcutDefinitions[node.dataset.shortcut];
    if (definition) node.textContent = mac ? definition.mac : definition.other;
  });
  document.querySelectorAll("[data-shortcut-action]").forEach((node) => {
    const definition = shortcutDefinitions[node.dataset.shortcutAction];
    if (definition) node.setAttribute("aria-keyshortcuts", mac ? definition.ariaMac : definition.ariaOther);
  });
}

function prunePlatformSpecificContent() {
  const platform = frontendPlatform();
  document.querySelectorAll("[data-runtime-platform]").forEach((node) => {
    if (node.dataset.runtimePlatform !== platform) node.remove();
  });
}
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
const terminalJobStates = new Set(["succeeded", "failed", "cancelled", "cleanup_failed"]);
const activeJobStates = new Set(["preparing", "running", "exporting", "stopping"]);
const scenarioCopyBlockingStates = new Set(["waiting", "preparing", "running", "exporting", "stopping"]);
const stopRunTooltip = "Stops only the selected active run and deletes that run's partial files.";
const stopAllRunsTooltip = "Stops every active run and removes all waiting queue items in the current workspace.";

function confirmWorkbench(message, { title = "Confirm action", confirmLabel = "Continue", danger = true, requiredPhrase = "" } = {}) {
  const dialog = $("confirmationDialog");
  if (dialog.open) dialog.close("cancel");
  $("confirmationDialogTitle").textContent = title;
  $("confirmationDialogMessage").textContent = message;
  const accept = $("confirmationDialogAccept");
  const alternative = $("confirmationDialogAlternative");
  const phraseLabel = $("confirmationDialogPhraseLabel");
  const phraseHint = $("confirmationDialogPhraseHint");
  const phraseInput = $("confirmationDialogPhrase");
  alternative.value = "baseline";
  accept.textContent = confirmLabel;
  accept.classList.toggle("danger", danger);
  alternative.hidden = true;
  phraseLabel.hidden = !requiredPhrase;
  phraseHint.textContent = requiredPhrase ? `Type ${requiredPhrase} to continue.` : "";
  phraseInput.value = "";
  accept.disabled = Boolean(requiredPhrase);
  return new Promise((resolve) => {
    const update = () => { accept.disabled = Boolean(requiredPhrase) && phraseInput.value !== requiredPhrase; };
    const close = () => {
      phraseInput.removeEventListener("input", update);
      resolve(dialog.returnValue === "confirm" && (!requiredPhrase || phraseInput.value === requiredPhrase));
    };
    phraseInput.addEventListener("input", update);
    dialog.addEventListener("close", close, { once: true });
    dialog.showModal();
    if (requiredPhrase) requestAnimationFrame(() => phraseInput.focus());
  });
}

function chooseOverlappingOperation(overlapCount) {
  if (!overlapCount) return Promise.resolve("current");
  const dialog = $("confirmationDialog");
  if (dialog.open) dialog.close("cancel");
  $("confirmationDialogTitle").textContent = "Apply an additional operation?";
  $("confirmationDialogMessage").textContent = `This operation affects ${Number(overlapCount).toLocaleString()} cell${overlapCount === 1 ? "" : "s"} already adjusted from baseline. Apply from the untouched baseline to replace the prior effect on those cells, or apply an additional operation using their current scenario values.`;
  const accept = $("confirmationDialogAccept"), alternative = $("confirmationDialogAlternative");
  $("confirmationDialogPhraseLabel").hidden = true;
  $("confirmationDialogPhrase").value = "";
  accept.disabled = false; accept.textContent = "Apply additional operation"; accept.classList.remove("danger");
  alternative.hidden = false; alternative.value = "baseline"; alternative.textContent = "From baseline";
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => {
      const result = dialog.returnValue === "baseline" ? "baseline" : dialog.returnValue === "confirm" ? "current" : "cancel";
      alternative.hidden = true;
      resolve(result);
    }, {once:true});
    dialog.showModal();
  });
}

function jobFailureKind(job) {
  if (job?.failureKind) return job.failureKind;
  if (Number(job?.exitCode) === 137 || /(?:exit(?:ed)?(?: with)? code|code)\s+137\b/i.test(job?.message || "")) return "memory_suspected";
  return "";
}

function memoryFailure(job) {
  return ["memory", "memory_suspected"].includes(jobFailureKind(job));
}

function jobDisplayMessage(job) {
  if (jobFailureKind(job) === "memory") return "Docker stopped this run because it ran out of available memory. Reduce parallel runs or increase Docker’s memory allocation, then retry.";
  if (jobFailureKind(job) === "memory_suspected") return "This run was forcibly stopped. Memory pressure is the most common cause of exit code 137; check Resources and the run log before retrying.";
  return job?.message || "";
}

function chooseMemoryRetry(job) {
  const dialog = $("confirmationDialog");
  if (dialog.open) dialog.close("cancel");
  const allocation = Number(state.data?.runtime?.dockerMemoryBytes || 0);
  const concurrency = Number(state.desktop?.resources?.maxConcurrentRuns || state.data?.queue?.maxActive || 1);
  const cap = Number(state.desktop?.resources?.memoryLimitGb || 0);
  const details = [`Current concurrency: ${concurrency}`];
  if (allocation) details.push(`Docker Desktop allocation: ${humanBytes(allocation)}`);
  details.push(`Per-run Workbench limit: ${cap ? `${cap.toLocaleString()} GB` : "none"}`);
  $("confirmationDialogTitle").textContent = "Retry memory-related failure?";
  $("confirmationDialogMessage").textContent = `${jobDisplayMessage(job)}\n\n${details.join(" · ")}\n\nRetrying without changing resources may produce the same failure.`;
  $("confirmationDialogPhraseLabel").hidden = true;
  $("confirmationDialogPhrase").value = "";
  const accept = $("confirmationDialogAccept"), alternative = $("confirmationDialogAlternative");
  accept.disabled = false; accept.textContent = "Retry Anyway"; accept.classList.remove("danger");
  alternative.hidden = false; alternative.value = "settings"; alternative.textContent = "Open Resource Settings";
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => {
      const result = dialog.returnValue === "settings" ? "settings" : dialog.returnValue === "confirm" ? "retry" : "cancel";
      alternative.hidden = true;
      alternative.value = "baseline";
      resolve(result);
    }, {once:true});
    dialog.showModal();
  });
}

async function retryRun(job) {
  if (!job || job.state !== "failed" || job.retryable === false) return;
  if (memoryFailure(job)) {
    const choice = await chooseMemoryRetry(job);
    if (choice === "settings") {
      await openSettings("settingsResources");
      return;
    }
    if (choice !== "retry") return;
  }
  await jobAction("/api/runs/retry", job.id);
}

function baselineDisplayName(project = state.selectedProject) {
  return project?.baseline?.displayName?.trim() || "Baseline";
}

function currentActiveJob() {
  const jobs = (state.data?.jobs || []).filter((job) => activeJobStates.has(job.state) && job.state !== "stopping");
  const selected = jobs.find((job) => job.id === state.selectedJob);
  return selected || (jobs.length === 1 ? jobs[0] : null);
}
function selectedActiveJob() {
  return (state.data?.jobs || []).find((job) => job.id === state.selectedJob && activeJobStates.has(job.state) && job.state !== "stopping") || null;
}
function runnableJobs() {
  return (state.data?.jobs || []).filter((job) => (activeJobStates.has(job.state) && job.state !== "stopping") || job.state === "waiting");
}
function unresolvedRunQueueJobs() {
  return (state.data?.jobs || []).filter((job) => activeJobStates.has(job.state) || job.state === "waiting");
}
function activeScenarioCopyJobs(projectId, variationIds) {
  const selected = new Set(variationIds || []);
  return (state.data?.jobs || []).filter((job) =>
    job.projectId === projectId && selected.has(job.variationId) && scenarioCopyBlockingStates.has(job.state)
  );
}
function activeProjectCopyJobs(projectId) {
  return (state.data?.jobs || []).filter((job) => job.projectId === projectId && scenarioCopyBlockingStates.has(job.state));
}
function destinationCopyBlockedMessage(projectId) {
  if(!projectId)return"";
  const project=state.data?.projects?.find((item)=>item.id===projectId),jobs=activeProjectCopyJobs(projectId);
  if(!jobs.length)return"";
  const states=[...new Set(jobs.map((job)=>job.state))].sort().join(", ");
  return `${project?.name||"This project"} has unfinished runs (${states}). Please wait until every run in this project has finished or been stopped.`;
}
function scenarioCopyBlockedMessage(projectId, variationIds) {
  const source = state.data?.projects?.find((item) => item.id === projectId);
  const names = new Map((source?.variations || []).map((item) => [item.id, item.name]));
  const blocked = activeScenarioCopyJobs(projectId, variationIds);
  if (!blocked.length) return "";
  const grouped = new Map();
  blocked.forEach((job) => {
    const entry = grouped.get(job.variationId) || {name:names.get(job.variationId) || job.variationName || job.variationId,states:new Set()};
    entry.states.add(job.state);grouped.set(job.variationId,entry);
  });
  const descriptions = [...grouped.values()].map((entry) => `${entry.name} (${[...entry.states].sort().join(", ")})`);
  return `Wait for or stop active scenario runs before copying: ${descriptions.join(", ")}`;
}

function resolvedTheme(theme) {
  return theme === "system" ? (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark") : theme === "light" ? "light" : "dark";
}
function applyTheme(theme, persist = true) {
  const preference = ["system", "light", "dark"].includes(theme) ? theme : "system";
  const selected = resolvedTheme(preference);
  document.documentElement.dataset.theme = selected;
  document.documentElement.dataset.themePreference = preference;
  localStorage.setItem("visioneval-theme", preference);
  if (persist) window.__TAURI_INTERNALS__?.invoke("set_theme", { theme: preference }).catch(() => {});
  const next = selected === "dark" ? "light" : "dark";
  $("themeIcon").textContent = selected === "dark" ? "☀︎" : "☾";
  $("themeLabel").textContent = `${next[0].toUpperCase()}${next.slice(1)} mode`;
  $("themeToggle").setAttribute("aria-label", `Switch to ${next} mode`);
  $("themeToggle").title = `Switch to ${next} mode`;
}

const comparisonPaletteDefaults={table:{increase:'#168354',decrease:'#c43d49',neutral:'#a96800'},map:{increase:'#2274a7',decrease:'#be3742',neutral:'#edf1f4'},chart:{increase:'#2274a7',decrease:'#be3742',neutral:'#9aa6af'}};
const masterComparisonPaletteDefault={...comparisonPaletteDefaults.map};
function storedComparisonPalettes(){return {table:{...comparisonPaletteDefaults.table,...state.desktop?.comparisonPalettes?.table},map:{...comparisonPaletteDefaults.map,...state.desktop?.comparisonPalettes?.map},chart:{...comparisonPaletteDefaults.chart,...state.desktop?.comparisonPalettes?.chart}}}
function masterComparisonPalette(){return {...masterComparisonPaletteDefault,...state.desktop?.masterComparisonPalette}}
function comparisonPalettes(){const palettes=storedComparisonPalettes();if(!state.desktop?.useMasterComparisonPalette)return palettes;const master=masterComparisonPalette();return {table:{...master},map:{...master},chart:{...master}}}
function comparisonPaletteColor(kind,direction){return comparisonPalettes()[kind]?.[direction]||comparisonPaletteDefaults[kind][direction]}
function applyComparisonPalettes(){for(const [kind,palette] of Object.entries(comparisonPalettes()))for(const [direction,color] of Object.entries(palette))document.documentElement.style.setProperty(`--comparison-${kind}-${direction}`,color)}
function renderComparisonPaletteSettings(){
  const root=$("comparisonPaletteSettings");if(!root)return;
  const labels={table:'Result-table deltas',map:'Comparison maps',chart:'Diverging charts'};
  const colorControls=(kind,palette,label)=>`<div class="palette-inputs">${['decrease','neutral','increase'].map((direction)=>{const title=direction[0].toUpperCase()+direction.slice(1),id=`palette-${kind}-${direction}`;return `<label class="palette-color-control" for="${id}"><input id="${id}" type="color" data-palette-color="${direction}" value="${palette[direction]}" aria-label="Choose ${title.toLowerCase()} color for ${label}"><span class="palette-color-copy"><strong>${title}</strong><span class="palette-color-value" data-palette-value="${direction}">${palette[direction].toUpperCase()}</span><span class="palette-color-action" aria-hidden="true">Choose color…</span></span></label>`}).join('')}</div><div class="palette-preview" aria-label="Live diverging preview" style="--preview-decrease:${palette.decrease};--preview-neutral:${palette.neutral};--preview-increase:${palette.increase}"></div>`;
  const enabled=Boolean(state.desktop?.useMasterComparisonPalette),master=masterComparisonPalette(),individual=storedComparisonPalettes();
  root.innerHTML=`<section class="palette-card palette-master" data-palette-kind="master"><div class="palette-master-heading"><div><h4>Master palette</h4><p class="muted">Override tables, maps, charts, and their exports with one consistent palette.</p></div><label class="checkbox"><input id="useMasterComparisonPalette" type="checkbox" ${enabled?'checked':''}> Use everywhere</label></div>${colorControls('master',master,'the master palette')}<footer class="palette-card-footer"><button type="button" class="secondary" data-palette-preset>Accessible preset</button><button type="button" class="secondary" data-palette-reset>Reset to default</button></footer></section>${Object.entries(individual).map(([kind,palette])=>`<section class="palette-card${enabled?' palette-overridden':''}" data-palette-kind="${kind}"><h4>${labels[kind]}</h4>${colorControls(kind,palette,labels[kind])}<footer class="palette-card-footer"><button type="button" class="secondary" data-palette-preset>Accessible preset</button><button type="button" class="secondary" data-palette-reset>Reset to default</button></footer></section>`).join('')}`;
  $('useMasterComparisonPalette').addEventListener('change',(event)=>{state.desktop.useMasterComparisonPalette=event.target.checked;applyComparisonPalettes();renderComparisonPaletteSettings()});
  root.querySelectorAll('[data-palette-color]').forEach((input)=>input.addEventListener('input',()=>{const card=input.closest('[data-palette-kind]'),kind=card.dataset.paletteKind,direction=input.dataset.paletteColor;if(kind==='master'){state.desktop.masterComparisonPalette ||= masterComparisonPalette();state.desktop.masterComparisonPalette[direction]=input.value}else{state.desktop.comparisonPalettes ||= storedComparisonPalettes();state.desktop.comparisonPalettes[kind] ||= {...comparisonPaletteDefaults[kind]};state.desktop.comparisonPalettes[kind][direction]=input.value}card.querySelector(`[data-palette-value="${direction}"]`).textContent=input.value.toUpperCase();const palette=kind==='master'?state.desktop.masterComparisonPalette:state.desktop.comparisonPalettes[kind],preview=card.querySelector('.palette-preview');preview.style.setProperty('--preview-decrease',palette.decrease);preview.style.setProperty('--preview-neutral',palette.neutral);preview.style.setProperty('--preview-increase',palette.increase);applyComparisonPalettes()}));
  root.querySelectorAll('[data-palette-preset]').forEach((button)=>button.addEventListener('click',()=>{const kind=button.closest('[data-palette-kind]').dataset.paletteKind,preset={increase:'#0072B2',decrease:'#D55E00',neutral:'#999999'};if(kind==='master')state.desktop.masterComparisonPalette=preset;else{state.desktop.comparisonPalettes ||= storedComparisonPalettes();state.desktop.comparisonPalettes[kind]=preset}applyComparisonPalettes();renderComparisonPaletteSettings()}));
  root.querySelectorAll('[data-palette-reset]').forEach((button)=>button.addEventListener('click',()=>{const kind=button.closest('[data-palette-kind]').dataset.paletteKind;if(kind==='master')state.desktop.masterComparisonPalette={...masterComparisonPaletteDefault};else{state.desktop.comparisonPalettes ||= storedComparisonPalettes();state.desktop.comparisonPalettes[kind]={...comparisonPaletteDefaults[kind]}}applyComparisonPalettes();renderComparisonPaletteSettings()}));
}
function readComparisonPalettes(){return storedComparisonPalettes()}

const storedTheme = localStorage.getItem("visioneval-theme");
applyTheme(storedTheme || "light", false);
applyComparisonPalettes();
window.__TAURI_INTERNALS__?.invoke("get_theme").then((theme) => {
  if (["system", "light", "dark"].includes(theme)) applyTheme(theme, false);
}).catch(() => {});
$("themeToggle").addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => { if (document.documentElement.dataset.themePreference === "system") applyTheme("system", false); });

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: options.body ? { "Content-Type": "application/json", ...(options.headers || {}) } : options.headers,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `${response.status} ${response.statusText}`);
  return payload;
}

function post(path, payload) {
  return request(path, { method: "POST", body: JSON.stringify(payload) });
}

async function waitForRuntimeInstallation(operationId) {
  const deadline = Date.now() + (20 * 60 * 1000);
  let transientFailures = 0;
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    let operation;
    try {
      operation = await request(`/api/runtime/install/status?id=${encodeURIComponent(operationId)}`);
      transientFailures = 0;
    } catch (error) {
      transientFailures += 1;
      if (transientFailures < 5) continue;
      throw error;
    }
    state.runtimeSetupMessage = operation.message || "Downloading and verifying the pinned runtime…";
    renderRuntimeSetupControls();
    if (operation.state === "succeeded") return operation.result;
    if (operation.state === "failed") throw new Error(operation.message || "Runtime installation failed");
  }
  throw new Error("Runtime installation did not finish within 20 minutes.");
}

async function chooseFolder(targetId) {
  const invoke = window.__TAURI_INTERNALS__?.invoke;
  if (!invoke) return notify("Folder selection is available in the VisionEval Workbench desktop app. You can also enter the path manually.", "error");
  try {
    const path = await invoke("choose_folder");
    if (path) {
      const input = $(targetId);
      input.value = path;
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
  } catch (error) {
    notify(`Could not open the folder picker: ${error}`, "error");
  }
}

document.querySelectorAll("[data-folder-target]").forEach((button) => button.addEventListener("click", () => chooseFolder(button.dataset.folderTarget)));

let noticeTimer;
function notify(message, type = "", action = null) {
  const settingsOpen = Boolean($("settingsDialog")?.open);
  const notice = settingsOpen ? $("settingsNotice") : $("notice");
  if (settingsOpen) {
    $("settingsNoticeText").textContent = message;
    const button = $("settingsNoticeAction");
    button.hidden = !action;
    button.disabled = false;
    button.textContent = action?.label || "";
    button.onclick = action ? () => action.onClick() : null;
  } else {
    notice.textContent = message;
  }
  notice.className = `notice ${type}`;
  notice.hidden = false;
  clearTimeout(noticeTimer);
  if (action) return;
  noticeTimer = setTimeout(() => { notice.hidden = true; }, type === "error" ? 9000 : 4500);
}

function settingsRefreshAction(){return{label:"Refresh Workbench",onClick:refreshWorkbenchAfterSettingsSave}}
async function refreshWorkbenchAfterSettingsSave(){
  const unfinished=(state.data?.jobs||[]).filter(job=>!terminalJobStates.has(job.state));
  if(unfinished.length)return notify(`Finish or stop ${unfinished.length} active or waiting run${unfinished.length===1?"":"s"} before refreshing Workbench.`,"error",settingsRefreshAction());
  notify("Refreshing Workbench to apply the resource change…","success");
  try{const url=await window.__TAURI_INTERNALS__.invoke("restart_backend");window.location.replace(url)}catch(error){notify(`Workbench could not refresh: ${error}`,"error",settingsRefreshAction())}
}

function nativeNotification(title, body, {outcome="succeeded", elapsedSeconds=null, force=false}={}) {
  if (!state.desktop?.notificationsEnabled || !window.__TAURI_INTERNALS__?.invoke) return;
  window.__TAURI_INTERNALS__.invoke("send_workbench_notification", {title, body, outcome, elapsedSeconds, force}).catch(() => {});
}

function observeJobStates(jobs) {
  const next = new Map((jobs || []).map((job) => [job.id, job.state]));
  if (state.jobStateSnapshot) {
    for (const job of jobs || []) {
      const previous = state.jobStateSnapshot.get(job.id);
      if (!previous || terminalJobStates.has(previous) || !terminalJobStates.has(job.state)) continue;
      const label = jobDisplayName(job), duration = jobRuntime(job), elapsedMilliseconds = jobRuntimeMilliseconds(job), elapsedSeconds = Number.isFinite(elapsedMilliseconds) ? Math.floor(elapsedMilliseconds / 1000) : null;
      if (job.state === "succeeded") nativeNotification(`${label} completed`, `${job.projectName || "VisionEval"} finished in ${duration}.`, {outcome:"succeeded", elapsedSeconds});
      else if (job.state === "failed" || job.state === "cleanup_failed") nativeNotification(`${label} failed`, job.message || `${job.projectName || "VisionEval"} needs attention.`, {outcome:"failed", elapsedSeconds});
    }
  }
  state.jobStateSnapshot = next;
}

function setBusy(button, busy, label = "Working…") {
  if (!button) return;
  if (busy) {
    button.dataset.originalText = button.textContent;
    button.dataset.originalDisabled = button.disabled ? "true" : "false";
    button.dataset.originalDisabledReason = button.dataset.disabledReason || "";
    button.textContent = label;
    setButtonAvailability(button, false, `${label.replace(/…$/, "")} is in progress.`);
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    const wasDisabled = button.dataset.originalDisabled === "true";
    setButtonAvailability(button, !wasDisabled, button.dataset.originalDisabledReason || disabledReasonFor(button));
    delete button.dataset.originalDisabled;
    delete button.dataset.originalDisabledReason;
  }
}

const DISABLED_BUTTON_REASONS = {
  previewRegionBuild: "Choose an installed regional package and region first.",
  buildRegionAssets: "Preview the current region before building its assets.",
  customizeRegionGeography: "Statewide geography already includes every packaged zone.",
  applyRegionGeography: "Select at least one Bzone.",
  fitRegionMap: "Choose an MPO before fitting the map.",
  openRunDialog: "The project must be valid and the VisionEval runtime must be ready.",
  verifyRuntime: "Start Docker Desktop and install the pinned runtime image first.",
  settingsVerifyRuntime: "Start Docker Desktop and install the pinned runtime image first.",
  onboardingVerify: "Choose and verify the VisionEval runtime first.",
  saveOverlay: "Load a file and make a change before saving.",
  undoEditorChange: "There is no editor change to undo.",
  redoEditorChange: "There is no editor change to redo.",
  duplicateEditorScenario: "Create a scenario before copying one.",
  applyBatchChanges: "Complete the batch selections and operation first.",
  continueToRun: "Resolve the project validation errors before continuing.",
  runComparison: "Load comparison data and complete the comparison filters first.",
  findChangedOutputs: "Load at least two results and complete the selected location scope.",
  openCompareExports: "Load or generate comparison results before exporting.",
  scanScopeSelected: "The loaded outputs do not provide a safe shared location scope.",
  comparePrevious: "This is the first page.",
  compareNext: "This is the last page.",
  generateMap: "Load compatible results, variables, and map geometry first.",
  fitComparisonMap: "Choose an MPO before fitting the map.",
  toggleMapExport: "Generate a current comparison map before exporting.",
  generateDashboard: "Load at least two results and choose chart inputs first.",
};

function disabledReasonFor(button) {
  if (!button) return "This action is currently unavailable.";
  if (button.dataset.disabledReason) return button.dataset.disabledReason;
  if (button.title && button.disabled) return button.title;
  if (DISABLED_BUTTON_REASONS[button.id]) return DISABLED_BUTTON_REASONS[button.id];
  const text = button.textContent.trim().toLowerCase();
  if (text.includes("export") || /^(pdf|png|svg|csv|excel)$/.test(text)) return "Generate a current result before exporting.";
  if (text.includes("previous")) return "This is the first available page.";
  if (text.includes("next")) return "There are no more pages.";
  if (text.includes("remove") || text.includes("delete")) return "This item is protected or still in use.";
  if (text.includes("save")) return "Make a valid change before saving.";
  if (text.includes("run")) return "Complete the required setup and selections before running.";
  return "This action is currently unavailable because its requirements have not been met.";
}

function setButtonAvailability(button, enabled, reason = "") {
  if (!button) return;
  button.disabled = !enabled;
  if (enabled) {
    delete button.dataset.disabledReason;
    button.removeAttribute("aria-description");
    if (button.dataset.disabledTitle === "true") button.removeAttribute("title");
    delete button.dataset.disabledTitle;
    return;
  }
  const message = reason || disabledReasonFor(button);
  button.dataset.disabledReason = message;
  button.setAttribute("aria-description", message);
  if (!button.title || button.dataset.disabledTitle === "true") {
    button.title = message;
    button.dataset.disabledTitle = "true";
  }
}

function installDisabledButtonGuidance() {
  const tooltip = document.createElement("div");
  tooltip.className = "disabled-button-tooltip";
  tooltip.setAttribute("role", "tooltip");
  tooltip.hidden = true;
  document.body.appendChild(tooltip);
  let active = null;
  const hide = () => { active = null; tooltip.hidden = true; };
  document.addEventListener("pointermove", (event) => {
    const button = event.target instanceof Element ? event.target.closest("button:disabled") : null;
    if (!button) { hide(); return; }
    if (!button.dataset.disabledReason) setButtonAvailability(button, false, disabledReasonFor(button));
    active = button;
    tooltip.textContent = button.dataset.disabledReason;
    tooltip.hidden = false;
    const rect = button.getBoundingClientRect();
    const width = Math.min(340, window.innerWidth - 20);
    tooltip.style.maxWidth = `${width}px`;
    const tooltipRect = tooltip.getBoundingClientRect();
    tooltip.style.left = `${Math.max(10, Math.min(window.innerWidth - tooltipRect.width - 10, rect.left + rect.width / 2 - tooltipRect.width / 2))}px`;
    tooltip.style.top = `${Math.max(10, rect.top - tooltipRect.height - 8)}px`;
  }, true);
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") hide(); });
  window.addEventListener("blur", hide);
  new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      const button = mutation.target;
      if (button instanceof HTMLButtonElement && button.disabled && !button.dataset.disabledReason) {
        setButtonAvailability(button, false, disabledReasonFor(button));
      }
      if (button instanceof HTMLButtonElement && !button.disabled && button.dataset.disabledReason) {
        delete button.dataset.disabledReason;
        button.removeAttribute("aria-description");
        if (button.dataset.disabledTitle === "true") button.removeAttribute("title");
        delete button.dataset.disabledTitle;
      }
      if (active === button && !button.disabled) hide();
    }
  }).observe(document.body, {subtree: true, attributes: true, attributeFilter: ["disabled"]});
  document.querySelectorAll("button:disabled").forEach((button) => setButtonAvailability(button, false, disabledReasonFor(button)));
}

installDisabledButtonGuidance();

function selectedOption(select, value) {
  if ([...select.options].some((option) => option.value === value)) select.value = value;
}

function showAppRecovery(error) {
  const recovery = $("appRecovery");
  if (!recovery) return;
  $("appRecoveryMessage").textContent = `${error?.message || String(error || "Unexpected application error")}. Your workspace data is safe.`;
  recovery.hidden = false;
}

function recordAppError(message, context = {}) {
  if (!message || !window.fetch) return;
  fetch("/api/diagnostics/app-error", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({source:"frontend", message:String(message), path:location.pathname, context})}).catch(()=>{});
}

document.addEventListener("submit", (event) => { if (event.target?.getAttribute("method") !== "dialog") event.preventDefault(); }, true);
window.addEventListener("error", (event) => { recordAppError(event.error?.message || event.message); showAppRecovery(event.error || event.message); });
window.addEventListener("unhandledrejection", (event) => { recordAppError(event.reason?.message || event.reason); showAppRecovery(event.reason); });

async function refreshState({ quiet = false } = {}) {
  try {
    if (window.__TAURI_INTERNALS__?.invoke) state.desktop = await window.__TAURI_INTERNALS__.invoke("desktop_state");
    applyComparisonPalettes();
    renderPlatformShortcuts();
    state.data = await request("/api/state");
    state.hypercubeResourceReport=null;
    pruneEditorDrafts();
    if (state.stopAllPending && !unresolvedRunQueueJobs().length) state.stopAllPending = false;
    observeJobStates(state.data.jobs || []);
    renderAll();
    followActiveConsoleJob();
    maybeShowOnboarding();
    if (!quiet) notify("Workspace refreshed.", "success");
  } catch (error) {
    notify(error.message, "error");
  }
}

function renderAll() {
  renderDocumentationStatus();
  renderExploreLibraries();
  renderRegionBuilder();
  renderRuntime();
  renderSetup();
  renderProjects();
  renderArchivedProjects();
  renderEditorProjectSelect();
  renderHypercubeSetup();
  renderRunProjects();
  renderJobs();
  renderDatastores();
  renderUpdateIndicator();
  syncMenuContext();
}

const updateSourceLabels={visioneval:"VisionEval",runtimeImage:"Workbench runtime image",workbench:"VisionEval Workbench"};
function availableUpdateStatuses(payload=state.data?.updates){return Object.values(payload?.statuses||{}).filter(item=>item?.status==="update_available")}
function renderUpdateIndicator(payload=state.data?.updates){
  const available=availableUpdateStatuses(payload),show=available.length>0;
  if($("settingsUpdateIndicator"))$("settingsUpdateIndicator").hidden=!show;
  if($("settingsUpdatesNavIndicator"))$("settingsUpdatesNavIndicator").hidden=!show;
  if(show){
    const key=available.map(item=>`${item.source}:${item.availableVersion||item.requiresWorkbenchVersion||"available"}`).sort().join("|");
    if(state.updateNotificationKey!==key){state.updateNotificationKey=key;notify(`${available.length} advisory update${available.length===1?" is":"s are"} available. Review Settings → Updates.`,"success")}
  }
}

function renderDocumentationStatus() {
  const status = state.data?.documentation;
  const warning = $("documentationWarning");
  if (!warning) return;
  const show = status?.state === "warning";
  warning.hidden = !show;
  warning.textContent = show ? `${status.message} Restart Workbench to retry; files in Documentation/User Notes are safe.` : "";
}

function renderExploreExplanationNotice(packageMetadata = null) {
  const notice = $("exploreExplanationNotice");
  if (!notice) return;
  const selected = (state.data?.inputExplanations || []).find((item) => item.id === state.exploreExplanationId);
  const appliesTo = packageMetadata?.appliesTo || selected?.appliesTo || {};
  const familyId = selected?.familyId || packageMetadata?.familyId || "";
  const isVirginiaPackage = Boolean(state.exploreExplanationId)
    && (String(appliesTo.state || "").toUpperCase() === "VA" || familyId === "virginia-visioneval-input-explanations");
  notice.hidden = !isVirginiaPackage;
  notice.textContent = isVirginiaPackage
    ? "Input explanations were developed for a Virginia dataset. They can still help interpret other VisionEval input files, but locally customized inputs may differ."
    : "";
}

function renderExploreLibraries() {
  const libraries = state.data?.inputLibraries || [];
  const explanations = state.data?.inputExplanations || [];
  const select = $("exploreExplanations");
  const previous = state.exploreExplanationId || state.data?.workspaceSettings?.defaultInputExplanationId || select.value;
  select.innerHTML = `<option value="">Built-in module metadata</option>${explanations.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}${item.fileCount ? ` · ${item.fileCount} guides` : ""}${item.familyConflict?" · ⚠ different catalog":""}</option>`).join("")}`;
  selectedOption(select, previous);
  state.exploreExplanationId = select.value;
  renderExploreExplanationNotice();
  const libraryIds = new Set(libraries.map((item) => item.id));
  const preferredLibrary = state.exploreLibraryId || state.data?.workspaceSettings?.defaultInputLibraryId || "";
  const nextLibrary = libraryIds.has(preferredLibrary) ? preferredLibrary : libraries[0]?.id || "";
  if (nextLibrary !== state.exploreLibraryId) loadExploreFiles(nextLibrary);
  else if (!state.exploreFiles.length) loadExploreFiles(nextLibrary);
  renderExploreTemplates();
}

function renderExploreTemplates() {
  const templates = state.data?.templates || [];
  const select = $("dependencyTemplate"), prior = state.dependencyTemplateId || select.value;
  const catalogOption = `<option value="__builtin_module_catalog__">VisionEval module catalog (built in)</option>`;
  select.innerHTML = templates.length
    ? `${templates.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join("")}${catalogOption}`
    : catalogOption;
  selectedOption(select, prior);
  const templateControl = $("dependencyTemplateControl"), toolbar = document.querySelector(".dependency-toolbar");
  const hideTemplate = false;
  templateControl.hidden = hideTemplate;
  toolbar?.classList.toggle("template-hidden", hideTemplate);
  const nextDependency = $("dependencyTemplate").value;
  if (nextDependency && nextDependency !== state.dependencyTemplateId) loadDependencyGraph(nextDependency);
  if (!nextDependency) {
    state.dependencyTemplateId = ""; state.dependencyFullGraph = null; state.dependencyGraph = null; renderDependencyGraph();
  }
}

async function loadRegionBuilderPackage(packageId) {
  if (!packageId) return;
  state.regionBuilderReference = null;
  state.regionBuilderSources = null;
  state.regionBuilderRegions = null;
  try {
    const encoded = encodeURIComponent(packageId);
    [state.regionBuilderReference, state.regionBuilderSources, state.regionBuilderRegions] = await Promise.all([
      request(`/api/region-builder/reference?packageId=${encoded}`),
      request(`/api/region-builder/sources?packageId=${encoded}`),
      request(`/api/region-builder/regions?packageId=${encoded}`),
    ]);
    renderRegionBuilder();
  } catch (error) {
    state.regionBuilderReference = { error: error.message };
    state.regionBuilderSources = { sources: [] };
    state.regionBuilderRegions = { regions: [] };
    renderRegionBuilder();
  }
}

function openPackageSourceDialog(button, regionBuilder = false) {
  state.packageInstallButton = button;
  state.packageInstallRegionBuilder = regionBuilder;
  $("packageSourceDialog").showModal();
}

async function installSelectedPackage(command) {
  const button = state.packageInstallButton;
  try {
    $("packageSourceDialog").close();
    const source = await window.__TAURI_INTERNALS__.invoke(command);
    if (!source) return;
    setBusy(button, true, "Installing…");
    const result = await post("/api/packages/install", {source});
    if (state.packageInstallRegionBuilder) {
      state.regionBuilderPackageId = result.id || "";
      state.regionBuilderReference = null;
      state.regionBuilderSources = null;
      state.regionBuilderRegions = null;
    }
    await refreshState({quiet:true});
    if (!state.packageInstallRegionBuilder) await openSettings("settingsAssets");
    notify(`Installed ${result.name}.`, "success");
  } catch (error) {
    notify(error.message || String(error), "error");
  } finally {
    setBusy(button, false);
    state.packageInstallButton = null;
    state.packageInstallRegionBuilder = false;
  }
}

function renderRegionBuilder() {
  const packages = state.data?.developSources || [];
  const packageSelect = $("regionPackage");
  const sourceSelect = $("regionSourceLibrary");
  const regionSelect = $("regionDefinition");
  if (!packageSelect || !sourceSelect || !regionSelect) return;
  state.regionBuilderPackages = packages;
  $("regionBuilderEmpty").hidden = packages.length > 0;
  $("regionBuilderForm").hidden = packages.length === 0;
  $("regionBuilderPreview").hidden = packages.length === 0;
  $("regionGeographyModeSwitch").hidden = packages.length === 0;
  $("regionPackageField").hidden = packages.length === 1;
  document.querySelector(".region-builder-primary")?.classList.toggle("single-package", packages.length === 1);
  if (!packages.length) {
    state.regionBuilderPackageId = "";
    state.regionBuilderPreview = null;
    $("regionBuilderDescription").textContent = "Install a compatible model or regional package to create a runnable VisionEval region.";
    return;
  }
  const priorPackage = state.regionBuilderPackageId || packageSelect.value || packages[0].id;
  packageSelect.innerHTML = packages.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · ${escapeHtml(item.coverage)}</option>`).join("");
  selectedOption(packageSelect, priorPackage);
  const packageChanged = state.regionBuilderPackageId !== packageSelect.value;
  state.regionBuilderPackageId = packageSelect.value;
  if (packageChanged || !state.regionBuilderReference || !state.regionBuilderSources || !state.regionBuilderRegions) {
    loadRegionBuilderPackage(state.regionBuilderPackageId);
    return;
  }
  const sources = state.regionBuilderSources?.sources || [];
  const regions = state.regionBuilderRegions?.regions || [];
  const previousSource = state.regionBuilderSourceLibraryId || sourceSelect.value || "";
  const previousRegion = state.regionBuilderRegionId || regionSelect.value || "";
  sourceSelect.innerHTML = sources.length ? sources.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}${item.fileCount ? ` (${item.fileCount} files)` : ""}</option>`).join("") : `<option value="">No compatible Input Library</option>`;
  if (regions.length) {
    const regional = regions.filter((item) => item.regionType !== "statewide");
    regionSelect.innerHTML = regional.length ? `<optgroup label="MPO study areas">${regional.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join("")}</optgroup>` : `<option value="">No supported MPO definitions</option>`;
  } else regionSelect.innerHTML = `<option value="">No region definitions</option>`;
  selectedOption(sourceSelect, previousSource);
  selectedOption(regionSelect, previousRegion);
  state.regionBuilderSourceLibraryId = sourceSelect.value;
  state.regionBuilderRegionId = regionSelect.value;
  const selectedRegion = regions.find((item) => item.id === state.regionBuilderRegionId);
  initializeRegionBuilderIdentity(selectedRegion, packageChanged);
  updateRegionBuilderAvailability(sources, regions);
  renderRegionMapLoadStatus();
  $("customizeRegionGeography").disabled = selectedRegion?.regionType === "statewide";
  $("customizeRegionGeography").title = selectedRegion?.regionType === "statewide" ? "The statewide build includes every packaged Bzone." : "Include or exclude individual Azones and Bzones.";
  const terminology = state.regionBuilderReference?.terminology || {};
  $("regionSelectorLabel").textContent = terminology.regionSelector || terminology.regionSingular || "Region";
  const activePackage = packages.find((item) => item.id === state.regionBuilderPackageId);
  $("regionBuilderDescription").textContent = activePackage?.description || `Build a region using ${activePackage?.name || "the installed package"}.`;
  const modelBacked = activePackage?.sourceKind === "model-bundle";
  $("useOfficialRegionGeography").textContent = modelBacked ? "Installed scope" : "Official MPO";
  document.querySelector("#officialRegionGeographyView .muted").textContent = modelBacked
    ? "Use all geography contained in the installed model, or choose a smaller subregion."
    : "Use the regional package's official MPO boundary rule.";
  renderRegionBuilderReference();
  renderRegionGeographySummary();
  renderRegionBuilderMode();
}

function regionBuilderModelBacked() {
  return (state.regionBuilderPackages || []).find((item) => item.id === state.regionBuilderPackageId)?.sourceKind === "model-bundle";
}

function regionBuilderInstalledScope() {
  return regionBuilderModelBacked() && state.regionBuilderGeographyMode !== "custom";
}

function renderRegionBuilderMode() {
  const installed = regionBuilderInstalledScope();
  $("regionOutputOptions").hidden = installed;
  $("previewRegionBuild").hidden = installed;
  $("buildRegionAssets").hidden = installed;
  $("regionSourceLibrary").disabled = installed;
  $("regionDefinition").disabled = installed;
  if (installed) renderInstalledScopeSummary(); else renderRegionBuilderPreview();
  renderRegionMapLoadStatus();
}

function renderInstalledScopeSummary() {
  const box = $("regionBuilderPreview");
  const region = (state.regionBuilderRegions?.regions || []).find((item) => item.id === state.regionBuilderRegionId);
  const activePackage = (state.regionBuilderPackages || []).find((item) => item.id === state.regionBuilderPackageId);
  if (!box || !region) return;
  const azones = region.azones || [];
  box.className = "panel region-builder-preview";
  box.innerHTML = `
    <div class="section-title"><div><p class="step">Installed model scope</p><h3>${escapeHtml(region.name || `${activePackage?.name || "Installed model"} installed scope`)}</h3><p class="muted">Already installed from ${escapeHtml(activePackage?.name || region.shortName || "model package")}</p></div></div>
    <div class="region-preview-summary"><div><strong>${Number(region.selectedCount || 0).toLocaleString()}</strong><span>Included Bzones</span></div><div><strong>${azones.length.toLocaleString()}</strong><span>Azones / localities</span></div></div>
    ${azones.length ? `<p class="region-preview-localities"><strong>Included localities:</strong> ${azones.map(escapeHtml).join(", ")}</p>` : ""}
    <div class="region-preview-advisory"><p><strong>Installed model scope:</strong> Every displayed Azone and Bzone is contained in the model package.</p><button type="button" class="secondary" data-open-region-map>View map</button></div>`;
}

function renderRegionBuilderReference() {
  const box = $("regionBuilderReference");
  if (!box) return;
  const reference = state.regionBuilderReference;
  if (!reference) return;
  if (reference.error) {
    box.className = "notice error";
    box.textContent = reference.error;
    return;
  }
  const links = (reference.sources || []).map((source) => `<a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.label)}</a>`).join("");
  const checked = reference.package?.retrievedAt ? ` · checked ${escapeHtml(reference.package.retrievedAt)}` : "";
  const activePackage = (state.regionBuilderPackages || []).find((item) => item.id === state.regionBuilderPackageId);
  const modelBacked = activePackage?.sourceKind === "model-bundle";
  box.className = "region-builder-provenance";
  box.innerHTML = `<details><summary>Data sources${checked}</summary><div class="region-builder-provenance-body"><p><strong>Boundary:</strong> ${modelBacked ? "Geography contained in the installed model" : "Official VDOT MPO Study Areas"}</p><p><strong>Model geography:</strong> VisionEval Virginia Azone/Bzone geography</p><p><strong>Selection rule:</strong> ${modelBacked ? "Only Bzones present in the paired model package can be selected." : "A Bzone is included according to the installed regional package's boundary crosswalk."}</p><div class="region-builder-sources">${links}</div></div></details>`;
}

function regionBuilderPayload() {
  return {
    packageId: $("regionPackage").value,
    sourceLibraryId: $("regionSourceLibrary").value,
    regionId: $("regionDefinition").value,
    regionName: $("regionName").value,
    stateAbbr: $("regionState").value,
    geographyMode: state.regionBuilderGeographyMode,
    selectedBzones: state.regionBuilderGeographyMode === "custom" ? [...state.regionBuilderSelectedBzones] : [],
  };
}

function currentRegionBuilderIdentity() {
  return {name: $("regionName").value, state: $("regionState").value};
}

function applyRegionBuilderIdentity(mode) {
  const draft = state.regionBuilderIdentityDrafts[mode];
  if (!draft) return;
  $("regionName").value = draft.name || "";
  $("regionState").value = draft.state || "";
}

function initializeRegionBuilderIdentity(selectedRegion, force = false) {
  if (!selectedRegion) return;
  const key = `${state.regionBuilderPackageId}|${selectedRegion.id}`;
  if (force || state.regionBuilderIdentityKey !== key) {
    state.regionBuilderIdentityKey = key;
    state.regionBuilderIdentityDrafts = {
      official: {name: selectedRegion.name || "", state: selectedRegion.state || state.regionBuilderReference?.package?.state || ""},
      custom: null,
    };
  }
  applyRegionBuilderIdentity(state.regionBuilderGeographyMode);
}

function switchRegionBuilderIdentity(mode) {
  state.regionBuilderIdentityDrafts[state.regionBuilderGeographyMode] = currentRegionBuilderIdentity();
  if (mode === "custom" && !state.regionBuilderIdentityDrafts.custom) {
    state.regionBuilderIdentityDrafts.custom = {name: "", state: state.regionBuilderIdentityDrafts.official?.state || $("regionState").value};
  }
  state.regionBuilderGeographyMode = mode;
  applyRegionBuilderIdentity(mode);
  state.regionBuilderPreview = null;
  renderRegionGeographySummary();
  renderRegionBuilderMode();
  updateRegionBuilderAvailability();
}

function updateRegionBuilderAvailability(sources = state.regionBuilderSources?.sources || [], regions = state.regionBuilderRegions?.regions || []) {
  const custom = state.regionBuilderGeographyMode === "custom";
  const requiresCustom = regionBuilderModelBacked();
  const identityReady = Boolean($("regionName").value.trim());
  const geographyReady = !custom || state.regionBuilderSelectedBzones.size > 0;
  const ready = Boolean((!requiresCustom || custom) && sources.length && regions.length && identityReady && geographyReady);
  const reason = !identityReady ? "Enter a region name before previewing." : !geographyReady ? "Choose at least one Bzone before previewing." : "Choose an installed regional package and region first.";
  setButtonAvailability($("previewRegionBuild"), ready, reason);
  if (!ready) setButtonAvailability($("buildRegionAssets"), false, reason);
}

function resetRegionBuilderGeography() {
  state.regionBuilderGeographyMode = "official";
  state.regionBuilderGeographyOptions = null;
  state.regionBuilderGeographyKey = "";
  state.regionBuilderSelectedBzones = new Set();
  state.regionBuilderDraftBzones = new Set();
  state.regionBuilderDraftInitialized = false;
  state.regionBuilderGeographyQuery = "";
  applyRegionBuilderIdentity("official");
  renderRegionGeographySummary();
}

function renderRegionGeographySummary() {
  const summary = $("regionGeographySummary"), detail = $("regionGeographyDetail");
  if (!summary || !detail) return;
  const selectedRegion = (state.regionBuilderRegions?.regions || []).find((item) => item.id === state.regionBuilderRegionId);
  const custom = state.regionBuilderGeographyMode === "custom" && selectedRegion?.regionType !== "statewide";
  $("officialRegionGeographyView").hidden = custom;
  $("customRegionGeographyView").hidden = !custom;
  $("useOfficialRegionGeography").classList.toggle("active", !custom);
  $("customizeRegionGeography").classList.toggle("active", custom);
  $("useOfficialRegionGeography").setAttribute("aria-pressed", String(!custom));
  $("customizeRegionGeography").setAttribute("aria-pressed", String(custom));
  if (selectedRegion?.regionType === "statewide") {
    summary.textContent = "Complete statewide geography";
    detail.textContent = "Includes all 133 Virginia county-equivalent localities and 5,963 packaged Bzones.";
    return;
  }
  if (!custom) return;
  const selected = state.regionBuilderSelectedBzones;
  const representedAzones = (state.regionBuilderGeographyOptions?.azones || []).filter((item) => regionGeographyAzoneBzones(item).some((id) => selected.has(id))).length;
  summary.textContent = selected.size ? `${selected.size.toLocaleString()} planner-selected Bzones` : "No custom geography selected";
  detail.textContent = selected.size ? `${representedAzones.toLocaleString()} ${representedAzones === 1 ? "Azone" : "Azones"} represented in the custom geography.` : "Choose Azones and Bzones, then apply and preview the exact selection.";
  $("editCustomRegionGeography").textContent = selected.size ? "Edit geography…" : "Choose geography…";
  updateRegionBuilderAvailability();
}

async function loadRegionGeographyOptions() {
  const packageId = $("regionPackage").value, sourceLibraryId = $("regionSourceLibrary").value, regionId = $("regionDefinition").value;
  const key = `${packageId}|${sourceLibraryId}|${regionId}`;
  if (state.regionBuilderGeographyOptions && state.regionBuilderGeographyKey === key) return state.regionBuilderGeographyOptions;
  const query = new URLSearchParams({packageId, sourceLibraryId, regionId});
  state.regionBuilderGeographyOptions = await request(`/api/region-builder/geography-options?${query}`);
  state.regionBuilderGeographyKey = key;
  return state.regionBuilderGeographyOptions;
}

function regionGeographyAzoneBzones(azone) {
  return (state.regionBuilderGeographyOptions?.bzones || []).filter((item) => item.fips === azone.fips).map((item) => item.id);
}

function renderRegionGeographyDialog() {
  const options = state.regionBuilderGeographyOptions;
  if (!options) return;
  const query = state.regionBuilderGeographyQuery.trim().toLowerCase();
  const azones = (options.azones || []).filter((item) => !query || `${item.name} ${item.fips}`.toLowerCase().includes(query));
  const bzones = (options.bzones || []).filter((item) => !query || `${item.id} ${item.azone} ${item.fips}`.toLowerCase().includes(query));
  $("regionGeographyAzones").innerHTML = azones.map((item) => {
    const ids = regionGeographyAzoneBzones(item), selected = ids.filter((id) => state.regionBuilderDraftBzones.has(id)).length;
    return `<label class="check-option"><input type="checkbox" data-region-azone="${escapeHtml(item.fips)}" ${ids.length && selected === ids.length ? "checked" : ""}><span>${escapeHtml(item.name)} <small>${selected.toLocaleString()} / ${ids.length.toLocaleString()}</small></span></label>`;
  }).join("") || `<p class="empty-state">No matching Azones.</p>`;
  $("regionGeographyAzones").querySelectorAll("[data-region-azone]").forEach((input) => {
    const item = options.azones.find((value) => value.fips === input.dataset.regionAzone), ids = regionGeographyAzoneBzones(item);
    const selected = ids.filter((id) => state.regionBuilderDraftBzones.has(id)).length;
    input.indeterminate = selected > 0 && selected < ids.length;
  });
  $("regionGeographyBzones").innerHTML = bzones.map((item) => `<label class="check-option"><input type="checkbox" data-region-bzone="${escapeHtml(item.id)}" ${state.regionBuilderDraftBzones.has(item.id) ? "checked" : ""}><span>${escapeHtml(item.id)} <small>${escapeHtml(item.azone)}</small></span></label>`).join("") || `<p class="empty-state">No matching Bzones.</p>`;
  const selected = state.regionBuilderDraftBzones;
  const representedAzones = (options.azones || []).filter((item) => regionGeographyAzoneBzones(item).some((id) => selected.has(id))).length;
  $("regionGeographyStatus").textContent = `${representedAzones.toLocaleString()} ${representedAzones === 1 ? "Azone" : "Azones"} represented · ${selected.size.toLocaleString()} ${selected.size === 1 ? "Bzone" : "Bzones"} selected`;
  $("regionGeographyFooterCount").textContent = `${selected.size.toLocaleString()} ${selected.size === 1 ? "Bzone" : "Bzones"} selected`;
  $("applyRegionGeography").disabled = selected.size === 0;
  renderRegionGeographySelectionMap();
}

function updateCustomRegionMapView() {
  if (state.regionBuilderGeographyFrame) return;
  state.regionBuilderGeographyFrame = requestAnimationFrame(() => {
    state.regionBuilderGeographyFrame = null;
    const svg = $("regionGeographyMap")?.querySelector("[data-custom-region-svg]");
    const view = state.regionBuilderGeographyView;
    if (svg) svg.setAttribute("viewBox", `${view.x} ${view.y} ${view.width} ${view.height}`);
  });
}

function renderRegionGeographySelectionMap({rebuild = false, relabel = true} = {}) {
  const canvas = $("regionGeographyMap"), data = state.regionMapData, options = state.regionBuilderGeographyOptions;
  if (!canvas || !data || !options) return;
  const bounds = regionMapBounds([data.azones, data.bzones]);
  if (!bounds) { canvas.innerHTML = '<p class="empty-state">Virginia geography is unavailable.</p>'; return; }
  const projection = regionMapProjection(bounds), selected = state.regionBuilderDraftBzones;
  const known = new Set((options.bzones || []).map((item) => String(item.id)));
  const azoneBzones = new Map();
  (options.bzones || []).forEach((item) => { const id=String(item.fips); if(!azoneBzones.has(id))azoneBzones.set(id,[]); azoneBzones.get(id).push(String(item.id)); });
  const sceneKey = `${state.regionMapKey}|${state.regionBuilderGeographyKey}`;
  let svg = canvas.querySelector("[data-custom-region-svg]");
  if (rebuild || !svg || canvas.dataset.sceneKey !== sceneKey) {
    const azonePaths = (data.azones?.features || []).map((feature) => {
      const id = String(feature.properties?.azoneId || feature.properties?.Azones || ""), ids = azoneBzones.get(id) || [];
      return `<path class="custom-region-azone" data-custom-region-azone="${escapeHtml(id)}" d="${regionMapPath(feature, projection)}"><title>${escapeHtml(feature.properties?.localityName || feature.properties?.name || id)} · 0/${ids.length} Bzones selected</title></path>`;
    }).join("");
    const bzonePaths = (data.bzones?.features || []).map((feature) => {
      const id = String(feature.properties?.bzoneId || feature.properties?.GEOID || "");
      return known.has(id) ? `<path class="custom-region-bzone" data-custom-region-bzone="${escapeHtml(id)}" d="${regionMapPath(feature, projection)}"><title>${escapeHtml(feature.properties?.localityName || '')} · ${escapeHtml(id)}</title></path>` : "";
    }).join("");
    const mpoPaths = (data.mpos?.features || []).map((feature) => `<path class="custom-region-mpo" d="${regionMapPath(feature, projection)}"></path>`).join("");
    const view = state.regionBuilderGeographyView;
    canvas.innerHTML = `<svg data-custom-region-svg viewBox="${view.x} ${view.y} ${view.width} ${view.height}" role="img" aria-label="Select custom Virginia Azones and Bzones"><g data-custom-region-azones>${azonePaths}</g><g data-custom-region-bzones>${bzonePaths}</g><g data-custom-region-labels></g><g data-custom-region-mpos>${mpoPaths}</g></svg>`;
    canvas.dataset.sceneKey = sceneKey;
    svg = canvas.querySelector("[data-custom-region-svg]");
    canvas.querySelectorAll("[data-custom-region-azone]").forEach((path) => path.addEventListener("click", () => {
      const ids = azoneBzones.get(path.dataset.customRegionAzone) || [], add = ids.some((id) => !state.regionBuilderDraftBzones.has(id));
      ids.forEach((id) => add ? state.regionBuilderDraftBzones.add(id) : state.regionBuilderDraftBzones.delete(id)); renderRegionGeographyDialog();
    }));
    canvas.querySelectorAll("[data-custom-region-bzone]").forEach((path) => path.addEventListener("click", () => {
      const id = path.dataset.customRegionBzone; if (state.regionBuilderDraftBzones.has(id)) state.regionBuilderDraftBzones.delete(id); else state.regionBuilderDraftBzones.add(id); renderRegionGeographyDialog();
    }));
    canvas.onwheel = (event) => { event.preventDefault(); zoomCustomRegionMap(event.deltaY < 0 ? .8 : 1.25); };
    svg?.addEventListener("pointerdown",(event)=>{
      if(event.button!==0||event.target!==svg)return;
      event.preventDefault();
      state.regionBuilderGeographyPan={startX:event.clientX,startY:event.clientY,rect:svg.getBoundingClientRect(),view:{...state.regionBuilderGeographyView}};
      canvas.classList.add("is-panning");
    });
  }
  canvas.querySelector("[data-custom-region-mpos]")?.toggleAttribute("hidden", !$("customRegionMpoLayer")?.checked);
  canvas.querySelector("[data-custom-region-azones]")?.toggleAttribute("hidden", !$("customRegionAzoneLayer")?.checked);
  canvas.querySelector("[data-custom-region-bzones]")?.toggleAttribute("hidden", !$("customRegionBzoneLayer")?.checked);
  canvas.querySelectorAll("[data-custom-region-bzone]").forEach((path) => path.classList.toggle("selected", selected.has(path.dataset.customRegionBzone)));
  canvas.querySelectorAll("[data-custom-region-azone]").forEach((path) => {
    const ids=azoneBzones.get(path.dataset.customRegionAzone)||[], count=ids.filter((id)=>selected.has(id)).length;
    path.classList.toggle("selected", count>0); const title=path.querySelector("title"); if(title)title.textContent=`${title.textContent.split(" · ")[0]} · ${count}/${ids.length} Bzones selected`;
  });
  updateCustomRegionMapView();
  if (!relabel) return;
  const labelEntries = [], showAzoneNames = $("customRegionAzoneLabels")?.checked, showAzoneIds = $("customRegionAzoneIdLabels")?.checked;
  if ((showAzoneNames || showAzoneIds) && $("customRegionAzoneLayer")?.checked) (data.azones?.features || []).forEach((feature) => {
    const id=String(feature.properties?.azoneId||feature.properties?.Azones||""),ids=azoneBzones.get(id)||[],name=feature.properties?.localityName||feature.properties?.name||id,shortName=WorkbenchPolygonLabels.shortenLocality(name);
    const candidates = showAzoneNames && showAzoneIds ? [[name, id], ...(shortName && shortName !== name ? [[shortName, id]] : []), [id]] : showAzoneNames ? [[name], ...(shortName && shortName !== name ? [[shortName]] : [])] : [[id]];
    labelEntries.push({feature,priority:ids.some((value)=>selected.has(value))?35:0,candidates,className:showAzoneNames?"custom-region-azone-label":"custom-region-azone-id-label"});
  });
  if ($("customRegionBzoneLabels")?.checked && $("customRegionBzoneLayer")?.checked) (data.bzones?.features || []).forEach((feature) => { const id=String(feature.properties?.bzoneId||feature.properties?.GEOID||""); if(known.has(id))labelEntries.push({feature,priority:selected.has(id)?40:0,candidates:[[id]],className:"custom-region-bzone-label"}); });
  WorkbenchPolygonLabels.layout({group:canvas.querySelector("[data-custom-region-labels]"),entries:labelEntries,view:state.regionBuilderGeographyView,viewport:{width:Math.max(1,canvas.clientWidth),height:Math.max(1,canvas.clientHeight)},project:projection.point,pathFor:(feature)=>regionMapPath(feature,projection),maxLabels:250});
}

window.addEventListener("pointermove",(event)=>{
  const pan=state.regionBuilderGeographyPan;if(!pan)return;
  const dx=(event.clientX-pan.startX)/Math.max(1,pan.rect.width)*pan.view.width,dy=(event.clientY-pan.startY)/Math.max(1,pan.rect.height)*pan.view.height;
  state.regionBuilderGeographyView={...pan.view,x:pan.view.x-dx,y:pan.view.y-dy};
  updateCustomRegionMapView();
  $("regionGeographyMap")?.classList.add("is-panning");
});
window.addEventListener("pointerup",()=>{state.regionBuilderGeographyPan=null;$("regionGeographyMap")?.classList.remove("is-panning");});
window.addEventListener("pointercancel",()=>{state.regionBuilderGeographyPan=null;$("regionGeographyMap")?.classList.remove("is-panning");});

function zoomCustomRegionMap(factor) {
  const view = state.regionBuilderGeographyView, width = Math.max(80, Math.min(1000, view.width * factor)), height = width * .62;
  state.regionBuilderGeographyView = {x: view.x + (view.width-width)/2, y: view.y + (view.height-height)/2, width, height};
  updateCustomRegionMapView();
}

async function openRegionGeographyDialog() {
  const button = $("editCustomRegionGeography");
  setBusy(button, true, "Loading…");
  try {
    // Geography options now guarantee MPO boundary metadata. Loading them
    // first also primes the statewide geometry cache used by the map request.
    await loadRegionGeographyOptions();
    await preloadRegionMapGeometry();
    if (!state.regionBuilderDraftInitialized) {
      state.regionBuilderDraftBzones = new Set(state.regionBuilderGeographyMode === "custom" ? state.regionBuilderSelectedBzones : []);
      state.regionBuilderDraftInitialized = true;
    }
    state.regionBuilderGeographyView = {x: 0, y: 0, width: 1000, height: 620};
    state.regionBuilderGeographyQuery = "";
    $("regionGeographySearch").value = "";
    $("regionGeographyCsv").value = "";
    renderRegionGeographyDialog();
    $("regionGeographyDialog").showModal();
  } catch (error) {
    notify(error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function parseRegionGeographyCsv(text) {
  const lines = String(text).replace(/\r/g, "").split("\n").filter((line) => line.trim());
  if (!lines.length) throw new Error("The CSV is empty.");
  const parseLine = (line) => { const values = []; let value = "", quoted = false; for (let index = 0; index < line.length; index += 1) { const char = line[index]; if (char === '"' && line[index + 1] === '"' && quoted) { value += '"'; index += 1; } else if (char === '"') quoted = !quoted; else if (char === "," && !quoted) { values.push(value.trim()); value = ""; } else value += char; } values.push(value.trim()); return values; };
  const headers = parseLine(lines[0]).map((value) => value.toLowerCase().replace(/[^a-z]/g, ""));
  const azoneIndex = headers.indexOf("azone"), bzoneIndex = headers.indexOf("bzone");
  if (azoneIndex < 0 && bzoneIndex < 0) throw new Error("CSV must contain an Azone or Bzone column.");
  const options = state.regionBuilderGeographyOptions, byAzone = new Map(), knownBzones = new Set((options.bzones || []).map((item) => item.id));
  (options.azones || []).forEach((item) => { byAzone.set(item.name.toLowerCase(), item); byAzone.set(item.fips, item); });
  const selected = new Set(), unknown = [];
  lines.slice(1).forEach((line, rowIndex) => { const values = parseLine(line); const azoneValue = azoneIndex >= 0 ? (values[azoneIndex] || "").trim() : ""; const bzoneValue = bzoneIndex >= 0 ? (values[bzoneIndex] || "").trim() : ""; if (azoneValue) { const azone = byAzone.get(azoneValue.toLowerCase()); if (azone) regionGeographyAzoneBzones(azone).forEach((id) => selected.add(id)); else unknown.push(`row ${rowIndex + 2}: Azone ${azoneValue}`); } if (bzoneValue) { if (knownBzones.has(bzoneValue)) selected.add(bzoneValue); else unknown.push(`row ${rowIndex + 2}: Bzone ${bzoneValue}`); } });
  if (unknown.length) throw new Error(`Unknown geography (${unknown.slice(0, 5).join("; ")}${unknown.length > 5 ? "; …" : ""}).`);
  if (!selected.size) throw new Error("The CSV did not select any Bzones.");
  return selected;
}

function renderRegionBuilderPreview() {
  const box = $("regionBuilderPreview");
  if (!box) return;
  const preview = state.regionBuilderPreview;
  $("buildRegionAssets").disabled = !preview;
  if (!preview) {
    box.className = "panel region-builder-preview empty-state";
    box.textContent = "Choose a source and region, then preview the generated assets.";
    return;
  }
  box.className = "panel region-builder-preview";
  const selection = preview.selection || {};
  const rows = (preview.files || []).map((item) => `<tr><td>${escapeHtml(item.file)}</td><td>${escapeHtml(item.action)}</td><td>${escapeHtml(item.level || "non-spatial")}</td><td>${item.rowsBefore ?? "—"}</td><td>${item.rowsAfter ?? "—"}</td></tr>`).join("");
  const azones = (selection.azones || []).map((item) => escapeHtml(item)).join(", ");
  const boundary = selection.boundary || {};
  const sourceName = preview.sourceLibrary?.name || preview.sourceTemplate?.name || "source";
  const title = state.regionBuilderGeographyMode === "custom"
    ? ($("regionName").value.trim() || "Selected region")
    : (preview.region?.name || "Selected region");
  const selectedCount = boundary.selectedCount || (selection.bzones || []).length;
  const includedBoundary = boundary.boundaryCount || 0;
  const customized = selection.method === "custom-bzone-selection";
  const installedScope = selection.method === "installed-model-scope";
  const added = (boundary.addedBzones || []).length, removed = (boundary.removedBzones || []).length;
  const copiedFiles = (preview.files || []).length;
  const warnings = (preview.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join("");
  box.innerHTML = `
    <div class="section-title"><div><p class="step">Region preview</p><h3>${escapeHtml(title)}</h3><p class="muted">Prepared from ${escapeHtml(sourceName)}</p></div></div>
    <div class="region-preview-summary"><div><strong>${selectedCount.toLocaleString()}</strong><span>Included Bzones</span></div><div><strong>${(selection.azones || []).length.toLocaleString()}</strong><span>Azones / localities</span></div><div><strong>${(customized ? added : includedBoundary).toLocaleString()}</strong><span>${customized ? "Added vs. official" : "Boundary overlaps included"}</span></div>${customized ? `<div><strong>${removed.toLocaleString()}</strong><span>Removed vs. official</span></div>` : ""}</div>
    ${azones ? `<p class="region-preview-localities"><strong>Included localities:</strong> ${azones}</p>` : ""}
    <div class="region-preview-advisory"><p><strong>${customized ? "Planner-defined geography" : installedScope ? "Installed model scope" : "Boundary review"}:</strong> ${customized ? `${removed} Bzones are excluded from the installed model scope.` : installedScope ? "Every displayed Azone and Bzone is contained in the model package." : `${includedBoundary} boundary-crossing ${includedBoundary === 1 ? "Bzone is" : "Bzones are"} included according to the installed regional package.`}</p><button type="button" class="secondary" data-open-region-map>View map</button></div>
    <div class="region-preview-build"><strong>Ready to build</strong><p class="muted">Workbench will create a filtered Input Library and runnable model package from ${copiedFiles} input files. Azone and Marea values remain whole-locality values.</p></div>
    <details class="region-preview-technical"><summary>Technical details</summary>${warnings ? `<ul>${warnings}</ul>` : ""}<table><thead><tr><th>File</th><th>Action</th><th>Level</th><th>Rows before</th><th>Rows after</th></tr></thead><tbody>${rows}</tbody></table></details>`;
}

function renderRegionBuilderPreviewError() {
  const box = $("regionBuilderPreviewError");
  if (!box) return;
  box.hidden = !state.regionBuilderPreviewError;
  box.innerHTML = state.regionBuilderPreviewError
    ? `<strong>Region preview could not be generated.</strong><p>${escapeHtml(state.regionBuilderPreviewError)} Your geography selection is preserved. Review the inputs and choose Preview region to retry.</p>`
    : "";
}

async function previewRegionBuild(button = $("previewRegionBuild")) {
  setBusy(button, true, "Previewing…");
  state.regionBuilderPreviewError = "";
  renderRegionBuilderPreviewError();
  try {
    const payload = regionBuilderPayload();
    state.regionBuilderPreview = await post("/api/region-builder/preview", payload);
    renderRegionBuilderPreview();
    return state.regionBuilderPreview;
  } catch (error) {
    state.regionBuilderPreview = null;
    state.regionBuilderPreviewError = error.message || String(error);
    renderRegionBuilderPreview();
    renderRegionBuilderPreviewError();
    return null;
  } finally {
    setBusy(button, false);
  }
}

function regionMapGeometryRings(geometry) {
  if (!geometry) return [];
  if (geometry.type === "Polygon") return geometry.coordinates || [];
  if (geometry.type === "MultiPolygon") return (geometry.coordinates || []).flat();
  return [];
}

function regionMapBounds(collections) {
  const bounds = {minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity};
  collections.flatMap((collection) => collection?.features || []).forEach((feature) => {
    regionMapGeometryRings(feature.geometry).flat().forEach(([rawX, rawY]) => {
      const x = Number(rawX), y = Number(rawY);
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;
      bounds.minX = Math.min(bounds.minX, x); bounds.maxX = Math.max(bounds.maxX, x);
      bounds.minY = Math.min(bounds.minY, y); bounds.maxY = Math.max(bounds.maxY, y);
    });
  });
  return Number.isFinite(bounds.minX) ? bounds : null;
}

function regionMapProjection(bounds) {
  const width = 1000, height = 620, padding = 24;
  const dx = Math.max(bounds.maxX - bounds.minX, 0.00001);
  const dy = Math.max(bounds.maxY - bounds.minY, 0.00001);
  const scale = Math.min((width - padding * 2) / dx, (height - padding * 2) / dy);
  const drawnWidth = dx * scale, drawnHeight = dy * scale;
  const offsetX = (width - drawnWidth) / 2, offsetY = (height - drawnHeight) / 2;
  return { width, height, point: ([x, y]) => [offsetX + (Number(x) - bounds.minX) * scale, height - offsetY - (Number(y) - bounds.minY) * scale] };
}

function regionMapPath(feature, projection) {
  return regionMapGeometryRings(feature.geometry).map((ring) => ring.map((point, index) => `${index ? "L" : "M"}${projection.point(point).map((value) => value.toFixed(2)).join(" ")}`).join(" ") + " Z").join(" ");
}

function regionMapFeatureCenter(feature, projection) {
  const points = regionMapGeometryRings(feature.geometry).flat();
  if (!points.length) return [0, 0];
  const projected = points.map(projection.point);
  return [(Math.min(...projected.map((point) => point[0])) + Math.max(...projected.map((point) => point[0]))) / 2, (Math.min(...projected.map((point) => point[1])) + Math.max(...projected.map((point) => point[1]))) / 2];
}

function regionMapFeatureBounds(feature, projection) {
  const points = regionMapGeometryRings(feature?.geometry).flat().map(projection.point);
  if (!points.length) return null;
  return {
    minX: Math.min(...points.map((point) => point[0])), maxX: Math.max(...points.map((point) => point[0])),
    minY: Math.min(...points.map((point) => point[1])), maxY: Math.max(...points.map((point) => point[1])),
  };
}

function regionMapPointInRing(point, ring, projection) {
  const vertices = ring.map(projection.point);
  let inside = false;
  for (let index = 0, previous = vertices.length - 1; index < vertices.length; previous = index++) {
    const [xi, yi] = vertices[index], [xj, yj] = vertices[previous];
    if ((yi > point.y) !== (yj > point.y) && point.x < (xj - xi) * (point.y - yi) / ((yj - yi) || Number.EPSILON) + xi) inside = !inside;
  }
  return inside;
}

function regionMapFeatureContains(feature, point, projection) {
  const geometry = feature?.geometry;
  if (!geometry) return false;
  const polygons = geometry.type === "Polygon" ? [geometry.coordinates || []] : geometry.type === "MultiPolygon" ? geometry.coordinates || [] : [];
  return polygons.some((rings) => rings.length && regionMapPointInRing(point, rings[0], projection) && !rings.slice(1).some((ring) => regionMapPointInRing(point, ring, projection)));
}

function regionMapViewportRatio() {
  const canvas = $("regionMapCanvas");
  return canvas.clientWidth > 0 && canvas.clientHeight > 0 ? canvas.clientWidth / canvas.clientHeight : 1000 / 620;
}

function regionMapFullView(projection) {
  const ratio = regionMapViewportRatio();
  let width = projection.width, height = projection.height;
  if (width / height < ratio) width = height * ratio;
  else height = width / ratio;
  return {x: (projection.width - width) / 2, y: (projection.height - height) / 2, width, height};
}

function constrainRegionMapView(view) {
  const full = state.regionMapScene?.fullView || view;
  const ratio = regionMapViewportRatio();
  const maxWidth = full.width * 1.15;
  const width = Math.min(maxWidth, Math.max(full.width / 256, Number(view.width) || full.width));
  const height = width / ratio;
  const minX = full.x - width * 0.75, maxX = full.x + full.width - width * 0.25;
  const minY = full.y - height * 0.75, maxY = full.y + full.height - height * 0.25;
  return {
    x: Math.min(maxX, Math.max(minX, Number(view.x) || 0)),
    y: Math.min(maxY, Math.max(minY, Number(view.y) || 0)),
    width,
    height,
  };
}

function setRegionMapView(view) {
  state.regionMapView = constrainRegionMapView(view);
  const svg = $("regionMapCanvas").querySelector("[data-region-map-svg]");
  svg?.setAttribute("viewBox", `${state.regionMapView.x} ${state.regionMapView.y} ${state.regionMapView.width} ${state.regionMapView.height}`);
  const scale = Math.max(0.08, state.regionMapView.width / 1000);
  svg?.querySelectorAll(".region-map-label").forEach((label) => {
    label.style.fontSize = `${12 * scale}px`;
    label.style.strokeWidth = `${3 * scale}px`;
  });
  updateRegionMapNameLabels();
  updateRegionMapIdLabels();
}

function regionMapSegmentDistance(point, start, end) {
  let x=start[0],y=start[1],dx=end[0]-x,dy=end[1]-y;
  if(dx||dy){const t=((point[0]-x)*dx+(point[1]-y)*dy)/(dx*dx+dy*dy);if(t>1){x=end[0];y=end[1]}else if(t>0){x+=dx*t;y+=dy*t}}
  dx=point[0]-x;dy=point[1]-y;return Math.sqrt(dx*dx+dy*dy);
}

function regionMapSignedDistance(point, feature, projection) {
  const projected={x:point[0],y:point[1]},inside=regionMapFeatureContains(feature,projected,projection);
  let distance=Infinity;
  for(const ring of regionMapGeometryRings(feature.geometry)){const vertices=ring.map(projection.point);for(let index=0,previous=vertices.length-1;index<vertices.length;previous=index++)distance=Math.min(distance,regionMapSegmentDistance(point,vertices[previous],vertices[index]));}
  return (inside?1:-1)*distance;
}

function regionMapInteriorLabel(feature, projection) {
  const bounds=regionMapFeatureBounds(feature,projection);if(!bounds)return{x:0,y:0,radius:0};
  let best={x:(bounds.minX+bounds.maxX)/2,y:(bounds.minY+bounds.maxY)/2,radius:-Infinity};
  let span=Math.max(bounds.maxX-bounds.minX,bounds.maxY-bounds.minY),step=Math.max(span/7,.001);
  for(let pass=0;pass<6;pass++){
    const minX=pass?best.x-step*2:bounds.minX,maxX=pass?best.x+step*2:bounds.maxX,minY=pass?best.y-step*2:bounds.minY,maxY=pass?best.y+step*2:bounds.maxY;
    for(let x=minX;x<=maxX;x+=step)for(let y=minY;y<=maxY;y+=step){const radius=regionMapSignedDistance([x,y],feature,projection);if(radius>best.radius)best={x,y,radius};}
    step/=2;
  }
  return best;
}

function regionMapFeaturesView(features, projection) {
  const projected = features.flatMap((feature) => regionMapGeometryRings(feature?.geometry).flat().map(projection.point));
  if (!projected.length) return regionMapFullView(projection);
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  projected.forEach(([x, y]) => { minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y); });
  const spanX = Math.max(1, maxX - minX), spanY = Math.max(1, maxY - minY);
  let width = Math.max(80, spanX * 1.18);
  let height = Math.max(50, spanY * 1.18);
  const ratio = regionMapViewportRatio();
  if (width / height > ratio) height = width / ratio; else width = height * ratio;
  return {x: (minX + maxX - width) / 2, y: (minY + maxY - height) / 2, width, height};
}

function zoomRegionMap(factor, anchor) {
  const view = state.regionMapView;
  if (!view) return;
  const point = anchor || {x: view.x + view.width / 2, y: view.y + view.height / 2};
  const width = view.width * factor, height = width / regionMapViewportRatio();
  const xRatio = (point.x - view.x) / view.width, yRatio = (point.y - view.y) / view.height;
  setRegionMapView({x: point.x - xRatio * width, y: point.y - yRatio * height, width, height});
}

function applyRegionMapLayers() {
  document.querySelectorAll("[data-region-map-layer]").forEach((input) => {
    const group = $("regionMapCanvas").querySelector(`[data-map-group="${input.dataset.regionMapLayer}"]`);
    if (group) group.style.display = regionMapLayerVisible(input.dataset.regionMapLayer) ? "" : "none";
  });
  updateRegionMapNameLabels();
  updateRegionMapIdLabels();
  if (state.regionMapSelectedFeature && !regionMapSelectedFeatureVisible()) clearRegionMapInspector();
}

function configureRegionMapControls() {
  const modelScoped = regionBuilderModelBacked();
  const modelName = (state.regionBuilderPackages || []).find((item) => item.id === state.regionBuilderPackageId)?.name || "Model";
  document.querySelector("#regionMapDialog .region-map-shell")?.classList.toggle("model-scope", modelScoped);
  $("regionMapFocus").hidden = modelScoped;
  $("regionMapSelectedLayerWrapper").hidden = modelScoped;
  $("regionMapBoundaryLayerWrapper").hidden = modelScoped;
  $("regionMapNameLabelsWrapper").hidden = modelScoped;
  $("regionMapSelectedLegend").hidden = modelScoped;
  $("regionMapBoundaryLegend").hidden = modelScoped;
  $("regionMapMpoLayerWrapper").querySelector("span").textContent = modelScoped ? `${modelName} boundary` : "All MPO boundaries";
  $("regionMapAzoneLayerWrapper").querySelector("span").textContent = modelScoped ? "Azones" : "All Azones";
  $("regionMapBzoneLayerWrapper").querySelector("span").textContent = modelScoped ? "Bzones" : "All Bzones";
  $("regionMapMpoLegend").querySelector("span").textContent = modelScoped ? `${modelName} boundary` : "All MPO boundaries";
  $("regionMapAzoneLegend").querySelector("span").textContent = modelScoped ? "Azones" : "All Azones";
  $("regionMapBzoneLegend").querySelector("span").textContent = modelScoped ? "Bzones" : "All Bzones";
  $("fitRegionMap").textContent = modelScoped ? "Fit scope" : "Fit MPO";
  $("resetRegionMap").textContent = modelScoped ? "Full scope" : "Virginia";
}

function regionMapLayerVisible(name) {
  const input = document.querySelector(`[data-region-map-layer="${name}"]`);
  return Boolean(input?.checked && !input.closest("[hidden]"));
}

function regionMapVisibleBzoneIds() {
  const scene = state.regionMapScene;
  if (!scene) return new Set();
  if (regionMapLayerVisible("all-bzones")) return null;
  const selected = new Set((scene.currentRegion?.selectedBzones || []).map(String));
  const included = new Set((scene.currentRegion?.includedBoundaryBzones || []).map(String));
  const visible = new Set();
  if (regionMapLayerVisible("selected-bzones")) {
    selected.forEach((id) => { if (!included.has(id)) visible.add(id); });
  }
  if (regionMapLayerVisible("included-boundary")) included.forEach((id) => visible.add(id));
  return visible;
}

function regionMapSelectedFeatureVisible() {
  const selected = state.regionMapSelectedFeature;
  if (!selected) return false;
  if (selected.type === "azone") return regionMapLayerVisible("azones");
  if (selected.type === "mpo") return regionMapLayerVisible("mpos");
  if (selected.type !== "bzone") return false;
  const visibleBzones = regionMapVisibleBzoneIds();
  return visibleBzones === null || visibleBzones.has(String(selected.id));
}

function regionMapScreenPosition(point, view, width, height) {
  return {x: (point[0] - view.x) / view.width * width, y: (point[1] - view.y) / view.height * height};
}

function regionMapOccupyLabel(occupied, screenX, screenY, cellWidth, cellHeight, rowSpan = 1) {
  const x = Math.floor(screenX / cellWidth), y = Math.floor(screenY / cellHeight);
  for (let row = 0; row < rowSpan; row += 1) {
    if (occupied.has(`${x}:${y + row}`)) return false;
  }
  for (let row = 0; row < rowSpan; row += 1) occupied.add(`${x}:${y + row}`);
  return true;
}

function updateRegionMapLabelControls() {
  const input = $("regionMapNameLabels"), wrapper = $("regionMapNameLabelsWrapper");
  if (!input || !wrapper) return;
  const hasMpo = Boolean(state.regionMapScene?.currentRegion);
  input.disabled = !hasMpo;
  const reason = hasMpo ? "Show names for localities participating in the selected MPO." : "Choose an MPO to enable selected-MPO locality names.";
  input.title = reason;
  wrapper.title = reason;
}

function updateRegionMapNameLabels(sharedOccupied = null) {
  const occupied = sharedOccupied instanceof Set ? sharedOccupied : new Set();
  const scene = state.regionMapScene;
  if (!scene?.groups?.labels) return;
  updateRegionMapLabelControls();
  if (!$("regionMapNameLabels")?.checked || !regionMapLayerVisible("azones")) {
    scene.groups.labels.innerHTML = "";
    return occupied;
  }
  const region = scene.currentRegion;
  const participating = new Set(region?.azoneFips || []);
  const entries = region
    ? [...scene.azoneFeatures].filter(([id]) => participating.has(String(id)))
    : [];
  const view = state.regionMapView || scene.fullView;
  const canvas = $("regionMapCanvas"), width = Math.max(1, canvas.clientWidth), height = Math.max(1, canvas.clientHeight);
  const labels = [];
  const includeId = Boolean($("regionMapIdLabels")?.checked);
  for (const [id, feature] of entries) {
    const center = scene.featureCenters.get(`azone:${id}`);
    if (!center || center[0] < view.x || center[0] > view.x + view.width || center[1] < view.y || center[1] > view.y + view.height) continue;
    const {x: screenX, y: screenY} = regionMapScreenPosition(center, view, width, height);
    if (!regionMapOccupyLabel(occupied, screenX, screenY, includeId ? 132 : 118, includeId ? 38 : 28, includeId ? 2 : 1)) continue;
    const label = feature.properties?.localityName || feature.properties?.name || scene.localityNames.get(String(id)) || "";
    labels.push(`<text class="region-map-label${includeId ? " region-map-name-id" : ""}" x="${center[0].toFixed(2)}" y="${center[1].toFixed(2)}" text-anchor="middle">${includeId ? `<tspan x="${center[0].toFixed(2)}" dy="-0.58em">${escapeHtml(label)}</tspan><tspan class="zone-id-line" x="${center[0].toFixed(2)}" dy="1.32em">${escapeHtml(id)}</tspan>` : escapeHtml(label)}</text>`);
  }
  scene.groups.labels.innerHTML = labels.join("");
  const scale = Math.max(0.08, view.width / 1000);
  scene.groups.labels.querySelectorAll(".region-map-label").forEach((label) => {
    label.style.fontSize = `${(label.classList.contains("region-map-name-id") ? 9.5 : 11) * scale}px`;
    label.style.strokeWidth = `${3 * scale}px`;
  });
  return occupied;
}

function updateRegionMapIdLabels() {
  const scene = state.regionMapScene, view = state.regionMapView;
  if (!scene?.groups?.idLabels || !view || !$('regionMapIdLabels')?.checked) {
    if (scene?.groups?.idLabels) scene.groups.idLabels.innerHTML = "";
    return;
  }
  const zoom = scene.fullView.width / view.width;
  const visibleBzoneIds = new Set();
  if (regionMapLayerVisible("all-bzones")) {
    scene.bzoneFeatures.forEach((_feature, id) => visibleBzoneIds.add(id));
  } else if (scene.currentRegion) {
    const selected = new Set((scene.currentRegion.selectedBzones || []).map(String));
    const included = new Set((scene.currentRegion.includedBoundaryBzones || []).map(String));
    if (regionMapLayerVisible("selected-bzones")) {
      selected.forEach((id) => { if (!included.has(id)) visibleBzoneIds.add(id); });
    }
    if (regionMapLayerVisible("included-boundary")) {
      included.forEach((id) => visibleBzoneIds.add(id));
    }
  }
  const useBzones = zoom >= 40 && visibleBzoneIds.size > 0;
  const useAzones = !useBzones && zoom >= 1.75 && regionMapLayerVisible("azones");
  if (!useBzones && !useAzones) { scene.groups.idLabels.innerHTML = ""; return; }
  const canvas = $("regionMapCanvas"), width = Math.max(1, canvas.clientWidth), height = Math.max(1, canvas.clientHeight);
  const cellWidth = useBzones ? 132 : 82, cellHeight = useBzones ? 30 : 28;
  const occupied = updateRegionMapNameLabels(new Set()) || new Set(), selected = new Set(scene.currentRegion?.selectedBzones || []);
  const namedAzones = !useBzones && $("regionMapNameLabels")?.checked && scene.currentRegion
    ? new Set((scene.currentRegion.azoneFips || []).map(String))
    : new Set();
  const entries = useBzones ? [...visibleBzoneIds].map((id) => ({id, feature: scene.bzoneFeatures.get(id)})).filter((entry) => entry.feature) : [...scene.azoneFeatures].map(([id, feature]) => ({id, feature}));
  entries.sort((left, right) => Number(selected.has(right.id)) - Number(selected.has(left.id)) || left.id.localeCompare(right.id));
  const labels = [];
  for (const entry of entries) {
    if (!useBzones && namedAzones.has(String(entry.id))) continue;
    const center = scene.featureCenters.get(`${useBzones ? "bzone" : "azone"}:${entry.id}`);
    if (!center || center[0] < view.x || center[0] > view.x + view.width || center[1] < view.y || center[1] > view.y + view.height) continue;
    const {x: screenX, y: screenY} = regionMapScreenPosition(center, view, width, height);
    if (useBzones) {
      const bounds = regionMapFeatureBounds(entry.feature, scene.projection);
      if (!bounds) continue;
      const screenMin = regionMapScreenPosition([bounds.minX, bounds.minY], view, width, height);
      const screenMax = regionMapScreenPosition([bounds.maxX, bounds.maxY], view, width, height);
      const availableWidth = Math.abs(screenMax.x - screenMin.x), availableHeight = Math.abs(screenMax.y - screenMin.y);
      const fontPx = 5.2;
      if (availableWidth < entry.id.length * fontPx * 0.78 + 8 || availableHeight < fontPx * 1.8) continue;
    }
    if (!regionMapOccupyLabel(occupied, screenX, screenY, cellWidth, cellHeight)) continue;
    const labelClass = useBzones ? "bzone-id" : "azone-id";
    labels.push(`<text class="region-map-label region-map-id-label ${labelClass}" x="${center[0].toFixed(2)}" y="${center[1].toFixed(2)}" text-anchor="middle">${escapeHtml(entry.id)}</text>`);
    if (labels.length >= (useBzones ? 45 : 90)) break;
  }
  scene.groups.idLabels.innerHTML = labels.join("");
  const scale = Math.max(0.08, view.width / 1000);
  scene.groups.idLabels.querySelectorAll(".region-map-label").forEach((label) => {
    const base = label.classList.contains("bzone-id") ? 5.2 : 9;
    label.style.fontSize = `${base * scale}px`;
    label.style.strokeWidth = `${2.5 * scale}px`;
  });
}

function regionMapOverlayPath(scene, geoid, className, suffix) {
  const item = scene.bzonePaths.get(String(geoid));
  return item ? `<path class="${className}" d="${item.path}"><title>${escapeHtml(item.label)} · ${suffix}</title></path>` : "";
}

function regionMapMembershipNames(ids) {
  const scene = state.regionMapScene;
  return [...(ids || [])].map((id) => scene?.regionsById.get(id)?.name || id).sort((left, right) => left.localeCompare(right));
}

function regionMapDetailRow(label, value) {
  if (value === undefined || value === null || value === "" || (Array.isArray(value) && !value.length)) return "";
  const display = Array.isArray(value) ? value.join(", ") : String(value);
  return `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(display)}</dd></div>`;
}

function clearRegionMapInspector() {
  state.regionMapSelectedFeature = null;
  $("regionMapInspector").hidden = true;
  if (state.regionMapScene?.groups?.inspected) state.regionMapScene.groups.inspected.innerHTML = "";
}

function renderRegionMapInspector() {
  const selected = state.regionMapSelectedFeature, scene = state.regionMapScene;
  if (!selected || !scene) { clearRegionMapInspector(); return; }
  const {type, id, feature} = selected;
  const properties = feature.properties || {};
  const region = type === "mpo" ? scene.regionsById.get(properties.regionId || id) : null;
  const azoneId = type === "azone" ? id : type === "bzone" ? String(properties.azoneId || id.slice(0, 5)) : "";
  const localityName = properties.localityName || scene.localityNames.get(azoneId) || "";
  const includedMpos = type === "bzone" ? regionMapMembershipNames(scene.bzoneMemberships.get(id)) : type === "azone" ? regionMapMembershipNames(scene.azoneMemberships.get(id)) : [];
  const current = scene.currentRegion;
  let currentStatus = "";
  let overlap;
  if (type === "bzone" && current) {
    const includedCase = (current.includedBoundaryCases || []).find((item) => String(item.geoid) === id);
    if (includedCase) { currentStatus = "Boundary inclusion"; overlap = includedCase.overlapRatio; }
    else if ((current.selectedBzones || []).includes(id)) currentStatus = "Included (substantially inside)";
    else currentStatus = "Context only";
  } else if (type === "azone" && current) {
    currentStatus = (current.azoneFips || []).includes(id) ? "Participating locality" : "Context only";
  }
  const title = type === "mpo" ? properties.name || region?.name || "MPO boundary" : type === "azone" ? localityName || `Azone ${id}` : `Bzone ${id}`;
  $("regionMapInspectorTitle").textContent = title;
  $("regionMapInspectorBody").innerHTML = `<dl class="region-map-details">
    ${regionMapDetailRow("Feature", type === "mpo" ? "MPO boundary" : type === "azone" ? "Azone / locality" : "Bzone")}
    ${regionMapDetailRow("MPO", region?.name)}
    ${regionMapDetailRow("Official MPO ID", properties.officialMpoId || region?.officialMpoId)}
    ${regionMapDetailRow("Explored MPO", type !== "mpo" ? current?.name : "")}
    ${regionMapDetailRow("Explored MPO official ID", type !== "mpo" ? current?.officialMpoId : "")}
    ${regionMapDetailRow("Locality", localityName)}
    ${regionMapDetailRow("Azone ID", azoneId)}
    ${regionMapDetailRow("Bzone ID", type === "bzone" ? id : "")}
    ${regionMapDetailRow("Included in MPOs", includedMpos)}
    ${regionMapDetailRow(current ? `Status in ${current.shortName || current.name}` : "Selected MPO status", currentStatus)}
    ${regionMapDetailRow("Boundary overlap", Number.isFinite(Number(overlap)) ? `${(Number(overlap) * 100).toFixed(1)}%` : "")}
  </dl>`;
  $("regionMapInspector").hidden = false;
  const path = regionMapPath(feature, scene.projection);
  scene.groups.inspected.innerHTML = `<path class="region-map-inspected region-map-inspected-${type}" d="${path}"></path>`;
}

function inspectRegionMapFeature(type, id, feature) {
  state.regionMapSelectedFeature = {type, id: String(id), feature};
  renderRegionMapInspector();
}

function regionMapHitFeature(point) {
  const scene = state.regionMapScene;
  if (!scene || !point) return null;
  const visibleBzones = regionMapVisibleBzoneIds();
  if (visibleBzones === null || visibleBzones.size) {
    for (const entry of scene.hitBzones) {
      if (visibleBzones !== null && !visibleBzones.has(entry.id)) continue;
      const bounds = entry.bounds;
      if (bounds && point.x >= bounds.minX && point.x <= bounds.maxX && point.y >= bounds.minY && point.y <= bounds.maxY && regionMapFeatureContains(entry.feature, point, scene.projection)) return {type: "bzone", ...entry};
    }
  }
  if (regionMapLayerVisible("azones")) {
    for (const entry of scene.hitAzones) {
      const bounds = entry.bounds;
      if (bounds && point.x >= bounds.minX && point.x <= bounds.maxX && point.y >= bounds.minY && point.y <= bounds.maxY && regionMapFeatureContains(entry.feature, point, scene.projection)) return {type: "azone", ...entry};
    }
  }
  if (regionMapLayerVisible("mpos")) {
    const entries = [...scene.hitMpos].sort((left, right) => Number(right.id === state.regionMapSelectedRegionId) - Number(left.id === state.regionMapSelectedRegionId));
    for (const entry of entries) {
      const bounds = entry.bounds;
      if (bounds && point.x >= bounds.minX && point.x <= bounds.maxX && point.y >= bounds.minY && point.y <= bounds.maxY && regionMapFeatureContains(entry.feature, point, scene.projection)) return {type: "mpo", ...entry};
    }
  }
  return null;
}

function updateRegionMapSelection({zoom = true} = {}) {
  const data = state.regionMapData, scene = state.regionMapScene;
  if (!data || !scene) return;
  const regionId = $("regionMapRegion").value;
  state.regionMapSelectedRegionId = regionId;
  const region = (data.regions || []).find((item) => item.id === regionId);
  scene.currentRegion = region || null;
  const mpoFeature = scene.mpoFeatures.get(regionId);
  const selected = region?.selectedBzones || [];
  const included = new Set(region?.includedBoundaryBzones || []);
  const ordinary = selected.filter((geoid) => !included.has(String(geoid)));
  const modelScoped = regionBuilderModelBacked();
  scene.groups.mpoFocus.innerHTML = !modelScoped && mpoFeature ? `<path class="region-map-mpo-focus" d="${regionMapPath(mpoFeature, scene.projection)}"><title>${escapeHtml(region.name)}</title></path>` : "";
  scene.groups.selected.innerHTML = modelScoped ? "" : ordinary.map((geoid) => regionMapOverlayPath(scene, geoid, "region-map-bzone-selected", "selected MPO Bzone")).join("");
  scene.groups.included.innerHTML = modelScoped ? "" : [...included].map((geoid) => regionMapOverlayPath(scene, geoid, "region-map-bzone-boundary", "included boundary case")).join("");
  scene.groups.labels.innerHTML = "";
  $("regionMapTitle").textContent = region?.name || "Virginia MPO geography";
  $("regionMapSubtitle").textContent = modelScoped && region
    ? `${selected.length.toLocaleString()} included Bzones · ${(region.azoneFips || []).length.toLocaleString()} Azones / localities`
    : region
    ? `${selected.length.toLocaleString()} included Bzones · ${(selected.length - included.size).toLocaleString()} substantially inside · ${included.size} boundary overlaps of at least 1%`
    : `${(data.summary?.mpos || 0).toLocaleString()} MPOs · ${(data.summary?.azones || 0).toLocaleString()} Azones · ${(data.summary?.bzones || 0).toLocaleString()} Bzones statewide`;
  const reviewFeatures = [mpoFeature, ...selected].map((item) => typeof item === "string" ? scene.bzoneFeatures.get(item) : item).filter(Boolean);
  scene.focusView = region ? regionMapFeaturesView(reviewFeatures, scene.projection) : scene.fullView;
  $("fitRegionMap").disabled = !region;
  if (zoom && region) setRegionMapView(scene.focusView);
  else setRegionMapView(state.regionMapView);
  applyRegionMapLayers();
  if (state.regionMapSelectedFeature) renderRegionMapInspector();
}

function renderRegionMap() {
  const canvas = $("regionMapCanvas");
  const data = state.regionMapData;
  const bounds = data && regionMapBounds([data.mpos, data.azones, data.bzones]);
  if (!bounds) { canvas.className = "region-map-canvas empty-state"; canvas.textContent = "No statewide map geometry was returned."; return; }
  const projection = regionMapProjection(bounds);
  const path = (feature, className, label) => `<path class="${className}" d="${regionMapPath(feature, projection)}"><title>${escapeHtml(label)}</title></path>`;
  const bzoneFeatures = new Map((data.bzones?.features || []).map((feature) => [String(feature.properties?.bzoneId || feature.properties?.GEOID || ""), feature]));
  const azoneFeatures = new Map((data.azones?.features || []).map((feature) => [String(feature.properties?.azoneId || feature.properties?.Azones || ""), feature]));
  const bzonePaths = new Map([...bzoneFeatures].map(([geoid, feature]) => [geoid, {path: regionMapPath(feature, projection), label: geoid || "Bzone"}]));
  const mpos = (data.mpos?.features || []).map((feature) => path(feature, "region-map-mpo", feature.properties?.name || feature.properties?.MPO_NAME || "MPO boundary")).join("");
  const azones = (data.azones?.features || []).map((feature) => path(feature, "region-map-azone", feature.properties?.localityName || feature.properties?.name || "Azone")).join("");
  const bzones = [...bzonePaths.values()].map((item) => `<path class="region-map-bzone" d="${item.path}"><title>${escapeHtml(item.label)}</title></path>`).join("");
  canvas.className = "region-map-canvas";
  canvas.innerHTML = `<svg role="img" aria-label="Virginia MPO, Azone, and Bzone geography map" viewBox="0 0 ${projection.width} ${projection.height}" data-region-map-svg><g aria-hidden="true" data-map-group="all-bzones">${bzones}</g><g aria-hidden="true" data-map-group="azones">${azones}</g><g aria-hidden="true" data-map-group="mpos">${mpos}</g><g aria-hidden="true" data-map-group="selected-bzones"></g><g aria-hidden="true" data-map-group="included-boundary"></g><g aria-hidden="true" data-map-group="mpo-focus"></g><g aria-hidden="true" data-map-group="labels"></g><g aria-hidden="true" data-map-group="id-labels"></g><g aria-hidden="true" data-map-group="inspected"></g></svg>`;
  const fullView = regionMapFullView(projection);
  state.regionMapView = fullView;
  const regionsById = new Map((data.regions || []).map((region) => [region.id, region]));
  const bzoneMemberships = new Map(), azoneMemberships = new Map();
  const addMembership = (index, key, regionId) => { if (!index.has(key)) index.set(key, new Set()); index.get(key).add(regionId); };
  (data.regions || []).forEach((region) => {
    (region.selectedBzones || []).forEach((id) => addMembership(bzoneMemberships, String(id), region.id));
    (region.azoneFips || []).forEach((id) => addMembership(azoneMemberships, String(id), region.id));
  });
  const featureCenters = new Map();
  bzoneFeatures.forEach((feature, id) => featureCenters.set(`bzone:${id}`, regionMapFeatureCenter(feature, projection)));
  azoneFeatures.forEach((feature, id) => featureCenters.set(`azone:${id}`, regionMapFeatureCenter(feature, projection)));
  const hitEntries = (features, idFor) => features.map((feature) => ({id: String(idFor(feature)), feature, bounds: regionMapFeatureBounds(feature, projection)})).filter((entry) => entry.id && entry.bounds);
  const mpoFeatures = new Map((data.mpos?.features || []).map((feature) => [String(feature.properties?.regionId || feature.properties?.officialMpoId || feature.properties?.MPO_ID || ""), feature]));
  mpoFeatures.forEach((feature, id) => featureCenters.set(`mpo:${id}`, regionMapFeatureCenter(feature, projection)));
  state.regionMapScene = {
    projection,
    bzonePaths,
    bzoneFeatures,
    azoneFeatures,
    featureCenters,
    regionsById,
    bzoneMemberships,
    azoneMemberships,
    localityNames: new Map((data.localities || []).map((item) => [String(item.azoneId), item.localityName])),
    hitBzones: hitEntries(data.bzones?.features || [], (feature) => feature.properties?.bzoneId || feature.properties?.GEOID),
    hitAzones: hitEntries(data.azones?.features || [], (feature) => feature.properties?.azoneId || feature.properties?.Azones),
    hitMpos: hitEntries(data.mpos?.features || [], (feature) => feature.properties?.regionId || feature.properties?.officialMpoId || feature.properties?.MPO_ID),
    fullView,
    focusView: fullView,
    mpoFeatures,
    groups: {
      mpoFocus: canvas.querySelector('[data-map-group="mpo-focus"]'), selected: canvas.querySelector('[data-map-group="selected-bzones"]'),
      included: canvas.querySelector('[data-map-group="included-boundary"]'), labels: canvas.querySelector('[data-map-group="labels"]'),
      idLabels: canvas.querySelector('[data-map-group="id-labels"]'), inspected: canvas.querySelector('[data-map-group="inspected"]'),
    },
  };
  clearRegionMapInspector();
  configureRegionMapControls();
  updateRegionMapSelection({zoom: false});
  $("regionMapLegend").hidden = false;
}

function renderRegionMapLoadStatus() {
  const status = $("regionMapStatus"), button = $("viewRegionMap");
  if (!status || !button) return;
  const labels = {
    idle: "",
    loading: "Preparing map…",
    ready: state.regionMapData?.cached ? "Cached locally" : "Map ready",
    failed: "Map unavailable · select Retry map",
  };
  status.textContent = labels[state.regionMapLoadState] || "";
  status.classList.toggle("error-text", state.regionMapLoadState === "failed");
  const hasRegions = Boolean((state.regionBuilderRegions?.regions || []).length);
  const loading = state.regionMapLoadState === "loading";
  const text = state.regionMapLoadState === "failed" ? "Retry map" : loading ? "View map (loading…)" : "View map";
  [button, ...document.querySelectorAll("[data-open-region-map]")].forEach((mapButton) => {
    mapButton.textContent = text;
    mapButton.disabled = !hasRegions || loading;
    mapButton.setAttribute("aria-busy", String(loading));
    mapButton.title = loading ? "Map geometry is loading." : state.regionMapLoadState === "failed" ? "Retry loading map geometry." : "Open the boundary map.";
  });
}

async function preloadRegionMapGeometry({force = false} = {}) {
  const packageId = state.regionBuilderPackageId || $("regionPackage").value;
  if (!packageId) return null;
  if (!force && state.regionMapKey === packageId && state.regionMapData) {
    state.regionMapLoadState = "ready";
    renderRegionMapLoadStatus();
    return state.regionMapData;
  }
  if (!force && state.regionMapLoadPromise) return state.regionMapLoadPromise;
  state.regionMapLoadState = "loading";
  state.regionMapLoadError = "";
  renderRegionMapLoadStatus();
  const loadPromise = request(`/api/region-builder/map/statewide?packageId=${encodeURIComponent(packageId)}`)
    .then((data) => {
      if (state.regionBuilderPackageId !== packageId) return null;
      state.regionMapData = data;
      state.regionMapKey = packageId;
      state.regionMapView = null;
      state.regionMapScene = null;
      state.regionMapLoadState = "ready";
      renderRegionMapLoadStatus();
      return data;
    })
    .catch((error) => {
      if (state.regionBuilderPackageId === packageId) {
        state.regionMapLoadState = "failed";
        state.regionMapLoadError = error.message;
        renderRegionMapLoadStatus();
      }
      throw error;
    });
  const trackedPromise = loadPromise.finally(() => {
    if (state.regionMapLoadPromise === trackedPromise) state.regionMapLoadPromise = null;
  });
  state.regionMapLoadPromise = trackedPromise;
  return trackedPromise;
}

async function openRegionMap() {
  const packageId = state.regionBuilderPackageId || $("regionPackage").value;
  const regionId = state.regionBuilderRegionId || $("regionDefinition").value;
  if (!packageId) return notify("Choose an installed regional package before opening the map.", "error");
  $("regionMapDialog").showModal();
  syncMenuContext();
  configureRegionMapControls();
  $("regionMapTitle").textContent = "Virginia MPO geography";
  $("regionMapCanvas").className = "region-map-canvas empty-state";
  $("regionMapCanvas").textContent = state.regionMapLoadState === "failed" ? "Retrying official map geometry…" : "Loading official map geometry…";
  $("regionMapLegend").hidden = true;
  try {
    const data = await preloadRegionMapGeometry({force:state.regionMapLoadState === "failed"});
    if (!data) throw new Error("The selected regional package changed while the map was loading.");
    state.regionMapSelectedRegionId = regionId || "";
    $("regionMapRegion").innerHTML = `<option value="">All MPOs</option>${(data.regions || []).map((region) => `<option value="${escapeHtml(region.id)}">${escapeHtml(region.name)}</option>`).join("")}`;
    selectedOption($("regionMapRegion"), state.regionMapSelectedRegionId);
    renderRegionMap();
  } catch (error) {
    $("regionMapCanvas").className = "region-map-canvas empty-state";
    $("regionMapCanvas").textContent = error.message;
    $("regionMapSubtitle").textContent = "Map unavailable; preview and build still work offline.";
  }
}

async function loadExploreFiles(libraryId = state.exploreLibraryId) {
  state.exploreLibraryId = libraryId;
  const explanationId = state.exploreExplanationId;
  state.exploreSelectedFile = "";
  state.exploreDetail = null;
  $("exploreFiles").className = "explore-file-list empty-state";
  $("exploreFiles").textContent = "Loading input files…";
  try {
    const payload = await request(`/api/explore/files?libraryId=${encodeURIComponent(libraryId || "")}&explanationPackageId=${encodeURIComponent(explanationId || "")}`);
    if (state.exploreLibraryId !== libraryId || state.exploreExplanationId !== explanationId) return;
    state.exploreFiles = payload.files || [];
    renderExploreExplanationNotice(payload.explanationPackage || null);
    renderExploreFiles();
  } catch (error) {
    notify(error.message, "error");
    $("exploreFiles").textContent = "Input files could not be loaded.";
  }
}

function filteredExploreFiles() {
  const query = $("exploreSearch").value.trim().toLowerCase();
  return state.exploreFiles.filter((file) => {
    if (!query) return true;
    return [file.filename, file.level, file.description, ...(file.columns || [])].join(" ").toLowerCase().includes(query);
  });
}

function renderExploreFiles() {
  const container = $("exploreFiles");
  const files = filteredExploreFiles();
  $("exploreCount").textContent = `${files.length} ${files.length === 1 ? "file" : "files"}`;
  container.className = `explore-file-list${files.length ? "" : " empty-state"}`;
  container.innerHTML = files.length ? files.map((file) => `
    <button class="explore-file ${state.exploreSelectedFile === file.filename ? "selected" : ""}" data-explore-file="${escapeHtml(file.filename)}" type="button">
      <span><strong>${escapeHtml(file.filename)}</strong><small>${escapeHtml(file.level)} · ${file.columnCount} fields</small></span>
      ${file.installed ? `<span class="pill">Installed</span>` : `<span class="pill" title="VisionEval recognizes this input, but the selected Input Library does not contain it.">Not included</span>`}
      <p>${escapeHtml(file.description)}</p>
    </button>`).join("") : "No input files match this search.";
  container.querySelectorAll("[data-explore-file]").forEach((button) => button.addEventListener("click", () => loadExploreFile(button.dataset.exploreFile)));
}

async function loadExploreFile(filename) {
  state.exploreSelectedFile = filename;
  renderExploreFiles();
  $("exploreDetail").innerHTML = `<section class="panel empty-state">Loading ${escapeHtml(filename)}…</section>`;
  try {
    const detail = await request(`/api/explore/file?libraryId=${encodeURIComponent(state.exploreLibraryId || "")}&filename=${encodeURIComponent(filename)}&explanationPackageId=${encodeURIComponent(state.exploreExplanationId || "")}`);
    if (state.exploreSelectedFile !== filename) return;
    state.exploreDetail = detail;
    renderExploreDetail();
  } catch (error) {
    if (state.exploreSelectedFile !== filename) return;
    state.exploreDetail = null;
    $("exploreDetail").innerHTML = `<section class="panel empty-state"><h3>Input details unavailable</h3><p>This input could not be loaded. Try again, or repair the workspace from Settings.</p></section>`;
    notify("This input detail could not be loaded. Try again or repair the workspace from Settings.", "error");
  }
}

function renderExploreDetail() {
  const detail = state.exploreDetail;
  if (!detail) return;
  const catalogOnly = detail.availability === "catalog_only";
  $("exploreDetail").innerHTML = `
    <section class="panel explore-overview">
      <div><p class="step">${escapeHtml(detail.level)} input</p><h3>${escapeHtml(detail.filename)}</h3><p>${escapeHtml(detail.description)}</p></div>
      <span class="stable-id" title="Stable mapping identifier">${escapeHtml(detail.id)}</span>
    </section>
    ${catalogOnly ? `<section class="notice"><strong>This file is not included in the selected Input Library.</strong><p>Install a model package containing this file to inspect its fields and values.</p></section>` : ""}
    <section class="panel">
      <div class="section-title"><div><p class="step">Fields</p><h3>Fields in this file</h3><p class="muted">Definitions and units come from VisionEval module specifications and the packaged input guide when available.</p></div></div>
      ${detail.fields.length ? `<div class="explore-fields">${detail.fields.map((field) => `
        <article class="explore-field ${field.unitWarning ? "metadata-warning" : ""}"><div><strong>${escapeHtml(field.display)}</strong>${field.display !== field.name ? `<code>${escapeHtml(field.name)}</code>` : ""}</div><p class="${field.descriptionAvailable === false ? "missing-description" : ""}">${escapeHtml(field.description)}</p><small>${field.identifier ? "Identifier · preserved as text" : [field.type, field.units].filter(Boolean).map(escapeHtml).join(" · ") || "Unit not verified"}</small><small class="metadata-source ${field.sourceAvailable === false ? "missing-source" : ""}">Source: ${escapeHtml(field.source || "Not recorded")}</small>${field.unitWarning ? `<p class="unit-warning"><strong>Unit review needed:</strong> ${escapeHtml(field.unitWarning)}</p>` : ""}</article>`).join("")}</div>
    </section>` : `<div class="explore-fields"><p class="muted">Install a model package containing this file to inspect its actual columns and field definitions.</p></div></section>`}
    ${detail.explanationHtml ? `<details class="panel explanation-panel" open><summary>Full input-file explanation</summary><div class="explanation-content">${detail.explanationHtml}</div></details>` : `<section class="panel"><h3>Input explanation</h3><p class="muted">${catalogOnly ? "No preloaded explanation is available for this input." : "A long-form guide has not been written for this file yet. The field descriptions above remain available."}</p></section>`}
    <section class="panel mapping-preview">
      <div><p class="step">Dependency network</p><h3>What could this input affect?</h3><p>Open the selected model’s declared execution network focused on this input file.</p></div>
      <button id="viewFileDependencies" type="button">View Dependencies</button>
    </section>`;
  $("viewFileDependencies").addEventListener("click", async () => {
    switchExploreSubpage("exploreDependencyPage");
    if (state.dependencyTemplateId) { $("dependencyTemplate").value = state.dependencyTemplateId; await loadDependencyGraph(state.dependencyTemplateId); focusDependencyNode(`file:${detail.filename}`); }
  });
}

function switchExploreSubpage(pageId, resetScroll = true) {
  state.activeExploreSubpage = pageId;
  document.querySelectorAll(".explore-subpage").forEach((page) => page.classList.toggle("active", page.id === pageId));
  document.querySelectorAll("[data-explore-subpage]").forEach((button) => button.classList.toggle("active", button.dataset.exploreSubpage === pageId));
  if (resetScroll) window.scrollTo({left:0, top:0});
}

function dependencyKind(node) {
  if (node.kind === "file") return "file";
  if (node.kind === "input") return "input";
  if (node.kind === "module") return "module";
  if (node.storedOutput) return "output";
  if (node.kind === "variable" || node.kind === "source") return "intermediary";
  return node.kind;
}

async function loadDependencyGraph(templateId = $("dependencyTemplate").value, focusId = "", options = {}) {
  if (!templateId) return renderDependencyGraph();
  state.dependencyTemplateId = templateId;
  if (!focusId) { state.dependencyOriginId = ""; state.dependencyScope = ""; state.dependencyView = ""; state.dependencyNavigation = []; }
  const scope = options.scope || "", originId = options.originId || "", view = options.view || "";
  $("dependencyGraph").className = "dependency-graph empty-state";
  $("dependencyGraph").textContent = "Building the model dependency graph…";
  try {
    const mode = templateId === "__builtin_module_catalog__" ? "catalog" : "execution";
    const graph = await request(`/api/dependencies?templateId=${encodeURIComponent(templateId)}&mode=${mode}${focusId ? `&focusId=${encodeURIComponent(focusId)}` : ""}${scope ? `&scope=${encodeURIComponent(scope)}` : ""}${originId ? `&originId=${encodeURIComponent(originId)}` : ""}${view ? `&view=${encodeURIComponent(view)}` : ""}`);
    state.dependencyGraph = graph;
    state.dependencyOriginId = graph.focusView?.originId || "";
    state.dependencyScope = graph.focusView?.scope || "";
    state.dependencyView = graph.focusView?.view || "";
    if (!focusId) { state.dependencyFullGraph = graph; renderDependencyFocusItems(); }
    renderDependencyGraph();
  } catch (error) { notify(error.message, "error"); $("dependencyGraph").textContent = "The dependency graph could not be loaded."; }
}

function renderDependencyFocusItems(preferred = "") {
  const kind = $("dependencyFocusKind").value, select = $("dependencyFocusItem"), graph = state.dependencyFullGraph;
  if (!graph || kind === "all") { select.disabled = true; select.innerHTML = `<option value="">Full execution path</option>`; return; }
  const nodes = graph.nodes.filter((node) => dependencyKind(node) === kind).sort((a,b) => `${a.file || a.table || ""}/${a.label}`.localeCompare(`${b.file || b.table || ""}/${b.label}`));
  select.disabled = !nodes.length;
  select.innerHTML = nodes.map((node) => `<option value="${escapeHtml(node.id)}">${escapeHtml(node.kind === "input" ? `${node.file} · ${node.label}` : node.kind === "module" ? `${node.order}. ${node.label} — ${node.package}` : node.kind === "file" ? node.label : `${node.table || "Datastore"} / ${node.label}`)}</option>`).join("") || `<option value="">No matching nodes</option>`;
  selectedOption(select, preferred);
}

async function focusDependencyNode(nodeId, options = {}) {
  const node = state.dependencyFullGraph?.nodes.find((item) => item.id === nodeId); if (!node) return;
  $("dependencyFocusKind").value = dependencyKind(node); renderDependencyFocusItems(nodeId); $("dependencyFocusItem").value = nodeId;
  const current = state.dependencyGraph?.focusId;
  if (options.fromCanvas && current && current !== nodeId) {
    state.dependencyNavigation.push({id:current, scope:state.dependencyScope, originId:state.dependencyOriginId, view:state.dependencyView});
  } else if (!options.keepNavigation) state.dependencyNavigation = [];
  let originId = options.originId || "", scope = options.scope || "", view = options.view || "";
  if (node.kind === "module" && options.fromCanvas) {
    const currentNode = state.dependencyFullGraph?.nodes.find((item) => item.id === current);
    if (["file", "input"].includes(currentNode?.kind)) { originId = currentNode.id; scope = "path"; }
    else if (state.dependencyGraph?.focusView?.originId) {
      originId = state.dependencyGraph.focusView.originId;
      scope = state.dependencyGraph.focusView.scope || "path";
    }
  }
  if (node.kind === "module" && !scope) scope = "context";
  await loadDependencyGraph(state.dependencyTemplateId, nodeId, {scope, originId, view});
}

function renderDependencyFocusContext() {
  const graph = state.dependencyGraph, container = $("dependencyFocusContext"), breadcrumb = $("dependencyBreadcrumb"), toggle = $("dependencyScopeToggle"), valueToggle = $("dependencyValueToggle");
  const focus = state.dependencyFullGraph?.nodes.find((node) => node.id === graph?.focusId);
  const origin = state.dependencyFullGraph?.nodes.find((node) => node.id === graph?.focusView?.originId);
  if (!graph?.focusId || !focus) { container.hidden = true; breadcrumb.innerHTML = ""; toggle.hidden = true; valueToggle.hidden = true; return; }
  container.hidden = false;
  const trail = [...state.dependencyNavigation];
  if (!trail.length && origin && origin.id !== focus.id) trail.push({id:origin.id});
  breadcrumb.innerHTML = trail.map((entry,index) => { const item=state.dependencyFullGraph?.nodes.find(node=>node.id===entry.id); return item ? `<button type="button" data-dependency-crumb="${index}">${escapeHtml(item.kind === "input" ? `${item.file} · ${item.label}` : item.label)}</button><span aria-hidden="true">›</span>` : ""; }).join("") + `<strong>${escapeHtml(focus.label)}</strong>`;
  const canToggle = focus.kind === "module" && Boolean(origin);
  toggle.hidden = !canToggle;
  toggle.querySelectorAll("[data-dependency-scope]").forEach((button) => {
    const selected = button.dataset.dependencyScope === graph.focusView?.scope;
    button.setAttribute("aria-pressed", String(selected));
    button.onclick = () => loadDependencyGraph(state.dependencyTemplateId, focus.id, {scope:button.dataset.dependencyScope, originId:origin?.id || ""});
  });
  const valueFocus = ["variable", "source"].includes(focus.kind);
  valueToggle.hidden = !valueFocus;
  valueToggle.querySelectorAll("[data-dependency-view]").forEach(button => {
    const selected = button.dataset.dependencyView === graph.focusView?.view;
    button.setAttribute("aria-pressed", String(selected));
    button.disabled = button.dataset.dependencyView === "production" && graph.focusView?.navigation?.canShowProduction === false;
    button.onclick = () => loadDependencyGraph(state.dependencyTemplateId, focus.id, {view:button.dataset.dependencyView});
  });
  breadcrumb.querySelectorAll("[data-dependency-crumb]").forEach(button => button.onclick = () => {
    const index=Number(button.dataset.dependencyCrumb), entry=trail[index]; state.dependencyNavigation=trail.slice(0,index);
    focusDependencyNode(entry.id,{scope:entry.scope,originId:entry.originId,view:entry.view,keepNavigation:true});
  });
}

function dependencyNodeDetail(node) {
  if (node.kind === "module" && node.catalogOnly) return `${node.package} - catalog declaration`;
  let role = {"file-input":"File column","written-value":"Written by selected module","direct-effect-value":"Directly written by a module using selection"}[node.viewRole] || "";
  if (node.viewRole === "prior-value") role = node.upstreamSource?.type === "module"
    ? `From ${node.upstreamSource.order}. ${node.upstreamSource.label}`
    : "Loaded earlier — source not declared";
  if (node.viewRole === "selected-value") role="Selected value";
  const moduleRole={"producer-module":"Producing module","consumer-module":"Uses selected value","module":"Selected module"}[node.viewRole]||"";
  return node.kind === "module" ? [`${node.order}. ${node.package}${node.supported ? "" : " · unresolved"}`,moduleRole].filter(Boolean).join(" · ") : node.kind === "file" ? (node.active ? "Used by this model" : "Not used by this execution path") : [node.table, node.units, role || (node.intermediary && node.storedOutput ? "Intermediary + stored" : "")].filter(Boolean).join(" · ");
}
function dependencyViewportTransform() {
  const view = state.dependencyViewport, group = $("dependencyGraph").querySelector(".dependency-canvas-content");
  if (group) group.setAttribute("transform", `translate(${view.x} ${view.y}) scale(${view.scale})`);
  $("dependencyGraph").classList.toggle("semantic-compact", view.scale < .48);
  renderDependencyMinimap();
}
function fitDependencyGraph() {
  const layout = state.dependencyDisplayLayout, container = $("dependencyGraph"); if (!layout || !container.clientWidth) return;
  const bounds = layout.bounds, width = Math.max(100, container.clientWidth - 34), height = Math.max(100, container.clientHeight - 34);
  const scale = Math.max(.08, Math.min(1, width / bounds.width, height / bounds.height));
  state.dependencyViewport = {...state.dependencyViewport, scale, x:(container.clientWidth-bounds.width*scale)/2, y:(container.clientHeight-bounds.height*scale)/2, fitPending:false};
  dependencyViewportTransform();
}
function zoomDependencyGraph(factor, clientX, clientY) {
  const container = $("dependencyGraph"), rect = container.getBoundingClientRect(), view = state.dependencyViewport;
  const px = (clientX ?? rect.left + rect.width/2) - rect.left, py = (clientY ?? rect.top + rect.height/2) - rect.top;
  const scale = Math.max(.08, Math.min(3, view.scale * factor)), gx = (px-view.x)/view.scale, gy = (py-view.y)/view.scale;
  view.x = px-gx*scale; view.y = py-gy*scale; view.scale = scale; view.fitPending=false; dependencyViewportTransform();
}
function centerDependencyNode(nodeId) {
  const position=state.dependencyDisplayLayout?.nodes?.[nodeId], container=$("dependencyGraph"); if(!position)return;
  const view=state.dependencyViewport; view.x=container.clientWidth/2-(position.x+position.width/2)*view.scale; view.y=container.clientHeight/2-(position.y+position.height/2)*view.scale; view.highlighted=nodeId; dependencyViewportTransform();
  container.querySelectorAll(".dependency-svg-node").forEach(node=>node.classList.toggle("search-match",node.dataset.dependencyNode===nodeId));
}
function renderDependencyMinimap() {
  const layout=state.dependencyDisplayLayout, map=$("dependencyGraph").querySelector(".dependency-minimap"), container=$("dependencyGraph"); if(!layout||!map)return;
  const bounds=layout.bounds, sx=150/bounds.width, sy=96/bounds.height, scale=Math.min(sx,sy), view=state.dependencyViewport;
  const x=Math.max(0,-view.x/view.scale), y=Math.max(0,-view.y/view.scale), w=Math.min(bounds.width,container.clientWidth/view.scale), h=Math.min(bounds.height,container.clientHeight/view.scale);
  map.setAttribute("viewBox",`0 0 ${bounds.width} ${bounds.height}`);
  map.innerHTML=`<rect class="minimap-bg" width="${bounds.width}" height="${bounds.height}"/>${Object.values(layout.nodes).map(pos=>`<rect class="minimap-node" x="${pos.x}" y="${pos.y}" width="${pos.width}" height="${pos.height}"/>`).join("")}<rect class="minimap-window" x="${x}" y="${y}" width="${w}" height="${h}"/>`;
}
function bindDependencyCanvas() {
  const container=$("dependencyGraph"), svg=container.querySelector(".dependency-canvas"); if(!svg)return;
  svg.addEventListener("pointerdown",event=>{if(event.target.closest(".dependency-svg-node"))return;svg.setPointerCapture(event.pointerId);state.dependencyViewport.drag={x:event.clientX,y:event.clientY,originX:state.dependencyViewport.x,originY:state.dependencyViewport.y};container.classList.add("panning")});
  svg.addEventListener("pointermove",event=>{const drag=state.dependencyViewport.drag;if(!drag)return;state.dependencyViewport.x=drag.originX+event.clientX-drag.x;state.dependencyViewport.y=drag.originY+event.clientY-drag.y;dependencyViewportTransform()});
  const stop=()=>{state.dependencyViewport.drag=null;container.classList.remove("panning")}; svg.addEventListener("pointerup",stop);svg.addEventListener("pointercancel",stop);
  svg.addEventListener("wheel",event=>{event.preventDefault();zoomDependencyGraph(Math.exp(-event.deltaY*.0015),event.clientX,event.clientY)},{passive:false});
  const connected=new Map(); state.dependencyGraph.edges.forEach(edge=>{(connected.get(edge.from)||connected.set(edge.from,new Set()).get(edge.from)).add(edge.to);(connected.get(edge.to)||connected.set(edge.to,new Set()).get(edge.to)).add(edge.from)});
  container.querySelectorAll(".dependency-svg-node").forEach(node=>{
    const highlight=active=>{const ids=new Set([node.dataset.dependencyNode,...(connected.get(node.dataset.dependencyNode)||[])]);container.querySelectorAll(".dependency-svg-node").forEach(item=>item.classList.toggle("connected",active&&ids.has(item.dataset.dependencyNode)));container.classList.toggle("has-highlight",active)};
    node.addEventListener("mouseenter",()=>highlight(true));node.addEventListener("mouseleave",()=>highlight(false));node.addEventListener("focus",()=>highlight(true));node.addEventListener("blur",()=>highlight(false));
    node.addEventListener("click",()=>focusDependencyNode(node.dataset.dependencyNode,{fromCanvas:true}));node.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();focusDependencyNode(node.dataset.dependencyNode,{fromCanvas:true})}});
  });
}

function renderDependencyGraph() {
  const graph = state.dependencyGraph, container = $("dependencyGraph");
  if (!graph) { container.className = "dependency-graph empty-state"; container.textContent = "Create region assets in Develop to build a model dependency graph."; $("dependencyMetrics").innerHTML = ""; $("dependencyFocusContext").hidden = true; return; }
  const focusTitle = !graph.focusId ? (graph.graphMode === "catalog" ? "declaration overview" : "execution overview")
    : graph.focusView?.kind === "value" ? (graph.focusView.view === "consumers" ? "where used" : "how produced")
    : graph.focusView?.kind === "module" ? (graph.focusView.scope === "context" ? "full module context" : "selected path")
    : "direct possible effects";
  $("dependencyTitle").textContent = `${graph.template.name} · ${focusTitle}`;
  $("dependencySummary").textContent = graph.notice;
  const focusMetrics = graph.focusView?.metrics;
  const metrics = focusMetrics
    ? focusMetrics.map(item=>[item.label,item.value])
    : [["Input files",graph.counts.files],[graph.executionOrderAvailable ? "Executed modules" : "Catalog modules",graph.counts.modules],["Intermediaries",graph.counts.intermediaries],["Stored outputs",graph.counts.outputs]];
  $("dependencyMetrics").innerHTML = metrics.map(([label,value]) => `<div class="metric"><small>${label}</small><strong>${Number(value || 0).toLocaleString()}</strong></div>`).join("");
  renderDependencyFocusContext();
  container.className = "dependency-graph dependency-canvas-shell";
  const fullOverview=!graph.focusId;
  let displayLayout=graph.layout;
  if(fullOverview){
    const moduleNodes=graph.nodes.filter(node=>node.kind==="module").sort((a,b)=>(a.order||0)-(b.order||0));
    const columns=4,nodeWidth=270,nodeHeight=54,xGap=32,yGap=24;
    const overviewNodes={};
    moduleNodes.forEach((node,index)=>{const column=index%columns,row=Math.floor(index/columns);overviewNodes[node.id]={x:40+column*(nodeWidth+xGap),y:76+row*(nodeHeight+yGap),width:nodeWidth,height:nodeHeight,lane:"module",orderAnchor:node.order||0}});
    displayLayout={version:graph.layout?.version||1,nodes:overviewNodes,lanes:[{id:"module",label:"Execution sequence — select a module to inspect its inputs and outputs",x:40,width:nodeWidth}],bounds:{x:0,y:0,width:40+columns*(nodeWidth+xGap),height:120+Math.ceil(moduleNodes.length/columns)*(nodeHeight+yGap)}};
  }
  if (fullOverview && !graph.executionOrderAvailable && displayLayout?.lanes?.[0]) {
    displayLayout.lanes[0].label = "Module catalog - declarations are not model execution order";
  }
  state.dependencyDisplayLayout=displayLayout;
  const positions=displayLayout?.nodes||{}, byId=new Map(graph.nodes.map(node=>[node.id,node]));
  const edgeSvg=graph.edges.map(edge=>{const a=positions[edge.from],b=positions[edge.to];if(!a||!b)return"";const x1=a.x+a.width,y1=a.y+a.height/2,x2=b.x,y2=b.y+b.height/2,mid=(x1+x2)/2;return`<path data-from="${escapeHtml(edge.from)}" data-to="${escapeHtml(edge.to)}" d="M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}"/>`}).join("");
  const nodesSvg=Object.entries(positions).map(([id,pos])=>{const node=byId.get(id),detail=dependencyNodeDetail(node),label=String(node.label||"");return`<g class="dependency-svg-node ${pos.lane} ${node.supported===false||node.active===false?"unresolved":""}" data-dependency-node="${escapeHtml(id)}" role="button" tabindex="0" aria-label="${escapeHtml(`${label}. ${detail}`)}" transform="translate(${pos.x} ${pos.y})"><rect width="${pos.width}" height="${pos.height}" rx="8"/><rect class="node-accent" width="5" height="${pos.height}" rx="3"/><text class="node-label" x="13" y="22">${escapeHtml(label.length>40?`${label.slice(0,39)}…`:label)}</text><text class="node-detail" x="13" y="41">${escapeHtml(detail.length>54?`${detail.slice(0,53)}…`:detail)}</text></g>`}).join("");
  const laneLabels=(displayLayout?.lanes||[]).map(lane=>`<text class="dependency-lane-label" x="${lane.x}" y="55">${escapeHtml(lane.label)}</text>`).join("");
  const groupLabels=(displayLayout?.groups||[]).map(group=>`<text class="dependency-group-label" x="${group.x}" y="${group.y}">${escapeHtml(group.label)}</text>`).join("");
  const focusHelp = fullOverview ? "Execution overview · Select a module or search for any node"
    : graph.focusView?.kind === "value" ? (graph.focusView.view === "consumers" ? "Where used · Direct consumers only" : "How produced · Select an earlier value to continue upstream")
    : graph.focusView?.kind === "module" ? (graph.focusView.scope === "path" ? "Selected path · Expand to full module context when needed" : "Full module context · Inputs and outputs grouped by role")
    : "Direct possible effects · Select a module or value to continue";
  container.innerHTML=`<svg class="dependency-canvas" aria-label="Interactive dependency graph"><g class="dependency-canvas-content">${laneLabels}${groupLabels}<g class="dependency-edge-layer">${edgeSvg}</g><g>${nodesSvg}</g></g></svg><svg class="dependency-minimap" aria-hidden="true"></svg><div class="dependency-canvas-help">${focusHelp} · Drag to pan · Scroll or pinch to zoom</div>`;
  state.dependencyViewport={scale:1,x:0,y:0,drag:null,fitPending:true,highlighted:""};bindDependencyCanvas();requestAnimationFrame(fitDependencyGraph);
  $("dependencyWarnings").innerHTML = graph.unknownModules?.length ? `<div class="dependency-warning"><strong>Unresolved custom modules:</strong> ${graph.unknownModules.map(escapeHtml).join(", ")}. They remain visible but no relationships were inferred.</div>` : "";
}

async function saveDependencyExport(format) {
  const graph = state.dependencyGraph;
  if (!state.dependencyTemplateId || !graph) return notify("Load a dependency graph before exporting.", "error");
  const button = $(`dependencyExport${format.charAt(0).toUpperCase()}${format.slice(1)}`);
  setBusy(button, true, "Exporting…");
  try {
    const saved = await window.__TAURI_INTERNALS__.invoke("save_dependency_export", {
      format,
      templateId: state.dependencyTemplateId,
      focusId: graph.focusId || "",
      scope: graph.focusView?.scope || "",
      originId: graph.focusView?.originId || "",
      view: graph.focusView?.view || "",
    });
    if (saved) notify(`Export saved to ${saved}.`, "success");
  } catch (error) {
    notify(error.message || String(error), "error");
  } finally {
    setBusy(button, false);
  }
}

function renderRuntime() {
  const {runtime, profile, native, verified} = runtimeSetupSnapshot();
  const releaseCheck = runtime.releaseCheck || {};
  const dot = $("runtimeDot");
  dot.className = `dot ${runtime.running ? "ok" : "bad"}`;
  $("runtimeSummary").textContent = native ? (verified ? "Native VisionEval ready" : "VE_Runtime setup required") : !runtime.installed ? "Docker Desktop is not installed" : !runtime.running ? "Docker Desktop is not running" : verified ? "VisionEval runtime ready" : "Runtime setup required";
  $("runtimeCard").innerHTML = (native ? [
    ["Version", profile?.runtimeVersion || "Not verified"],
    ["VE_RUNTIME", runtime.veRuntime || "Not found"],
    ["VE_HOME", runtime.veHome || runtime.image || "Not found"],
    ["Rscript", runtime.executable || "Not found"],
    ["Run mode", "Queued / one at a time"],
  ] : [
    ["Docker", runtime.running ? "Running" : runtime.installed ? "Stopped" : "Not installed"],
    ["Runtime", verified ? "Ready" : runtime.imagePresent ? "Needs verification" : "Image not installed"],
    ["Version", runtime.imagePresent ? (runtime.runtimeVersion || runtime.imageReleaseTag || "VisionEval runtime") : "—"],
  ]).map(([label, value]) => `<div class="runtime-fact"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`).join("");
  $("runtimeHelp").textContent = native ? (runtime.error || (!runtime.executable || !runtime.imagePresent ? "Choose VE_RUNTIME first, review the detected VE_HOME and Rscript paths, then verify them." : !verified ? "Verify once. Workbench will start this VisionEval installation and confirm its registered modules without comparing hashes or contacting GitHub." : "The native VisionEval runtime is ready. Runs are queued and Workbench owns their prepared models, logs, and results.")) : runtime.error || (!runtime.installed
    ? "Install Docker Desktop. Workbench can start it after installation."
    : !runtime.running
      ? "Start Docker Desktop here, then Workbench will wait for the engine and verify the pinned runtime."
      : !runtime.imagePresent
        ? "The compatible VisionEval runtime image is not installed. Select Install runtime to download and verify it."
        : !runtime.provenanceMatches ? "This image does not carry the required VisionEval compatibility identity. Replace it before verification."
        : !verified ? "Verify the VisionEval runtime once. Workbench will save its immutable digest for later launches."
        : releaseCheck.status === "update_available" ? `${releaseCheck.message} The verified runtime remains available; Workbench will never update it automatically.`
        : "Docker and the verified VisionEval runtime are ready. Containers are created temporarily for each run.");
  $("startDockerDesktop").hidden = native || !runtime.installed || runtime.running;
  $("verifyRuntime").disabled = native ? !(runtime.executable && runtime.imagePresent) : !runtime.running || !runtime.imagePresent;
  $("openRunDialog").disabled = !verified || !runtime.running || !runtime.imagePresent;
  if (releaseCheck.status === "update_available" && releaseCheck.latestTag) {
    const noticeKey = "visioneval-workbench-release-notice";
    try {
      if (localStorage.getItem(noticeKey) !== releaseCheck.latestTag) {
        localStorage.setItem(noticeKey, releaseCheck.latestTag);
        notify(`${releaseCheck.latestTag} is available. Your verified ${releaseCheck.currentTag || "VisionEval"} runtime will keep working.`, "success");
      }
    } catch (_) { /* A blocked localStorage must never affect runtime use. */ }
  }
  renderRuntimeSetupControls();
}

async function startDockerAndVerify(button) {
  if (!window.__TAURI_INTERNALS__?.invoke) return notify("Start Docker Desktop from the desktop application.", "error");
  setBusy(button, true, "Starting…");
  try {
    await window.__TAURI_INTERNALS__.invoke("start_docker_desktop");
    notify("Starting Docker Desktop. Workbench will reconnect when its engine is ready.");
    for (let attempt = 0; attempt < 48; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 2500));
      await refreshState({quiet:true});
      if (!state.data?.runtime?.running) continue;
      notify("Docker Desktop is ready.", "success");
      if (state.data.runtime.imagePresent) {
        await verifyAndSaveRuntime();
        await refreshState({quiet:true});
        state.runtimeSetupPhase = "idle";
        state.runtimeSetupMessage = "";
        renderRuntime();
        notify("Official VisionEval VE-40-RC6 runtime verified.", "success");
      } else {
        state.runtimeSetupPhase = "failed";
        state.runtimeSetupMessage = "Docker is ready, but the pinned VE-40-RC6 image still needs to be installed.";
        renderRuntimeSetupControls();
        notify("Docker is ready, but the pinned VE-40-RC6 image still needs to be installed.", "error");
      }
      return;
    }
    throw new Error("Docker Desktop did not become ready within two minutes.");
  } catch (error) {
    state.runtimeSetupPhase = "failed";
    state.runtimeSetupMessage = error.message || String(error);
    renderRuntimeSetupControls();
    notify(error.message || String(error), "error");
  } finally {
    setBusy(button, false);
    renderRuntimeSetupControls();
  }
}

async function installAndSaveRuntime(button, statusElement = null) {
  if (!window.__TAURI_INTERNALS__?.invoke) return notify("Runtime installation is available in the macOS desktop application.", "error");
  const runtime = state.data?.runtime || {};
  if (!runtime.installed) {
    const message = "Docker Desktop is required before Workbench can install the VisionEval runtime.";
    state.runtimeSetupPhase = "failed";
    state.runtimeSetupMessage = message;
    renderRuntimeSetupControls();
    return notify(message, "error");
  }
  setBusy(button, true, "Installing…");
  state.runtimeSetupPhase = "installing";
  state.runtimeSetupMessage = runtime.running ? "Preparing the pinned runtime download…" : "Starting Docker Desktop…";
  renderRuntimeSetupControls();
  try {
    if (!runtime.running) {
      await window.__TAURI_INTERNALS__.invoke("start_docker_desktop");
      for (let attempt = 0; attempt < 48; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 2500));
        await refreshState({quiet:true});
        if (state.data?.runtime?.running) break;
      }
      if (!state.data?.runtime?.running) throw new Error("Docker Desktop did not become ready within two minutes.");
    }
    state.runtimeSetupMessage = "Downloading and verifying the pinned runtime… This can take several minutes the first time.";
    renderRuntimeSetupControls();
    const operation = await post("/api/runtime/install/start", {});
    const result = await waitForRuntimeInstallation(operation.id);
    const prior = (state.desktop?.runtimeProfiles || []).find((item) => item.id === state.desktop?.activeRuntimeProfileId);
    await window.__TAURI_INTERNALS__.invoke("save_runtime_profile", {profile:{
      id:prior?.adapter==="docker"?prior.id:"", name:"Apple Silicon Docker", adapter:"docker", platform:result.platform || "darwin", architecture:result.architecture || "arm64",
      imageReference:result.image, imageDigest:result.digest, runtimeVersion:result.runtimeVersion || "Compatible VisionEval runtime", verified:true,
      verifiedAt:result.verifiedAt || new Date().toISOString(), verificationMessage:"The pinned image digest, VisionEval provenance, doctor, and compatibility checks passed.", remoteStatus:result.source || "ghcr",
    }});
    state.desktop = await window.__TAURI_INTERNALS__.invoke("desktop_state");
    await refreshState({quiet:true});
    state.runtimeSetupPhase = "idle";
    state.runtimeSetupMessage = "";
    renderRuntime();
    notify("VisionEval runtime installed, verified, and connected.", "success");
    nativeNotification("VisionEval runtime ready", "The pinned runtime was installed, verified, and connected.", {outcome:"runtime_ready", force:false});
    return result;
  } catch (error) {
    const rawMessage = error.message || String(error);
    const message = rawMessage.includes("docker-credential-desktop")
      ? "Docker could not find Docker Desktop's credential helper. Quit and reopen Docker Desktop, then try Install runtime again."
      : rawMessage;
    state.runtimeSetupPhase = "failed";
    state.runtimeSetupMessage = message;
    renderRuntimeSetupControls();
    notify(message, "error");
    throw error;
  } finally {
    setBusy(button, false);
    renderRuntimeSetupControls();
  }
}

async function verifyRuntimeFromSetup(button) {
  setBusy(button, true, "Verifying…");
  state.runtimeSetupPhase = "verifying";
  state.runtimeSetupMessage = "Verifying the pinned runtime and saved compatibility profile…";
  renderRuntimeSetupControls();
  try {
    const result = await verifyAndSaveRuntime();
    await refreshState({quiet:true});
    state.runtimeSetupPhase = "idle";
    state.runtimeSetupMessage = "";
    renderRuntime();
    notify("VisionEval runtime verified and connected.", "success");
    nativeNotification("VisionEval runtime ready", "The pinned runtime was verified and connected.", {outcome:"runtime_ready", force:false});
    return result;
  } catch (error) {
    const message = error.message || String(error);
    state.runtimeSetupPhase = "failed";
    state.runtimeSetupMessage = message;
    renderRuntimeSetupControls();
    notify(message, "error");
    throw error;
  } finally {
    setBusy(button, false);
    renderRuntimeSetupControls();
  }
}

function renderSetup() {
  const libraries = state.data?.inputLibraries || [];
  const templates = state.data?.templates || [];
  const libraryValue = $("librarySelect").value;
  $("librarySelect").innerHTML = libraries.length ? libraries.map((item) => `<option value="${escapeHtml(item.id)}" ${item.pairingStatus === "paired" ? "" : "disabled"}>${escapeHtml(item.name)} · ${item.fileCount} CSVs${item.pairingStatus === "paired" ? "" : " · package repair required"}</option>`).join("") : `<option value="">Install a model or regional package first</option>`;
  let pending = state.pendingProjectSetup;
  if (pending) {
    const pendingLibrary = libraries.find((item) => item.id === pending.inputLibraryId);
    const pendingTemplate = templates.find((item) => item.id === pending.templateId);
    if (!pendingLibrary || !pendingTemplate) {
      state.pendingProjectSetup = null;
      pending = null;
    }
  }
  const preferredLibrary = pending?.inputLibraryId || libraryValue || state.data?.workspaceSettings?.defaultInputLibraryId || "";
  const eligibleLibraries = libraries.filter((item) => item.pairingStatus === "paired");
  selectedOption($("librarySelect"), eligibleLibraries.some((item) => item.id === preferredLibrary) ? preferredLibrary : eligibleLibraries[0]?.id || "");
  const selectedLibrary=libraries.find((item)=>item.id===$("librarySelect").value);
  const selectedTemplate=templates.find((item)=>item.id===selectedLibrary?.pairedTemplateId);
  const baselines=(state.data?.catalog||[]).filter((item)=>item.role==="baseline"&&item.verification==="verified"&&item.templateFingerprint===selectedTemplate?.fingerprint&&item.inputLibraryFingerprint===selectedLibrary?.fingerprint).sort((a,b)=>String(b.completedAt||"").localeCompare(String(a.completedAt||"")));
  $("existingBaseline").innerHTML=baselines.length?baselines.map((item)=>`<option value="${escapeHtml(item.id)}">${escapeHtml(item.displayLabel || item.label)}</option>`).join(""):`<option value="">No compatible completed baseline</option>`;
  const strategy=baselines.length?"existing":"fresh";
  const strategyControl=document.querySelector(`input[name="baselineStrategy"][value="${strategy}"]`);if(strategyControl)strategyControl.checked=true;
  $("existingBaselineStrategy").disabled=!baselines.length;
  $("existingBaselineChoice").classList.toggle("choice-unavailable",!baselines.length);
  $("existingBaselineHelp").textContent=baselines.length
    ? "Choose a verified completed baseline produced by this exact Model package."
    : "Run and successfully complete a baseline for this Model package before this option becomes available.";
  $("existingBaseline").disabled=!baselines.length||strategy!=="existing";
  if (pending?.projectName && !$("projectName").value) $("projectName").value = pending.projectName;
  const restored = !pending || ($("librarySelect").value === pending.inputLibraryId && selectedLibrary?.pairedTemplateId === pending.templateId);
  const identity = $("projectAssetIdentity");
  identity.hidden = !pending;
  const clearPendingAction = `<div class="notice-actions"><button id="clearBuiltRegionSelection" type="button" class="secondary">Clear built region selection</button></div>`;
  if (pending && !restored) identity.innerHTML = `<strong>Built region package is inconsistent</strong><p>The generated Input Library and Model package are still installed, but their pairing no longer matches. Clear this selection to use another Model package, or rebuild the region assets.</p>${clearPendingAction}`;
  else if (pending) {
    const packageName = pending.inputLibraryName || pending.templateName || pending.regionName;
    const details = packageName !== pending.regionName ? `<p><b>Model package:</b> ${escapeHtml(packageName)}</p>` : "";
    identity.innerHTML = `<strong>Built region selected: ${escapeHtml(pending.regionName)}</strong>${details}${clearPendingAction}`;
  }
  const pairingError = selectedLibrary && selectedLibrary.pairingStatus !== "paired"
    ? selectedLibrary.pairingError
    : (!eligibleLibraries.length && libraries.length ? libraries[0].pairingError : "");
  if (pairingError) {
    identity.hidden = false;
    identity.innerHTML = `<strong>Asset package repair required</strong><p>${escapeHtml(pairingError)}</p>${pending ? clearPendingAction : ""}`;
  }
  $("clearBuiltRegionSelection")?.addEventListener("click", () => {
    state.pendingProjectSetup = null;
    renderSetup();
    $("librarySelect").focus();
    notify("Built region selection cleared. Choose any installed Model package.", "success");
  });
  $("createProjectButton").disabled = !selectedLibrary || !selectedTemplate || !restored;
  const hypercube = document.querySelector('input[name="projectType"]:checked')?.value === "hypercube";
  $("projectTypeGuidance").textContent = hypercube
    ? "The untouched baseline is created with the project. You will configure its single scenario matrix next."
    : "The untouched baseline is created with the project. Add scenarios from the Editor sidebar.";
}

function renderArchivedProjects() {
  const projects = state.data?.archivedProjects || [];
  $("archiveCount").textContent = projects.length;
  $("archiveList").classList.toggle("empty-state", !projects.length);
  $("archiveList").innerHTML = projects.length ? projects.map((project) => `
    <article class="item-card project-card archived-project-card">
      <div class="project-card-open"><header><strong>${escapeHtml(project.name)}</strong><span class="pill">${project.daysRemaining} days remaining</span></header>
      <small>${escapeHtml(projectPackageName(project))} · ${project.variations?.length || 0} scenarios</small></div>
      <div class="project-card-actions"><button class="secondary" type="button" data-restore-project="${escapeHtml(project.id)}">Restore</button><button class="danger" type="button" data-purge-project="${escapeHtml(project.id)}">Delete now</button></div>
    </article>`).join("") : "No archived projects.";
  document.querySelectorAll("[data-restore-project]").forEach((button) => button.addEventListener("click", async () => {
    setBusy(button, true, "Restoring…");
    try { const project = await post("/api/projects/restore", {projectId:button.dataset.restoreProject}); await refreshState({quiet:true}); selectProject(project.id); notify(`Restored ${project.name}.`, "success"); }
    catch (error) { notify(error.message, "error"); } finally { setBusy(button, false); }
  }));
  document.querySelectorAll("[data-purge-project]").forEach((button) => button.addEventListener("click", () => {
    const project = projects.find((item) => item.id === button.dataset.purgeProject); if (!project) return;
    $("projectPurgeDialog").dataset.projectId = project.id; $("projectPurgeTitle").textContent = `Delete “${project.name}” permanently?`; $("projectPurgeDialog").showModal();
  }));
}

function activeEditorVariation() {
  return state.selectedProject?.variations.find((item) => item.id === state.editorVariationId) || null;
}

async function renameVariation(variationId, name) {
  try { await post("/api/projects/variations/update", { projectId: state.selectedProject.id, variationId, name }); await refreshState({ quiet: true }); }
  catch (error) { notify(error.message, "error"); await refreshState({ quiet: true }); }
}
function confirmScenarioRemoval(variation, impact) {
  const dialog=$("scenarioRemovalDialog");
  $("scenarioRemovalTitle").textContent=`Remove “${variation.name}”?`;
  const removedResults=Math.max(0,Number(impact.results||0)-Number(impact.retainedResults||0));
  const facts=[["Saved files",impact.files],["Terminal runs",impact.terminalRuns],["Run logs",impact.logs],["Results",removedResults],["Storage",humanBytes(impact.removableBytes||0)]];
  $("scenarioRemovalImpact").innerHTML=facts.map(([label,value])=>`<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("");
  const retained=$("scenarioRemovalRetained");retained.hidden=!impact.retainedResults;retained.textContent=impact.retainedResults?`${impact.retainedResults} shared result${impact.retainedResults===1?" is":"s are"} still referenced by another project and will be retained.`:"";
  return new Promise((resolve)=>{dialog.addEventListener("close",()=>resolve(dialog.returnValue==="remove"),{once:true});dialog.showModal()});
}
async function deleteVariation(variationId, requestedProjectId = state.selectedProject?.id) {
  const project=state.data?.projects?.find((item)=>item.id===requestedProjectId),variation=project?.variations?.find((item)=>item.id===variationId);
  if (!project || !variation) return;
  try {
    const impact=await request(`/api/projects/variations/delete-impact?projectId=${encodeURIComponent(project.id)}&variationId=${encodeURIComponent(variationId)}`);
    if(impact.blocked)return notify(`Stop or finish this scenario’s ${impact.activeRuns} active or queued run${impact.activeRuns===1?"":"s"} before removing it.`,"error");
    if(!await confirmScenarioRemoval(variation,impact))return;
    const result=await post("/api/projects/variations/delete", {projectId:project.id,variationId});
    removeEditorDrafts({projectId:project.id,scenarioId:variationId});
    state.projectScenarioSelections.get(project.id)?.delete(variationId);
    if(state.selectedProject?.id===project.id&&state.editorVariationId===variationId){state.editorVariationId="";state.editorFileName="";clearEditorFile()}
    await refreshState({quiet:true});
    notify(`Removed ${variation.name}, ${result.runsRemoved} run${result.runsRemoved===1?"":"s"}, and ${result.resultsRemoved} result${result.resultsRemoved===1?"":"s"}.`,"success");
  } catch (error) { notify(error.message, "error"); }
}
async function removeOverlay(variationId, filename) {
  if (!await confirmWorkbench(`Remove the saved changes for ${filename} and restore the original input file?`)) return;
  try { const projectId = state.selectedProject.id; await post("/api/overlays/delete", { projectId, variationId, filename }); removeEditorDrafts({projectId,scenarioId:variationId,filename}); if (state.editorFileName === filename) openNewFile(variationId); await refreshState({ quiet: true }); }
  catch (error) { notify(error.message, "error"); }
}

function editorFileUrl(filename) {
  const project = state.selectedProject;
  return `/api/input-file?libraryId=${encodeURIComponent(project.inputLibrary.id)}&filename=${encodeURIComponent(filename)}&projectId=${encodeURIComponent(project.id)}&variationId=${encodeURIComponent(state.editorVariationId)}`;
}
function baselineEditorFileUrl(filename) {
  const project = state.selectedProject;
  return `/api/input-file?libraryId=${encodeURIComponent(project.inputLibrary.id)}&filename=${encodeURIComponent(filename)}`;
}

function meaningfulEditOperations(operations, source = "") {
  return (operations || []).filter((operation) => operation && typeof operation === "object" && operation.operation !== "manual" && Array.isArray(operation.columns) && operation.columns.length && (!source || operation.source === source));
}
function combinedOperationFields(operations) {
  const rawOperations = operations.map((item) => String(item.operation || ""));
  const operationValues = [...new Set(rawOperations.filter(Boolean))];
  const rawAmounts = operations.map((item) => item.value === undefined || item.value === null || item.value === "" ? "" : String(item.value));
  const amounts = [...new Set(rawAmounts.filter(Boolean))];
  const years = [...new Set(operations.map((item) => String(item.year || "")).filter(Boolean))];
  const scopeUnavailable = !operations.every((item) => item.allLocations === true || (item.allLocations === false && Boolean(item.geographyType)));
  const scopes = scopeUnavailable ? [] : operations.map((item) => ({type:item.allLocations ? "all" : String(item.geographyType || ""),label:String(item.geographyLabel || (item.allLocations ? "All locations" : item.geographyType || "Selected locations")),all:Boolean(item.allLocations),locations:[...new Set((item.locations || []).map(String))]}));
  const uniqueScopes = [...new Map(scopes.map((scope) => [`${scope.type}|${scope.all}|${scope.locations.slice().sort().join("\u0000")}`,scope])).values()];
  const scopeKinds = new Set(scopes.map((scope) => `${scope.type}|${scope.all}`));
  const mixedScopes = scopeKinds.size > 1 ? uniqueScopes : [];
  return {
    operation:rawOperations.every(Boolean) && operationValues.length === 1 ? operationValues[0] : rawOperations.every(Boolean) && operationValues.length > 1 ? MIXED_EDITOR_VALUE : "",
    value:rawAmounts.every(Boolean) && amounts.length === 1 ? amounts[0] : "",
    mixedValue:rawAmounts.every(Boolean) && amounts.length > 1,
    year:years.length === 1 ? years[0] : years.includes("2045") ? "2045" : years[0] || "2045",
    geographyType:scopeUnavailable ? "" : mixedScopes.length ? MIXED_EDITOR_VALUE : scopes[0]?.type || "",
    locations:scopeUnavailable || mixedScopes.length || scopes[0]?.all ? [] : [...new Set(scopes.flatMap((scope) => scope.locations))],
    mixedScopes,
    scopeUnavailable,
  };
}
function savedFileDraft(operations) {
  const usable = meaningfulEditOperations(operations); if (!usable.length) return null;
  return {...combinedOperationFields(usable),savedReconstruction:true,columns:[...new Set(usable.flatMap((item) => item.columns.map(String)))],locationSearch:""};
}
function savedBatchDraft(scenario) {
  const grouped = [], columns = {};
  (scenario?.overlays || []).forEach((overlay) => {
    const operations = meaningfulEditOperations(overlay.editOperations, "batch");
    if (!operations.length) return;
    grouped.push(...operations);
    columns[overlay.fileName] = [...new Set(operations.flatMap((item) => item.columns.map(String)))];
  });
  if (!grouped.length) return null;
  return {...combinedOperationFields(grouped),savedReconstruction:true,files:Object.keys(columns),columns,locationSearch:""};
}
function scopeLocationLabel(value, payloads) {
  for (const payload of payloads) for (const level of payload?.levels || []) {
    const found = (level.values || []).find((item) => String(item.value) === String(value));
    if (found) return found.label;
  }
  return String(value);
}
function savedScopeSummary(scopes, payloads = []) {
  return (scopes || []).map((scope) => {
    if (scope.all) return "All locations";
    const labels = scope.locations.map((value) => scopeLocationLabel(value, payloads));
    return `${scope.label || scope.type || "Selected locations"}: ${labels.length ? labels.join(", ") : "selection unavailable"}`;
  }).join(" · ");
}
function savedDraftGuidance(draft, payloads = []) {
  const messages = [];
  if (draft?.operation === MIXED_EDITOR_VALUE || draft?.mixedValue) messages.push("Saved edits use different operations or change amounts. Choose a specific operation and value before applying another change.");
  const scopes = savedScopeSummary(draft?.mixedScopes, payloads);
  if (scopes) messages.push(`Saved location scopes: ${scopes}. Choose one location type before applying another change.`);
  return messages.join(" ");
}
function updateFileDraftGuidance(draft = fileDraftFromControls()) {
  const guidance = savedDraftGuidance(draft, [state.editorGeography]);
  $("editorSavedScopeSummary").hidden = !guidance; $("editorSavedScopeSummary").textContent = guidance;
}
function updateBatchDraftGuidance(draft = batchDraftFromControls()) {
  const guidance = savedDraftGuidance(draft, Object.values(state.batchGeographies));
  $("batchSavedScopeSummary").hidden = !guidance; $("batchSavedScopeSummary").textContent = guidance;
}
function setSelectDraftValue(select, value, mixedLabel) {
  select.querySelector(`option[value="${MIXED_EDITOR_VALUE}"]`)?.remove();
  if (value === MIXED_EDITOR_VALUE) {
    const option = new Option(mixedLabel, MIXED_EDITOR_VALUE, true, true); option.disabled = true; select.prepend(option);
  } else if ([...select.options].some((option) => option.value === value)) select.value = value;
}
function fileDraftFromControls() {
  return {columns:selectedEditorColumns(),geographyType:$('editorLocationField').value,locations:[...state.editorSelectedLocations],year:$('editorYear').value,operation:$('editorOperation').value,value:$('editorValue').value,mixedValue:$('editorValue').placeholder === "Mixed",mixedScopes:structuredClone(state.editorMixedScopes),scopeUnavailable:state.editorScopeUnavailable,locationSearch:$('editorLocationSearch').value};
}
function persistFileDraft() {
  if (!state.editorFileName || !state.csv) return;
  storeEditorDraft("file", fileDraftFromControls(), state.editorFileName);
}
function batchDraftFromControls() {
  return {files:[...state.batchSelectedFiles],columns:Object.fromEntries([...state.batchSelectedColumns].map(([filename,columns]) => [filename,[...columns]])),geographyType:$('batchLocationType').value,locations:[...state.batchSelectedLocations],year:$('batchYear').value,operation:$('batchOperation').value,value:$('batchValue').value,mixedValue:$('batchValue').placeholder === "Mixed",mixedScopes:structuredClone(state.batchMixedScopes),scopeUnavailable:state.batchDraftScopeUnavailable,locationSearch:$('batchLocationSearch').value,fromBaseline:$("batchFromBaseline").checked};
}
function persistBatchDraft() {
  if (!state.editorVariationId || state.editorMode !== "scenario") return;
  storeEditorDraft("batch", batchDraftFromControls());
}

async function loadEditorFile() {
  const filename = $("editorFile").value;
  if (!filename || !state.selectedProject) return;
  setBusy($("saveOverlay"), true, "Loading…");
  try {
    state.editorFileName = filename;
    state.csv = await request(editorFileUrl(filename));
    state.editorOriginalRows = state.csv.rows.map((row) => [...row]); state.editorUndo = []; state.editorRedo = [];
    renderEditorControls(); renderCsv(); renderScenarioTree(); renderEditorPage(); $("saveOverlay").disabled = false;
  } catch (error) { notify(error.message, "error"); } finally { setBusy($("saveOverlay"), false); $("saveOverlay").disabled = !state.csv; }
}

const protectedColumn = (name) => { const value = String(name).toLowerCase(); return ["geo", "year", "county", "bzone", "azone", "marea", "zone", "taz", "id"].includes(value) || value.endsWith("id") || value.endsWith("_id") || value.endsWith("code"); };
function roundedValue(value, column = "") {
  const text = String(value ?? "");
  if (!text.trim() || protectedColumn(column)) return text;
  const numeric = Number(text);
  if (!Number.isFinite(numeric)) return text;
  return new Intl.NumberFormat(undefined, {maximumFractionDigits:precisionFor("output"), useGrouping:false}).format(numeric);
}
function numericPrecisionSettings() {
  return state.data?.workspaceSettings?.numericPrecision || {default:2,singleFile:null,batch:null,output:null,percentage:null};
}
function precisionFor(context = "output") {
  const settings = numericPrecisionSettings(), fallback = Number.isInteger(settings.default) ? settings.default : 2;
  return Number.isInteger(settings[context]) ? settings[context] : fallback;
}
function calculatedValue(next, context = "singleFile", csv = null, column = "") {
  if (csv?.columnTypes?.[column] === "integer") return String(Math.round(next));
  return String(Number(Number(next).toFixed(precisionFor(context))));
}
function newOperationId(prefix = "operation") {
  return globalThis.crypto?.randomUUID?.() || `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
function operationRounding(csv, columns, context) {
  return {precision:precisionFor(context),integerColumns:integerColumns(csv, columns)};
}
function rowsDifferAt(leftRows, rightRows, rowIndex, columnIndex) {
  return String(leftRows?.[rowIndex]?.[columnIndex] ?? "") !== String(rightRows?.[rowIndex]?.[columnIndex] ?? "");
}
function normalizedOperationSet(values) { return [...new Set((values || []).map(String))].sort().join("\u0000"); }
function sameOperationScope(left, right) {
  return String(left?.year || "") === String(right?.year || "")
    && Boolean(left?.allLocations) === Boolean(right?.allLocations)
    && String(left?.geographyType || "") === String(right?.geographyType || "")
    && normalizedOperationSet(left?.columns) === normalizedOperationSet(right?.columns)
    && normalizedOperationSet(left?.locations) === normalizedOperationSet(right?.locations);
}
function operationsWithBaselineOverride(operations, nextOperation) {
  const prior = [...(operations || [])];
  if (nextOperation?.basis !== "baseline") return [...prior,nextOperation];
  return [...prior.filter((operation) => !sameOperationScope(operation,nextOperation)),nextOperation];
}
function integerColumns(csv, columns) { return columns.filter((column) => csv?.columnTypes?.[column] === "integer"); }
function numericColumns(csv) { return csv.columns.filter((column, index) => !protectedColumn(column) && csv.rows.some((row) => row[index] !== "" && Number.isFinite(Number(row[index])))); }
function locationColumns(csv) { const preferred = ["Geo", "County", "Bzone", "Azone", "Marea"]; const values = preferred.filter((name) => csv.columns.includes(name)); return values.length ? values : csv.columns.filter(protectedColumn).filter((name) => name !== "Year").slice(0, 4); }
function selectedValues(select) { return [...select.selectedOptions].map((option) => option.value); }

function renderEditorControls() {
  if (!state.csv) return;
  const locations = locationColumns(state.csv), priorField = $("editorLocationField").value;
  $("editorLocationField").innerHTML = locations.map((name) => `<option>${escapeHtml(name)}</option>`).join("");
  if (locations.includes(priorField)) $("editorLocationField").value = priorField;
  $("editorColumns").innerHTML = numericColumns(state.csv).map((name) => `<option>${escapeHtml(name)}</option>`).join("");
  const yearIndex = state.csv.columns.indexOf("Year");
  const years = yearIndex >= 0 ? [...new Set(state.csv.rows.map((row) => row[yearIndex]).filter(Boolean))].sort() : [""];
  $("editorYear").innerHTML = years.map((year) => `<option ${year === "2045" ? "selected" : ""}>${escapeHtml(year)}</option>`).join("");
  renderEditorLocations(); updateEditorHistoryButtons();
}
function renderEditorLocations() {
  if (!state.csv) return;
  const fieldIndex = state.csv.columns.indexOf($("editorLocationField").value), selected = new Set(selectedValues($("editorLocations"))), query = $("editorLocationSearch").value.toLowerCase();
  const values = fieldIndex >= 0 ? [...new Set(state.csv.rows.map((row) => row[fieldIndex]).filter(Boolean))].sort((a,b) => a.localeCompare(b, undefined, {numeric:true})).filter((value) => !query || value.toLowerCase().includes(query)) : [];
  $("editorLocations").innerHTML = values.map((value) => `<option value="${escapeHtml(value)}" ${selected.has(value) ? "selected" : ""}>${escapeHtml(value)}</option>`).join("");
}
function rowMatchesEditor(row) { const values = selectedValues($("editorLocations")); if (!values.length) return true; const index = state.csv.columns.indexOf($("editorLocationField").value); return values.includes(row[index]); }

function renderCsv() {
  const csv = state.csv; if (!csv) return;
  $("csvTableWrap").innerHTML = `<table><thead><tr>${csv.columns.map((item) => `<th>${escapeHtml(item)}</th>`).join("")}</tr></thead><tbody>${csv.rows.map((row, rowIndex) => `<tr ${rowMatchesEditor(row) ? "" : "hidden"}>${csv.columns.map((column, columnIndex) => { const editable = !protectedColumn(column); const changed = editable && String(row[columnIndex] ?? "") !== String(state.editorOriginalRows[rowIndex]?.[columnIndex] ?? ""); return `<td contenteditable="${editable}" class="${editable ? "" : "readonly-cell"} ${changed ? "changed-cell" : ""}" data-row="${rowIndex}" data-column="${columnIndex}">${escapeHtml(row[columnIndex] ?? "")}</td>`; }).join("")}</tr>`).join("")}</tbody></table>`;
  $("csvTableWrap").querySelectorAll('td[contenteditable="true"]').forEach((cell) => cell.addEventListener("input", () => { state.csv.rows[Number(cell.dataset.row)][Number(cell.dataset.column)] = cell.textContent; cell.classList.add("changed-cell"); }));
}
function editorSnapshot() { return state.csv.rows.map((row) => [...row]); }
function updateEditorHistoryButtons() { $("undoEditorChange").disabled = !state.editorUndo.length; $("redoEditorChange").disabled = !state.editorRedo.length; }
function calculateValue(current, operation, value) { if (operation === "set") return value; if (operation === "add") return current + value; if (operation === "subtract") return current - value; if (operation === "multiply") return current * value; if (operation === "percent") return current * (1 + value / 100); return current * (1 - value / 100); }
function applyEditorChange() {
  const columns = selectedValues($("editorColumns")), value = Number($("editorValue").value); if (!columns.length || !Number.isFinite(value)) return notify("Choose one or more columns and enter a numeric value.", "error");
  if ($("editorLocationField").value !== "all" && !state.editorSelectedLocations.size) return notify("Choose at least one location or use Select all locations.", "error");
  state.editorUndo.push(editorSnapshot()); state.editorRedo = [];
  const yearIndex = state.csv.columns.indexOf("Year"), targetYear = $("editorYear").value, operation = $("editorOperation").value; let changed = 0;
  state.csv.rows.forEach((row) => { if (!rowMatchesEditor(row) || (yearIndex >= 0 && row[yearIndex] !== targetYear)) return; columns.forEach((column) => { const index = state.csv.columns.indexOf(column), current = Number(row[index]); if (!Number.isFinite(current)) return; let next = calculateValue(current, operation, value); if (column.toLowerCase().includes("prop")) next = Math.min(1, next); row[index] = calculatedValue(next, "singleFile", state.csv, column); changed++; }); });
  const rounded = integerColumns(state.csv, columns);
  renderCsv(); updateEditorHistoryButtons(); notify(`Preview changed ${changed} values.${rounded.length ? ` Whole-number count fields were rounded: ${rounded.join(", ")}.` : ""} Save the overlay when ready.`, "success");
}
function undoEditor() { const rows = state.editorUndo.pop(); if (!rows) return; state.editorRedo.push(editorSnapshot()); state.csv.rows = rows; renderCsv(); updateEditorHistoryButtons(); }
function redoEditor() { const rows = state.editorRedo.pop(); if (!rows) return; state.editorUndo.push(editorSnapshot()); state.csv.rows = rows; renderCsv(); updateEditorHistoryButtons(); }

// Create workflow V2. Existing manifest field names remain internal for compatibility.
function editorRowsEqual(left, right) { return JSON.stringify(left || []) === JSON.stringify(right || []); }
function setEditorDirty(dirty = true) {
  state.editorDirty = Boolean(dirty);
  $("editorDirtyState").textContent = state.editorDirty ? "Unsaved changes" : "Saved";
  $("editorDirtyState").classList.toggle("dirty", state.editorDirty);
  $("saveOverlay").disabled = !state.csv || !state.editorDirty;
  syncMenuContext();
}
function recomputeEditorDirty() {
  setEditorDirty(Boolean(state.csv) && !editorRowsEqual(state.csv.rows, state.editorOriginalRows));
}
function noteStatusElement(kind) { return $(kind === "scenario" ? "scenarioNoteStatus" : "fileNoteStatus"); }
function setNoteStatus(kind, status) {
  const element = noteStatusElement(kind); if (!element) return;
  element.textContent = status;
  element.classList.toggle("saving", status === "Saving…");
  element.classList.toggle("failed", status === "Not saved");
}
function noteContext(kind) {
  const projectId = state.selectedProject?.id || "", variationId = state.editorVariationId || "";
  return kind === "scenario" ? `${projectId}|${variationId}` : `${projectId}|${variationId}|${state.editorFileName || ""}`;
}
function primeNoteAutosave(kind, value) {
  const tracker = state.noteAutosave[kind];
  if (tracker.timer) clearTimeout(tracker.timer);
  tracker.timer = null; tracker.dirty = false; tracker.revision += 1; tracker.context = noteContext(kind); tracker.value = String(value || "");
  setNoteStatus(kind, "Saved");
}
function updateLocalVariation(projectId, variationId, update) {
  const projects = [...(state.data?.projects || []), ...(state.data?.archivedProjects || [])];
  const seen = new Set();
  for (const project of [...projects, state.selectedProject].filter(Boolean)) {
    if (seen.has(project)) continue; seen.add(project);
    if (project.id !== projectId) continue;
    const variation = (project.variations || []).find((item) => item.id === variationId);
    if (variation) update(variation);
  }
}
function scheduleNoteAutosave(kind, value) {
  const tracker = state.noteAutosave[kind], context = noteContext(kind);
  if (!context.replaceAll("|", "")) return;
  if (tracker.context !== context) primeNoteAutosave(kind, value);
  tracker.value = String(value); tracker.dirty = true; tracker.revision += 1;
  if (tracker.timer) clearTimeout(tracker.timer);
  setNoteStatus(kind, "Saving…");
  tracker.timer = setTimeout(() => { tracker.timer = null; saveNoteNow(kind); }, 700);
}
async function saveNoteNow(kind) {
  const tracker = state.noteAutosave[kind];
  if (tracker.timer) { clearTimeout(tracker.timer); tracker.timer = null; }
  if (tracker.inFlight) {
    await tracker.inFlight;
  }
  if (!tracker.dirty) return true;
  const [projectId, variationId, filename] = tracker.context.split("|"), revision = tracker.revision, value = tracker.value;
  if (!projectId || !variationId || (kind === "file" && !filename)) return false;
  setNoteStatus(kind, "Saving…");
  const requestBody = kind === "scenario"
    ? {projectId, variationId, scenarioNote:value}
    : {projectId, variationId, fileNote:{filename, text:value}};
  const requestPromise = (async () => {
    try {
      await post("/api/projects/variations/update", requestBody);
      updateLocalVariation(projectId, variationId, (variation) => {
        if (kind === "scenario") variation.scenarioNote = value;
        else { variation.notes ||= {}; if (value) variation.notes[filename] = value; else delete variation.notes[filename]; }
      });
      if (tracker.context === noteContext(kind) && tracker.revision === revision) {
        tracker.dirty = false; setNoteStatus(kind, "Saved");
      }
      return true;
    } catch (error) {
      if (tracker.context === noteContext(kind)) setNoteStatus(kind, "Not saved");
      return false;
    }
  })();
  tracker.inFlight = requestPromise;
  const saved = await requestPromise;
  if (tracker.inFlight === requestPromise) tracker.inFlight = null;
  if (saved && tracker.dirty && tracker.revision !== revision) return saveNoteNow(kind);
  return saved;
}
async function flushPendingNoteSaves() {
  const saved = await Promise.all([saveNoteNow("scenario"), saveNoteNow("file")]);
  if (saved.every(Boolean)) return true;
  notify("A note could not be saved. Your text is still here; try again before leaving.", "error");
  return false;
}
async function guardUnsaved(action) {
  if (!await flushPendingNoteSaves()) return false;
  if (!await flushHypercubeAutosave()) return false;
  if (!state.editorDirty) { await action(); return true; }
  const dialog = $("unsavedDialog");
  return new Promise((resolve) => {
    dialog.addEventListener("close", async function decide() {
      dialog.removeEventListener("close", decide);
      if (dialog.returnValue === "save") {
        const saved = await saveFileChanges();
        if (!saved) return resolve(false);
        await action(); resolve(true);
      } else if (dialog.returnValue === "discard") {
        setEditorDirty(false); await action(); resolve(true);
      } else resolve(false);
    });
    dialog.showModal();
  });
}
function switchCreateSubpage(pageId, guarded = true) {
  if (pageId === "createHypercube" && !state.hypercubeSafetyAcknowledged) {
    const dialog = $("hypercubeSafetyDialog");
    renderHypercubeSafetyEstimate();
    if (!dialog.open) dialog.showModal();
    return false;
  }
  const change = () => {
    closeLocationPopovers();
    state.activeCreateSubpage = pageId;
    document.querySelectorAll(".create-subpage").forEach((page) => page.classList.toggle("active", page.id === pageId));
    document.querySelectorAll("[data-create-subpage]").forEach((button) => button.classList.toggle("active", button.dataset.createSubpage === pageId));
    if (pageId === "createReview") loadProjectReview();
    if (pageId === "createDevelop") preloadRegionMapGeometry().catch(() => {});
  };
  return guarded ? guardUnsaved(change) : change();
}
function openProjectEditDialog(projectId) {
  const project = state.data?.projects.find((item) => item.id === projectId); if (!project) return;
  $("projectEditDialog").dataset.projectId = projectId; $("projectEditName").value = project.name;
  $("projectEditDialog").showModal(); $("projectEditName").focus(); $("projectEditName").select();
}
function openProjectCopyDialog(projectId) {
  const project = state.data?.projects.find((item) => item.id === projectId); if (!project) return;
  const blocked=destinationCopyBlockedMessage(projectId);
  if(blocked)return notify(blocked,"error");
  $("projectCopyDialog").dataset.projectId = projectId;
  const existing=new Set([...(state.data?.projects||[]),...(state.data?.archivedProjects||[])].map((item)=>String(item.name||"").trim().replace(/\s+/g," ").toLocaleLowerCase()));
  const base=`${project.name} Copy`;let candidate=base,number=2;while(existing.has(candidate.trim().replace(/\s+/g," ").toLocaleLowerCase()))candidate=`${base} ${number++}`;
  $("projectCopyName").value = candidate;
  $("projectCopyResultEstimate").textContent = "Checking completed-result storage…";
  request(`/api/projects/copy-estimate?projectId=${encodeURIComponent(projectId)}`).then((estimate)=>{
    $("projectCopyResultEstimate").textContent=estimate.resultCount
      ? `${estimate.resultCount} completed result${estimate.resultCount===1?"":"s"} · approximately ${humanBytes(estimate.bytes)} will be copied into the new project.`
      : "No completed results are available; the project design will still be copied.";
  }).catch(()=>{$("projectCopyResultEstimate").textContent="Completed-result size could not be estimated. Workbench will verify available space before copying."});
  $("projectCopyDialog").showModal(); $("projectCopyName").focus(); $("projectCopyName").select();
}
function openBaselineRenameDialog() {
  if (!state.selectedProject) return;
  $("baselineDisplayName").value = baselineDisplayName();
  $("baselineRenameDialog").showModal();
  $("baselineDisplayName").focus(); $("baselineDisplayName").select();
}
function projectPackageName(project) {
  return project?.inputLibrary?.displayName || project?.inputLibrary?.name || project?.template?.name || "VisionEval model";
}
function isHypercubeProject(project) { return project?.projectType === "hypercube"; }
function isStatewideProject(project) {
  if (!project) return false;
  if (project.regionType === "statewide" || project.selectionMethod === "package-statewide") return true;
  const template = (state.data?.templates || []).find((item) => item.id === project.template?.id);
  return template?.regionType === "statewide"
    || template?.selectionMethod === "package-statewide"
    || template?.regionId === "virginia-statewide";
}
function editSourceValue(operations = []) {
  if (!operations.length || operations.some((item) => !["batch", "single_file"].includes(item?.source))) return "unavailable";
  const sources = new Set(operations.map((item) => item.source));
  return sources.size > 1 ? "mixed" : [...sources][0];
}
function scenarioEditSource(scenario) {
  const sources = new Set((scenario?.overlays || []).map((item) => editSourceValue(item.editOperations || [])));
  if (!sources.size || sources.has("unavailable")) return "unavailable";
  return sources.size > 1 || sources.has("mixed") ? "mixed" : [...sources][0];
}
function editSourceLabel(value) {
  return {batch:"Batch change",single_file:"Single-file change",mixed:"Batch and single-file changes"}[value] || "";
}
function editSourceMarker(value, focusable = true) {
  const label = editSourceLabel(value);
  if (!label) return "";
  const singleIcon = `<svg class="edit-source-icon edit-source-icon-single" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M7 3.5h7l3 3V20.5H7zM14 3.5v4h4"/></svg>`;
  const batchIcon = `<svg class="edit-source-icon edit-source-icon-batch" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M5.5 7.5h7l3 3v10h-10zM8.5 4.5h7l3 3v10"/></svg>`;
  const mixedIcon = `<span class="edit-source-mixed-letter" aria-hidden="true">M</span>`;
  const icons = value === "mixed" ? mixedIcon : value === "batch" ? batchIcon : singleIcon;
  return `<span class="edit-source-marker edit-source-${escapeHtml(value)}" role="img" aria-label="${escapeHtml(label)}"${focusable ? ' tabindex="0"' : ""}>${icons}<span class="edit-source-tooltip" role="tooltip">${escapeHtml(label)}</span></span>`;
}
function openProjectRemoveDialog(projectId) {
  const project = state.data?.projects.find((item) => item.id === projectId); if (!project) return;
  $("projectRemoveDialog").dataset.projectId = projectId;
  $("projectRemoveTitle").textContent = `Remove “${project.name}”?`; $("projectRemoveDialog").showModal();
}
function openScenarioDialog(duplicate = false) {
  if (!state.selectedProject) return;
  const source = duplicate ? activeEditorVariation() : null;
  if (duplicate && !source) return notify("Select a scenario to copy first.", "error");
  const dialog = $("scenarioDialog"); dialog.dataset.duplicateFrom = source?.id || "";
  $("scenarioDialogTitle").textContent = source ? `Copy ${source.name}` : "New scenario";
  $("scenarioDialogName").value = source ? `${source.name} Copy` : `Scenario ${state.selectedProject.variations.length + 1}`;
  $("scenarioDialogHelp").textContent = source ? "The copy includes all saved file changes and notes from the selected scenario." : "The new scenario starts with untouched project inputs.";
  $("confirmScenarioDialog").textContent = source ? "Copy Scenario" : "Create Scenario";
  dialog.showModal(); $("scenarioDialogName").focus(); $("scenarioDialogName").select();
}
function renderProjects() {
  const projects = state.data?.projects || [];
  const projectIds = new Set(projects.map((project) => project.id));
  for (const projectId of state.expandedProjectIds) if (!projectIds.has(projectId)) state.expandedProjectIds.delete(projectId);
  $("projectCount").textContent = projects.length;
  $("projectList").classList.toggle("empty-state", !projects.length);
  const catalog = new Map((state.data?.catalog || []).map((item)=>[item.id,item]));
  $("projectList").innerHTML = projects.length ? projects.map((project) => {
    const expanded=state.expandedProjectIds.has(project.id),links=project.resultLinks||[],linkedIds=new Set(links.map((item)=>item.datastoreId)),resultIds=[...new Set([...(project.datastoreIds||[]),...linkedIds])],selected=state.projectScenarioSelections.get(project.id)||new Set();
    const projectCopyJobs=activeProjectCopyJobs(project.id),projectCopyReason=projectCopyJobs.length?"Cannot copy this project while its runs are in progress. Wait until they finish or are stopped.":"";
    const selectedCopyReason=activeScenarioCopyJobs(project.id,[...selected]).length?"Cannot copy while selected scenario runs are in progress. Wait until they finish or are stopped.":"";
    const scenarios=project.variations.length?project.variations.map((scenario)=>{const copyJob=activeScenarioCopyJobs(project.id,[scenario.id])[0],copyBlocked=Boolean(copyJob),removeLabel=`Remove ${scenario.name}`;return `<div class="project-scenario-row ${copyBlocked?"copy-blocked":""}"><label class="project-scenario-selection"><input type="checkbox" data-project-scenario="${escapeHtml(project.id)}" value="${escapeHtml(scenario.id)}" ${selected.has(scenario.id)?"checked":""}><span><strong>${escapeHtml(scenario.name)} ${editSourceMarker(scenarioEditSource(scenario),false)}</strong><small>${scenario.overlays?.length||0} saved input files${scenario.hypercube?" · hypercube case":""}${scenario.resultStatus==="current"?" · current result available":scenario.resultStatus&&scenario.resultStatus!=="missing"?" · previous result available":""}${copyBlocked?` · ${escapeHtml(copyJob.state)} run; actions available after it finishes or is stopped`:""}</small></span></label>${isHypercubeProject(project)?"":`<button type="button" class="secondary project-scenario-remove" data-remove-project-scenario="${escapeHtml(scenario.id)}" data-remove-scenario-project="${escapeHtml(project.id)}" data-remove-disabled-reason="${copyBlocked?"Stop or finish this scenario’s run before removing it.":""}" aria-label="${escapeHtml(removeLabel)}" title="${escapeHtml(removeLabel)}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m-9 0 1 14h10l1-14M10 11v6m4-6v6"/></svg></button>`}</div>`}).join(""):`<p class="muted">No scenarios to copy.</p>`;
    const results=resultIds.length?resultIds.map((id)=>{const record=catalog.get(id),linked=linkedIds.has(id),status=(project.resultStatuses?.[record?.role==="baseline"?"baseline":record?.variationId]||[]).find((item)=>item.datastoreId===id)?.status||"";if(!record)return"";const statusLabel={current:"Current",previous:"Previous version",runtime_differs:"Runtime differs",unproven:"Reuse unverified"}[status]||"Completed";return `<div class="project-result-row"><span><strong>${escapeHtml(record.displayLabel||record.label||record.displayVariationName||record.variationName||"Completed result")}</strong><small>${linked?"Legacy shared result":"Independent project result"} · ${escapeHtml(statusLabel)} · ${escapeHtml(record.displayVariationName||record.variationName||record.role||"")}</small></span><span class="project-result-actions"><button type="button" class="secondary" data-compare-project-result="${escapeHtml(id)}">Compare</button>${linked?`<button type="button" class="text-button" data-unlink-project-result="${escapeHtml(id)}" data-result-project="${escapeHtml(project.id)}">Remove link</button>`:""}</span></div>`}).join(""):`<p class="muted">No completed results.</p>`;
    const hypercubeProject=isHypercubeProject(project),projectTypeLabel=hypercubeProject?"Hypercube":"Standard";
    const scenarioNoun=hypercubeProject?(project.variations.length===1?"case":"cases"):(project.variations.length===1?"scenario":"scenarios");
    return `<article class="item-card project-card ${expanded?"expanded":""}">
      <button class="project-card-open" type="button" data-expand-project="${escapeHtml(project.id)}" aria-expanded="${expanded}">
        <span class="project-card-chevron" aria-hidden="true"><svg viewBox="0 0 24 24" focusable="false"><path d="M7 4l10 8-10 8z"/></svg></span><header><strong>${escapeHtml(project.name)}</strong></header>
        <small>${escapeHtml(projectPackageName(project))} · ${projectTypeLabel}</small>
        <span class="project-card-metadata"><span class="scenario-count-badge"><b>${project.variations.length}</b> ${scenarioNoun}</span><small>${project.runIds.length} runs · ${resultIds.length} results${linkedIds.size?` (${linkedIds.size} linked)`:""}</small></span>
      </button>
      <div class="project-card-actions"><button class="secondary" type="button" data-open-project="${escapeHtml(project.id)}" data-project-type="${projectTypeLabel.toLowerCase()}">${hypercubeProject?"Open Hypercube":"Open in Editor"}</button><button class="secondary" type="button" data-copy-project="${escapeHtml(project.id)}" data-copy-disabled-reason="${escapeHtml(projectCopyReason)}">Copy Project</button><button class="secondary" type="button" data-edit-project="${escapeHtml(project.id)}">Edit name</button><button class="danger" type="button" data-remove-project="${escapeHtml(project.id)}">Remove</button></div>
      ${expanded?`<div class="project-card-details"><section><div class="checklist-heading"><strong>${hypercubeProject?"Generated cases":"Scenarios"}</strong><button type="button" data-copy-project-scenarios="${escapeHtml(project.id)}" data-copy-disabled-reason="${escapeHtml(selectedCopyReason)}">${hypercubeProject?"Copy Cases":"Copy Scenarios"} (${selected.size})</button></div><div class="project-scenario-list">${scenarios}</div></section><section><strong>Results</strong><div class="project-result-list">${results}</div></section></div>`:""}
    </article>`;
  }).join("") : "No projects yet.";
  document.querySelectorAll("[data-copy-project]").forEach((button)=>setButtonAvailability(button,!button.dataset.copyDisabledReason,button.dataset.copyDisabledReason));
  document.querySelectorAll("[data-copy-project-scenarios]").forEach((button)=>{
    const selected=state.projectScenarioSelections.get(button.dataset.copyProjectScenarios)||new Set();
    setButtonAvailability(button,Boolean(selected.size)&&!button.dataset.copyDisabledReason,button.dataset.copyDisabledReason||"Select one or more scenarios to copy.");
  });
  document.querySelectorAll("[data-remove-project-scenario]").forEach((button)=>{setButtonAvailability(button,!button.dataset.removeDisabledReason,button.dataset.removeDisabledReason);button.addEventListener("click",()=>deleteVariation(button.dataset.removeProjectScenario,button.dataset.removeScenarioProject))});
  document.querySelectorAll("[data-expand-project]").forEach((button)=>button.addEventListener("click",()=>{const id=button.dataset.expandProject;state.expandedProjectIds.has(id)?state.expandedProjectIds.delete(id):state.expandedProjectIds.add(id);renderProjects()}));
  document.querySelectorAll("[data-open-project]").forEach((button) => button.addEventListener("click", () => guardUnsaved(() => {
    selectProject(button.dataset.openProject);
    if(button.dataset.projectType==="hypercube") {
      if(state.hypercubeProjectId!==button.dataset.openProject) {
        state.hypercubeAxes=[];state.hypercubeSelectedLocations=new Set();state.hypercubePreview=null;state.hypercubeHydratedProjectId="";state.hypercubeFiles=new Map();
      }
      state.hypercubeProjectId=button.dataset.openProject;renderHypercubeSetup();switchCreateSubpage("createHypercube", false);
    }
    else switchCreateSubpage("createEditor", false);
  })));
  document.querySelectorAll("[data-project-scenario]").forEach((control)=>control.addEventListener("change",()=>{const projectId=control.dataset.projectScenario,selections=state.projectScenarioSelections.get(projectId)||new Set();control.checked?selections.add(control.value):selections.delete(control.value);state.projectScenarioSelections.set(projectId,selections);renderProjects()}));
  document.querySelectorAll("[data-copy-project-scenarios]").forEach((button)=>button.addEventListener("click",async()=>{if(await flushPendingNoteSaves())openScenarioCopyDialog(button.dataset.copyProjectScenarios)}));
  document.querySelectorAll("[data-compare-project-result]").forEach((button)=>button.addEventListener("click",()=>{switchPage("comparePage",{restoreScroll:false});switchSubpage("loadData");selectedOption($("referenceDatastore"),button.dataset.compareProjectResult);notify("Result selected as the Compare reference.","success")}));
  document.querySelectorAll("[data-unlink-project-result]").forEach((button)=>button.addEventListener("click",async()=>{if(!await confirmWorkbench("Remove this shared result link from the project? The original result data will not be deleted while another project still owns or references it."))return;try{await post("/api/projects/results/unlink",{projectId:button.dataset.resultProject,datastoreId:button.dataset.unlinkProjectResult});await refreshState({quiet:true});notify("Shared result link removed.","success")}catch(error){notify(error.message,"error")}}));
  document.querySelectorAll("[data-copy-project]").forEach((button) => button.addEventListener("click", () => openProjectCopyDialog(button.dataset.copyProject)));
  document.querySelectorAll("[data-edit-project]").forEach((button) => button.addEventListener("click", () => openProjectEditDialog(button.dataset.editProject)));
  document.querySelectorAll("[data-remove-project]").forEach((button) => button.addEventListener("click", () => openProjectRemoveDialog(button.dataset.removeProject)));
  if (state.selectedProject) {
    const current = projects.find((item) => item.id === state.selectedProject.id);
    if (current) selectProject(current.id, false);
  }
}

function openScenarioCopyDialog(projectId){
  const source=state.data?.projects.find((item)=>item.id===projectId),selected=[...(state.projectScenarioSelections.get(projectId)||[])];
  if(!source||!selected.length)return notify("Select one or more scenarios first.","error");
  const blockedMessage=scenarioCopyBlockedMessage(projectId,selected);if(blockedMessage)return notify(blockedMessage,"error");
  const compatible=(state.data?.projects||[]).filter((item)=>item.id!==projectId&&!isHypercubeProject(item)&&item.template?.fingerprint===source.template?.fingerprint&&item.inputLibrary?.fingerprint===source.inputLibrary?.fingerprint);
  const dialog=$("scenarioCopyDialog");dialog.dataset.sourceProjectId=projectId;dialog.dataset.variationIds=JSON.stringify(selected);
  $("scenarioCopySummary").textContent=`${selected.length} scenario${selected.length===1?"":"s"} selected from ${source.name}.`;
  $("scenarioCopyResultEstimate").textContent="Checking completed-result storage…";
  request(`/api/projects/copy-estimate?projectId=${encodeURIComponent(projectId)}&variationIds=${encodeURIComponent(selected.join(","))}`).then((estimate)=>{
    $("scenarioCopyResultEstimate").textContent=estimate.resultCount
      ? `${estimate.resultCount} completed result${estimate.resultCount===1?"":"s"} · approximately ${humanBytes(estimate.bytes)} will be copied independently.`
      : "These scenarios have no completed results. Workbench can offer to run them after copying.";
  }).catch(()=>{$("scenarioCopyResultEstimate").textContent="Completed-result size could not be estimated. Workbench will verify available space before copying."});
  const idle=compatible.filter((item)=>!activeProjectCopyJobs(item.id).length);
  $("scenarioCopyTargetProject").innerHTML=compatible.length?compatible.map((item)=>{const jobs=activeProjectCopyJobs(item.id),states=[...new Set(jobs.map((job)=>job.state))].sort().join(", ");return `<option value="${escapeHtml(item.id)}" ${jobs.length?"disabled":""}>${escapeHtml(item.name)}${jobs.length?` — unavailable (${escapeHtml(states)})`:""}</option>`}).join(""):`<option value="">No compatible existing projects</option>`;
  const existingRadio=document.querySelector('[name="scenarioCopyDestination"][value="existing"]'),newRadio=document.querySelector('[name="scenarioCopyDestination"][value="new"]');
  existingRadio.disabled=!idle.length;existingRadio.checked=Boolean(idle.length);newRadio.checked=!idle.length;
  $("scenarioCopyTargetProject").disabled=!idle.length;$("scenarioCopyNewProjectName").disabled=Boolean(idle.length);$("scenarioCopyNewProjectName").value=`${source.name} — Selected Scenarios`;
  const destinationStatus=$("scenarioCopyDestinationStatus");destinationStatus.hidden=compatible.length===idle.length;destinationStatus.textContent=compatible.length===idle.length?"":"Projects with unfinished runs are unavailable. Please wait until every run in the project has finished or been stopped.";
  dialog.showModal();
}
function renderEditorProjectSelect() {
  const projects = state.data?.projects || [], prior = state.selectedProject?.id || $("editorProjectSelect").value;
  const standardProjects = projects.filter((project)=>!isHypercubeProject(project));
  $("editorProjectSelect").innerHTML = `<option value="">Choose a standard project</option>${standardProjects.map((project) => `<option value="${escapeHtml(project.id)}">${escapeHtml(project.name)}</option>`).join("")}`;
  $("reviewProjectSelect").innerHTML = `<option value="">Choose a project</option>${projects.map((project) => `<option value="${escapeHtml(project.id)}">${escapeHtml(project.name)}</option>`).join("")}`;
  selectedOption($("editorProjectSelect"), standardProjects.some((project)=>project.id===prior)?prior:"");
  selectedOption($("reviewProjectSelect"), prior);
}
function hypercubeProject() {
  return state.data?.projects?.find((item) => item.id === state.hypercubeProjectId) || null;
}
function hypercubeLibrary() {
  const project = hypercubeProject();
  return state.data?.inputLibraries?.find((item) => item.id === project?.inputLibrary?.id) || null;
}
function hypercubeProjectEditable() {
  const project=hypercubeProject(),existing=project?.hypercubes?.[0];
  if(!project)return false;
  if(!existing)return true;
  return !(project.runIds||[]).length&&!Object.entries(project.resultStatuses||{}).some(([key,records])=>key!=="baseline"&&(records||[]).length);
}
function refreshHypercubeSaveControls() {
  const tracker=state.hypercubeAutosave;
  if($("hypercubeSaveStatus")){
    const label=tracker.inFlight?"Saving…":tracker.lastError?"Not saved—retry":state.hypercubeDirty?"Saving…":"Saved";
    $("hypercubeSaveStatus").textContent=label;
    $("hypercubeSaveStatus").classList.toggle("warning",Boolean(tracker.lastError||state.hypercubeDirty));
  }
  if($("retryHypercubeSave"))$("retryHypercubeSave").hidden=!tracker.lastError||!hypercubeProjectEditable()||Boolean(tracker.inFlight);
  if($("previewHypercube"))$("previewHypercube").disabled=state.hypercubeDirty||Boolean(tracker.inFlight)||!state.hypercubeSavedRevision||!state.hypercubeSavedComplete||!hypercubeProjectEditable();
  if($("generateHypercube"))$("generateHypercube").disabled=state.hypercubeDirty||Boolean(tracker.inFlight)||!state.hypercubePreviewRevision||state.hypercubePreviewRevision!==state.hypercubeSavedRevision;
}
function scheduleHypercubeAutosave() {
  const tracker=state.hypercubeAutosave;
  if(tracker.timer)clearTimeout(tracker.timer);
  if(!state.hypercubeDirty||!hypercubeProjectEditable())return;
  tracker.timer=setTimeout(()=>{tracker.timer=null;saveHypercubeDraft({announce:false,flush:false})},650);
}
function setHypercubeDirty(dirty=true) {
  state.hypercubeDirty=Boolean(dirty);
  if(dirty){state.hypercubeAutosave.changeRevision+=1;state.hypercubeAutosave.lastError="";state.hypercubePreview=null;state.hypercubePreviewRevision="";state.hypercubePreviewToken="";scheduleHypercubeAutosave()}
  else if(state.hypercubeAutosave.timer){clearTimeout(state.hypercubeAutosave.timer);state.hypercubeAutosave.timer=null}
  refreshHypercubeSaveControls();
}
function hydrateHypercubeProject(project) {
  if(!project||state.hypercubeHydratedProjectId===project.id)return;
  const source=project.hypercubeDraft||project.hypercubes?.[0]||null;
  state.hypercubeHydratedProjectId=project.id;
  state.hypercubeAxes=(source?.axes||[]).map((axis)=>({id:`hypercube-axis-${++state.hypercubeAxisSequence}`,filename:String(axis.filename||""),column:String(axis.column||""),operation:String(axis.operation||"percent"),start:String(axis.start??"10"),end:String(axis.end??"50"),interval:String(axis.interval??"5")}));
  state.hypercubeScopeDraft={year:source?String(source.year||""):null,geographyType:String(source?.geographyType||"all")};
  state.hypercubeSelectedLocations=new Set((source?.locations||[]).map(String));
  state.hypercubeSavedRevision=String(project.hypercubeDraft?.revision||"");
  state.hypercubeSavedComplete=project.hypercubeDraft?Boolean(project.hypercubeDraft.complete):Boolean(project.hypercubes?.length);
  state.hypercubePreviewRevision="";state.hypercubePreviewToken="";state.hypercubePreview=null;state.hypercubeLocationSearch="";
  state.hypercubeLocationPopoverOpen=false;
  if(state.hypercubeAutosave.timer)clearTimeout(state.hypercubeAutosave.timer);
  state.hypercubeAutosave={timer:null,inFlight:null,changeRevision:0,lastError:""};
  setHypercubeDirty(false);
  [...new Set(state.hypercubeAxes.map((axis)=>axis.filename).filter(Boolean))].forEach((filename)=>ensureHypercubeFile(filename));
}
function invalidateHypercubePreview(message = "Configure the parameters, then preview the matrix.") {
  state.hypercubePreview = null;state.hypercubePreviewRevision="";state.hypercubePreviewToken="";
  $("generateHypercube").disabled = true;
  $("hypercubePreview").className = "hypercube-preview empty-state";
  $("hypercubePreview").textContent = message;
}
function hypercubeFileKey(filename) { return `${state.hypercubeProjectId}:${filename}`; }
function hypercubeFileState(axis) { return state.hypercubeFiles.get(hypercubeFileKey(axis.filename)); }
function hypercubeFileRecord(axis) { const record=hypercubeFileState(axis);return record?.status==="ready"?record:null; }
async function ensureHypercubeFile(filename) {
  if(!filename)return null;
  const project=hypercubeProject();if(!project)return null;
  const key=hypercubeFileKey(filename),existing=state.hypercubeFiles.get(key);
  if(existing?.status==="ready")return existing;
  if(existing?.status==="loading")return existing.promise;
  const token=++state.hypercubeFileLoadSequence,projectId=project.id;
  const record={status:"loading",token,error:"",csv:null,geography:null,promise:null};
  record.promise=Promise.all([
    request(`/api/input-file?libraryId=${encodeURIComponent(project.inputLibrary.id)}&filename=${encodeURIComponent(filename)}`),
    request(`/api/geography-options?projectId=${encodeURIComponent(project.id)}&filename=${encodeURIComponent(filename)}`),
  ]).then(([csv,geography])=>{const current=state.hypercubeFiles.get(key);if(current?.token!==token)return current;Object.assign(record,{status:"ready",csv,geography,promise:null});return record}).catch((error)=>{const current=state.hypercubeFiles.get(key);if(current?.token===token)Object.assign(record,{status:"error",error:error.message||String(error),promise:null});return record}).finally(()=>{if(state.hypercubeProjectId===projectId){renderHypercubeAxes();renderHypercubeSharedFilters()}});
  state.hypercubeFiles.set(key,record);renderHypercubeAxes();renderHypercubeSharedFilters();return record.promise;
}
function renderHypercubeSetup() {
  if (!$("hypercubeProject")) return;
  const projects = (state.data?.projects || []).filter(isHypercubeProject);
  const prior = state.hypercubeProjectId || state.selectedProject?.id || $("hypercubeProject").value;
  $("hypercubeProject").innerHTML = `<option value="">Choose a Hypercube project</option>${projects.map((project) => `<option value="${escapeHtml(project.id)}">${escapeHtml(project.name)}</option>`).join("")}`;
  state.hypercubeProjectId = projects.some((item) => item.id === prior) ? prior : "";
  selectedOption($("hypercubeProject"), state.hypercubeProjectId);
  const project=hypercubeProject(),existing=project?.hypercubes?.[0],replaceAllowed=Boolean(existing)&&!(project.runIds||[]).length&&!Object.entries(project.resultStatuses||{}).some(([key,records])=>key!=="baseline"&&(records||[]).length);
  if(!project&&state.hypercubeHydratedProjectId){state.hypercubeHydratedProjectId="";state.hypercubeAxes=[];state.hypercubeSelectedLocations=new Set();state.hypercubeSavedRevision="";state.hypercubeSavedComplete=false;setHypercubeDirty(false)}
  hydrateHypercubeProject(project);
  $("hypercubeExistingNotice").hidden=!existing;
  if(existing) $("hypercubeExistingNotice").innerHTML=replaceAllowed
    ? `<strong>${escapeHtml(existing.name)} is this project’s current matrix.</strong><p>You may configure a replacement until a case is submitted to Run. Replacing it removes the current generated cases.</p>`
    : `<strong>${escapeHtml(existing.name)} is locked.</strong><p>A case has been submitted to Run or produced a result. Create a new Hypercube project to build a different matrix.</p>`;
  const editable=Boolean(project)&&(!existing||replaceAllowed);
  $("addHypercubeAxis").disabled = !editable;
  $("previewHypercube").disabled=!editable;
  renderHypercubeAxes();
  renderHypercubeSharedFilters();
  refreshHypercubeSaveControls();
  if(!editable) {
    $("hypercubeYear").disabled=true;$("hypercubeGeographyType").disabled=true;$("hypercubeLocationTrigger").disabled=true;
    $("hypercubeAxes").querySelectorAll("input,select,button").forEach((control)=>control.disabled=true);
  }
}
function addHypercubeAxis() {
  const library = hypercubeLibrary();
  if (!library?.files?.length) return notify("The selected project has no input CSV files.", "error");
  const axis = {id:`hypercube-axis-${++state.hypercubeAxisSequence}`,filename:"",column:"",operation:"percent",start:"10",end:"50",interval:"5"};
  state.hypercubeAxes.push(axis); setHypercubeDirty(); invalidateHypercubePreview(); renderHypercubeAxes();
}
async function loadHypercubeAxisFile(axis, filename) {
  axis.filename = filename; axis.column = ""; setHypercubeDirty(); invalidateHypercubePreview(); renderHypercubeAxes(); renderHypercubeSharedFilters();
  if (!filename) { renderHypercubeSharedFilters(); return; }
  try {
    const record=await ensureHypercubeFile(filename);
    const current = state.hypercubeAxes.find((item) => item.id === axis.id);
    if (!current || current.filename !== filename) return;
    if(record?.status!=="ready")return;
    current.column = numericColumns(record.csv)[0] || "";
    setHypercubeDirty();invalidateHypercubePreview();
    renderHypercubeAxes(); renderHypercubeSharedFilters();
  } catch (error) { notify(error.message, "error"); }
}
function hypercubeOperationOptions(selected) {
  const options = [["set","Set to"],["add","Increase by"],["subtract","Decrease by"],["multiply","Multiply by"],["percent","Increase by %"],["decrease_percent","Decrease by %"]];
  return options.map(([value,label]) => `<option value="${value}" ${selected===value?"selected":""}>${label}</option>`).join("");
}
function renderHypercubeAxes() {
  if (!$("hypercubeAxes")) return;
  const files = (hypercubeLibrary()?.files || []).filter((item) => item.toLowerCase().endsWith(".csv"));
  $("hypercubeAxes").classList.toggle("empty-state", !state.hypercubeAxes.length);
  $("hypercubeAxes").innerHTML = state.hypercubeAxes.length ? state.hypercubeAxes.map((axis) => {
    const load=hypercubeFileState(axis),record = hypercubeFileRecord(axis), columns = record ? numericColumns(record.csv) : [],loading=load?.status==="loading",failed=load?.status==="error";
    return `<article class="hypercube-axis-row" data-hypercube-axis="${escapeHtml(axis.id)}">
      <label>Input file<select data-hypercube-axis-field="filename"><option value="">Choose file</option>${files.map((name)=>`<option value="${escapeHtml(name)}" ${axis.filename===name?"selected":""}>${escapeHtml(name)}</option>`).join("")}</select></label>
      <label>Numeric column<select data-hypercube-axis-field="column" ${record?"":"disabled"}><option value="">${loading?"Loading file…":failed?"File could not load":record?"Choose column":"Choose file first"}</option>${columns.map((name)=>`<option value="${escapeHtml(name)}" ${axis.column===name?"selected":""}>${escapeHtml(name)}</option>`).join("")}</select>${failed?`<small class="field-error">${escapeHtml(load.error)}</small><button type="button" class="text-button" data-retry-hypercube-file="${escapeHtml(axis.filename)}">Retry loading file</button>`:""}</label>
      <label>Operation<select data-hypercube-axis-field="operation">${hypercubeOperationOptions(axis.operation)}</select></label>
      <label>Start<input data-hypercube-axis-field="start" type="number" step="any" value="${escapeHtml(axis.start)}"></label>
      <label>End<input data-hypercube-axis-field="end" type="number" step="any" value="${escapeHtml(axis.end)}"></label>
      <label>Interval<input data-hypercube-axis-field="interval" type="number" min="0" step="any" value="${escapeHtml(axis.interval)}"></label>
      <button type="button" class="danger" data-remove-hypercube-axis="${escapeHtml(axis.id)}" aria-label="Remove parameter">×</button>
    </article>`;
  }).join("") : (hypercubeProject() ? "Add at least one parameter axis." : "Choose a project, then add a parameter.");
  $("hypercubeAxes").querySelectorAll("[data-hypercube-axis-field]").forEach((control) => {
    const row = control.closest("[data-hypercube-axis]"), axis = state.hypercubeAxes.find((item)=>item.id===row.dataset.hypercubeAxis), field = control.dataset.hypercubeAxisField;
    const eventName = control.tagName === "INPUT" ? "input" : "change";
    control.addEventListener(eventName, () => {
      if (field === "filename") return loadHypercubeAxisFile(axis, control.value);
      axis[field] = control.value; setHypercubeDirty(); invalidateHypercubePreview();
    });
  });
  $("hypercubeAxes").querySelectorAll("[data-retry-hypercube-file]").forEach((button)=>button.addEventListener("click",()=>{state.hypercubeFiles.delete(hypercubeFileKey(button.dataset.retryHypercubeFile));ensureHypercubeFile(button.dataset.retryHypercubeFile)}));
  $("hypercubeAxes").querySelectorAll("[data-remove-hypercube-axis]").forEach((button)=>button.addEventListener("click",()=>{
    state.hypercubeAxes=state.hypercubeAxes.filter((axis)=>axis.id!==button.dataset.removeHypercubeAxis);setHypercubeDirty();invalidateHypercubePreview();renderHypercubeAxes();renderHypercubeSharedFilters();
  }));
}
function compatibleHypercubeGeographyLevels() {
  const selectedAxes=state.hypercubeAxes.filter((axis)=>axis.filename),records=selectedAxes.map(hypercubeFileRecord).filter(Boolean);
  if (!records.length||records.length!==selectedAxes.length) return [];
  const first = records[0].geography.levels || [];
  return first.filter((level)=>level.id!=="all"&&level.compatible&&records.every((record)=>record.geography.levels?.some((item)=>item.id===level.id&&item.compatible)));
}
function renderHypercubeSharedFilters() {
  if (!$("hypercubeYear")) return;
  const selectedAxes=state.hypercubeAxes.filter((axis)=>axis.filename),records=selectedAxes.map(hypercubeFileRecord).filter(Boolean),complete=selectedAxes.length>0&&records.length===selectedAxes.length;
  if(!complete){$("hypercubeScope").hidden=true;$("hypercubeYear").disabled=true;$("hypercubeGeographyType").disabled=true;$("hypercubeLocationTrigger").disabled=true;$("hypercubeScopeSummary").textContent=selectedAxes.length?"Loading every selected parameter file before resolving shared scope…":"";return}
  const priorYear=state.hypercubeScopeDraft.year;
  const yearSets = records.map((record)=>{const index=record.csv.columns.indexOf("Year");return index<0?null:new Set(record.csv.rows.map((row)=>row[index]).filter(Boolean))}).filter(Boolean);
  const years = yearSets.length ? [...yearSets[0]].filter((year)=>yearSets.every((set)=>set.has(year))).sort() : [];
  $("hypercubeYear").innerHTML = `<option value="">All rows / timeless inputs</option>${years.map((year)=>`<option value="${escapeHtml(year)}">${escapeHtml(year)}</option>`).join("")}`;
  selectedOption($("hypercubeYear"), priorYear===""?"":years.includes(priorYear)?priorYear:years.includes("2045")?"2045":years[0]||"");
  state.hypercubeScopeDraft.year=$("hypercubeYear").value;
  const levels = compatibleHypercubeGeographyLevels(), priorType = state.hypercubeScopeDraft.geographyType;
  $("hypercubeGeographyType").innerHTML = `<option value="all">All matching rows</option>${levels.map((level)=>`<option value="${escapeHtml(level.id)}">${escapeHtml(level.label)}</option>`).join("")}`;
  selectedOption($("hypercubeGeographyType"), levels.some((level)=>level.id===priorType)?priorType:"all");
  state.hypercubeScopeDraft.geographyType=$("hypercubeGeographyType").value;
  const ready=complete&&hypercubeProjectEditable();
  $("hypercubeScope").hidden=!complete;
  $("hypercubeYear").disabled=!ready;
  $("hypercubeGeographyType").disabled=!ready;
  renderHypercubeLocations();
}
function hypercubeLocationOptions() {
  const type = $("hypercubeGeographyType").value;
  if (type === "all") return [];
  const records = state.hypercubeAxes.map(hypercubeFileRecord).filter(Boolean), maps = records.map((record)=>new Map((record.geography.levels?.find((item)=>item.id===type)?.values||[]).map((item)=>[String(item.value),item.label])));
  if (!maps.length) return [];
  return [...maps[0]].filter(([value])=>maps.every((map)=>map.has(value))).sort((a,b)=>String(a[1]).localeCompare(String(b[1]),undefined,{numeric:true}));
}
function pluralGeography(label,count){
  const noun=String(label||"location");
  if(count===1)return noun;
  if(noun.toLowerCase()==="county")return `${noun.slice(0,-1)}ies`;
  return `${noun}s`;
}
function renderHypercubeLocations() {
  const selectedAxes=state.hypercubeAxes.filter((axis)=>axis.filename),records=selectedAxes.map(hypercubeFileRecord).filter(Boolean),complete=selectedAxes.length>0&&records.length===selectedAxes.length,type = $("hypercubeGeographyType").value, options = hypercubeLocationOptions(), valid = new Set(options.map(([value])=>value)),priorCount=state.hypercubeSelectedLocations.size;
  if(!complete){setHypercubeLocationPopoverOpen(false);$("hypercubeLocationTrigger").disabled=true;return}
  state.hypercubeSelectedLocations = new Set([...state.hypercubeSelectedLocations].filter((value)=>valid.has(value)));
  if(priorCount>state.hypercubeSelectedLocations.size)notify("Some location selections were cleared because they are not compatible with every selected parameter file.","success");
  const search=state.hypercubeLocationSearch.trim().toLowerCase(),visible=options.filter(([,label])=>!search||String(label).toLowerCase().includes(search));
  $("hypercubeLocationSearch").value=state.hypercubeLocationSearch;
  $("hypercubeLocations").innerHTML = visible.map(([value,label])=>`<label class="check-option"><input type="checkbox" data-hypercube-location="${escapeHtml(value)}" ${state.hypercubeSelectedLocations.has(value)?"checked":""}><span>${escapeHtml(label)}</span></label>`).join("") || `<p class="muted">${options.length?"No matching locations.":"No locations are shared by every selected input file."}</p>`;
  $("hypercubeSelectAllLocations").disabled = !complete||!hypercubeProjectEditable()||type === "all" || !options.length;
  $("hypercubeClearLocations").disabled = !state.hypercubeSelectedLocations.size;
  const selected = options.filter(([value])=>state.hypercubeSelectedLocations.has(value)).length;
  const level=compatibleHypercubeGeographyLevels().find((item)=>item.id===type),noun=level?.label||"locations";
  $("hypercubeLocationTrigger").disabled=!complete||!hypercubeProjectEditable()||type==="all"||!options.length;
  if(type==="all"||!options.length)setHypercubeLocationPopoverOpen(false);
  else setHypercubeLocationPopoverOpen(state.hypercubeLocationPopoverOpen);
  $("hypercubeLocationTrigger").textContent=type==="all"?"All matching rows":selected===options.length&&options.length?`All ${options.length.toLocaleString()} ${pluralGeography(noun,options.length)}`:selected?`${selected.toLocaleString()} of ${options.length.toLocaleString()} ${pluralGeography(noun,options.length)}`:`Choose ${pluralGeography(noun,2).toLowerCase()}`;
  const uniqueFiles=[...new Map(selectedAxes.map((axis)=>[axis.filename,hypercubeFileRecord(axis)]).filter(([,record])=>record)).entries()];
  const year=$("hypercubeYear").value;
  const summaries=uniqueFiles.map(([filename,record])=>{
    const yearIndex=record.csv.columns.indexOf("Year"),rows=record.csv.rows.filter((row)=>!year||yearIndex<0||String(row[yearIndex])===year),target=record.geography.targetLevel||"location";
    return `${filename}: ${type==="all"?`All ${rows.length.toLocaleString()} ${target}${rows.length===1?" row":" rows"} will receive each matrix combination`:`${selected.toLocaleString()} selected ${pluralGeography(noun,selected)}`}`;
  });
  $("hypercubeScopeSummary").innerHTML=`<strong>${type==="all"?"Each combination changes every matching row; no MPO aggregation or location dimension is added.":"Each combination changes the selected shared geography scope."}</strong>${summaries.length?`<span>${summaries.map(escapeHtml).join(" · ")}</span>`:""}`;
  $("hypercubeLocations").querySelectorAll("[data-hypercube-location]").forEach((box)=>box.addEventListener("change",()=>{if(box.checked)state.hypercubeSelectedLocations.add(box.dataset.hypercubeLocation);else state.hypercubeSelectedLocations.delete(box.dataset.hypercubeLocation);setHypercubeDirty();invalidateHypercubePreview();renderHypercubeLocations()}));
}
function hypercubePayload() {
  return {projectId:state.hypercubeProjectId,year:String(state.hypercubeScopeDraft.year||""),geographyType:state.hypercubeScopeDraft.geographyType,locations:[...state.hypercubeSelectedLocations],replaceExisting:Boolean(hypercubeProject()?.hypercubes?.length),axes:state.hypercubeAxes.map(({filename,column,operation,start,end,interval})=>({filename,column,operation,start,end,interval}))};
}
function hypercubeAxisLabel(axis){return `${axis.column} (${axis.values.length})`;}
function hypercubeDiagram(preview){
  const axes=preview.axes||[],labels=axes.map(hypercubeAxisLabel),description=`${axes.length}-dimensional matrix. ${labels.join(", ")}. ${Number(preview.caseCount).toLocaleString()} total scenarios.`;
  if(axes.length===1){
    const points=axes[0].values.slice(0,9).map((value,index,values)=>{const x=32+(values.length===1?108:index*216/(values.length-1));return `<circle cx="${x}" cy="58" r="5"/><text x="${x}" y="82" text-anchor="middle">${escapeHtml(value)}</text>`}).join("");
    return `<svg class="hypercube-diagram" viewBox="0 0 280 110" role="img" aria-label="${escapeHtml(description)}"><line x1="28" y1="58" x2="252" y2="58"/>${points}<text x="140" y="18" text-anchor="middle">${escapeHtml(labels[0])}</text></svg>`;
  }
  if(axes.length===2){
    const dots=[];for(let y=0;y<Math.min(axes[1].values.length,7);y++)for(let x=0;x<Math.min(axes[0].values.length,9);x++)dots.push(`<circle cx="${48+x*22}" cy="${24+y*18}" r="3.5"/>`);
    return `<svg class="hypercube-diagram" viewBox="0 0 280 170" role="img" aria-label="${escapeHtml(description)}"><path d="M40 14v126h216"/>${dots.join("")}<text x="150" y="164" text-anchor="middle">${escapeHtml(labels[0])}</text><text x="14" y="78" text-anchor="middle" transform="rotate(-90 14 78)">${escapeHtml(labels[1])}</text></svg>`;
  }
  const layers=Math.max(1,axes.slice(3).reduce((total,axis)=>total*axis.values.length,1)),layerShapes=Array.from({length:Math.min(layers,4)},(_,index)=>{const d=index*7;return `<path d="M${62+d} ${55-d}l92 -32 64 45 -92 34zM${62+d} ${55-d}v68l64 38v-59M${218+d} ${68-d}v68l-92 25"/>`}).join("");
  return `<svg class="hypercube-diagram" viewBox="0 0 310 205" role="img" aria-label="${escapeHtml(description)}">${layerShapes}<text x="204" y="190">${escapeHtml(labels[0])}</text><text x="18" y="105" transform="rotate(-55 18 105)">${escapeHtml(labels[1])}</text><text x="236" y="72" transform="rotate(55 236 72)">${escapeHtml(labels[2])}</text>${axes.length>3?`<text x="155" y="18" text-anchor="middle">${layers.toLocaleString()} layer${layers===1?"":"s"} across ${axes.length-3} more ${axes.length-3===1?"axis":"axes"}</text>`:""}</svg>`;
}
function medianNumber(values) {
  const ordered=values.filter(Number.isFinite).sort((a,b)=>a-b);
  if(!ordered.length)return NaN;
  const middle=Math.floor(ordered.length/2);
  return ordered.length%2?ordered[middle]:(ordered[middle-1]+ordered[middle])/2;
}
function approximateDuration(milliseconds) {
  if(!Number.isFinite(milliseconds)||milliseconds<=0)return "";
  const minutes=Math.max(1,Math.round(milliseconds/60000));
  if(minutes<60)return `about ${minutes} minute${minutes===1?"":"s"}`;
  const hours=Math.round(minutes/6)/10;
  return `about ${hours.toLocaleString(undefined,{maximumFractionDigits:1})} hour${hours===1?"":"s"}`;
}
function hypercubePlanningProject() {
  return hypercubeProject() || (isHypercubeProject(state.selectedProject)?state.selectedProject:null) || (state.data?.projects||[]).find(isHypercubeProject) || null;
}
async function loadHypercubeResourceReport() {
  if(state.hypercubeResourceReport)return state.hypercubeResourceReport;
  if(state.hypercubeResourceReportPromise)return state.hypercubeResourceReportPromise;
  const pending=request("/api/storage").then((report)=>{state.hypercubeResourceReport=report;return report}).finally(()=>{if(state.hypercubeResourceReportPromise===pending)state.hypercubeResourceReportPromise=null});
  state.hypercubeResourceReportPromise=pending;
  return pending;
}
function comparableHypercubeJobs(project) {
  if(!project)return [];
  const template=String(project.template?.fingerprint||""),library=String(project.inputLibrary?.fingerprint||"");
  return (state.data?.jobs||[]).filter((job)=>job.state==="succeeded"&&job.startedAt&&job.finishedAt&&(!template||job.templateFingerprint===template)&&(!library||job.inputLibraryFingerprint===library));
}
async function hypercubeResourcePlan(project) {
  const report=await loadHypercubeResourceReport(),jobs=comparableHypercubeJobs(project),runSizes=new Map((report.runs||[]).map((item)=>[item.id,item]));
  const durations=jobs.map(jobRuntimeMilliseconds).filter((value)=>Number.isFinite(value)&&value>0),retainExports=state.data?.workspaceSettings?.retainFullExports!==false;
  const measuredSizes=jobs.map((job)=>runSizes.get(job.id)).filter(Boolean).map((item)=>Number(retainExports?item.totalBytes:item.datastoreBytes)).filter((value)=>Number.isFinite(value)&&value>0);
  const regional=project&&!isStatewideProject(project),measuredBytes=medianNumber(measuredSizes);
  const perResultBytes=Number.isFinite(measuredBytes)?measuredBytes:(retainExports&&regional?Number(report.defaultResultEstimateBytes||0):NaN);
  return {medianRuntimeMs:medianNumber(durations),runtimeSamples:durations.length,perResultBytes,storageSamples:measuredSizes.length,retainExports,storageSource:Number.isFinite(measuredBytes)?"measured":Number.isFinite(perResultBytes)?"fallback":"unavailable"};
}
function hypercubeResourceEstimateMarkup({caseCount,concurrency,project,plan,illustrative=false}) {
  const count=Math.max(1,Number(caseCount)||1),runs=Math.max(1,Math.min(count,Number(concurrency)||1)),waves=Math.ceil(count/runs),statewide=isStatewideProject(project),perRunLow=statewide?24:2.5,perRunHigh=statewide?32:3.5,memoryLow=runs*perRunLow,memoryHigh=runs*perRunHigh;
  const elapsed=Number.isFinite(plan.medianRuntimeMs)?approximateDuration(waves*plan.medianRuntimeMs):"Available after a comparable successful run";
  const disk=Number.isFinite(plan.perResultBytes)?`about ${humanBytes(plan.perResultBytes*count)}`:"Available after a comparable completed result";
  const runtimeSource=plan.runtimeSamples?`Based on ${plan.runtimeSamples.toLocaleString()} comparable completed run${plan.runtimeSamples===1?"":"s"}.`:"No comparable completed-run timing is available yet.";
  const storageSource=plan.storageSource==="measured"?`Based on ${plan.storageSamples.toLocaleString()} comparable retained result${plan.storageSamples===1?"":"s"}.`:plan.storageSource==="fallback"?"Uses the packaged regional fallback planning estimate.":"No comparable retained-result size is available yet.";
  const availableBytes=Number(state.data?.runtime?.dockerMemoryBytes||0),availableGb=availableBytes/1024**3,cap=Number(state.desktop?.resources?.memoryLimitGb||0),memoryWarning=Boolean(availableBytes&&availableGb<memoryHigh),capWarning=Boolean(cap&&cap<perRunLow);
  const warning=memoryWarning?`The ${humanBytes(availableBytes)} Docker Desktop allocation is below the upper end of this planning range.`:capWarning?`The ${cap.toLocaleString()} GB per-run limit is below the applicable ${perRunLow.toLocaleString()} GB planning minimum.`:"";
  return `<div class="hypercube-resource-heading"><strong>${illustrative?"81-case planning example":"Resource estimate"}</strong>${illustrative?"":`<span>${count.toLocaleString()} complete run${count===1?"":"s"}</span>`}</div><div class="hypercube-resource-grid"><div><small>Execution</small><strong>${waves.toLocaleString()} wave${waves===1?"":"s"} at ${runs.toLocaleString()} parallel</strong><span>${escapeHtml(elapsed)}</span></div><div><small>Peak Docker memory</small><strong>${memoryLow.toLocaleString(undefined,{maximumFractionDigits:1})}–${memoryHigh.toLocaleString(undefined,{maximumFractionDigits:1})} GB</strong><span>While ${runs.toLocaleString()} run${runs===1?" is":"s are"} active</span></div><div><small>Retained disk</small><strong>${escapeHtml(disk)}</strong><span>${plan.retainExports?"Full CSV exports retained":"Datastores only"}</span></div></div><p class="muted">${escapeHtml(runtimeSource)} ${escapeHtml(storageSource)}</p>${warning?`<p class="hypercube-resource-warning">${escapeHtml(warning)} <button type="button" class="text-button" data-open-hypercube-resources>Open Settings → Resources</button></p>`:""}`;
}
async function renderHypercubeSafetyEstimate() {
  const target=$("hypercubeSafetyEstimate");if(!target)return;
  target.textContent="Calculating a planning estimate from comparable completed runs…";
  try{const project=hypercubePlanningProject(),plan=await hypercubeResourcePlan(project);target.innerHTML=hypercubeResourceEstimateMarkup({caseCount:81,concurrency:4,project,plan,illustrative:true});bindHypercubeResourceLinks(target)}
  catch(error){target.innerHTML=`<p class="muted">The 81-case example requires 21 waves at four parallel runs and approximately 10–14 GB of active Docker memory. Timing and disk estimates are unavailable: ${escapeHtml(error.message||String(error))}</p>`}
}
function bindHypercubeResourceLinks(container) {
  container?.querySelectorAll("[data-open-hypercube-resources]").forEach((button)=>button.addEventListener("click",()=>{if($("hypercubeSafetyDialog")?.open)$("hypercubeSafetyDialog").close("back");openSettings("settingsResources")}));
}
async function renderHypercubePreviewResourceEstimate(preview) {
  const target=$("hypercubePreviewResourceEstimate"),revision=String(preview.draftRevision||"");if(!target)return;
  try{const project=hypercubeProject(),plan=await hypercubeResourcePlan(project);if(!state.hypercubePreview||String(state.hypercubePreview.draftRevision||"")!==revision)return;const configured=state.data?.runtime?.adapter==="native"?1:Number(state.desktop?.resources?.maxConcurrentRuns||state.data?.queue?.maxActive||1);target.innerHTML=hypercubeResourceEstimateMarkup({caseCount:preview.caseCount,concurrency:configured,project,plan});bindHypercubeResourceLinks(target)}
  catch(error){if(state.hypercubePreview&&String(state.hypercubePreview.draftRevision||"")===revision)target.innerHTML=`<p class="muted">Resource estimate unavailable: ${escapeHtml(error.message||String(error))}</p>`}
}
function renderHypercubePreview(preview) {
  state.hypercubePreview = preview;state.hypercubePreviewRevision=String(preview.draftRevision||"");state.hypercubePreviewToken=String(preview.previewToken||""); $("hypercubePreview").className = "hypercube-preview";
  const formula=preview.axes.map((axis)=>axis.values.length.toLocaleString()).join(" × "),scope=(preview.scopeDetails||[]).map((item)=>`${item.filename}: all ${Number(item.matchedRows).toLocaleString()} ${item.targetLevel||"location"} row${Number(item.matchedRows)===1?"":"s"}`).join(" · ");
  const examples=(preview.examples||[]).map((combination,index)=>`<li><strong>Case ${index+1}:</strong> ${combination.map((item)=>`${escapeHtml(item.column)} = ${escapeHtml(item.value)}`).join("; ")}</li>`).join("");
  $("hypercubePreview").innerHTML = `<h3>${escapeHtml(preview.name)}</h3><div class="hypercube-preview-layout"><div>${hypercubeDiagram(preview)}<p class="hypercube-formula"><strong>${escapeHtml(formula)} = ${Number(preview.caseCount).toLocaleString()}</strong> scenarios</p></div><div><div class="hypercube-preview-grid"><div><strong>${Number(preview.caseCount).toLocaleString()}</strong><small>scenarios</small></div><div><strong>${preview.axes.length}</strong><small>parameter axes</small></div><div><strong>${Number(preview.affectedCellsPerCase).toLocaleString()}</strong><small>changed cells per case</small></div></div><div class="hypercube-axis-values">${preview.axes.map((axis)=>`<div><strong>${escapeHtml(axis.filename)} / ${escapeHtml(axis.column)}</strong>: ${axis.values.map(escapeHtml).join(", ")}</div>`).join("")}</div>${scope?`<p class="hypercube-preview-scope"><strong>Scope:</strong> ${escapeHtml(scope)}. Every combination changes these rows; locations are not additional cases.</p>`:""}${examples?`<div class="hypercube-examples"><strong>Example combinations</strong><ol>${examples}</ol></div>`:""}</div></div><div id="hypercubePreviewResourceEstimate" class="hypercube-resource-estimate" role="status" aria-live="polite">Calculating time, memory, and retained-disk estimates…</div>${preview.largeMatrix?`<label class="checkbox hypercube-large-warning"><input id="acknowledgeLargeHypercube" type="checkbox"> I understand this will create exactly ${Number(preview.caseCount).toLocaleString()} scenarios.</label>`:""}`;
  $("generateHypercube").disabled = preview.largeMatrix||state.hypercubePreviewRevision!==state.hypercubeSavedRevision;
  $("acknowledgeLargeHypercube")?.addEventListener("change",(event)=>{$("generateHypercube").disabled=!event.target.checked});
  renderHypercubePreviewResourceEstimate(preview);
}
async function saveHypercubeDraft({announce=true,flush=true}={}) {
  const tracker=state.hypercubeAutosave;
  if(tracker.timer){clearTimeout(tracker.timer);tracker.timer=null}
  if(tracker.inFlight){const active=tracker.inFlight,prior=await active;if(tracker.inFlight===active)tracker.inFlight=null;refreshHypercubeSaveControls();if(state.hypercubeDirty&&!tracker.lastError)return saveHypercubeDraft({announce,flush});if(!prior||tracker.lastError)return false;return true}
  const project=hypercubeProject();if(!project)return !state.hypercubeDirty;
  if(!state.hypercubeDirty&&!tracker.lastError)return true;
  const savedChangeRevision=tracker.changeRevision,payload={...hypercubePayload(),expectedProjectUpdatedAt:project.updatedAt||""};
  tracker.lastError="";refreshHypercubeSaveControls();
  const requestPromise=(async()=>{
    try{
      const result=await post("/api/projects/hypercubes/draft",payload);
      project.hypercubeDraft=result.draft;project.updatedAt=result.projectUpdatedAt;
      state.hypercubeSavedRevision=result.draft.revision;state.hypercubeSavedComplete=Boolean(result.complete);state.hypercubePreviewRevision="";state.hypercubePreviewToken="";state.hypercubePreview=null;
      if(tracker.changeRevision===savedChangeRevision){state.hypercubeDirty=false;invalidateHypercubePreview(result.complete?"Setup saved. Preview the saved matrix before generating scenarios.":"Setup saved. Complete every parameter before previewing the matrix.")}
      if(announce)notify(result.complete?"Hypercube setup saved.":"Incomplete Hypercube setup saved.","success");
      return true;
    }catch(error){tracker.lastError=error.message||String(error);state.hypercubeDirty=true;if(announce||flush)notify(`Hypercube setup was not saved: ${tracker.lastError}`,"error");return false}
  })();
  tracker.inFlight=requestPromise;refreshHypercubeSaveControls();
  const saved=await requestPromise;
  if(tracker.inFlight===requestPromise)tracker.inFlight=null;
  refreshHypercubeSaveControls();
  if(saved&&state.hypercubeDirty){if(flush)return saveHypercubeDraft({announce:false,flush:true});scheduleHypercubeAutosave()}
  return saved&&!state.hypercubeDirty;
}
async function flushHypercubeAutosave() {
  if(!state.hypercubeDirty&&!state.hypercubeAutosave.inFlight)return true;
  const saved=await saveHypercubeDraft({announce:false,flush:true});
  if(!saved)notify("Automatic saving failed. Stay on Hypercube and retry saving before leaving.","error");
  return saved;
}
async function previewHypercube() {
  if(state.hypercubeDirty||!state.hypercubeSavedRevision)return notify("Wait for the Hypercube setup to finish saving before previewing it.","error");
  setBusy($("previewHypercube"),true,"Previewing…");
  try { renderHypercubePreview(await post("/api/projects/hypercubes/preview",{projectId:state.hypercubeProjectId,draftRevision:state.hypercubeSavedRevision})); }
  catch(error){invalidateHypercubePreview(error.message);notify(error.message,"error")}
  finally{setBusy($("previewHypercube"),false)}
}
async function pollHypercubeOperation() {
  if (!state.hypercubeOperationId) return;
  try {
    const operation=await request(`/api/projects/hypercubes/status?id=${encodeURIComponent(state.hypercubeOperationId)}`);
    $("hypercubeProgress").hidden=false;$("hypercubeProgress").textContent=operation.message;
    if(["waiting","running","cancelling"].includes(operation.state)){setTimeout(pollHypercubeOperation,400);return}
    $("cancelHypercube").hidden=true;$("generateHypercube").disabled=true;state.hypercubeOperationId="";state.hypercubePreviewToken="";
    if(operation.state==="succeeded"){
      state.reviewHypercubeId=operation.result.hypercube.id;state.hypercubeHydratedProjectId="";state.hypercubeSavedRevision="";state.hypercubePreviewRevision="";state.hypercubeDirty=false;await refreshState({quiet:true});selectProject(operation.result.projectId);switchCreateSubpage("createReview",false);notify(operation.message,"success");
    }else notify(operation.message,operation.state==="cancelled"?"success":"error");
  }catch(error){state.hypercubeOperationId="";$("cancelHypercube").hidden=true;notify(error.message,"error")}
}
async function generateHypercube() {
  if(!state.hypercubePreview||state.hypercubeDirty||state.hypercubePreviewRevision!==state.hypercubeSavedRevision)return notify("Wait for automatic saving, then preview the current Hypercube setup before generating scenarios.","error");
  if(state.hypercubePreview.replacingExisting&&!await confirmWorkbench("Replace this project’s current matrix and all of its unrun generated cases? This cannot be undone."))return;
  const payload={projectId:state.hypercubeProjectId,draftRevision:state.hypercubeSavedRevision,previewToken:state.hypercubePreviewToken,acknowledgeLargeMatrix:!state.hypercubePreview.largeMatrix||Boolean($("acknowledgeLargeHypercube")?.checked)};
  setBusy($("generateHypercube"),true,"Starting…");
  try{const operation=await post("/api/projects/hypercubes/start",payload);state.hypercubeOperationId=operation.id;setBusy($("generateHypercube"),false);$("generateHypercube").disabled=true;$("cancelHypercube").hidden=false;$("hypercubeProgress").hidden=false;$("hypercubeProgress").textContent=operation.message;pollHypercubeOperation()}
  catch(error){notify(error.message,"error");setBusy($("generateHypercube"),false)}
}
function clearEditorFile() {
  state.editorFileName = ""; state.csv = null; state.editorGeography = null; state.editorBaselineRows = []; state.editorOriginalRows = []; state.editorUndo = []; state.editorRedo = []; state.editorManualEdit = false; setEditorDirty(false);
  $("editorNotes").value = ""; primeNoteAutosave("file", "");
  $("editorFile").value = "";
  $("editorLocationField").innerHTML = `<option value="">Choose an input file</option>`;
  $("editorYear").innerHTML = `<option value="">Choose an input file</option>`;
  $("editorOperation").value = ""; $("editorValue").value = ""; $("editorValue").placeholder = ""; $("editorLocationSearch").value = "";
  $("editorLocations").innerHTML = `<p class="muted">Choose an input file.</p>`;
  $("editorColumns").innerHTML = `<p class="muted">Choose an input file.</p>`;
  $("editorSavedScopeSummary").hidden = true; $("editorSavedScopeSummary").textContent = "";
  ["editorLocationField","editorLocationSearch","editorYear","editorOperation","editorValue","editorSelectAllLocations","editorSelectAllColumns","clearEditorColumns","applyEditorChange","clearEditorSelections","resetEditorFile","undoEditorChange","redoEditorChange"].forEach((id) => { $(id).disabled = true; });
  $("csvTableWrap").innerHTML = `<p class="empty-state">Choose an input file to preview rows.</p>`;
}
function selectProject(projectId, rerender = true) {
  const changed = state.selectedProject?.id !== projectId;
  state.selectedProject = state.data.projects.find((item) => item.id === projectId) || null;
  $("editorProjectSelect").value = state.selectedProject?.id || "";
  $("reviewProjectSelect").value = state.selectedProject?.id || "";
  if (!state.selectedProject) { $("inputEditor").hidden = true; state.review = null; renderReview(); return; }
  if (changed) { state.editorVariationId = ""; clearEditorFile(); clearBatchDraftState(""); state.review = null; state.reviewHypercubeId = ""; }
  if(isHypercubeProject(state.selectedProject)) {
    $("editorProjectSelect").value="";$("inputEditor").hidden=true;
    $("editorProjectFacts").textContent="This is a dedicated Hypercube project. Open it from Setup or the Hypercube tab.";
    syncMenuContext();if(rerender){renderProjects();renderEditorProjectSelect()}return;
  }
  $("inputEditor").hidden = false;
  $("editorProjectFacts").textContent = `${projectPackageName(state.selectedProject)} · ${state.selectedProject.variations.length} scenarios`;
  const baseline = state.selectedProject.baseline || {strategy:"fresh"};
  const baselineName = baselineDisplayName(state.selectedProject);
  const existingResult = state.data?.catalog?.find((item) => item.id === baseline.datastoreId);
  const baselineDescription = baseline.strategy === "fresh"
    ? "Untouched model and Input Library values"
    : `${escapeHtml(existingResult?.displayLabel || existingResult?.label || "Existing completed result")} · ${escapeHtml(baseline.compatibility || "unverified")}`;
  $("baselineCard").innerHTML = `<div class="baseline-card-header"><strong>${escapeHtml(baselineName)} <span class="pill">Read only</span></strong><button id="renameBaseline" class="text-button" type="button">Rename</button></div><small>${baselineDescription}</small>`;
  $("renameBaseline").addEventListener("click", openBaselineRenameDialog);
  if (!state.selectedProject.variations.some((item) => item.id === state.editorVariationId)) state.editorVariationId = state.selectedProject.variations[0]?.id || "";
  const library = state.data.inputLibraries.find((item) => item.id === state.selectedProject.inputLibrary.id);
  const previous = state.editorFileName;
  $("editorFile").innerHTML = `<option value="">Choose input file</option>${(library?.files || []).map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("")}`;
  if ((library?.files || []).includes(previous)) $("editorFile").value = previous;
  renderScenarioTree(); renderEditorPage();
  syncMenuContext();
  if (rerender) { renderProjects(); renderEditorProjectSelect(); }
}
function renderScenarioTree() {
  const project = state.selectedProject; if (!project) return;
  $("duplicateEditorScenario").disabled = !project.variations.length;
  $("editorScenarioTree").innerHTML = project.variations.map((scenario) => {
    const active = scenario.id === state.editorVariationId;
    const source = scenarioEditSource(scenario);
    return `<div class="scenario-group"><div class="scenario-title-row ${active ? "active" : ""}">
      <div class="scenario-name-field ${source === "unavailable" ? "" : "has-edit-source-marker"}"><input data-scenario-name="${escapeHtml(scenario.id)}" value="${escapeHtml(scenario.name)}" aria-label="Scenario name">${editSourceMarker(source)}</div>
      <button data-scenario-tools="${escapeHtml(scenario.id)}" title="Open scenario tools">›</button>
      <button class="remove-editor-scenario" data-delete-scenario="${escapeHtml(scenario.id)}" title="Remove scenario">×</button></div>
      <div class="file-edit-branch">${(scenario.overlays || []).map((file) => `<div class="file-edit-row ${active && state.editorFileName === file.fileName && state.editorMode === "file" ? "active" : ""}"><button data-open-file-change="${escapeHtml(scenario.id)}" data-file-name="${escapeHtml(file.fileName)}"><span>${escapeHtml(file.fileName)}</span>${editSourceMarker(editSourceValue(file.editOperations || []),false)}</button><button class="remove-file-edit" data-remove-file-change="${escapeHtml(scenario.id)}" data-file-name="${escapeHtml(file.fileName)}" title="Remove saved file change">×</button></div>`).join("")}<button class="new-file-edit" data-new-file="${escapeHtml(scenario.id)}">+ New File</button></div></div>`;
  }).join("") || `<p class="muted">No editable scenarios yet.</p>`;
  document.querySelectorAll("[data-scenario-tools]").forEach((button) => button.addEventListener("click", () => guardUnsaved(() => openScenarioTools(button.dataset.scenarioTools))));
  document.querySelectorAll("[data-new-file]").forEach((button) => button.addEventListener("click", () => guardUnsaved(() => openNewFile(button.dataset.newFile))));
  document.querySelectorAll("[data-open-file-change]").forEach((button) => button.addEventListener("click", () => guardUnsaved(() => openOverlay(button.dataset.openFileChange, button.dataset.fileName))));
  document.querySelectorAll("[data-scenario-name]").forEach((input) => input.addEventListener("change", () => renameVariation(input.dataset.scenarioName, input.value)));
  document.querySelectorAll("[data-delete-scenario]").forEach((button) => button.addEventListener("click", () => guardUnsaved(() => deleteVariation(button.dataset.deleteScenario))));
  document.querySelectorAll("[data-remove-file-change]").forEach((button) => button.addEventListener("click", () => guardUnsaved(() => removeOverlay(button.dataset.removeFileChange, button.dataset.fileName))));
}
function renderEditorPage() {
  const scenario = activeEditorVariation(), hasScenario = Boolean(scenario);
  $("editorEmpty").hidden = hasScenario;
  $("editorNotesPanel").hidden = !hasScenario;
  $("scenarioTools").hidden = !hasScenario || state.editorMode !== "scenario";
  $("fileEditorPage").hidden = !hasScenario || state.editorMode !== "file";
  if (!scenario) return;
  if (state.noteAutosave.scenario.context !== noteContext("scenario")) { $("scenarioNote").value = scenario.scenarioNote || ""; primeNoteAutosave("scenario", $("scenarioNote").value); }
  const showScenarioNote = state.editorMode === "scenario";
  const showFileNote = state.editorMode === "file" && Boolean(state.editorFileName);
  $("scenarioNoteField").hidden = !showScenarioNote;
  $("fileNoteField").hidden = !showFileNote;
  $("editorNotesTitle").textContent = showScenarioNote ? "Scenario note" : "File note";
  $("editorNotesGuidance").textContent = showScenarioNote
    ? "This scenario note saves automatically and does not save pending batch changes."
    : showFileNote
      ? "This file note saves automatically and does not save pending CSV edits."
      : "Choose an input file to add or edit its file note.";
  if (state.editorMode === "scenario") {
    $("scenarioToolsTitle").textContent = `Batch change ${scenario.name}`;
    if (!batchSessionMatches(scenario.id)) resetBatchDraft(scenario.id);
  }
  else { $("editorProjectName").textContent = `${scenario.name}${state.editorFileName ? ` · ${state.editorFileName}` : ""}`; }
}
function openScenarioTools(scenarioId) {
  state.editorVariationId = scenarioId; state.editorMode = "scenario"; clearEditorFile();
  if (!batchSessionMatches(scenarioId)) resetBatchDraft(scenarioId);
  renderScenarioTree(); renderEditorPage();
}
function openNewFile(scenarioId) { state.editorVariationId = scenarioId; state.editorMode = "file"; clearEditorFile(); renderScenarioTree(); renderEditorPage(); }
async function openOverlay(scenarioId, filename) { state.editorVariationId = scenarioId; state.editorMode = "file"; $("editorFile").value = filename; renderScenarioTree(); renderEditorPage(); await loadEditorFile(filename); }

async function loadEditorFile(requestedFilename = "") {
  const filename = requestedFilename || $("editorFile").value;
  if (!filename || !state.selectedProject || !state.editorVariationId) return;
  setBusy($("saveOverlay"), true, "Loading…");
  try {
    const [csvPayload, baselinePayload, geography] = await Promise.all([request(editorFileUrl(filename)), request(baselineEditorFileUrl(filename)), request(`/api/geography-options?projectId=${encodeURIComponent(state.selectedProject.id)}&filename=${encodeURIComponent(filename)}`)]);
    state.editorFileName = filename; state.csv = csvPayload; state.editorGeography = geography; state.editorSelectedLocations.clear(); state.editorManualEdit = false;
    state.editorBaselineRows = baselinePayload.rows.map((row) => [...row]);
    state.editorOriginalRows = csvPayload.rows.map((row) => [...row]); state.editorUndo = []; state.editorRedo = [];
    const overlayRecord=activeEditorVariation()?.overlays?.find((item)=>item.fileName===filename);
    state.editorSavedOperations=structuredClone(overlayRecord?.editOperations||[]);state.editorPendingOperations=structuredClone(state.editorSavedOperations);
    $("editorNotes").value = activeEditorVariation()?.notes?.[filename] || ""; primeNoteAutosave("file", $("editorNotes").value);
    const draft = loadEditorDraft("file", filename) || savedFileDraft(state.editorSavedOperations) || {};
    renderEditorControls(draft); renderCsv(); renderScenarioTree(); renderEditorPage(); setEditorDirty(false); persistFileDraft();
  } catch (error) { notify(error.message, "error"); } finally { setBusy($("saveOverlay"), false); $("saveOverlay").disabled = !state.editorDirty; }
}
function selectedGeographyLevel(payload, select) { return !select.value || select.value === MIXED_EDITOR_VALUE ? null : payload?.levels?.find((level) => level.id === select.value) || null; }
function renderEditorControls(draft = {}) {
  if (!state.csv) return;
  ["editorLocationField","editorLocationSearch","editorYear","editorOperation","editorValue","editorSelectAllLocations","editorSelectAllColumns","clearEditorColumns","applyEditorChange","clearEditorSelections","resetEditorFile"].forEach((id) => { $(id).disabled = false; });
  const levels = state.editorGeography?.levels || [{id:"all",label:"All locations",values:[]}];
  state.editorScopeUnavailable = Boolean(draft.scopeUnavailable);
  $("editorLocationField").innerHTML = `${state.editorScopeUnavailable ? '<option value="">Choose location type</option>' : ""}${levels.map((level) => `<option value="${escapeHtml(level.id)}">${escapeHtml(level.label)}</option>`).join("")}`;
  const preferred = state.editorScopeUnavailable ? "" : draft.geographyType || (levels.some((level) => level.id === "county") ? "county" : levels[0]?.id || "all");
  setSelectDraftValue($("editorLocationField"), preferred, "Mixed saved scopes");
  state.editorSelectedLocations = new Set((draft.locations || []).map(String));
  state.editorMixedScopes = structuredClone(draft.mixedScopes || []);
  const columns = numericColumns(state.csv);
  const selectedColumns = new Set((draft.columns || []).filter((name) => columns.includes(name)));
  $("editorColumns").innerHTML = columns.map((name) => `<label class="check-option"><input type="checkbox" data-editor-column="${escapeHtml(name)}" ${selectedColumns.has(name)?"checked":""}><span>${escapeHtml(name)}</span></label>`).join("") || `<p class="muted">No editable numeric columns.</p>`;
  document.querySelectorAll("[data-editor-column]").forEach((box) => box.addEventListener("change", () => { syncEditorColumnSelectAll(); persistFileDraft(); }));
  syncEditorColumnSelectAll();
  const yearIndex = state.csv.columns.indexOf("Year"), years = yearIndex >= 0 ? [...new Set(state.csv.rows.map((row) => row[yearIndex]).filter(Boolean))].sort() : [""];
  $("editorYear").innerHTML = years.map((year) => `<option>${escapeHtml(year)}</option>`).join("");
  $("editorYear").value = years.includes(String(draft.year || "")) ? String(draft.year) : years.includes("2045") ? "2045" : years[0] || "";
  setSelectDraftValue($("editorOperation"), Object.prototype.hasOwnProperty.call(draft,"operation") ? draft.operation : "", "Mixed saved changes");
  $("editorValue").value = draft.mixedValue ? "" : String(draft.value ?? "");
  $("editorValue").placeholder = draft.mixedValue ? "Mixed" : "";
  $("editorLocationSearch").value = draft.locationSearch || "";
  updateFileDraftGuidance({...draft,mixedScopes:state.editorMixedScopes});
  renderEditorLocations(); updateEditorHistoryButtons();
}
function renderEditorLocations() {
  if (!state.csv) return;
  const level = selectedGeographyLevel(state.editorGeography, $("editorLocationField")), allValues = level?.values || [], valid = new Set(allValues.map((item) => item.value)), query = $("editorLocationSearch").value.trim().toLowerCase();
  state.editorSelectedLocations = new Set([...state.editorSelectedLocations].filter((value) => valid.has(value)));
  const values = allValues.filter((item) => !query || item.label.toLowerCase().includes(query));
  $("editorLocations").innerHTML = !$("editorLocationField").value ? `<p class="muted">Choose a location type.</p>` : $("editorLocationField").value === MIXED_EDITOR_VALUE ? `<p class="muted">Saved changes use multiple location scopes. Choose a location type to edit.</p>` : $("editorLocationField").value === "all" ? `<p class="muted">All locations are included.</p>` : values.map((item) => `<label class="check-option"><input type="checkbox" data-editor-location="${escapeHtml(item.value)}" ${state.editorSelectedLocations.has(item.value) ? "checked" : ""}><span>${escapeHtml(item.label)}</span></label>`).join("") || `<p class="muted">No matching locations.</p>`;
  document.querySelectorAll("[data-editor-location]").forEach((box) => box.addEventListener("change", () => { if (box.checked) state.editorSelectedLocations.add(box.dataset.editorLocation); else state.editorSelectedLocations.delete(box.dataset.editorLocation); syncEditorLocationSelectAll(allValues); renderCsv(); persistFileDraft(); }));
  syncEditorLocationSelectAll(allValues);
}
function syncEditorLocationSelectAll(values = selectedGeographyLevel(state.editorGeography, $("editorLocationField"))?.values || []) {
  const box = $("editorSelectAllLocations"), count = values.filter((item) => state.editorSelectedLocations.has(item.value)).length;
  box.disabled = $("editorLocationField").value === "all" || !values.length; box.checked = values.length > 0 && count === values.length; box.indeterminate = count > 0 && count < values.length;
}
function rowMatchesEditor(row) {
  // Keep the loaded CSV visible before the user chooses a location. Applying
  // a change still requires an explicit selection for non-"all" levels.
  const selected = [...state.editorSelectedLocations]; if ($("editorLocationField").value === "all" || !selected.length) return true;
  const level = selectedGeographyLevel(state.editorGeography, $("editorLocationField")); if (!level) return false;
  const allowed = new Set((level.values || []).filter((item) => selected.includes(item.value)).flatMap((item) => item.targetValues || [item.value]));
  const geoIndex = state.csv.columns.indexOf(state.editorGeography?.targetField || "Geo");
  return geoIndex >= 0 && allowed.has(String(row[geoIndex]));
}
function selectedEditorColumns() { return [...document.querySelectorAll("[data-editor-column]:checked")].map((box) => box.dataset.editorColumn); }
function syncEditorColumnSelectAll() {
  const boxes = [...document.querySelectorAll("[data-editor-column]")], selected = boxes.filter((box) => box.checked).length, control = $("editorSelectAllColumns");
  control.disabled = !boxes.length; control.checked = boxes.length > 0 && selected === boxes.length; control.indeterminate = selected > 0 && selected < boxes.length;
}
function renderCsv() {
  const csv = state.csv; if (!csv) return;
  $("csvTableWrap").innerHTML = `<table><thead><tr>${csv.columns.map((item) => `<th>${escapeHtml(item)}</th>`).join("")}</tr></thead><tbody>${csv.rows.map((row, rowIndex) => `<tr ${rowMatchesEditor(row) ? "" : "hidden"}>${csv.columns.map((column, columnIndex) => { const editable = !protectedColumn(column), unsaved = editable && String(row[columnIndex] ?? "") !== String(state.editorOriginalRows[rowIndex]?.[columnIndex] ?? ""), saved = editable && String(state.editorOriginalRows[rowIndex]?.[columnIndex] ?? "") !== String(state.editorBaselineRows[rowIndex]?.[columnIndex] ?? ""), changeClass = unsaved ? "changed-cell" : saved ? "saved-change-cell" : "", changeTitle = unsaved ? "Unsaved direct edit" : saved ? "Saved scenario change from baseline" : ""; return `<td contenteditable="${editable}" class="${editable ? "" : "readonly-cell"} ${changeClass}" ${changeTitle ? `title="${changeTitle}"` : ""} data-row="${rowIndex}" data-column="${columnIndex}">${escapeHtml(roundedValue(row[columnIndex], column))}</td>`; }).join("")}</tr>`).join("")}</tbody></table>`;
  $("csvTableWrap").querySelectorAll('td[contenteditable="true"]').forEach((cell) => {
    const row = Number(cell.dataset.row), columnIndex = Number(cell.dataset.column), column = state.csv.columns[columnIndex];
    cell.addEventListener("focus", () => { cell.textContent = state.csv.rows[row][columnIndex] ?? ""; });
    cell.addEventListener("input", () => { state.csv.rows[row][columnIndex] = cell.textContent; state.editorManualEdit = true; recomputeEditorDirty(); });
    cell.addEventListener("blur", () => { cell.textContent = roundedValue(state.csv.rows[row][columnIndex], column); });
  });
}
async function applyEditorChange() {
  const columns = selectedEditorColumns(), operation = $("editorOperation").value, valueText = $("editorValue").value.trim(), value = Number(valueText); if (!columns.length || !operation || !valueText || !Number.isFinite(value) || operation === MIXED_EDITOR_VALUE) return notify("Choose one or more columns, a specific operation, and a numeric value.", "error");
  if (state.editorManualEdit || state.editorDirty) return notify("Save or revert direct table edits before applying a calculated change.", "error");
  if (!$("editorLocationField").value || $("editorLocationField").value === MIXED_EDITOR_VALUE) return notify("Choose one location type before applying another change.", "error");
  if ($("editorLocationField").value !== "all" && !state.editorSelectedLocations.size) return notify("Choose at least one location or use Select all locations.", "error");
  const button = $("applyEditorChange");
  if (button.disabled) return;
  setBusy(button, true, "Checking…");
  try {
    const yearIndex = state.csv.columns.indexOf("Year"), targetYear = $("editorYear").value;
    let overlap = 0;
    state.csv.rows.forEach((row, rowIndex) => {
      if (!rowMatchesEditor(row) || (yearIndex >= 0 && row[yearIndex] !== targetYear)) return;
      columns.forEach((column) => {
        const index = state.csv.columns.indexOf(column);
        if (Number.isFinite(Number(row[index])) && rowsDifferAt(state.csv.rows, state.editorBaselineRows, rowIndex, index)) overlap++;
      });
    });
    const basis = await chooseOverlappingOperation(overlap);
    if (basis === "cancel") return;
    setBusy(button, false); setBusy(button, true, "Applying and saving…");
    const beforeRows=editorSnapshot(),nextRows=beforeRows.map((row)=>[...row]);
    let changed = 0;
    nextRows.forEach((row,rowIndex) => { if (!rowMatchesEditor(row) || (yearIndex >= 0 && row[yearIndex] !== targetYear)) return; columns.forEach((column) => { const index = state.csv.columns.indexOf(column), sourceRow=basis==="baseline"?state.editorBaselineRows[rowIndex]:row,current=Number(sourceRow?.[index]); if (!Number.isFinite(current)) return; let next=calculateValue(current,operation,value); if(column.toLowerCase().includes("prop"))next=Math.min(1,next); row[index]=calculatedValue(next,"singleFile",state.csv,column); changed++; }); });
    const nextOperation={operationId:newOperationId("single-file"),source:"single_file",basis,columns:[...columns],operation,value,year:targetYear,allLocations:$("editorLocationField").value==="all",geographyType:$("editorLocationField").value,geographyLabel:$("editorLocationField").value==="all"?"all locations":`${state.editorSelectedLocations.size} selected locations`,locations:[...state.editorSelectedLocations],rounding:operationRounding(state.csv,columns,"singleFile")};
    const operations=operationsWithBaselineOverride(structuredClone(state.editorPendingOperations),nextOperation);
    await post("/api/overlays",{projectId:state.selectedProject.id,variationId:state.editorVariationId,filename:state.csv.filename,columns:state.csv.columns,rows:nextRows,editOperations:operations});
    state.editorUndo.push(beforeRows);state.editorRedo=[];state.csv.rows=nextRows;state.editorOriginalRows=nextRows.map((row)=>[...row]);state.editorSavedOperations=structuredClone(operations);state.editorPendingOperations=structuredClone(operations);state.editorManualEdit=false;setEditorDirty(false);
    persistFileDraft();renderCsv();updateEditorHistoryButtons();notify(`Applied and saved changes to ${changed.toLocaleString()} values${basis==="baseline"?" from the untouched baseline":""}.`,"success");
    await refreshState({quiet:true});
  } catch(error) { notify(error.message,"error"); }
  finally { setBusy(button, false); $("saveOverlay").disabled=!state.editorDirty; }
}
function undoEditor() { const rows = state.editorUndo.pop(); if (!rows) return; state.editorRedo.push(editorSnapshot()); state.csv.rows = rows; state.editorManualEdit=true; renderCsv(); updateEditorHistoryButtons(); recomputeEditorDirty(); }
function redoEditor() { const rows = state.editorRedo.pop(); if (!rows) return; state.editorUndo.push(editorSnapshot()); state.csv.rows = rows; state.editorManualEdit=true; renderCsv(); updateEditorHistoryButtons(); recomputeEditorDirty(); }
async function saveFileChanges(showNotice = true) {
  if (!state.csv || !state.editorVariationId) return false;
  const applyButton = $("applyEditorChange");
  setBusy($("saveOverlay"), true, "Saving…");
  setButtonAvailability(applyButton, false, "File save is in progress.");
  try {
    const hasNewOperation = state.editorPendingOperations.length > state.editorSavedOperations.length;
    const operations = state.editorManualEdit && !hasNewOperation
      ? [...state.editorPendingOperations, {operationId:newOperationId("manual"),source:"single_file",operation:"manual",columns:[]}]
      : state.editorPendingOperations;
    await post("/api/overlays", {projectId:state.selectedProject.id, variationId:state.editorVariationId, filename:state.csv.filename, columns:state.csv.columns, rows:state.csv.rows,editOperations:operations});
    state.editorOriginalRows = editorSnapshot(); state.editorSavedOperations=structuredClone(operations); state.editorPendingOperations=structuredClone(operations); state.editorManualEdit=false; setEditorDirty(false); persistFileDraft(); renderCsv();
    if (showNotice) notify("File changes saved to this scenario.", "success");
    await refreshState({quiet:true}); return true;
  } catch (error) { notify(error.message, "error"); return false; } finally { setBusy($("saveOverlay"), false); $("saveOverlay").disabled = !state.editorDirty; setButtonAvailability(applyButton, true); }
}

function renderRunProjects() {
  const projects = state.data?.projects || [];
  const prior = $("runProject").value;
  $("runProject").innerHTML = `<option value="">Choose project</option>${projects.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join("")}`;
  selectedOption($("runProject"), prior || state.selectedProject?.id || "");
  renderRunSelections();
}

function renderRunResourceGuide(project) {
  const guide=$("runResourceGuide");
  if(!project){guide.hidden=true;guide.textContent="";return}
  const cap=Number(state.desktop?.resources?.memoryLimitGb||0);
  const mode=state.data?.queue?.modeLock||state.desktop?.resources?.defaultRunMode||"queued";
  const warnings=[];
  if(isStatewideProject(project)){
    if(mode==="parallel")warnings.push("Statewide models should begin with one active run.");
    if(cap&&cap<24)warnings.push(`The ${cap.toLocaleString()} GB per-run limit is below the provisional statewide estimate.`);
  }else if(cap&&cap<2.5){
    warnings.push(`The ${cap.toLocaleString()} GB per-run limit is below the MPO/regional planning range.`);
  }
  const lead=warnings.length?warnings.join(" "):"Parallel runs share Docker memory.";
  guide.classList.toggle("warning",Boolean(warnings.length));
  guide.innerHTML=`<span>${escapeHtml(lead)}</span><span>${warnings.length?"Review concurrency and memory guidance in":"Adjust concurrency and view memory guidance in"}</span><button type="button" class="text-button" data-open-run-resources>Settings → Resources</button>`;
  guide.querySelector("[data-open-run-resources]")?.addEventListener("click",()=>openSettings("settingsResources").catch(error=>notify(error.message||String(error),"error")));
  guide.hidden=false;
}

function renderRunSelections() {
  const project = state.data?.projects.find((item) => item.id === $("runProject").value);
  if (!project) {
    $("runSelections").className = "selection-grid empty-state run-empty-state";
    $("runSelections").textContent = "";
    $("runSelectionSummary").className = "run-setup-helper";
    $("runSelectionSummary").textContent = "Choose a project to select baseline and scenarios.";
    $("openRunDialog").disabled = true;
    renderRunResourceGuide(null);
    return;
  }
  renderRunResourceGuide(project);
  $("runSelectionSummary").className = "muted";
  if (state.runSelectionProjectId !== project.id) {
    state.runSelectionProjectId = project.id;
    state.runSelectedVariationIds = new Set(project.variations.filter((item)=>item.resultStatus!=="current").map((item)=>item.id));
    state.runForceRerunIds = new Set();
    state.runBaselineSelected = Boolean(project.requiresBaseline);
  }
  const availableIds = new Set(project.variations.map((item) => item.id));
  state.runSelectedVariationIds = new Set([...state.runSelectedVariationIds].filter((id) => availableIds.has(id)));
  const baselineName = baselineDisplayName(project);
  if(project.requiresBaseline)state.runBaselineSelected=true;
  const baseline = `<label class="selection-option"><input type="checkbox" data-baseline ${state.runBaselineSelected ? "checked" : ""} ${project.requiresBaseline?"disabled":""}><span><strong>${escapeHtml(baselineName)}</strong><small>${project.requiresBaseline?"Required — no current compatible baseline exists":"Current result available; select to run again"}</small></span></label>`;
  const hypercubeGroups = (project.hypercubes || []).length ? `<div class="run-hypercube-groups"><strong>Hypercube groups</strong>${project.hypercubes.map((hypercube)=>{const ids=(hypercube.scenarioIds||[]).filter((id)=>availableIds.has(id)),all=ids.length>0&&ids.every((id)=>state.runSelectedVariationIds.has(id));return `<button type="button" class="secondary" data-run-hypercube="${escapeHtml(hypercube.id)}">${all?"Clear":"Select"} ${escapeHtml(hypercube.name)} (${ids.length})</button>`}).join("")}<button type="button" class="text-button" data-clear-run-selection>Clear all</button></div>` : "";
  $("runSelections").className = "selection-grid";
  $("runSelections").innerHTML = hypercubeGroups + baseline + project.variations.map((variant) => `<label class="selection-option"><input type="checkbox" data-run-variation="${escapeHtml(variant.id)}" ${state.runSelectedVariationIds.has(variant.id) ? "checked" : ""}><span><strong>${escapeHtml(variant.name)}</strong><small>${variant.overlays.length} edited input files · ${variant.resultStatus==="current"?"Current result available — select to run again":variant.resultStatus==="runtime_differs"?"Result uses a different runtime":variant.resultStatus==="previous"?"Inputs changed since the previous result":"No reusable result"}</small></span></label>`).join("");
  $("runSelections").querySelector("[data-baseline]")?.addEventListener("change", (event) => { state.runBaselineSelected = event.target.checked;if(event.target.checked&&!project.requiresBaseline)state.runForceRerunIds.add("baseline");else state.runForceRerunIds.delete("baseline"); updateRunSelectionSummary(); });
  $("runSelections").querySelectorAll("[data-run-variation]").forEach((input) => input.addEventListener("change", () => {
    const variation=project.variations.find((item)=>item.id===input.dataset.runVariation);
    if (input.checked){state.runSelectedVariationIds.add(input.dataset.runVariation);if(variation?.resultStatus==="current")state.runForceRerunIds.add(input.dataset.runVariation)}
    else{state.runSelectedVariationIds.delete(input.dataset.runVariation);state.runForceRerunIds.delete(input.dataset.runVariation)}
    updateRunSelectionSummary();
  }));
  $("runSelections").querySelectorAll("[data-run-hypercube]").forEach((button)=>button.addEventListener("click",()=>{const hypercube=project.hypercubes.find((item)=>item.id===button.dataset.runHypercube),ids=(hypercube?.scenarioIds||[]).filter((id)=>availableIds.has(id)),all=ids.length&&ids.every((id)=>state.runSelectedVariationIds.has(id));ids.forEach((id)=>all?state.runSelectedVariationIds.delete(id):state.runSelectedVariationIds.add(id));renderRunSelections()}));
  $("runSelections").querySelector("[data-clear-run-selection]")?.addEventListener("click",()=>{state.runSelectedVariationIds.clear();state.runForceRerunIds.clear();state.runBaselineSelected=Boolean(project.requiresBaseline);renderRunSelections()});
  updateRunSelectionSummary();
}

function selectedRunNames() {
  const project = state.data?.projects.find((item) => item.id === $("runProject").value);
  if (!project) return [];
  const names = [];
  if (state.runBaselineSelected) names.push(baselineDisplayName(project));
  project.variations.forEach((item) => { if (state.runSelectedVariationIds.has(item.id)) names.push(item.name); });
  return names;
}

function updateRunSelectionSummary() {
  const names = selectedRunNames();
  $("runSelectionSummary").className = "muted";
  $("runSelectionSummary").textContent = names.length ? (names.length > 10 ? `${names.length.toLocaleString()} scenarios selected.` : `${names.length} selected: ${names.join(", ")}`) : "Nothing selected — choose each run explicitly";
  $("openRunDialog").disabled = !names.length;
}

function jobDisplayName(job) {
  if (!job?.baseline) return job?.variationName || "Run";
  const project = state.data?.projects?.find((item) => item.id === job.projectId);
  return baselineDisplayName(project);
}

function formatDuration(milliseconds) {
  if (!Number.isFinite(milliseconds) || milliseconds < 0) return "—";
  const seconds = Math.max(0, Math.floor(milliseconds / 1000));
  const hours = Math.floor(seconds / 3600), minutes = Math.floor((seconds % 3600) / 60), remainder = seconds % 60;
  if (hours) return `${hours}h ${minutes}m ${remainder}s`;
  if (minutes) return `${minutes}m ${remainder}s`;
  return `${remainder}s`;
}

function jobRuntime(job) {
  if (!job?.startedAt) return "Not started";
  const started = new Date(job.startedAt).getTime();
  const finished = job.finishedAt ? new Date(job.finishedAt).getTime() : Date.now();
  return Number.isFinite(started) && Number.isFinite(finished) ? formatDuration(finished - started) : "—";
}

function jobRuntimeMilliseconds(job) {
  if (!job?.startedAt) return NaN;
  const started = new Date(job.startedAt).getTime();
  const finished = job.finishedAt ? new Date(job.finishedAt).getTime() : Date.now();
  return Number.isFinite(started) && Number.isFinite(finished) ? Math.max(0, finished - started) : NaN;
}

function renderJobActions(job) {
  const active = Boolean(job && activeJobStates.has(job.state) && job.state !== "stopping");
  const retry = Boolean(job && job.state === "failed" && job.retryable !== false);
  const waiting = job?.state === "waiting", cleanup = job?.state === "cleanup_failed";
  const removing = waiting && state.pendingJobActions.has(`/api/runs/queue/remove:${job.id}`);
  const hasRunnable = runnableJobs().length > 0;
  const stopAllBusy = state.stopAllPending && unresolvedRunQueueJobs().length > 0;
  $("jobActions").innerHTML = `<button id="cancelJob" class="danger" title="${escapeHtml(stopRunTooltip)}" aria-label="${escapeHtml(stopRunTooltip)}" ${active ? "" : "disabled"}>${job?.state === "stopping" ? "Stopping…" : "Stop Run"}</button><button id="stopAllJobs" class="danger" title="${escapeHtml(stopAllRunsTooltip)}" aria-label="${escapeHtml(stopAllRunsTooltip)}" aria-pressed="${stopAllBusy ? "true" : "false"}" ${hasRunnable && !stopAllBusy ? "" : "disabled"}>${stopAllBusy ? "Stopping All…" : "Stop All Runs"}</button>${waiting ? `<button id="removeQueuedJob" class="secondary" ${removing ? "disabled" : ""}>${removing ? "Removing…" : "Remove from Queue"}</button>` : ""}${retry ? `<button id="retryJob" class="secondary">Retry</button>` : ""}${cleanup ? `<button id="retryCleanup" class="secondary">Retry Cleanup</button>` : ""}`;
  if (active) $("cancelJob").addEventListener("click", () => jobAction("/api/runs/cancel", job.id));
  if (hasRunnable && !stopAllBusy) $("stopAllJobs").addEventListener("click", stopAllRuns);
  if (waiting && !removing) $("removeQueuedJob").addEventListener("click", () => jobAction("/api/runs/queue/remove", job.id));
  if (retry) $("retryJob").addEventListener("click", () => retryRun(job).catch(error=>notify(error.message||String(error),"error")));
  if (cleanup) $("retryCleanup").addEventListener("click", () => jobAction("/api/runs/cleanup/retry", job.id));
}

function renderJobs() {
  if (state.draggedJobId) return;
  const jobs = [...(state.data?.jobs || [])];
  state.queueRevision = Number(state.data?.queue?.revision || state.queueRevision || 0);
  const active = jobs.filter((job) => activeJobStates.has(job.state)).sort((a,b) => new Date(a.startedAt || a.createdAt || 0)-new Date(b.startedAt || b.createdAt || 0));
  const waiting = jobs.filter((job) => job.state === "waiting").sort((a,b) => (a.queuePosition ?? 1e9)-(b.queuePosition ?? 1e9));
  const history = jobs.filter((job) => !activeJobStates.has(job.state) && job.state !== "waiting").sort((a,b) => new Date(b.finishedAt || b.createdAt || 0)-new Date(a.finishedAt || a.createdAt || 0));
  const ordered = [...active, ...waiting, ...history];
  const activeBatches = new Set(jobs.filter((job) => !terminalJobStates.has(job.state)).map((job) => job.batchId));
  $("jobList").classList.toggle("empty-state", !jobs.length);
  const card = (job) => {
    const draggable = job.state === "waiting" ? `data-queue-job="${escapeHtml(job.id)}" aria-label="Drag ${escapeHtml(jobDisplayName(job))} to reorder queued runs" title="Drag this queued run to reorder. Right-click for queue options."` : terminalJobStates.has(job.state) ? `data-history-job="${escapeHtml(job.id)}" title="Right-click for history options"` : "";
    return `<article class="item-card job-card ${state.selectedJob === job.id ? "selected" : ""} ${activeBatches.has(job.batchId) ? "active-batch" : ""} ${escapeHtml(job.state)}" data-job="${escapeHtml(job.id)}" ${draggable}>
      <header><strong>${escapeHtml(jobDisplayName(job))}</strong><span class="job-card-metrics">${job.state === "waiting" ? `<span class="pill">Queued #${job.queuePosition || "—"}</span>` : ""}<span class="job-runtime">${escapeHtml(jobRuntime(job))}</span><span class="status ${escapeHtml(job.state)}">${escapeHtml(job.state.replace("_", " "))}${job.state === "waiting" ? `<small class="queue-drag-cue">Drag to reorder</small>` : ""}</span></span></header>
      <small>${escapeHtml(job.projectName)} · ${formatTime(job.createdAt)}</small><small>${escapeHtml(jobDisplayMessage(job))}</small></article>`;
  };
  const maxActive = Number(state.data?.queue?.maxActive || 2), modeLock = state.data?.queue?.modeLock;
  const modeLabel = modeLock ? ` · ${modeLock === "queued" ? "Queued" : "Parallel"} workspace mode` : "";
  $("jobList").innerHTML = ordered.length ? `${active.length ? `<div class="job-group-label">Active · ${active.length} of ${maxActive} runtime slot${maxActive === 1 ? "" : "s"}${modeLabel}</div>${active.map(card).join("")}` : ""}${waiting.length ? `<div class="job-group-label">Queue · drag cards to reorder${modeLabel}</div>${waiting.map(card).join("")}` : ""}${history.length ? `<div class="job-group-label">History</div>${history.map(card).join("")}` : ""}` : "No jobs yet.";
  document.querySelectorAll("[data-job]").forEach((element) => element.addEventListener("click", () => {
    if (element.dataset.suppressClick === "true") return;
    selectJob(element.dataset.job);
  }));
  document.querySelectorAll("[data-queue-job]").forEach((element) => element.addEventListener("contextmenu", (event) => openQueuedJobMenu(event, element.dataset.queueJob)));
  document.querySelectorAll("[data-history-job]").forEach((element) => element.addEventListener("contextmenu", (event) => openJobHistoryMenu(event, element.dataset.historyJob)));
  enableQueueDragging(waiting);
  if (state.selectedJob && !jobs.some((job) => job.id === state.selectedJob)) { state.selectedJob = null; if (state.logSource) state.logSource.close(); $("runLog").textContent = ""; $("logTitle").textContent = "R console"; }
  renderJobActions(jobs.find((job) => job.id === state.selectedJob));
  renderActiveJobTabs();
}

function closeJobHistoryMenu() {
  $("jobHistoryMenu")?.remove();
}

function openJobHistoryMenu(event, jobId) {
  event.preventDefault(); event.stopPropagation(); closeJobHistoryMenu();
  const job = state.data?.jobs?.find((item) => item.id === jobId);
  if (!job || !terminalJobStates.has(job.state)) return;
  const menu = document.createElement("div"); menu.id = "jobHistoryMenu"; menu.className = "job-history-menu"; menu.setAttribute("role", "menu");
  const canRetry=job.state==="failed"&&job.retryable!==false;
  menu.innerHTML = `${canRetry?`<button type="button" role="menuitem" data-retry-history>Retry Run…</button><small>${memoryFailure(job)?"Review memory settings before retrying this run.":"Queue a new run with the same project and scenario."}</small><div class="menu-divider" aria-hidden="true"></div>`:""}<button type="button" role="menuitem" data-remove-history>Hide / Remove from History</button><small>${job.resultPath || job.datastoreId ? "Completed results will be preserved." : "The run log and history record will be removed."}</small>`;
  document.body.appendChild(menu);
  const left = Math.min(event.clientX, window.innerWidth - menu.offsetWidth - 10), top = Math.min(event.clientY, window.innerHeight - menu.offsetHeight - 10);
  menu.style.left = `${Math.max(8, left)}px`; menu.style.top = `${Math.max(8, top)}px`;
  menu.querySelector("[data-retry-history]")?.addEventListener("click", () => {
    closeJobHistoryMenu();
    retryRun(job).catch(error=>notify(error.message||String(error),"error"));
  });
  menu.querySelector("[data-remove-history]").addEventListener("click", async () => {
    closeJobHistoryMenu();
    if (!await confirmWorkbench(`Remove ${jobDisplayName(job)} from Run History?\n\nIts history record and run log will be deleted. Completed datastore and comparison results will be kept.`)) return;
    try {
      if (state.selectedJob === jobId) {
        state.logSource?.close(); state.selectedJob = null; $("runLog").textContent = ""; $("logTitle").textContent = "R console";
      }
      const result = await post("/api/runs/history/remove", {jobId});
      notify(result.resultsPreserved ? "Run history removed; completed results were preserved." : "Run history removed.", "success");
      await refreshState({quiet:true});
    } catch (error) { notify(error.message, "error"); }
  });
}

function openQueuedJobMenu(event, jobId) {
  event.preventDefault(); event.stopPropagation(); closeJobHistoryMenu();
  const job = state.data?.jobs?.find((item) => item.id === jobId);
  if (!job || job.state !== "waiting") return;
  const removing = state.pendingJobActions.has(`/api/runs/queue/remove:${jobId}`);
  const menu = document.createElement("div"); menu.id = "jobHistoryMenu"; menu.className = "job-history-menu"; menu.setAttribute("role", "menu");
  menu.innerHTML = `<button type="button" role="menuitem" class="danger-menu-item" ${removing ? "disabled" : ""}>${removing ? "Removing…" : "Remove from Queue"}</button><small>No completed results are affected. Only this waiting run is removed from the queue.</small>`;
  document.body.appendChild(menu);
  const left = Math.min(event.clientX, window.innerWidth - menu.offsetWidth - 10), top = Math.min(event.clientY, window.innerHeight - menu.offsetHeight - 10);
  menu.style.left = `${Math.max(8, left)}px`; menu.style.top = `${Math.max(8, top)}px`;
  if (!removing) {
    menu.querySelector("button").addEventListener("click", () => {
      closeJobHistoryMenu();
      jobAction("/api/runs/queue/remove", jobId);
    });
  }
}

document.addEventListener("pointerdown", (event) => { if (!event.target.closest("#jobHistoryMenu")) closeJobHistoryMenu(); });
document.addEventListener("scroll", closeJobHistoryMenu, true);

async function submitQueueOrder(jobIds) {
  try { const queue = await post("/api/runs/queue/reorder", {jobIds, revision:state.queueRevision}); state.queueRevision = queue.revision; await refreshState({quiet:true}); }
  catch (error) { notify(error.message, "error"); await refreshState({quiet:true}); }
}

function enableQueueDragging(waiting) {
  const waitingIds = waiting.map((job) => job.id);
  document.querySelectorAll("[data-queue-job]").forEach((card) => {
    card.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || waitingIds.length < 2) return;
      const draggedId = card.dataset.queueJob || "";
      const startX = event.clientX, startY = event.clientY;
      let dragging = false, insertionIndex = waitingIds.indexOf(draggedId);
      const controller = new AbortController();
      const line = document.createElement("div");
      line.className = "queue-insertion-line";
      line.setAttribute("aria-hidden", "true");

      const positionLine = (clientY) => {
        const remainingCards = [...document.querySelectorAll("[data-queue-job]")].filter((item) => item !== card);
        insertionIndex = remainingCards.findIndex((item) => clientY < item.getBoundingClientRect().top + item.getBoundingClientRect().height / 2);
        if (insertionIndex < 0) insertionIndex = remainingCards.length;
        if (insertionIndex < remainingCards.length) remainingCards[insertionIndex].before(line);
        else (remainingCards.at(-1) || card).after(line);
      };
      const finish = async (cancelled = false) => {
        controller.abort();
        line.remove();
        card.classList.remove("queue-dragging");
        state.draggedJobId = "";
        if (!dragging) return;
        card.dataset.suppressClick = "true";
        setTimeout(() => { delete card.dataset.suppressClick; }, 0);
        if (cancelled) return;
        const next = waitingIds.filter((id) => id !== draggedId);
        next.splice(Math.max(0, Math.min(next.length, insertionIndex)), 0, draggedId);
        if (next.some((id, index) => id !== waitingIds[index])) await submitQueueOrder(next);
      };
      const move = (moveEvent) => {
        if (!dragging && Math.hypot(moveEvent.clientX - startX, moveEvent.clientY - startY) < 6) return;
        if (!dragging) {
          dragging = true;
          state.draggedJobId = draggedId;
          card.classList.add("queue-dragging");
          // Window-level move/up listeners already keep the drag alive. Capturing
          // the pointer after the movement threshold is crossed is invalid
          // in some WebView2 pointer sequences and used to crash the first drag.
        }
        moveEvent.preventDefault();
        positionLine(moveEvent.clientY);
      };
      window.addEventListener("pointermove", move, {signal: controller.signal});
      window.addEventListener("pointerup", () => finish(false), {signal: controller.signal, once: true});
      window.addEventListener("pointercancel", () => finish(true), {signal: controller.signal, once: true});
    });
  });
}

function consoleBatchJobs() {
  const jobs = state.data?.jobs || [], selected = jobs.find((job) => job.id === state.selectedJob);
  const activeBatchIds = new Set(jobs.filter((job) => !terminalJobStates.has(job.state)).map((job) => job.batchId));
  const batchId = selected && activeBatchIds.has(selected.batchId) ? selected.batchId : state.consoleBatchId && activeBatchIds.has(state.consoleBatchId) ? state.consoleBatchId : jobs.filter((job) => activeBatchIds.has(job.batchId)).sort((a,b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))[0]?.batchId;
  if (batchId) return jobs.filter((job) => job.batchId === batchId).sort((a,b) => {
    const rank = (job) => activeJobStates.has(job.state) ? 0 : job.state === "waiting" ? 1 : 2;
    return rank(a)-rank(b) || (a.queuePosition ?? 1e9)-(b.queuePosition ?? 1e9) || new Date(a.createdAt || 0)-new Date(b.createdAt || 0);
  });
  return selected ? [selected] : [];
}
function renderActiveJobTabs() {
  const tabs = consoleBatchJobs(), container = $("activeJobTabs");
  container.hidden = tabs.length < 2;
  container.innerHTML = tabs.map((job) => `<button class="job-tab ${job.id === state.selectedJob ? "selected" : ""} ${job.id === state.consoleAutoFollowJob ? "auto-following" : ""} ${state.logUnread.has(job.id) ? "unread" : ""} ${job.state === "failed" ? "failed" : ""}" data-log-tab="${escapeHtml(job.id)}" type="button">${escapeHtml(jobDisplayName(job))} · ${escapeHtml(job.state)}${job.id === state.consoleAutoFollowJob ? " · live" : ""}</button>`).join("");
  document.querySelectorAll("[data-log-tab]").forEach((button) => button.addEventListener("click", () => selectJob(button.dataset.logTab)));
}

function followActiveConsoleJob() {
  const jobs=state.data?.jobs||[],selected=jobs.find((job)=>job.id===state.selectedJob),batchId=state.consoleBatchId||selected?.batchId||"";
  const candidates=jobs.filter((job)=>activeJobStates.has(job.state)&&job.state!=="stopping"&&(!batchId||job.batchId===batchId)).sort((a,b)=>new Date(a.startedAt||a.createdAt||0)-new Date(b.startedAt||b.createdAt||0));
  const active=candidates[0];
  if(!active){state.consoleAutoFollowJob="";return}
  const prior=state.lastActiveConsoleByBatch[active.batchId]||"";
  state.consoleAutoFollowJob=active.id;
  if(prior===active.id&&state.selectedJob)return;
  state.lastActiveConsoleByBatch[active.batchId]=active.id;
  state.consoleManualSelection=false;
  if(state.selectedJob!==active.id)selectJob(active.id,{automatic:true});
}
function appendJobLog(jobId, text) {
  if (!text) return;
  const limit = 200000, current = (state.logBuffers[jobId] || "") + text;
  state.logBuffers[jobId] = current.length > limit ? current.slice(current.length - limit) : current;
  if (jobId !== state.selectedJob) state.logUnread.add(jobId);
}
function updateJobSnapshot(job) {
  if (!job || !state.data?.jobs) return;
  const index = state.data.jobs.findIndex((item) => item.id === job.id);
  if (index >= 0) state.data.jobs[index] = job;
}
async function pollBackgroundJobLogs() {
  for (const job of consoleBatchJobs()) {
    if (job.id === state.selectedJob || terminalJobStates.has(job.state)) continue;
    try {
      const chunk = await request(`/api/run-log?id=${encodeURIComponent(job.id)}&offset=${state.logOffsets[job.id] || 0}`);
      appendJobLog(job.id, chunk.text || ""); state.logOffsets[job.id] = chunk.offset || state.logOffsets[job.id] || 0; updateJobSnapshot(chunk.job);
      if (chunk.terminal) await refreshState({quiet:true});
    } catch (_) { /* The next poll reconnects. */ }
  }
  renderJobs();
  followActiveConsoleJob();
}

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function renderDatastores() {
  const datastores = state.data?.catalog || [];
  $("datastoreCount").textContent = datastores.length;
  $("datastoreList").classList.toggle("empty-state", !datastores.length);
  const grouped = new Map();
  datastores.forEach((item) => { const group=item.displayProjectName || item.projectName || "Previously registered"; if(!grouped.has(group))grouped.set(group,[]); grouped.get(group).push(item); });
  $("datastoreList").innerHTML = datastores.length ? [...grouped.entries()].map(([group,items]) => `<section class="datastore-group"><h4>${escapeHtml(group)}</h4>${items.map((item) => `
    <article class="item-card datastore-card"><header><strong>${escapeHtml(item.displayLabel || item.label)}</strong><span class="datastore-card-actions"><span class="status ${item.verification === "verified" ? "succeeded" : ""}">${escapeHtml(item.verification || "unverified")}</span>${item.role === "imported" ? `<span class="pill">Legacy · read only</span>` : ""}</span></header>
      <small>${escapeHtml(item.displayProjectName || item.projectName || (item.role === "imported" ? "Previously registered result" : "Completed result"))} · ${escapeHtml(item.displayVariationName || item.variationName || item.role || "")}</small>
      <small>${escapeHtml(item.packageDisplayName || "VisionEval model")} · ${formatTime(item.completedAt || item.registeredAt)}</small>
    </article>`).join("")}</section>`).join("") : "No completed datastores registered.";
  const options = [...grouped.entries()].map(([group,items])=>`<optgroup label="${escapeHtml(group)}">${items.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.displayLabel || item.label)}${item.verification !== "verified" ? " ⚠" : ""}</option>`).join("")}</optgroup>`).join("");
  const values = [$("referenceDatastore").value, $("comparisonOne").value, $("comparisonTwo").value];
  $("referenceDatastore").innerHTML = `<option value="">Choose reference</option>${options}`;
  $("comparisonOne").innerHTML = `<option value="">None — view reference only</option>${options}`;
  $("comparisonTwo").innerHTML = `<option value="">None</option>${options}`;
  [$("referenceDatastore"), $("comparisonOne"), $("comparisonTwo")].forEach((select, index) => selectedOption(select, values[index]));
  const mapValues=[$("mapReference")?.value,$("mapComparison")?.value];
  if($("mapReference")){
    $("mapReference").innerHTML=`<option value="">Choose reference</option>${options}`;
    $("mapComparison").innerHTML=`<option value="">Choose comparison</option>${options}`;
    selectedOption($("mapReference"),mapValues[0]);selectedOption($("mapComparison"),mapValues[1]);
    if(!$("mapReference").value||!$("mapComparison").value){$("mapTable").innerHTML='<option value="">Choose two results first</option>';$("mapVariable").innerHTML='';$("mapYear").innerHTML='';$("generateMap").disabled=true;}
  }
  const selectedLibrary=(state.data?.inputLibraries||[]).find((item)=>item.id===$("librarySelect")?.value);
  const selectedTemplate=(state.data?.templates||[]).find((item)=>item.id===selectedLibrary?.pairedTemplateId);
  const baselines=datastores.filter((item)=>item.role==="baseline"&&item.verification==="verified"&&item.templateFingerprint===selectedTemplate?.fingerprint&&item.inputLibraryFingerprint===selectedLibrary?.fingerprint).sort((a,b)=>String(b.completedAt||"").localeCompare(String(a.completedAt||"")));
  $("existingBaseline").innerHTML=baselines.length?baselines.map((item)=>`<option value="${escapeHtml(item.id)}">${escapeHtml(item.displayLabel || item.label)}</option>`).join(""):`<option value="">No compatible completed baseline</option>`;
}

async function submitForm(form, action, busyLabel = "Working…") {
  const button = form.querySelector('button[type="submit"], button:not([type])');
  setBusy(button, true, busyLabel);
  try { await action(); } catch (error) { notify(error.message, "error"); } finally { setBusy(button, false); }
}

$("installRegionPackage").addEventListener("click", (event) => openPackageSourceDialog(event.currentTarget, true));
$("choosePackageZip").addEventListener("click", () => installSelectedPackage("choose_package"));
$("choosePackageFolder").addEventListener("click", () => installSelectedPackage("choose_package_folder"));
$("regionPackage").addEventListener("change", (event) => {
  state.regionBuilderPackageId = event.target.value;
  state.regionBuilderReference = null;
  state.regionBuilderSources = null;
  state.regionBuilderRegions = null;
  state.regionBuilderSourceLibraryId = "";
  state.regionBuilderRegionId = "";
  state.regionBuilderPreview = null;
  state.regionMapData = null;
  state.regionMapKey = "";
  state.regionMapView = null;
  state.regionMapSelectedRegionId = "";
  state.regionMapScene = null;
  state.regionMapLoadState = "idle";
  state.regionMapLoadError = "";
  state.regionMapLoadPromise = null;
  $("regionName").value = "";
  $("regionState").value = "";
  state.regionBuilderIdentityKey = "";
  state.regionBuilderIdentityDrafts = {official:null, custom:null};
  resetRegionBuilderGeography();
  renderRegionBuilder();
});
$("regionSourceLibrary").addEventListener("change", (event) => { state.regionBuilderSourceLibraryId = event.target.value; state.regionBuilderPreview = null; resetRegionBuilderGeography(); renderRegionBuilderMode(); });
$("regionDefinition").addEventListener("change", (event) => {
  state.regionBuilderRegionId = event.target.value;
  state.regionBuilderPreview = null;
  const selectedRegion = (state.regionBuilderRegions?.regions || []).find((item) => item.id === event.target.value);
  state.regionBuilderIdentityKey = "";
  resetRegionBuilderGeography();
  initializeRegionBuilderIdentity(selectedRegion, true);
  renderRegionBuilderMode();
  updateRegionBuilderAvailability();
});
["regionName", "regionState"].forEach((id) => $(id).addEventListener("input", () => { state.regionBuilderIdentityDrafts[state.regionBuilderGeographyMode] = currentRegionBuilderIdentity(); state.regionBuilderPreview = null; renderRegionBuilderPreview(); updateRegionBuilderAvailability(); }));
$("useOfficialRegionGeography").addEventListener("click", () => switchRegionBuilderIdentity("official"));
$("customizeRegionGeography").addEventListener("click", () => switchRegionBuilderIdentity("custom"));
$("editCustomRegionGeography").addEventListener("click", openRegionGeographyDialog);
[$("customRegionMpoLayer"), $("customRegionAzoneLayer"), $("customRegionBzoneLayer"), $("customRegionAzoneLabels"), $("customRegionAzoneIdLabels"), $("customRegionBzoneLabels")].forEach((control) => control.addEventListener("change", renderRegionGeographySelectionMap));
$("zoomInRegionGeography").addEventListener("click", () => zoomCustomRegionMap(.8));
$("zoomOutRegionGeography").addEventListener("click", () => zoomCustomRegionMap(1.25));
$("virginiaRegionGeography").addEventListener("click", () => { state.regionBuilderGeographyView = {x:0,y:0,width:1000,height:620}; renderRegionGeographySelectionMap(); });
$("fitRegionGeography").addEventListener("click", () => {
  const data = state.regionMapData, selected = state.regionBuilderDraftBzones;
  if (!data || !selected.size) { state.regionBuilderGeographyView = {x:0,y:0,width:1000,height:620}; renderRegionGeographySelectionMap(); return; }
  const fullBounds = regionMapBounds([data.azones, data.bzones]), projection = regionMapProjection(fullBounds);
  const features = (data.bzones?.features || []).filter((feature) => selected.has(String(feature.properties?.bzoneId || feature.properties?.GEOID || "")));
  const fit = regionMapFeaturesView(features, projection);
  state.regionBuilderGeographyView = fit || {x:0,y:0,width:1000,height:620};
  renderRegionGeographySelectionMap();
});
$("regionGeographySearch").addEventListener("input", (event) => { state.regionBuilderGeographyQuery = event.target.value; renderRegionGeographyDialog(); });
$("clearRegionGeography").addEventListener("click", () => { state.regionBuilderDraftBzones.clear(); renderRegionGeographyDialog(); });
$("selectVisibleAzones").addEventListener("click", () => {
  const query = state.regionBuilderGeographyQuery.trim().toLowerCase();
  (state.regionBuilderGeographyOptions?.azones || []).filter((item) => !query || `${item.name} ${item.fips}`.toLowerCase().includes(query)).forEach((item) => regionGeographyAzoneBzones(item).forEach((id) => state.regionBuilderDraftBzones.add(id)));
  renderRegionGeographyDialog();
});
$("regionGeographyDialog").addEventListener("change", async (event) => {
  const azone = event.target.closest("[data-region-azone]");
  if (azone) {
    const item = state.regionBuilderGeographyOptions.azones.find((value) => value.fips === azone.dataset.regionAzone);
    regionGeographyAzoneBzones(item).forEach((id) => azone.checked ? state.regionBuilderDraftBzones.add(id) : state.regionBuilderDraftBzones.delete(id));
    renderRegionGeographyDialog();
    return;
  }
  const bzone = event.target.closest("[data-region-bzone]");
  if (bzone) {
    if (bzone.checked) state.regionBuilderDraftBzones.add(bzone.dataset.regionBzone); else state.regionBuilderDraftBzones.delete(bzone.dataset.regionBzone);
    renderRegionGeographyDialog();
    return;
  }
  if (event.target.id === "regionGeographyCsv" && event.target.files?.[0]) {
    try {
      state.regionBuilderDraftBzones = parseRegionGeographyCsv(await event.target.files[0].text());
      state.regionBuilderGeographyQuery = "";
      $("regionGeographySearch").value = "";
      renderRegionGeographyDialog();
      notify(`Loaded ${state.regionBuilderDraftBzones.size.toLocaleString()} Bzones from CSV.`, "success");
    } catch (error) {
      event.target.value = "";
      notify(error.message, "error");
    }
  }
});
$("applyRegionGeography").addEventListener("click", async (event) => {
  if (!state.regionBuilderDraftBzones.size) return;
  state.regionBuilderSelectedBzones = new Set(state.regionBuilderDraftBzones);
  state.regionBuilderGeographyMode = "custom";
  state.regionBuilderPreview = null;
  state.regionBuilderPreviewError = "";
  renderRegionGeographySummary();
  renderRegionBuilderPreview();
  $("regionGeographyDialog").close();
  switchCreateSubpage("createDevelop", false);
  updateRegionBuilderAvailability();
  if (!$("regionName").value.trim()) {
    $("regionOutputOptions").open = true;
    $("regionName").focus();
    notify("Enter a custom region name, then choose Preview region.", "error");
    return;
  }
  await previewRegionBuild(event.currentTarget);
});
$("viewRegionMap").addEventListener("click", openRegionMap);
$("regionBuilderPreview").addEventListener("click", (event) => { if (event.target.closest("[data-open-region-map]")) openRegionMap(); });
$("regionMapRegion").addEventListener("change", () => updateRegionMapSelection({zoom: true}));
$("regionMapDialog").addEventListener("close", syncMenuContext);
document.querySelectorAll("[data-region-map-layer]").forEach((input) => input.addEventListener("change", applyRegionMapLayers));
$("regionMapIdLabels").addEventListener("change", () => { updateRegionMapNameLabels(); updateRegionMapIdLabels(); });
$("regionMapNameLabels").addEventListener("change", () => { updateRegionMapNameLabels(); updateRegionMapIdLabels(); });
$("closeRegionMapInspector").addEventListener("click", clearRegionMapInspector);
$("resetRegionMap").addEventListener("click", () => {
  const scene = state.regionMapScene;
  if (scene) {
    scene.fullView = regionMapFullView(scene.projection);
    setRegionMapView(scene.fullView);
  }
});
$("fitRegionMap").addEventListener("click", () => { if (state.regionMapScene?.focusView) setRegionMapView(state.regionMapScene.focusView); });
$("zoomInRegionMap").addEventListener("click", () => zoomRegionMap(0.76));
$("zoomOutRegionMap").addEventListener("click", () => zoomRegionMap(1.32));

function regionMapClientPoint(event) {
  const svg = $("regionMapCanvas").querySelector("[data-region-map-svg]");
  const matrix = svg?.getScreenCTM();
  if (!svg || !matrix) return null;
  const point = svg.createSVGPoint();
  point.x = event.clientX; point.y = event.clientY;
  const mapped = point.matrixTransform(matrix.inverse());
  return {x: mapped.x, y: mapped.y};
}

$("regionMapCanvas").addEventListener("wheel", (event) => {
  if (!state.regionMapView) return;
  event.preventDefault();
  const factor = Math.min(1.24, Math.max(0.8, Math.exp(event.deltaY * 0.0012)));
  zoomRegionMap(factor, regionMapClientPoint(event));
}, { passive: false });
$("regionMapCanvas").addEventListener("dblclick", (event) => { event.preventDefault(); zoomRegionMap(0.64, regionMapClientPoint(event)); });
$("regionMapCanvas").addEventListener("pointerdown", (event) => {
  if (!state.regionMapView || !$("regionMapCanvas").querySelector("[data-region-map-svg]")) return;
  if (event.button !== 0) return;
  $("regionMapCanvas").focus({preventScroll: true});
  $("regionMapCanvas").setPointerCapture(event.pointerId);
  $("regionMapCanvas").classList.add("dragging");
  state.regionMapPointerMoved = false;
  state.regionMapView.drag = { x: event.clientX, y: event.clientY, view: {...state.regionMapView} };
});
$("regionMapCanvas").addEventListener("pointermove", (event) => {
  const drag = state.regionMapView?.drag;
  if (!drag) return;
  if (Math.hypot(event.clientX - drag.x, event.clientY - drag.y) > 3) state.regionMapPointerMoved = true;
  const rect = $("regionMapCanvas").getBoundingClientRect();
  setRegionMapView({
    x: drag.view.x - (event.clientX - drag.x) * drag.view.width / rect.width,
    y: drag.view.y - (event.clientY - drag.y) * drag.view.height / rect.height,
    width: drag.view.width,
    height: drag.view.height,
  });
  state.regionMapView.drag = drag;
});
const stopRegionMapDrag = () => { if (state.regionMapView) delete state.regionMapView.drag; $("regionMapCanvas").classList.remove("dragging"); };
$("regionMapCanvas").addEventListener("pointerup", stopRegionMapDrag);
$("regionMapCanvas").addEventListener("pointercancel", stopRegionMapDrag);
$("regionMapCanvas").addEventListener("click", (event) => {
  if (state.regionMapPointerMoved) { state.regionMapPointerMoved = false; return; }
  const hit = regionMapHitFeature(regionMapClientPoint(event));
  if (hit) inspectRegionMapFeature(hit.type, hit.id, hit.feature);
  else clearRegionMapInspector();
});
$("regionMapCanvas").addEventListener("keydown", (event) => {
  const view = state.regionMapView;
  if (!view) return;
  const keys = {ArrowLeft: [-0.1, 0], ArrowRight: [0.1, 0], ArrowUp: [0, -0.1], ArrowDown: [0, 0.1]};
  if (event.key === "+" || event.key === "=") { event.preventDefault(); zoomRegionMap(0.76); return; }
  if (event.key === "-") { event.preventDefault(); zoomRegionMap(1.32); return; }
  if (!keys[event.key]) return;
  event.preventDefault();
  const [dx, dy] = keys[event.key];
  setRegionMapView({x: view.x + view.width * dx, y: view.y + view.height * dy, width: view.width, height: view.height});
});
$("previewRegionBuild").addEventListener("click", (event) => previewRegionBuild(event.currentTarget));
$("buildRegionAssets").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  setBusy(button, true, "Building…");
  try {
    const buildRequest = regionBuilderPayload();
    const result = await post("/api/region-builder/build", buildRequest);
    state.pendingProjectSetup = {
      templateId: result.modelTemplate.id,
      templateName: result.modelTemplate.name,
      inputLibraryId: result.inputLibrary.id,
      inputLibraryName: result.inputLibrary.name || result.inputLibrary.id,
      regionName: buildRequest.regionName,
      projectName: buildRequest.regionName,
    };
    state.regionBuilderPreview = null;
    await refreshState({ quiet: true });
    selectedOption($("librarySelect"), result.inputLibrary.id);
    switchCreateSubpage("createSetup", false);
    renderSetup();
    $("projectName").focus();
    notify(`Built ${result.modelTemplate.name}.`, "success");
  } catch (error) {
    notify(error.message, "error");
  } finally {
    setBusy(button, false);
  }
});

document.querySelectorAll('input[name="baselineStrategy"]').forEach((input) => input.addEventListener("change", () => {
  $("existingBaseline").disabled = $("existingBaselineStrategy").disabled || document.querySelector('input[name="baselineStrategy"]:checked').value !== "existing";
}));
document.querySelectorAll('input[name="projectType"]').forEach((input)=>input.addEventListener("change",renderSetup));
$("librarySelect").addEventListener("change",() => {
  const selectedLibrary = (state.data?.inputLibraries || []).find((item) => item.id === $("librarySelect").value);
  if (state.pendingProjectSetup && (
    $("librarySelect").value !== state.pendingProjectSetup.inputLibraryId
    || selectedLibrary?.pairedTemplateId !== state.pendingProjectSetup.templateId
  )) state.pendingProjectSetup = null;
  renderSetup();
});

$("projectForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  submitForm(form, async () => {
    const selectedLibrary = (state.data?.inputLibraries || []).find((item) => item.id === $("librarySelect").value);
    if (state.pendingProjectSetup && (selectedLibrary?.pairedTemplateId !== state.pendingProjectSetup.templateId || $("librarySelect").value !== state.pendingProjectSetup.inputLibraryId)) {
      throw new Error("The exact model package built for this region is no longer selected. Rebuild or refresh the region assets before creating the project.");
    }
    const strategy = document.querySelector('input[name="baselineStrategy"]:checked').value;
    const projectType = document.querySelector('input[name="projectType"]:checked')?.value || "standard";
    const project = await post("/api/projects", {
      name: $("projectName").value,
      inputLibraryId: $("librarySelect").value,
      projectType,
      baseline: strategy === "fresh" ? { strategy } : { strategy, datastoreId: $("existingBaseline").value, compatibility: "unverified" },
      variations: [],
    });
    state.pendingProjectSetup = null;
    form.reset();
    notify(`Created ${project.name}.`, "success");
    await refreshState({ quiet: true });
    selectProject(project.id);
    if(projectType==="hypercube") {
      state.hypercubeProjectId=project.id;state.hypercubeHydratedProjectId="";state.hypercubeFiles=new Map();state.hypercubeSafetyAcknowledged=true;renderHypercubeSetup();switchCreateSubpage("createHypercube",false);
    } else switchCreateSubpage("createEditor", false);
  }, "Creating…");
});

$("saveOverlay").addEventListener("click", () => saveFileChanges());

function renderBatchFiles(scenarioId = state.editorVariationId) {
  if (!batchSessionMatches(scenarioId)) { resetBatchDraft(scenarioId); return; }
  state.batchScenarioId = scenarioId;
  const library = state.data.inputLibraries.find((item) => item.id === state.selectedProject.inputLibrary.id);
  $("batchFileChecklist").innerHTML = (library?.files || []).map((name) => `<label class="check-option"><input type="checkbox" data-batch-file="${escapeHtml(name)}" ${state.batchSelectedFiles.has(name)?"checked":""}><span>${escapeHtml(name)}</span></label>`).join("");
  document.querySelectorAll("[data-batch-file]").forEach((input) => {
    // WebKit can retain a checkbox property when identical markup is replaced.
    // The session draft is authoritative, especially after switching scenarios.
    input.checked = state.batchSelectedFiles.has(input.dataset.batchFile);
    input.addEventListener("change",()=>{if(input.checked)state.batchSelectedFiles.add(input.dataset.batchFile);else{state.batchSelectedFiles.delete(input.dataset.batchFile);state.batchSelectedColumns.delete(input.dataset.batchFile)}persistBatchDraft();renderBatchColumns()});
  });
  if (state.batchSelectedFiles.size) renderBatchColumns();
  else {
    $("batchColumnChecklist").innerHTML = `<p class="muted">Select one or more files.</p>`;
    renderBatchLocationTypes();
    syncBatchSelectAll();
  }
}
function batchSessionPrefix(scenarioId = state.editorVariationId) {
  return `${state.selectedProject?.id || ""}:${scenarioId}:`;
}
function batchSessionMatches(scenarioId = state.editorVariationId) {
  return state.batchScenarioId === scenarioId && state.batchSessionOwner.startsWith(batchSessionPrefix(scenarioId));
}
function clearBatchDraftState(scenarioId = state.editorVariationId, startSession = false) {
  state.batchColumnsRequestId += 1;
  if (startSession) {
    state.batchSessionGeneration += 1;
    state.batchSessionOwner = `${batchSessionPrefix(scenarioId)}${state.batchSessionGeneration}`;
  } else if (!scenarioId) {
    state.batchSessionOwner = "";
  }
  state.batchScenarioId=scenarioId; state.batchFiles={}; state.batchBaselineFiles={}; state.batchGeographies={}; state.batchSelectedFiles=new Set(); state.batchSelectedColumns=new Map(); state.batchSelectedLocations=new Set();
  if ($("batchFromBaseline")) $("batchFromBaseline").checked = false;
}
function resetBatchDraft(scenarioId = state.editorVariationId, clear = false) {
  clearBatchDraftState(scenarioId, true);
  const scenario = state.selectedProject?.variations?.find((item) => item.id === scenarioId);
  const draft = clear ? {} : loadEditorDraft("batch") || savedBatchDraft(scenario) || {};
  state.batchSelectedFiles = new Set((draft.files || []).map(String));
  state.batchSelectedColumns = new Map(Object.entries(draft.columns || {}).map(([filename,columns]) => [filename,new Set((columns || []).map(String))]));
  state.batchSelectedLocations = new Set((draft.locations || []).map(String));
  state.batchMixedScopes = structuredClone(draft.mixedScopes || []);
  state.batchDraftGeographyType = draft.geographyType || "";
  state.batchDraftScopeUnavailable = Boolean(draft.scopeUnavailable);
  $("batchLocationSearch").value = draft.locationSearch || "";
  $("batchValue").value = draft.mixedValue ? "" : String(draft.value ?? "");
  $("batchValue").placeholder = draft.mixedValue ? "Mixed" : "";
  $("batchFromBaseline").checked = Boolean(draft.fromBaseline);
  setSelectDraftValue($("batchOperation"), draft.operation || "", "Mixed saved changes");
  $("batchYear").innerHTML = `<option value="">Choose year</option>`;
  $("batchYear").dataset.draftYear = draft.year || "2045";
  $("batchSelectAllColumns").checked = false;
  $("batchSelectAllColumns").indeterminate = false;
  $("batchLocationType").innerHTML = `<option value="all">All locations</option>`;
  $("batchLocations").innerHTML = `<p class="muted">Choose a location type.</p>`;
  $("batchSelectAllLocations").disabled = true;
  $("batchCompatibility").textContent = "";
  updateBatchDraftGuidance({...draft,mixedScopes:state.batchMixedScopes});
  renderBatchFiles(scenarioId);
  if (clear) persistBatchDraft();
}
function syncBatchSelectAll() {
  const boxes = [...document.querySelectorAll("[data-batch-column-file]")], checked = boxes.filter((box) => box.checked).length;
  $("batchSelectAllColumns").disabled = !boxes.length; $("batchSelectAllColumns").checked = boxes.length > 0 && checked === boxes.length; $("batchSelectAllColumns").indeterminate = checked > 0 && checked < boxes.length;
}
function batchCommonLevels() {
  const levels = new Map([["all", {id:"all",label:"All locations",values:[]}]]);
  Object.values(state.batchGeographies).forEach((payload) => (payload.levels || []).forEach((level) => { if (!levels.has(level.id)) levels.set(level.id, {id:level.id,label:level.label,values:[]}); }));
  return [...levels.values()];
}
function batchLocationValues(type = $("batchLocationType").value) {
  const values = new Set();
  Object.values(state.batchGeographies).forEach((payload) => (payload.levels?.find((level) => level.id === type)?.values || []).forEach((item) => values.add(item.value)));
  return values;
}
function renderBatchLocationTypes() {
  const levels = batchCommonLevels(), prior = state.batchDraftScopeUnavailable ? "" : state.batchDraftGeographyType || $("batchLocationType").value;
  $("batchLocationType").innerHTML = `${state.batchDraftScopeUnavailable ? '<option value="">Choose location type</option>' : ""}${levels.map((level) => `<option value="${escapeHtml(level.id)}">${escapeHtml(level.label)}</option>`).join("")}`;
  const next = state.batchDraftScopeUnavailable ? "" : prior === MIXED_EDITOR_VALUE ? MIXED_EDITOR_VALUE : levels.some((level) => level.id === prior) ? prior : levels.some((level) => level.id === "county") ? "county" : "all";
  setSelectDraftValue($("batchLocationType"), next, "Mixed saved scopes"); state.batchDraftGeographyType = next;
  renderBatchLocations();
}
function renderBatchLocations() {
  const type = $("batchLocationType").value, query = $("batchLocationSearch").value.trim().toLowerCase(), values = new Map();
  Object.values(state.batchGeographies).forEach((payload) => {
    const level = payload.levels?.find((item) => item.id === type);
    (level?.values || []).forEach((item) => values.set(item.value, item.label));
  });
  const allItems = [...values].sort((a,b) => a[1].localeCompare(b[1], undefined, {numeric:true})), valid = new Set(allItems.map(([value]) => value));
  state.batchSelectedLocations = new Set([...state.batchSelectedLocations].filter((value) => valid.has(value)));
  const items = allItems.filter(([,label]) => !query || label.toLowerCase().includes(query));
  $("batchLocations").innerHTML = !type ? `<p class="muted">Choose a location type.</p>` : type === MIXED_EDITOR_VALUE ? `<p class="muted">Saved changes use multiple location scopes. Choose a location type to edit.</p>` : type === "all" ? `<p class="muted">All locations are included.</p>` : items.map(([value,label]) => `<label class="check-option"><input type="checkbox" data-batch-location="${escapeHtml(value)}" ${state.batchSelectedLocations.has(value) ? "checked" : ""}><span>${escapeHtml(label)}</span></label>`).join("") || `<p class="muted">No matching locations.</p>`;
  document.querySelectorAll("[data-batch-location]").forEach((box) => box.addEventListener("change", () => { if (box.checked) state.batchSelectedLocations.add(box.dataset.batchLocation); else state.batchSelectedLocations.delete(box.dataset.batchLocation); syncBatchLocationSelectAll(allItems); persistBatchDraft(); }));
  syncBatchLocationSelectAll(allItems);
  renderBatchCompatibility();
}
function syncBatchLocationSelectAll(items = []) {
  const box = $("batchSelectAllLocations"), count = items.filter(([value]) => state.batchSelectedLocations.has(value)).length;
  box.disabled = $("batchLocationType").value === "all" || !items.length; box.checked = items.length > 0 && count === items.length; box.indeterminate = count > 0 && count < items.length;
}
function renderBatchCompatibility() {
  const type = $("batchLocationType").value; if (!type || type === MIXED_EDITOR_VALUE) { $("batchCompatibility").textContent = "Choose one location type before applying another change."; return; } if (type === "all") { $("batchCompatibility").textContent = "All selected files are eligible."; return; }
  const selectedFiles = [...state.batchSelectedFiles];
  const skipped = selectedFiles.filter((filename) => !state.batchGeographies[filename]?.levels?.some((level) => level.id === type && level.compatible));
  $("batchCompatibility").textContent = skipped.length ? `${skipped.length} selected file${skipped.length === 1 ? " is" : "s are"} not compatible with this location type and will be skipped: ${skipped.join(", ")}` : "All selected files support this location type.";
}
async function renderBatchColumns() {
  const requestId = ++state.batchColumnsRequestId, scenarioId = state.editorVariationId, sessionOwner = state.batchSessionOwner;
  const files = [...state.batchSelectedFiles], fileSignature = [...files].sort().join("\n");
  const priorYear = $("batchYear").value || $("batchYear").dataset.draftYear || "";
  if (!files.length) { $("batchColumnChecklist").innerHTML = `<p class="muted">Select one or more files.</p>`; state.batchFiles = {}; state.batchBaselineFiles = {}; state.batchGeographies = {}; state.batchSelectedColumns.clear(); renderBatchLocationTypes(); syncBatchSelectAll(); return; }
  $("batchColumnChecklist").innerHTML = `<p class="muted">Loading columns…</p>`;
  try {
    const payloads = await Promise.all(files.map(async (filename) => {
      const [csvPayload, baselinePayload, geography] = await Promise.all([request(editorFileUrl(filename)), request(baselineEditorFileUrl(filename)), request(`/api/geography-options?projectId=${encodeURIComponent(state.selectedProject.id)}&filename=${encodeURIComponent(filename)}`)]);
      return [filename, csvPayload, baselinePayload, geography];
    }));
    const currentFileSignature = [...state.batchSelectedFiles].sort().join("\n");
    if (requestId !== state.batchColumnsRequestId || sessionOwner !== state.batchSessionOwner || scenarioId !== state.editorVariationId || !batchSessionMatches(scenarioId) || state.editorMode !== "scenario" || fileSignature !== currentFileSignature) return;
    payloads.forEach(([filename, csvPayload, baselinePayload, geography]) => { state.batchFiles[filename] = csvPayload; state.batchBaselineFiles[filename] = baselinePayload; state.batchGeographies[filename] = geography; });
    Object.keys(state.batchFiles).filter((name) => !files.includes(name)).forEach((name) => { delete state.batchFiles[name]; delete state.batchBaselineFiles[name]; delete state.batchGeographies[name]; });
    const years = new Set(); payloads.forEach(([,csvPayload]) => { const index = csvPayload.columns.indexOf("Year"); if (index >= 0) csvPayload.rows.forEach((row) => years.add(row[index])); });
    const sortedYears = [...years].sort();
    $("batchYear").innerHTML = sortedYears.map((year) => `<option>${escapeHtml(year)}</option>`).join("");
    $("batchYear").value = sortedYears.includes(priorYear) ? priorYear : sortedYears.includes("2045") ? "2045" : sortedYears[0] || "";
    delete $("batchYear").dataset.draftYear;
    $("batchColumnChecklist").innerHTML = payloads.map(([filename,csvPayload]) => `<section class="batch-column-group"><header><strong>${escapeHtml(filename)}</strong><button class="text-button" type="button" data-select-file-columns="${escapeHtml(filename)}">Select all</button></header>${numericColumns(csvPayload).map((column) => `<label class="check-option"><input type="checkbox" data-batch-column-file="${escapeHtml(filename)}" data-batch-column="${escapeHtml(column)}" ${state.batchSelectedColumns.get(filename)?.has(column)?"checked":""}><span>${escapeHtml(column)}</span></label>`).join("") || `<span class="muted">No editable numeric columns.</span>`}</section>`).join("");
    document.querySelectorAll("[data-batch-column-file]").forEach((box) => {
      box.checked = state.batchSelectedColumns.get(box.dataset.batchColumnFile)?.has(box.dataset.batchColumn) || false;
      box.addEventListener("change",()=>{const selected=state.batchSelectedColumns.get(box.dataset.batchColumnFile)||new Set();if(box.checked)selected.add(box.dataset.batchColumn);else selected.delete(box.dataset.batchColumn);state.batchSelectedColumns.set(box.dataset.batchColumnFile,selected);syncBatchSelectAll();persistBatchDraft()});
    });
    document.querySelectorAll("[data-select-file-columns]").forEach((button) => button.addEventListener("click", () => { const boxes = [...document.querySelectorAll(`[data-batch-column-file="${CSS.escape(button.dataset.selectFileColumns)}"]`)], select = boxes.some((box) => !box.checked),selected=new Set(); boxes.forEach((box) => { box.checked = select;if(select)selected.add(box.dataset.batchColumn); });state.batchSelectedColumns.set(button.dataset.selectFileColumns,selected); button.textContent = select ? "Clear" : "Select all"; syncBatchSelectAll(); persistBatchDraft(); }));
    updateBatchDraftGuidance();
    renderBatchLocationTypes(); syncBatchSelectAll();
  } catch (error) { if(requestId===state.batchColumnsRequestId&&sessionOwner===state.batchSessionOwner&&batchSessionMatches(scenarioId))$("batchColumnChecklist").innerHTML = `<p class="muted">${escapeHtml(error.message)}</p>`; }
}
function rowMatchesBatch(row, csvPayload, geography, type, selected) {
  if (type === "all") return true;
  const level = geography?.levels?.find((item) => item.id === type && item.compatible); if (!level) return false;
  const chosen = level.values.filter((item) => selected.includes(item.value));
  const allowed = new Set(chosen.flatMap((item) => item.targetValues || [item.value])), geoIndex = csvPayload.columns.indexOf(geography.targetField || "Geo");
  return geoIndex >= 0 && allowed.has(String(row[geoIndex]));
}
async function applyBatchChanges() {
  const grouped=Object.fromEntries([...state.batchSelectedColumns].filter(([filename,columns])=>state.batchSelectedFiles.has(filename)&&columns.size).map(([filename,columns])=>[filename,[...columns]])), valueText = $("batchValue").value.trim(), value = Number(valueText), operation = $("batchOperation").value;
  if (!Object.keys(grouped).length || !valueText || !Number.isFinite(value) || !operation || operation === MIXED_EDITOR_VALUE || !$("batchYear").value) return notify("Choose files, columns, a year, a specific operation, and a numeric value.", "error");
  const type = $("batchLocationType").value, locations = [...state.batchSelectedLocations];
  if (!type || type === MIXED_EDITOR_VALUE) return notify("Choose one location type before applying another change.", "error");
  if (type !== "all" && !locations.length) return notify("Choose at least one location or use Select all locations.", "error");
  const button = $("applyBatchChanges");
  if (button.disabled) return;
  setBusy(button, true, "Checking…");
  try {
    const requestedFromBaseline = $("batchFromBaseline").checked;
    let overlap = 0;
    for (const [filename, columns] of Object.entries(grouped)) {
      const csvPayload = state.batchFiles[filename], baselinePayload = state.batchBaselineFiles[filename], geography = state.batchGeographies[filename];
      if (!csvPayload || !baselinePayload || (type !== "all" && !geography?.levels?.some((level) => level.id === type && level.compatible))) continue;
      const yearIndex = csvPayload.columns.indexOf("Year");
      csvPayload.rows.forEach((row, rowIndex) => {
        if (yearIndex >= 0 && row[yearIndex] !== $("batchYear").value) return;
        if (!rowMatchesBatch(row, csvPayload, geography, type, locations)) return;
        columns.forEach((column) => {
          const index = csvPayload.columns.indexOf(column);
          if (Number.isFinite(Number(row[index])) && rowsDifferAt(csvPayload.rows, baselinePayload.rows, rowIndex, index)) overlap++;
        });
      });
    }
    const basis = requestedFromBaseline ? "baseline" : await chooseOverlappingOperation(overlap);
    if (basis === "cancel") return;
    setBusy(button, false); setBusy(button, true, "Applying…");
    let changed = 0, saved = 0, skipped = [], rounded = new Set();
    const batchId = globalThis.crypto?.randomUUID?.() || `batch-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const operationId = newOperationId("batch");
    for (const [filename, columns] of Object.entries(grouped)) {
      const csvPayload = state.batchFiles[filename], baselinePayload = state.batchBaselineFiles[filename], geography = state.batchGeographies[filename];
      if (type !== "all" && !geography?.levels?.some((level) => level.id === type && level.compatible)) { skipped.push(filename); continue; }
      const yearIndex = csvPayload.columns.indexOf("Year");
      integerColumns(csvPayload, columns).forEach((column) => rounded.add(column));
      csvPayload.rows.forEach((row,rowIndex) => { if (yearIndex >= 0 && row[yearIndex] !== $("batchYear").value) return; if (!rowMatchesBatch(row, csvPayload, geography, type, locations)) return; columns.forEach((column) => { const index = csvPayload.columns.indexOf(column), sourceRow = basis === "baseline" ? baselinePayload?.rows?.[rowIndex] : row, current = Number(sourceRow?.[index]); if (!Number.isFinite(current)) return; let next = calculateValue(current, operation, value); if (column.toLowerCase().includes("prop")) next = Math.min(1, next); row[index] = calculatedValue(next, "batch", csvPayload, column); changed++; }); });
      const nextOperation={operationId,source:"batch",batchId,basis,columns:[...columns],operation,value,year:$("batchYear").value,allLocations:type==="all",geographyType:type,geographyLabel:type==="all"?"all locations":`${locations.length} selected locations`,locations:[...locations],rounding:operationRounding(csvPayload,columns,"batch")};
      const priorOperations=(activeEditorVariation()?.overlays||[]).find((item)=>item.fileName===filename)?.editOperations||[];
      await post("/api/overlays", {projectId:state.selectedProject.id, variationId:state.editorVariationId, filename, columns:csvPayload.columns, rows:csvPayload.rows,editOperations:operationsWithBaselineOverride(priorOperations,nextOperation)}); saved++;
    }
    $("batchFromBaseline").checked=false;
    notify(`Saved ${saved} file changes and changed ${changed} values${basis === "baseline" ? " from the untouched baseline" : ""}${skipped.length ? `; skipped ${skipped.length} incompatible files` : ""}.${rounded.size ? ` Whole-number count fields were rounded: ${[...rounded].join(", ")}.` : ""}`, "success"); persistBatchDraft(); await refreshState({quiet:true});
  } catch (error) { notify(error.message, "error"); } finally { setBusy(button, false); }
}

$("editorFile").addEventListener("change", async (event) => {
  const next = event.target.value;
  if (!next) return;
  const changed = await guardUnsaved(() => loadEditorFile(next));
  if (!changed) event.target.value = state.editorFileName;
});
$("editorLocationField").addEventListener("change", () => { state.editorSelectedLocations = new Set(); state.editorMixedScopes = []; state.editorScopeUnavailable = false; renderEditorLocations(); renderCsv(); updateFileDraftGuidance(); persistFileDraft(); });
$("editorLocationSearch").addEventListener("input", () => { renderEditorLocations(); persistFileDraft(); });
$("editorSelectAllLocations").addEventListener("change", (event) => {
  const values = selectedGeographyLevel(state.editorGeography, $("editorLocationField"))?.values || [];
  state.editorSelectedLocations = event.target.checked ? new Set(values.map((item) => item.value)) : new Set(); renderEditorLocations(); renderCsv(); persistFileDraft();
});
$("applyEditorChange").addEventListener("click", applyEditorChange);
$("clearEditorSelections").addEventListener("click", () => { renderEditorControls({year:$("editorYear").value}); persistFileDraft(); notify("Single-file selections cleared. Saved scenario changes were not removed.", "success"); });
$("resetEditorFile").addEventListener("click", () => { if (!state.csv) return; state.editorUndo.push(editorSnapshot()); state.editorRedo = []; state.csv.rows = state.editorOriginalRows.map((row) => [...row]);state.editorPendingOperations=structuredClone(state.editorSavedOperations); renderCsv(); updateEditorHistoryButtons(); recomputeEditorDirty(); });
$("undoEditorChange").addEventListener("click", undoEditor);
$("redoEditorChange").addEventListener("click", redoEditor);
$("editorNotes").addEventListener("input", (event) => scheduleNoteAutosave("file", event.currentTarget.value));
$("editorNotes").addEventListener("blur", () => saveNoteNow("file"));
$("editorSelectAllColumns").addEventListener("change", (event) => { document.querySelectorAll("[data-editor-column]").forEach((box) => { box.checked = event.target.checked; }); syncEditorColumnSelectAll(); persistFileDraft(); });
$("clearEditorColumns").addEventListener("click", () => { document.querySelectorAll("[data-editor-column]").forEach((box) => { box.checked = false; }); syncEditorColumnSelectAll(); persistFileDraft(); });
$("editorOperation").addEventListener("change", () => { updateFileDraftGuidance(); persistFileDraft(); });
$("editorYear").addEventListener("change", persistFileDraft);
$("editorValue").addEventListener("input", () => { $("editorValue").placeholder = ""; updateFileDraftGuidance(); persistFileDraft(); });
$("scenarioNote").addEventListener("input", (event) => scheduleNoteAutosave("scenario", event.currentTarget.value));
$("scenarioNote").addEventListener("blur", () => saveNoteNow("scenario"));
$("applyBatchChanges").addEventListener("click", applyBatchChanges);
$("batchSelectAllColumns").addEventListener("change", (event) => { const grouped=new Map();document.querySelectorAll("[data-batch-column-file]").forEach((box) => { box.checked = event.target.checked;const selected=grouped.get(box.dataset.batchColumnFile)||new Set();if(event.target.checked)selected.add(box.dataset.batchColumn);grouped.set(box.dataset.batchColumnFile,selected); });state.batchSelectedColumns=grouped;syncBatchSelectAll();persistBatchDraft(); });
$("batchLocationType").addEventListener("change", () => { state.batchSelectedLocations = new Set(); state.batchMixedScopes = []; state.batchDraftScopeUnavailable = false; state.batchDraftGeographyType = $("batchLocationType").value; renderBatchLocations(); updateBatchDraftGuidance(); persistBatchDraft(); });
$("batchLocationSearch").addEventListener("input", () => { renderBatchLocations(); persistBatchDraft(); });
$("batchSelectAllLocations").addEventListener("change", (event) => {
  const values = batchLocationValues();
  state.batchSelectedLocations = event.target.checked ? values : new Set(); renderBatchLocations(); persistBatchDraft();
});
$("batchOperation").addEventListener("change", () => { updateBatchDraftGuidance(); persistBatchDraft(); });
$("batchYear").addEventListener("change", persistBatchDraft);
$("batchValue").addEventListener("input", () => { $("batchValue").placeholder = ""; updateBatchDraftGuidance(); persistBatchDraft(); });
$("batchFromBaseline").addEventListener("change",persistBatchDraft);
$("clearBatchSelections").addEventListener("click", () => { resetBatchDraft(state.editorVariationId, true); notify("Batch selections cleared. Saved scenario changes were not removed.", "success"); });
function setScenarioSidebarWidth(width) {
  const workspace = $("inputEditor");
  const availableWidth = workspace.getBoundingClientRect().width || window.innerWidth;
  const max = Math.max(320, Math.min(480, availableWidth * .46));
  const next = Math.round(Math.max(320, Math.min(max, width)));
  workspace.style.setProperty("--scenario-sidebar-width", `${next}px`);
  $("scenarioSidebarResizer").setAttribute("aria-valuenow", String(next));
  localStorage.setItem("visioneval-scenario-sidebar-width", String(next));
}
const storedScenarioSidebarWidth = Number(localStorage.getItem("visioneval-scenario-sidebar-width"));
if (Number.isFinite(storedScenarioSidebarWidth)) setScenarioSidebarWidth(storedScenarioSidebarWidth);
$("scenarioSidebarResizer").addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  const resizer = event.currentTarget;
  const startX = event.clientX;
  const startWidth = $("inputEditor").querySelector(".scenario-sidebar").getBoundingClientRect().width;
  const controller = new AbortController();
  resizer.classList.add("resizing");
  resizer.setPointerCapture?.(event.pointerId);
  window.addEventListener("pointermove", (moveEvent) => {
    moveEvent.preventDefault();
    setScenarioSidebarWidth(startWidth + moveEvent.clientX - startX);
  }, {signal: controller.signal});
  const finish = () => { controller.abort(); resizer.classList.remove("resizing"); };
  window.addEventListener("pointerup", finish, {signal: controller.signal, once:true});
  window.addEventListener("pointercancel", finish, {signal: controller.signal, once:true});
});
$("scenarioSidebarResizer").addEventListener("keydown", (event) => {
  if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
  event.preventDefault();
  const width = $("inputEditor").querySelector(".scenario-sidebar").getBoundingClientRect().width;
  setScenarioSidebarWidth(width + (event.key === "ArrowRight" ? 16 : -16));
});
$("addEditorScenario").addEventListener("click", () => openScenarioDialog(false));
$("duplicateEditorScenario").addEventListener("click", () => openScenarioDialog(true));
$("cancelScenarioDialog").addEventListener("click", () => $("scenarioDialog").close());
$("scenarioDialogForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = $("scenarioDialogName").value.trim(); if (!name || !state.selectedProject) return;
  const duplicateFrom=$("scenarioDialog").dataset.duplicateFrom||"",source=state.selectedProject.variations.find((item)=>item.id===duplicateFrom),sourceType=source?scenarioEditSource(source):"",sourceMode=state.editorMode,sourceFile=state.editorFileName;
  setBusy($("confirmScenarioDialog"), true, "Saving…");
  try {
    const scenario = await post("/api/projects/variations", {projectId:state.selectedProject.id,name,duplicateFrom});
    const projectId = state.selectedProject.id;
    $("scenarioDialog").close();
    // Do not stamp the new scenario id onto the previous batch draft before
    // the refreshed project exists. Leaving the draft owner empty guarantees
    // the first Batch Change visit starts from an entirely clean state.
    clearBatchDraftState("");
    await refreshState({quiet:true}); selectProject(projectId);
    state.editorVariationId=scenario.id;
    const copied=activeEditorVariation(),copiedFiles=(copied?.overlays||[]).map((item)=>item.fileName).sort((a,b)=>a.localeCompare(b));
    const openFile=sourceType==="single_file"||(sourceType==="mixed"&&sourceMode==="file");
    if(duplicateFrom&&openFile&&copiedFiles.length)await openOverlay(scenario.id,copiedFiles.includes(sourceFile)?sourceFile:copiedFiles[0]);
    else openScenarioTools(scenario.id);
    notify(`${duplicateFrom?"Copied":"Created"} scenario ${scenario.name}.`, "success");
  } catch (error) { notify(error.message,"error"); } finally { setBusy($("confirmScenarioDialog"), false); }
});

$("cancelProjectEdit").addEventListener("click", () => $("projectEditDialog").close());
$("projectEditForm").addEventListener("submit", async (event) => {
  event.preventDefault(); const dialog = $("projectEditDialog"), projectId = dialog.dataset.projectId;
  setBusy(event.currentTarget.querySelector('button[type="submit"], button:not([type])'), true, "Saving…");
  try {
    const project = await post("/api/projects/update", {projectId,name:$("projectEditName").value}); dialog.close();
    await refreshState({quiet:true}); if (state.selectedProject?.id === projectId) selectProject(projectId); notify(`Updated ${project.name}.`, "success");
  } catch (error) { notify(error.message,"error"); } finally { setBusy(event.currentTarget.querySelector('button[type="submit"], button:not([type])'), false); }
});
$("cancelProjectCopy").addEventListener("click", () => $("projectCopyDialog").close());
function showCopyComplete(projectId, variationIds, summary={}){
  const project=state.data?.projects?.find((item)=>item.id===projectId),ids=variationIds||[];
  const pending=ids.filter((id)=>project?.variations?.find((item)=>item.id===id)?.resultStatus!=="current");
  const current=ids.filter((id)=>!pending.includes(id));
  const dialog=$("copyCompleteDialog");dialog.dataset.projectId=projectId;dialog.dataset.pendingVariationIds=JSON.stringify(pending);
  $("copyCompleteSummary").textContent=`Copied ${ids.length} scenario${ids.length===1?"":"s"} and ${Number(summary.resultsCopied||0)} independent result${Number(summary.resultsCopied||0)===1?"":"s"}${summary.bytesCopied?` (${humanBytes(summary.bytesCopied)})`:""}. ${current.length} scenario${current.length===1?" has":"s have"} a current reusable result.`;
  $("copyCompleteRunMessage").textContent=pending.length?`${pending.length} copied scenario${pending.length===1?" needs":"s need"} a run. Review Runs will select only those scenarios${project?.requiresBaseline?" and the required baseline":""}.`:"Every copied scenario already has a current result. You can still choose Run again from the Run page.";
  $("reviewCopiedRuns").hidden=!pending.length;dialog.showModal();
}
async function waitForCopyOperation(operation){
  state.copyOperationId=operation.id;const dialog=$("copyProgressDialog");$("cancelCopyOperation").disabled=false;$("copyProgress").removeAttribute("value");$("copyProgressMessage").textContent="Preparing copy…";$("copyProgressDetail").textContent="Completed results are copied into independent project storage.";if(!dialog.open)dialog.showModal();
  while(state.copyOperationId===operation.id){
    const status=await request(`/api/projects/copy/status?id=${encodeURIComponent(operation.id)}`);
    $("copyProgressMessage").textContent=status.message||"Copying…";
    if(status.totalBytes>0){$("copyProgress").value=Math.min(100,status.completedBytes/status.totalBytes*100);$("copyProgressDetail").textContent=`${humanBytes(status.completedBytes)} of ${humanBytes(status.totalBytes)} copied.`}else $("copyProgress").removeAttribute("value");
    if(status.state==="succeeded"){state.copyOperationId="";dialog.close();return status.result}
    if(status.state==="failed"){state.copyOperationId="";dialog.close();throw new Error(status.message||"Copy failed")}
    if(status.state==="cancelled"){state.copyOperationId="";dialog.close();throw new Error("Copy cancelled")}
    await new Promise((resolve)=>setTimeout(resolve,250));
  }
  throw new Error("Copy cancelled");
}
$("cancelCopyOperation").addEventListener("click",async()=>{if(!state.copyOperationId)return;$("copyProgressMessage").textContent="Cancelling copy…";$("cancelCopyOperation").disabled=true;try{await post("/api/projects/copy/cancel",{id:state.copyOperationId})}catch(error){notify(error.message,"error")}finally{$("cancelCopyOperation").disabled=false}});
$("reviewCopiedRuns").addEventListener("click",()=>{const dialog=$("copyCompleteDialog"),projectId=dialog.dataset.projectId,pending=JSON.parse(dialog.dataset.pendingVariationIds||"[]"),project=state.data?.projects?.find((item)=>item.id===projectId);switchPage("runPage",{restoreScroll:false});$("runProject").value=projectId;state.runSelectionProjectId=projectId;state.runSelectedVariationIds=new Set(pending);state.runForceRerunIds=new Set();state.runBaselineSelected=Boolean(project?.requiresBaseline);renderRunSelections()});
$("projectCopyForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const dialog = $("projectCopyDialog"), projectId = dialog.dataset.projectId, name = $("projectCopyName").value.trim();
  if (!projectId || !name) return;
  const button = event.currentTarget.querySelector('button[type="submit"], button:not([type])');
  setBusy(button, true, "Copying…");
  try {
    const operation = await post("/api/projects/copy/start", {projectId, name});
    dialog.close();const project = await waitForCopyOperation(operation);
    await refreshState({quiet:true});state.expandedProjectIds.add(project.id);renderProjects();
    notify(`Copied ${project.name} with independent completed-result snapshots and no run history.`, "success");
    showCopyComplete(project.id,(project.variations||[]).map((item)=>item.id),project.copySummary||{});
  } catch (error) { notify(error.message, "error"); } finally { setBusy(button, false); }
});
$("cancelScenarioCopy").addEventListener("click",()=>$("scenarioCopyDialog").close());
document.querySelectorAll('[name="scenarioCopyDestination"]').forEach((control)=>control.addEventListener("change",()=>{const existing=control.value==="existing"&&control.checked;$("scenarioCopyTargetProject").disabled=!existing;$("scenarioCopyNewProjectName").disabled=existing}));
$("scenarioCopyForm").addEventListener("submit",async(event)=>{
  event.preventDefault();const dialog=$("scenarioCopyDialog"),sourceProjectId=dialog.dataset.sourceProjectId,variationIds=JSON.parse(dialog.dataset.variationIds||"[]"),mode=document.querySelector('[name="scenarioCopyDestination"]:checked')?.value;
  const destination=mode==="existing"?{projectId:$("scenarioCopyTargetProject").value}:{name:$("scenarioCopyNewProjectName").value.trim()};
  if(!(destination.projectId||destination.name))return notify("Choose a destination project.","error");
  const blockedMessage=scenarioCopyBlockedMessage(sourceProjectId,variationIds);if(blockedMessage)return notify(blockedMessage,"error");
  const destinationBlocked=destinationCopyBlockedMessage(destination.projectId);if(destinationBlocked){const status=$("scenarioCopyDestinationStatus");status.hidden=false;status.textContent=destinationBlocked;return notify(destinationBlocked,"error")}
  const button=$("confirmScenarioCopy");setBusy(button,true,"Copying…");
  try{const operation=await post("/api/projects/variations/copy/start",{sourceProjectId,variationIds,destination});dialog.close();const result=await waitForCopyOperation(operation);state.projectScenarioSelections.set(sourceProjectId,new Set());await refreshState({quiet:true});state.expandedProjectIds.add(result.project.id);renderProjects();notify(`Copied ${result.variations.length} scenario${result.variations.length===1?"":"s"} to ${result.project.name}.`,"success");showCopyComplete(result.project.id,result.variations.map((item)=>item.id),result.copySummary||{})}
  catch(error){notify(error.message,"error")}finally{setBusy(button,false)}
});
$("cancelBaselineRename").addEventListener("click", () => $("baselineRenameDialog").close());
$("baselineRenameForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedProject) return;
  const button = event.currentTarget.querySelector('button[type="submit"], button:not([type])');
  setBusy(button, true, "Saving…");
  try {
    const projectId = state.selectedProject.id;
    await post("/api/projects/baseline/update", {projectId, displayName:$("baselineDisplayName").value});
    $("baselineRenameDialog").close();
    await refreshState({quiet:true}); selectProject(projectId);
    notify(`Baseline renamed to ${baselineDisplayName()}.`, "success");
  } catch (error) { notify(error.message, "error"); } finally { setBusy(button, false); }
});
$("cancelProjectRemove").addEventListener("click", () => $("projectRemoveDialog").close());
$("projectRemoveForm").addEventListener("submit", async (event) => {
  event.preventDefault(); const dialog = $("projectRemoveDialog"), projectId = dialog.dataset.projectId;
  const button = event.currentTarget.querySelector('button[type="submit"], button:not([type])'); setBusy(button, true, "Removing…");
  try {
    await post("/api/projects/remove", {projectId}); dialog.close();
    if (state.selectedProject?.id === projectId) { state.selectedProject = null; state.editorVariationId = ""; clearEditorFile(); $("inputEditor").hidden = true; }
    await refreshState({quiet:true}); notify("Project archived for 30 days and hidden from Run and Compare.", "success");
  } catch (error) { notify(error.message,"error"); } finally { setBusy(button, false); }
});
$("cancelProjectPurge").addEventListener("click", () => $("projectPurgeDialog").close());
$("projectPurgeForm").addEventListener("submit", async (event) => {
  event.preventDefault(); const dialog = $("projectPurgeDialog"), button = event.currentTarget.querySelector("button.danger"); setBusy(button, true, "Deleting…");
  try { await post("/api/projects/purge", {projectId:dialog.dataset.projectId}); dialog.close(); await refreshState({quiet:true}); notify("Archived project permanently deleted.", "success"); }
  catch (error) { notify(error.message, "error"); } finally { setBusy(button, false); }
});

function automaticSummarySearchText(file) {
  const details = file.automaticSummaryDetails;
  if (!details) return String(file.automaticSummary || "");
  return [file.automaticSummary, details.filename, details.ordered ? "applied operations in order" : "", ...(details.groups || []).flatMap((group) => [
    group.otherChanges ? "other saved changes" : "",
    group.allVariables ? "all variables" : "",
    (group.variables || []).join(" "),
    group.change,
    group.basis === "baseline" ? "from baseline" : "",
    group.locations?.text,
    group.locations?.effectiveText,
    ...(group.locations?.names || []),
  ])].filter(Boolean).join(" ");
}
function renderAutomaticSummaryFile(file) {
  const details = file.automaticSummaryDetails;
  if (!details?.groups?.length) return `<section class="automatic-summary-file" role="listitem"><h4>${escapeHtml(file.filename)}</h4><p>${escapeHtml(file.automaticSummary || "Changed")}</p></section>`;
  const multiple = details.groups.length > 1, ordered = Boolean(details.ordered);
  const hasOtherChanges = details.groups.some((group) => group.otherChanges);
  let operationNumber = 0;
  const groups = details.groups.map((group) => {
    const variables = group.allVariables ? "All variables" : (group.variables || []).join(", ") || "Values";
    const groupTitle = group.otherChanges ? "Other saved changes" : ordered ? `Operation ${++operationNumber}` : hasOtherChanges ? "Applied operation" : "";
    return `<div class="automatic-summary-group ${multiple ? "automatic-summary-group-nested" : ""}">
      ${groupTitle ? `<p class="automatic-summary-operation-title"><strong>${escapeHtml(groupTitle)}</strong></p>` : ""}
      <p><strong>${multiple ? ((group.variables || []).length === 1 ? "Variable" : "Variables") : "Variables"}:</strong> ${escapeHtml(variables)}</p>
      <p><strong>Change:</strong> ${escapeHtml(group.change || "Changed")}</p>
      <p class="automatic-summary-locations"><strong>Locations:</strong> ${escapeHtml(group.locations?.text || "No changed locations")}</p>
      ${group.locations?.effectiveText ? `<p class="automatic-summary-effective"><strong>Effective differences:</strong> ${escapeHtml(group.locations.effectiveText)}</p>` : ""}
    </div>`;
  }).join("");
  return `<section class="automatic-summary-file" role="listitem"><h4>${escapeHtml(details.filename || file.filename)}</h4>${ordered ? `<p class="automatic-summary-order-heading"><strong>Effective operations, in order:</strong> From-baseline entries replace prior effects on their targeted cells; other entries compound from the preceding scenario values.</p>` : ""}<div class="automatic-summary-file-details">${groups}</div></section>`;
}
function reviewAuditRows(file) {
  if (Array.isArray(file.auditRows)) return file.auditRows;
  const grouped = new Map();
  (file.changes || []).forEach((change) => {
    const key=String(change.row),row=grouped.get(key)||{row:change.row,geo:change.geo,year:change.year,cells:[]};
    row.cells.push({column:change.column,before:change.before,after:change.after});grouped.set(key,row);
  });
  return [...grouped.values()];
}
function reviewAuditColumns(file, rows) {
  if (Array.isArray(file.auditColumns)) return file.auditColumns;
  return [...new Set(rows.flatMap((row)=>(row.cells||[]).map((cell)=>cell.column).filter((column)=>!['Geo','Year'].includes(column))))];
}
function auditRowMatches(row, query) {
  return !query || [row.row,row.geo,row.year,...(row.cells||[]).flatMap((cell)=>[cell.column,cell.before,cell.after])]
    .some((value)=>String(value??"").toLowerCase().includes(query));
}
function renderAuditCell(row, column) {
  const cell=(row.cells||[]).find((item)=>item.column===column);
  if(!cell)return `<td class="audit-unchanged" aria-label="Not changed">—</td>`;
  const before=roundedValue(cell.before,column),after=roundedValue(cell.after,column);
  return `<td class="audit-changed" aria-label="Changed from ${escapeHtml(before)} to ${escapeHtml(after)}"><span class="audit-value"><small>Before</small>${escapeHtml(before)}</span><span class="audit-arrow" aria-hidden="true">→</span><span class="audit-value"><small>After</small>${escapeHtml(after)}</span></td>`;
}
function renderReview() {
  const review = state.review, query = $("reviewSearch").value.trim().toLowerCase();
  if (!review) { $("reviewContent").className = "review-content empty-state"; $("reviewContent").textContent = "Choose a project in Editor or Setup."; return; }
  const validation = review.validation || {valid:false,errors:["Validation unavailable"],warnings:[]};
  $("reviewValidation").innerHTML = `<section class="validation-card ${validation.valid ? "valid" : "invalid"}"><strong>${validation.valid ? "Project is ready to run" : "Resolve validation errors before running"}</strong>${(validation.errors || []).map((item) => `<p>${escapeHtml(item)}</p>`).join("")}${(validation.warnings || []).map((item) => `<p class="muted">Warning: ${escapeHtml(item)}</p>`).join("")}</section>`;
  $("continueToRun").disabled = !validation.valid;
  $("reviewProjectTitle").textContent = review.hypercube ? `Review ${review.hypercube.name}` : `Review ${review.projectName}`;
  const scenarios = review.scenarios.map((scenario) => {
    const files = scenario.files.map((file) => {
      const auditRows=reviewAuditRows(file),columns=reviewAuditColumns(file,auditRows),matchingRows=auditRows.filter((row)=>auditRowMatches(row,query));
      const metadataMatch=!query||file.filename.toLowerCase().includes(query)||file.notes.toLowerCase().includes(query)||automaticSummarySearchText(file).toLowerCase().includes(query);
      if(query&&!matchingRows.length&&!metadataMatch)return"";
      const rows=query?matchingRows:auditRows,shown=Number(file.auditRowsShown??auditRows.length),truncated=Boolean(file.auditTruncated)||(shown<Number(file.changedRows||0));
      const table=`<div class="table-wrap review-table changed-row-table"><table><thead><tr><th>Row</th><th>Location</th><th>Year</th>${columns.map((column)=>`<th>${escapeHtml(column)}</th>`).join("")}</tr></thead><tbody>${rows.map((row)=>`<tr><td>${row.row}</td><td>${escapeHtml(row.geo)}</td><td>${escapeHtml(row.year)}</td>${columns.map((column)=>renderAuditCell(row,column)).join("")}</tr>`).join("")||`<tr><td colspan="${Math.max(3,columns.length+3)}">No matching changed rows.</td></tr>`}</tbody></table></div>`;
      return `<details class="review-file" ${query?"open":""}><summary><span class="review-file-heading"><span><small class="review-audit-label">Changed-row audit</small><h3>${escapeHtml(file.filename)}</h3></span>${editSourceMarker(file.editSource)}</span><span class="review-summary"><span class="pill">${file.changedRows} changed rows</span><span class="pill">${file.changedCells} changed cells</span></span></summary><div class="review-file-body">${file.notes?`<p class="muted">Notes: ${escapeHtml(file.notes)}</p>`:""}${truncated?`<p class="notice guidance-notice">Showing ${shown.toLocaleString()} of ${Number(file.changedRows||0).toLocaleString()} changed rows.</p>`:""}${table}</div></details>`;
    }).join("");
    if (query && !files && !scenario.name.toLowerCase().includes(query) && !String(scenario.automaticSummary||"").toLowerCase().includes(query) && !String(scenario.automaticSummaryHeadline||"").toLowerCase().includes(query) && !String(scenario.scenarioNote||"").toLowerCase().includes(query)) return "";
    const open = Boolean(query) || state.reviewExpandedScenarioIds.has(scenario.id);
    const automaticSummary = scenario.automaticSummary ? `<details class="automatic-summary" ${query ? "open" : ""}><summary><span class="automatic-summary-heading"><strong>Automatic summary</strong></span></summary><div class="automatic-summary-files" role="list">${scenario.files.filter((file)=>file.automaticSummary).map(renderAutomaticSummaryFile).join("")}</div></details>` : "";
    const headline = scenario.automaticSummaryHeadline || scenario.automaticSummary || "No saved changes";
    return `<details class="review-scenario" data-review-scenario="${escapeHtml(scenario.id)}" ${open ? "open" : ""}><summary><span class="review-scenario-heading"><span class="review-scenario-title">${escapeHtml(scenario.name)} ${editSourceMarker(scenario.editSource,false)}</span><span class="review-scenario-headline">${escapeHtml(headline)}</span></span><span class="review-summary"><span class="pill">${scenario.fileCount} saved files</span><span class="pill">${scenario.changedRows} changed rows</span><span class="pill">${scenario.changedCells} changed cells</span></span></summary><div class="review-scenario-body">${automaticSummary}${scenario.scenarioNote ? `<p class="scenario-note-display"><strong>Scenario note:</strong> ${escapeHtml(scenario.scenarioNote)}</p>` : ""}${files || `<p class="muted">No saved file changes. This scenario currently matches the baseline inputs.</p>`}</div></details>`;
  }).join("");
  $("reviewContent").className = "review-content";
  const baselineDescription = state.selectedProject?.baseline?.strategy === "existing" ? "Existing completed result used as the comparison reference." : "Untouched project inputs used as the comparison reference.";
  $("reviewContent").innerHTML = `<section class="review-scenario"><h3>${escapeHtml(baselineDisplayName())} <span class="pill">Read only</span></h3><p class="muted">${baselineDescription}</p></section>${scenarios || `<section class="review-scenario"><p class="muted">No scenarios yet. Add one from Editor, or continue to Run to execute only the fresh baseline.</p></section>`}`;
  document.querySelectorAll("[data-review-scenario]").forEach((details) => details.addEventListener("toggle", () => {
    if (details.open) state.reviewExpandedScenarioIds.add(details.dataset.reviewScenario);
    else state.reviewExpandedScenarioIds.delete(details.dataset.reviewScenario);
  }));
}
async function loadProjectReview() {
  if (!state.selectedProject) { state.review = null; renderReview(); return; }
  $("reviewContent").className = "review-content empty-state"; $("reviewContent").textContent = "Calculating saved changes…";
  try { const hypercube = state.reviewHypercubeId ? `&hypercubeId=${encodeURIComponent(state.reviewHypercubeId)}` : ""; state.review = await request(`/api/project-review?projectId=${encodeURIComponent(state.selectedProject.id)}${hypercube}`); state.reviewedScenarioIds = state.review.scenarios.map((scenario) => scenario.id); renderReview(); }
  catch (error) { $("reviewContent").textContent = error.message; $("continueToRun").disabled = true; }
}
$("reviewSearch").addEventListener("input", renderReview);
$("continueToRun").addEventListener("click", () => {
  if (!state.selectedProject || !state.review?.validation?.valid) return;
  switchPage("runPage", {restoreScroll:false}); $("runProject").value = state.selectedProject.id;
  state.runSelectionProjectId = state.selectedProject.id; state.runSelectedVariationIds = new Set(state.reviewedScenarioIds); state.runBaselineSelected = Boolean(state.selectedProject.requiresBaseline); renderRunSelections();
});
$("editorProjectSelect").addEventListener("change", async (event) => {
  const changed = await guardUnsaved(() => selectProject(event.target.value));
  if (!changed) event.target.value = state.selectedProject?.id || "";
});
$("reviewProjectSelect").addEventListener("change", async (event) => {
  const changed = await guardUnsaved(async () => {
    state.reviewHypercubeId = "";
    selectProject(event.target.value);
    await loadProjectReview();
  });
  if (!changed) event.target.value = state.selectedProject?.id || "";
});
$("openCreateSetup").addEventListener("click", () => switchCreateSubpage("createSetup"));
document.querySelectorAll("[data-create-subpage]").forEach((button) => button.addEventListener("click", () => switchCreateSubpage(button.dataset.createSubpage)));
$("hypercubeSafetyDialog").addEventListener("close", () => {
  if ($("hypercubeSafetyDialog").returnValue !== "open") return;
  state.hypercubeSafetyAcknowledged = true;
  switchCreateSubpage("createHypercube");
});
$("hypercubeSafetyResources").addEventListener("click",()=>{$("hypercubeSafetyDialog").close("back");openSettings("settingsResources")});
$("hypercubeProject").addEventListener("change",async(event)=>{const next=event.target.value,changed=await flushHypercubeAutosave();if(!changed){event.target.value=state.hypercubeProjectId;return}closeLocationPopovers();state.hypercubeProjectId=next;state.hypercubeHydratedProjectId="";if(next)selectProject(next,false);state.hypercubeAxes=[];state.hypercubeSelectedLocations=new Set();state.hypercubePreview=null;state.hypercubeLocationSearch="";state.hypercubeFiles=new Map();invalidateHypercubePreview();renderHypercubeSetup()});
$("addHypercubeAxis").addEventListener("click",addHypercubeAxis);
$("hypercubeYear").addEventListener("change",()=>{state.hypercubeScopeDraft.year=$("hypercubeYear").value;setHypercubeDirty();invalidateHypercubePreview();renderHypercubeLocations()});
$("hypercubeGeographyType").addEventListener("change",()=>{state.hypercubeScopeDraft.geographyType=$("hypercubeGeographyType").value;state.hypercubeSelectedLocations=new Set();state.hypercubeLocationSearch="";setHypercubeDirty();invalidateHypercubePreview();renderHypercubeLocations()});
$("hypercubeLocationTrigger").addEventListener("click",()=>{const opening=!state.hypercubeLocationPopoverOpen;if(opening)closeLocationPopovers("hypercubeLocationPopover");setHypercubeLocationPopoverOpen(opening,{focusSearch:opening})});
$("hypercubeLocationSearch").addEventListener("input",(event)=>{state.hypercubeLocationSearch=event.target.value;renderHypercubeLocations()});
$("hypercubeSelectAllLocations").addEventListener("click",()=>{state.hypercubeSelectedLocations=new Set(hypercubeLocationOptions().map(([value])=>value));setHypercubeDirty();invalidateHypercubePreview();renderHypercubeLocations()});
$("hypercubeClearLocations").addEventListener("click",()=>{state.hypercubeSelectedLocations=new Set();setHypercubeDirty();invalidateHypercubePreview();renderHypercubeLocations()});
$("retryHypercubeSave").addEventListener("click",()=>saveHypercubeDraft({announce:true,flush:true}));
$("previewHypercube").addEventListener("click",previewHypercube);
$("generateHypercube").addEventListener("click",generateHypercube);
$("cancelHypercube").addEventListener("click",async()=>{if(!state.hypercubeOperationId)return;try{await post("/api/projects/hypercubes/cancel",{id:state.hypercubeOperationId})}catch(error){notify(error.message,"error")}});

$("runProject").addEventListener("change", () => { renderRunSelections(); syncMenuContext(); });
$("openRunDialog").addEventListener("click", () => {
  if (!$("runProject").value) return notify("Choose a project first.", "error");
  const names=selectedRunNames(); if(!names.length)return notify("Select at least one baseline or scenario.","error");
  const native=state.data?.runtime?.adapter==="native";
  const modeLock=native?"queued":state.data?.queue?.modeLock;
  const preferred=modeLock||state.desktop?.resources?.defaultRunMode||"queued";
  $("queuedRunMode").hidden=modeLock==="parallel";
  $("parallelRunMode").hidden=native||modeLock==="queued";
  const radio=document.querySelector(`input[name="runMode"][value="${preferred}"]`);if(radio)radio.checked=true;
  const lockMessage=modeLock?` Workbench is using ${modeLock === "queued" ? "Queued" : "Parallel"} mode across all projects until every active and waiting run is finished or removed.`:"";
  $("runDialogSelectionSummary").textContent=names.length>10?`This batch will contain exactly ${names.length.toLocaleString()} runs.${lockMessage}`:`This batch will contain exactly ${names.length} run${names.length===1?"":"s"}: ${names.join(", ")}.${lockMessage}`;
  $("runDialog").showModal();
});
$("confirmRun").addEventListener("click", async (event) => {
  event.preventDefault();
  const variationIds = [...state.runSelectedVariationIds];
  const includeBaseline = state.runBaselineSelected;
  const mode = state.data?.runtime?.adapter === "native" ? "queued" : state.data?.queue?.modeLock || document.querySelector('input[name="runMode"]:checked')?.value || "queued";
  if (!variationIds.length && !includeBaseline) return notify("Select at least one run.", "error");
  setBusy($("confirmRun"), true, "Starting…");
  try {
    const batch = await post("/api/batches", { projectId: $("runProject").value, variationIds, includeBaseline, mode,forceRerunVariationIds:[...state.runForceRerunIds] });
    $("runDialog").close();
    const reused=batch.reusedResults?.length||0;
    notify(batch.jobs.length?`Added ${batch.jobs.length} run${batch.jobs.length === 1 ? "" : "s"} to the workspace-wide ${mode} backlog${reused?`; reused ${reused} current result${reused===1?"":"s"}`:""}.`:`No run was needed; reused ${reused} current result${reused===1?"":"s"}.`, "success");
    await refreshState({ quiet: true });
    if(batch.jobs[0])selectJob(batch.jobs[0].id,{automatic:true});
  } catch (error) { notify(error.message, "error"); } finally { setBusy($("confirmRun"), false); }
});

async function selectJob(jobId,{automatic=false}={}) {
  state.selectedJob = jobId;
  state.consoleManualSelection=!automatic;
  state.logUnread.delete(jobId);
  state.logFollowTail = true;
  renderJobs();
  if (state.logSource) state.logSource.close();
  const job = state.data.jobs.find((item) => item.id === jobId);
  if (job?.batchId) state.consoleBatchId = job.batchId;
  if (job && activeJobStates.has(job.state)) { state.lastActiveConsoleJob = job.id; if (job.batchId) state.lastActiveConsoleByBatch[job.batchId] = job.id; }
  $("logTitle").textContent = job ? `${jobDisplayName(job)} · ${job.state}` : "R console";
  $("runLog").textContent = state.logBuffers[jobId] || "";
  renderJobActions(job);
  state.logSource = new EventSource(`/api/run-events?id=${encodeURIComponent(jobId)}&offset=${state.logOffsets[jobId] || 0}`);
  state.logSource.onmessage = (event) => {
    const chunk = JSON.parse(event.data);
    updateJobSnapshot(chunk.job);
    if (chunk.text) {
      appendJobLog(jobId, chunk.text); state.logOffsets[jobId] = chunk.offset || state.logOffsets[jobId] || 0;
      $("runLog").textContent = state.logBuffers[jobId];
      if (state.logFollowTail) $("runLog").scrollTop = $("runLog").scrollHeight;
    }
    $("logTitle").textContent = `${jobDisplayName(chunk.job)} · ${chunk.job.state}`;
    renderJobActions(chunk.job);
    if (chunk.terminal) {
      state.logSource.close();
      refreshState({ quiet: true });
    }
    renderJobs();
  };
  syncMenuContext();
}

$("runLog").addEventListener("scroll", () => {
  const log = $("runLog"), distanceFromBottom = log.scrollHeight - log.scrollTop - log.clientHeight;
  state.logFollowTail = distanceFromBottom < 28;
});

async function jobAction(path, jobId) {
  const actionKey = `${path}:${jobId}`;
  if (state.pendingJobActions.has(actionKey)) return;
  state.pendingJobActions.add(actionKey);
  const current = state.data?.jobs?.find((item) => item.id === jobId);
  if (current) renderJobActions(current);
  try {
    const result = await post(path, { jobId });
    const needsFallback = (path.includes("queue/remove") || path.includes("cleanup")) && state.selectedJob === jobId;
    if (needsFallback) { if (state.logSource) state.logSource.close(); state.selectedJob = null; if (current?.batchId) state.consoleBatchId = current.batchId; }
    const message = path.includes("queue/remove") ? "Waiting run removed." : path.includes("cleanup") ? "Cancelled run files deleted." : path.includes("cancel") ? "Stopping run and deleting partial files…" : "Retry queued.";
    notify(message, "success");
    await refreshState({ quiet: true });
    if (needsFallback) { const fallback = fallbackConsoleJob(current); if (fallback) await selectJob(fallback.id); }
    else if (result.id) selectJob(result.id);
  } catch (error) { notify(error.message, "error"); }
  finally {
    state.pendingJobActions.delete(actionKey);
    const refreshed = state.data?.jobs?.find((item) => item.id === state.selectedJob);
    renderJobActions(refreshed || null);
  }
}

async function stopAllRuns() {
  const jobs = runnableJobs();
  if (!jobs.length) return notify("No active or waiting runs to stop.", "error");
  const activeCount = jobs.filter((job) => activeJobStates.has(job.state) && job.state !== "stopping").length;
  const waitingCount = jobs.filter((job) => job.state === "waiting").length;
  const activeLabel = `${activeCount} active ${activeCount === 1 ? "run" : "runs"}`;
  const waitingLabel = `${waitingCount} waiting ${waitingCount === 1 ? "run" : "runs"}`;
  if (!await confirmWorkbench(`Stop all runs in this workspace?\n\nThis will stop ${activeLabel} and remove ${waitingLabel} from the queue. Partial files from stopped runs will be deleted. Completed results remain available in Compare.`)) return;
  state.stopAllPending = true;
  renderJobActions(state.data?.jobs?.find((item) => item.id === state.selectedJob) || null);
  syncMenuContext();
  try {
    const result = await post("/api/runs/stop-all", {});
    const message = `Stopped ${result.stopped || 0} active ${(result.stopped || 0) === 1 ? "run" : "runs"} and removed ${result.removed || 0} queued ${(result.removed || 0) === 1 ? "run" : "runs"}.`;
    notify(result.failures?.length ? `${message} ${result.failures.length} action failed.` : message, result.failures?.length ? "error" : "success");
    if (state.logSource) state.logSource.close();
    await refreshState({ quiet: true });
    const fallback = fallbackConsoleJob(null);
    if (fallback) await selectJob(fallback.id);
  } catch (error) {
    state.stopAllPending = false;
    notify(error.message, "error");
  } finally {
    if (!unresolvedRunQueueJobs().length) state.stopAllPending = false;
    const refreshed = state.data?.jobs?.find((item) => item.id === state.selectedJob);
    renderJobActions(refreshed || null);
    syncMenuContext();
  }
}

function fallbackConsoleJob(removedJob) {
  const jobs=state.data?.jobs||[], active=jobs.filter((job)=>activeJobStates.has(job.state)&&job.state!=="stopping"), batchId=removedJob?.batchId||state.consoleBatchId;
  const rememberedBatch=state.lastActiveConsoleByBatch[batchId];
  return active.find((job)=>job.batchId===batchId&&job.id===rememberedBatch)
    || active.find((job)=>job.batchId===batchId)
    || active.find((job)=>job.id===state.lastActiveConsoleJob)
    || active[0]
    || jobs.filter((job)=>job.batchId===batchId&&job.state==="waiting").sort((a,b)=>(a.queuePosition??1e9)-(b.queuePosition??1e9))[0]
    || jobs.filter((job)=>job.batchId===batchId&&terminalJobStates.has(job.state)).sort((a,b)=>new Date(b.finishedAt||b.createdAt||0)-new Date(a.finishedAt||a.createdAt||0))[0]
    || null;
}

$("pullRuntime").addEventListener("click", async () => {
  try { await openSettings("settingsRuntime"); } catch (error) { notify(error.message,"error"); }
});
$("startDockerDesktop").addEventListener("click", event => startDockerAndVerify(event.currentTarget));
$("verifyRuntime").addEventListener("click",event=>verifyRuntimeFromSetup(event.currentTarget).catch(()=>{}));

async function verifyAndSaveRuntime() {
  const native = state.data?.runtime?.adapter === "native";
  const veRuntime = $("settingsVeRuntime")?.value || $("onboardingVeRuntime")?.value || state.data?.runtime?.veRuntime || "";
  const veHome = $("settingsVeHome")?.value || $("onboardingVeHome")?.value || state.data?.runtime?.image || "";
  const rscript = $("settingsRscript")?.value || $("onboardingRscript")?.value || state.data?.runtime?.executable || "";
  const result = await post("/api/runtime/verify", native ? {veRuntime, veHome, rscript} : {});
  if (window.__TAURI_INTERNALS__?.invoke) {
    const prior = (state.desktop?.runtimeProfiles || []).find((item) => item.id === state.desktop?.activeRuntimeProfileId);
    await window.__TAURI_INTERNALS__.invoke("save_runtime_profile", {profile:{
      id:prior?.adapter===(native?"native":"docker")?prior.id:"", name:native?"Windows VE_Runtime":"Apple Silicon Docker", adapter:native?"native":"docker", platform:result.platform || (native?"windows":"darwin"), architecture:result.architecture || (native?"amd64":"arm64"),
      imageReference:native?"":result.image, veRuntimePath:native?result.veRuntime:"", veHomePath:native?result.veHome:"", imageDigest:native?"":result.digest, rscriptPath:native?result.rscript:"", runtimeVersion:result.runtimeVersion || (native?"Native VisionEval / R":"Compatible VisionEval runtime"), verified:true,
      verifiedAt:result.verifiedAt || new Date().toISOString(), verificationMessage:native?"VisionEval startup and registered-module checks passed.":"VisionEval startup and Workbench compatibility checks passed.", remoteStatus:"local",
    }});
    state.desktop = await window.__TAURI_INTERNALS__.invoke("desktop_state");
  }
  return result;
}

function compareElapsedText() {
  const elapsed = Math.max(0, Date.now() - (state.compareActivity?.startedAt || Date.now()));
  if (elapsed < 1000) return "Starting…";
  const seconds = Math.floor(elapsed / 1000), minutes = Math.floor(seconds / 60);
  return minutes ? `${minutes}m ${seconds % 60}s elapsed` : `${seconds}s elapsed`;
}

function setCompareControlsDisabled(disabled) {
  ["referenceDatastore", "comparisonOne", "comparisonTwo", "loadComparison", "compareTable", "compareVariable", "compareYear", "comparePageSize", "runComparison", "findChangedOutputs", "generateDashboard", "generateMap"].forEach((id) => { if ($(id)) $(id).disabled = disabled; });
}

function renderCompareActivity() {
  const activity = state.compareActivity, panel = $("compareActivity");
  if (!activity) { panel.hidden = true; return; }
  panel.hidden = false;
  panel.className = `compare-activity ${activity.status} ${activity.collapsed ? "collapsed" : ""}`;
  $("compareActivityTitle").textContent = activity.title;
  $("compareActivityElapsed").textContent = activity.status === "running" ? compareElapsedText() : activity.elapsedText;
  $("compareActivityDetails").textContent = activity.details;
  $("toggleCompareActivity").textContent = activity.collapsed ? "Expand" : "Collapse";
  $("toggleCompareActivity").setAttribute("aria-expanded", String(!activity.collapsed));
  $("dismissCompareActivity").hidden = activity.status === "running";
  $("stopCompareActivity").hidden = activity.status !== "running";
}

function startCompareActivity(title, details) {
  if (state.compareActivity?.status === "running") throw new Error("Another Compare operation is already running.");
  clearInterval(state.compareActivityTimer); clearTimeout(state.compareActivityCollapseTimer);
  state.compareActivity = {status:"running", title, details, startedAt:Date.now(), elapsedText:"Starting…", collapsed:false};
  state.compareController = new AbortController();
  setCompareControlsDisabled(true); renderCompareActivity();
  state.compareActivityTimer = setInterval(renderCompareActivity, 500);
}

function setCompareActivityPhase(title, details) {
  if (!state.compareActivity || state.compareActivity.status !== "running") return;
  state.compareActivity.title = title; state.compareActivity.details = details; renderCompareActivity();
}

function finishCompareActivity(status, title, details) {
  if (!state.compareActivity) return;
  clearInterval(state.compareActivityTimer); state.compareActivityTimer = null;
  const elapsed = Math.max(0, Date.now() - state.compareActivity.startedAt), seconds = Math.max(1, Math.round(elapsed / 1000));
  state.compareActivity = {...state.compareActivity, status, title, details, elapsedText:`${status === "succeeded" ? "Completed" : "Stopped"} in ${seconds}s`};
  state.compareController = null;
  setCompareControlsDisabled(false); syncSingleDatastoreControls(); renderCompareActivity();
  clearTimeout(state.compareActivityCollapseTimer);
  if (status === "succeeded") state.compareActivityCollapseTimer = setTimeout(() => { if (state.compareActivity?.status === "succeeded") { state.compareActivity.collapsed = true; renderCompareActivity(); } }, 2500);
  if (status === "succeeded") nativeNotification(title, `${details} ${state.compareActivity.elapsedText}`, {outcome:"succeeded", elapsedSeconds:seconds});
  else if (status === "failed" && !title.toLowerCase().includes("stopped")) nativeNotification(title, details, {outcome:"failed", elapsedSeconds:seconds});
}

function nextPaint() { return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))); }

async function withCompareActivity(title, details, action) {
  startCompareActivity(title, details);
  try {
    await nextPaint();
    const result = await action();
    finishCompareActivity("succeeded", `${title} complete`, "The operation completed successfully.");
    return result;
  } catch (error) {
    finishCompareActivity("failed", error.name === "AbortError" ? `${title} stopped` : `${title} failed`, error.name === "AbortError" ? "The operation was stopped." : error.message || String(error));
    throw error;
  }
}

$("toggleCompareActivity").addEventListener("click", () => { if (!state.compareActivity) return; state.compareActivity.collapsed = !state.compareActivity.collapsed; renderCompareActivity(); });
$("dismissCompareActivity").addEventListener("click", () => { if (state.compareActivity?.status === "running") return; clearTimeout(state.compareActivityCollapseTimer); state.compareActivity = null; renderCompareActivity(); });
$("stopCompareActivity").addEventListener("click", async () => {
  if (state.comparisonOperationId) {
    try { await post("/api/comparison/operations/cancel", {id:state.comparisonOperationId}); } catch (error) { notify(error.message, "error"); }
  }
  if (state.comparisonScanOperationId) {
    try { await post("/api/comparison/scans/cancel", {id:state.comparisonScanOperationId}); } catch (error) { notify(error.message, "error"); }
  }
  if (state.comparisonExportOperationId) {
    try { await post("/api/comparison/exports/cancel", {id:state.comparisonExportOperationId}); } catch (error) { notify(error.message, "error"); }
  }
  state.compareController?.abort();
});

$("loadComparison").addEventListener("click", async () => {
  const ids = [$("referenceDatastore").value, $("comparisonOne").value, $("comparisonTwo").value].filter(Boolean);
  if (!ids.length || new Set(ids).size !== ids.length) return notify("Choose a reference. Any comparison results must be different datastores.", "error");
  setBusy($("loadComparison"), true, "Loading…");
  try {
    const payload = await withCompareActivity("Loading comparison data", "Scanning the selected datastore variables and model years.", async () => {
      const result = await request(`/api/comparison/variables?ids=${encodeURIComponent(ids.join(","))}`);
      setCompareActivityPhase("Preparing comparison controls", `Found ${result.variables.length} comparable variables.`);
      await nextPaint();
      state.comparisonIds = ids; state.variables = result.variables; state.lastComparison=null; state.comparisonScan=null; state.comparisonScanId=""; state.dashboardPayload=null; state.dashboardDirty=true; state.dashboardInputSignature=""; state.mapPayload=null; state.mapDirty=true; state.mapInputSignature=""; state.exportFilterField="";state.exportFilterValues.clear();state.fullExportVariableKeys.clear();
      resetCompareResults();
      renderVariableSelectors(); switchSubpage("compareData");
      await loadScanGeoOptions();
      return result;
    });
    syncSingleDatastoreControls();
    notify(`Loaded ${payload.variables.length} variables.`, "success");
  } catch (error) { notify(error.message, "error"); } finally { setBusy($("loadComparison"), false); }
});

function renderVariableSelectors() {
  const tables = [...new Set(state.variables.map((item) => item.table))];
  $("compareTable").innerHTML = tables.map((table) => `<option>${escapeHtml(table)}</option>`).join("");
  renderVariablesForTable(); renderDashboardControls();
}
function renderVariablesForTable() {
  const variables = state.variables.filter((item) => item.table === $("compareTable").value);
  $("compareVariable").innerHTML = variables.map((item) => `<option value="${escapeHtml(item.name)}">${escapeHtml(item.name)}</option>`).join("");
  const micro = ["Household","Vehicle","Worker"].includes($("compareTable").value);
  $("compareModeField").hidden = !micro;
  if (!micro) $("compareMode").value = "records";
  else if (!state.lastComparison || state.lastComparison.table !== $("compareTable").value) $("compareMode").value = "aggregate";
  renderYears();
}
function renderYears() {
  const item = state.variables.find((variable) => variable.table === $("compareTable").value && variable.name === $("compareVariable").value);
  $("compareYear").innerHTML = (item?.years || []).map((year) => `<option value="${year}" ${year === "2045" ? "selected" : ""}>${year}</option>`).join("");
  state.compareOffset = 0; renderCompareExplanation(item); loadCompareGeoOptions();
}
function renderCompareExplanation(item = state.variables.find((variable) => variable.table === $("compareTable").value && variable.name === $("compareVariable").value)) {
  if (!item) { $("compareExplanation").innerHTML = `<p class="muted">Choose an output variable to see its definition and units.</p>`; return; }
  $("compareExplanation").innerHTML = `<div class="compare-explanation-grid"><div><p class="step">Output explanation</p><h3>${escapeHtml(item.table)} / ${escapeHtml(item.name)}</h3><p>${escapeHtml(item.description || "No output description is available.")}</p></div><dl class="compare-explanation-meta"><div><dt>Units</dt><dd>${escapeHtml(item.units || "Unspecified")}</dd></div><div><dt>Produced by</dt><dd>${escapeHtml(item.module || "Not recorded")}</dd></div><div><dt>Table</dt><dd>${escapeHtml(item.table)}</dd></div></dl></div>${item.metadataWarning ? `<p class="unit-warning"><strong>Unit review needed:</strong> ${escapeHtml(item.metadataWarning)}${item.proposedUnit ? ` Proposed label: ${escapeHtml(item.proposedUnit)}.` : ""}</p>` : ""}`;
}
$("compareTable").addEventListener("change", renderVariablesForTable);
$("compareVariable").addEventListener("change", renderYears);
$("compareMode").addEventListener("change", () => { state.compareOffset = 0; resetCompareResults(); });
$("compareYear").addEventListener("change", () => { state.compareOffset = 0; loadCompareGeoOptions(); loadScanGeoOptions(); });

$("runComparison").addEventListener("click", async () => {
  if (!state.comparisonIds.length) return notify("Load a datastore first.", "error");
  if (state.compareFilterField && !state.compareFilterValues.size) {
    return notify("Select at least one location or set Location level to All locations.", "error");
  }
  activateCompareResultMode("comparison");
  setBusy($("runComparison"), true, "Comparing…");
  try {
    const [reference, ...comparisons] = state.comparisonIds;
    const title = comparisons.length ? "Comparing datastore values" : "Loading datastore values";
    await withCompareActivity(title, `Reading ${$("compareTable").value} / ${$("compareVariable").value} for ${$("compareYear").value}.`, async () => {
      const operation = await post("/api/comparison/operations/start", comparisonRequest());
      state.comparisonOperationId = operation.id;
      let status = operation, renderedPage = false;
      while (["waiting","running"].includes(status.state)) {
        setCompareActivityPhase(status.phase === "statistics" ? "Calculating full statistics" : "Preparing comparison cache", status.message || "Loading datastore values.");
        if (status.page && !renderedPage) { state.lastComparison = status.page; await nextPaint(); renderComparison(status.page); renderedPage = true; }
        await new Promise((resolve)=>setTimeout(resolve,250));
        status = await request(`/api/comparison/operations/status?id=${encodeURIComponent(operation.id)}`, {signal:state.compareController.signal});
      }
      if (status.state === "cancelled") throw new DOMException("Stopped", "AbortError");
      if (status.state !== "succeeded" || !status.result) throw new Error(status.message || "Comparison failed");
      state.lastComparison = status.result;
      state.compareLocationDirty = false;
      renderCompareViewGeoValues();
      setCompareActivityPhase("Rendering comparison results", `Building the table and statistics for ${state.lastComparison.totalRows} rows.`);
      await nextPaint(); renderComparison(state.lastComparison);
      return state.lastComparison;
    });
  } catch (error) { if (error.name !== "AbortError") notify(error.message, "error"); } finally { state.comparisonOperationId=""; setBusy($("runComparison"), false); }
});

function number(value, column = "", context = "output") {
  if (value == null) return "—";
  if (protectedColumn(column)) return String(value);
  if (typeof value !== "number") return String(value);
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: precisionFor(context) }).format(value);
}
function percentage(value) { return number(value, "", "percentage"); }
function metric(label, value, {title="",className=""}={}) { return `<article class="metric ${escapeHtml(className)}"${title?` title="${escapeHtml(title)}"`:""}><small>${escapeHtml(label)}</small><strong>${escapeHtml(number(value))}</strong></article>`; }

function comparisonValuesDiffer(left, right) {
  if (typeof left === "number" && Number.isFinite(left) && typeof right === "number" && Number.isFinite(right)) {
    return Number(left.toFixed(5)) !== Number(right.toFixed(5));
  }
  return left !== right;
}

function activateCompareResultMode(mode) {
  state.compareResultMode = mode;
  $("comparisonResults").hidden = mode !== "comparison";
  $("changedVariablesPanel").hidden = mode !== "changedOutputs";
}

function resetCompareResults() {
  activateCompareResultMode("comparison");
  $("comparisonStats").hidden=true;$("comparisonStats").innerHTML="";
  $("comparisonTable").querySelector("thead").innerHTML="";
  $("comparisonTable").querySelector("tbody").innerHTML=`<tr><td class="empty-state">Choose a variable and update the comparison.</td></tr>`;
  $("comparePageLabel").textContent="Page 1";$("comparePrevious").disabled=true;$("compareNext").disabled=true;
  state.changedVariableQuery="";$("changedVariableSearch").value="";
}

function renderComparison(payload) {
  activateCompareResultMode("comparison");
  const aggregate = payload.mode === "aggregate";
  $("comparisonOptionBar").hidden = aggregate;
  $("comparisonTableWrap").hidden = aggregate;
  $("comparisonPager").hidden = aggregate;
  $("recordComparisonWarning").hidden = payload.mode !== "records" || payload.identitySemantics !== "run_local_synthetic";
  if (aggregate) {
    renderAggregateComparison(payload);
    updateExportLinks(); syncMenuContext();
    return;
  }
  const reference = payload.reference;
  const comparisons = payload.comparisons;
  state.compareSortColumn = payload.sortColumn || "id";
  state.compareSortDirection = payload.sortDirection || "original";
  const sortHeader = (label, key) => {
    const active=payload.sortColumn===key,direction=active?payload.sortDirection:"original",marker=direction==="asc"?"↑":direction==="desc"?"↓":"---";
    const aria=direction==="asc"?"ascending":direction==="desc"?"descending":"none",next=direction==="original"?"ascending":direction==="asc"?"descending":"default";
    return `<th aria-sort="${aria}"><button class="sort-header" data-compare-sort="${escapeHtml(key)}" title="Currently ${aria}; click for ${next} order" aria-label="${escapeHtml(label)}, currently ${aria}; click for ${next} order">${escapeHtml(label)} <span class="sort-state" aria-hidden="true">${marker}</span></button></th>`;
  };
  $("comparisonTable").querySelector("thead").innerHTML = `<tr>${sortHeader(payload.key,"id")}${sortHeader(reference.label,"reference")}${comparisons.map((item,index) => `${sortHeader(item.label,`comparison:${index}`)}${sortHeader("Change %",`percent:${index}`)}`).join("")}</tr>`;
  const directional = $("directionalDeltas").checked;
  $("comparisonTable").querySelector("tbody").innerHTML = payload.rows.map((row) => {
    const changedFlags=row.comparisons.map((value)=>comparisonValuesDiffer(row.reference,value));
    return `<tr class="${changedFlags.some(Boolean) ? "changed" : ""}"><td>${escapeHtml(row.id)}</td><td>${escapeHtml(number(row.reference, payload.variable))}</td>${row.comparisons.map((value, index) => { const delta=row.deltas[index], percent=(row.percentChanges||[])[index], changed=changedFlags[index],cls=directional&&changed?(delta>0?"delta-positive":delta<0?"delta-negative":"changed-cell"):changed?"changed-cell":""; return `<td class="${cls}">${escapeHtml(number(value, payload.variable))}</td><td class="${cls}">${percent==null?"—":`${escapeHtml(percentage(percent))}%`}</td>`; }).join("")}</tr>`;
  }).join("") || `<tr><td class="empty-state" colspan="${2 + comparisons.length * 2}">No matching rows.</td></tr>`;
  const page = Math.floor(payload.offset / payload.limit) + 1, pages = Math.max(1, Math.ceil(payload.displayRows / payload.limit));
  $("comparePageLabel").textContent = `Page ${page} of ${pages}`; $("comparePrevious").disabled = payload.offset <= 0; $("compareNext").disabled = payload.offset + payload.limit >= payload.displayRows;
  renderComparisonStats(payload);
  updateExportLinks();
  syncMenuContext();
  document.querySelectorAll("[data-compare-sort]").forEach((button) => button.addEventListener("click", () => {
    const current=button.dataset.compareSort;
    if(state.compareSortColumn!==current){state.compareSortColumn=current;state.compareSortDirection="asc";}
    else if(state.compareSortDirection==="original")state.compareSortDirection="asc";
    else if(state.compareSortDirection==="asc")state.compareSortDirection="desc";
    else {state.compareSortDirection="original";state.compareSortColumn="id";}
    state.compareOffset=0; refreshComparisonPage();
  }));
}

async function refreshComparisonPage() {
  if (!state.lastComparison?.comparisonToken || state.compareLocationDirty) return $("runComparison").click();
  try {
    const payload=await post("/api/comparison/page",{comparisonToken:state.lastComparison.comparisonToken,changedOnly:$("changedOnly").checked,limit:Number($("comparePageSize").value),offset:Number(state.compareOffset||0),sortColumn:state.compareSortColumn||"id",sortDirection:state.compareSortDirection||"original"});
    state.lastComparison=payload; renderComparison(payload);
  } catch (_) { $("runComparison").click(); }
}

function comparisonParams({changedOnly=$("changedOnly").checked} = {}) {
  const [reference, ...comparisons] = state.comparisonIds;
  const micro=["Household","Vehicle","Worker"].includes($("compareTable").value);
  const params = new URLSearchParams({reference, comparisons:comparisons.join(","), table:$("compareTable").value, variable:$("compareVariable").value, year:$("compareYear").value, mode:micro?$("compareMode").value:"records", changedOnly:String(changedOnly), limit:$("comparePageSize").value, offset:String(state.compareOffset || 0), filterField:state.compareFilterField || "", sortColumn:state.compareSortColumn || "id", sortDirection:state.compareSortDirection || "original"});
  if (state.compareFilterValues.size) params.set("filterValue", [...state.compareFilterValues].join("|"));
  return params;
}
function comparisonRequest({changedOnly=$("changedOnly").checked} = {}) {
  const [reference,...comparisons]=state.comparisonIds;
  const micro=["Household","Vehicle","Worker"].includes($("compareTable").value);
  return {reference,comparisons,table:$("compareTable").value,variable:$("compareVariable").value,year:$("compareYear").value,mode:micro?$("compareMode").value:"records",changedOnly,limit:Number($("comparePageSize").value),offset:Number(state.compareOffset||0),filterField:state.compareFilterField||"",filterValues:[...state.compareFilterValues],sortColumn:state.compareSortColumn||"id",sortDirection:state.compareSortDirection||"original"};
}

async function loadCompareGeoOptions() {
  if (!state.comparisonIds.length || !$("compareTable").value || !$("compareYear").value) return;
  try {
    const payload = await request(`/api/comparison/geo-options?reference=${encodeURIComponent(state.comparisonIds[0])}&table=${encodeURIComponent($("compareTable").value)}&year=${encodeURIComponent($("compareYear").value)}`);
    state.compareGeoOptions = payload.levels || []; state.compareGeoMessage = payload.message || "";
    if (!state.compareGeoOptions.some((item)=>item.field===state.compareFilterField)) { state.compareFilterField=""; state.compareFilterValues.clear(); }
    state.compareLocationDirty = Boolean(state.lastComparison); renderCompareViewGeoControls(); renderChangeDiscoveryControls();
  } catch (error) { $("compareViewGeoControls").innerHTML=`<p class="muted">${escapeHtml(error.message)}</p>`; }
}
async function loadScanGeoOptions() {
  if (!state.comparisonIds.length || !$("compareYear").value) return;
  try {
    const payload=await request(`/api/comparison/cross-output-geo-options?reference=${encodeURIComponent(state.comparisonIds[0])}&year=${encodeURIComponent($("compareYear").value)}`);
    state.scanGeoOptions=payload.levels||[];state.scanGeoMessage=payload.message||"";
    if(!state.scanGeoOptions.some((item)=>item.field===state.scanFilterField)){state.scanFilterField="";state.scanFilterValues.clear();}
    if(!state.scanGeoOptions.some((item)=>item.field===state.exportFilterField)){state.exportFilterField="";state.exportFilterValues.clear();}
    renderCompareGeoControls();renderChangeDiscoveryControls();
  }catch(error){state.scanGeoOptions=[];state.scanGeoMessage=error.message;renderCompareGeoControls();}
}

const locationSelectorConfigs={};
function setHypercubeLocationPopoverOpen(open,{focusSearch=false,returnFocus=false}={}) {
  state.hypercubeLocationPopoverOpen=Boolean(open);
  const popover=$("hypercubeLocationPopover"),trigger=$("hypercubeLocationTrigger");
  if(popover)popover.hidden=!state.hypercubeLocationPopoverOpen;
  if(trigger)trigger.setAttribute("aria-expanded",String(state.hypercubeLocationPopoverOpen));
  if(focusSearch&&state.hypercubeLocationPopoverOpen)$("hypercubeLocationSearch")?.focus();
  if(returnFocus&&!state.hypercubeLocationPopoverOpen)trigger?.focus();
}
function closeLocationPopovers(except="",{returnFocus=false}={}) {
  const focusedTrigger=[...document.querySelectorAll(".location-selector-trigger[aria-expanded='true']")].find((button)=>button.getAttribute("aria-controls")!==except);
  document.querySelectorAll("[data-location-popover]").forEach((item)=>{if(item.id!==except)item.hidden=true;});
  document.querySelectorAll(".location-selector-trigger").forEach((button)=>{if(button.getAttribute("aria-controls")!==except)button.setAttribute("aria-expanded","false");});
  if(except!=="hypercubeLocationPopover")state.hypercubeLocationPopoverOpen=false;
  if(returnFocus)focusedTrigger?.focus();
}
function eventInsideLocationPopover(event){const target=event.target;return Boolean(target?.closest?.(".location-selector-trigger")||target?.closest?.("[data-location-popover]"));}
document.addEventListener("pointerdown",(event)=>{if(!eventInsideLocationPopover(event))closeLocationPopovers();},true);
document.addEventListener("focusin",(event)=>{if(!eventInsideLocationPopover(event))closeLocationPopovers();});
document.addEventListener("keydown",(event)=>{if(event.key==="Escape"&&document.querySelector(".location-selector-trigger[aria-expanded='true']")){event.preventDefault();closeLocationPopovers("",{returnFocus:true});}});
function configureLocationSelector(config){locationSelectorConfigs[config.prefix]=config;renderLocationSelector(config.prefix);}
function renderLocationSelector(prefix,open=false,focusSearch=false){
  const config=locationSelectorConfigs[prefix],container=$(config.containerId);if(!config||!container)return;
  const levels=config.levels||[];if(!levels.length){container.innerHTML=`<p class="muted">${escapeHtml(config.message||"No geography filters are available.")}</p>`;return;}
  const level=levels.find((item)=>item.field===config.field),query=(config.search||"").toLowerCase();
  const options=(level?.options||level?.values?.map((value)=>({value,label:value}))||[]);
  const visible=options.filter((item)=>!query||item.label.toLowerCase().includes(query)||item.value.toLowerCase().includes(query));
  const count=config.values.size,summary=!level?(config.allowAll?"All locations":"Choose locations"):count?`${count} selected`:`No locations selected`;
  const popoverId=`${prefix}LocationPopover`;
  container.innerHTML=`<div class="location-selector"><label>Location level<select id="${prefix}LocationLevel"><option value="">${config.allowAll?"All locations":"Choose a level"}</option>${levels.map((item)=>`<option value="${escapeHtml(item.field)}" ${item.field===config.field?"selected":""}>${escapeHtml(item.label)}</option>`).join("")}</select></label><div class="location-selector-field"><span class="field-label">Locations</span><button id="${prefix}LocationTrigger" class="location-selector-trigger" type="button" aria-haspopup="dialog" aria-controls="${popoverId}" aria-expanded="${open}" ${level?"":"disabled"}>${escapeHtml(summary)}</button><div id="${popoverId}" class="location-popover" data-location-popover ${open?"":"hidden"}><div class="location-popover-toolbar"><input id="${prefix}LocationSearch" type="search" value="${escapeHtml(config.search||"")}" placeholder="Search ${escapeHtml((level?.label||"locations").toLowerCase())}"><div class="location-popover-actions"><button id="${prefix}SelectVisible" class="text-button" type="button">Select visible</button><button id="${prefix}ClearLocations" class="text-button" type="button">Clear</button></div></div><div class="location-popover-list">${visible.map((item)=>`<label class="check-option"><input type="checkbox" data-location-prefix="${prefix}" value="${escapeHtml(item.value)}" ${config.values.has(item.value)?"checked":""}><span>${escapeHtml(item.label)}</span></label>`).join("")||`<p class="muted">No matching locations.</p>`}</div></div></div>${config.note?`<p class="location-selector-note">${escapeHtml(config.note)}</p>`:""}</div>`;
  $(prefix+"LocationLevel").addEventListener("change",(event)=>{const value=event.target.value;config.field=value;config.search="";config.setField(value);config.values.clear();config.setSearch("");config.onChange();renderLocationSelector(prefix);});
  $(prefix+"LocationTrigger").addEventListener("click",(event)=>{const popover=$(popoverId),willOpen=popover.hidden;closeLocationPopovers(willOpen?popoverId:"");popover.hidden=!willOpen;event.currentTarget.setAttribute("aria-expanded",String(willOpen));if(willOpen)$(prefix+"LocationSearch").focus();});
  $(prefix+"LocationSearch").addEventListener("input",(event)=>{config.search=event.target.value;config.setSearch(config.search);renderLocationSelector(prefix,true,true);});
  container.querySelectorAll(`[data-location-prefix="${prefix}"]`).forEach((box)=>box.addEventListener("change",()=>{box.checked?config.values.add(box.value):config.values.delete(box.value);config.onChange();renderLocationSelector(prefix,true); }));
  $(prefix+"SelectVisible").addEventListener("click",()=>{visible.forEach((item)=>config.values.add(item.value));config.onChange();renderLocationSelector(prefix,true);});
  $(prefix+"ClearLocations").addEventListener("click",()=>{config.values.clear();config.onChange();renderLocationSelector(prefix,true);});
  if(focusSearch){const input=$(prefix+"LocationSearch");input?.focus();input?.setSelectionRange(input.value.length,input.value.length);}
}
function renderCompareViewGeoControls(){configureLocationSelector({containerId:"compareViewGeoControls",prefix:"compareView",levels:state.compareGeoOptions||[],message:state.compareGeoMessage,field:state.compareFilterField,values:state.compareFilterValues,search:state.compareLocationSearch,allowAll:true,setField:(value)=>state.compareFilterField=value,setSearch:(value)=>state.compareLocationSearch=value,onChange:()=>{state.compareOffset=0;state.compareLocationDirty=Boolean(state.lastComparison);renderChangeDiscoveryControls();},note:state.compareLocationDirty?"Update Comparison to apply this location selection.":""});}
function renderCompareViewGeoValues(){renderCompareViewGeoControls();}
function renderCompareGeoControls(){const container=$("compareGeoControls");container.hidden=state.comparisonScanScope!=="selected";if(container.hidden)return;configureLocationSelector({containerId:"compareGeoControls",prefix:"scan",levels:state.scanGeoOptions||[],message:state.scanGeoMessage,field:state.scanFilterField,values:state.scanFilterValues,search:state.scanLocationSearch,allowAll:false,setField:(value)=>state.scanFilterField=value,setSearch:(value)=>state.scanLocationSearch=value,onChange:renderChangeDiscoveryControls,note:""});}
function renderCompareGeoValues(){renderCompareGeoControls();}
function renderComparisonStats(payload) {
  const container=$("comparisonStats"); container.hidden=!$("showCompareStats").checked;
  if(container.hidden)return;
  if (!payload.comparisons?.length) {
    const summary=payload.referenceSummary||{};
    container.innerHTML=`<article class="stat-card"><h3>${escapeHtml(payload.reference?.label||"Datastore")}</h3><div class="stat-key-grid">${metric("Rows",summary.count||0)}${metric("Numeric rows",summary.numericCount||0)}${summary.kind==="numeric"?metric("Mean",summary.mean)+metric("Minimum",summary.min)+metric("Maximum",summary.max):metric("Categories",summary.topCategories?.length||0)}</div></article>`;
    return;
  }
  container.innerHTML=(payload.stats||[]).map((item)=>{
    const unmatched=item.unmatchedRows||0;
    const formula=`Total % change = ((sum of comparison - sum of reference) / sum of reference) x 100 across ${number(item.matchedRows||0)} matched numeric rows. ${number(unmatched)} unmatched row${unmatched===1?" was":"s were"} excluded.`;
    return `<article class="stat-card"><h3>${escapeHtml(item.label)}</h3><div class="stat-key-grid">${metric("Rows changed",item.rowsChanged)}${metric("Increased",item.rowsIncreased)}${metric("Decreased",item.rowsDecreased)}${metric("Net change",item.netChange)}${metric("Average row %",item.averageRowPercentChange==null?"Not available":`${percentage(item.averageRowPercentChange)}%`)}${metric("Total % change",item.totalPercentChange==null?"Not available":`${percentage(item.totalPercentChange)}%`,{title:formula,className:"primary-stat"})}</div>${iqrComparison(item.reference,item.comparison,payload.reference?.label||"Reference",item.label)}<p class="stat-note" title="${escapeHtml(formula)}">${escapeHtml(number(item.matchedRows||0))} matched numeric rows · ${escapeHtml(number(unmatched))} unmatched excluded</p></article>`;
  }).join("")||`<p class="muted">No statistics are available.</p>`;
}

function iqrComparison(reference, comparison, referenceLabel, comparisonLabel) {
  if(reference?.kind!=="numeric"||comparison?.kind!=="numeric")return `<p class="muted stat-note">IQR distribution is available for numeric outputs.</p>`;
  const values=[reference.min,reference.q1,reference.median,reference.q3,reference.max,comparison.min,comparison.q1,comparison.median,comparison.q3,comparison.max].filter((value)=>Number.isFinite(value));
  if(!values.length)return "";
  const min=Math.min(...values),max=Math.max(...values),span=max-min;
  const position=(value)=>span?Math.max(0,Math.min(100,((value-min)/span)*100)):50;
  const row=(summary,label)=>{const low=position(summary.min),q1=position(summary.q1),median=position(summary.median),q3=position(summary.q3),high=position(summary.max),values=[["Minimum",summary.min],["Q1",summary.q1],["Median",summary.median],["Q3",summary.q3],["Maximum",summary.max]];return `<div class="iqr-series"><strong class="iqr-series-label">${escapeHtml(label)}</strong><div class="iqr-track" title="Minimum ${escapeHtml(number(summary.min))}; Q1 ${escapeHtml(number(summary.q1))}; median ${escapeHtml(number(summary.median))}; Q3 ${escapeHtml(number(summary.q3))}; maximum ${escapeHtml(number(summary.max))}"><span class="iqr-whisker" style="left:${low}%;width:${Math.max(0,high-low)}%"></span><span class="iqr-box" style="left:${q1}%;width:${Math.max(.5,q3-q1)}%"></span><span class="iqr-median" style="left:${median}%"></span></div><div class="iqr-values">${values.map(([name,value])=>`<span><small>${name}</small><strong>${escapeHtml(number(value))}</strong></span>`).join("")}</div></div>`;};
  return `<div class="iqr-visual"><div class="iqr-heading"><strong>Distribution</strong><small>Five-number summary on a shared scale</small></div>${row(reference,referenceLabel)}${row(comparison,comparisonLabel)}</div>`;
}

function syncSingleDatastoreControls() {
  const single = state.comparisonIds.length === 1;
  $("runComparison").textContent = single ? "Update View" : "Update Comparison";
  ["changedOnly","directionalDeltas","findChangedOutputs","generateDashboard"].forEach((id) => { $(id).disabled = state.comparisonIds.length < 2; });
  if (single) { $("changedOnly").checked = false; $("directionalDeltas").checked = false; }
  renderChangeDiscoveryControls();
}
$("showCompareStats").addEventListener("change",()=>state.lastComparison&&renderComparisonStats(state.lastComparison));
$("directionalDeltas").addEventListener("change",()=>state.lastComparison&&renderComparison(state.lastComparison));
$("changedOnly").addEventListener("change",()=>{state.compareOffset=0;refreshComparisonPage();});
$("comparePageSize").addEventListener("change",()=>{state.compareOffset=0;refreshComparisonPage();});
$("comparePrevious").addEventListener("click",()=>{state.compareOffset=Math.max(0,state.compareOffset-Number($("comparePageSize").value));refreshComparisonPage();});
$("compareNext").addEventListener("click",()=>{state.compareOffset+=Number($("comparePageSize").value);refreshComparisonPage();});

function renderChangeDiscoveryControls() {
  const count = state.scanFilterValues.size, selected = state.comparisonScanScope === "selected";
  const selectedScopeIncomplete = selected && (!state.scanFilterField || !count);
  const viewScopeIncomplete = Boolean(state.compareFilterField && !state.compareFilterValues.size);
  $("scanScopeAll").setAttribute("aria-pressed", String(state.comparisonScanScope === "all"));
  $("scanScopeSelected").setAttribute("aria-pressed", String(state.comparisonScanScope === "selected"));
  $("scanScopeSelected").textContent = `Selected locations (${count})`;
  $("scanScopeSelected").disabled = !(state.scanGeoOptions||[]).length;
  $("runComparison").disabled = !state.comparisonIds.length || viewScopeIncomplete || state.compareActivity?.status === "running";
  $("findChangedOutputs").disabled = state.comparisonIds.length<2 || selectedScopeIncomplete;
  $("openCompareExports").disabled = (!state.lastComparison && state.comparisonIds.length<2) || state.compareActivity?.status === "running";
  $("compareGeoControls").hidden=!selected;
  $("changeDiscoveryScopeHelp").textContent = selected
    ? count ? `${count} selected location${count === 1 ? "" : "s"} will be used for the changed-output scan.` : "Choose a location level and at least one location to use the selected-location scan scope."
    : "All locations will be scanned.";
  updateExportLinks();
  syncMenuContext();
}
document.querySelectorAll("[data-scan-scope]").forEach((button) => button.addEventListener("click", () => {
  state.comparisonScanScope = button.dataset.scanScope;
  renderCompareGeoControls();
  renderChangeDiscoveryControls();
}));

async function runChangeScan() {
  if(state.comparisonIds.length<2)return notify("Load comparison results first.","error");
  const useSelected=state.comparisonScanScope==="selected";
  if(useSelected&&(!state.scanFilterField||!state.scanFilterValues.size))return notify("Select at least one location or switch the scan scope to All locations.","error");
  const [reference,...comparisons]=state.comparisonIds, title=useSelected?"Finding changes in selected locations":"Finding changed outputs";
  try{
    startCompareActivity(title,"Checking saved scan results. The first scan may need to prepare reusable comparison caches from the workspace RDA files.");
    const operation=await post("/api/comparison/scans/start",{reference,comparisons,year:$("compareYear").value,filterField:useSelected?state.scanFilterField:"",filterValues:useSelected?[...state.scanFilterValues]:[]});
    state.comparisonScanOperationId=operation.id;
    let status=operation;
    while(["waiting","running"].includes(status.state)){
      const progress=status.progress||{};
      const phase=progress.phase||status.phase;
      const cacheDetail=progress.total
        ? `Preparing comparison cache ${progress.completed||0} of ${progress.total}${progress.recordLabel?`: ${progress.recordLabel}`:""}${progress.table?` / ${progress.table}`:""}. ${progress.cacheHits||0} reused, ${progress.cacheMisses||0} built.`
        : "Preparing reusable comparison caches from the workspace RDA files. The first scan can take longer.";
      const detail=phase==="loading_metadata"?"Loading datastore metadata…":phase==="preparing_cache"?cacheDetail:progress.total&&phase==="scanning"?`Scanning ${progress.completed||0} of ${progress.total}${progress.table?`: ${progress.table} / ${progress.variable}`:""}`:phase==="finalizing"?"Finalizing changed-output results…":phase==="cache_validation"?"Validating saved scan results…":phase==="starting_runtime"?"Starting the batch runtime…":phase==="fallback"?"Starting the compatibility scanner…":status.message||"Preparing changed-output scan…";
      setCompareActivityPhase(title,detail);
      await new Promise((resolve)=>setTimeout(resolve,500));
      status=await request(`/api/comparison/scans/status?id=${encodeURIComponent(operation.id)}`);
    }
    if(status.state==="cancelled")throw new DOMException("Stopped","AbortError");
    if(status.state!=="succeeded")throw new Error(status.message||"Change scan failed");
    state.comparisonScan=status.result; state.comparisonScanId=operation.id; renderChangedVariables(state.comparisonScan); updateExportLinks(); syncMenuContext();
    finishCompareActivity("succeeded",`${title} complete`,status.cached?"Loaded a cached scan.":"The batch scan completed successfully.");
  }catch(error){
    if(state.compareActivity?.status==="running")finishCompareActivity("failed",error.name==="AbortError"?`${title} stopped`:`${title} failed`,error.name==="AbortError"?"The backend scan was stopped.":error.message);
    if(error.name!=="AbortError")notify(error.message,"error");
  }finally{state.comparisonScanOperationId="";}
}
function renderChangedVariables(payload){
  activateCompareResultMode("changedOutputs");$("changedVariablesTitle").textContent=`${payload.changedVariables} changed variables`;$("changedVariablesMeta").textContent=`Scanned ${payload.scanned}; skipped ${payload.skipped.length} unsafe or unavailable variables.`;
  renderChangedVariableTable();
}
function renderChangedVariableTable(){
  const payload=state.comparisonScan,table=$("changedVariablesList");if(!payload||!table)return;
  const labels=(payload.results.find((item)=>item.pairStats?.length)?.pairStats||[]).map((pair,index)=>pair.label||`Comparison ${index+1}`);
  const query=(state.changedVariableQuery||"").toLowerCase(),sort=state.changedVariableSort;
  const rows=(payload.results||[]).filter((item)=>!query||`${item.table} ${item.variable}`.toLowerCase().includes(query));
  const sortValue=(item)=>sort.column==="output"?`${item.table}/${item.variable}`.toLowerCase():sort.column.startsWith("pair-")?(item.pairStats?.[Number(sort.column.slice(5))]?.totalPercentChange??null):null;
  if(sort.direction!=="original")rows.sort((left,right)=>{const a=sortValue(left),b=sortValue(right);if(a==null&&b==null)return 0;if(a==null)return 1;if(b==null)return-1;const result=typeof a==="string"?a.localeCompare(b,undefined,{numeric:true}):a-b;return sort.direction==="desc"?-result:result;});
  const header=(label,column)=>{const active=sort.column===column,direction=active?sort.direction:"original",marker=direction==="asc"?"↑":direction==="desc"?"↓":"---",aria=direction==="asc"?"ascending":direction==="desc"?"descending":"none",next=direction==="original"?"ascending":direction==="asc"?"descending":"default";return `<th aria-sort="${aria}"><button class="sort-header" type="button" data-changed-sort="${column}" title="Currently ${aria}; click for ${next} order" aria-label="${escapeHtml(label)}, currently ${aria}; click for ${next} order">${escapeHtml(label)} <span class="sort-state" aria-hidden="true">${marker}</span></button></th>`;};
  table.innerHTML=`<colgroup><col class="changed-output-column">${labels.map(()=>`<col class="changed-percent-column">`).join("")}</colgroup><thead><tr>${header("Output","output")}${labels.map((label,index)=>header(`${label} change %`,`pair-${index}`)).join("")}</tr></thead><tbody>${rows.map((item)=>`<tr tabindex="0" data-changed-table="${escapeHtml(item.table)}" data-changed-variable="${escapeHtml(item.variable)}"><td>${escapeHtml(item.table)} / ${escapeHtml(item.variable)}</td>${labels.map((_,index)=>{const value=item.pairStats?.[index]?.totalPercentChange;return `<td>${value==null?"Not available":`${percentage(value)}%`}</td>`;}).join("")}</tr>`).join("")||`<tr><td colspan="${labels.length+1}" class="empty-state">No matching changed outputs.</td></tr>`}</tbody>`;
  table.querySelectorAll("[data-changed-sort]").forEach((button)=>button.addEventListener("click",()=>{const column=button.dataset.changedSort;if(state.changedVariableSort.column!==column)state.changedVariableSort={column,direction:"asc"};else if(state.changedVariableSort.direction==="original")state.changedVariableSort={column,direction:"asc"};else if(state.changedVariableSort.direction==="asc")state.changedVariableSort={column,direction:"desc"};else state.changedVariableSort={column:"output",direction:"original"};renderChangedVariableTable();}));
  const openOutput=(row)=>{$("compareTable").value=row.dataset.changedTable;renderVariablesForTable();$("compareVariable").value=row.dataset.changedVariable;renderYears();state.compareOffset=0;activateCompareResultMode("comparison");$("runComparison").click();};
  table.querySelectorAll("tbody [data-changed-table]").forEach((row)=>{row.addEventListener("click",()=>openOutput(row));row.addEventListener("keydown",(event)=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();openOutput(row);}});});
}
$("changedVariableSearch").addEventListener("input",(event)=>{state.changedVariableQuery=event.target.value;renderChangedVariableTable();});
$("findChangedOutputs").addEventListener("click",runChangeScan);

function renderExportGeoControls(){
  configureLocationSelector({containerId:"exportGeoControls",prefix:"export",levels:state.scanGeoOptions||[],message:state.scanGeoMessage,field:state.exportFilterField,values:state.exportFilterValues,search:state.exportLocationSearch,allowAll:false,setField:(value)=>state.exportFilterField=value,setSearch:(value)=>state.exportLocationSearch=value,onChange:updateExportLinks,note:""});
}

function fullExportVariables(){
  const year=$("fullExportYear").value;
  return state.variables.filter((item)=>(item.years||[]).includes(year));
}

function renderFullExportVariableList(){
  const query=(state.fullExportVariableQuery||"").trim().toLowerCase(),variables=fullExportVariables();
  const visible=variables.filter((item)=>!query||`${item.table} ${item.name} ${item.description||""}`.toLowerCase().includes(query));
  $("fullExportVariableList").innerHTML=visible.map((item)=>{const key=`${item.table}/${item.name}`;return `<label class="check-option" data-full-export-option><input type="checkbox" data-full-export-variable="${escapeHtml(key)}" ${state.fullExportVariableKeys.has(key)?"checked":""}><span>${escapeHtml(item.table)} / ${escapeHtml(item.name)}</span></label>`;}).join("")||`<p class="muted">No matching outputs.</p>`;
  document.querySelectorAll("[data-full-export-variable]").forEach((box)=>box.addEventListener("change",()=>{box.checked?state.fullExportVariableKeys.add(box.dataset.fullExportVariable):state.fullExportVariableKeys.delete(box.dataset.fullExportVariable);updateExportLinks();}));
  updateExportLinks();
}

function prepareFullExportControls(){
  const years=[...new Set(state.variables.flatMap((item)=>item.years||[]))].sort(),current=$("compareYear").value;
  $("fullExportYear").innerHTML=years.map((year)=>`<option ${year===current?"selected":""}>${escapeHtml(year)}</option>`).join("");
  if(!years.includes($("fullExportYear").value)&&years.length)$("fullExportYear").value=years[0];
  state.fullExportVariableKeys=new Set([...state.fullExportVariableKeys].filter((key)=>fullExportVariables().some((item)=>`${item.table}/${item.name}`===key)));
  renderFullExportVariableList();
}

function updateExportLinks(){
  const hasComparison=Boolean(state.lastComparison)&&!state.compareLocationDirty,hasPairs=state.comparisonIds.length>1,hasFullSelection=state.fullExportVariableKeys.size>0,hasSelectedScope=Boolean(state.exportFilterField&&state.exportFilterValues.size);
  document.querySelector('[data-export-group="current"]').hidden=!hasComparison;
  document.querySelector('[data-export-group="all-changed"]').hidden=!hasPairs;
  document.querySelector('[data-export-group="selected-changed"]').hidden=!hasPairs;
  document.querySelector('[data-export-group="full-variables"]').hidden=!hasPairs;
  ["exportSelectedChangedCsv","exportSelectedChangedWorkbook"].forEach((id)=>{if($(id))$(id).disabled=!hasSelectedScope;});
  ["exportFullVariablesZip","exportFullVariablesWorkbook"].forEach((id)=>{if($(id))$(id).disabled=!hasFullSelection;});
  if($("fullExportVariableSummary"))$("fullExportVariableSummary").textContent=hasFullSelection?`${state.fullExportVariableKeys.size} output${state.fullExportVariableKeys.size===1?"":"s"} selected.`:"No outputs selected.";
}

function openCompareExportDialog(group=""){
  prepareFullExportControls();renderExportGeoControls();updateExportLinks();
  document.querySelectorAll(".compare-export-options section").forEach((section)=>section.classList.remove("export-focus"));
  $("compareExportDialog").showModal();
  if(group){const section=document.querySelector(`[data-export-group="${group}"]`);section?.classList.add("export-focus");section?.scrollIntoView({block:"nearest"});}
}
$("openCompareExports").addEventListener("click",()=>openCompareExportDialog());

function changeSummaryParams(scanId, result) {
  const [reference,...comparisons]=state.comparisonIds;
  const params=new URLSearchParams({reference,comparisons:comparisons.join(","),year:result?.year||$("compareYear").value,filterField:result?.filterField||"",scanId:scanId||""});
  if(result?.filterValues?.length)params.set("filterValue",result.filterValues.join("|"));
  return params;
}

function compareExportFilename(label, extension) {
  const now=new Date(),pad=(value)=>String(value).padStart(2,"0");
  const stamp=`${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} ${pad(now.getHours())}.${pad(now.getMinutes())}.${pad(now.getSeconds())}`;
  return `VE ${label} ${stamp}.${extension}`;
}

function comparisonExportRequest(changedOnly=false) {
  const payload=state.lastComparison;
  if(!payload)return null;
  return {
    reference:payload.reference.id,
    comparisons:(payload.comparisons||[]).map((item)=>item.id),
    table:payload.table,
    variable:payload.variable,
    year:payload.year,
    changedOnly,
    limit:0,
    offset:0,
    filterField:payload.filterField||"",
    filterValues:payload.filterValues||[],
    sortColumn:payload.sortColumn||"id",
    sortDirection:payload.sortDirection||"original",
    mode:payload.mode||"records",
    comparisonToken:payload.comparisonToken||"",
  };
}

function comparisonExportParams(changedOnly=false) {
  const request= comparisonExportRequest(changedOnly);
  const params=new URLSearchParams({reference:request.reference,comparisons:request.comparisons.join(","),table:request.table,variable:request.variable,year:request.year,mode:request.mode,changedOnly:String(changedOnly),limit:"0",offset:"0",filterField:request.filterField,sortColumn:request.sortColumn,sortDirection:request.sortDirection});
  if(request.filterValues.length)params.set("filterValue",request.filterValues.join("|"));
  if(request.comparisonToken)params.set("comparisonToken",request.comparisonToken);
  return params;
}

async function saveBackendExport(kind, paramsOverride=null, filenameOverride="") {
  const configuration={
    "comparison-current-csv":{params:()=>comparisonExportParams(false),filename:compareExportFilename("current view","csv"),route:"/api/comparison/export-current"},
    "comparison-changed-csv":{params:()=>comparisonExportParams(true),filename:compareExportFilename("changed rows in current view","csv"),route:"/api/comparison/export-filtered-changes"},
    "comparison-scan-csv":{params:()=>changeSummaryParams(state.comparisonScanId,state.comparisonScan),filename:compareExportFilename("changed outputs","csv"),route:"/api/comparison/export-change-summary"},
    "comparison-map-csv":{params:comparisonMapExportParams,filename:compareExportFilename("comparison map data","csv"),route:"/api/comparison/export-map-csv"},
    "dashboard-pdf":{params:dashboardExportParams,filename:compareExportFilename("percent-change chart","pdf"),route:"/api/comparison/export-dashboard-pdf"},
    "dashboard-csv":{params:dashboardExportParams,filename:compareExportFilename("percent-change chart","csv"),route:"/api/comparison/export-dashboard-csv"},
  }[kind];
  if(!configuration)return;
  const query=(paramsOverride||configuration.params()).toString(),filename=filenameOverride||configuration.filename,invoke=window.__TAURI_INTERNALS__?.invoke;
  if(invoke){const saved=await invoke("save_backend_export",{exportKind:kind,query,filename});if(saved)notify(`Saved ${saved}.`,"success");return saved;}
  const link=document.createElement("a");link.href=`${configuration.route}?${query}`;link.download=filename;document.body.appendChild(link);link.click();link.remove();return filename;
}

function dashboardExportParams(){const settings=dashboardDisplaySettings(),palette=comparisonPalettes().chart;return new URLSearchParams({dashboardToken:state.dashboardPayload?.dashboardToken||"",sortBy:settings.sortBy,displayMode:settings.displayMode,threshold:String(settings.threshold),count:String(settings.count),hideZero:String(settings.hideZero),increaseColor:palette.increase,decreaseColor:palette.decrease,neutralColor:palette.neutral});}

function workbookRequest(kind, override={}) {
  if(kind==="full-variables")return{kind,format:override.format,reference:state.comparisonIds[0],comparisons:state.comparisonIds.slice(1),year:$("fullExportYear").value,variableKeys:[...state.fullExportVariableKeys]};
  if(kind==="dashboard")return{kind,dashboardToken:state.dashboardPayload?.dashboardToken||"",...dashboardDisplaySettings(),palette:comparisonPalettes().chart};
  if(kind==="comparison-map")return{kind,mapToken:state.mapPayload?.mapToken||"",scopeIds:[...comparisonMapScopeIds()],scopeLabel:"Project geography"};
  if (kind === "change-scan") {
    const [reference,...comparisons]=state.comparisonIds;
    return {kind,reference,comparisons,year:override.result?.year||$("compareYear").value,filterField:override.result?.filterField||"",filterValues:override.result?.filterValues||[],scanId:override.scanId||""};
  }
  return {...comparisonExportRequest(kind==="filtered"),kind};
}

async function exportArtifact(kind, override={}) {
  if(kind==="dashboard"){
    if(!state.dashboardPayload?.dashboardToken||state.dashboardDirty)return notify("Generate the chart before exporting it.","error");
  } else if(kind==="comparison-map") {
    if(!state.mapPayload?.mapToken||state.mapDirty)return notify("Generate the map before exporting it.","error");
  } else if (kind === "change-scan") {
    if (!override.scanId || !override.result) return notify("Prepare the changed-output scan before exporting.", "error");
  } else if(kind==="full-variables"){
    if(!state.fullExportVariableKeys.size)return notify("Select at least one output to export.","error");
  } else if (!state.lastComparison) {
    return notify("Run a comparison before exporting the current view.", "error");
  }
  $("compareExportDialog").close();
  const isZip=kind==="full-variables"&&override.format==="csv-zip",artifactLabel=isZip?"CSV ZIP":kind==="comparison-map"?"map workbook":"Excel workbook";
  startCompareActivity(`Preparing ${artifactLabel}`, "Querying the selected comparison data.");
  try {
    const operation=await post("/api/comparison/exports/start",workbookRequest(kind,override)); state.comparisonExportOperationId=operation.id;
    let status=operation;
    while(["waiting","running"].includes(status.state)){
      setCompareActivityPhase(status.phase==="workbook"?`Formatting ${artifactLabel}`:isZip?"Packaging CSV files":"Querying comparison data",status.message||`Preparing ${artifactLabel}.`);
      await new Promise((resolve)=>setTimeout(resolve,500));
      status=await request(`/api/comparison/exports/status?id=${encodeURIComponent(operation.id)}`);
    }
    if(status.state==="cancelled")throw new DOMException("Stopped","AbortError");
    if(status.state!=="succeeded")throw new Error(status.message||"Excel export failed");
    if(window.__TAURI_INTERNALS__?.invoke){
      const saved=await window.__TAURI_INTERNALS__.invoke("save_comparison_export",{operationId:operation.id,filename:status.filename||"visioneval_comparison.xlsx"});
      if(!saved){finishCompareActivity("failed","Export save cancelled","No file was written.");return;}
      finishCompareActivity("succeeded",`${artifactLabel} saved`,saved);
    }else{
      const link=document.createElement("a");link.href=`/api/comparison/exports/download?id=${encodeURIComponent(operation.id)}`;link.download=status.filename||"visioneval_comparison.xlsx";document.body.appendChild(link);link.click();link.remove();
      finishCompareActivity("succeeded",`${artifactLabel} ready`,status.filename||"The download has started.");
    }
  }catch(error){
    if(state.compareActivity?.status==="running")finishCompareActivity("failed",error.name==="AbortError"?"Export stopped":"Export failed",error.name==="AbortError"?"The export was stopped.":error.message);
    if(error.name!=="AbortError")notify(error.message,"error");
  }finally{state.comparisonExportOperationId="";}
}

async function prepareChangedOutputExport(scope,format){
  const selected=scope==="selected",filterField=selected?state.exportFilterField:"",filterValues=selected?[...state.exportFilterValues]:[];
  if(selected&&(!filterField||!filterValues.length))return notify("Choose at least one export location.","error");
  $("compareExportDialog").close();startCompareActivity("Preparing changed-output export","Checking the scan cache.");
  try{
    const [reference,...comparisons]=state.comparisonIds,operation=await post("/api/comparison/scans/start",{reference,comparisons,year:$("compareYear").value,filterField,filterValues});state.comparisonScanOperationId=operation.id;let status=operation;
    while(["waiting","running"].includes(status.state)){const progress=status.progress||{};setCompareActivityPhase("Preparing changed-output export",progress.total?`Scanning ${progress.completed||0} of ${progress.total}${progress.table?`: ${progress.table} / ${progress.variable}`:""}`:status.message||"Preparing scan.");await new Promise((resolve)=>setTimeout(resolve,500));status=await request(`/api/comparison/scans/status?id=${encodeURIComponent(operation.id)}`);}
    if(status.state==="cancelled")throw new DOMException("Stopped","AbortError");if(status.state!=="succeeded")throw new Error(status.message||"Changed-output scan failed");
    finishCompareActivity("succeeded","Changed-output data ready",status.cached?"Loaded a matching cached scan.":"The changed-output scan completed.");
    if(format==="csv")return saveBackendExport("comparison-scan-csv",changeSummaryParams(operation.id,status.result),compareExportFilename(`${scope} locations changed outputs`,"csv"));
    return exportArtifact("change-scan",{scanId:operation.id,result:status.result});
  }catch(error){if(state.compareActivity?.status==="running")finishCompareActivity("failed",error.name==="AbortError"?"Export stopped":"Export failed",error.name==="AbortError"?"The export was stopped.":error.message);if(error.name!=="AbortError")notify(error.message,"error");}
  finally{state.comparisonScanOperationId="";}
}

$("exportCurrentWorkbook").addEventListener("click",()=>exportArtifact("current"));
function startVisibleBackendExport(kind) {
  $("compareExportDialog").close();
  saveBackendExport(kind).catch((error)=>notify(error.message||String(error),"error"));
}
$("exportCurrentComparison").addEventListener("click",()=>startVisibleBackendExport("comparison-current-csv"));
$("exportAllChangedCsv").addEventListener("click",()=>prepareChangedOutputExport("all","csv"));
$("exportAllChangedWorkbook").addEventListener("click",()=>prepareChangedOutputExport("all","xlsx"));
$("exportSelectedChangedCsv").addEventListener("click",()=>prepareChangedOutputExport("selected","csv"));
$("exportSelectedChangedWorkbook").addEventListener("click",()=>prepareChangedOutputExport("selected","xlsx"));
$("fullExportYear").addEventListener("change",()=>{state.fullExportVariableKeys.clear();renderFullExportVariableList();});
$("fullExportVariableSearch").addEventListener("input",(event)=>{state.fullExportVariableQuery=event.target.value;renderFullExportVariableList();});
$("selectFullExportVariables").addEventListener("click",()=>{document.querySelectorAll("[data-full-export-variable]").forEach((box)=>state.fullExportVariableKeys.add(box.dataset.fullExportVariable));renderFullExportVariableList();});
$("clearFullExportVariables").addEventListener("click",()=>{state.fullExportVariableKeys.clear();renderFullExportVariableList();});
$("exportFullVariablesZip").addEventListener("click",()=>exportArtifact("full-variables",{format:"csv-zip"}));
$("exportFullVariablesWorkbook").addEventListener("click",()=>exportArtifact("full-variables",{format:"xlsx"}));

function humanBytes(value) {
  const bytes=Number(value)||0, units=["B","KB","MB","GB","TB"]; let amount=bytes,index=0;
  while(amount>=1000&&index<units.length-1){amount/=1000;index++;}
  return `${amount.toFixed(index>1?1:0)} ${units[index]}`;
}

function runtimeProfile() {
  return (state.desktop?.runtimeProfiles || []).find((item) => item.id === state.desktop?.activeRuntimeProfileId);
}

function runtimeSetupSnapshot() {
  const runtime = state.data?.runtime || {};
  const profile = runtimeProfile();
  const native = runtime.adapter === "native";
  const verified = Boolean(profile?.verified && runtime.imagePresent && (native || (runtime.digestMatches !== false && runtime.provenanceMatches !== false)));
  return {runtime, profile, native, verified};
}

function setRuntimeSetupStatus(element, message, tone = "") {
  if (!element) return;
  const icon = tone === "success" ? "✓" : tone === "error" ? "!" : tone === "progress" ? "…" : "";
  element.className = `runtime-setup-status ${tone}`.trim();
  element.innerHTML = icon ? `<span class="runtime-setup-status-icon" aria-hidden="true">${icon}</span><span>${escapeHtml(message)}</span>` : escapeHtml(message);
}

function styleRuntimeAction(button, {hidden = false, enabled = true, label, primary = false, disabledReason = ""} = {}) {
  if (!button) return;
  button.hidden = hidden;
  if (label) button.textContent = label;
  button.classList.toggle("secondary", !primary);
  setButtonAvailability(button, enabled, disabledReason);
}

function renderRuntimeSetupControls() {
  const {runtime, native, verified} = runtimeSetupSnapshot();
  const busy = state.runtimeSetupPhase === "installing" || state.runtimeSetupPhase === "verifying";
  if (native) {
    const canVerify = Boolean(runtime.imagePresent && runtime.executable);
    styleRuntimeAction($("onboardingVerify"), {enabled:canVerify, label:verified?"Verify again":"Verify runtime", disabledReason:"Choose the runtime paths first."});
    styleRuntimeAction($("settingsVerifyRuntime"), {enabled:canVerify, label:verified?"Verify again":"Verify runtime", disabledReason:"Choose the runtime paths first."});
    return;
  }

  const imagePresent = Boolean(runtime.imagePresent);
  const canVerify = Boolean(runtime.running && imagePresent && !busy);
  const failed = state.runtimeSetupPhase === "failed";
  const message = state.runtimeSetupMessage || (!verified && runtime.error) || (verified
    ? "Runtime installed, verified, and connected."
    : imagePresent
      ? "The runtime image is installed but still needs verification."
      : !runtime.installed
        ? "Docker Desktop is not installed. Install it before adding the VisionEval runtime."
        : runtime.running
          ? "Docker is ready. Install the pinned VisionEval runtime to enable runs."
          : "Docker Desktop is installed but stopped. Install runtime will start it and continue.");
  const tone = busy ? "progress" : verified ? "success" : failed || runtime.error ? "error" : "";
  setRuntimeSetupStatus($("onboardingRuntimeStatus"), message, tone);
  setRuntimeSetupStatus($("settingsRuntimeStatus"), message, tone);

  const installLabel = busy && state.runtimeSetupPhase === "installing" ? "Installing…" : failed || imagePresent ? "Retry installation" : "Install runtime";
  const installEnabled = Boolean(runtime.installed && !busy);
  const installReason = !runtime.installed ? "Install Docker Desktop before installing the VisionEval runtime." : busy ? "Runtime setup is in progress." : "";
  styleRuntimeAction($("onboardingInstallRuntime"), {hidden:verified, enabled:installEnabled, label:installLabel, primary:!imagePresent, disabledReason:installReason});
  styleRuntimeAction($("settingsInstallRuntime"), {hidden:verified, enabled:installEnabled, label:installLabel, primary:!imagePresent, disabledReason:installReason});

  const verifyLabel = busy && state.runtimeSetupPhase === "verifying" ? "Verifying…" : verified ? "Verify again" : "Verify runtime";
  const verifyReason = !runtime.running ? "Start Docker Desktop before verifying the runtime." : !imagePresent ? "Install the pinned runtime image first." : busy ? "Runtime setup is in progress." : "";
  styleRuntimeAction($("onboardingVerify"), {hidden:!imagePresent, enabled:canVerify, label:verifyLabel, primary:imagePresent&&!verified, disabledReason:verifyReason});
  styleRuntimeAction($("settingsVerifyRuntime"), {hidden:!imagePresent, enabled:canVerify, label:verifyLabel, primary:imagePresent&&!verified, disabledReason:verifyReason});

  if ($("onboardingSkip")) {
    $("onboardingSkip").hidden = verified;
    setButtonAvailability($("onboardingSkip"), !busy, busy ? "Runtime setup is in progress." : "");
  }
  if ($("onboardingRuntimeGuide")) setButtonAvailability($("onboardingRuntimeGuide"), !busy, busy ? "Runtime setup is in progress." : "");
  if ($("onboardingStartDocker")) $("onboardingStartDocker").hidden = verified || !runtime.installed || runtime.running;
  if ($("settingsStartDocker")) $("settingsStartDocker").hidden = verified || !runtime.installed || runtime.running;
}

function maybeShowOnboarding() {
  if (!window.__TAURI_INTERNALS__?.invoke || state.onboardingShown || (state.desktop?.onboardingVersion || 0) >= 1) return;
  state.onboardingShown = true;
  const {runtime,native,profile}=runtimeSetupSnapshot();
  if(native&&$("onboardingNativePaths")){
    $("onboardingNativePaths").hidden=false;
    $("onboardingVeRuntime").value=profile?.veRuntimePath||runtime.veRuntime||"";
    $("onboardingVeHome").value=profile?.veHomePath||runtime.veHome||runtime.image||"";
    $("onboardingRscript").value=profile?.rscriptPath||runtime.executable||"";
  }
  $("onboardingRuntimeHelp").textContent=native?"Choose the VE_RUNTIME folder used to launch VisionEval. Workbench will detect VE_HOME and its matching Rscript when possible.":"macOS uses the verified VisionEval Docker runtime.";
  $("onboardingRuntimeStatus").textContent=native?(runtime.error||((runtime.imagePresent&&runtime.executable)?"Runtime paths detected. Verify them to enable runs.":"Choose VE_RUNTIME first. You can review or override the detected VE_HOME and Rscript paths.")):runtime.error||(!runtime.installed?"Docker Desktop is not installed. You can skip and set it up later.":runtime.imagePresent?`Found ${runtime.image}. Verify it or select Install runtime to reinstall the pinned image.`:runtime.running?"Docker is ready. Select Install runtime to download, verify, and connect the pinned image.":"Docker Desktop is installed but stopped. Install runtime will start it and continue.");
  if($("onboardingInstallRuntime"))setButtonAvailability($("onboardingInstallRuntime"),Boolean(runtime.installed),"Install Docker Desktop before installing the VisionEval runtime.");
  if($("onboardingStartDocker"))$("onboardingStartDocker").hidden=native||!runtime.installed||runtime.running;
  const canVerify=native?Boolean($("onboardingVeRuntime")?.value&&$("onboardingVeHome")?.value&&$("onboardingRscript")?.value):Boolean(runtime.running&&runtime.imagePresent);
  setButtonAvailability($("onboardingVerify"),canVerify,native?"Choose the VE_RUNTIME, VE_HOME, and Rscript paths first.":!runtime.running?"Start Docker Desktop, then return to verify the runtime.":"Select Install runtime first, then verify it again if needed.");
  renderRuntimeSetupControls();
  $("onboardingDialog").showModal();
}

function closeWorkspaceMenus(except=null) {
  document.querySelectorAll("[data-workspace-menu]").forEach((menu)=>{if(menu!==except)menu.hidden=true;});
  document.querySelectorAll("[data-toggle-workspace-menu]").forEach((button)=>{if(!except||button.getAttribute("aria-controls")!==except.id)button.setAttribute("aria-expanded","false");});
}

function renderSettingsWorkspaces() {
  const recents=(state.desktop?.recentWorkspaces||[]).filter((item)=>!item.current);
  $("settingsWorkspacePath").textContent=state.desktop?.workspaceDisplayPath||state.desktop?.workspaceRoot||"";
  $("settingsWorkspacePath").title=state.desktop?.workspaceRoot||"";
  $("settingsRecentCount").textContent=String(recents.length);
  $("settingsRecent").innerHTML=recents.length?recents.map((item,index)=>{
    const menuId=`workspaceMenu${index}`;
    return `<article class="workspace-recent-row"><div class="workspace-recent-details"><strong>${escapeHtml(item.name)}</strong><small title="${escapeHtml(item.path)}">${escapeHtml(item.displayPath||item.path)}</small><span class="workspace-status ${item.valid?"valid":"invalid"}">${escapeHtml(item.status)}</span></div><div class="workspace-row-actions"><button type="button" class="secondary" data-open-workspace="${index}" ${item.valid?"":"disabled"}>Open</button><div class="workspace-action-menu"><button type="button" class="secondary icon-button" data-toggle-workspace-menu="${index}" aria-label="Actions for ${escapeHtml(item.name)}" aria-haspopup="menu" aria-expanded="false" aria-controls="${menuId}">⋯</button><div id="${menuId}" data-workspace-menu role="menu" hidden><button type="button" data-forget-workspace="${index}" role="menuitem">Forget</button><button type="button" class="danger-text" data-trash-workspace="${index}" role="menuitem" ${item.removable?"":"disabled"}>Move to Trash…</button></div></div></div></article>`;
  }).join(""):`<p class="muted">No other recent workspaces.</p>`;
  document.querySelectorAll("[data-open-workspace]").forEach((button)=>button.addEventListener("click",()=>changeWorkspace(recents[Number(button.dataset.openWorkspace)].path)));
  document.querySelectorAll("[data-toggle-workspace-menu]").forEach((button)=>button.addEventListener("click",(event)=>{event.stopPropagation();const menu=$(button.getAttribute("aria-controls")),open=menu.hidden;closeWorkspaceMenus(open?menu:null);menu.hidden=!open;button.setAttribute("aria-expanded",String(open));}));
  document.querySelectorAll("[data-workspace-menu]").forEach((menu)=>menu.addEventListener("click",(event)=>event.stopPropagation()));
  document.querySelectorAll("[data-forget-workspace]").forEach((button)=>button.addEventListener("click",async()=>{const item=recents[Number(button.dataset.forgetWorkspace)];closeWorkspaceMenus();if(!await confirmWorkbench(`Forget ${item.name}?\n\nIts files will remain at ${item.path}.`))return;try{await window.__TAURI_INTERNALS__.invoke("forget_workspace",{id:item.id,path:item.path});state.desktop=await window.__TAURI_INTERNALS__.invoke("desktop_state");renderSettingsWorkspaces();notify("Workspace removed from recents.","success")}catch(error){notify(String(error),"error")}}));
  document.querySelectorAll("[data-trash-workspace]").forEach((button)=>button.addEventListener("click",async()=>{const item=recents[Number(button.dataset.trashWorkspace)];closeWorkspaceMenus();if(!await confirmWorkbench(`Move ${item.name} to Trash?\n\nThis moves the complete workspace folder, including its projects, assets, runs, and results. You can recover it from Trash until Trash is emptied.`))return;try{await window.__TAURI_INTERNALS__.invoke("trash_workspace",{id:item.id,path:item.path});state.desktop=await window.__TAURI_INTERNALS__.invoke("desktop_state");renderSettingsWorkspaces();notify("Workspace moved to Trash.","success")}catch(error){notify(String(error),"error")}}));
}

$("onboardingVerify").addEventListener("click",event=>verifyRuntimeFromSetup(event.currentTarget).catch(()=>{}));
if($("onboardingInstallRuntime"))$("onboardingInstallRuntime").addEventListener("click",event=>installAndSaveRuntime(event.currentTarget,$("onboardingRuntimeStatus")).catch(()=>{}));
if($("onboardingStartDocker"))$("onboardingStartDocker").addEventListener("click",event=>startDockerAndVerify(event.currentTarget));
$("onboardingRuntimeGuide").addEventListener("click",()=>$("runtimeGuideDialog").showModal());
function updateNativeVerifyAvailability(){
  if($("onboardingVeRuntime"))$("onboardingVerify").disabled=!($("onboardingVeRuntime").value&&$("onboardingVeHome").value&&$("onboardingRscript").value);
  if($("settingsVeRuntime"))$("settingsVerifyRuntime").disabled=!($("settingsVeRuntime").value&&$("settingsVeHome").value&&$("settingsRscript").value);
}

function renderAggregateComparison(payload) {
  const summaries = payload.aggregateSummaries || [];
  const labels = [payload.reference?.label || "Reference", ...(payload.comparisons || []).map((item) => item.label)];
  const changes = payload.aggregateChanges || [];
  const numeric = summaries[0]?.kind === "numeric";
  const summaryMarkup = numeric
    ? changes.map((change,index) => {
        const reference = summaries[0] || {}, comparison = summaries[index + 1] || {};
        const averagePercent = change.measures?.mean?.percentChange;
        const headline = averagePercent == null ? "Not available" : `${averagePercent > 0 ? "+" : ""}${percentage(averagePercent)}%`;
        return `<article class="aggregate-result aggregate-distribution"><div class="aggregate-result-heading"><div><h4>${escapeHtml(change.label)}</h4><p class="muted">Compared with ${escapeHtml(labels[0])}</p></div><div class="aggregate-average-change"><small>Average change</small><strong>${escapeHtml(headline)}</strong></div></div>${iqrComparison(reference,comparison,labels[0],labels[index+1]||change.label)}<p class="aggregate-context"><span>Records: <strong>${escapeHtml(number(reference.recordCount))}</strong> → <strong>${escapeHtml(number(comparison.recordCount))}</strong></span><span>Mean: <strong>${escapeHtml(number(reference.mean))}</strong> → <strong>${escapeHtml(number(comparison.mean))}</strong></span></p></article>`;
      }).join("")
    : summaries.map((summary,index) => `<article class="aggregate-result"><h4>${escapeHtml(labels[index] || `Result ${index+1}`)}</h4><div class="aggregate-metrics">${metric("Record count",summary.recordCount)}${metric("Missing",summary.missingCount)}${metric("Categories",summary.categories?.length || 0)}</div><div class="table-wrap"><table><thead><tr><th>Category</th><th>Count</th><th>Share</th></tr></thead><tbody>${(summary.categories||[]).map((item)=>`<tr><td>${escapeHtml(item.label)}</td><td>${escapeHtml(number(item.count))}</td><td>${escapeHtml(percentage(item.share))}%</td></tr>`).join("")}</tbody></table></div></article>`).join("");
  $("comparisonStats").hidden = false;
  $("comparisonStats").innerHTML = `<div class="notice guidance-notice"><strong>Aggregate synthetic-population comparison</strong><p>Records are summarized independently because IDs are run-local and are not assumed to identify the same entity.</p></div><div class="aggregate-comparison">${summaryMarkup}</div>`;
}
async function discoverNativePaths(prefix){
  const veRuntime=$(`${prefix}VeRuntime`).value;
  const detected=await post("/api/runtime/discover",{veRuntime});
  if(detected.veRuntime)$(`${prefix}VeRuntime`).value=detected.veRuntime;
  if(detected.veHome)$(`${prefix}VeHome`).value=detected.veHome;
  if(detected.rscript)$(`${prefix}Rscript`).value=detected.rscript;
  updateNativeVerifyAvailability();
  notify(detected.veHome&&detected.rscript?"VE_HOME and Rscript were detected. Review them, then verify.":"VE_RUNTIME selected. Review the advanced paths before verification.",detected.veHome&&detected.rscript?"success":"");
}
async function chooseNativePath(inputId, command, discoverPrefix=""){try{const path=await window.__TAURI_INTERNALS__.invoke(command);if(path){$(inputId).value=path;if(discoverPrefix)await discoverNativePaths(discoverPrefix);else updateNativeVerifyAvailability()}}catch(error){notify(String(error),"error")}}
if($("onboardingChooseVeRuntime"))$("onboardingChooseVeRuntime").addEventListener("click",()=>chooseNativePath("onboardingVeRuntime","choose_folder","onboarding"));
if($("onboardingChooseVeHome"))$("onboardingChooseVeHome").addEventListener("click",()=>chooseNativePath("onboardingVeHome","choose_folder"));
if($("onboardingChooseRscript"))$("onboardingChooseRscript").addEventListener("click",()=>chooseNativePath("onboardingRscript","choose_rscript"));
if($("settingsChooseVeRuntime"))$("settingsChooseVeRuntime").addEventListener("click",()=>chooseNativePath("settingsVeRuntime","choose_folder","settings"));
if($("settingsChooseVeHome"))$("settingsChooseVeHome").addEventListener("click",()=>chooseNativePath("settingsVeHome","choose_folder"));
if($("settingsChooseRscript"))$("settingsChooseRscript").addEventListener("click",()=>chooseNativePath("settingsRscript","choose_rscript"));
$("onboardingSkip").addEventListener("click",()=>{state.runtimeSetupPhase="idle";state.runtimeSetupMessage="Runtime setup skipped. Run remains unavailable; all other tabs continue to work.";renderRuntimeSetupControls();notify("Runtime setup skipped for now.")});
$("finishOnboarding").addEventListener("click",async()=>{try{await window.__TAURI_INTERNALS__.invoke("complete_onboarding");state.desktop=await window.__TAURI_INTERNALS__.invoke("desktop_state");$("onboardingDialog").close();notify("Workspace setup complete.","success");renderAll()}catch(error){notify(String(error),"error")}});

function updateParallelMemoryGuide(){
  const runs=Math.max(1,Number($("maxConcurrentRuns")?.value||1));
  const runtime=state.data?.runtime||{},availableBytes=Number(runtime.dockerMemoryBytes||0),availableGb=availableBytes/1024**3;
  const formatGb=(value)=>Number(value).toLocaleString(undefined,{maximumFractionDigits:1});
  const runWords=["Zero","One","Two","Three","Four","Five","Six","Seven","Eight"];
  const runLabel=runWords[runs]||String(runs);
  const mpoLow=runs*2.5,mpoHigh=runs*3.5,statewideLow=runs*24,statewideHigh=runs*32;
  const allocationAssessment=availableBytes?(availableGb<mpoLow?`The current ${humanBytes(availableBytes)} Docker allocation is below the planning range; runs may fail or be killed for memory pressure.`:availableGb<=mpoHigh?`The current ${humanBytes(availableBytes)} Docker allocation is tight.`:`The current ${humanBytes(availableBytes)} Docker allocation is above the planning range, although actual use varies.`):"Docker Desktop allocation is unavailable while its engine is stopped.";
  $("dockerMemory").textContent=runtime.adapter==="native"?"Windows native runs are serialized so the connected VE_Runtime is used by only one run at a time.":availableBytes?`Docker Desktop allocation: ${humanBytes(availableBytes)} shared by all active containers.`:"Docker Desktop allocation is unavailable while its engine is stopped.";
  $("parallelMemoryGuide").textContent=`MPO/regional models: ${runLabel} concurrent MPO run${runs===1?"":"s"} may use approximately ${formatGb(mpoLow)}–${formatGb(mpoHigh)} GB of Docker memory (2.5–3.5 GB per active run). ${allocationAssessment}`;
  $("parallelMemoryGuide").classList.toggle("warning-notice",Boolean(availableBytes&&availableGb<=mpoHigh));
  $("statewideMemoryGuide").textContent=`A statewide Virginia model is provisionally estimated at 24–32 GB per active run (will be updated once tested). At ${runs} concurrent run${runs===1?"":"s"}, that is approximately ${formatGb(statewideLow)}–${formatGb(statewideHigh)} GB. Run the first statewide baseline by itself.`;
  $("statewideMemoryGuide").classList.toggle("warning-notice",Boolean(availableBytes&&availableGb<statewideLow));
  const cap=Number($("memoryLimit")?.value||0),capGuide=$("memoryLimitGuide");
  if(!cap){
    capGuide.textContent="No Workbench limit—each run can use the shared Docker allocation. Concurrency reserves no memory.";
    capGuide.classList.remove("warning-text");
  }else{
    const aggregate=cap*runs,capRisk=cap<2.5?" This is below the MPO/regional planning range and may terminate a run.":cap<24?" This is below the provisional statewide estimate; do not use it for a statewide run before testing.":"";
    capGuide.textContent=`Workbench passes ${formatGb(cap)} GB as Docker’s --memory limit for each new run. ${runs} run${runs===1?"":"s"} could use up to ${formatGb(aggregate)} GB, but all still share ${availableBytes?humanBytes(availableBytes):"Docker Desktop’s allocation"}. The limit does not reserve memory, does not increase Docker’s allocation, can terminate a run that reaches it, and does not affect containers already running.${capRisk}`;
    capGuide.classList.toggle("warning-text",Boolean(capRisk||(availableBytes&&aggregate>availableGb)));
  }
}
async function openSettings(page="settingsWorkspace") {
  if (!window.__TAURI_INTERNALS__?.invoke) return notify("Settings are available in the desktop app.","error");
  state.desktop=await window.__TAURI_INTERNALS__.invoke("desktop_state");
  state.desktop.comparisonPalettes=storedComparisonPalettes();
  applyComparisonPalettes();
  renderComparisonPaletteSettings();
  const workspaceSettings=state.data?.workspaceSettings||{};
  renderSettingsWorkspaces();
  const libraries=state.data?.inputLibraries||[],explanations=state.data?.inputExplanations||[];
  $("defaultLibrary").innerHTML=`<option value="">No default</option>${libraries.map(item=>`<option value="${escapeHtml(item.id)}" ${item.pairingStatus === "paired" ? "" : "disabled"}>${escapeHtml(item.name)}${item.pairingStatus === "paired" ? "" : " · package repair required"}</option>`).join("")}`;
  $("defaultInputExplanations").innerHTML=`<option value="">Built-in module metadata</option>${explanations.map(item=>`<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}${item.familyConflict?" · ⚠ different catalog":""}</option>`).join("")}`;
  selectedOption($("defaultLibrary"),workspaceSettings.defaultInputLibraryId||"");selectedOption($("defaultInputExplanations"),workspaceSettings.defaultInputExplanationId||"");
  const precision={default:2,singleFile:null,batch:null,output:null,percentage:null,...(workspaceSettings.numericPrecision||{})};
  $("precisionDefault").value=precision.default;
  const precisionOptions=`<option value="">Use default</option>${Array.from({length:9},(_,value)=>`<option value="${value}">${value} decimal place${value===1?"":"s"}</option>`).join("")}`;
  [["precisionSingleFile","singleFile"],["precisionBatch","batch"],["precisionOutput","output"],["precisionPercentage","percentage"]].forEach(([id,key])=>{$(id).innerHTML=precisionOptions;$(id).value=precision[key]==null?"":String(precision[key]);});
  renderInstalledAssetGroups();
  $("retainExports").checked=workspaceSettings.retainFullExports!==false;
  renderUpdateSettings(state.data?.updates||{...workspaceSettings.updateChecks,statuses:workspaceSettings.updateChecks?.statuses||{}});
  $("appearanceSetting").value=state.desktop.theme||"system";$("notificationsEnabled").checked=Boolean(state.desktop.notificationsEnabled);$("notificationSuccessThreshold").value=String(state.desktop.notificationSuccessThresholdSeconds||60);$("defaultRunMode").value=state.desktop.resources?.defaultRunMode||"queued";$("autoStartDocker").checked=state.desktop.autoStartDocker!==false;$("memoryLimit").value=state.desktop.resources?.memoryLimitGb??"";
  const runtime=state.data?.runtime||{},profile=runtimeProfile();
  const native=runtime.adapter==="native";
  $("notificationsPlatformLabel").textContent=native?"Show Windows notifications for background work":"Show macOS notifications for background work";
  $("notificationsPlatformHelp").textContent=`Successful work notifies only after the selected delay. Failures notify immediately. ${native?"Windows":"macOS"} notifications stay silent while Workbench is focused because the status is already visible here.`;
  $("defaultRunMode").value=native?"queued":state.desktop.resources?.defaultRunMode||"queued";
  $("defaultRunMode").disabled=native;
  $("maxConcurrentRuns").value=String(native?1:(state.desktop.resources?.maxConcurrentRuns||2));
  $("maxConcurrentRuns").disabled=native;
  $("autoStartDocker").closest("label").hidden=native;
  $("memoryLimit").closest("label").hidden=native;
  if(native&&$("settingsNativePaths")){
    $("settingsNativePaths").hidden=false;
    $("settingsVeRuntime").value=profile?.veRuntimePath||runtime.veRuntime||"";
    $("settingsVeHome").value=profile?.veHomePath||runtime.veHome||runtime.image||"";
    $("settingsRscript").value=profile?.rscriptPath||runtime.executable||"";
  }
  const digest=profile?.imageDigest||"Not verified";
  $("settingsRuntimeSummary").innerHTML=[["Adapter",profile?.adapter||"Not configured"],["Platform",profile?`${profile.platform} / ${profile.architecture}`:"—"],["Image",profile?.imageReference||runtime.image||"—"],["Release",`${runtime.imageReleaseTag||"VisionEval"}${runtime.imageRevision?` · ${runtime.imageRevision.slice(0,12)}`:""}`],["Compatibility",runtime.imageCompatibilityPatch?"Workbench compatibility verified":"Not detected"],["Last verified",profile?.verifiedAt||"Never"]].map(([label,value])=>`<div class="runtime-fact"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`).join("")+`<div class="runtime-fact digest"><small>Digest</small><div class="runtime-digest"><code title="${escapeHtml(digest)}">${escapeHtml(digest)}</code><button id="copyRuntimeDigest" type="button" class="secondary" ${digest==="Not verified"?"disabled":""}>Copy Digest</button></div></div>`;
  if(native) $("settingsRuntimeSummary").innerHTML=[["Adapter","Native VisionEval"],["Version",profile?.runtimeVersion||"Not verified"],["VE_RUNTIME",profile?.veRuntimePath||runtime.veRuntime||"—"],["VE_HOME",profile?.veHomePath||runtime.veHome||runtime.image||"—"],["Rscript",profile?.rscriptPath||runtime.executable||"—"],["Run mode","Queued / one at a time"],["Last verified",profile?.verifiedAt||"Never"]].map(([label,value])=>`<div class="runtime-fact"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`).join("");
  if($("settingsInstallRuntime"))setButtonAvailability($("settingsInstallRuntime"),Boolean(runtime.installed),"Install Docker Desktop before installing the VisionEval runtime.");
  if($("settingsStartDocker"))$("settingsStartDocker").hidden=native||!runtime.installed||runtime.running;
  $("settingsVerifyRuntime").disabled=native?!($("settingsVeRuntime")?.value&&$("settingsVeHome")?.value&&$("settingsRscript")?.value):!runtime.running||!runtime.imagePresent;
  if($("copyRuntimeDigest")) $("copyRuntimeDigest").addEventListener("click",async()=>{try{await navigator.clipboard.writeText(digest);notify("Runtime digest copied.","success")}catch(error){notify("The digest could not be copied.","error")}});
  updateParallelMemoryGuide();
  renderRuntimeSetupControls();
  switchSettingsPage(page);if(!$("settingsDialog").open)$("settingsDialog").showModal();
}
function renderInstalledAssetGroups(){
  const explanations=state.data?.inputExplanations||[],regions=state.data?.regionPackages||[],libraries=state.data?.inputLibraries||[],templates=state.data?.templates||[];
  const dependencies=new Map((state.data?.assets?.installed||[]).map(item=>[`${item.asset.kind}:${item.asset.id}`,item]));
  const kindFor={regions:"regional-data",explanations:"input-explanations",libraries:"input-library",templates:"model-template"};
  const group=(title,items,kind)=>`<details class="asset-group" ${kind==="regions"&&items.length?"open":""}><summary><span>${escapeHtml(title)}</span><span class="pill">${items.length}</span></summary><div class="asset-list">${items.length?items.map(item=>{
    const assetKind=kindFor[kind],dependency=dependencies.get(`${assetKind}:${item.id}`)||{projects:[],related:[],isDefault:false,removable:true};
    const usage=dependency.projects.length?`Used by ${dependency.projects.map(project=>`${project.name} (${project.status})`).join(", ")}`:dependency.isDefault?"Current default; removing it will clear the default.":dependency.related.length?`Paired with ${dependency.related.map(value=>value.name).join(", ")}`:"Not used by a project.";
    const detail=kind==="explanations"?`${item.description||`${item.fileCount||0} guides`}${item.providerCount>1?` · ${item.providerCount} equivalent providers`:""}${item.familyConflict?" · Warning: another provider has different guidance":""}`:kind==="regions"?`${item.coverage||"Regional"} · version ${item.version||"unknown"}`:kind==="libraries"?`${item.fileCount||0} CSV files`:`${(item.inputFiles||[]).length} input files`;
    return `<article class="asset-row"><div><strong>${escapeHtml(item.name||item.id)}</strong><small>${escapeHtml(detail)}</small><small class="asset-usage">${escapeHtml(usage)}</small></div><button type="button" class="secondary" data-archive-asset="${escapeHtml(item.id)}" data-asset-kind="${assetKind}" ${dependency.removable?"":`disabled title="${escapeHtml(usage)}"`}>Remove</button></article>`;
  }).join(""):`<p class="muted">None installed.</p>`}</div></details>`;
  const archived=state.data?.assets?.archived||[];
  const archivedKindLabel=(kind)=>({"input-library":"Input Library","model-template":"Model package","input-explanations":"Input explanations","regional-data":"Regional data package"}[kind]||"Asset");
  const archivedGroup=`<details class="asset-group"><summary><span>Removed assets</span><span class="pill">${archived.length}</span></summary><div class="asset-list">${archived.length?archived.map(item=>`<article class="asset-row"><div><strong>${escapeHtml(item.name||item.id)}</strong><small>${escapeHtml(archivedKindLabel(item.kind))} · ${item.daysRemaining} days remaining</small></div><div class="asset-row-actions"><button type="button" class="secondary" data-restore-asset="${escapeHtml(item.archiveId)}">Restore</button><button type="button" class="danger" data-purge-asset="${escapeHtml(item.archiveId)}">Delete now</button></div></article>`).join(""):`<p class="muted">None.</p>`}</div></details>`;
  $("installedAssetGroups").innerHTML=group("Regional data packages",regions,"regions")+group("Input explanations",explanations,"explanations")+group("Input Libraries",libraries,"libraries")+group("Model packages",templates,"templates")+archivedGroup;
  document.querySelectorAll("[data-archive-asset]").forEach(button=>button.addEventListener("click",async()=>{
    const dependency=dependencies.get(`${button.dataset.assetKind}:${button.dataset.archiveAsset}`),includeRelated=Boolean(dependency?.related?.length);
    const relatedText=includeRelated?`\n\nIts generated pair (${dependency.related.map(item=>item.name).join(", ")}) will be removed with it.`:"";
    const defaultText=dependency?.isDefault?"\n\nThis is a current default; the default will be cleared.":"";
    if(!await confirmWorkbench(`Remove ${dependency?.asset?.name||button.dataset.archiveAsset}? It can be restored for 30 days.${relatedText}${defaultText}`))return;
    try{await post("/api/assets/archive",{kind:button.dataset.assetKind,id:button.dataset.archiveAsset,includeRelated});await refreshState({quiet:true});await openSettings("settingsAssets");notify("Asset moved to Removed assets.","success")}catch(error){notify(error.message||String(error),"error")}
  }));
  document.querySelectorAll("[data-restore-asset]").forEach(button=>button.addEventListener("click",async()=>{try{await post("/api/assets/restore",{archiveId:button.dataset.restoreAsset});await refreshState({quiet:true});await openSettings("settingsAssets");notify("Asset restored.","success")}catch(error){notify(error.message||String(error),"error")}}));
  document.querySelectorAll("[data-purge-asset]").forEach(button=>button.addEventListener("click",async()=>{if(!await confirmWorkbench("Delete this removed asset permanently? This cannot be undone."))return;try{await post("/api/assets/purge",{archiveId:button.dataset.purgeAsset});await refreshState({quiet:true});await openSettings("settingsAssets");notify("Removed asset permanently deleted.","success")}catch(error){notify(error.message||String(error),"error")}}));
}
function documentationDirectory(path){const parts=String(path||"").split("/");parts.pop();return parts.join("/")}
function documentationPath(basePath,href){const raw=String(href||"").split("#",1)[0];if(!raw||/^[a-z][a-z0-9+.-]*:/i.test(raw)||raw.startsWith("#"))return raw;const parts=`${documentationDirectory(basePath)}/${raw}`.split("/"),output=[];for(const part of parts){if(!part||part===".")continue;if(part==="..")output.pop();else output.push(part)}return output.join("/")||"README.md"}
function markdownLite(markdown,pagePath="README.md"){
  const lines=String(markdown||"").split(/\r?\n/),html=[];let list=null;const close=()=>{if(list){html.push(`</${list}>`);list=null}};
  const inline=(value)=>escapeHtml(value).replace(/`([^`]+)`/g,"<code>$1</code>").replace(/\*\*([^*]+)\*\*/g,"<strong>$1</strong>").replace(/!\[([^\]]*)\]\(([^)]+)\)/g,(_m,alt,href)=>{const target=documentationPath(pagePath,href);return /^[a-z][a-z0-9+.-]*:/i.test(target)?"":`<img src="/api/documentation/asset?path=${encodeURIComponent(target)}" alt="${escapeHtml(alt)}">`}).replace(/\[([^\]]+)\]\(([^)]+)\)/g,(_m,label,href)=>{const target=documentationPath(pagePath,href);return /^[a-z][a-z0-9+.-]*:/i.test(target)?`<a href="${escapeHtml(target)}" target="_blank" rel="noreferrer">${label}</a>`:`<a href="#" data-doc-path="${escapeHtml(target)}">${label}</a>`});
  for(const line of lines){const text=line.trim();if(!text){close();continue}const heading=text.match(/^(#{1,3})\s+(.+)$/);if(heading){close();html.push(`<h${heading[1].length}>${inline(heading[2])}</h${heading[1].length}>`);continue}const bullet=text.match(/^[-*]\s+(.+)$/),ordered=text.match(/^\d+\.\s+(.+)$/);if(bullet||ordered){const kind=bullet?"ul":"ol";if(list!==kind){close();html.push(`<${kind}>`);list=kind}html.push(`<li>${inline((bullet||ordered)[1])}</li>`);continue}close();html.push(`<p>${inline(text)}</p>`)}close();return html.join("")
}
async function loadSettingsDocumentation(path="README.md"){const body=$("settingsDocumentationBody");body.classList.add("empty-state");body.textContent="Loading user guide…";try{const payload=await request(`/api/documentation/page?path=${encodeURIComponent(path)}`);body.classList.remove("empty-state");$("settingsDocumentationPath").textContent=payload.path||path;body.innerHTML=markdownLite(payload.body||"",payload.path||path)}catch(error){body.textContent=error.message||String(error)}}
function diagnosticsOptions(){return{includeResults:Boolean($("diagnosticsIncludeResults").checked),includeCache:Boolean($("diagnosticsIncludeCache").checked)}}
function diagnosticFilename(job){const safe=(value)=>String(value||"run").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,48)||"run";return `visioneval-diagnostics-${safe(job?.projectName)}-${safe(jobDisplayName(job))}.zip`}
async function exportRunDiagnostics(jobId){const job=state.data?.jobs?.find(item=>item.id===jobId);if(!job)return notify("Select a run before exporting diagnostics.","error");const options=diagnosticsOptions(),params=new URLSearchParams({jobId,includeResults:String(options.includeResults),includeCache:String(options.includeCache)});const route=`/api/diagnostics/run?${params}`,invoke=window.__TAURI_INTERNALS__?.invoke;if(invoke){const saved=await invoke("save_backend_export",{exportKind:"diagnostics-run",query:params.toString(),filename:diagnosticFilename(job)});if(saved)notify(`Saved ${saved}.`,"success");return}const link=document.createElement("a");link.href=route;link.download=diagnosticFilename(job);link.click()}
async function loadDiagnosticsSettings(){
  const runsEl=$("diagnosticsRuns"),errorsEl=$("diagnosticsErrors");
  runsEl.textContent="Loading failed runs…";errorsEl.textContent="Loading recent app errors…";
  try{
    const[runsPayload,errorsPayload]=await Promise.all([request("/api/diagnostics/runs?state=failed"),request("/api/diagnostics/errors")]),runs=runsPayload.runs||[],errors=errorsPayload.errors||[];
    runsEl.innerHTML=runs.length?runs.map(job=>`<article class="asset-row"><div><strong>${escapeHtml(jobDisplayName(job))}</strong><small>${escapeHtml(job.projectName||"Unknown project")} · ${formatTime(job.createdAt)}</small><small>${escapeHtml(job.message||"")}</small></div><button type="button" class="secondary" data-diagnostics-run="${escapeHtml(job.id)}">Export diagnostics</button></article>`).join(""):"No failed runs are available.";
    runsEl.querySelectorAll("[data-diagnostics-run]").forEach(button=>button.addEventListener("click",()=>exportRunDiagnostics(button.dataset.diagnosticsRun).catch(error=>notify(error.message,"error"))));
    errorsEl.innerHTML=errors.length?errors.slice().reverse().map(error=>`<article class="asset-row"><div><strong>${escapeHtml(error.message||"Unknown app error")}</strong><small>${escapeHtml(error.source||"app")} · ${formatTime(error.timestamp)}</small></div></article>`).join(""):"No recent app errors are recorded.";
  }catch(error){runsEl.textContent=error.message||String(error);errorsEl.textContent="Diagnostics could not be loaded."}
}
function updateCheckControls(){
  const enabled=$("automaticUpdateChecks").checked,sourceInputs=[$("updateSourceVisionEval"),$("updateSourceRuntime"),$("updateSourceWorkbench")];
  if(enabled&&!sourceInputs.some(input=>input.checked))sourceInputs.forEach(input=>{input.checked=true});
}
function updateCheckSettingsFromControls(){return{automatic:$("automaticUpdateChecks").checked,sources:{visioneval:$("updateSourceVisionEval").checked,runtimeImage:$("updateSourceRuntime").checked,workbench:$("updateSourceWorkbench").checked}}}
function updateStatusLabel(status){return({current:"Up to date",update_available:"Update available",unavailable:"Unable to check",not_selected:"Not selected",not_checked:"Not checked"})[status]||"Not checked"}
function renderUpdateSettings(payload=state.data?.updates){
  if(!payload)return;
  const settings=state.data?.workspaceSettings?.updateChecks||payload;
  $("automaticUpdateChecks").checked=Boolean(settings.automatic);
  $("updateSourceVisionEval").checked=settings.sources?.visioneval!==false;
  $("updateSourceRuntime").checked=settings.sources?.runtimeImage!==false;
  $("updateSourceWorkbench").checked=settings.sources?.workbench!==false;
  $("automaticUpdateChecks").disabled=Boolean(payload.administrativelyDisabled);
  const last=payload.lastCheckedAt||settings.lastCheckedAt;
  $("updatesLastChecked").textContent=payload.administrativelyDisabled?"Update checks were disabled by an administrator.":last?`Last checked ${formatTime(last)}.`:"Never checked.";
  const statuses=payload.statuses||{};
  $("updateStatusList").innerHTML=["workbench","runtimeImage","visioneval"].map(source=>{
    const item=statuses[source]||{status:"not_checked",message:"This source has not been checked yet."},link=item.releaseNotesUrl||item.url||"";
    const canInstall=source==="runtimeImage"&&item.status==="update_available"&&item.runtimeProfile&&!item.requiresWorkbenchVersion;
    const canRestore=source==="runtimeImage"&&Boolean(state.data?.runtime?.runtimeProfiles?.previous);
    const actions=[link?`<button type="button" class="secondary" data-update-url="${escapeHtml(link)}">${item.status==="update_available"?"View release":"Release notes"}</button>`:"",canInstall?`<button type="button" data-install-runtime-update>Install Runtime Update</button>`:"",canRestore?`<button type="button" class="secondary" data-restore-runtime>Restore Previous Runtime</button>`:""].filter(Boolean).join("");
    const profile=item.runtimeProfile||{},detail=source==="runtimeImage"&&profile.digest?`<small>Trusted digest ${escapeHtml(profile.digest)}</small>`:"";
    return `<article class="update-status-card ${escapeHtml(item.status||"not_checked")}"><div class="update-status-heading"><div><strong>${escapeHtml(updateSourceLabels[source])}</strong><span class="update-status-badge">${escapeHtml(updateStatusLabel(item.status))}</span></div><div class="update-status-actions">${actions}</div></div><p>${escapeHtml(item.message||"")}</p>${item.installedVersion||item.availableVersion?`<dl><div><dt>Installed</dt><dd>${escapeHtml(item.installedVersion||"Unknown")}</dd></div><div><dt>Available</dt><dd>${escapeHtml(item.availableVersion||"Unknown")}</dd></div></dl>`:""}${detail}</article>`;
  }).join("");
  $("checkUpdatesNow").disabled=Boolean(payload.checking||payload.administrativelyDisabled);
  $("checkUpdatesNow").textContent=payload.checking?"Checking…":"Check Now";
  renderUpdateIndicator(payload);
}
async function openUpdateUrl(url){
  if(!/^https:\/\/github\.com\//.test(String(url||"")))return notify("Workbench blocked an untrusted update link.","error");
  try{await window.__TAURI_INTERNALS__.invoke("open_external_url",{url})}catch(error){notify(`Could not open the release page: ${error}`,"error")}
}
async function checkUpdatesNow(){
  const button=$("checkUpdatesNow");setBusy(button,true,"Checking…");
  try{
    const updateChecks=updateCheckSettingsFromControls();
    await post("/api/settings",{updateChecks});
    const sources=Object.entries(updateChecks.sources).filter(([,selected])=>selected).map(([source])=>source);
    const payload=await post("/api/updates/check",{sources});
    state.data.workspaceSettings.updateChecks={...updateChecks,lastCheckedAt:payload.lastCheckedAt,statuses:payload.statuses};state.data.updates=payload;
    renderUpdateSettings(payload);notify(availableUpdateStatuses(payload).length?"Update check complete. Updates are available.":"Update check complete.","success");
  }catch(error){notify(error.message||String(error),"error")}
  finally{setBusy(button,false)}
}
async function persistDesktopRuntimeProfile(result){
  if(!window.__TAURI_INTERNALS__?.invoke)return;
  const profile=result?.activeProfile||state.data?.runtime?.runtimeProfiles?.active||{};
  await window.__TAURI_INTERNALS__.invoke("save_runtime_profile",{profile:{
    id:"",name:`${profile.visionEvalVersion||"Verified"} Docker runtime`,adapter:"docker",platform:"darwin",architecture:profile.architecture||"arm64",
    imageReference:profile.reference||result.image||"",imageDigest:profile.digest||result.digest||"",runtimeVersion:profile.visionEvalVersion||result.runtimeVersion||"Compatible VisionEval runtime",verified:true,
    verifiedAt:result.verifiedAt||new Date().toISOString(),verificationMessage:"The immutable digest, VisionEval provenance, architecture, doctor, and household-ID alignment checks passed.",remoteStatus:"ghcr",
  }});
  state.desktop=await window.__TAURI_INTERNALS__.invoke("desktop_state");
}
async function installRuntimeUpdate(button){
  const item=state.data?.updates?.statuses?.runtimeImage||{},profile=item.runtimeProfile||{};
  if(!profile.reference)return notify("Check for updates before installing a runtime update.","error");
  const download=profile.downloadSizeBytes?humanBytes(profile.downloadSizeBytes):"an unreported amount",storage=profile.storageSizeBytes?humanBytes(profile.storageSizeBytes):"an unreported amount";
  const approved=await confirmWorkbench(`Replace the active ${item.installedVersion||"VisionEval"} runtime with ${profile.visionEvalVersion||item.availableVersion}?\n\nDownload: ${download}\nApproximate local Docker storage: ${storage}\n\nWorkbench will verify the immutable digest and runtime checks, and keep the current runtime for rollback. No active or waiting runs may exist.`,{title:"Install runtime update?",confirmLabel:"Install Runtime Update",danger:false});
  if(!approved)return;
  setBusy(button,true,"Installing…");
  try{
    const operation=await post("/api/runtime/install/start",{source:"update"}),result=await waitForRuntimeInstallation(operation.id);
    await persistDesktopRuntimeProfile(result);await refreshState({quiet:true});renderUpdateSettings();renderRuntime();notify(`${profile.visionEvalVersion||"The runtime update"} is verified and active.`,"success");
  }catch(error){notify(error.message||String(error),"error")}finally{setBusy(button,false)}
}
async function restorePreviousRuntime(button){
  const previous=state.data?.runtime?.runtimeProfiles?.previous;
  if(!previous)return notify("No previous verified runtime is available.","error");
  if(!await confirmWorkbench(`Restore ${previous.visionEvalVersion||"the previous verified runtime"}? The current verified runtime will remain available for rollback.`,{title:"Restore previous runtime?",confirmLabel:"Restore Runtime",danger:false}))return;
  setBusy(button,true,"Restoring…");
  try{const result=await post("/api/runtime/restore-previous",{});await persistDesktopRuntimeProfile(result);await refreshState({quiet:true});renderUpdateSettings();renderRuntime();notify(`${result.activeProfile?.visionEvalVersion||"The previous runtime"} is active.`,"success")}catch(error){notify(error.message||String(error),"error")}finally{setBusy(button,false)}
}
function switchSettingsPage(page){document.querySelectorAll(".settings-page").forEach(item=>item.classList.toggle("active",item.id===page));document.querySelectorAll("[data-settings-page]").forEach(item=>item.classList.toggle("active",item.dataset.settingsPage===page));if(page==="settingsStorage")loadStorageReport();if(page==="settingsDiagnostics")loadDiagnosticsSettings();if(page==="settingsDocumentation")loadSettingsDocumentation();if(page==="settingsUpdates")renderUpdateSettings()}
document.querySelectorAll("[data-settings-page]").forEach(button=>button.addEventListener("click",()=>switchSettingsPage(button.dataset.settingsPage)));
$("automaticUpdateChecks").addEventListener("change",updateCheckControls);
[$("updateSourceVisionEval"),$("updateSourceRuntime"),$("updateSourceWorkbench")].forEach(input=>input.addEventListener("change",updateCheckControls));
$("checkUpdatesNow").addEventListener("click",checkUpdatesNow);
$("updateStatusList").addEventListener("click",event=>{const link=event.target.closest("[data-update-url]");if(link)return openUpdateUrl(link.dataset.updateUrl);const install=event.target.closest("[data-install-runtime-update]");if(install)return installRuntimeUpdate(install);const restore=event.target.closest("[data-restore-runtime]");if(restore)return restorePreviousRuntime(restore)});
$('refreshDiagnostics').addEventListener('click',loadDiagnosticsSettings);$('refreshDocumentation').addEventListener('click',()=>loadSettingsDocumentation());$('settingsDocumentation').addEventListener('click',(event)=>{const link=event.target.closest('[data-doc-path]');if(!link)return;event.preventDefault();loadSettingsDocumentation(link.dataset.docPath||'README.md')});
async function loadStorageReport(){try{const report=await request("/api/storage");$("storageReport").innerHTML=metric("Workspace",humanBytes(report.workspaceBytes))+metric("Model runs",humanBytes(report.categories.models))+metric("Datastores",humanBytes(report.runs.reduce((sum,item)=>sum+item.datastoreBytes,0)))+metric("Full CSV exports",humanBytes(report.runs.reduce((sum,item)=>sum+item.exportBytes,0)))+metric("Comparison cache",`${humanBytes(report.comparisonCache?.bytes||0)} · ${report.comparisonCache?.entries||0} tables`);}catch(error){$("storageReport").innerHTML=`<p class="muted">${escapeHtml(error.message)}</p>`}}
async function clearComparisonCache(rebuild=false){const button=$(rebuild?"rebuildComparisonCache":"clearComparisonCache");setBusy(button,true,"Clearing…");try{await post(rebuild?"/api/comparison/cache/rebuild":"/api/comparison/cache/clear",{});state.lastComparison=null;await loadStorageReport();notify(rebuild?"Comparison cache cleared and will rebuild on next use.":"Comparison cache cleared.","success");}catch(error){notify(error.message,"error");}finally{setBusy(button,false);}}
$("clearComparisonCache").addEventListener("click",()=>clearComparisonCache(false));
$("rebuildComparisonCache").addEventListener("click",()=>clearComparisonCache(true));
async function changeWorkspace(path){try{await window.__TAURI_INTERNALS__.invoke("switch_workspace",{path});const url=await window.__TAURI_INTERNALS__.invoke("start_backend");window.location.replace(url)}catch(error){notify(String(error),"error")}}
window.requestWorkbenchQuit=async()=>{try{if(!await flushHypercubeAutosave())return;let result=await post("/api/runtime/shutdown",{cancelActive:false});if(result.requiresConfirmation){const names=(result.jobs||[]).map(job=>job.name).join(", ");if(!await confirmWorkbench(`VisionEval is still running${names?`: ${names}`:""}. Stop these Workbench runs and quit?`))return;result=await post("/api/runtime/shutdown",{cancelActive:true})}if(!result.ok){notify((result.failures||[]).map(item=>item.message).join("; ")||"Workbench could not safely stop the active runtime.","error");return}await window.__TAURI_INTERNALS__.invoke("complete_quit")}catch(error){notify(`Workbench could not quit safely: ${error}`,"error")}};
$("closeSettings").addEventListener("click",()=>$("settingsDialog").close());
$("resetPreferences").addEventListener("click",async(event)=>{
  if(!await confirmWorkbench("Restore all Workbench preferences to their defaults? Workspaces, installed packages, projects, results, and the VisionEval runtime will not be changed.",{title:"Reset settings to defaults?",confirmLabel:"Reset settings"}))return;
  const button=event.currentTarget;setBusy(button,true,"Resetting…");
  try{
    const result=await window.__TAURI_INTERNALS__.invoke("reset_preferences");
    localStorage.setItem("visioneval-theme","light");
    localStorage.removeItem("visioneval-scenario-sidebar-width");
    localStorage.removeItem("visioneval-app-zoom");
    $("inputEditor")?.querySelector(".input-editor-workspace")?.style.removeProperty("--scenario-sidebar-width");
    await window.__TAURI_INTERNALS__.invoke("set_app_zoom",{scale:1});
    state.desktop=result.desktop;applyTheme("light",false);applyComparisonPalettes();
    if(result.restartRequired&&!result.deferred){
      sessionStorage.setItem("visioneval-settings-reset-message","Settings were restored to their defaults. Workspaces, packages, projects, results, and runtime profiles were preserved.");
      const url=await window.__TAURI_INTERNALS__.invoke("restart_backend");window.location.replace(url);return;
    }
    await refreshState({quiet:true});await openSettings("settingsReset");
    notify(result.deferred?"Settings were restored. Resource changes will apply after active and waiting runs finish and Workbench restarts.":"Settings were restored to their defaults.","success");
  }catch(error){notify(String(error),"error");setBusy(button,false)}
});
$("repairWorkspace").addEventListener("click",async(event)=>{const button=event.currentTarget;setBusy(button,true,"Repairing…");try{const result=await post("/api/workspace/repair",{});await refreshState({quiet:true});await openSettings("settingsReset");notify(`Workspace repaired. ${result.abandonedStagingRemoved||0} abandoned staging item(s) removed${result.pathWarnings?.length?`; ${result.pathWarnings.length} path warning(s) remain`:""}. No settings save is required.`,result.pathWarnings?.length?"":"success")}catch(error){notify(error.message||String(error),"error")}finally{setBusy(button,false)}});
$("archiveAllProjects").addEventListener("click",async()=>{if(!await confirmWorkbench("Archive every active project? They can be restored for 30 days."))return;try{const result=await post("/api/projects/archive-all",{});await refreshState({quiet:true});await openSettings("settingsReset");notify(`Archived ${result.archived.length} project${result.archived.length===1?"":"s"}.`,"success")}catch(error){notify(error.message||String(error),"error")}});
$("wipeProjectData").addEventListener("click",async(event)=>{const button=event.currentTarget,confirmation="DELETE ALL PROJECTS";if(!await confirmWorkbench("This permanently deletes every project and its owned runs and results. Installed assets and standalone imported results remain.",{title:"Permanently wipe project data?",confirmLabel:"Wipe projects",requiredPhrase:confirmation}))return;setBusy(button,true,"Wiping…");try{const result=await post("/api/projects/wipe-all",{confirmation});await refreshState({quiet:true});await openSettings("settingsReset");notify(`Permanently removed ${result.wipedProjects.length} projects. Installed assets were preserved.`,"success")}catch(error){notify(error.message||String(error),"error")}finally{setBusy(button,false)}});
$("factoryResetWorkspace").addEventListener("click",async(event)=>{const button=event.currentTarget,confirmation="FACTORY RESET";if(!await confirmWorkbench("The entire current workspace will be moved to Trash and a fresh workspace will be created at the same location. The installed app, preferences, and VisionEval runtime image remain.",{title:"Factory reset Workbench?",confirmLabel:"Factory reset",requiredPhrase:confirmation}))return;setBusy(button,true,"Resetting…");try{await window.__TAURI_INTERNALS__.invoke("factory_reset_workspace",{confirmation});const url=await window.__TAURI_INTERNALS__.invoke("start_backend");window.location.replace(url)}catch(error){notify(String(error),"error");setBusy(button,false)}});
document.addEventListener("pointerdown",(event)=>{if(!event.target.closest(".workspace-action-menu"))closeWorkspaceMenus();});
document.addEventListener("keydown",(event)=>{if(event.key==="Escape")closeWorkspaceMenus();});
document.querySelectorAll("[data-reveal-workspace-location]").forEach(button=>button.addEventListener("click",()=>window.__TAURI_INTERNALS__.invoke("reveal_workspace_location",{location:button.dataset.revealWorkspaceLocation}).catch(error=>notify(String(error),"error"))));
$("revealWorkspaceRoot").addEventListener("click",()=>window.__TAURI_INTERNALS__.invoke("reveal_workspace_location",{location:"root"}).catch(error=>notify(String(error),"error")));
$("switchWorkspace").addEventListener("click",async()=>{const path=await window.__TAURI_INTERNALS__.invoke("choose_folder");if(path)changeWorkspace(path)});
$("moveWorkspace").addEventListener("click",async()=>{try{const path=await window.__TAURI_INTERNALS__.invoke("choose_folder");if(!path)return;await window.__TAURI_INTERNALS__.invoke("move_workspace",{destination:path});const url=await window.__TAURI_INTERNALS__.invoke("start_backend");window.location.replace(url)}catch(error){notify(String(error),"error")}});
$("settingsVerifyRuntime").addEventListener("click",event=>verifyRuntimeFromSetup(event.currentTarget).then(()=>openSettings("settingsRuntime")).catch(()=>{}));
if($("settingsInstallRuntime"))$("settingsInstallRuntime").addEventListener("click",event=>installAndSaveRuntime(event.currentTarget).then(()=>openSettings("settingsRuntime")).catch(()=>{}));
if($("settingsStartDocker"))$("settingsStartDocker").addEventListener("click",event=>startDockerAndVerify(event.currentTarget));
$("testNotification").addEventListener("click",async()=>{if(!state.desktop?.notificationsEnabled)return notify("Save Settings with notifications enabled first.","error");try{const result=await window.__TAURI_INTERNALS__.invoke("send_workbench_notification",{title:"VisionEval Workbench test",body:"Notifications are configured correctly.",outcome:"test",elapsedSeconds:0,force:true});notify(result?.shown?"Test notification sent.":"Enable notifications and save Settings first.",result?.shown?"success":"error")}catch(error){notify(String(error),"error")}});
$("openRuntimeGuide").addEventListener("click",()=>$("runtimeGuideDialog").showModal());
async function copyRuntimeCommands(sourceId, label) {
  try { await navigator.clipboard.writeText($(sourceId).innerText); notify(`${label} copied.`,"success"); }
  catch(error) { notify(`The ${label.toLowerCase()} could not be copied.`,"error"); }
}
if($("copyRuntimeInstallCommands"))$("copyRuntimeInstallCommands").addEventListener("click",()=>copyRuntimeCommands("runtimeInstallCommands","macOS runtime commands"));
if($("copyRuntimeAdvancedCommands"))$("copyRuntimeAdvancedCommands").addEventListener("click",()=>copyRuntimeCommands("runtimeAdvancedCommands","macOS verification commands"));
$("settingsInstallPackage").addEventListener("click",event=>openPackageSourceDialog(event.currentTarget,false));
$("maxConcurrentRuns").addEventListener("change",updateParallelMemoryGuide);
$("memoryLimit").addEventListener("input",updateParallelMemoryGuide);
async function saveWorkbenchSettings(closeAfter=false){
  const activePage=document.querySelector(".settings-page.active")?.id||"settingsWorkspace",previousMemory=state.desktop?.resources?.memoryLimitGb??null,previousRuns=Number(state.desktop?.resources?.maxConcurrentRuns||2),previousAutoStart=state.desktop?.autoStartDocker!==false,nextMemory=$("memoryLimit").value===""?null:Number($("memoryLimit").value),nextRuns=Number($("maxConcurrentRuns").value||1),nextAutoStart=$("autoStartDocker").checked;
  try{
    const optionalPrecision=(id)=>$(id).value===""?null:Number($(id).value);
    await post("/api/settings",{defaultInputLibraryId:$("defaultLibrary").value,defaultInputExplanationId:$("defaultInputExplanations").value,retainFullExports:$("retainExports").checked,updateChecks:updateCheckSettingsFromControls(),numericPrecision:{default:Number($("precisionDefault").value),singleFile:optionalPrecision("precisionSingleFile"),batch:optionalPrecision("precisionBatch"),output:optionalPrecision("precisionOutput"),percentage:optionalPrecision("precisionPercentage")}});
    state.desktop=await window.__TAURI_INTERNALS__.invoke("update_desktop_preferences",{theme:$("appearanceSetting").value,defaultRunMode:$("defaultRunMode").value,maxConcurrentRuns:nextRuns,memoryLimitGb:nextMemory,notificationsEnabled:$("notificationsEnabled").checked,notificationSuccessThresholdSeconds:Number($("notificationSuccessThreshold").value||60),autoStartDocker:nextAutoStart,comparisonPalettes:readComparisonPalettes(),masterComparisonPalette:masterComparisonPalette(),useMasterComparisonPalette:Boolean(state.desktop.useMasterComparisonPalette)});
    applyTheme(state.desktop.theme,false);applyComparisonPalettes();
    const resourcesChanged=previousMemory!==nextMemory||previousRuns!==nextRuns;
    if(resourcesChanged&&Number(state.desktop.blockingJobCount||0)===0){
      if(closeAfter)$("settingsDialog").close();
      const url=await window.__TAURI_INTERNALS__.invoke("restart_backend");window.location.replace(url);return;
    }
    await refreshState({quiet:true});
    if(closeAfter)$("settingsDialog").close();else await openSettings(activePage);
    if(resourcesChanged)notify("Settings saved. Resource changes will apply after active and waiting runs finish and Workbench restarts.","success");else if(previousAutoStart!==nextAutoStart)notify("Settings saved. The Docker startup preference will be used the next time Workbench opens.","success");else notify("Settings saved and applied.","success");
  }catch(error){notify(String(error),"error")}
}
$("settingsForm").addEventListener("submit",async(event)=>{event.preventDefault();await saveWorkbenchSettings(false)});
$("saveCloseSettings").addEventListener("click",()=>saveWorkbenchSettings(true));

function comparisonMapPackage() {
  const providers = state.data?.comparisonMapPackages || state.data?.regionPackages || [];
  const selected = [$('mapReference')?.value,$('mapComparison')?.value].filter(Boolean);
  const records = (selected.length===2?selected:state.comparisonIds).map((id) => state.data?.catalog?.find((item) => item.id === id)).filter(Boolean);
  const templateIds = new Set(records.map((item) => item.templateId).filter(Boolean));
  return providers.find((item) => item.comparisonMap?.enabled && item.compatibleTemplateIds?.some((id) => templateIds.has(id)))
    || providers.find((item) => item.comparisonMap?.enabled) || null;
}

async function loadComparisonMapOptions() {
  if (!$('mapVariable')) return;
  const ids=[$('mapReference').value,$('mapComparison').value];
  if (!ids[0] || !ids[1] || ids[0]===ids[1]) {
    state.comparisonMapOptionsController?.abort();
    state.comparisonMapOptionsRequest = '';
    state.mapOptions = [];
    $('mapTable').innerHTML = `<option value="">${ids[0]&&ids[0]===ids[1]?'Choose different results':'Choose two results first'}</option>`;
    $('mapVariable').innerHTML = '';
    $('mapYear').innerHTML = '';
    $('generateMap').disabled = true;
    setComparisonMapEmpty('Load a reference and comparison result to create a map.');
    return;
  }
  const key=ids.join('|'),cached=state.comparisonMapOptionsCache.get(key);
  if(state.comparisonMapOptionsRequest!==key)state.comparisonMapOptionsController?.abort();
  let pending=state.comparisonMapOptionsInflight.get(key),controller=state.comparisonMapOptionsController;
  if(!cached&&!pending){controller=new AbortController();state.comparisonMapOptionsController=controller;pending=request(`/api/comparison/map-options?ids=${encodeURIComponent(ids.join(','))}`,{signal:controller.signal}).finally(()=>state.comparisonMapOptionsInflight.delete(key));state.comparisonMapOptionsInflight.set(key,pending)}
  state.comparisonMapOptionsRequest=key;
  $('mapTable').innerHTML='<option value="">Loading map outputs…</option>';$('mapVariable').innerHTML='';$('mapYear').innerHTML='';$('generateMap').disabled=true;
  try {
    const payload = cached || await pending;
    if(state.comparisonMapOptionsRequest!==key)return;
    state.comparisonMapOptionsCache.set(key,payload);
    state.mapOptions = payload.variables || [];
    const tables = [...new Set(state.mapOptions.map((item) => item.table))].sort();
    $('mapTable').innerHTML = tables.map((table) => `<option>${escapeHtml(table)}</option>`).join('');
    renderComparisonMapVariables();
    $('generateMap').disabled = !state.mapOptions.length || !comparisonMapPackage();
    setComparisonMapEmpty(comparisonMapPackage()
      ? 'Choose a map-compatible output and generate the map.'
      : 'Install a model or regional package that provides map geometry to use Map Visualization.');
  } catch (error) {
    if(error.name==='AbortError')return;
    state.mapOptions = [];
    $('generateMap').disabled = true;
    setComparisonMapEmpty(error.message);
  }
}

function renderComparisonMapVariables() {
  const variables = state.mapOptions.filter((item) => item.table === $('mapTable').value);
  $('mapVariable').innerHTML = variables.map((item) => `<option value="${escapeHtml(item.name)}">${escapeHtml(item.name)}</option>`).join('');
  const micro=['Household','Vehicle','Worker'].includes($('mapTable').value);
  $('mapAggregationField').hidden=!micro;
  $('mapAggregation').value='mean';
  renderComparisonMapYears();
}

function renderComparisonMapYears() {
  const option = state.mapOptions.find((item) => item.table === $('mapTable').value && item.name === $('mapVariable').value);
  $('mapYear').innerHTML = (option?.years || []).map((year) => `<option value="${escapeHtml(year)}" ${year === '2045' ? 'selected' : ''}>${escapeHtml(year)}</option>`).join('');
  const levels = option?.geographyLevels || [];
  $('mapGeography').innerHTML = levels.map((level) => {
    const descriptor = typeof level === 'string' ? {id:level,label:level === 'azone' ? 'Azone / locality' : level === 'county' ? 'County / locality' : 'Bzone'} : level;
    return `<option value="${escapeHtml(descriptor.id)}" data-map-geometry="${escapeHtml(descriptor.geometry || descriptor.id)}">${escapeHtml(descriptor.label || descriptor.id)}</option>`;
  }).join('');
  setComparisonMapDirty();
}

function comparisonMapRequest() {
  return {operationKind:'map', reference:$('mapReference').value, comparison:$('mapComparison').value, year:$('mapYear').value, table:$('mapTable').value, variable:$('mapVariable').value, geographyLevel:$('mapGeography').value, aggregation:$('mapAggregationField').hidden?'mean':$('mapAggregation').value};
}

function setComparisonMapDirty() {
  state.mapDirty = Boolean(state.mapPayload);
  $('mapStaleMessage').hidden = !state.mapDirty;
  setComparisonMapExportAvailability();
  syncMenuContext();
}

function setComparisonMapEmpty(message) {
  const canvas = $('comparisonMapCanvas');
  canvas.className = 'region-map-canvas empty-state';
  canvas.textContent = message;
  $('comparisonMapLegend').hidden = true;
  $('comparisonMapInspector').hidden = true;
}

async function loadComparisonMapGeometry() {
  const packageItem = comparisonMapPackage();
  if (!packageItem) throw new Error('Install a model or regional package that provides map geometry to use Map Visualization.');
  if (state.comparisonMapData && state.comparisonMapPackageId === packageItem.id) return state.comparisonMapData;
  const data = await request(`/api/region-builder/map/statewide?packageId=${encodeURIComponent(packageItem.id)}`);
  state.comparisonMapData = data; state.comparisonMapPackageId = packageItem.id;
  return data;
}

function comparisonMapViewportRatio() {
  const canvas = $('comparisonMapCanvas');
  return canvas.clientWidth > 0 && canvas.clientHeight > 0 ? canvas.clientWidth / canvas.clientHeight : 1000 / 620;
}

function comparisonMapFullView(projection) {
  const ratio = comparisonMapViewportRatio(); let width = projection.width, height = projection.height;
  if (width / height < ratio) width = height * ratio; else height = width / ratio;
  return {x:(projection.width-width)/2,y:(projection.height-height)/2,width,height};
}

function comparisonMapSpatialIndex(entries, projection, columns=32, rows=20) {
  const buckets=new Map(),cellWidth=projection.width/columns,cellHeight=projection.height/rows;
  for(const entry of entries){
    entry.label=regionMapInteriorLabel(entry.feature,projection);entry.center=[entry.label.x,entry.label.y];
    const minColumn=Math.max(0,Math.floor(entry.bounds.minX/cellWidth)),maxColumn=Math.min(columns-1,Math.floor(entry.bounds.maxX/cellWidth));
    const minRow=Math.max(0,Math.floor(entry.bounds.minY/cellHeight)),maxRow=Math.min(rows-1,Math.floor(entry.bounds.maxY/cellHeight));
    for(let column=minColumn;column<=maxColumn;column++)for(let row=minRow;row<=maxRow;row++){const key=`${column}:${row}`;if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(entry);}
  }
  return {buckets,cellWidth,cellHeight,columns,rows};
}

function comparisonMapIndexedEntries(index, bounds) {
  if(!index)return[];const found=new Set(),result=[];
  const minColumn=Math.max(0,Math.floor(bounds.minX/index.cellWidth)),maxColumn=Math.min(index.columns-1,Math.floor(bounds.maxX/index.cellWidth));
  const minRow=Math.max(0,Math.floor(bounds.minY/index.cellHeight)),maxRow=Math.min(index.rows-1,Math.floor(bounds.maxY/index.cellHeight));
  for(let column=minColumn;column<=maxColumn;column++)for(let row=minRow;row<=maxRow;row++)for(const entry of index.buckets.get(`${column}:${row}`)||[]){if(found.has(entry))continue;found.add(entry);result.push(entry);}
  return result;
}

function constrainComparisonMapView(view) {
  const full = state.comparisonMapScene?.fullView || view, ratio = comparisonMapViewportRatio();
  const width = Math.min(full.width * 1.15, Math.max(full.width / 256, Number(view.width) || full.width));
  const height = width / ratio;
  return {x:Math.min(full.x + full.width - width * .25, Math.max(full.x - width * .75, Number(view.x) || 0)), y:Math.min(full.y + full.height - height * .25, Math.max(full.y - height * .75, Number(view.y) || 0)), width, height};
}

function setComparisonMapView(view) {
  state.comparisonMapView = constrainComparisonMapView(view);
  if(state.comparisonMapFrame)return;
  state.comparisonMapFrame=requestAnimationFrame(()=>{
    state.comparisonMapFrame=0;
    const current=state.comparisonMapView,svg=$('comparisonMapCanvas').querySelector('[data-comparison-map-svg]');
    svg?.setAttribute('viewBox', `${current.x} ${current.y} ${current.width} ${current.height}`);
    clearTimeout(state.comparisonMapLabelTimer);
    state.comparisonMapLabelTimer=setTimeout(updateComparisonMapLabels,70);
  });
}

function zoomComparisonMap(factor, anchor) {
  const view = state.comparisonMapView; if (!view) return;
  const point = anchor || {x:view.x + view.width / 2,y:view.y + view.height / 2};
  const width = view.width * factor, height = width / comparisonMapViewportRatio();
  const xr = (point.x-view.x)/view.width, yr = (point.y-view.y)/view.height;
  setComparisonMapView({x:point.x-xr*width,y:point.y-yr*height,width,height});
}

function comparisonMapMetricValue(row) {
  if (!row) return null;
  return {percentChange:row.percentChange,absoluteChange:row.absoluteChange,referenceValue:row.referenceValue,comparisonValue:row.comparisonValue}[$('mapMetric').value];
}

function comparisonMapDirection(value) {
  return !Number.isFinite(value) ? 'unavailable' : value < 0 ? 'decrease' : value > 0 ? 'increase' : 'neutral';
}

function comparisonMapSignedValue(value, {percent = false, unit = ''} = {}) {
  if (!Number.isFinite(value)) return 'Unavailable';
  const direction = comparisonMapDirection(value), marker = direction === 'decrease' ? '▼' : direction === 'increase' ? '▲' : '•';
  const magnitude = percent ? percentage(Math.abs(value)) : number(Math.abs(value));
  const sign = value < 0 ? '−' : value > 0 ? '+' : '';
  return `${marker} ${sign}${magnitude}${percent ? '%' : unit}`;
}

function comparisonMapPercentile(values, percentile) {
  const sorted = values.filter(Number.isFinite).sort((a,b)=>a-b); if (!sorted.length) return 1;
  return sorted[Math.min(sorted.length-1, Math.max(0, Math.ceil(sorted.length * percentile)-1))] || 1;
}

function comparisonMapColor(value, scale) {
  if (!Number.isFinite(value)) return 'url(#comparison-map-unavailable)';
  if (value === 0) return comparisonPaletteColor('map','neutral');
  if (scale.kind === 'sequential') {
    const ratio = Math.max(0,Math.min(1,(value-scale.min)/Math.max(Number.EPSILON,scale.max-scale.min)));
    return `rgb(${Math.round(226-166*ratio)},${Math.round(238-111*ratio)},${Math.round(246-50*ratio)})`;
  }
  const parse=(hex)=>[1,3,5].map((index)=>parseInt(hex.slice(index,index+2),16)),ratio=Math.min(1,Math.abs(value)/scale.limit),target=parse(comparisonPaletteColor('map',value<0?'decrease':'increase')),neutral=parse(comparisonPaletteColor('map','neutral'));
  return `rgb(${neutral.map((channel,index)=>Math.round(channel+(target[index]-channel)*ratio)).join(',')})`;
}

function comparisonMapScale() {
  const values = (state.mapPayload?.geographyRows || []).map(comparisonMapMetricValue).filter(Number.isFinite);
  const metricName = $('mapMetric').value;
  if (metricName === 'referenceValue' || metricName === 'comparisonValue') return {kind:'sequential',min:Math.min(...values,0),max:Math.max(...values,1)};
  return {kind:'diverging',limit:comparisonMapPercentile(values.map(Math.abs),.95)};
}

function comparisonMapDisplayRows(){
  const direct=new Map((state.mapPayload?.geographyRows||[]).map((row)=>[String(row.geographyId),row]));
  if(state.mapPayload?.geographyLevel!=="marea")return direct;
  const expanded=new Map();
  for(const [marea,bzones] of Object.entries(state.mapPayload?.mareaBzones||{})){
    const row=direct.get(String(marea));for(const bzone of bzones||[])expanded.set(String(bzone),row?{...row,mareaId:marea,geographyId:String(bzone)}:null);
  }
  return expanded;
}

function comparisonMapScopeIds() {
  return new Set([...comparisonMapDisplayRows()].filter(([,row])=>row&&(Number.isFinite(row.referenceValue)||Number.isFinite(row.comparisonValue))).map(([id])=>id));
}

function applyComparisonMapPresentation() {
  const scene = state.comparisonMapScene; if (!scene) return;
  const rows = comparisonMapDisplayRows(), scale = comparisonMapScale(), scope = comparisonMapScopeIds();
  scene.valuePaths.forEach((path,id)=>{const row=rows.get(id),value=comparisonMapMetricValue(row),outsideModel=!scope.has(id);path.style.fill=outsideModel?'#f4f6f8':comparisonMapColor(value,scale);path.dataset.direction=outsideModel?'context':comparisonMapDirection(value);path.classList.toggle('comparison-map-context',outsideModel);path.classList.toggle('comparison-map-outside-scope',outsideModel);path.classList.toggle('comparison-map-saturated',Number.isFinite(value)&&scale.kind==='diverging'&&Math.abs(value)>scale.limit);});
  document.querySelectorAll('[data-comparison-map-layer]').forEach((input)=>{const group=scene.svg.querySelector(`[data-comparison-map-group="${input.dataset.comparisonMapLayer}"]`);if(group)group.style.display=input.checked?'':'none';});
  const metricLabels={percentChange:'Change %',absoluteChange:'Absolute change',referenceValue:'Reference value',comparisonValue:'Comparison value'}, units=$('mapMetric').value==='percentChange'?'%':state.mapPayload?.units||'';
  $('comparisonMapLegend').hidden=false;
  const formatLegendValue=(value)=>comparisonMapSignedValue(value,{percent:$('mapMetric').value==='percentChange',unit:$('mapMetric').value==='percentChange'?'':units?` ${units}`:''});
  const keys='<span class="comparison-map-legend-key"><strong aria-hidden="true">▼</strong> Decrease (dashed top border in 3D)</span><span class="comparison-map-legend-key"><strong aria-hidden="true">▲</strong> Increase (solid top border in 3D)</span><span class="comparison-map-legend-key"><i class="comparison-map-hatch"></i>Unavailable</span><span class="comparison-map-legend-key"><i class="comparison-map-context-key"></i>Outside model region</span>';
  $('comparisonMapLegend').innerHTML=scale.kind==='diverging'
    ? `<div class="comparison-map-scale"><strong>${escapeHtml(metricLabels[$('mapMetric').value])}</strong><div class="comparison-map-scale-axis"><span>${escapeHtml(formatLegendValue(-scale.limit))}</span><i class="comparison-map-gradient diverging"><b aria-hidden="true"></b></i><span>${escapeHtml(formatLegendValue(scale.limit))}</span></div><small>• 0 at center · colors clipped at the 95th percentile</small></div><div class="comparison-map-legend-keys">${keys}</div>`
    : `<div class="comparison-map-scale"><strong>${escapeHtml(metricLabels[$('mapMetric').value])}</strong><div class="comparison-map-scale-axis"><span>${escapeHtml(formatLegendValue(scale.min))}</span><i class="comparison-map-gradient sequential"></i><span>${escapeHtml(formatLegendValue(scale.max))}</span></div></div><div class="comparison-map-legend-keys">${keys}</div>`;
  updateComparisonMapLabels();
  if (state.comparisonMapSelectedFeature) renderComparisonMapInspector();
}

function updateComparisonMapLabels() {
  const scene=state.comparisonMapScene,view=state.comparisonMapView,showIds=$('comparisonMapIdLabels').checked,showValues=$('comparisonMapValueLabels').checked;if(!scene?.labels||!view||(!showIds&&!showValues)){if(scene?.labels)scene.labels.innerHTML='';return;}
  const useBzones=['bzone','marea'].includes(state.mapPayload?.geographyLevel),useAzones=!useBzones;
  const viewport={minX:view.x,minY:view.y,maxX:view.x+view.width,maxY:view.y+view.height};
  const scope=comparisonMapScopeIds(),entries=comparisonMapIndexedEntries(useBzones?scene.bzoneIndex:scene.azoneIndex,viewport).filter((entry)=>scope.has(entry.id));
  const canvas=$('comparisonMapCanvas'),labelEntries=[],seenMareas=new Set();
  const metric=$('mapMetric').value,units=metric==='percentChange'?'%':state.mapPayload?.units||'';
  for(const entry of entries){
    const label=entry.label||regionMapInteriorLabel(entry.feature,scene.projection),x=label.x,y=label.y;if(x<view.x||x>view.x+view.width||y<view.y||y>view.y+view.height)continue;
    const sx=(x-view.x)/view.width*canvas.clientWidth,sy=(y-view.y)/view.height*canvas.clientHeight,radiusPx=Math.max(0,label.radius*Math.min(canvas.clientWidth/view.width,canvas.clientHeight/view.height));
    if(radiusPx<6)continue;
    const row=scene.rows.get(entry.id),value=comparisonMapMetricValue(row),valueText=Number.isFinite(value)?comparisonMapSignedValue(value,{percent:metric==='percentChange',unit:metric==='percentChange'?'':units?` ${units}`:''}):'N/A';
    const properties=entry.feature?.properties||{},azoneId=useBzones?String(properties.azoneId||entry.id.slice(0,5)):entry.id;
    const locality=row?.name||properties.localityName||properties.name||scene.localityNames?.get(azoneId)||'',identifier=state.mapPayload?.geographyLevel==='marea'?(row?.mareaId||row?.name||entry.id):entry.id;
    if(state.mapPayload?.geographyLevel==='marea'){if(seenMareas.has(identifier))continue;seenMareas.add(identifier);}
    const candidates=[];
    if(showIds&&showValues){if(useAzones&&locality&&radiusPx>=70)candidates.push([locality,identifier,valueText]);if(radiusPx>=30)candidates.push([identifier,valueText]);candidates.push([valueText]);}
    else if(showIds){if(useAzones&&locality&&radiusPx>=70)candidates.push([locality,identifier]);if(radiusPx>=25)candidates.push([identifier]);}else candidates.push([valueText]);
    labelEntries.push({feature: entry.feature, label, priority: state.comparisonMapSelectedFeature?.id === entry.id ? 50 : 10, candidates, className: "region-map-id-label"});
  }
  WorkbenchPolygonLabels.layout({group: scene.labels, entries: labelEntries, view, viewport: {width: Math.max(1, canvas.clientWidth), height: Math.max(1, canvas.clientHeight)}, project: scene.projection.point, pathFor: (feature) => regionMapPath(feature, scene.projection), className: "region-map-label", minFontPx: 8, maxFontPx: 11, maxLabels: 250});
}

function comparisonMapFeatureView(features) {
  return regionMapFeaturesView(features,state.comparisonMapScene.projection);
}

function focusComparisonMapProject({zoom=true}={}) {
  const scene=state.comparisonMapScene;if(!scene)return;
  const ids=comparisonMapScopeIds(),features=[...ids].map((id)=>['bzone','marea'].includes(state.mapPayload?.geographyLevel)?scene.bzoneFeatures.get(id):scene.azoneFeatures.get(id)).filter(Boolean);
  scene.projectView=features.length?comparisonMapFeatureView(features):scene.fullView;
  $('fitComparisonMap').disabled=!features.length;
  if(zoom)setComparisonMapView(scene.projectView);
  applyComparisonMapPresentation();
  syncMenuContext();
}

function clearComparisonMapInspector() {
  state.comparisonMapSelectedFeature=null;$('comparisonMapInspector').hidden=true;if(state.comparisonMapScene?.inspected)state.comparisonMapScene.inspected.innerHTML='';
}

function renderComparisonMapInspector() {
  const selected=state.comparisonMapSelectedFeature,scene=state.comparisonMapScene;if(!selected||!scene)return clearComparisonMapInspector();
  if(selected.densityRow){const item=selected.densityRow,properties=selected.feature?.properties||{};$('comparisonMapInspectorTitle').textContent=item.name||properties.localityName||selected.id;$('comparisonMapInspectorBody').innerHTML=`<div class="comparison-map-detail-cards"><section class="comparison-map-detail-card identity"><h4>Identity</h4><dl class="region-map-details">${regionMapDetailRow(selected.type==='bzone'?'Bzone GEOID':'Azone ID',selected.id)}${regionMapDetailRow('Locality',item.name||properties.localityName)}${regionMapDetailRow('Project coverage','Included in project results')}</dl></section><section class="comparison-map-detail-card change"><h4>Changed-variable density</h4><strong>${Number(item.changedVariableCount||0).toLocaleString()} changed variables</strong><small>${Number(item.scannedVariableCount||0).toLocaleString()} safely assigned variables scanned · ${Number(item.unavailableVariableCount||0).toLocaleString()} unavailable</small></section></div>`;$('comparisonMapInspector').hidden=false;if(scene.inspected)scene.inspected.innerHTML=`<path class="region-map-inspected" d="${regionMapPath(selected.feature,scene.projection)}"></path>`;return;}
  const row=scene.rows.get(selected.id),metric=comparisonMapMetricValue(row),scale=comparisonMapScale(),properties=selected.feature.properties||{},scope=comparisonMapScopeIds();
  const status=scope.has(selected.id)?'Included in project results':'Virginia context only';
  $('comparisonMapInspectorTitle').textContent=row?.name||properties.localityName||properties.name||selected.id;
  const unit=state.mapPayload.units||'',value=(numberValue)=>Number.isFinite(numberValue)?`${number(numberValue)}${unit?` ${escapeHtml(unit)}`:''}`:'Not available';
  const scaleStatus=!Number.isFinite(metric)||scale.kind!=='diverging'||Math.abs(metric)<=scale.limit?'Within color scale':metric>0?`Above +${percentage(scale.limit)}% scale cap`:`Below −${percentage(scale.limit)}% scale cap`;
  const identityLabel=selected.type==='bzone'?'Bzone GEOID':selected.type==='marea'?'Member Bzone / Marea':'County / locality FIPS';
  $('comparisonMapInspectorBody').innerHTML=`<div class="comparison-map-detail-cards"><section class="comparison-map-detail-card identity"><h4>Identity</h4><dl class="region-map-details">${regionMapDetailRow(identityLabel,selected.id)}${selected.type!=='bzone'?regionMapDetailRow('Technical geography','Azone'):''}${regionMapDetailRow('Locality',row?.name||properties.localityName)}${regionMapDetailRow('Project coverage',status)}</dl></section><div class="comparison-map-value-cards"><section class="comparison-map-detail-card"><h4>Reference</h4><strong>${value(row?.referenceValue)}</strong><small>${row?.referenceCount?.toLocaleString()||0} contributing rows</small></section><section class="comparison-map-detail-card"><h4>Comparison</h4><strong>${value(row?.comparisonValue)}</strong><small>${row?.comparisonCount?.toLocaleString()||0} contributing rows</small></section></div><section class="comparison-map-detail-card change"><h4>Change</h4><dl class="region-map-details">${regionMapDetailRow('Absolute',Number.isFinite(row?.absoluteChange)?comparisonMapSignedValue(row.absoluteChange):'Not available')}${regionMapDetailRow('Percent',Number.isFinite(row?.percentChange)?comparisonMapSignedValue(row.percentChange,{percent:true}):'Not available')}${regionMapDetailRow('Scale status',scaleStatus)}</dl></section></div>`;
  $('comparisonMapInspector').hidden=false;scene.inspected.innerHTML=`<path class="region-map-inspected" d="${regionMapPath(selected.feature,scene.projection)}"></path>`;
}

function renderComparisonMap() {
  const data=state.comparisonMapData,payload=state.mapPayload,canvas=$('comparisonMapCanvas'),bounds=data&&regionMapBounds([data.mpos,data.azones,data.bzones]);
  if(!bounds||!payload)return setComparisonMapEmpty('Map geometry or comparison values are unavailable.');
  const projection=regionMapProjection(bounds),geo=payload.geographyLevel,features=['bzone','marea'].includes(geo)?data.bzones?.features||[]:data.azones?.features||[],idFor=(feature)=>String(['bzone','marea'].includes(geo)?(feature.properties?.bzoneId||feature.properties?.GEOID||''):(feature.properties?.azoneId||feature.properties?.Azones||''));
  const pathFor=(feature)=>regionMapPath(feature,projection),mpos=(data.mpos?.features||[]).map((feature)=>`<path class="region-map-mpo comparison-map-context" d="${pathFor(feature)}"></path>`).join(''),azones=(data.azones?.features||[]).map((feature)=>`<path class="region-map-azone comparison-map-context" d="${pathFor(feature)}"></path>`).join(''),bzones=(data.bzones?.features||[]).map((feature)=>`<path class="region-map-bzone comparison-map-context" d="${pathFor(feature)}"></path>`).join(''),values=features.map((feature)=>`<path class="comparison-map-value" data-map-geography-id="${escapeHtml(idFor(feature))}" d="${pathFor(feature)}"><title>${escapeHtml(feature.properties?.localityName||feature.properties?.name||idFor(feature))}</title></path>`).join('');
  canvas.className='region-map-canvas comparison-map-canvas';
  canvas.innerHTML=`<svg role="img" aria-label="Virginia comparison map" viewBox="0 0 1000 620" data-comparison-map-svg><defs><pattern id="comparison-map-unavailable" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="#e3e7ea"></rect><path d="M-2 2L2-2M0 8L8 0M6 10L10 6" stroke="#9aa6af" stroke-width="1"></path></pattern></defs><g data-comparison-map-group="mpos">${mpos}</g><g data-comparison-map-group="azones">${azones}</g><g data-comparison-map-group="bzones">${bzones}</g><g data-comparison-map-group="values">${values}</g><g data-comparison-map-group="labels"></g><g data-comparison-map-group="inspected"></g></svg>`;
  const svg=canvas.querySelector('svg'),fullView=comparisonMapFullView(projection),bzoneFeatures=new Map((data.bzones?.features||[]).map((feature)=>[String(feature.properties?.bzoneId||feature.properties?.GEOID||''),feature])),azoneFeatures=new Map((data.azones?.features||[]).map((feature)=>[String(feature.properties?.azoneId||feature.properties?.Azones||''),feature])),hit=(items,getId)=>items.map((feature)=>({id:String(getId(feature)),feature,bounds:regionMapFeatureBounds(feature,projection)})).filter((entry)=>entry.id&&entry.bounds);
  const hitBzones=hit(data.bzones?.features||[],(feature)=>feature.properties?.bzoneId||feature.properties?.GEOID),hitAzones=hit(data.azones?.features||[],(feature)=>feature.properties?.azoneId||feature.properties?.Azones);
  state.comparisonMapScene={svg,projection,fullView,rows:comparisonMapDisplayRows(),valuePaths:new Map([...svg.querySelectorAll('[data-map-geography-id]')].map((path)=>[path.dataset.mapGeographyId,path])),bzoneFeatures,azoneFeatures,mpoFeatures:new Map((data.mpos?.features||[]).map((feature)=>[String(feature.properties?.regionId||''),feature])),regionsById:new Map((data.regions||[]).map((region)=>[String(region.id),region])),localityNames:new Map((data.localities||[]).map((item)=>[String(item.azoneId),item.localityName])),hitBzones,hitAzones,bzoneIndex:comparisonMapSpatialIndex(hitBzones,projection),azoneIndex:comparisonMapSpatialIndex(hitAzones,projection),labels:svg.querySelector('[data-comparison-map-group="labels"]'),inspected:svg.querySelector('[data-comparison-map-group="inspected"]'),projectView:null};
  state.comparisonMapView=fullView;clearComparisonMapInspector();
  $('comparisonMapTitle').textContent=`${payload.table} / ${payload.variable} by ${payload.geographyLabel || (geo==='bzone'?'Bzone':'County / locality')}`;
  const assignments=payload.assignments||[],unmatched=assignments.reduce((sum,item)=>sum+(item.unmatchedRows||0),0),mapped=(payload.geographyRows||[]).filter((row)=>Number.isFinite(row.referenceValue)||Number.isFinite(row.comparisonValue)).length;
  const project=state.data?.projects?.find((item)=>item.id===payload.reference?.projectId),identity=project?projectPackageName(project):(payload.reference?.packageDisplayName||"VisionEval model");
  $('comparisonMapSubtitle').textContent=`${payload.reference?.label || 'Reference'} compared with ${payload.comparison?.label || 'Comparison'} · ${payload.year} · ${identity} · ${mapped.toLocaleString()} project geographies${unmatched?` · ${unmatched.toLocaleString()} unmatched rows excluded`:''}`;
  focusComparisonMapProject({zoom:true});setComparisonMapExportAvailability();
  if(state.comparisonMapMode==='3d')renderComparisonMap3d();
}

const COMPARISON_MAP_3D_CAPABILITY_STATES = Object.freeze(['loading','ready','renderer-unavailable','webgl-unavailable','initialization-failed']);

function setComparisonMap3dCapability(capability,message=''){
  if(!COMPARISON_MAP_3D_CAPABILITY_STATES.includes(capability))throw new Error(`Unknown 3D capability state: ${capability}`);
  state.comparisonMap3dCapability=capability;state.comparisonMap3dCapabilityMessage=message;
  const control=$('comparisonMap3d'),built=window.__WORKBENCH_BUILD_CAPABILITIES__?.comparisonMap3d!==false;
  control.hidden=!built;control.disabled=capability!=='ready';control.setAttribute('aria-disabled',String(control.disabled));control.title=message;
  if(capability!=='ready'&&state.comparisonMapMode==='3d')setComparisonMapMode('2d');
}

function probeComparisonMapWebgl(){try{const canvas=document.createElement('canvas'),context=canvas.getContext('webgl2',{failIfMajorPerformanceCaveat:false});context?.getExtension('WEBGL_lose_context')?.loseContext();return Boolean(context)}catch{return false}}

async function initializeComparisonMap3dCapability(){
  const enabled=window.__WORKBENCH_BUILD_CAPABILITIES__?.comparisonMap3d!==false;
  if(!enabled)return setComparisonMap3dCapability('renderer-unavailable','3D was omitted from this build because its packaged renderer smoke test did not pass.');
  if(window.__WORKBENCH_MAPLIBRE_ASSET_ERROR__||typeof window.maplibregl?.Map!=='function')return setComparisonMap3dCapability('renderer-unavailable','The bundled 3D renderer asset is unavailable.');
  if(!probeComparisonMapWebgl())return setComparisonMap3dCapability('webgl-unavailable','WebGL 2 is unavailable or disabled. The complete 2D map remains available.');
  const host=document.createElement('div');host.setAttribute('aria-hidden','true');host.style.cssText='position:fixed;left:-10000px;top:-10000px;width:4px;height:4px;overflow:hidden';document.body.appendChild(host);
  let map;
  try{
    await new Promise((resolve,reject)=>{let settled=false,timer;const finish=(error)=>{if(settled)return;settled=true;clearTimeout(timer);error?reject(error):resolve()};timer=setTimeout(()=>finish(new Error('The empty renderer scene timed out.')),8000);try{map=new window.maplibregl.Map({container:host,style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#ffffff'}}]},center:[0,0],zoom:0,attributionControl:false,interactive:false,renderWorldCopies:false});map.once('error',(event)=>finish(event?.error||new Error('The empty renderer scene failed.')));map.once('idle',()=>finish());}catch(error){finish(error)}});
    setComparisonMap3dCapability('ready','Interactive 3D is ready.');
  }catch(error){setComparisonMap3dCapability('initialization-failed',`Map initialization failed: ${error.message}`)}
  finally{try{map?.remove()}catch{}host.remove()}
}

function comparisonMapFeatureId(feature,level){return String(['bzone','marea'].includes(level)?(feature.properties?.bzoneId||feature.properties?.GEOID||''):(feature.properties?.azoneId||feature.properties?.Azones||''))}

function comparisonMap3dBounds(features){const bounds=regionMapBounds([{features}]);return bounds?[[bounds.minX,bounds.minY],[bounds.maxX,bounds.maxY]]:null}

function comparisonMap3dVirginiaBounds(scene=state.comparisonMap3dScene){
  if(!scene)return null;
  // The Virginia camera action is independent of context visibility. Azones
  // provide the clean statewide extent; retain packaged fallbacks for maps
  // whose regional package omits that layer.
  return comparisonMap3dBounds(scene.azones?.length?scene.azones:scene.bzones?.length?scene.bzones:scene.mpos||[]);
}

function comparisonMap3dLabelRows(map,features,level){
  state.comparisonMap3dMarkers.forEach((marker)=>marker.remove());state.comparisonMap3dMarkers=[];
  const showNames=$('comparisonMapIdLabels').checked,showValues=$('comparisonMapValueLabels').checked;if(!showNames&&!showValues)return;
  const occupied=[];
  const valueText=(feature)=>{const rawValue=feature.properties?.__displayValue,value=rawValue===null||rawValue===undefined?NaN:Number(rawValue);return Number.isFinite(value)?comparisonMapSignedValue(value,{percent:$('mapMetric').value==='percentChange',unit:$('mapMetric').value==='percentChange'?'':state.mapPayload?.units?` ${state.mapPayload.units}`:''}):'N/A'};
  for(const feature of features){const id=comparisonMapFeatureId(feature,level),point=regionMapInteriorLabel(feature,{point:(value)=>value});if(point.radius<=0)continue;const name=feature.properties?.localityName||feature.properties?.name||feature.properties?.__name||'',value=showValues?valueText(feature):'',candidates=showNames&&showValues?[[name,id,value],[id,value],[value]]:showNames?[[name,id],[id]]:[[value]],screen=map.project([point.x,point.y]),radiusScreen=map.project([point.x+point.radius,point.y]),available=Math.max(18,Math.hypot(radiusScreen.x-screen.x,radiusScreen.y-screen.y)*2);let accepted='';for(const candidate of candidates){const text=candidate.filter(Boolean).join('\n');if(!text)continue;const lines=text.split('\n'),width=Math.min(190,Math.max(42,...lines.map((line)=>line.length*6))),height=lines.length*13+7,box={left:screen.x-width/2,right:screen.x+width/2,top:screen.y-height/2,bottom:screen.y+height/2};if(width>available*1.8||occupied.some((item)=>item.left<box.right&&item.right>box.left&&item.top<box.bottom&&item.bottom>box.top))continue;occupied.push(box);accepted=text;break}if(!accepted)continue;const element=document.createElement('div');element.className='comparison-map-3d-label';element.textContent=accepted;const marker=new window.maplibregl.Marker({element,anchor:'center'}).setLngLat([point.x,point.y]).addTo(map);state.comparisonMap3dMarkers.push(marker);if(state.comparisonMap3dMarkers.length>=100)break;
  }
}

function comparisonMap3dRows(){
  const density=$('comparisonMap3dHeight').value==='change-density',level=state.mapPayload?.geographyLevel,displayRows=comparisonMapDisplayRows();let heightRows=density?new Map((state.comparisonMapDensity?.geographyRows||[]).map((row)=>[String(row.geographyId),row])):comparisonMapDisplayRows();
  if(density&&level==='marea'){const expanded=new Map();for(const [marea,bzones] of Object.entries(state.mapPayload?.mareaBzones||{})){const row=heightRows.get(String(marea));for(const bzone of bzones||[])expanded.set(String(bzone),row?{...row,mareaId:marea,geographyId:String(bzone)}:null);}heightRows=expanded;}
  return {density,level,displayRows,heightRows};
}

async function loadComparisonMapDensity(){
  const geographyLevel=['bzone','marea'].includes(state.mapPayload?.geographyLevel)?state.mapPayload.geographyLevel:'azone',signature=JSON.stringify([$('mapReference').value,$('mapComparison').value,$('mapYear').value,geographyLevel]);if(state.comparisonMapDensity&&state.comparisonMapDensitySignature===signature)return state.comparisonMapDensity;
  startCompareActivity('Calculating changed-variable density','Validating saved comparison results.');const operation=await post('/api/comparison/operations/start',{operationKind:'change-density',reference:$('mapReference').value,comparison:$('mapComparison').value,year:$('mapYear').value,geographyLevel});state.comparisonMapDensityOperationId=operation.id;state.comparisonOperationId=operation.id;let status=operation;
  while(['waiting','running'].includes(status.state)){setCompareActivityPhase('Calculating changed-variable density',status.message||status.phase||'Assigning output variables to project geography.');await new Promise((resolve)=>setTimeout(resolve,350));status=await request(`/api/comparison/operations/status?id=${encodeURIComponent(operation.id)}`);}
  state.comparisonMapDensityOperationId='';state.comparisonOperationId='';if(status.state==='cancelled')throw new DOMException('Stopped','AbortError');if(status.state!=='succeeded'||!status.result)throw new Error(status.message||'Changed-variable density could not be calculated.');state.comparisonMapDensity=status.result;state.comparisonMapDensitySignature=signature;finishCompareActivity('succeeded','Changed-variable density ready',`${status.result.geographyRows?.length||0} project geographies were evaluated.`);return status.result;
}

async function comparisonMap3dSceneData(){
  if($('comparisonMap3dHeight').value==='change-density')await loadComparisonMapDensity();
  const {density,level,displayRows,heightRows}=comparisonMap3dRows(),data=state.comparisonMapData,features=(['bzone','marea'].includes(level)?data.bzones?.features:data.azones?.features)||[],scope=new Set(displayRows.keys()),project=features.filter((feature)=>scope.has(comparisonMapFeatureId(feature,level))),scale=comparisonMapScale(),densityMax=Math.max(1,...[...heightRows.values()].map((row)=>Number(row?.changedVariableCount)||0)),heightLimit=comparisonMapPercentile([...heightRows.values()].map((row)=>Math.abs(comparisonMapMetricValue(row))).filter(Number.isFinite),.95),elevationDirection=['increase','decrease'].includes(state.comparisonMap3dElevationDirection)?state.comparisonMap3dElevationDirection:'all';
  const valueFeatures=project.map((feature)=>{const id=comparisonMapFeatureId(feature,level),displayRow=displayRows.get(id),heightRow=heightRows.get(id),displayCandidate=comparisonMapMetricValue(displayRow),heightCandidate=density?Number(heightRow?.changedVariableCount):displayCandidate,displayValue=Number.isFinite(displayCandidate)?displayCandidate:null,heightValue=Number.isFinite(heightCandidate)?heightCandidate:null,direction=comparisonMapDirection(displayValue),directionVisible=elevationDirection==='all'||elevationDirection===direction,ratio=!Number.isFinite(heightValue)?0:density?Math.min(1,Math.abs(heightValue)/densityMax):Math.min(1,Math.abs(heightValue)/heightLimit),color=!Number.isFinite(displayValue)?comparisonPaletteColor('map','neutral'):comparisonMapColor(displayValue,scale),base=0,height=directionVisible&&['increase','decrease'].includes(direction)?ratio*12000:0;return {type:'Feature',geometry:feature.geometry,properties:{...feature.properties,__id:id,__displayValue:displayValue,__heightValue:heightValue,__available:Number.isFinite(displayValue),__heightAvailable:Number.isFinite(heightValue),__base:base,__height:height,__color:color,__direction:direction,__name:displayRow?.name||feature.properties?.localityName||feature.properties?.name||id,__capped:!density&&Number.isFinite(heightValue)&&Math.abs(heightValue)>heightLimit}}});
  return {density,level,displayRows,heightRows,project:valueFeatures,originalProject:project,azones:data.azones?.features||[],bzones:data.bzones?.features||[],mpos:data.mpos?.features||[],elevationDirection,scale,densityMax,heightLimit};
}

function comparisonMapHexRgba(value,alpha=.94){const text=String(value||''),hex=text.match(/^#([0-9a-f]{6})$/i),rgb=text.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);if(rgb)return rgb.slice(1,4).map((channel)=>Math.max(0,Math.min(255,Number(channel)))/255).concat(alpha);if(!hex)return[.5,.5,.5,alpha];const number=parseInt(hex[1],16);return[(number>>16&255)/255,(number>>8&255)/255,(number&255)/255,alpha]}

function comparisonMap3dLayerVisible(name){return Boolean(document.querySelector(`[data-comparison-map-layer="${name}"]`)?.checked)}

function updateComparisonMap3dSources(map,scene){
  const collection=(features)=>({type:'FeatureCollection',features});
  const borderColor=getComputedStyle(document.documentElement).getPropertyValue('--text').trim()||'#243244';
  const borderMesh=window.WorkbenchExtrusionBorders?.buildMesh(scene.project,window.maplibregl,borderColor);
  const projectBounds=comparisonMap3dBounds(scene.project);if(projectBounds)state.comparisonMap3dDefaultCamera={bounds:projectBounds,pitch:52,bearing:-20};
  map.getSource('azones')?.setData(collection(scene.azones));map.getSource('bzones')?.setData(collection(scene.bzones));map.getSource('project')?.setData(collection(scene.originalProject));map.getSource('mpos')?.setData(collection(scene.mpos));map.getSource('values')?.setData(collection(scene.project));
  const projectOnly=$('comparisonMapProjectOnly').checked;
  ['azone-context-fill','azone-context-line'].forEach((id)=>map.setLayoutProperty(id,'visibility',!projectOnly&&comparisonMap3dLayerVisible('azones')?'visible':'none'));['bzone-context-fill','bzone-context-line'].forEach((id)=>map.setLayoutProperty(id,'visibility',!projectOnly&&comparisonMap3dLayerVisible('bzones')?'visible':'none'));map.setLayoutProperty('mpo-line','visibility',!projectOnly&&comparisonMap3dLayerVisible('mpos')?'visible':'none');
  state.comparisonMap3dBorderLayer?.setMesh(borderMesh);
  comparisonMap3dLabelRows(map,scene.project,scene.level);state.comparisonMap3dScene=scene;
}

function initializeComparisonMap3dMap(scene){
  const maplibre=window.maplibregl,container=$('comparisonMap3dCanvas'),collection=(features)=>({type:'FeatureCollection',features});container.innerHTML='';
  const map=new maplibre.Map({container,style:{version:8,sources:{azones:{type:'geojson',data:collection(scene.azones)},bzones:{type:'geojson',data:collection(scene.bzones)},project:{type:'geojson',data:collection(scene.originalProject)},mpos:{type:'geojson',data:collection(scene.mpos)},values:{type:'geojson',data:collection(scene.project)}},layers:[{id:'background',type:'background',paint:{'background-color':'#eef2f5'}},{id:'azone-context-fill',type:'fill',source:'azones',paint:{'fill-color':'#dbe3e9','fill-opacity':.11}},{id:'azone-context-line',type:'line',source:'azones',paint:{'line-color':'#8094a5','line-width':.55,'line-opacity':.42}},{id:'bzone-context-fill',type:'fill',source:'bzones',paint:{'fill-color':'#dbe3e9','fill-opacity':.035}},{id:'bzone-context-line',type:'line',source:'bzones',paint:{'line-color':'#aab7c2','line-width':.35,'line-opacity':.3}},{id:'mpo-line',type:'line',source:'mpos',paint:{'line-color':'#163f68','line-width':1.3,'line-opacity':.68}},{id:'values-hit',type:'fill',source:'values',paint:{'fill-color':'#000000','fill-opacity':.001}},{id:'values-extrusion',type:'fill-extrusion',source:'values',paint:{'fill-extrusion-color':['get','__color'],'fill-extrusion-height':['get','__height'],'fill-extrusion-base':['get','__base'],'fill-extrusion-opacity':.92}}]},center:[-78.5,37.8],zoom:6,pitch:52,bearing:-20,attributionControl:false,renderWorldCopies:false,preserveDrawingBuffer:true});state.comparisonMap3d=map;state.comparisonMap3dScene=scene;
  map.addControl(new maplibre.NavigationControl({showCompass:true,showZoom:false,visualizePitch:true}),'top-right');
  map.on('load',()=>{state.comparisonMap3dBorderLayer=new window.WorkbenchExtrusionBorders.BorderLayer();map.addLayer(state.comparisonMap3dBorderLayer);updateComparisonMap3dSources(map,scene);const bounds=comparisonMap3dBounds(scene.project);if(bounds){map.fitBounds(bounds,{padding:45,pitch:52,bearing:-20,duration:0});state.comparisonMap3dDefaultCamera={bounds,pitch:52,bearing:-20}}});map.on('moveend',()=>comparisonMap3dLabelRows(map,state.comparisonMap3dScene?.project||[],state.comparisonMap3dScene?.level));
  const tooltip=$('comparisonMap3dTooltip');map.on('mousemove','values-hit',(event)=>{map.getCanvas().style.cursor='pointer';const item=event.features?.[0]?.properties||{},available=item.__available===true||item.__available==='true',densityNow=state.comparisonMap3dScene?.density,displayNumber=Number(item.__displayValue),displayValue=!available?'Unavailable':comparisonMapSignedValue(displayNumber,{percent:$('mapMetric').value==='percentChange',unit:$('mapMetric').value==='percentChange'?'':state.mapPayload?.units||''}),heightValue=Number(item.__heightValue),height=densityNow&&Number.isFinite(heightValue)?`<span>3D height: ${heightValue.toLocaleString()} changed variables</span>`:'',direction=item.__direction==='decrease'?'▼ Decrease':item.__direction==='increase'?'▲ Increase':item.__direction==='neutral'?'• Neutral':'Unavailable';tooltip.innerHTML=`<strong>${escapeHtml(item.__name||item.__id)}</strong><span>${escapeHtml(item.__id||'')} · ${escapeHtml(direction)}</span><b>${escapeHtml(displayValue)}</b>${height}`;tooltip.style.left=`${event.point.x+12}px`;tooltip.style.top=`${event.point.y+12}px`;tooltip.hidden=false});map.on('mouseleave','values-hit',()=>{map.getCanvas().style.cursor='';tooltip.hidden=true});map.on('click','values-hit',(event)=>{const id=String(event.features?.[0]?.properties?.__id||''),current=state.comparisonMap3dScene;if(!id||!current)return;const original=current.originalProject.find((item)=>comparisonMapFeatureId(item,current.level)===id),densityRow=current.density?current.heightRows.get(id):null;state.comparisonMapSelectedFeature={id,feature:original,type:current.level,densityRow};renderComparisonMapInspector()});
}

async function renderComparisonMap3dBars(){
  if(state.comparisonMapMode!=='3d'||!state.mapPayload||!state.comparisonMapData)return;const container=$('comparisonMap3dCanvas'),fallback=$('comparisonMap3dFallback');if(state.comparisonMap3dCapability!=='ready'){setComparisonMapMode('2d');fallback.textContent=`${state.comparisonMap3dCapabilityMessage} The complete 2D comparison map remains available.`;fallback.hidden=false;return}fallback.hidden=true;container.hidden=false;
  try{const scene=await comparisonMap3dSceneData(),map=state.comparisonMap3d;if(map&&map.getSource('values'))updateComparisonMap3dSources(map,scene);else initializeComparisonMap3dMap(scene);const modeText={all:'▼ Decreases and ▲ increases rise by magnitude.',increase:'Only ▲ increases rise; decreases remain flat.',decrease:'Only ▼ decreases rise; increases remain flat.'}[scene.elevationDirection],legend=$('comparisonMapLegend');legend.querySelector('[data-comparison-map-3d-note]')?.remove();legend.insertAdjacentHTML('beforeend',`<small data-comparison-map-3d-note><strong>Elevation:</strong> ${escapeHtml(modeText)} Dashed top borders identify decreases; solid borders identify increases.</small>`)}catch(error){fallback.textContent=`Map update failed: ${error.message} The 2D comparison map remains functional.`;fallback.hidden=false;container.hidden=true;}
}

async function renderComparisonMap3d(){return renderComparisonMap3dBars()}

function setComparisonMapMode(mode){state.comparisonMapMode=mode==='3d'?'3d':'2d';const raised=state.comparisonMapMode==='3d',twoD=$('comparisonMap2d'),threeD=$('comparisonMap3d'),switcher=twoD.closest('.comparison-map-mode');twoD.classList.toggle('active',!raised);threeD.classList.toggle('active',raised);twoD.setAttribute('aria-checked',String(!raised));threeD.setAttribute('aria-checked',String(raised));twoD.tabIndex=raised?-1:0;threeD.tabIndex=raised?0:-1;switcher?.classList.toggle('is-3d',raised);$('comparisonMapCanvas').hidden=raised;$('comparisonMap3dCanvas').hidden=!raised;$('comparisonMap3dHeightField').hidden=!raised;$('comparisonMapProjectOnlyField').hidden=!raised;$('comparisonMap3dAdvanced').hidden=!raised;$('resetComparisonMapBearing').hidden=!raised;if(raised)renderComparisonMap3d();else{$('comparisonMap3dFallback').hidden=true;$('comparisonMapLegend').querySelector('[data-comparison-map-3d-note]')?.remove();updateComparisonMapLabels();}}

function comparisonMapPointer(event) {
  const rect=$('comparisonMapCanvas').getBoundingClientRect(),view=state.comparisonMapView;return{x:view.x+(event.clientX-rect.left)/rect.width*view.width,y:view.y+(event.clientY-rect.top)/rect.height*view.height};
}

function inspectComparisonMapAt(point) {
  const scene=state.comparisonMapScene;if(!scene)return;
  const index=['bzone','marea'].includes(state.mapPayload?.geographyLevel)?scene.bzoneIndex:scene.azoneIndex,entries=comparisonMapIndexedEntries(index,{minX:point.x,minY:point.y,maxX:point.x,maxY:point.y});
  const hit=entries.find((entry)=>point.x>=entry.bounds.minX&&point.x<=entry.bounds.maxX&&point.y>=entry.bounds.minY&&point.y<=entry.bounds.maxY&&regionMapFeatureContains(entry.feature,point,scene.projection));
  if(!hit)return clearComparisonMapInspector();state.comparisonMapSelectedFeature={...hit,type:state.mapPayload.geographyLevel};renderComparisonMapInspector();
}

async function generateComparisonMap() {
  if(!comparisonMapPackage())return notify('Install a model or regional package that provides map geometry to use Map Visualization.','error');
  if($('mapReference').value===$('mapComparison').value)return notify('Choose different reference and comparison results.','error');
  setBusy($('generateMap'),true,'Generating…');
  try{
    await loadComparisonMapGeometry();startCompareActivity('Generating comparison map','Preparing geographic aggregation.');
    const requestBody=comparisonMapRequest(),operation=await post('/api/comparison/operations/start',requestBody);state.comparisonOperationId=operation.id;let status=operation;
    while(['waiting','running'].includes(status.state)){setCompareActivityPhase('Generating comparison map',status.message||'Aggregating numeric rows by geography.');await new Promise((resolve)=>setTimeout(resolve,300));status=await request(`/api/comparison/operations/status?id=${encodeURIComponent(operation.id)}`,{signal:state.compareController.signal});}
    if(status.state==='cancelled')throw new DOMException('Stopped','AbortError');if(status.state!=='succeeded'||!status.result)throw new Error(status.message||'Map aggregation failed.');
    state.mapPayload=status.result;state.mapInputSignature=JSON.stringify(requestBody);state.mapDirty=false;$('mapStaleMessage').hidden=true;renderComparisonMap();finishCompareActivity('succeeded','Generating comparison map complete',`${status.result.geographyRows?.length||0} geographic values are ready.`);syncMenuContext();
  }catch(error){if(state.compareActivity?.status==='running')finishCompareActivity('failed',error.name==='AbortError'?'Generating comparison map stopped':'Generating comparison map failed',error.name==='AbortError'?'The operation was stopped.':error.message);if(error.name!=='AbortError')notify(error.message,'error');}
  finally{state.comparisonOperationId='';setBusy($('generateMap'),false);}
}

function setComparisonMapExportAvailability() {
  const enabled=Boolean(state.mapPayload?.mapToken)&&!state.mapDirty&&Boolean(state.comparisonMapScene);
  $('toggleMapExport').disabled=!enabled;
  ['exportMapPdf','exportMapPng','exportMapSvg','exportMapCsv','exportMapWorkbook'].forEach((id)=>{if($(id))$(id).disabled=!enabled;});
}

function setComparisonMapExportOpen(open) {
  const menu=$('mapExportMenu'),button=$('toggleMapExport');
  menu.hidden=!open;button.setAttribute('aria-expanded',String(open));
  if(open)menu.querySelector('button:not(:disabled)')?.focus();
}

function runComparisonMapExport(action) {
  setComparisonMapExportOpen(false);
  return action();
}

function comparisonMapExportParams() {
  return new URLSearchParams({mapToken:state.mapPayload?.mapToken||'',packageId:state.comparisonMapPackageId||'',scopeId:[...comparisonMapScopeIds()].join('|')});
}

async function exportComparisonMapVisual(format) {
  if(!state.comparisonMapScene||state.mapDirty)return notify('Generate the map before exporting it.','error');
  if(format==='png'&&state.comparisonMapMode==='3d'){
    const canvas=state.comparisonMap3d?.getCanvas();if(!canvas)throw new Error('The 3D map is not ready to export.');const content=canvas.toDataURL('image/png'),filename=compareExportFilename('comparison map 3d','png'),invoke=window.__TAURI_INTERNALS__?.invoke;
    if(invoke){const saved=await invoke('save_visual_export',{format:'png',content,filename,width:canvas.width,height:canvas.height});if(saved)notify(`Saved ${saved}.`,'success');return}const link=document.createElement('a');link.href=content;link.download=filename;link.click();return;
  }
  const source=state.comparisonMapScene.svg.cloneNode(true),view=state.comparisonMapView,scale=comparisonMapScale(),metric=$('mapMetric').selectedOptions[0]?.textContent||'Map value',scope='Project geography';
  const inner=[...source.children].map((child)=>new XMLSerializer().serializeToString(child)).join(''),width=1600,height=1120,mapHeight=850;
  const mapPalette=comparisonPalettes().map,range=scale.kind==='diverging'?`${number(-scale.limit)} to ${number(scale.limit)}`:`${number(scale.min)} to ${number(scale.max)}`,gradient=scale.kind==='diverging'?`${mapPalette.decrease} 0%,${mapPalette.neutral} 50%,${mapPalette.increase} 100%`:`${mapPalette.neutral} 0%,${mapPalette.increase} 100%`;
  const aggregationLabel=String(state.mapPayload.aggregation||"mean").replaceAll("_"," ");
  const stops=scale.kind==='diverging'?`<stop offset="0%" stop-color="${mapPalette.decrease}"/><stop offset="50%" stop-color="${mapPalette.neutral}"/><stop offset="100%" stop-color="${mapPalette.increase}"/>`:`<stop offset="0%" stop-color="${mapPalette.neutral}"/><stop offset="100%" stop-color="${mapPalette.increase}"/>`;
  const svgText=`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><title>${escapeHtml($('comparisonMapTitle').textContent)}</title><style>text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#182331}.region-map-mpo{fill:none;stroke:#163f68;stroke-width:1.5;vector-effect:non-scaling-stroke}.region-map-azone{fill:none;stroke:#2878b8;stroke-width:1;vector-effect:non-scaling-stroke}.region-map-bzone{fill:none;stroke:#98a7b4;stroke-width:.55;vector-effect:non-scaling-stroke}.comparison-map-value{stroke:#fff9;stroke-width:.45;vector-effect:non-scaling-stroke}.comparison-map-context{opacity:.22}.comparison-map-outside-scope{opacity:.16}.region-map-inspected{fill:#2563eb2e;stroke:#1d4ed8;stroke-width:3;vector-effect:non-scaling-stroke}.region-map-label{font-weight:700;paint-order:stroke;stroke:#fff;stroke-width:3px}</style><rect width="1600" height="1120" fill="#fff"/><text x="44" y="50" font-size="30" font-weight="750">${escapeHtml($('comparisonMapTitle').textContent)}</text><text x="44" y="82" font-size="17" fill="#53657a">${escapeHtml($('comparisonMapSubtitle').textContent)}</text><svg x="40" y="112" width="1520" height="${mapHeight}" viewBox="${view.x} ${view.y} ${view.width} ${view.height}" preserveAspectRatio="xMidYMid meet">${inner}</svg><text x="44" y="1000" font-size="18" font-weight="700">${escapeHtml(metric)}</text><defs><linearGradient id="export-scale">${stops}</linearGradient></defs><rect x="210" y="982" width="650" height="22" fill="url(#export-scale)" stroke="#aab4bd"/><text x="880" y="1000" font-size="16">${escapeHtml(range)} ${escapeHtml($('mapMetric').value==='percentChange'?'%':state.mapPayload.units||'')}</text><text x="44" y="1040" font-size="15" fill="#53657a">Scope: ${escapeHtml(scope)} · Gray hatching means unavailable · Muted polygons are outside the model region</text><text x="44" y="1075" font-size="14" fill="#68798b">Generated ${escapeHtml(state.mapPayload.generatedAt||'')} from ${escapeHtml(state.mapPayload.reference?.label||'Reference')} and ${escapeHtml(state.mapPayload.comparison?.label||'Comparison')}. Aggregation: ${escapeHtml(aggregationLabel)} across project rows.</text></svg>`;
  const filename=compareExportFilename('comparison map',format),invoke=window.__TAURI_INTERNALS__?.invoke;
  if(format==='svg'){if(invoke){const saved=await invoke('save_visual_export',{format,content:svgText,filename,width,height});if(saved)notify(`Saved ${saved}.`,'success');return;}const blob=new Blob([svgText],{type:'image/svg+xml'}),link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=filename;link.click();URL.revokeObjectURL(link.href);return;}
  const url=URL.createObjectURL(new Blob([svgText],{type:'image/svg+xml'})),image=new Image();await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=url;});const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;const context=canvas.getContext('2d');context.fillStyle='#ffffff';context.fillRect(0,0,canvas.width,canvas.height);context.drawImage(image,0,0,canvas.width,canvas.height);URL.revokeObjectURL(url);const mime=format==='pdf'?'image/jpeg':'image/png',content=canvas.toDataURL(mime,.94);
  if(invoke){const saved=await invoke('save_visual_export',{format,content,filename,width:canvas.width,height:canvas.height});if(saved)notify(`Saved ${saved}.`,'success');return;}
  if(format==='pdf')return notify('PDF map export is available in the desktop app.','error');const link=document.createElement('a');link.href=content;link.download=filename;link.click();
}

['mapReference','mapComparison'].forEach((id)=>$(id).addEventListener('change',()=>{setComparisonMapDirty();loadComparisonMapOptions()}));
['mapYear','mapGeography','mapAggregation'].forEach((id)=>$(id).addEventListener('change',setComparisonMapDirty));
$('mapTable').addEventListener('change',renderComparisonMapVariables);$('mapVariable').addEventListener('change',renderComparisonMapYears);$('generateMap').addEventListener('click',generateComparisonMap);
$('mapMetric').addEventListener('change',()=>{applyComparisonMapPresentation();if(state.comparisonMapMode==='3d')renderComparisonMap3d()});$('comparisonMapIdLabels').addEventListener('change',()=>{if(state.comparisonMapMode==='3d')renderComparisonMap3d();else updateComparisonMapLabels();});$('comparisonMapValueLabels').addEventListener('change',()=>{if(state.comparisonMapMode==='3d')renderComparisonMap3d();else updateComparisonMapLabels();});
$('comparisonMap2d').addEventListener('click',()=>setComparisonMapMode('2d'));$('comparisonMap3d').addEventListener('click',()=>setComparisonMapMode('3d'));document.querySelector('.comparison-map-mode').addEventListener('keydown',(event)=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const wants3d=['ArrowRight','End'].includes(event.key);if(wants3d&&$('comparisonMap3d').disabled)return;setComparisonMapMode(wants3d?'3d':'2d');$(wants3d?'comparisonMap3d':'comparisonMap2d').focus()});$('comparisonMap3dHeight').addEventListener('change',()=>renderComparisonMap3d());$('resetComparisonMapBearing').addEventListener('click',()=>{const map=state.comparisonMap3d,camera=state.comparisonMap3dDefaultCamera;if(!map||!camera)return;map.fitBounds(camera.bounds,{padding:45,pitch:camera.pitch,bearing:camera.bearing,duration:500})});
document.querySelectorAll('[data-comparison-map-layer]').forEach((input)=>input.addEventListener('change',()=>{applyComparisonMapPresentation();if(state.comparisonMapMode==='3d')renderComparisonMap3d();}));
$('comparisonMapProjectOnly').addEventListener('change',renderComparisonMap3d);
document.querySelectorAll('[data-elevation-direction]').forEach((button)=>button.addEventListener('click',()=>{
  state.comparisonMap3dElevationDirection=button.dataset.elevationDirection;
  document.querySelectorAll('[data-elevation-direction]').forEach((item)=>{const active=item===button;item.classList.toggle('active',active);item.setAttribute('aria-checked',String(active));item.tabIndex=active?0:-1;});
  renderComparisonMap3d();
}));
$('zoomInComparisonMap').addEventListener('click',()=>{if(state.comparisonMapMode==='3d')state.comparisonMap3d?.zoomIn();else zoomComparisonMap(.65)});$('zoomOutComparisonMap').addEventListener('click',()=>{if(state.comparisonMapMode==='3d')state.comparisonMap3d?.zoomOut();else zoomComparisonMap(1/.65)});$('resetComparisonMap').addEventListener('click',()=>{if(state.comparisonMapMode==='3d'){const map=state.comparisonMap3d,bounds=comparisonMap3dVirginiaBounds();if(map&&bounds)map.fitBounds(bounds,{padding:35,pitch:map.getPitch(),bearing:map.getBearing(),duration:500})}else if(state.comparisonMapScene)setComparisonMapView(state.comparisonMapScene.fullView)});$('fitComparisonMap').addEventListener('click',()=>{if(state.comparisonMapMode==='3d'){const map=state.comparisonMap3d,bounds=comparisonMap3dBounds(state.comparisonMap3dScene?.project||[]);if(map&&bounds)map.fitBounds(bounds,{padding:45,pitch:map.getPitch(),bearing:map.getBearing()})}else focusComparisonMapProject({zoom:true})});$('closeComparisonMapInspector').addEventListener('click',clearComparisonMapInspector);
$('comparisonMapCanvas').addEventListener('wheel',(event)=>{if(!state.comparisonMapView)return;event.preventDefault();const pixels=event.deltaY*(event.deltaMode===1?16:event.deltaMode===2?$('comparisonMapCanvas').clientHeight:1),clamped=Math.max(-90,Math.min(90,pixels));zoomComparisonMap(Math.exp(clamped*.0028),comparisonMapPointer(event));},{passive:false});
$('comparisonMapCanvas').addEventListener('dblclick',(event)=>{event.preventDefault();zoomComparisonMap(.5,comparisonMapPointer(event));});
$('comparisonMapCanvas').addEventListener('pointerdown',(event)=>{if(!state.comparisonMapView)return;const canvas=$('comparisonMapCanvas'),start={x:event.clientX,y:event.clientY,view:{...state.comparisonMapView}};state.comparisonMapPointerMoved=false;canvas.setPointerCapture(event.pointerId);const move=(moveEvent)=>{const rect=canvas.getBoundingClientRect(),dx=(moveEvent.clientX-start.x)/rect.width*start.view.width,dy=(moveEvent.clientY-start.y)/rect.height*start.view.height;if(Math.abs(dx)+Math.abs(dy)>.5)state.comparisonMapPointerMoved=true;setComparisonMapView({...start.view,x:start.view.x-dx,y:start.view.y-dy});};const up=(upEvent)=>{canvas.removeEventListener('pointermove',move);canvas.removeEventListener('pointerup',up);canvas.removeEventListener('pointercancel',up);if(!state.comparisonMapPointerMoved)inspectComparisonMapAt(comparisonMapPointer(upEvent));};canvas.addEventListener('pointermove',move);canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);});
$('comparisonMapCanvas').addEventListener('keydown',(event)=>{if(!state.comparisonMapView)return;const view=state.comparisonMapView,step=view.width*.08;if(event.key==='+'||event.key==='=')zoomComparisonMap(.65);else if(event.key==='-')zoomComparisonMap(1/.65);else if(event.key==='ArrowLeft')setComparisonMapView({...view,x:view.x-step});else if(event.key==='ArrowRight')setComparisonMapView({...view,x:view.x+step});else if(event.key==='ArrowUp')setComparisonMapView({...view,y:view.y-step});else if(event.key==='ArrowDown')setComparisonMapView({...view,y:view.y+step});else return;event.preventDefault();});
$('toggleMapExport').addEventListener('click',()=>setComparisonMapExportOpen($('mapExportMenu').hidden));
$('exportMapPdf').addEventListener('click',()=>runComparisonMapExport(()=>exportComparisonMapVisual('pdf')).catch((error)=>notify(error.message,'error')));$('exportMapPng').addEventListener('click',()=>runComparisonMapExport(()=>exportComparisonMapVisual('png')).catch((error)=>notify(error.message,'error')));$('exportMapSvg').addEventListener('click',()=>runComparisonMapExport(()=>exportComparisonMapVisual('svg')).catch((error)=>notify(error.message,'error')));$('exportMapCsv').addEventListener('click',()=>runComparisonMapExport(()=>saveBackendExport('comparison-map-csv')).catch((error)=>notify(error.message,'error')));$('exportMapWorkbook').addEventListener('click',()=>runComparisonMapExport(()=>exportArtifact('comparison-map')));
document.addEventListener('pointerdown',(event)=>{if(!$('mapExportMenu').hidden&&!event.target.closest('.map-export-menu'))setComparisonMapExportOpen(false);});
document.addEventListener('keydown',(event)=>{if(event.key==='Escape'&&!$('mapExportMenu').hidden){setComparisonMapExportOpen(false);$('toggleMapExport').focus();}});
if(window.ResizeObserver){
  new ResizeObserver(()=>{if(state.comparisonMapMode==='2d')updateComparisonMapLabels();else state.comparisonMap3d?.resize()}).observe($('comparisonMapCanvas').parentElement);
  new ResizeObserver(()=>{if($("regionGeographyDialog").open)renderRegionGeographySelectionMap()}).observe($("regionGeographyMap"));
}
let workbenchDevicePixelRatio=window.devicePixelRatio;
window.addEventListener("resize",()=>{if(window.devicePixelRatio!==workbenchDevicePixelRatio){workbenchDevicePixelRatio=window.devicePixelRatio;if($("regionGeographyDialog").open)renderRegionGeographySelectionMap();updateComparisonMapLabels();}});

function renderDashboardControls(){
  if(state.comparisonIds.length<2){$("dashboardVariableList").innerHTML=`<p class="muted">Load at least two datastores to build a percent-change chart.</p>`;$("generateDashboard").disabled=true;return;}const records=state.comparisonIds.map((id)=>state.data.catalog.find((item)=>item.id===id)).filter(Boolean),options=records.map((item)=>`<option value="${escapeHtml(item.id)}">${escapeHtml(item.displayLabel || item.label)}</option>`).join("");$("dashboardReference").innerHTML=options;$("dashboardComparison").innerHTML=options;$("dashboardReference").value=state.comparisonIds[0];$("dashboardComparison").value=state.comparisonIds[1];
  const years=[...new Set(state.variables.flatMap((item)=>item.years))].sort();$("dashboardYear").innerHTML=years.map((year)=>`<option ${year==="2045"?"selected":""}>${year}</option>`).join("");
  $("dashboardVariableList").innerHTML=state.variables.map((item)=>`<label class="check-option" data-dashboard-variable-option="${escapeHtml(`${item.table} ${item.name}`.toLowerCase())}"><input type="checkbox" data-dashboard-variable="${escapeHtml(`${item.table}/${item.name}`)}"><span><strong>${escapeHtml(item.table)} / ${escapeHtml(item.name)}</strong>${item.description?`<small>${escapeHtml(item.description)}</small>`:""}</span></label>`).join("");
  document.querySelectorAll("[data-dashboard-variable]").forEach((box)=>box.addEventListener("change",()=>{updateDashboardVariableSummary();setDashboardDirty();}));
  state.dashboardVariableQuery="";$("dashboardVariableSearch").value="";setDashboardVariablesExpanded(true);updateDashboardVariableVisibility();
  loadDashboardGeoOptions();
}
async function loadDashboardGeoOptions(){
  if(!state.comparisonIds.length||!$("dashboardYear").value)return;
  try{const payload=await request(`/api/comparison/cross-output-geo-options?reference=${encodeURIComponent($("dashboardReference").value||state.comparisonIds[0])}&year=${encodeURIComponent($("dashboardYear").value)}`);state.dashboardGeoOptions=payload.levels||[];state.dashboardGeoMessage=payload.message||"";if(!state.dashboardGeoOptions.some((item)=>item.field===state.dashboardFilterField)){state.dashboardFilterField="";state.dashboardFilterValues.clear();}renderDashboardGeoControls();}
  catch(error){state.dashboardGeoOptions=[];state.dashboardGeoMessage=error.message;renderDashboardGeoControls();}
}
function renderDashboardGeoControls(){configureLocationSelector({containerId:"dashboardGeoControls",prefix:"dashboard",levels:state.dashboardGeoOptions||[],message:state.dashboardGeoMessage,field:state.dashboardFilterField,values:state.dashboardFilterValues,search:state.dashboardLocationSearch,allowAll:true,setField:(value)=>state.dashboardFilterField=value,setSearch:(value)=>state.dashboardLocationSearch=value,onChange:setDashboardDirty,note:""});}
function setDashboardDirty(){state.dashboardDirty=Boolean(state.dashboardPayload);$("dashboardStaleMessage").hidden=!state.dashboardDirty;setDashboardExportAvailability();syncMenuContext();}
function setDashboardExportAvailability(){const enabled=Boolean(state.dashboardPayload?.dashboardToken)&&!state.dashboardDirty;["exportDashboardPdf","exportDashboardCsv","exportDashboardWorkbook"].forEach((id)=>{$(id).disabled=!enabled;});}
function setDashboardVariablesExpanded(expanded){state.dashboardVariablesExpanded=expanded;$("dashboardVariablesBody").hidden=!expanded;$("toggleDashboardVariables").setAttribute("aria-expanded",String(expanded));}
function updateDashboardVariableSummary(){const selected=document.querySelectorAll("[data-dashboard-variable]:checked").length;$("dashboardVariableSummary").textContent=selected?`${selected} selected`:"All numeric outputs";}
function updateDashboardVariableVisibility(){const query=(state.dashboardVariableQuery||"").trim().toLowerCase();document.querySelectorAll("[data-dashboard-variable-option]").forEach((option)=>{option.hidden=Boolean(query&&!option.dataset.dashboardVariableOption.includes(query));});updateDashboardVariableSummary();}
$("toggleDashboardVariables").addEventListener("click",()=>setDashboardVariablesExpanded(!state.dashboardVariablesExpanded));
$("dashboardVariableSearch").addEventListener("input",(event)=>{state.dashboardVariableQuery=event.target.value;updateDashboardVariableVisibility();});
$("selectDashboardVariables").addEventListener("click",()=>{document.querySelectorAll("[data-dashboard-variable-option]:not([hidden]) [data-dashboard-variable]").forEach((box)=>{box.checked=true;});updateDashboardVariableSummary();setDashboardDirty();});
$("clearDashboardVariables").addEventListener("click",()=>{document.querySelectorAll("[data-dashboard-variable]").forEach((box)=>{box.checked=false;});updateDashboardVariableSummary();setDashboardDirty();});
function dashboardParams(){const params=new URLSearchParams({reference:$("dashboardReference").value,comparison:$("dashboardComparison").value,year:$("dashboardYear").value});const selected=[...document.querySelectorAll("[data-dashboard-variable]:checked")].map((box)=>box.dataset.dashboardVariable);if(selected.length)params.set("variableKey",selected.join("|"));if(state.dashboardFilterField&&state.dashboardFilterValues.size){params.set("filterField",state.dashboardFilterField);params.set("filterValue",[...state.dashboardFilterValues].join("|"));}return params;}
function dashboardDisplaySettings(){const mode=$("dashboardDisplayMode").value,value=Number($("dashboardDisplayValue").value)||0;return{sortBy:$("dashboardSort").value,displayMode:mode,threshold:mode==="threshold"?Math.max(0,value):0,count:mode==="extremes"?Math.max(1,Math.floor(value||5)):5,hideZero:$("dashboardHideZero").checked};}
function dashboardDisplayRows(){const source=[...(state.dashboardPayload?.rows||[])],settings=dashboardDisplaySettings();let rows=source;if(settings.displayMode==="threshold")rows=source.filter((row)=>Math.abs(row.percentChange)>=settings.threshold);else if(settings.displayMode==="extremes"){const increases=source.filter((row)=>row.percentChange>0).sort((a,b)=>b.percentChange-a.percentChange).slice(0,settings.count),decreases=source.filter((row)=>row.percentChange<0).sort((a,b)=>a.percentChange-b.percentChange).slice(0,settings.count),keys=new Set([...increases,...decreases].map((row)=>`${row.table}/${row.variable}`));rows=source.filter((row)=>keys.has(`${row.table}/${row.variable}`));}if(settings.hideZero)rows=rows.filter((row)=>row.percentChange!==0);if(settings.sortBy==="value_desc")rows.sort((a,b)=>b.percentChange-a.percentChange);else if(settings.sortBy==="value_asc")rows.sort((a,b)=>a.percentChange-b.percentChange);else if(settings.sortBy==="magnitude")rows.sort((a,b)=>Math.abs(b.percentChange)-Math.abs(a.percentChange));else rows.sort((a,b)=>a.label.localeCompare(b.label,undefined,{numeric:true}));return rows;}
$("generateDashboard").addEventListener("click",async()=>{const params=dashboardParams();try{state.dashboardPayload=await withCompareActivity("Generating chart","Scanning selected numeric variables.",()=>request(`/api/comparison/dashboard?${params}`,{signal:state.compareController.signal}));state.dashboardInputSignature=params.toString();state.dashboardDirty=false;$("dashboardStaleMessage").hidden=true;setDashboardVariablesExpanded(false);renderDashboard(state.dashboardPayload);setDashboardExportAvailability();syncMenuContext();}catch(error){if(error.name!=="AbortError")notify(error.message,"error");}});
function renderDashboard(payload){const rows=dashboardDisplayRows(),unavailable=(payload.unavailable||[]),notChartedTitle=unavailable.length?unavailable.map((item)=>`${item.table} / ${item.variable}: ${item.reason}`).join("\n"):"Outputs are not charted when they are nonnumeric, have no numeric rows in the selected location scope, have a zero reference total, or cannot be read safely.";$("dashboardMetrics").innerHTML=metric("Displayed bars",rows.length)+metric("Chartable outputs",payload.availableRows)+metric("Not charted",payload.unavailableRows,{title:notChartedTitle})+metric("Year",payload.year);const max=Math.max(1,...rows.map((row)=>Math.abs(row.percentChange)));$("dashboardDetails").className="dashboard-chart";$("dashboardDetails").innerHTML=`<p class="dashboard-scope"><strong>Scope:</strong> ${escapeHtml(payload.scopeLabel||"All locations")}</p>`+(rows.map((row)=>{const width=Math.abs(row.percentChange)/max*50,left=row.percentChange<0?50-width:50;return `<div class="dashboard-row"><div><strong>${escapeHtml(row.label)}</strong><small>${escapeHtml(row.units||"")}</small></div><div class="dashboard-track"><span class="dashboard-zero"></span><span class="dashboard-bar ${row.percentChange<0?"negative":"positive"}" style="left:${left}%;width:${width}%"></span></div><strong>${percentage(row.percentChange)}%</strong></div>`;}).join("")||`<p class="muted">No generated variables match this display filter.</p>`);}
function updateDashboardDisplayControl(){const mode=$("dashboardDisplayMode").value,label=$("dashboardDisplayValueLabel");label.hidden=mode==="all";document.querySelector(".dashboard-view-controls").classList.toggle("has-display-value",mode!=="all");if(mode==="threshold"){$("dashboardDisplayValueText").textContent="Minimum magnitude (%)";$("dashboardDisplayValue").min="0";$("dashboardDisplayValue").step="0.1";$("dashboardDisplayValue").title="Show changes at or above this percentage in either direction.";}else if(mode==="extremes"){$("dashboardDisplayValueText").textContent="Bars per direction";$("dashboardDisplayValue").min="1";$("dashboardDisplayValue").step="1";$("dashboardDisplayValue").title="Show up to this many largest increases and this many largest decreases.";}if(state.dashboardPayload)renderDashboard(state.dashboardPayload);}
$("dashboardSort").addEventListener("change",()=>state.dashboardPayload&&renderDashboard(state.dashboardPayload));
$("dashboardDisplayMode").addEventListener("change",updateDashboardDisplayControl);$("dashboardDisplayValue").addEventListener("input",()=>state.dashboardPayload&&renderDashboard(state.dashboardPayload));$("dashboardHideZero").addEventListener("change",()=>state.dashboardPayload&&renderDashboard(state.dashboardPayload));
["dashboardReference","dashboardComparison","dashboardYear"].forEach((id)=>$(id).addEventListener("change",()=>{setDashboardDirty();if(id!=="dashboardComparison")loadDashboardGeoOptions();}));
$("exportDashboardPdf").addEventListener("click",()=>saveBackendExport("dashboard-pdf").catch((error)=>notify(error.message||String(error),"error")));
$("exportDashboardCsv").addEventListener("click",()=>saveBackendExport("dashboard-csv").catch((error)=>notify(error.message||String(error),"error")));
$("exportDashboardWorkbook").addEventListener("click",()=>exportArtifact("dashboard"));

let lastMenuContext = "";
const APP_ZOOM_KEY="visioneval-app-zoom";
function appZoomValue(){const value=Number(localStorage.getItem(APP_ZOOM_KEY)||1);return Math.max(.8,Math.min(2,Number.isFinite(value)?value:1));}
async function setApplicationZoom(value){const scale=Math.max(.8,Math.min(2,Math.round(value*10)/10));localStorage.setItem(APP_ZOOM_KEY,String(scale));if(window.__TAURI_INTERNALS__?.invoke)await window.__TAURI_INTERNALS__.invoke('set_app_zoom',{scale});syncWorkbenchViewport();requestAnimationFrame(syncWorkbenchViewport);}
function activeMapKind(){if($('regionMapDialog').open&&state.regionMapScene)return'region';if($('comparePage').classList.contains('active')&&$('mapData').classList.contains('active')&&state.comparisonMapScene)return'comparison';return'';}
function runActiveMapAction(action){const kind=activeMapKind();if(kind==='region'){if(action==='in')return zoomRegionMap(.76);if(action==='out')return zoomRegionMap(1.32);if(action==='fit'&&state.regionMapScene?.focusView)return setRegionMapView(state.regionMapScene.focusView);if(action==='extent'&&state.regionMapScene?.fullView)return setRegionMapView(state.regionMapScene.fullView);}if(kind==='comparison'){if(action==='in')return zoomComparisonMap(.65);if(action==='out')return zoomComparisonMap(1/.65);if(action==='fit')return focusComparisonMapProject({zoom:true});if(action==='extent'&&state.comparisonMapScene)return setComparisonMapView(state.comparisonMapScene.fullView);}}
function syncMenuContext() {
  const invoke = window.__TAURI_INTERNALS__?.invoke;
  if (!invoke) return;
  const runtime = state.data?.runtime || {}, activeJob = selectedActiveJob();
  const activeMap=activeMapKind(),mapFocused=activeMap==='region'?Boolean(state.regionMapScene?.currentRegion):activeMap==='comparison'?Boolean(state.comparisonMapScene?.projectView):false,context = {
    hasProject:Boolean(state.selectedProject),
    hasScenario:Boolean(activeEditorVariation()),
    hasFile:Boolean(state.csv),
    fileDirty:Boolean(state.csv && state.editorDirty),
    canRun:Boolean((state.selectedProject || $("runProject")?.value) && runtime.running && runtime.imagePresent && runtimeProfile()?.verified && (runtime.adapter==="native" || runtime.digestMatches !== false)),
    activeJobId:activeJob?.id || "",
    hasRunnableJobs:runnableJobs().length > 0 && !state.stopAllPending,
    hasDependencyExport:Boolean(state.dependencyGraph && state.dependencyTemplateId),
    hasComparisonExport:Boolean(state.lastComparison && !state.compareLocationDirty),
    hasChangeExport:state.comparisonIds.length > 1,
    hasDashboardExport:Boolean(state.dashboardPayload?.dashboardToken) && !state.dashboardDirty,
    hasMapExport:Boolean(state.mapPayload?.mapToken) && !state.mapDirty,
    hasActiveMap:Boolean(activeMap),
    mapHasMpoFocus:mapFocused,
  };
  const serialized = JSON.stringify(context); if (serialized === lastMenuContext) return;
  lastMenuContext = serialized;
  invoke("set_menu_context", {context}).catch(() => { lastMenuContext = ""; });
}

async function handleMenuAction(action) {
  if(action==='zoom-in')return setApplicationZoom(appZoomValue()+.1);
  if(action==='zoom-out')return setApplicationZoom(appZoomValue()-.1);
  if(action==='actual-size')return setApplicationZoom(1);
  if(action==='map-zoom-in')return runActiveMapAction('in');
  if(action==='map-zoom-out')return runActiveMapAction('out');
  if(action==='map-fit-mpo')return runActiveMapAction('fit');
  if(action==='map-virginia')return runActiveMapAction('extent');
  if (action === "new-scenario") return guardUnsaved(() => { switchPage("createPage", {restoreScroll:false}); switchCreateSubpage("createEditor", false); openScenarioDialog(false); });
  if (action === "new-file") return guardUnsaved(() => { const scenario = activeEditorVariation(); if (!scenario) return; switchPage("createPage", {restoreScroll:false}); switchCreateSubpage("createEditor", false); openNewFile(scenario.id); });
  if (action === "batch-change") return guardUnsaved(() => { const scenario=activeEditorVariation(); if (!scenario) return; switchPage("createPage",{restoreScroll:false}); switchCreateSubpage("createEditor",false); openScenarioTools(scenario.id); });
  if (action === "save-file") return saveFileChanges();
  if (action === "run-selected") return guardUnsaved(() => {
    const projectId = $("runProject").value || state.selectedProject?.id;
    if (!projectId) return;
    switchPage("runPage", {restoreScroll:false}); $("runProject").value = projectId; renderRunSelections(); $("runDialog").showModal();
  });
  if (action === "stop-selected-run") { const job = selectedActiveJob(); if (job) return jobAction("/api/runs/cancel", job.id); return; }
  if (action === "stop-all-runs") return stopAllRuns();
  if (action === "export-dependency-svg") return saveDependencyExport("svg");
  if (action === "export-dependency-pdf") return saveDependencyExport("pdf");
  if (action === "export-dependency-html") return saveDependencyExport("html");
  if (action === "export-current-csv") return saveBackendExport("comparison-current-csv");
  if (action === "export-current-xlsx") return exportArtifact("current");
  if (action === "export-all-changed-csv") return prepareChangedOutputExport("all","csv");
  if (action === "export-all-changed-xlsx") return prepareChangedOutputExport("all","xlsx");
  if (action === "export-selected-changed") return openCompareExportDialog("selected-changed");
  if (action === "export-full-variables") return openCompareExportDialog("full-variables");
  if (action === "export-dashboard-pdf") return saveBackendExport("dashboard-pdf");
  if (action === "export-dashboard-csv") return saveBackendExport("dashboard-csv");
  if (action === "export-dashboard-xlsx") return exportArtifact("dashboard");
  if (action === "export-map-pdf") return exportComparisonMapVisual("pdf");
  if (action === "export-map-png") return exportComparisonMapVisual("png");
  if (action === "export-map-svg") return exportComparisonMapVisual("svg");
  if (action === "export-map-csv") return saveBackendExport("comparison-map-csv");
  if (action === "export-map-xlsx") return exportArtifact("comparison-map");
  if (action === "show-workspace-in-finder") return window.__TAURI_INTERNALS__?.invoke("reveal_workspace_location", {location:"projects"}).catch((error) => notify(String(error), "error"));
  if (action === "settings") return openSettings();
  if (action === "user-guide") {
    const invoke = window.__TAURI_INTERNALS__?.invoke;
    if (!invoke) return notify("The workspace user guide is available from the VisionEval Workbench desktop app.", "error");
    return invoke("open_user_guide").catch((error) => notify(String(error), "error"));
  }
  if (action === "keyboard-shortcuts") return $("shortcutDialog").showModal();
  if (action === "runtime-setup-guide") return $("runtimeGuideDialog").showModal();
  if (action === "view-explore") return guardUnsaved(() => switchPage("explorePage"));
  if (action === "view-create") return guardUnsaved(() => switchPage("createPage"));
  if (action === "view-run") return guardUnsaved(() => switchPage("runPage"));
  if (action === "view-compare") return guardUnsaved(() => switchPage("comparePage"));
  if (action === "refresh") return guardUnsaved(() => refreshState());
}
window.addEventListener("visioneval-menu-action", (event) => handleMenuAction(event.detail).catch((error) => notify(error.message || String(error), "error")));

function restorePrimaryPageScroll(pageId, token) {
  const position = state.primaryPageScroll.get(pageId) || {left:0,top:0};
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (state.activePrimaryPage === pageId && state.pageNavigationToken === token) window.scrollTo(position);
  }));
}
function switchPage(pageId, {restoreScroll = true} = {}) {
  const outgoing = document.querySelector(".page.active")?.id;
  if (outgoing === pageId) {
    if (!restoreScroll) window.scrollTo({left:0, top:0});
    return;
  }
  if (outgoing && outgoing !== pageId) state.primaryPageScroll.set(outgoing, {left:window.scrollX,top:window.scrollY});
  closeLocationPopovers();
  state.activePrimaryPage = pageId;
  const token = ++state.pageNavigationToken;
  document.querySelectorAll(".page").forEach((page) => page.classList.toggle("active", page.id === pageId));
  document.querySelectorAll(".primary-tab[data-page]").forEach((button) => button.classList.toggle("active", button.dataset.page === pageId));
  if (pageId === "explorePage") switchExploreSubpage(state.activeExploreSubpage, false);
  if (pageId === "createPage") switchCreateSubpage(state.activeCreateSubpage, false);
  if (pageId === "comparePage") switchSubpage(state.activeCompareSubpage);
  const refresh = pageId === "runPage" || pageId === "comparePage" ? refreshState({ quiet: true }) : null;
  if (restoreScroll) {
    restorePrimaryPageScroll(pageId, token);
    refresh?.finally(() => restorePrimaryPageScroll(pageId, token));
  } else window.scrollTo({left:0, top:0});
  syncMenuContext();
}
function switchSubpage(pageId) {
  state.activeCompareSubpage = pageId;
  document.querySelectorAll(".subpage").forEach((page) => page.classList.toggle("active", page.id === pageId));
  document.querySelectorAll(".subtab").forEach((button) => button.classList.toggle("active", button.dataset.subpage === pageId));
  syncMenuContext();
}
document.querySelectorAll(".primary-tab[data-page]").forEach((button) => button.addEventListener("click", () => guardUnsaved(() => switchPage(button.dataset.page))));
document.querySelectorAll(".subtab[data-subpage]").forEach((button) => button.addEventListener("click", () => switchSubpage(button.dataset.subpage)));
document.querySelectorAll("[data-explore-subpage]").forEach((button) => button.addEventListener("click", () => switchExploreSubpage(button.dataset.exploreSubpage)));
$("exploreExplanations").addEventListener("change", () => { state.exploreExplanationId = $("exploreExplanations").value; loadExploreFiles(state.exploreLibraryId); });
$("exploreSearch").addEventListener("input", renderExploreFiles);
$("dependencyTemplate").addEventListener("change", () => { $("dependencyFocusKind").value = "all"; loadDependencyGraph(); });
$("dependencyFocusKind").addEventListener("change", () => { renderDependencyFocusItems(); if ($("dependencyFocusKind").value === "all") loadDependencyGraph(state.dependencyTemplateId); else if ($("dependencyFocusItem").value) focusDependencyNode($("dependencyFocusItem").value); });
$("dependencyFocusItem").addEventListener("change", () => { if ($("dependencyFocusItem").value) focusDependencyNode($("dependencyFocusItem").value); });
$("dependencyReset").addEventListener("click", () => { $("dependencyFocusKind").value = "all"; renderDependencyFocusItems(); loadDependencyGraph(state.dependencyTemplateId); });
$("dependencyZoomIn").addEventListener("click",()=>zoomDependencyGraph(1.25));
$("dependencyZoomOut").addEventListener("click",()=>zoomDependencyGraph(.8));
$("dependencyZoomActual").addEventListener("click",()=>{const view=state.dependencyViewport,container=$("dependencyGraph");view.scale=1;view.x=20;view.y=20;view.fitPending=false;dependencyViewportTransform();container.focus?.()});
$("dependencyZoomFit").addEventListener("click",fitDependencyGraph);
$("dependencyExportSvg").addEventListener("click",()=>saveDependencyExport("svg"));
$("dependencyExportPdf").addEventListener("click",()=>saveDependencyExport("pdf"));
$("dependencyExportHtml").addEventListener("click",()=>saveDependencyExport("html"));
$("dependencySearch").addEventListener("input",event=>{const query=event.target.value.trim().toLowerCase();if(!query)return $("dependencyGraph").querySelectorAll(".search-match").forEach(node=>node.classList.remove("search-match"));const node=state.dependencyGraph?.nodes.find(item=>[item.label,item.table,item.package,item.file].some(value=>String(value||"").toLowerCase().includes(query)));if(node)centerDependencyNode(node.id)});
$("dependencySearch").addEventListener("keydown",event=>{if(event.key!=="Enter")return;event.preventDefault();const query=event.currentTarget.value.trim().toLowerCase();const node=state.dependencyFullGraph?.nodes.find(item=>[item.label,item.table,item.package,item.file].some(value=>String(value||"").toLowerCase().includes(query)));if(node)focusDependencyNode(node.id)});
$("settingsGear").addEventListener("click",()=>openSettings());
window.addEventListener("resize", () => requestAnimationFrame(fitDependencyGraph));
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
    event.preventDefault();
    if (state.csv && state.editorDirty) saveFileChanges();
  }
});
$("refreshCreate").addEventListener("click", () => guardUnsaved(() => refreshState()));
$("refreshJobs").addEventListener("click", () => refreshState());
function setRunHistoryHidden(hidden) {
  state.runHistoryHidden = Boolean(hidden);
  $("runLayout")?.classList.toggle("history-hidden", state.runHistoryHidden);
  if ($("showRunHistory")) $("showRunHistory").hidden = !state.runHistoryHidden;
}
$("hideRunHistory").addEventListener("click", () => setRunHistoryHidden(true));
$("showRunHistory").addEventListener("click", () => setRunHistoryHidden(false));
$("reloadWorkbench").addEventListener("click", () => window.location.reload());

prunePlatformSpecificContent();
renderPlatformShortcuts();
initializeComparisonMap3dCapability();
setApplicationZoom(appZoomValue()).catch(()=>{});
async function pollAutomaticUpdateStatus(attempt=0){
  try{const payload=await request("/api/updates/status");state.data.updates=payload;renderUpdateIndicator(payload);if(payload.checking&&attempt<4)setTimeout(()=>pollAutomaticUpdateStatus(attempt+1),2500)}catch(_error){}
}
refreshState({ quiet: true }).then(()=>{const message=sessionStorage.getItem("visioneval-settings-reset-message");if(message){sessionStorage.removeItem("visioneval-settings-reset-message");notify(message,"success")}pollAutomaticUpdateStatus()});
setInterval(() => {
  if ($("runPage").classList.contains("active") && !state.selectedJob) refreshState({ quiet: true });
}, 5000);
setInterval(() => { if ($("runPage").classList.contains("active")) pollBackgroundJobLogs(); }, 1800);
