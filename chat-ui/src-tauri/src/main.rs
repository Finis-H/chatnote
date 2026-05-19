// Prevents additional console window on Windows in release, DO NOT REMOVE!!
// src-tauri/src/main.rs (或 lib.rs)

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use tauri::Manager;
use std::fs;
//窃密插件
#[tauri::command]
fn get_run_token() -> Result<String, String> {
    // 1. 先尝试在开发环境的相对路径找
    let dev_paths = ["vault/.run_token", "../vault/.run_token", "../../vault/.run_token"];
    for path in dev_paths.iter() {
        if let Ok(content) = fs::read_to_string(path) {
            return Ok(content.trim().to_string());
        }
    }
    // 2. 如果相对路径没有，去生产环境的 AppData/Roaming 找！
    if let Some(mut app_data) = dirs::data_dir() { // 需要在 Cargo.toml 添加 dirs = "5.0" 依赖
        app_data.push("VaultOS");
        app_data.push("vault");
        app_data.push(".run_token");
        if let Ok(content) = fs::read_to_string(&app_data) {
            return Ok(content.trim().to_string());
        }
    }
    Err("未找到Token，请确认后端已点火！".to_string())
}

fn main() {
    tauri::Builder::default()
        // 激活全局热键插件
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        // 把刚才写的窃密插件注册给前端！
        .invoke_handler(tauri::generate_handler![get_run_token])
        .setup(|app| {
            let _window = app.get_webview_window("main").unwrap();
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}