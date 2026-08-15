use base64::{engine::general_purpose::STANDARD as BASE64, Engine as _};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs;
use std::io::{self, Read};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem, Submenu};
use tauri::{AppHandle, Manager};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_notification::NotificationExt;

const CONFIG_VERSION: u32 = 7;
const LEGACY_RUNTIME_IMAGE: &str = "local/visioneval:3.1.1-arm64";
const UNPATCHED_RC6_RUNTIME_IMAGE: &str = "local/visioneval:ve-40-rc6-arm64";
const V1_RUNTIME_IMAGE: &str = "local/visioneval:1.0.0-arm64";
const ARM64_RUNTIME_IMAGE: &str = "local/visioneval:1.0.0-arm64";
#[cfg(target_os = "windows")]
const AMD64_RUNTIME_IMAGE: &str = "local/visioneval:2.0.0-amd64";
const ONBOARDING_VERSION: u32 = 1;
const WORKSPACE_FORMAT_VERSION: u32 = 2;
const WORKSPACE_MARKER: &str = ".visioneval-workspace.json";
const WORKSPACE_SETTINGS: &str = ".workbench/settings.json";

#[derive(Default)]
struct BackendState {
    child: Mutex<Option<Child>>,
    port: Mutex<Option<u16>>,
    quit_requested: Mutex<bool>,
}

fn default_appearance() -> String {
    "light".into()
}
fn default_run_mode() -> String {
    "queued".into()
}
fn default_parallel() -> u8 {
    2
}
fn default_retain_exports() -> bool {
    true
}
fn default_auto_start_docker() -> bool {
    cfg!(not(target_os = "windows"))
}
#[cfg(target_os = "windows")]
fn default_runtime_image() -> &'static str {
    AMD64_RUNTIME_IMAGE
}
#[cfg(not(target_os = "windows"))]
fn default_runtime_image() -> &'static str {
    ARM64_RUNTIME_IMAGE
}

#[derive(Serialize, Deserialize, Clone, Default)]
#[serde(default, rename_all = "camelCase")]
struct RecentWorkspace {
    id: String,
    name: String,
    path: String,
    last_opened_at: String,
}

#[derive(Serialize, Clone, Default)]
#[serde(rename_all = "camelCase")]
struct RecentWorkspaceState {
    id: String,
    name: String,
    path: String,
    display_path: String,
    last_opened_at: String,
    exists: bool,
    valid: bool,
    current: bool,
    removable: bool,
    status: String,
}

#[derive(Serialize, Deserialize, Clone, Default)]
#[serde(default, rename_all = "camelCase")]
struct RuntimeProfile {
    id: String,
    name: String,
    adapter: String,
    platform: String,
    architecture: String,
    image_reference: String,
    ve_runtime_path: String,
    ve_home_path: String,
    rscript_path: String,
    image_digest: String,
    runtime_version: String,
    verified: bool,
    verified_at: String,
    verification_message: String,
    remote_status: String,
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(default, rename_all = "camelCase")]
struct ResourcePreferences {
    default_run_mode: String,
    max_concurrent_runs: u8,
    memory_limit_gb: Option<f64>,
}
impl Default for ResourcePreferences {
    fn default() -> Self {
        Self {
            default_run_mode: default_run_mode(),
            max_concurrent_runs: default_parallel(),
            memory_limit_gb: None,
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Default)]
#[serde(default, rename_all = "camelCase")]
struct MigrationRecovery {
    source_path: String,
    destination_path: String,
    state: String,
    updated_at: String,
    message: String,
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(default, rename_all = "camelCase")]
struct ComparisonPalette {
    increase: String,
    decrease: String,
    neutral: String,
}
impl Default for ComparisonPalette {
    fn default() -> Self {
        Self {
            increase: "#2274a7".into(),
            decrease: "#be3742".into(),
            neutral: "#edf1f4".into(),
        }
    }
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(default, rename_all = "camelCase")]
struct ComparisonPalettes {
    table: ComparisonPalette,
    map: ComparisonPalette,
    chart: ComparisonPalette,
}

impl Default for ComparisonPalettes {
    fn default() -> Self {
        Self {
            table: ComparisonPalette {
                increase: "#168354".into(),
                decrease: "#c43d49".into(),
                neutral: "#a96800".into(),
            },
            map: ComparisonPalette::default(),
            chart: ComparisonPalette {
                increase: "#2274a7".into(),
                decrease: "#be3742".into(),
                neutral: "#9aa6af".into(),
            },
        }
    }
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(default, rename_all = "camelCase")]
struct DesktopConfig {
    configuration_version: u32,
    onboarding_version: u32,
    workspace_root: String,
    workspace_id: String,
    recent_workspaces: Vec<RecentWorkspace>,
    #[serde(default = "default_appearance")]
    theme: String,
    runtime_profiles: Vec<RuntimeProfile>,
    active_runtime_profile_id: String,
    resources: ResourcePreferences,
    notifications_enabled: bool,
    #[serde(default = "default_notification_success_threshold_seconds")]
    notification_success_threshold_seconds: u64,
    #[serde(default = "default_auto_start_docker")]
    auto_start_docker: bool,
    notification_registration_sent: bool,
    comparison_palettes: ComparisonPalettes,
    master_comparison_palette: ComparisonPalette,
    use_master_comparison_palette: bool,
    migration_recovery: Option<MigrationRecovery>,
}
impl Default for DesktopConfig {
    fn default() -> Self {
        Self {
            configuration_version: CONFIG_VERSION,
            onboarding_version: 0,
            workspace_root: String::new(),
            workspace_id: String::new(),
            recent_workspaces: vec![],
            theme: default_appearance(),
            runtime_profiles: vec![],
            active_runtime_profile_id: String::new(),
            resources: ResourcePreferences::default(),
            notifications_enabled: false,
            notification_success_threshold_seconds: default_notification_success_threshold_seconds(
            ),
            auto_start_docker: default_auto_start_docker(),
            notification_registration_sent: false,
            comparison_palettes: ComparisonPalettes::default(),
            master_comparison_palette: ComparisonPalette::default(),
            use_master_comparison_palette: false,
            migration_recovery: None,
        }
    }
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopState {
    platform: String,
    configuration_version: u32,
    onboarding_version: u32,
    configured: bool,
    workspace_valid: bool,
    workspace_status: String,
    workspace_root: String,
    workspace_display_path: String,
    workspace_id: String,
    recommended_workspace_root: String,
    recommended_workspace_display_path: String,
    recent_workspaces: Vec<RecentWorkspaceState>,
    theme: String,
    runtime_profiles: Vec<RuntimeProfile>,
    active_runtime_profile_id: String,
    resources: ResourcePreferences,
    notifications_enabled: bool,
    notification_success_threshold_seconds: u64,
    comparison_palettes: ComparisonPalettes,
    master_comparison_palette: ComparisonPalette,
    use_master_comparison_palette: bool,
    auto_start_docker: bool,
    migration_recovery: Option<MigrationRecovery>,
    blocking_job_count: usize,
}

fn default_notification_success_threshold_seconds() -> u64 {
    60
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct NotificationDelivery {
    shown: bool,
    reason: String,
}

fn notification_suppression_reason(
    enabled: bool,
    outcome: &str,
    elapsed_seconds: Option<u64>,
    success_threshold_seconds: u64,
    force: bool,
    focused: bool,
) -> Option<&'static str> {
    if !enabled {
        return Some("disabled");
    }
    if force {
        return None;
    }
    if outcome == "succeeded" && elapsed_seconds.unwrap_or(0) < success_threshold_seconds {
        return Some("duration");
    }
    focused.then_some("focused")
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(default, rename_all = "camelCase")]
struct WorkspaceSettings {
    version: u32,
    default_template_id: String,
    default_input_library_id: String,
    default_input_explanation_id: String,
    retain_full_exports: bool,
    asset_registrations: Vec<Value>,
}
impl Default for WorkspaceSettings {
    fn default() -> Self {
        Self {
            version: 1,
            default_template_id: String::new(),
            default_input_library_id: String::new(),
            default_input_explanation_id: String::new(),
            retain_full_exports: default_retain_exports(),
            asset_registrations: vec![],
        }
    }
}

#[derive(Deserialize, Default)]
#[serde(default, rename_all = "camelCase")]
struct MenuContext {
    has_project: bool,
    has_scenario: bool,
    has_file: bool,
    file_dirty: bool,
    can_run: bool,
    active_job_id: String,
    has_runnable_jobs: bool,
    has_dependency_export: bool,
    has_comparison_export: bool,
    has_change_export: bool,
    has_dashboard_export: bool,
    has_map_export: bool,
    has_active_map: bool,
    map_has_mpo_focus: bool,
}

fn now_string() -> String {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
        .to_string()
}
fn stable_id(prefix: &str) -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    format!("{prefix}-{nanos:x}-{:x}", std::process::id())
}
fn home_dir() -> PathBuf {
    std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
}

fn reveal_path(path: &Path) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    let mut command = {
        let mut command = Command::new("explorer.exe");
        command.arg(path);
        command
    };
    #[cfg(target_os = "macos")]
    let mut command = {
        let mut command = Command::new("open");
        command.arg(path);
        command
    };
    #[cfg(all(not(target_os = "windows"), not(target_os = "macos")))]
    let mut command = {
        let mut command = Command::new("xdg-open");
        command.arg(path);
        command
    };
    command.spawn().map_err(|error| error.to_string())?;
    Ok(())
}
fn recommended_workspace_root() -> PathBuf {
    home_dir().join("VisionEval Workbench Workspace")
}
fn display_workspace_path(path: &Path) -> String {
    let home = home_dir();
    if let Ok(relative) = path.strip_prefix(&home) {
        if relative.as_os_str().is_empty() {
            return "~".into();
        }
        return format!("~/{}", relative.to_string_lossy());
    }
    path.to_string_lossy().to_string()
}

