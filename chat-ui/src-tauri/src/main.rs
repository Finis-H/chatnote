// src-tauri/src/main.rs
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::path::PathBuf;
use std::thread;
use std::time::Duration;
use tauri::Manager;
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

fn get_vault_path() -> PathBuf {
    #[cfg(debug_assertions)]
    {
        let dev_path = std::env::current_dir()
            .unwrap_or_default()
            .join("../../vault");
        if dev_path.exists() {
            return dev_path;
        }
    }

    #[cfg(not(debug_assertions))]
    {
        if let Some(local_data_dir) = dirs::data_local_dir() {
            let vault_path = local_data_dir.join("Vault OS").join("vault");
            let _ = fs::create_dir_all(&vault_path);
            return vault_path;
        }
    }

    if let Ok(mut exe_path) = std::env::current_exe() {
        exe_path.pop();
        let prod_vault = exe_path.join("vault");
        let _ = fs::create_dir_all(&prod_vault);
        return prod_vault;
    }

    let fallback = PathBuf::from("vault");
    let _ = fs::create_dir_all(&fallback);
    fallback
}

#[tauri::command]
fn get_run_token() -> Result<String, String> {
    let token_file = get_vault_path().join(".run_token");

    for _ in 0..30 {
        if let Ok(content) = fs::read_to_string(&token_file) {
            if !content.trim().is_empty() {
                return Ok(content.trim().to_string());
            }
        }
        thread::sleep(Duration::from_millis(500));
    }
    Err("等待 Vault OS 后端启动超时，请重启应用。".to_string())
}

#[tauri::command]
fn get_server_port() -> Result<u16, String> {
    let port_file = get_vault_path().join(".server_port");

    for _ in 0..30 {
        if let Ok(content) = fs::read_to_string(&port_file) {
            if let Ok(port) = content.trim().parse::<u16>() {
                return Ok(port);
            }
        }
        thread::sleep(Duration::from_millis(500));
    }
    Ok(8000)
}

fn main() {
    let mut builder = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .invoke_handler(tauri::generate_handler![get_run_token, get_server_port]);

    #[cfg(not(debug_assertions))]
    {
        builder = builder.setup(|app| {
            let vault_dir = get_vault_path();
            let _ = fs::remove_file(vault_dir.join(".server_port"));
            let _ = fs::remove_file(vault_dir.join(".run_token"));

            let sidecar_command = app
                .shell()
                .sidecar("vault_engine")
                .unwrap()
                .env("PYTHONIOENCODING", "utf-8")
                .env("PYTHONUTF8", "1")
                .env("VAULT_ROOT", vault_dir.to_string_lossy().to_string());

            let (mut rx, child) = sidecar_command.spawn().expect("Failed to spawn sidecar");
            app.manage(std::sync::Mutex::new(Some(child.pid())));

            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            println!("Python: {}", String::from_utf8_lossy(&line))
                        }
                        CommandEvent::Stderr(line) => {
                            eprintln!("Python ERR: {}", String::from_utf8_lossy(&line))
                        }
                        _ => {}
                    }
                }
            });
            Ok(())
        });
    }

    #[cfg(debug_assertions)]
    {
        builder = builder.setup(|_app| {
            println!("[VaultOS Dev] Development mode.");
            Ok(())
        });
    }

    let app = builder
        .build(tauri::generate_context!())
        .expect("error while running tauri application");

    #[cfg(not(debug_assertions))]
    app.run(|app_handle, event| {
        if let tauri::RunEvent::Exit = event {
            if let Some(pid_state) = app_handle.try_state::<std::sync::Mutex<Option<u32>>>() {
                if let Ok(mut pid_lock) = pid_state.lock() {
                    if let Some(pid) = pid_lock.take() {
                        std::process::Command::new("taskkill")
                            .args(["/F", "/T", "/PID", &pid.to_string()])
                            .spawn()
                            .ok();
                    }
                }
            }
        }
    });

    #[cfg(debug_assertions)]
    app.run(|_, _| {});
}
