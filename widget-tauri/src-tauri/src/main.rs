#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::Value;

const AGENT_URL: &str = "http://127.0.0.1:8000";

#[tauri::command]
fn get_task_status() -> Value {
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
}

#[tauri::command]
fn send_message(msg: String) -> Value {
    let client = match reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(300))
        .build()
    {
        Ok(c) => c,
        Err(_) => return serde_json::json!({ "error": "client" }),
    };

    let body = serde_json::json!({
        "model": "myra-agent",
        "messages": [{"role": "user", "content": msg}]
    });

    match client
        .post(format!("{}/v1/chat/completions", AGENT_URL))
        .json(&body)
        .send()
    {
        Ok(r) => r.json().unwrap_or_else(|_| serde_json::json!({ "error": "parse" })),
        Err(e) => serde_json::json!({ "error": format!("{}", e) }),
    }
}

#[tauri::command]
fn cancel_task() -> Value {
    let client = reqwest::blocking::Client::new();
    match client.post(format!("{}/task_cancel", AGENT_URL)).send() {
        Ok(r) => r.json().unwrap_or_else(|_| serde_json::json!({ "status": "ok" })),
        Err(_) => serde_json::json!({ "status": "erro" }),
    }
}

#[tauri::command]
fn resize_window(window: tauri::Window, width: u32, height: u32) -> Result<(), String> {
    window
        .set_size(tauri::LogicalSize::new(width, height))
        .map_err(|e| e.to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_task_status,
            send_message,
            cancel_task,
            resize_window
        ])
        .run(tauri::generate_context!())
        .expect("error while running myra-widget");
}