fn workbench_menu(app: &AppHandle) -> tauri::Result<Menu<tauri::Wry>> {
    let app_menu = Submenu::with_id_and_items(
        app,
        "workbench-app",
        app.package_info().name.clone(),
        true,
        &[
            &PredefinedMenuItem::about(app, None, None)?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app, "settings", "Settings…", true, Some("CmdOrCtrl+,"))?,
            &MenuItem::with_id(
                app,
                "show-workspace-in-finder",
                "Show Projects in Finder",
                true,
                None::<&str>,
            )?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::services(app, None)?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::hide(app, None)?,
            &PredefinedMenuItem::hide_others(app, None)?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::quit(app, None)?,
        ],
    )?;
    let file_menu = Submenu::with_id_and_items(
        app,
        "workbench-file",
        "File",
        true,
        &[
            &MenuItem::with_id(
                app,
                "new-scenario",
                "New Scenario",
                false,
                Some("CmdOrCtrl+N"),
            )?,
            &MenuItem::with_id(
                app,
                "new-file",
                "New File",
                false,
                Some("CmdOrCtrl+Shift+N"),
            )?,
            &MenuItem::with_id(
                app,
                "batch-change",
                "Batch Change",
                false,
                Some("CmdOrCtrl+Alt+B"),
            )?,
            &MenuItem::with_id(
                app,
                "save-file",
                "Save File Changes",
                false,
                Some("CmdOrCtrl+S"),
            )?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::close_window(app, None)?,
        ],
    )?;
    let edit_menu = Submenu::with_items(
        app,
        "Edit",
        true,
        &[
            &PredefinedMenuItem::undo(app, None)?,
            &PredefinedMenuItem::redo(app, None)?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::cut(app, None)?,
            &PredefinedMenuItem::copy(app, None)?,
            &PredefinedMenuItem::paste(app, None)?,
            &PredefinedMenuItem::select_all(app, None)?,
        ],
    )?;
    let view_menu = Submenu::with_id_and_items(
        app,
        "workbench-view",
        "View",
        true,
        &[
            &MenuItem::with_id(app, "view-explore", "Explore", true, Some("CmdOrCtrl+1"))?,
            &MenuItem::with_id(app, "view-create", "Create", true, Some("CmdOrCtrl+2"))?,
            &MenuItem::with_id(app, "view-run", "Run", true, Some("CmdOrCtrl+3"))?,
            &MenuItem::with_id(app, "view-compare", "Compare", true, Some("CmdOrCtrl+4"))?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app, "zoom-in", "Zoom In", true, Some("CmdOrCtrl+="))?,
            &MenuItem::with_id(app, "zoom-out", "Zoom Out", true, Some("CmdOrCtrl+-"))?,
            &MenuItem::with_id(app, "actual-size", "Actual Size", true, Some("CmdOrCtrl+0"))?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app, "map-zoom-in", "Map Zoom In", false, None::<&str>)?,
            &MenuItem::with_id(app, "map-zoom-out", "Map Zoom Out", false, None::<&str>)?,
            &MenuItem::with_id(app, "map-fit-mpo", "Fit MPO", false, None::<&str>)?,
            &MenuItem::with_id(app, "map-virginia", "Virginia Extent", false, None::<&str>)?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app, "refresh", "Refresh", true, Some("CmdOrCtrl+R"))?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::fullscreen(app, None)?,
        ],
    )?;
    let run_menu = Submenu::with_id_and_items(
        app,
        "workbench-run",
        "Run",
        true,
        &[
            &MenuItem::with_id(
                app,
                "run-selected",
                "Review / Run Selected…",
                false,
                Some("CmdOrCtrl+Shift+R"),
            )?,
            &MenuItem::with_id(
                app,
                "stop-selected-run",
                "Stop Selected Run",
                false,
                Some("CmdOrCtrl+."),
            )?,
            &MenuItem::with_id(app, "stop-all-runs", "Stop All Runs", false, None::<&str>)?,
        ],
    )?;
    let dependency_exports = Submenu::with_id_and_items(
        app,
        "export-dependency",
        "Dependency View",
        true,
        &[
            &MenuItem::with_id(app, "export-dependency-svg", "SVG", false, None::<&str>)?,
            &MenuItem::with_id(app, "export-dependency-pdf", "PDF", false, None::<&str>)?,
            &MenuItem::with_id(app, "export-dependency-html", "HTML", false, None::<&str>)?,
        ],
    )?;
    let current_exports = Submenu::with_id_and_items(
        app,
        "export-current",
        "Current View",
        true,
        &[
            &MenuItem::with_id(app, "export-current-csv", "CSV", false, None::<&str>)?,
            &MenuItem::with_id(app, "export-current-xlsx", "Excel", false, None::<&str>)?,
        ],
    )?;
    let all_changed_exports = Submenu::with_id_and_items(
        app,
        "export-all-changed",
        "All Locations Changed Outputs",
        true,
        &[
            &MenuItem::with_id(app, "export-all-changed-csv", "CSV", false, None::<&str>)?,
            &MenuItem::with_id(app, "export-all-changed-xlsx", "Excel", false, None::<&str>)?,
        ],
    )?;
    let selected_changed_export = MenuItem::with_id(
        app,
        "export-selected-changed",
        "Selected Locations Changed Outputs…",
        false,
        None::<&str>,
    )?;
    let full_variables_export = MenuItem::with_id(
        app,
        "export-full-variables",
        "Full Variable Data…",
        false,
        None::<&str>,
    )?;
    let dashboard_exports = Submenu::with_id_and_items(
        app,
        "export-dashboard",
        "Percent-Change Chart",
        true,
        &[
            &MenuItem::with_id(app, "export-dashboard-pdf", "PDF", false, None::<&str>)?,
            &MenuItem::with_id(app, "export-dashboard-csv", "CSV", false, None::<&str>)?,
            &MenuItem::with_id(app, "export-dashboard-xlsx", "Excel", false, None::<&str>)?,
        ],
    )?;
    let comparison_map_exports = Submenu::with_id_and_items(
        app,
        "export-comparison-map",
        "Comparison Map",
        true,
        &[
            &MenuItem::with_id(app, "export-map-pdf", "PDF", false, None::<&str>)?,
            &MenuItem::with_id(app, "export-map-png", "PNG", false, None::<&str>)?,
            &MenuItem::with_id(app, "export-map-svg", "SVG", false, None::<&str>)?,
            &MenuItem::with_id(app, "export-map-csv", "CSV", false, None::<&str>)?,
            &MenuItem::with_id(app, "export-map-xlsx", "Excel", false, None::<&str>)?,
        ],
    )?;
    let export_menu = Submenu::with_id_and_items(
        app,
        "workbench-export",
        "Export",
        true,
        &[
            &dependency_exports,
            &current_exports,
            &all_changed_exports,
            &selected_changed_export,
            &full_variables_export,
            &comparison_map_exports,
            &dashboard_exports,
        ],
    )?;
    let window_menu = Submenu::with_items(
        app,
        "Window",
        true,
        &[
            &PredefinedMenuItem::minimize(app, None)?,
            &PredefinedMenuItem::maximize(app, None)?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::close_window(app, None)?,
        ],
    )?;
    let help_menu = Submenu::with_id_and_items(
        app,
        "workbench-help",
        "Help",
        true,
        &[
            &MenuItem::with_id(
                app,
                "user-guide",
                "VisionEval Workbench User Guide",
                true,
                None::<&str>,
            )?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(
                app,
                "keyboard-shortcuts",
                "Keyboard Shortcuts",
                true,
                None::<&str>,
            )?,
            &MenuItem::with_id(
                app,
                "runtime-setup-guide",
                "Runtime Setup Guide",
                true,
                None::<&str>,
            )?,
        ],
    )?;
    Menu::with_items(
        app,
        &[
            &app_menu,
            &file_menu,
            &edit_menu,
            &view_menu,
            &run_menu,
            &export_menu,
            &window_menu,
            &help_menu,
        ],
    )
}

fn set_nested_menu_item_enabled(
    app: &AppHandle,
    submenu_id: &str,
    group_id: &str,
    item_id: &str,
    enabled: bool,
) -> Result<(), String> {
    let menu = app.menu().ok_or("Workbench menu is unavailable")?;
    let submenu = menu
        .get(submenu_id)
        .and_then(|item| item.as_submenu().cloned())
        .ok_or_else(|| format!("Menu {submenu_id} is unavailable"))?;
    let group = submenu
        .get(group_id)
        .and_then(|item| item.as_submenu().cloned())
        .ok_or_else(|| format!("Menu group {group_id} is unavailable"))?;
    let item = group
        .get(item_id)
        .and_then(|item| item.as_menuitem().cloned())
        .ok_or_else(|| format!("Menu item {item_id} is unavailable"))?;
    item.set_enabled(enabled).map_err(|error| error.to_string())
}

fn set_menu_item_enabled(
    app: &AppHandle,
    submenu_id: &str,
    item_id: &str,
    enabled: bool,
) -> Result<(), String> {
    let menu = app.menu().ok_or("Workbench menu is unavailable")?;
    let submenu = menu
        .get(submenu_id)
        .and_then(|item| item.as_submenu().cloned())
        .ok_or_else(|| format!("Menu {submenu_id} is unavailable"))?;
    let item = submenu
        .get(item_id)
        .and_then(|item| item.as_menuitem().cloned())
        .ok_or_else(|| format!("Menu item {item_id} is unavailable"))?;
    item.set_enabled(enabled).map_err(|error| error.to_string())
}

#[tauri::command]
fn set_menu_context(app: AppHandle, context: MenuContext) -> Result<(), String> {
    set_menu_item_enabled(&app, "workbench-file", "new-scenario", context.has_project)?;
    set_menu_item_enabled(
        &app,
        "workbench-file",
        "new-file",
        context.has_project && context.has_scenario,
    )?;
    set_menu_item_enabled(
        &app,
        "workbench-file",
        "batch-change",
        context.has_project && context.has_scenario,
    )?;
    set_menu_item_enabled(
        &app,
        "workbench-file",
        "save-file",
        context.has_file && context.file_dirty,
    )?;
    set_menu_item_enabled(&app, "workbench-run", "run-selected", context.can_run)?;
    set_menu_item_enabled(
        &app,
        "workbench-run",
        "stop-selected-run",
        !context.active_job_id.is_empty(),
    )?;
    set_menu_item_enabled(
        &app,
        "workbench-run",
        "stop-all-runs",
        context.has_runnable_jobs,
    )?;
    for item in ["map-zoom-in", "map-zoom-out", "map-virginia"] {
        set_menu_item_enabled(&app, "workbench-view", item, context.has_active_map)?;
    }
    set_menu_item_enabled(
        &app,
        "workbench-view",
        "map-fit-mpo",
        context.has_active_map && context.map_has_mpo_focus,
    )?;
    for item in [
        "export-dependency-svg",
        "export-dependency-pdf",
        "export-dependency-html",
    ] {
        set_nested_menu_item_enabled(
            &app,
            "workbench-export",
            "export-dependency",
            item,
            context.has_dependency_export,
        )?;
    }
    for item in ["export-current-csv", "export-current-xlsx"] {
        set_nested_menu_item_enabled(
            &app,
            "workbench-export",
            "export-current",
            item,
            context.has_comparison_export,
        )?;
    }
    for item in ["export-all-changed-csv", "export-all-changed-xlsx"] {
        set_nested_menu_item_enabled(
            &app,
            "workbench-export",
            "export-all-changed",
            item,
            context.has_change_export,
        )?;
    }
    set_menu_item_enabled(
        &app,
        "workbench-export",
        "export-selected-changed",
        context.has_change_export,
    )?;
    set_menu_item_enabled(
        &app,
        "workbench-export",
        "export-full-variables",
        context.has_change_export,
    )?;
    for item in [
        "export-dashboard-pdf",
        "export-dashboard-csv",
        "export-dashboard-xlsx",
    ] {
        set_nested_menu_item_enabled(
            &app,
            "workbench-export",
            "export-dashboard",
            item,
            context.has_dashboard_export,
        )?;
    }
    for item in [
        "export-map-pdf",
        "export-map-png",
        "export-map-svg",
        "export-map-csv",
        "export-map-xlsx",
    ] {
        set_nested_menu_item_enabled(
            &app,
            "workbench-export",
            "export-comparison-map",
            item,
            context.has_map_export,
        )?;
    }
    Ok(())
}

