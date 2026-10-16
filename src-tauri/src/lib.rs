use tauri::Manager;

// ============================================================
// IPC: widget sizing
// ============================================================

#[tauri::command]
fn resize_window(window: tauri::Window, width: u32, height: u32) -> Result<(), String> {
    window
        .set_size(tauri::LogicalSize::new(width, height))
        .map_err(|e| e.to_string())
}

// ============================================================
// IPC: TARS overlay visibility
// ============================================================

#[tauri::command]
fn set_overlay_visible(app: tauri::AppHandle, visible: bool) -> Result<(), String> {
    let overlay = app
        .get_webview_window("overlay")
        .ok_or_else(|| "janela overlay nao encontrada".to_string())?;

    if visible {
        overlay.show().map_err(|e| e.to_string())?;
        overlay.set_always_on_top(true).map_err(|e| e.to_string())?;
    } else {
        overlay.hide().map_err(|e| e.to_string())?;
    }
    Ok(())
}

// ============================================================
// IPC: task status
// ============================================================

#[tauri::command]
async fn get_task_status() -> Result<serde_json::Value, String> {
    let url = "http://127.0.0.1:8000/task_status";
    let response = std::thread::spawn(move || {
        std::process::Command::new("powershell")
            .args([
                "-NoProfile",
                "-Command",
                &format!(
                    "(Invoke-WebRequest -Uri '{}' -UseBasicParsing -TimeoutSec 3).Content",
                    url
                ),
            ])
            .output()
            .ok()
            .filter(|o| o.status.success())
            .and_then(|o| String::from_utf8(o.stdout).ok())
    })
    .join()
    .map_err(|_| "thread panic".to_string())?
    .ok_or_else(|| "agent offline".to_string())?;

    serde_json::from_str(&response).map_err(|e| e.to_string())
}

// ============================================================
// IPC: cancel task
// ============================================================

#[tauri::command]
async fn cancel_task() -> Result<serde_json::Value, String> {
    let url = "http://127.0.0.1:8000/task_cancel";
    let response = std::thread::spawn(move || {
        std::process::Command::new("powershell")
            .args([
                "-NoProfile",
                "-Command",
                &format!(
                    "(Invoke-WebRequest -Uri '{}' -Method POST -UseBasicParsing -TimeoutSec 3).Content",
                    url
                ),
            ])
            .output()
            .ok()
            .filter(|o| o.status.success())
            .and_then(|o| String::from_utf8(o.stdout).ok())
    })
    .join()
    .map_err(|_| "thread panic".to_string())?
    .ok_or_else(|| "agent offline".to_string())?;

    serde_json::from_str(&response).map_err(|e| e.to_string())
}

// ============================================================
// RUN
// ============================================================

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().build())
        .setup(|app| {
            if let Some(overlay) = app.get_webview_window("overlay") {
                // Native click-through: the transparent window never blocks real clicks.
                overlay.set_ignore_cursor_events(true)?;
                overlay.set_always_on_top(true)?;
                overlay.hide()?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            resize_window,
            get_task_status,
            cancel_task,
            set_overlay_visible
        ])
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
