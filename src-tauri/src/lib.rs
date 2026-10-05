// ============================================================
// COMANDO IPC: resize_window
// ============================================================

#[tauri::command]
fn resize_window(window: tauri::Window, width: u32, height: u32) -> Result<(), String> {
    window
        .set_size(tauri::LogicalSize::new(width, height))
        .map_err(|e| e.to_string())
}

// ============================================================
// COMANDO IPC: get_task_status
// ============================================================

#[tauri::command]
async fn get_task_status() -> Result<serde_json::Value, String> {
    let url = "http://127.0.0.1:8000/task_status";

    let response = std::thread::spawn(move || {
        let output = std::process::Command::new("powershell")
            .args([
                "-NoProfile",
                "-Command",
                &format!(
                    "(Invoke-WebRequest -Uri '{}' -UseBasicParsing -TimeoutSec 3).Content",
                    url
                ),
            ])
            .output();

        match output {
            Ok(o) if o.status.success() => String::from_utf8(o.stdout).ok(),
            _ => None,
        }
    })
    .join()
    .map_err(|_| "thread panic".to_string())?
    .ok_or_else(|| "agent offline".to_string())?;

    let json: serde_json::Value =
        serde_json::from_str(&response).map_err(|e| e.to_string())?;

    Ok(json)
}

// ============================================================
// COMANDO IPC: cancel_task
// ============================================================

#[tauri::command]
async fn cancel_task() -> Result<serde_json::Value, String> {
    let url = "http://127.0.0.1:8000/task_cancel";

    let response = std::thread::spawn(move || {
        let output = std::process::Command::new("powershell")
            .args([
                "-NoProfile",
                "-Command",
                &format!(
                    "(Invoke-WebRequest -Uri '{}' -Method POST -UseBasicParsing -TimeoutSec 3).Content",
                    url
                ),
            ])
            .output();

        match output {
            Ok(o) if o.status.success() => String::from_utf8(o.stdout).ok(),
            _ => None,
        }
    })
    .join()
    .map_err(|_| "thread panic".to_string())?
    .ok_or_else(|| "agent offline".to_string())?;

    let json: serde_json::Value =
        serde_json::from_str(&response).map_err(|e| e.to_string())?;

    Ok(json)
}

// ============================================================
// RUN
// ============================================================

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().build())
        .invoke_handler(tauri::generate_handler![
            resize_window,
            get_task_status,
            cancel_task
        ])
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}