#[tauri::command]
fn set_app_zoom(app: AppHandle, scale: f64) -> Result<(), String> {
    let window = app
        .get_webview_window("main")
        .ok_or_else(|| "Workbench window is unavailable".to_string())?;
    window
        .set_zoom(scale.clamp(0.8, 2.0))
        .map_err(|error| error.to_string())
}

fn config_path(app: &AppHandle) -> Result<PathBuf, String> {
    let directory = app
        .path()
        .app_config_dir()
        .map_err(|error| error.to_string())?;
    fs::create_dir_all(&directory).map_err(|error| error.to_string())?;
    Ok(directory.join("desktop-config.json"))
}
fn migrate_runtime_profiles(config: &mut DesktopConfig) -> bool {
    let active_profile_id = config.active_runtime_profile_id.clone();
    let mut changed = false;
    #[cfg(target_os = "windows")]
    let supported_adapter = "native";
    #[cfg(not(target_os = "windows"))]
    let supported_adapter = "docker";
    let disabled_message =
        "Runtime setup has changed. Verify the supported runtime before running models.";
    for profile in &mut config.runtime_profiles {
        let invalid_windows_native = cfg!(target_os = "windows")
            && profile.adapter == "native"
            && (profile.ve_runtime_path.is_empty()
                || profile.ve_home_path.is_empty()
                || profile.image_reference.contains("\\.tools\\")
                || profile.image_reference.contains("/.tools/"));
        if profile.adapter != supported_adapter
            || config.configuration_version < CONFIG_VERSION
            || invalid_windows_native
        {
            profile.image_digest.clear();
            profile.verified = false;
            profile.verified_at.clear();
            profile.verification_message = disabled_message.into();
            changed = true;
        }
    }
    if config.runtime_profiles.iter().any(|profile| {
        profile.id == active_profile_id
            && (profile.adapter != supported_adapter
                || !profile.verified
                || (cfg!(target_os = "windows")
                    && (profile.ve_runtime_path.is_empty() || profile.ve_home_path.is_empty())))
    }) {
        config.active_runtime_profile_id.clear();
        changed = true;
    }
    changed
}
fn read_config(app: &AppHandle) -> DesktopConfig {
    let mut config: DesktopConfig = config_path(app)
        .ok()
        .and_then(|path| fs::read_to_string(path).ok())
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_default();
    let mut changed = false;
    if config.configuration_version < 4 {
        config.auto_start_docker = true;
        changed = true;
    }
    changed |= migrate_runtime_profiles(&mut config);
    #[cfg(target_os = "windows")]
    {
        config.resources.default_run_mode = "queued".into();
        config.resources.max_concurrent_runs = 1;
        config.resources.memory_limit_gb = None;
        config.auto_start_docker = false;
    }
    for profile in &mut config.runtime_profiles {
        if profile.adapter != "docker" {
            continue;
        }
        if matches!(
            profile.image_reference.as_str(),
            LEGACY_RUNTIME_IMAGE | UNPATCHED_RC6_RUNTIME_IMAGE | V1_RUNTIME_IMAGE
        ) {
            profile.image_reference = default_runtime_image().into();
            profile.image_digest.clear();
            profile.runtime_version = "Compatible VisionEval runtime / R 4.5.1".into();
            profile.verified = false;
            profile.verified_at.clear();
            profile.verification_message =
                "Verify the VisionEval runtime before running models.".into();
            changed = true;
        }
    }
    if config.configuration_version != CONFIG_VERSION {
        changed = true;
    }
    config.configuration_version = CONFIG_VERSION;
    if !matches!(config.theme.as_str(), "system" | "light" | "dark") {
        config.theme = default_appearance();
        changed = true;
    }
    #[cfg(not(target_os = "windows"))]
    if config.resources.max_concurrent_runs != 2 {
        config.resources.max_concurrent_runs = 2;
        changed = true;
    }
    if changed {
        let _ = write_config(app, &config);
    }
    config
}
fn write_config(app: &AppHandle, config: &DesktopConfig) -> Result<(), String> {
    let path = config_path(app)?;
    let temporary = path.with_extension("json.tmp");
    fs::write(
        &temporary,
        serde_json::to_string_pretty(config).map_err(|error| error.to_string())?,
    )
    .map_err(|error| error.to_string())?;
    fs::rename(&temporary, &path).map_err(|error| error.to_string())
}

fn is_legacy_workspace(path: &Path) -> bool {
    let expected = [
        "Projects",
        "models",
        "runs",
        "InputLibrary",
        "ModelTemplates",
        "datastore_catalog.json",
    ];
    expected
        .iter()
        .filter(|name| path.join(name).exists())
        .count()
        >= 2
}
fn workspace_status(path: &Path) -> Result<String, String> {
    if !path.exists() {
        return Err("The saved workspace folder is missing or unavailable.".into());
    }
    if !path.is_dir() {
        return Err("The selected workspace is not a folder.".into());
    }
    if path.join(WORKSPACE_MARKER).is_file() {
        return Ok("ready".into());
    }
    let mut entries =
        fs::read_dir(path).map_err(|error| format!("Could not read the workspace: {error}"))?;
    if entries.next().is_none() {
        return Ok("empty".into());
    }
    if is_legacy_workspace(path) {
        return Ok("legacy".into());
    }
    Err("This nonempty folder is not a recognizable VisionEval Workbench workspace.".into())
}
fn read_workspace_id(path: &Path) -> String {
    fs::read_to_string(path.join(WORKSPACE_MARKER))
        .ok()
        .and_then(|text| serde_json::from_str::<Value>(&text).ok())
        .and_then(|v| v.get("id").and_then(Value::as_str).map(str::to_owned))
        .unwrap_or_default()
}
fn initialize_workspace(path: &Path) -> Result<String, String> {
    fs::create_dir_all(path).map_err(|error| format!("Could not create workspace: {error}"))?;
    workspace_status(path)?;
    let mut id = read_workspace_id(path);
    if id.is_empty() {
        id = stable_id("workspace");
        let marker = serde_json::json!({"formatVersion": WORKSPACE_FORMAT_VERSION, "id": id, "createdAt": now_string()});
        fs::write(
            path.join(WORKSPACE_MARKER),
            serde_json::to_string_pretty(&marker).unwrap(),
        )
        .map_err(|error| error.to_string())?;
    }
    let settings = path.join(WORKSPACE_SETTINGS);
    if !settings.exists() {
        if let Some(parent) = settings.parent() {
            fs::create_dir_all(parent).map_err(|error| error.to_string())?;
        }
        fs::write(
            settings,
            serde_json::to_string_pretty(&WorkspaceSettings::default()).unwrap(),
        )
        .map_err(|error| error.to_string())?;
    }
    for name in [
        "Assets/InputLibraries",
        "Assets/ModelTemplates",
        "Assets/InputExplanations",
        "Assets/RegionalData",
        "Projects",
        "Results/Models",
        "Documentation/User Notes",
        ".workbench/runs",
        ".workbench/exchange/inbox",
        ".workbench/exchange/outbox",
        ".workbench/exchange/system",
        ".workbench/archive/assets",
        ".workbench/archive/projects",
    ] {
        fs::create_dir_all(path.join(name)).map_err(|error| error.to_string())?;
    }
    if !path.join(".workbench/datastore_catalog.json").exists() {
        fs::write(
            path.join(".workbench/datastore_catalog.json"),
            "{\n  \"version\": 1,\n  \"datastores\": []\n}\n",
        )
        .map_err(|error| error.to_string())?;
    }
    Ok(id)
}
fn remember_workspace(config: &mut DesktopConfig, path: &Path, id: &str) {
    let path_text = path.to_string_lossy().to_string();
    let name = path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("VisionEval Workspace")
        .to_string();
    config
        .recent_workspaces
        .retain(|item| item.path != path_text && item.id != id);
    config.recent_workspaces.insert(
        0,
        RecentWorkspace {
            id: id.into(),
            name,
            path: path_text.clone(),
            last_opened_at: now_string(),
        },
    );
    config.recent_workspaces.truncate(8);
    config.workspace_root = path_text;
    config.workspace_id = id.into();
}

fn workspace_is_safe_to_trash(path: &Path) -> bool {
    let Ok(candidate) = path.canonicalize() else {
        return false;
    };
    let home = home_dir().canonicalize().unwrap_or_else(|_| home_dir());
    candidate != home && candidate.parent().is_some() && candidate != Path::new("/")
}

fn recent_workspace_state(item: &RecentWorkspace, config: &DesktopConfig) -> RecentWorkspaceState {
    let path = PathBuf::from(&item.path);
    let exists = path.exists();
    let current = item.path == config.workspace_root
        || (!item.id.is_empty() && item.id == config.workspace_id);
    let marker_id = if exists {
        read_workspace_id(&path)
    } else {
        String::new()
    };
    let valid =
        exists && !item.id.is_empty() && marker_id == item.id && workspace_status(&path).is_ok();
    let removable = valid && !current && workspace_is_safe_to_trash(&path);
    let status = if current {
        "Current workspace"
    } else if !exists {
        "Folder not found"
    } else if !valid {
        "Workspace identity could not be verified"
    } else {
        "Ready"
    };
    RecentWorkspaceState {
        id: item.id.clone(),
        name: item.name.clone(),
        path: item.path.clone(),
        display_path: display_workspace_path(&path),
        last_opened_at: item.last_opened_at.clone(),
        exists,
        valid,
        current,
        removable,
        status: status.into(),
    }
}

