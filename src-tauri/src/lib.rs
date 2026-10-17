use tauri::Manager;


// ============================================================
// Win32: GetCursorPos (posicao global do mouse na tela)
// ============================================================
#[cfg(target_os = "windows")]
mod win32 {
    use std::os::raw::c_int;

    #[repr(C)]
    #[derive(Default, Clone, Copy)]
    pub struct POINT {
        pub x: c_int,
        pub y: c_int,
    }

    extern "system" {
        pub fn GetCursorPos(lpPoint: *mut POINT) -> i32;
    }

    pub fn cursor_pos() -> POINT {
        let mut p = POINT::default();
        unsafe {
            GetCursorPos(&mut p);
        }
        p
    }
}

#[cfg(not(target_os = "windows"))]
mod win32 {
    #[derive(Default, Clone, Copy)]
    pub struct POINT { pub x: i32, pub y: i32 }
    pub fn cursor_pos() -> POINT { POINT::default() }
}

// ============================================================
// IPC: posicao global do cursor
// ============================================================
#[tauri::command]
fn get_mouse_pos() -> Result<serde_json::Value, String> {
    let p = win32::cursor_pos();
    Ok(serde_json::json!({ "x": p.x, "y": p.y }))
}

// ============================================================
// IPC: click-through condicional (por label)
// ============================================================
#[tauri::command]
fn set_ignore_cursor_events(
    app: tauri::AppHandle,
    label: String,
    ignore: bool,
) -> Result<(), String> {
    let win = app
        .get_webview_window(&label)
        .ok_or_else(|| format!("janela {} nao encontrada", label))?;
    win.set_ignore_cursor_events(ignore).map_err(|e| e.to_string())?;
    Ok(())
}

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
// IPC: recursos do widget vivo (GPU, topmost e cursor global)
// ============================================================
#[tauri::command]
async fn get_gpu_info() -> serde_json::Value {
    let output = std::process::Command::new("nvidia-smi")
        .args(["--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"])
        .output();
    let output = match output {
        Ok(o) if o.status.success() => o,
        _ => return serde_json::json!({ "ok": false, "error": "nvidia-smi indisponivel" }),
    };
    let line = String::from_utf8_lossy(&output.stdout);
    let parts: Vec<&str> = line.lines().next().unwrap_or("").split(',').map(str::trim).collect();
    if parts.len() < 2 {
        return serde_json::json!({ "ok": false, "error": "resposta da GPU invalida" });
    }
    let used = parts[0].parse::<u64>().unwrap_or(0);
    let total = parts[1].parse::<u64>().unwrap_or(0);
    serde_json::json!({ "ok": true, "used": used, "total": total })
}
#[tauri::command]
fn toggle_always_on_top(app: tauri::AppHandle, on_top: bool) -> Result<bool, String> {
    let win = app.get_webview_window("main").ok_or_else(|| "janela main nao encontrada".to_string())?;
    win.set_always_on_top(on_top).map_err(|e| e.to_string())?;
    Ok(on_top)
}
#[tauri::command]
fn get_cursor_relative_to_window(app: tauri::AppHandle) -> serde_json::Value {
    let win = match app.get_webview_window("main") {
        Some(w) => w,
        None => return serde_json::json!({ "ok": false, "error": "janela main indisponivel" }),
    };
    let cursor = win32::cursor_pos();
    let position = match win.outer_position() {
        Ok(p) => p,
        Err(_) => return serde_json::json!({ "ok": false, "error": "posicao indisponivel" }),
    };
    let size = match win.outer_size() {
        Ok(s) => s,
        Err(_) => return serde_json::json!({ "ok": false, "error": "tamanho indisponivel" }),
    };
    let dx = cursor.x - (position.x + size.width as i32 / 2);
    let dy = cursor.y - (position.y + size.height as i32 / 2);
    let dist = ((dx as f64 * dx as f64) + (dy as f64 * dy as f64)).sqrt();
    serde_json::json!({ "ok": true, "dx": dx, "dy": dy, "dist": dist, "win_w": size.width, "win_h": size.height })
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
            get_gpu_info,
            toggle_always_on_top,
            get_cursor_relative_to_window,
            get_mouse_pos,
            set_ignore_cursor_events,
            set_overlay_visible
        ])
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
