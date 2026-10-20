#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::Value;
use tauri::Manager;

const AGENT_URL: &str = "http://127.0.0.1:8000";

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
// Comandos
// ============================================================

#[tauri::command]
async fn get_task_status() -> Value {
    tauri::async_runtime::spawn_blocking(|| {
        let client = match reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(3))
            .build()
        {
            Ok(c) => c,
            Err(_) => return serde_json::json!({ "state": "idle", "error": "client" }),
        };
        match client.get(format!("{}/task_status", AGENT_URL)).send() {
            Ok(r) => r.json().unwrap_or_else(|_| serde_json::json!({ "state": "idle" })),
            Err(_) => serde_json::json!({ "state": "idle", "error": "offline" }),
        }
    }).await.unwrap_or_else(|_| serde_json::json!({ "state": "idle" }))
}

#[tauri::command]
async fn cancel_task() -> Value {
    tauri::async_runtime::spawn_blocking(|| {
        let client = reqwest::blocking::Client::new();
        match client.post(format!("{}/task_cancel", AGENT_URL)).send() {
            Ok(r) => r.json().unwrap_or_else(|_| serde_json::json!({ "status": "ok" })),
            Err(_) => serde_json::json!({ "status": "erro" }),
        }
    }).await.unwrap_or_else(|_| serde_json::json!({ "status": "erro" }))
}

#[tauri::command]
fn resize_window(window: tauri::Window, width: u32, height: u32) -> Result<(), String> {
    window
        .set_size(tauri::LogicalSize::new(width, height))
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn get_gpu_info() -> Value {
    tauri::async_runtime::spawn_blocking(|| {
        use std::process::Command;
        let output = match Command::new("nvidia-smi")
            .args([
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ])
            .output()
        {
            Ok(o) => o,
            Err(_) => return serde_json::json!({ "ok": false, "error": "nvidia-smi nao encontrado" }),
        };
        if !output.status.success() {
            return serde_json::json!({ "ok": false, "error": "nvidia-smi falhou" });
        }
        let s = String::from_utf8_lossy(&output.stdout);
        let line = s.lines().next().unwrap_or("");
        let parts: Vec<&str> = line.split(',').map(|x| x.trim()).collect();
        if parts.len() < 2 {
            return serde_json::json!({ "ok": false, "error": "parse falhou" });
        }
        let used: u64 = parts[0].parse().unwrap_or(0);
        let total: u64 = parts[1].parse().unwrap_or(0);
        serde_json::json!({ "ok": true, "used": used, "total": total })
    }).await.unwrap_or_else(|_| serde_json::json!({ "ok": false }))
}

#[tauri::command]
fn toggle_always_on_top(app: tauri::AppHandle, on_top: bool) -> Result<bool, String> {
    let win = app.get_webview_window("main").ok_or("janela main nao encontrada")?;
    win.set_always_on_top(on_top).map_err(|e| e.to_string())?;
    Ok(on_top)
}

// ============================================================
// [NOVO] Posicao global do cursor + posicao da janela
// ============================================================
#[tauri::command]
fn get_cursor_relative_to_window(app: tauri::AppHandle) -> Value {
    let win = match app.get_webview_window("main") {
        Some(w) => w,
        None => return serde_json::json!({ "ok": false, "error": "sem janela" }),
    };

    // Posicao global do cursor
    let cursor = win32::cursor_pos();

    // Posicao da janela na tela
    let pos = match win.outer_position() {
        Ok(p) => p,
        Err(_) => return serde_json::json!({ "ok": false, "error": "sem posicao" }),
    };
    let size = match win.outer_size() {
        Ok(s) => s,
        Err(_) => return serde_json::json!({ "ok": false, "error": "sem tamanho" }),
    };

    let win_x = pos.x;
    let win_y = pos.y;
    let win_w = size.width as i32;
    let win_h = size.height as i32;

    // Centro da janela
    let cx = win_x + win_w / 2;
    let cy = win_y + win_h / 2;

    // Delta do cursor em relacao ao centro da janela
    let dx = cursor.x - cx;
    let dy = cursor.y - cy;
    let dist = ((dx * dx + dy * dy) as f64).sqrt();

    serde_json::json!({
        "ok": true,
        "dx": dx,
        "dy": dy,
        "dist": dist,
        "win_w": win_w,
        "win_h": win_h,
    })
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_task_status,
            cancel_task,
            resize_window,
            get_gpu_info,
            toggle_always_on_top,
            get_cursor_relative_to_window
        ])
        .run(tauri::generate_context!())
        .expect("error while running myra-widget");
}