#[tauri::command]
fn desktop_state(app: AppHandle) -> DesktopState {
    let mut config = read_config(&app);
    if config.notifications_enabled && !config.notification_registration_sent {
        let registration = app
            .notification()
            .builder()
            .title("VisionEval Workbench notifications enabled")
            .body("Workbench will alert you when runs and long-running comparisons finish or fail.")
            .show();
        if registration.is_ok() {
            config.notification_registration_sent = true;
            let _ = write_config(&app, &config);
        }
    }
    let configured = !config.workspace_root.trim().is_empty();
    let status = if configured {
        workspace_status(Path::new(&config.workspace_root))
    } else {
        Err("No workspace has been selected.".into())
    };
    let blocking_job_count = if configured && status.is_ok() {
        nonterminal_job_count(Path::new(&config.workspace_root))
    } else {
        0
    };
    let recommended = recommended_workspace_root();
    let recent_workspaces = config
        .recent_workspaces
        .iter()
        .map(|item| recent_workspace_state(item, &config))
        .collect();
    DesktopState {
        platform: if cfg!(target_os = "macos") {
            "macos".into()
        } else if cfg!(target_os = "windows") {
            "windows".into()
        } else {
            "linux".into()
        },
        configuration_version: config.configuration_version,
        onboarding_version: config.onboarding_version,
        configured,
        workspace_valid: status.is_ok(),
        workspace_status: status.unwrap_or_else(|error| error),
        workspace_display_path: display_workspace_path(Path::new(&config.workspace_root)),
        workspace_root: config.workspace_root,
        workspace_id: config.workspace_id,
        recommended_workspace_root: recommended.to_string_lossy().to_string(),
        recommended_workspace_display_path: display_workspace_path(&recommended),
        recent_workspaces,
        theme: config.theme,
        runtime_profiles: config.runtime_profiles,
        active_runtime_profile_id: config.active_runtime_profile_id,
        resources: config.resources,
        notifications_enabled: config.notifications_enabled,
        notification_success_threshold_seconds: config.notification_success_threshold_seconds,
        comparison_palettes: config.comparison_palettes.clone(),
        master_comparison_palette: config.master_comparison_palette.clone(),
        use_master_comparison_palette: config.use_master_comparison_palette,
        auto_start_docker: config.auto_start_docker,
        migration_recovery: config.migration_recovery,
        blocking_job_count,
    }
}

fn select_workspace_path(app: &AppHandle, path: PathBuf) -> Result<String, String> {
    let id = initialize_workspace(&path)?;
    let mut config = read_config(app);
    remember_workspace(&mut config, &path, &id);
    write_config(app, &config)?;
    Ok(path.to_string_lossy().to_string())
}

fn create_workspace_path(app: &AppHandle, path: PathBuf) -> Result<String, String> {
    if path.exists() {
        let status = workspace_status(&path)?;
        match status.as_str() {
            "empty" => {}
            "ready" | "legacy" => return Err(
                "A Workbench workspace already exists there. Use Open existing workspace instead."
                    .into(),
            ),
            _ => {
                return Err("The selected destination is not available for a new workspace.".into())
            }
        }
    }
    select_workspace_path(app, path)
}

fn select_existing_workspace_path(app: &AppHandle, path: PathBuf) -> Result<String, String> {
    if workspace_status(&path)? == "empty" {
        return Err("The selected folder is empty. Create a workspace there instead.".into());
    }
    select_workspace_path(app, path)
}

#[tauri::command]
fn create_workspace(app: AppHandle, path: String) -> Result<String, String> {
    create_workspace_path(&app, PathBuf::from(path))
}

#[tauri::command]
fn create_recommended_workspace(app: AppHandle) -> Result<String, String> {
    create_workspace_path(&app, recommended_workspace_root())
}

#[tauri::command]
async fn choose_workspace(app: AppHandle) -> Result<Option<String>, String> {
    let (sender, receiver) = std::sync::mpsc::channel();
    app.dialog().file().pick_folder(move |path| {
        let _ = sender.send(path);
    });
    let Some(path) = receiver.recv().map_err(|error| error.to_string())? else {
        return Ok(None);
    };
    select_existing_workspace_path(&app, PathBuf::from(path.to_string())).map(Some)
}

#[tauri::command]
async fn choose_workspace_destination(app: AppHandle) -> Result<Option<String>, String> {
    let (sender, receiver) = std::sync::mpsc::channel();
    app.dialog().file().pick_folder(move |path| {
        let _ = sender.send(path);
    });
    Ok(receiver
        .recv()
        .map_err(|error| error.to_string())?
        .map(|path| {
            PathBuf::from(path.to_string())
                .join("VisionEval Workbench Workspace")
                .to_string_lossy()
                .to_string()
        }))
}

#[tauri::command]
async fn choose_workspace_parent(app: AppHandle) -> Result<Option<String>, String> {
    let (sender, receiver) = std::sync::mpsc::channel();
    app.dialog().file().pick_folder(move |path| {
        let _ = sender.send(path);
    });
    let Some(path) = receiver.recv().map_err(|error| error.to_string())? else {
        return Ok(None);
    };
    let destination = PathBuf::from(path.to_string()).join("VisionEval Workbench Workspace");
    create_workspace_path(&app, destination).map(Some)
}

#[tauri::command]
async fn choose_folder(app: AppHandle) -> Result<Option<String>, String> {
    let (sender, receiver) = std::sync::mpsc::channel();
    app.dialog().file().pick_folder(move |path| {
        let _ = sender.send(path);
    });
    Ok(receiver
        .recv()
        .map_err(|error| error.to_string())?
        .map(|path| path.to_string()))
}

#[tauri::command]
async fn choose_package(app: AppHandle) -> Result<Option<String>, String> {
    let (sender, receiver) = std::sync::mpsc::channel();
    app.dialog()
        .file()
        .add_filter("Workbench package", &["zip"])
        .pick_file(move |path| {
            let _ = sender.send(path);
        });
    Ok(receiver
        .recv()
        .map_err(|error| error.to_string())?
        .map(|path| path.to_string()))
}

#[tauri::command]
async fn choose_package_folder(app: AppHandle) -> Result<Option<String>, String> {
    let (sender, receiver) = std::sync::mpsc::channel();
    app.dialog().file().pick_folder(move |path| {
        let _ = sender.send(path);
    });
    Ok(receiver
        .recv()
        .map_err(|error| error.to_string())?
        .map(|path| path.to_string()))
}

#[tauri::command]
async fn choose_rscript(app: AppHandle) -> Result<Option<String>, String> {
    let (sender, receiver) = std::sync::mpsc::channel();
    app.dialog()
        .file()
        .add_filter("Rscript executable", &["exe"])
        .pick_file(move |path| {
            let _ = sender.send(path);
        });
    Ok(receiver
        .recv()
        .map_err(|error| error.to_string())?
        .map(|path| path.to_string()))
}

fn valid_export_operation_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 120
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'-')
}

fn url_component(value: &str) -> String {
    let mut output = String::new();
    for byte in value.bytes() {
        if byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b'.' | b'~') {
            output.push(byte as char);
        } else {
            output.push_str(&format!("%{byte:02X}"));
        }
    }
    output
}

fn dependency_export_filename(format: &str, focus_id: &str, scope: &str, view: &str) -> String {
    let stamp = Command::new("date")
        .arg("+%Y-%m-%d %H.%M.%S")
        .output()
        .ok()
        .and_then(|output| String::from_utf8(output.stdout).ok())
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(now_string);
    let _ = (focus_id, scope, view);
    format!("VE dependency {stamp}.{format}")
}

#[tauri::command]
async fn save_dependency_export(
    app: AppHandle,
    format: String,
    template_id: String,
    focus_id: String,
    scope: String,
    origin_id: String,
    view: String,
) -> Result<Option<String>, String> {
    let format = format.to_ascii_lowercase();
    if format != "svg" && format != "pdf" && format != "html" {
        return Err("Dependency export format must be svg, pdf, or html".into());
    }
    if template_id.trim().is_empty() {
        return Err("Choose a model template before exporting dependencies".into());
    }
    let suggested = dependency_export_filename(&format, &focus_id, &scope, &view);
    let downloads = app
        .path()
        .download_dir()
        .unwrap_or_else(|_| home_dir().join("Downloads"));
    let filter_name = match format.as_str() {
        "pdf" => "PDF",
        "html" => "HTML",
        _ => "SVG",
    };
    let extension = format.clone();
    let app_for_dialog = app.clone();
    let destination = tauri::async_runtime::spawn_blocking(move || {
        app_for_dialog
            .dialog()
            .file()
            .add_filter(filter_name, &[extension.as_str()])
            .set_directory(downloads)
            .set_file_name(suggested)
            .blocking_save_file()
    })
    .await
    .map_err(|error| format!("Could not open the Save dialog: {error}"))?;
    let Some(destination) = destination else {
        return Ok(None);
    };
    let destination = destination
        .into_path()
        .map_err(|error| format!("Could not use the selected export location: {error}"))?;
    let port = app
        .state::<BackendState>()
        .port
        .lock()
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Workbench backend is not running".to_string())?;
    let mut query = format!("templateId={}", url_component(&template_id));
    if !focus_id.is_empty() {
        query.push_str(&format!("&focusId={}", url_component(&focus_id)));
    }
    if !scope.is_empty() {
        query.push_str(&format!("&scope={}", url_component(&scope)));
    }
    if !origin_id.is_empty() {
        query.push_str(&format!("&originId={}", url_component(&origin_id)));
    }
    if !view.is_empty() {
        query.push_str(&format!("&view={}", url_component(&view)));
    }
    let url = format!("http://127.0.0.1:{port}/api/dependencies/export.{format}?{query}");
    let saved_path = destination.clone();
    tauri::async_runtime::spawn_blocking(move || -> Result<(), String> {
        let response = ureq::get(&url)
            .call()
            .map_err(|error| format!("Could not retrieve the dependency export: {error}"))?;
        let mut bytes = Vec::new();
        response
            .into_reader()
            .read_to_end(&mut bytes)
            .map_err(|error| format!("Could not read the dependency export: {error}"))?;
        fs::write(&saved_path, bytes)
            .map_err(|error| format!("Could not save the dependency export: {error}"))
    })
    .await
    .map_err(|error| format!("Dependency export save task failed: {error}"))??;
    Ok(Some(destination.to_string_lossy().to_string()))
}

