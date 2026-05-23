// src-tauri/src/main.rs
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;
use tauri::Manager;
use std::fs;
use std::path::PathBuf;
use std::thread;
use std::time::Duration;
use std::sync::Mutex;

// 统一路径雷达
fn get_vault_path() -> PathBuf {
    if let Ok(mut exe_path) = std::env::current_exe() {
        exe_path.pop();
        let prod_vault = exe_path.join("vault");
        if prod_vault.exists() {
            return prod_vault;
        }
    }
    // 开发环境向外退两层找根目录下的 vault (完美对齐你手动运行的 python server.py)
    let dev_path = std::env::current_dir().unwrap_or_default().join("../../vault");
    if dev_path.exists() {
        return dev_path;
    }
    PathBuf::from("vault")
}

#[tauri::command]
fn get_run_token() -> Result<String, String> {
    let vault_dir = get_vault_path();
    let token_file = vault_dir.join(".run_token");
    
    // 轮询 30 次（15秒），让前端 Vue 可以安心 await 
    for _ in 0..30 {
        if let Ok(content) = fs::read_to_string(&token_file) {
            if !content.trim().is_empty() {
                return Ok(content.trim().to_string());
            }
        }
        thread::sleep(Duration::from_millis(500));
    }
    Err("等待大脑凭证超时！请确保外部终端的 python server.py 已成功启动。".to_string())
}

#[tauri::command]
fn get_server_port() -> Result<u16, String> {
    let vault_dir = get_vault_path();
    let port_file = vault_dir.join(".server_port");
    
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
        // 🚀 修复 1：把被我无情抹除的快捷键插件请回来！(确保你的 Cargo.toml 里有这个依赖)
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .invoke_handler(tauri::generate_handler![get_run_token, get_server_port]);

    #[cfg(not(debug_assertions))]
    {
        builder = builder.setup(|app| {
            let vault_dir = get_vault_path();
            let _ = fs::remove_file(vault_dir.join(".server_port"));
            let _ = fs::remove_file(vault_dir.join(".run_token"));

            let sidecar_command = app.shell().sidecar("vault_engine").unwrap()
                .env("PYTHONIOENCODING", "utf-8")
                .env("PYTHONUTF8", "1");
            
            let (mut rx, child) = sidecar_command.spawn().expect("Failed to spawn sidecar");
            
            // 🚀 核心改动：不再保存 child 句柄，而是直接提取它的底层系统 PID！
            app.manage(std::sync::Mutex::new(Some(child.pid())));

            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => println!("Python: {}", String::from_utf8_lossy(&line)),
                        CommandEvent::Stderr(line) => eprintln!("Python ERR: {}", String::from_utf8_lossy(&line)),
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
            println!("🛠️  [VaultOS Dev] 开发环境。");
            Ok(())
        });
    }

    let app = builder.build(tauri::generate_context!())
        .expect("error while running tauri application");

    #[cfg(not(debug_assertions))]
    app.run(|app_handle, event| {
        if let tauri::RunEvent::Exit = event {
            // 🚀 修复 2：动用 Windows 原生核武器，执行“进程树”物理击杀！
            if let Some(pid_state) = app_handle.try_state::<std::sync::Mutex<Option<u32>>>() {
                if let Ok(mut pid_lock) = pid_state.lock() {
                    if let Some(pid) = pid_lock.take() {
                        println!("🧹 [生命周期] 正在拔除 Python 引擎进程树 (PID: {})...", pid);
                        // /T 参数代表连同其产生的所有子进程一起击杀，专治 PyInstaller 套娃！
                        std::process::Command::new("taskkill")
                            .args(&["/F", "/T", "/PID", &pid.to_string()])
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