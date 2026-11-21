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
    pub struct POINT {
        pub x: i32,
        pub y: i32,
    }
    pub fn cursor_pos() -> POINT {
        POINT::default()
    }
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
    win.set_ignore_cursor_events(ignore)
        .map_err(|e| e.to_string())?;
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

#[tauri::command]
fn set_widget_size(app: tauri::AppHandle, size: String) -> Result<(), String> {
    let (width, height) = match size.as_str() {
        "idle" => (200.0, 44.0),
        "pill" => (200.0, 44.0),
        "running" | "done" | "error" => (340.0, 260.0),
        "compact" => (90.0, 44.0),
        _ => return Err(format!("unknown widget size: {size}")),
    };
    let window = app
        .get_webview_window("main")
        .ok_or_else(|| "janela principal do widget nao encontrada".to_string())?;
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
        .args([
            "--query-gpu=memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ])
        .output();
    let output = match output {
        Ok(o) if o.status.success() => o,
        _ => return serde_json::json!({ "ok": false, "error": "nvidia-smi indisponivel" }),
    };
    let line = String::from_utf8_lossy(&output.stdout);
    let parts: Vec<&str> = line
        .lines()
        .next()
        .unwrap_or("")
        .split(',')
        .map(str::trim)
        .collect();
    if parts.len() < 2 {
        return serde_json::json!({ "ok": false, "error": "resposta da GPU invalida" });
    }
    let used = parts[0].parse::<u64>().unwrap_or(0);
    let total = parts[1].parse::<u64>().unwrap_or(0);
    serde_json::json!({ "ok": true, "used": used, "total": total })
}
#[tauri::command]
fn toggle_always_on_top(app: tauri::AppHandle, on_top: bool) -> Result<bool, String> {
    let win = app
        .get_webview_window("main")
        .ok_or_else(|| "janela main nao encontrada".to_string())?;
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
fn get_widget_visible(app: tauri::AppHandle) -> Result<bool, String> {
    let widget = app
        .get_webview_window("main")
        .ok_or_else(|| "janela do widget nao encontrada".to_string())?;
    widget.is_visible().map_err(|e| e.to_string())
}

#[tauri::command]
fn set_widget_visible(app: tauri::AppHandle, visible: bool) -> Result<bool, String> {
    let widget = app
        .get_webview_window("main")
        .ok_or_else(|| "janela do widget nao encontrada".to_string())?;
    if visible {
        widget.show().map_err(|e| e.to_string())?;
        widget.set_always_on_top(true).map_err(|e| e.to_string())?;
    } else {
        widget.hide().map_err(|e| e.to_string())?;
    }
    Ok(visible)
}

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
    let response = std::process::Command::new("curl")
        .args(["--fail", "--silent", "--show-error", "--max-time", "3", url])
        .output()
        .ok()
        .filter(|o| o.status.success())
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .ok_or_else(|| "agent offline".to_string())?;

    serde_json::from_str(&response).map_err(|e| e.to_string())
}

// ============================================================
// IPC: cancel task
// ============================================================

#[tauri::command]
async fn cancel_task() -> Result<serde_json::Value, String> {
    let url = "http://127.0.0.1:8000/task_cancel";
    let response = std::process::Command::new("curl")
        .args([
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            "3",
            "-X",
            "POST",
            url,
        ])
        .output()
        .ok()
        .filter(|o| o.status.success())
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .ok_or_else(|| "agent offline".to_string())?;

    serde_json::from_str(&response).map_err(|e| e.to_string())
}

// ============================================================
// IPC: focus the existing Chrome window for human takeover
#[tauri::command]
fn focus_chrome_window() -> Result<serde_json::Value, String> {
    #[cfg(target_os = "macos")]
    {
        let output = std::process::Command::new("osascript")
            .args(["-e", "tell application \"Google Chrome\" to activate"])
            .output()
            .map_err(|e| e.to_string())?;
        if !output.status.success() {
            return Err(String::from_utf8_lossy(&output.stderr).to_string());
        }
        return Ok(serde_json::json!({"ok": true, "platform": "macos"}));
    }
    #[cfg(target_os = "linux")]
    {
        let output = std::process::Command::new("wmctrl")
            .args(["-a", "Google Chrome"])
            .output()
            .map_err(|e| e.to_string())?;
        return Ok(serde_json::json!({"ok": output.status.success(), "platform": "linux"}));
    }
    #[cfg(target_os = "windows")]
    {
        let script = r#"
Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class MyraForeground { [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd); [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow); }'
$p = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if ($null -eq $p) { @{ok=$false;error="Nenhuma janela visível do Chrome foi encontrada."} | ConvertTo-Json -Compress; exit 0 }
[void][MyraForeground]::ShowWindowAsync($p.MainWindowHandle, 9)
$ok = [MyraForeground]::SetForegroundWindow($p.MainWindowHandle)
@{ok=$ok;processId=$p.Id} | ConvertTo-Json -Compress
"#;
        let output = std::process::Command::new("powershell")
            .args([
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ])
            .output()
            .map_err(|e| e.to_string())?;
        if !output.status.success() {
            return Err(String::from_utf8_lossy(&output.stderr).to_string());
        }
        serde_json::from_slice(&output.stdout)
            .map_err(|_| String::from_utf8_lossy(&output.stdout).to_string())
    }
}
// RUN
// ============================================================

#[tauri::command]
fn open_external_url(url: String) -> Result<(), String> {
    let parsed = url::Url::parse(&url).map_err(|e| e.to_string())?;
    if !matches!(parsed.scheme(), "https" | "http") {
        return Err("Somente links HTTP/HTTPS podem ser abertos externamente.".to_string());
    }
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("rundll32.exe")
            .args(["url.dll,FileProtocolHandler", parsed.as_str()])
            .spawn()
            .map_err(|e| e.to_string())?;
        return Ok(());
    }
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg(parsed.as_str())
            .spawn()
            .map_err(|e| e.to_string())?;
        return Ok(());
    }
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open")
            .arg(parsed.as_str())
            .spawn()
            .map_err(|e| e.to_string())?;
        Ok(())
    }
}