fn backend_export_spec(export_kind: &str) -> Option<(&'static str, &'static str, &'static str)> {
    match export_kind {
        "comparison-current-csv" => Some(("/api/comparison/export-current", "csv", "CSV")),
        "comparison-changed-csv" => Some(("/api/comparison/export-filtered-changes", "csv", "CSV")),
        "comparison-scan-csv" => Some(("/api/comparison/export-change-summary", "csv", "CSV")),
        "comparison-map-csv" => Some(("/api/comparison/export-map-csv", "csv", "CSV")),
        "diagnostics-run" => Some(("/api/diagnostics/run", "zip", "ZIP archive")),
        "dashboard-pdf" => Some(("/api/comparison/export-dashboard-pdf", "pdf", "PDF")),
        "dashboard-csv" => Some(("/api/comparison/export-dashboard-csv", "csv", "CSV")),
        _ => None,
    }
}

#[tauri::command]
async fn save_backend_export(
    app: AppHandle,
    export_kind: String,
    query: String,
    filename: String,
) -> Result<Option<String>, String> {
    let (route, extension, filter_name) = backend_export_spec(&export_kind)
        .ok_or_else(|| "Unsupported Workbench export kind".to_string())?;
    if query.len() > 16_384
        || query
            .bytes()
            .any(|byte| byte.is_ascii_control() || byte == b'#')
    {
        return Err("Invalid Workbench export query".into());
    }
    let filename_path = Path::new(&filename);
    let valid_filename = filename_path.components().count() == 1
        && filename_path
            .extension()
            .and_then(|value| value.to_str())
            .is_some_and(|value| value.eq_ignore_ascii_case(extension));
    if !valid_filename {
        return Err("Invalid Workbench export filename".into());
    }
    let downloads = app
        .path()
        .download_dir()
        .unwrap_or_else(|_| home_dir().join("Downloads"));
    let app_for_dialog = app.clone();
    let extension_owned = extension.to_string();
    let destination = tauri::async_runtime::spawn_blocking(move || {
        app_for_dialog
            .dialog()
            .file()
            .add_filter(filter_name, &[extension_owned.as_str()])
            .set_directory(downloads)
            .set_file_name(filename)
            .blocking_save_file()
    })
    .await
    .map_err(|error| format!("Could not open the Save dialog: {error}"))?;
    let Some(destination) = destination else {
        return Ok(None);
    };
    let destination = destination
        .into_path()
        .map_err(|error| format!("Could not use the selected export location: {error}"))?;
    let port = app
        .state::<BackendState>()
        .port
        .lock()
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Workbench backend is not running".to_string())?;
    let separator = if query.is_empty() { "" } else { "?" };
    let url = format!("http://127.0.0.1:{port}{route}{separator}{query}");
    let saved_path = destination.clone();
    tauri::async_runtime::spawn_blocking(move || -> Result<(), String> {
        let response = ureq::get(&url)
            .call()
            .map_err(|error| format!("Could not retrieve the Workbench export: {error}"))?;
        let mut bytes = Vec::new();
        response
            .into_reader()
            .read_to_end(&mut bytes)
            .map_err(|error| format!("Could not read the Workbench export: {error}"))?;
        fs::write(&saved_path, bytes)
            .map_err(|error| format!("Could not save the Workbench export: {error}"))
    })
    .await
    .map_err(|error| format!("Workbench export save task failed: {error}"))??;
    Ok(Some(destination.to_string_lossy().to_string()))
}

fn jpeg_pdf(jpeg: &[u8], width: u32, height: u32) -> Vec<u8> {
    let page_width = 792.0_f64;
    let page_height = page_width * f64::from(height.max(1)) / f64::from(width.max(1));
    let content = format!("q {page_width:.2} 0 0 {page_height:.2} 0 0 cm /Im0 Do Q\n");
    let objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>".to_vec(),
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>".to_vec(),
        format!("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width:.2} {page_height:.2}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>").into_bytes(),
        {
            let mut object = format!("<< /Type /XObject /Subtype /Image /Width {} /Height {} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {} >>\nstream\n", width, height, jpeg.len()).into_bytes();
            object.extend_from_slice(jpeg); object.extend_from_slice(b"\nendstream"); object
        },
        {
            let mut object = format!("<< /Length {} >>\nstream\n", content.len()).into_bytes();
            object.extend_from_slice(content.as_bytes()); object.extend_from_slice(b"endstream"); object
        },
    ];
    let mut output = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n".to_vec();
    let mut offsets = vec![0_usize];
    for (index, object) in objects.iter().enumerate() {
        offsets.push(output.len());
        output.extend_from_slice(format!("{} 0 obj\n", index + 1).as_bytes());
        output.extend_from_slice(object);
        output.extend_from_slice(b"\nendobj\n");
    }
    let xref = output.len();
    output.extend_from_slice(
        format!("xref\n0 {}\n0000000000 65535 f \n", objects.len() + 1).as_bytes(),
    );
    for offset in offsets.iter().skip(1) {
        output.extend_from_slice(format!("{offset:010} 00000 n \n").as_bytes());
    }
    output.extend_from_slice(
        format!(
            "trailer\n<< /Size {} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n",
            objects.len() + 1
        )
        .as_bytes(),
    );
    output
}

#[tauri::command]
async fn save_visual_export(
    app: AppHandle,
    format: String,
    content: String,
    filename: String,
    width: u32,
    height: u32,
) -> Result<Option<String>, String> {
    let (filter_name, extension) = match format.as_str() {
        "svg" => ("SVG", "svg"),
        "png" => ("PNG", "png"),
        "pdf" => ("PDF", "pdf"),
        _ => return Err("Unsupported visual export format".into()),
    };
    if content.len() > 80_000_000 || width == 0 || height == 0 || width > 10_000 || height > 10_000
    {
        return Err("Visual export is invalid or too large".into());
    }
    let filename_path = Path::new(&filename);
    if filename_path.components().count() != 1
        || !filename_path
            .extension()
            .and_then(|value| value.to_str())
            .is_some_and(|value| value.eq_ignore_ascii_case(extension))
    {
        return Err("Invalid visual export filename".into());
    }
    let bytes = if format == "svg" {
        content.into_bytes()
    } else {
        let encoded = content
            .split_once(',')
            .map(|(_, value)| value)
            .ok_or("Invalid image data")?;
        let image = BASE64
            .decode(encoded)
            .map_err(|error| format!("Could not decode image data: {error}"))?;
        if format == "pdf" {
            jpeg_pdf(&image, width, height)
        } else {
            image
        }
    };
    let downloads = app
        .path()
        .download_dir()
        .unwrap_or_else(|_| home_dir().join("Downloads"));
    let app_for_dialog = app.clone();
    let destination = tauri::async_runtime::spawn_blocking(move || {
        app_for_dialog
            .dialog()
            .file()
            .add_filter(filter_name, &[extension])
            .set_directory(downloads)
            .set_file_name(filename)
            .blocking_save_file()
    })
    .await
    .map_err(|error| format!("Could not open the Save dialog: {error}"))?;
    let Some(destination) = destination else {
        return Ok(None);
    };
    let destination = destination
        .into_path()
        .map_err(|error| format!("Could not use the selected export location: {error}"))?;
    fs::write(&destination, bytes)
        .map_err(|error| format!("Could not save the visual export: {error}"))?;
    Ok(Some(destination.to_string_lossy().to_string()))
}

#[tauri::command]
async fn save_comparison_export(
    app: AppHandle,
    operation_id: String,
    filename: String,
) -> Result<Option<String>, String> {
    if !valid_export_operation_id(&operation_id) {
        return Err("Invalid comparison export identifier".into());
    }
    let lower_filename = filename.to_ascii_lowercase();
    let (suggested, filter_name, extensions) = if lower_filename.ends_with(".zip") {
        (filename, "ZIP Archive", vec!["zip"])
    } else if lower_filename.ends_with(".xlsx") {
        (filename, "Excel Workbook", vec!["xlsx"])
    } else {
        return Err("Comparison export filename must end in .xlsx or .zip".into());
    };
    let app_for_dialog = app.clone();
    let destination = tauri::async_runtime::spawn_blocking(move || {
        app_for_dialog
            .dialog()
            .file()
            .add_filter(filter_name, &extensions)
            .set_file_name(suggested)
            .blocking_save_file()
    })
    .await
    .map_err(|error| format!("Could not open the Save dialog: {error}"))?;
    let Some(destination) = destination else {
        return Ok(None);
    };
    let destination = destination
        .into_path()
        .map_err(|error| format!("Could not use the selected export location: {error}"))?;
    let port = app
        .state::<BackendState>()
        .port
        .lock()
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "Workbench backend is not running".to_string())?;
    let url = format!("http://127.0.0.1:{port}/api/comparison/exports/download?id={operation_id}");
    let saved_path = destination.clone();
    tauri::async_runtime::spawn_blocking(move || -> Result<(), String> {
        let response = ureq::get(&url)
            .call()
            .map_err(|error| format!("Could not retrieve the completed export: {error}"))?;
        let mut bytes = Vec::new();
        response
            .into_reader()
            .read_to_end(&mut bytes)
            .map_err(|error| format!("Could not read the completed export: {error}"))?;
        fs::write(&saved_path, bytes).map_err(|error| format!("Could not save the export: {error}"))
    })
    .await
    .map_err(|error| format!("Export save task failed: {error}"))??;
    Ok(Some(destination.to_string_lossy().to_string()))
}

fn has_nonterminal_jobs(root: &Path) -> bool {
    nonterminal_job_count(root) > 0
}

fn nonterminal_job_count(root: &Path) -> usize {
    let managed = root.join(".workbench/runs");
    let runs = if managed.is_dir() {
        managed
    } else {
        root.join("runs")
    };
    let Ok(entries) = fs::read_dir(runs) else {
        return 0;
    };
    entries
        .flatten()
        .filter(|entry| {
            let path = entry.path().join("job.json");
            fs::read_to_string(path)
                .ok()
                .and_then(|text| serde_json::from_str::<Value>(&text).ok())
                .and_then(|job| {
                    job.get("state").and_then(Value::as_str).map(|state| {
                        matches!(
                            state,
                            "waiting" | "preparing" | "running" | "exporting" | "stopping"
                        )
                    })
                })
                .unwrap_or(false)
        })
        .count()
}

