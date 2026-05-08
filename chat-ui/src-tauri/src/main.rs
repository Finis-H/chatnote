// Prevents additional console window on Windows in release, DO NOT REMOVE!!
// src-tauri/src/main.rs (或 lib.rs)

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use tauri::Manager;
use std::fs;
//窃密插件
#[tauri::command]
fn get_run_token() -> Result<String, String> {
    // 极客容错：开发模式和打包后的运行路径不同，我们多找几个地方
    let paths = [
        "vault/.run_token", 
        "../vault/.run_token",
        "../../vault/.run_token"];
    for path in paths.iter() {
        if let Ok(content) = fs::read_to_string(path) {
            return Ok(content.trim().to_string()); // 去掉空格和换行
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