#[tauri::command]
fn focus_desktop_window(app: tauri::AppHandle) -> Result<(), String> {
    let win = app
        .get_webview_window("desktop")
        .ok_or_else(|| "janela desktop nao encontrada".to_string())?;
    win.show().map_err(|e| e.to_string())?;
    win.set_focus().map_err(|e| e.to_string())?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().build())
        .on_window_event(|window, event| {
            // The desktop workspace is the application owner. Closing it must
            // terminate the widget and overlay too, rather than leaving a
            // floating MYRA process behind in the background.
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                if window.label() == "desktop" {
                    window.app_handle().exit(0);
                }
            }
        })
        .setup(|app| {
            if let Some(overlay) = app.get_webview_window("overlay") {
                // Native click-through: the transparent window never blocks real clicks.
                overlay.set_ignore_cursor_events(true)?;
                overlay.set_always_on_top(true)?;
                overlay.hide()?;
            }
            // Fit the desktop workspace to the monitor work area. A fixed 1440x920
            // window can push the composer below the visible screen on 1366x768 / HiDPI displays.
            if let Some(desktop) = app.get_webview_window("desktop") {
                desktop.show()?;
                let monitor = desktop.current_monitor()?.or(desktop.primary_monitor()?);
                if let Some(monitor) = monitor {
                    let scale = monitor.scale_factor().max(1.0);
                    let area = monitor.work_area().size;
                    let width = ((area.width as f64 / scale) * 0.95).min(1440.0).max(980.0);
                    let height = ((area.height as f64 / scale) * 0.92).min(780.0).max(600.0);
                    desktop.set_size(tauri::LogicalSize::new(width, height))?;
                    desktop.center()?;
                }
                desktop.set_focus()?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            resize_window,
            set_widget_size,
            get_task_status,
            cancel_task,
            get_gpu_info,
            toggle_always_on_top,
            get_cursor_relative_to_window,
            get_mouse_pos,
            set_ignore_cursor_events,
            set_overlay_visible,
            set_widget_visible,
            get_widget_visible,
            focus_chrome_window,
            open_external_url,
            focus_desktop_window
        ])
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