fn copy_directory(source: &Path, destination: &Path) -> io::Result<()> {
    fs::create_dir_all(destination)?;
    for entry in fs::read_dir(source)? {
        let entry = entry?;
        let source_path = entry.path();
        let destination_path = destination.join(entry.file_name());
        if entry.file_type()?.is_dir() {
            copy_directory(&source_path, &destination_path)?;
        } else {
            fs::copy(&source_path, &destination_path)?;
        }
    }
    Ok(())
}
fn tree_summary(root: &Path) -> io::Result<(u64, u64)> {
    let mut files = 0u64;
    let mut bytes = 0u64;
    for entry in fs::read_dir(root)? {
        let entry = entry?;
        if entry.file_type()?.is_dir() {
            let summary = tree_summary(&entry.path())?;
            files += summary.0;
            bytes += summary.1;
        } else {
            files += 1;
            bytes += entry.metadata()?.len();
        }
    }
    Ok((files, bytes))
}

#[tauri::command]
fn move_workspace(app: AppHandle, destination: String) -> Result<String, String> {
    let state = app.state::<BackendState>();
    let mut config = read_config(&app);
    let source = PathBuf::from(&config.workspace_root);
    let destination = PathBuf::from(destination);
    workspace_status(&source)?;
    if has_nonterminal_jobs(&source) {
        return Err(
            "Finish or remove all active and waiting jobs before moving the workspace.".into(),
        );
    }
    if source == destination {
        return Ok(config.workspace_root);
    }
    if destination.exists()
        && fs::read_dir(&destination)
            .map_err(|error| error.to_string())?
            .next()
            .is_some()
    {
        return Err("The destination folder is not empty.".into());
    }
    stop_backend(&state);
    config.migration_recovery = Some(MigrationRecovery {
        source_path: source.to_string_lossy().to_string(),
        destination_path: destination.to_string_lossy().to_string(),
        state: "moving".into(),
        updated_at: now_string(),
        message: "The original path remains recorded until the moved workspace is verified.".into(),
    });
    write_config(&app, &config)?;
    if destination.exists() {
        fs::remove_dir(&destination).map_err(|error| error.to_string())?;
    }
    if let Some(parent) = destination.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    if fs::rename(&source, &destination).is_err() {
        copy_directory(&source, &destination)
            .map_err(|error| format!("Could not copy workspace: {error}"))?;
        if tree_summary(&source).map_err(|error| error.to_string())?
            != tree_summary(&destination).map_err(|error| error.to_string())?
        {
            return Err(
                "Workspace copy verification failed; the original remains unchanged.".into(),
            );
        }
        fs::remove_dir_all(&source).map_err(|error| {
            format!("The copy was verified but the original could not be removed: {error}")
        })?;
    }
    workspace_status(&destination)?;
    let id = initialize_workspace(&destination)?;
    remember_workspace(&mut config, &destination, &id);
    if let Some(recovery) = config.migration_recovery.as_mut() {
        recovery.state = "verified".into();
        recovery.updated_at = now_string();
    }
    write_config(&app, &config)?;
    Ok(destination.to_string_lossy().to_string())
}

#[tauri::command]
fn switch_workspace(app: AppHandle, path: String) -> Result<String, String> {
    let state = app.state::<BackendState>();
    let config = read_config(&app);
    if !config.workspace_root.is_empty() && has_nonterminal_jobs(Path::new(&config.workspace_root))
    {
        return Err(
            "Finish or remove all active and waiting jobs before switching workspaces.".into(),
        );
    }
    stop_backend(&state);
    select_existing_workspace_path(&app, PathBuf::from(path))
}

#[tauri::command]
fn forget_workspace(app: AppHandle, id: String, path: String) -> Result<(), String> {
    let mut config = read_config(&app);
    if path == config.workspace_root || (!id.is_empty() && id == config.workspace_id) {
        return Err(
            "The current workspace cannot be forgotten. Open another workspace first.".into(),
        );
    }
    let previous = config.recent_workspaces.len();
    config
        .recent_workspaces
        .retain(|item| !(item.id == id && item.path == path));
    if config.recent_workspaces.len() == previous {
        return Err("That recent workspace is no longer recorded.".into());
    }
    write_config(&app, &config)
}

#[tauri::command]
fn trash_workspace(app: AppHandle, id: String, path: String) -> Result<(), String> {
    let mut config = read_config(&app);
    if path == config.workspace_root || (!id.is_empty() && id == config.workspace_id) {
        return Err(
            "The current workspace cannot be moved to Trash. Open another workspace first.".into(),
        );
    }
    let recorded = config
        .recent_workspaces
        .iter()
        .any(|item| item.id == id && item.path == path);
    if !recorded {
        return Err("That workspace is not in the recent-workspace list.".into());
    }
    let candidate = PathBuf::from(&path);
    let metadata = fs::symlink_metadata(&candidate).map_err(|_| {
        "The workspace folder is missing. Forget it from the recent list instead.".to_string()
    })?;
    if !metadata.is_dir() || metadata.file_type().is_symlink() {
        return Err("Only a verified Workbench workspace folder can be moved to Trash.".into());
    }
    workspace_status(&candidate)?;
    if id.is_empty() || read_workspace_id(&candidate) != id {
        return Err("The workspace identity could not be verified. No files were changed.".into());
    }
    if !workspace_is_safe_to_trash(&candidate) {
        return Err("Workbench refused to move that protected location to Trash.".into());
    }
    trash::delete(&candidate)
        .map_err(|error| format!("The workspace could not be moved to Trash: {error}"))?;
    config
        .recent_workspaces
        .retain(|item| !(item.id == id && item.path == path));
    write_config(&app, &config)
}

#[tauri::command]
fn reveal_workspace(app: AppHandle) -> Result<(), String> {
    let config = read_config(&app);
    workspace_status(Path::new(&config.workspace_root))?;
    reveal_path(Path::new(&config.workspace_root))
}

#[tauri::command]
fn reveal_workspace_location(app: AppHandle, location: String) -> Result<(), String> {
    let config = read_config(&app);
    let root = Path::new(&config.workspace_root);
    workspace_status(root)?;
    let relative = match location.as_str() {
        "projects" => "Projects",
        "assets" => "Assets",
        "results" => "Results",
        "documentation" => "Documentation",
        "root" => "",
        _ => return Err("Unknown workspace location".into()),
    };
    let target = root.join(relative);
    fs::create_dir_all(&target).map_err(|error| error.to_string())?;
    reveal_path(&target)
}

#[tauri::command]
fn open_user_guide(app: AppHandle) -> Result<(), String> {
    let config = read_config(&app);
    workspace_status(Path::new(&config.workspace_root))?;
    let resolved = resolve_user_guide_path(Path::new(&config.workspace_root))?;
    reveal_path(&resolved).map_err(|error| format!("Could not open the user guide: {error}"))
}

fn resolve_user_guide_path(workspace_path: &Path) -> Result<PathBuf, String> {
    let workspace = workspace_path
        .canonicalize()
        .map_err(|error| format!("Could not resolve the current workspace: {error}"))?;
    let guide = workspace.join("Documentation").join("README.md");
    if !guide.is_file() {
        return Err(
            "The Workbench User Guide is not installed. Restart Workbench to retry documentation setup."
                .into(),
        );
    }
    let resolved = guide
        .canonicalize()
        .map_err(|error| format!("Could not resolve the user guide: {error}"))?;
    if !resolved.starts_with(&workspace) {
        return Err("The user guide path is outside the current workspace".into());
    }
    Ok(resolved)
}

#[tauri::command]
fn get_workspace_settings(app: AppHandle) -> Result<WorkspaceSettings, String> {
    let config = read_config(&app);
    workspace_status(Path::new(&config.workspace_root))?;
    let text = fs::read_to_string(Path::new(&config.workspace_root).join(WORKSPACE_SETTINGS))
        .map_err(|error| error.to_string())?;
    serde_json::from_str(&text).map_err(|error| error.to_string())
}

#[tauri::command]
fn update_workspace_settings(
    app: AppHandle,
    settings: WorkspaceSettings,
) -> Result<WorkspaceSettings, String> {
    let config = read_config(&app);
    let path = Path::new(&config.workspace_root).join(WORKSPACE_SETTINGS);
    fs::write(
        path,
        serde_json::to_string_pretty(&settings).map_err(|error| error.to_string())?,
    )
    .map_err(|error| error.to_string())?;
    Ok(settings)
}

#[tauri::command]
fn update_desktop_preferences(
    app: AppHandle,
    theme: String,
    default_run_mode: String,
    memory_limit_gb: Option<f64>,
    notifications_enabled: bool,
    notification_success_threshold_seconds: u64,
    auto_start_docker: bool,
    comparison_palettes: ComparisonPalettes,
    master_comparison_palette: ComparisonPalette,
    use_master_comparison_palette: bool,
) -> Result<DesktopState, String> {
    if !matches!(theme.as_str(), "system" | "light" | "dark") {
        return Err("Unknown appearance mode".into());
    }
    if !matches!(default_run_mode.as_str(), "queued" | "parallel") {
        return Err("Unknown run mode".into());
    }
    if memory_limit_gb.is_some_and(|value| value < 1.0 || value > 512.0) {
        return Err("Memory limit must be between 1 and 512 GB".into());
    }
    if !(10..=86400).contains(&notification_success_threshold_seconds) {
        return Err("Notification delay must be between 10 seconds and 24 hours".into());
    }
    let valid_color = |value: &str| {
        value.len() == 7
            && value.starts_with('#')
            && value[1..]
                .chars()
                .all(|character| character.is_ascii_hexdigit())
    };
    for palette in [
        &comparison_palettes.table,
        &comparison_palettes.map,
        &comparison_palettes.chart,
        &master_comparison_palette,
    ] {
        if !valid_color(&palette.increase)
            || !valid_color(&palette.decrease)
            || !valid_color(&palette.neutral)
        {
            return Err("Comparison colors must use #RRGGBB format".into());
        }
    }
    let mut config = read_config(&app);
    let newly_enabled = notifications_enabled && !config.notifications_enabled;
    config.theme = theme;
    #[cfg(target_os = "windows")]
    {
        config.resources.default_run_mode = "queued".into();
        config.resources.max_concurrent_runs = 1;
        config.resources.memory_limit_gb = None;
    }
    #[cfg(not(target_os = "windows"))]
    {
        config.resources.default_run_mode = default_run_mode;
        config.resources.max_concurrent_runs = 2;
        config.resources.memory_limit_gb = memory_limit_gb;
    }
    config.notifications_enabled = notifications_enabled;
    config.notification_success_threshold_seconds = notification_success_threshold_seconds;
    config.auto_start_docker = cfg!(not(target_os = "windows")) && auto_start_docker;
    config.comparison_palettes = comparison_palettes;
    config.master_comparison_palette = master_comparison_palette;
    config.use_master_comparison_palette = use_master_comparison_palette;
    if !notifications_enabled {
        config.notification_registration_sent = false;
    }
    write_config(&app, &config)?;
    if newly_enabled {
        app.notification()
            .builder()
            .title("VisionEval Workbench notifications enabled")
            .body("Workbench will alert you when runs and long-running comparisons finish or fail.")
            .show()
            .map_err(|error| {
                format!(
                    "Notifications were saved, but the confirmation could not be shown: {error}"
                )
            })?;
        config.notification_registration_sent = true;
        write_config(&app, &config)?;
    }
    Ok(desktop_state(app))
}

