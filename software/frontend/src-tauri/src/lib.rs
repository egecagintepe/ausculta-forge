mod process_manager;

use process_manager::{BackendConfig, BackendManager};
use std::sync::{Arc, Mutex};
use tauri::State;

struct AppState {
    backend: Arc<Mutex<BackendManager>>,
}

#[tauri::command]
fn get_backend_config(state: State<'_, AppState>) -> Result<BackendConfig, String> {
    let mgr = state.backend.lock().map_err(|e| e.to_string())?;
    mgr.config
        .clone()
        .ok_or_else(|| "Backend is not currently running or ready".to_string())
}

#[tauri::command]
fn restart_backend(state: State<'_, AppState>) -> Result<BackendConfig, String> {
    let mut mgr = state.backend.lock().map_err(|e| e.to_string())?;
    mgr.stop();
    mgr.start()
}

#[tauri::command]
fn open_storage_directory(state: State<'_, AppState>) -> Result<(), String> {
    let mgr = state.backend.lock().map_err(|e| e.to_string())?;
    if let Some(ref config) = mgr.config {
        #[cfg(windows)]
        {
            std::process::Command::new("explorer")
                .arg(&config.storage_dir)
                .spawn()
                .map_err(|e| format!("Failed to open directory: {}", e))?;
        }
        #[cfg(not(windows))]
        {
            let _ = config;
        }
        Ok(())
    } else {
        Err("Storage directory not yet resolved".to_string())
    }
}

#[tauri::command]
fn get_desktop_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_manager = Arc::new(Mutex::new(BackendManager::new()));
    let manager_for_setup = Arc::clone(&backend_manager);
    let manager_for_exit = Arc::clone(&backend_manager);

    tauri::Builder::default()
        .manage(AppState {
            backend: backend_manager,
        })
        .setup(move |_app| {
            eprintln!("[Desktop] AuscultaForge Desktop Workstation initializing...");
            let mut mgr = manager_for_setup
                .lock()
                .map_err(|e| tauri::Error::from(std::io::Error::new(std::io::ErrorKind::Other, e.to_string())))?;
            
            match mgr.start() {
                Ok(cfg) => {
                    eprintln!(
                        "[Desktop] Initialized backend on port {} with auth token",
                        cfg.port
                    );
                }
                Err(err) => {
                    eprintln!("[Desktop] Error during backend initial startup: {}", err);
                    // Do not panic so the desktop shell can still display the failure diagnostic screen
                }
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_config,
            restart_backend,
            open_storage_directory,
            get_desktop_version
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(move |_app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                eprintln!("[Desktop] Application exiting; terminating backend...");
                if let Ok(mut mgr) = manager_for_exit.lock() {
                    mgr.stop();
                }
            }
        });
}