#[tauri::command]
fn send_workbench_notification(
    app: AppHandle,
    title: String,
    body: String,
    outcome: String,
    elapsed_seconds: Option<u64>,
    force: bool,
) -> Result<NotificationDelivery, String> {
    let config = read_config(&app);
    let focused = if force {
        false
    } else {
        app.get_webview_window("main")
            .map(|window| window.is_focused())
            .transpose()
            .map_err(|error| format!("Could not read Workbench window focus: {error}"))?
            .unwrap_or(false)
    };
    if let Some(reason) = notification_suppression_reason(
        config.notifications_enabled,
        &outcome,
        elapsed_seconds,
        config.notification_success_threshold_seconds,
        force,
        focused,
    ) {
        return Ok(NotificationDelivery {
            shown: false,
            reason: reason.into(),
        });
    }
    app.notification()
        .builder()
        .title(title)
        .body(body)
        .show()
        .map_err(|error| format!("Could not show notification: {error}"))?;
    Ok(NotificationDelivery {
        shown: true,
        reason: "shown".into(),
    })
}

#[tauri::command]
fn save_runtime_profile(
    app: AppHandle,
    mut profile: RuntimeProfile,
) -> Result<RuntimeProfile, String> {
    #[cfg(target_os = "windows")]
    if profile.adapter != "native"
        || !profile.verified
        || profile.ve_runtime_path.is_empty()
        || profile.ve_home_path.is_empty()
        || profile.rscript_path.is_empty()
    {
        return Err(
            "Select and verify VE_RUNTIME, VE_HOME, and Rscript.exe before saving the Windows runtime"
                .into(),
        );
    }
    #[cfg(not(target_os = "windows"))]
    if profile.adapter != "docker" || !profile.verified || profile.image_digest.is_empty() {
        return Err("Only a verified Docker runtime profile can be saved".into());
    }
    if profile.id.is_empty() {
        profile.id = stable_id("runtime");
    }
    profile.remote_status = "local".into();
    let mut config = read_config(&app);
    config.runtime_profiles.retain(|item| item.id != profile.id);
    config.runtime_profiles.push(profile.clone());
    config.active_runtime_profile_id = profile.id.clone();
    write_config(&app, &config)?;
    Ok(profile)
}

#[tauri::command]
fn complete_onboarding(app: AppHandle) -> Result<(), String> {
    let mut config = read_config(&app);
    workspace_status(Path::new(&config.workspace_root))?;
    config.onboarding_version = ONBOARDING_VERSION;
    write_config(&app, &config)
}

#[tauri::command]
fn get_theme(app: AppHandle) -> String {
    read_config(&app).theme
}
#[tauri::command]
fn set_theme(app: AppHandle, theme: String) -> Result<(), String> {
    if !matches!(theme.as_str(), "system" | "light" | "dark") {
        return Err("Unknown appearance mode".into());
    }
    let mut config = read_config(&app);
    config.theme = theme;
    write_config(&app, &config)
}

fn free_port() -> Result<u16, String> {
    let listener = TcpListener::bind("127.0.0.1:0").map_err(|error| error.to_string())?;
    Ok(listener
        .local_addr()
        .map_err(|error| error.to_string())?
        .port())
}
fn stop_backend(state: &BackendState) {
    if let Ok(mut child) = state.child.lock() {
        if let Some(mut running) = child.take() {
            let _ = running.kill();
            let _ = running.wait();
        }
    }
    if let Ok(mut port) = state.port.lock() {
        *port = None;
    }
}
#[tauri::command]
fn start_docker_desktop() -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        return Err("Docker is not used by VisionEval Workbench on Windows".into());
    }
    #[cfg(not(target_os = "windows"))]
    {
        if !Path::new("/Applications/Docker.app").exists() {
            return Err("Docker Desktop is not installed in /Applications".into());
        }
        Command::new("open")
            .args(["-gj", "-a", "Docker"])
            .spawn()
            .map_err(|error| format!("Could not start Docker Desktop: {error}"))?;
        Ok(())
    }
}
fn start_backend_blocking(app: AppHandle) -> Result<String, String> {
    let state = app.state::<BackendState>();
    if let Some(port) = *state.port.lock().map_err(|error| error.to_string())? {
        let url = format!("http://127.0.0.1:{port}");
        if ureq::get(&format!("{url}/api/health"))
            .call()
            .map(|response| response.status() == 200)
            .unwrap_or(false)
        {
            return Ok(url);
        }
        stop_backend(&state);
    }
    let config = read_config(&app);
    let workspace_root = std::env::var("WORKBENCH_SMOKE_WORKSPACE")
        .unwrap_or_else(|_| config.workspace_root.clone());
    workspace_status(Path::new(&workspace_root))
        .map_err(|error| format!("Workspace recovery is required: {error}"))?;
    let port = free_port()?;
    let executable = std::env::current_exe()
        .map_err(|error| error.to_string())?
        .parent()
        .ok_or("Could not find app executable folder")?
        .join("visioneval-workbench-backend");
    #[cfg(target_os = "windows")]
    let executable = {
        let mut path = executable;
        path.set_extension("exe");
        path
    };
    let mut command = Command::new(&executable);
    command
        .env("PORT", port.to_string())
        .env("VISIONEVAL_WORKSPACE_ROOT", &workspace_root)
        .env("WORKBENCH_PARENT_PID", std::process::id().to_string());
    if std::env::var("WORKBENCH_RENDERER_SMOKE").as_deref() == Ok("1") {
        command.env("WORKBENCH_RENDERER_SMOKE", "1");
    }
    #[cfg(target_os = "windows")]
    if let Some(profile) = config.runtime_profiles.iter().find(|profile| {
        profile.id == config.active_runtime_profile_id && profile.adapter == "native"
    }) {
        command
            .env("VISIONEVAL_RUNTIME", &profile.ve_runtime_path)
            .env("VE_RUNTIME", &profile.ve_runtime_path)
            .env("VISIONEVAL_HOME", &profile.ve_home_path)
            .env("VE_HOME", &profile.ve_home_path)
            .env("RSCRIPT", &profile.rscript_path);
    }
    #[cfg(not(target_os = "windows"))]
    if let Some(profile) = config.runtime_profiles.iter().find(|profile| {
        profile.id == config.active_runtime_profile_id && profile.adapter == "docker"
    }) {
        command
            .env("VISIONEVAL_IMAGE", &profile.image_reference)
            .env("VISIONEVAL_EXPECTED_DIGEST", &profile.image_digest);
    }
    command.env(
        "VISIONEVAL_RUNTIME_ADAPTER",
        if cfg!(target_os = "windows") {
            "native"
        } else {
            "docker"
        },
    );
    let runtime_enabled = config.runtime_profiles.iter().any(|profile| {
        profile.id == config.active_runtime_profile_id
            && profile.adapter
                == if cfg!(target_os = "windows") {
                    "native"
                } else {
                    "docker"
                }
            && profile.verified
    });
    command.env(
        "VISIONEVAL_RUNTIME_ENABLED",
        if runtime_enabled { "true" } else { "false" },
    );
    if let Some(memory) = config.resources.memory_limit_gb {
        command.env("VISIONEVAL_MEMORY_GB", memory.to_string());
    }
    let child = command
        .spawn()
        .map_err(|error| format!("{}: {}", executable.display(), error))?;
    *state.child.lock().map_err(|error| error.to_string())? = Some(child);
    let url = format!("http://127.0.0.1:{port}");
    let started = Instant::now();
    while started.elapsed() < Duration::from_secs(45) {
        let exit_status = {
            let mut child = state.child.lock().map_err(|error| error.to_string())?;
            match child.as_mut() {
                Some(running) => running.try_wait().map_err(|error| error.to_string())?,
                None => return Err("Workbench backend process disappeared during startup".into()),
            }
        };
        if let Some(status) = exit_status {
            stop_backend(&state);
            return Err(format!(
                "Workbench backend exited during startup ({status})"
            ));
        }
        if ureq::get(&format!("{url}/api/health"))
            .call()
            .map(|response| response.status() == 200)
            .unwrap_or(false)
        {
            *state.port.lock().map_err(|error| error.to_string())? = Some(port);
            return Ok(url);
        }
        std::thread::sleep(Duration::from_millis(250));
    }
    stop_backend(&state);
    Err("Workbench backend did not become ready within 45 seconds".into())
}
#[tauri::command]
async fn start_backend(app: AppHandle) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || start_backend_blocking(app))
        .await
        .map_err(|error| format!("Workbench startup task failed: {error}"))?
}
#[tauri::command]
async fn restart_backend(app: AppHandle) -> Result<String, String> {
    {
        let state = app.state::<BackendState>();
        stop_backend(&state);
    }
    start_backend(app).await
}

#[tauri::command]
fn renderer_smoke_mode() -> bool {
    std::env::var("WORKBENCH_RENDERER_SMOKE").as_deref() == Ok("1")
}

#[tauri::command]
fn report_renderer_smoke(app: AppHandle, result: Value) -> Result<(), String> {
    if !renderer_smoke_mode() {
        return Err("Renderer smoke reporting is only available in smoke mode".into());
    }
    let report_path = std::env::var("WORKBENCH_RENDERER_SMOKE_REPORT")
        .map_err(|_| "WORKBENCH_RENDERER_SMOKE_REPORT is required".to_string())?;
    let path = PathBuf::from(report_path);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    fs::write(
        &path,
        serde_json::to_string_pretty(&result).map_err(|error| error.to_string())?,
    )
    .map_err(|error| error.to_string())?;
    let passed = result
        .get("success")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let state = app.state::<BackendState>();
    stop_backend(&state);
    app.exit(if passed { 0 } else { 2 });
    Ok(())
}

#[tauri::command]
fn complete_quit(app: AppHandle) -> Result<(), String> {
    let state = app.state::<BackendState>();
    *state
        .quit_requested
        .lock()
        .map_err(|error| error.to_string())? = true;
    stop_backend(&state);
    app.exit(0);
    Ok(())
}

fn main() {
    tauri::Builder::default().plugin(tauri_plugin_dialog::init()).plugin(tauri_plugin_notification::init()).manage(BackendState::default())
        .menu(workbench_menu)
        .on_menu_event(|app, event| {
            let id = event.id().as_ref();
            let action = match id {
                "new-scenario" | "new-file" | "batch-change" | "save-file" | "view-explore" | "view-create" | "view-run" | "view-compare" | "zoom-in" | "zoom-out" | "actual-size" | "map-zoom-in" | "map-zoom-out" | "map-fit-mpo" | "map-virginia" | "refresh" | "run-selected" | "stop-selected-run" | "stop-all-runs" | "settings" | "show-workspace-in-finder" | "user-guide" | "keyboard-shortcuts" | "runtime-setup-guide" | "export-dependency-svg" | "export-dependency-pdf" | "export-dependency-html" | "export-current-csv" | "export-current-xlsx" | "export-all-changed-csv" | "export-all-changed-xlsx" | "export-selected-changed" | "export-full-variables" | "export-map-pdf" | "export-map-png" | "export-map-svg" | "export-map-csv" | "export-map-xlsx" | "export-dashboard-pdf" | "export-dashboard-csv" | "export-dashboard-xlsx" => Some(id),
                _ => None,
            };
            if let (Some(action), Some(window)) = (action, app.get_webview_window("main")) {
                if let Ok(value) = serde_json::to_string(action) { let _ = window.eval(format!("window.dispatchEvent(new CustomEvent('visioneval-menu-action', {{ detail: {value} }}));")); }
            }
        })
        .invoke_handler(tauri::generate_handler![desktop_state, create_workspace, create_recommended_workspace, choose_workspace, choose_workspace_destination, choose_workspace_parent, choose_folder, choose_package, choose_package_folder, choose_rscript, save_dependency_export, save_backend_export, save_visual_export, save_comparison_export, move_workspace, switch_workspace, forget_workspace, trash_workspace, reveal_workspace, reveal_workspace_location, open_user_guide, get_workspace_settings, update_workspace_settings, update_desktop_preferences, send_workbench_notification, save_runtime_profile, complete_onboarding, get_theme, set_theme, set_menu_context, set_app_zoom, start_docker_desktop, start_backend, restart_backend, renderer_smoke_mode, report_renderer_smoke, complete_quit])
        .on_window_event(|window, event| if let tauri::WindowEvent::CloseRequested { api, .. } = event {
            let already_quitting = window.try_state::<BackendState>().and_then(|state| state.quit_requested.lock().ok().map(|value| *value)).unwrap_or(false);
            if !already_quitting {
                api.prevent_close();
                if let Some(webview) = window.app_handle().get_webview_window("main") {
                    let _ = webview.eval("window.requestWorkbenchQuit && window.requestWorkbenchQuit();");
                }
            }
        })
        .run(tauri::generate_context!()).expect("error while running VisionEval Workbench");
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn notification_policy_applies_threshold_focus_and_force_rules() {
        assert_eq!(
            notification_suppression_reason(false, "failed", Some(1), 60, false, false),
            Some("disabled")
        );
        assert_eq!(
            notification_suppression_reason(true, "succeeded", Some(59), 60, false, false),
            Some("duration")
        );
        assert_eq!(
            notification_suppression_reason(true, "succeeded", Some(60), 60, false, false),
            None
        );
        assert_eq!(
            notification_suppression_reason(true, "failed", Some(1), 60, false, false),
            None
        );
        assert_eq!(
            notification_suppression_reason(true, "failed", Some(1), 60, false, true),
            Some("focused")
        );
        assert_eq!(
            notification_suppression_reason(true, "succeeded", Some(600), 60, false, true),
            Some("focused")
        );
        assert_eq!(
            notification_suppression_reason(true, "test", Some(0), 60, true, true),
            None
        );
    }
    #[test]
    fn unrelated_nonempty_folder_is_rejected() {
        let root = std::env::temp_dir().join(stable_id("workspace-unrelated-test"));
        fs::create_dir_all(&root).unwrap();
        fs::write(root.join("unrelated.txt"), "x").unwrap();
        assert!(workspace_status(&root)
            .unwrap_err()
            .contains("not a recognizable"));
        fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn empty_and_legacy_folders_are_recognized() {
        let root = std::env::temp_dir().join(stable_id("workspace-legacy-test"));
        fs::create_dir_all(&root).unwrap();
        assert_eq!(workspace_status(&root).unwrap(), "empty");
        fs::create_dir_all(root.join("Projects")).unwrap();
        fs::create_dir_all(root.join("runs")).unwrap();
        assert_eq!(workspace_status(&root).unwrap(), "legacy");
        fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn recent_workspace_state_requires_matching_identity_and_protects_current() {
        let root = std::env::temp_dir().join(stable_id("workspace-recent-state-test"));
        let id = initialize_workspace(&root).unwrap();
        let item = RecentWorkspace {
            id: id.clone(),
            name: "Test workspace".into(),
            path: root.to_string_lossy().to_string(),
            last_opened_at: now_string(),
        };
        let mut config = DesktopConfig::default();
        let available = recent_workspace_state(&item, &config);
        assert!(available.exists);
        assert!(available.valid);
        assert!(!available.current);
        assert!(available.removable);

        config.workspace_root = item.path.clone();
        config.workspace_id = id;
        let current = recent_workspace_state(&item, &config);
        assert!(current.current);
        assert!(!current.removable);

        fs::remove_dir_all(&root).unwrap();
        let missing = recent_workspace_state(&item, &DesktopConfig::default());
        assert!(!missing.exists);
        assert!(!missing.valid);
        assert!(!missing.removable);
    }
    #[test]
    fn recommended_workspace_path_is_home_relative_for_display() {
        assert_eq!(
            display_workspace_path(&recommended_workspace_root()),
            "~/VisionEval Workbench Workspace"
        );
    }
    #[test]
    fn user_guide_resolves_only_after_it_is_installed() {
        let root = std::env::temp_dir().join(stable_id("guide-test"));
        fs::create_dir_all(root.join("Documentation")).unwrap();
        assert!(resolve_user_guide_path(&root)
            .unwrap_err()
            .contains("not installed"));
        fs::write(root.join("Documentation").join("README.md"), "# Guide").unwrap();
        let resolved = resolve_user_guide_path(&root).unwrap();
        assert_eq!(
            resolved,
            root.canonicalize()
                .unwrap()
                .join("Documentation")
                .join("README.md")
        );
        fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn notifications_are_opt_in_for_existing_and_new_configs() {
        let config: DesktopConfig = serde_json::from_str("{}").unwrap();
        assert!(!config.notifications_enabled);
        assert!(!DesktopConfig::default().notifications_enabled);
        assert_eq!(config.notification_success_threshold_seconds, 60);
        assert_eq!(
            DesktopConfig::default().notification_success_threshold_seconds,
            60
        );
        assert!(!config.notification_registration_sent);
    }
    #[test]
    fn docker_auto_start_matches_platform() {
        let config: DesktopConfig = serde_json::from_str("{}").unwrap();
        assert_eq!(default_auto_start_docker(), !cfg!(target_os = "windows"));
        assert_eq!(
            DesktopConfig::default().auto_start_docker,
            !cfg!(target_os = "windows")
        );
        assert_eq!(config.auto_start_docker, !cfg!(target_os = "windows"));
    }
    #[test]
    fn runtime_profile_migration_selects_the_platform_adapter() {
        let unsupported_adapter = if cfg!(target_os = "windows") {
            "docker"
        } else {
            "native"
        };
        let supported_adapter = if cfg!(target_os = "windows") {
            "native"
        } else {
            "docker"
        };
        let mut config = DesktopConfig::default();
        config.configuration_version = CONFIG_VERSION - 1;
        config.active_runtime_profile_id = "runtime-profile".into();
        config.runtime_profiles.push(RuntimeProfile {
            id: "runtime-profile".into(),
            adapter: unsupported_adapter.into(),
            image_reference: r"C:\VisionEval".into(),
            image_digest: "sha256:old".into(),
            verified: true,
            verified_at: "2026-08-07T00:00:00Z".into(),
            ve_runtime_path: r"C:\VE".into(),
            ve_home_path: r"C:\VisionEval".into(),
            ..RuntimeProfile::default()
        });
        assert!(migrate_runtime_profiles(&mut config));
        assert!(config.active_runtime_profile_id.is_empty());
        assert!(!config.runtime_profiles[0].verified);
        assert!(config.runtime_profiles[0].image_digest.is_empty());
        assert!(config.runtime_profiles[0]
            .verification_message
            .contains("Runtime setup changed"));
        config.configuration_version = CONFIG_VERSION;
        config.runtime_profiles[0].adapter = supported_adapter.into();
        assert!(!migrate_runtime_profiles(&mut config));
    }
    #[test]
    fn comparison_export_ids_are_restricted_to_generated_identifiers() {
        assert!(valid_export_operation_id(
            "comparison-export-change-summary-156fb9567c"
        ));
        assert!(!valid_export_operation_id("../change-summary"));
        assert!(!valid_export_operation_id("comparison export"));
        assert!(!valid_export_operation_id(""));
    }
    #[test]
    fn backend_exports_are_limited_to_fixed_routes() {
        assert_eq!(
            backend_export_spec("comparison-current-csv"),
            Some(("/api/comparison/export-current", "csv", "CSV"))
        );
        assert_eq!(
            backend_export_spec("dashboard-pdf"),
            Some(("/api/comparison/export-dashboard-pdf", "pdf", "PDF"))
        );
        assert_eq!(backend_export_spec("http://example.com/file"), None);
    }
}
