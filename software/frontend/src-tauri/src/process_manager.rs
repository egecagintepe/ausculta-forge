use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc::{channel, RecvTimeoutError};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

#[cfg(windows)]
use std::os::windows::io::AsRawHandle;
#[cfg(windows)]
use std::os::windows::process::CommandExt;
#[cfg(windows)]
use windows_sys::Win32::Foundation::{CloseHandle, HANDLE, INVALID_HANDLE_VALUE};
#[cfg(windows)]
use windows_sys::Win32::System::JobObjects::{
    AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
    SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
};

fn default_schema_version() -> String {
    "1.0.0".to_string()
}
fn default_app_name() -> String {
    "AuscultaForge Desktop".to_string()
}
fn default_version() -> String {
    "0.1.0-alpha.1".to_string()
}
fn default_host() -> String {
    "127.0.0.1".to_string()
}
fn default_status() -> String {
    "ready".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendConfig {
    pub schema_version: String,
    pub app: String,
    pub version: String,
    pub host: String,
    pub port: u16,
    pub auth_token: Option<String>,
    pub pid: u32,
    pub storage_dir: String,
    pub status: String,
    pub http_base_url: String,
    pub ws_url: String,
    pub health_url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HandshakePayload {
    #[serde(default = "default_schema_version")]
    pub schema_version: String,
    #[serde(default = "default_app_name")]
    pub app: String,
    #[serde(default = "default_version")]
    pub version: String,
    #[serde(default = "default_status")]
    pub status: String,
    #[serde(default = "default_host")]
    pub host: String,
    pub port: u16,
    #[serde(default)]
    pub auth_token: Option<String>,
    pub pid: u32,
    #[serde(default)]
    pub storage_dir: Option<String>,
    #[serde(default)]
    pub user_data_dir: Option<String>,
    #[serde(default)]
    pub sessions_dir: Option<String>,
    #[serde(default)]
    pub assets_dir: Option<String>,
    #[serde(default)]
    pub analysis_dir: Option<String>,
    #[serde(default)]
    pub reports_dir: Option<String>,
    #[serde(default)]
    pub logs_dir: Option<String>,
    #[serde(default)]
    pub health_url: Option<String>,
}

impl HandshakePayload {
    pub fn resolved_storage_dir(&self) -> String {
        self.storage_dir
            .clone()
            .or_else(|| self.user_data_dir.clone())
            .unwrap_or_else(|| ".".to_string())
    }
}

pub struct BackendManager {
    child: Option<Child>,
    #[cfg(windows)]
    job_handle: Option<HANDLE>,
    pub config: Option<BackendConfig>,
    pub resource_dir: Option<PathBuf>,
}

// Safety: Windows HANDLE is safe to send between threads when handled properly
unsafe impl Send for BackendManager {}
unsafe impl Sync for BackendManager {}

impl BackendManager {
    pub fn new() -> Self {
        Self {
            child: None,
            #[cfg(windows)]
            job_handle: None,
            config: None,
            resource_dir: None,
        }
    }

    pub fn set_resource_dir(&mut self, dir: Option<PathBuf>) {
        self.resource_dir = dir;
    }

    #[cfg(windows)]
    fn create_job_object() -> Option<HANDLE> {
        unsafe {
            let job = CreateJobObjectW(std::ptr::null_mut(), std::ptr::null());
            if job == std::ptr::null_mut() || job == INVALID_HANDLE_VALUE {
                eprintln!("[Desktop] Warning: Unable to create Windows Job Object");
                return None;
            }

            let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;

            let res = SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                &info as *const _ as *const _,
                std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            );

            if res == 0 {
                eprintln!("[Desktop] Warning: SetInformationJobObject failed");
                CloseHandle(job);
                return None;
            }

            Some(job)
        }
    }

    /// Locate the backend executable with strict resource resolution
    pub fn resolve_backend_command(&self) -> Result<(PathBuf, Vec<String>), String> {
        let current_exe = std::env::current_exe().unwrap_or_default();
        let exe_dir = current_exe.parent().unwrap_or(Path::new(""));

        // Candidate subpaths within resource or exe directories (handles standard NSIS and Tauri bundle layouts)
        let subpaths = [
            PathBuf::from("auscultaforge-backend").join("auscultaforge-backend.exe"),
            PathBuf::from("resources").join("auscultaforge-backend").join("auscultaforge-backend.exe"),
            PathBuf::from("_up_").join("_up_").join("dist_backend").join("auscultaforge-backend").join("auscultaforge-backend.exe"),
            PathBuf::from("_up_").join("dist_backend").join("auscultaforge-backend").join("auscultaforge-backend.exe"),
            PathBuf::from("dist_backend").join("auscultaforge-backend").join("auscultaforge-backend.exe"),
        ];

        // 1. Search in Tauri resource_dir if provided
        if let Some(ref res_dir) = self.resource_dir {
            for sub in &subpaths {
                let candidate = res_dir.join(sub);
                if candidate.exists() {
                    return Ok((candidate, Vec::new()));
                }
            }
        }

        // 2. Search relative to current executable directory
        for sub in &subpaths {
            let candidate = exe_dir.join(sub);
            if candidate.exists() {
                return Ok((candidate, Vec::new()));
            }
        }

        // 3. In development / debug mode ONLY:
        #[cfg(debug_assertions)]
        {
            // Check relative to working directory / source root
            let dev_dist_paths = [
                PathBuf::from("..").join("dist_backend").join("auscultaforge-backend").join("auscultaforge-backend.exe"),
                PathBuf::from("..").join("..").join("dist_backend").join("auscultaforge-backend").join("auscultaforge-backend.exe"),
                PathBuf::from("software").join("dist_backend").join("auscultaforge-backend").join("auscultaforge-backend.exe"),
            ];
            for p in &dev_dist_paths {
                if p.exists() {
                    return Ok((p.clone(), Vec::new()));
                }
            }

            // Virtual environment Python
            let dev_pythons = [
                PathBuf::from("..").join("..").join(".venv").join("Scripts").join("python.exe"),
                PathBuf::from(".venv").join("Scripts").join("python.exe"),
                PathBuf::from("python.exe"),
            ];
            for py in &dev_pythons {
                if py.exists() {
                    return Ok((
                        py.clone(),
                        vec!["-m".to_string(), "pcg_app.desktop_server".to_string()],
                    ));
                }
            }
            return Ok((
                PathBuf::from("python.exe"),
                vec!["-m".to_string(), "pcg_app.desktop_server".to_string()],
            ));
        }

        // 4. In release mode: Do NOT silently fall back to global python!
        #[cfg(not(debug_assertions))]
        {
            Err(format!(
                "Packaged AuscultaForge backend executable could not be found in application resources or installation root.\nResource directory: {:?}\nExecutable directory: {:?}",
                self.resource_dir,
                exe_dir
            ))
        }
    }

    /// Perform a bounded HTTP health check against /api/health before declaring backend ready
    pub fn verify_backend_health(host: &str, port: u16, auth_token: Option<&str>, timeout: Duration) -> Result<(), String> {
        let start = Instant::now();
        let addr_str = format!("{}:{}", host, port);
        let addr = addr_str
            .parse()
            .map_err(|e| format!("Invalid loopback socket address {}: {}", addr_str, e))?;

        while start.elapsed() < timeout {
            if let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(400)) {
                let _ = stream.set_read_timeout(Some(Duration::from_millis(800)));
                let _ = stream.set_write_timeout(Some(Duration::from_millis(800)));

                let mut req = format!(
                    "GET /api/health HTTP/1.1\r\nHost: {}:{}\r\nConnection: close\r\n",
                    host, port
                );
                if let Some(token) = auth_token {
                    req.push_str(&format!("X-AuscultaForge-Auth: {}\r\n", token));
                }
                req.push_str("\r\n");

                if stream.write_all(req.as_bytes()).is_ok() {
                    let mut buf = [0u8; 1024];
                    if let Ok(n) = stream.read(&mut buf) {
                        let resp = String::from_utf8_lossy(&buf[..n]);
                        if resp.contains("200 OK") {
                            return Ok(());
                        }
                    }
                }
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        Err("Backend /api/health did not return 200 OK within timeout".to_string())
    }

    pub fn start(&mut self) -> Result<BackendConfig, String> {
        let (cmd_path, mut initial_args) = self.resolve_backend_command()?;
        let current_pid = std::process::id();

        initial_args.push("--port".to_string());
        initial_args.push("0".to_string());
        initial_args.push("--parent-pid".to_string());
        initial_args.push(current_pid.to_string());

        let mut cmd = Command::new(&cmd_path);
        cmd.args(&initial_args);
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());

        // Set working directory to software root if running Python module
        if initial_args.iter().any(|a| a == "pcg_app.desktop_server") {
            let software_dir = PathBuf::from("..").join("..");
            if software_dir.exists() {
                cmd.current_dir(&software_dir);
            }
        }

        #[cfg(windows)]
        {
            // CREATE_NO_WINDOW = 0x08000000 to prevent flash of console window
            const CREATE_NO_WINDOW: u32 = 0x08000000;
            cmd.creation_flags(CREATE_NO_WINDOW);
        }

        eprintln!("[Desktop] Launching backend: {:?} with args {:?}", cmd_path, initial_args);

        let mut child = cmd.spawn().map_err(|e| {
            format!("Failed to spawn backend process ({:?}): {}", cmd_path, e)
        })?;

        #[cfg(windows)]
        {
            if let Some(job) = Self::create_job_object() {
                let raw_child = child.as_raw_handle() as HANDLE;
                unsafe {
                    let assigned = AssignProcessToJobObject(job, raw_child);
                    if assigned != 0 {
                        eprintln!("[Desktop] Assigned backend child PID {} to Job Object", child.id());
                    } else {
                        eprintln!("[Desktop] Warning: AssignProcessToJobObject returned 0 (fallback to parent PID watchdog)");
                    }
                }
                self.job_handle = Some(job);
            }
        }

        let stdout = child.stdout.take().ok_or("Failed to capture backend stdout")?;
        let stderr = child.stderr.take().ok_or("Failed to capture backend stderr")?;

        // 1. Spawn non-blocking reader thread for stdout
        let (tx_stdout, rx_stdout) = channel::<String>();
        std::thread::Builder::new()
            .name("backend-stdout-reader".into())
            .spawn(move || {
                let reader = BufReader::new(stdout);
                for line in reader.lines() {
                    match line {
                        Ok(l) => {
                            if tx_stdout.send(l).is_err() {
                                break;
                            }
                        }
                        Err(_) => break,
                    }
                }
            })
            .map_err(|e| format!("Failed to spawn stdout reader thread: {}", e))?;

        // 2. Spawn non-blocking drain thread for stderr to prevent pipe buffer deadlock
        let stderr_buffer = Arc::new(Mutex::new(Vec::<String>::new()));
        let stderr_buffer_clone = Arc::clone(&stderr_buffer);
        std::thread::Builder::new()
            .name("backend-stderr-reader".into())
            .spawn(move || {
                let reader = BufReader::new(stderr);
                for line in reader.lines() {
                    match line {
                        Ok(l) => {
                            let mut buf = stderr_buffer_clone.lock().unwrap();
                            if buf.len() < 200 {
                                buf.push(l);
                            }
                        }
                        Err(_) => break,
                    }
                }
            })
            .map_err(|e| format!("Failed to spawn stderr reader thread: {}", e))?;

        // 3. Supervised polling loop with strict 20s timeout and child exit detection
        let start_time = Instant::now();
        let timeout = Duration::from_secs(20);
        let mut captured_lines = Vec::new();
        let mut handshake: Option<BackendConfig> = None;

        while start_time.elapsed() < timeout {
            // Check if child exited prematurely
            if let Ok(Some(status)) = child.try_wait() {
                let err_lines = stderr_buffer.lock().unwrap().join("\n");
                let _ = child.kill();
                let _ = child.wait();
                return Err(format!(
                    "Backend process exited prematurely with status {:?}.\nBackend Stderr:\n{}",
                    status, err_lines
                ));
            }

            // Non-blocking wait for stdout line with 100ms timeout
            match rx_stdout.recv_timeout(Duration::from_millis(100)) {
                Ok(line) => {
                    let trimmed = line.trim();
                    if !trimmed.is_empty() {
                        captured_lines.push(trimmed.to_string());
                    }

                    if let Some(payload_str) = trimmed.strip_prefix("AUSCULTAFORGE_BACKEND_READY:") {
                        match serde_json::from_str::<HandshakePayload>(payload_str) {
                            Ok(payload) => {
                                // Gate 5: Perform real HTTP health check against /api/health
                                let auth_ref = payload.auth_token.as_deref();
                                if let Err(health_err) = Self::verify_backend_health(&payload.host, payload.port, auth_ref, Duration::from_secs(5)) {
                                    let _ = child.kill();
                                    let _ = child.wait();
                                    return Err(format!(
                                        "Backend process bound port {} but health check failed: {}",
                                        payload.port, health_err
                                    ));
                                }

                                let http_base_url = format!("http://{}:{}", payload.host, payload.port);
                                let ws_url = match &payload.auth_token {
                                    Some(token) => format!("ws://{}:{}/ws?token={}", payload.host, payload.port, token),
                                    None => format!("ws://{}:{}/ws", payload.host, payload.port),
                                };
                                let health_url = format!("http://{}:{}/api/health", payload.host, payload.port);

                                eprintln!(
                                    "[Desktop] Backend handshake verified on port {}, PID {}, health OK",
                                    payload.port, payload.pid
                                );

                                let storage_dir = payload.resolved_storage_dir();

                                handshake = Some(BackendConfig {
                                    schema_version: payload.schema_version,
                                    app: payload.app,
                                    version: payload.version,
                                    host: payload.host,
                                    port: payload.port,
                                    auth_token: payload.auth_token,
                                    pid: payload.pid,
                                    storage_dir,
                                    status: "healthy".to_string(),
                                    http_base_url,
                                    ws_url,
                                    health_url,
                                });
                                break;
                            }
                            Err(e) => {
                                eprintln!("[Desktop] Error parsing handshake JSON: {}", e);
                            }
                        }
                    }
                }
                Err(RecvTimeoutError::Timeout) => {
                    // Loop continues, evaluating total elapsed timeout and try_wait
                }
                Err(RecvTimeoutError::Disconnected) => {
                    // Stdout pipe closed
                    std::thread::sleep(Duration::from_millis(50));
                }
            }
        }

        let config = match handshake {
            Some(c) => c,
            None => {
                let _ = child.kill();
                let _ = child.wait();
                let err_lines = stderr_buffer.lock().unwrap().join("\n");
                let stdout_summary = if captured_lines.is_empty() {
                    "(no stdout output captured)".to_string()
                } else {
                    captured_lines.join("\n")
                };
                return Err(format!(
                    "Backend handshake timed out after 20s.\nCaptured Stdout:\n{}\nCaptured Stderr:\n{}",
                    stdout_summary, err_lines
                ));
            }
        };

        self.child = Some(child);
        self.config = Some(config.clone());
        Ok(config)
    }

    pub fn stop(&mut self) {
        if let Some(mut child) = self.child.take() {
            eprintln!("[Desktop] Stopping backend child PID: {}", child.id());
            let _ = child.kill();
            let _ = child.wait();
        }

        #[cfg(windows)]
        {
            if let Some(job) = self.job_handle.take() {
                unsafe {
                    CloseHandle(job);
                }
            }
        }

        self.config = None;
    }
}

impl Drop for BackendManager {
    fn drop(&mut self) {
        self.stop();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_handshake_deserialization_from_actual_python_schema() {
        // Exact JSON format emitted by software/pcg_app/desktop_server.py
        let python_json = r#"{
            "schema_version": "1.0.0",
            "app": "AuscultaForge Desktop",
            "version": "0.1.0-alpha.1",
            "status": "ready",
            "host": "127.0.0.1",
            "port": 58903,
            "auth_token": "8a3c8e7c10b7b6c5d4e3f2a109876543210fedcba9876543210fedcba9876543",
            "pid": 12344,
            "storage_dir": "C:\\Users\\User\\AppData\\Roaming\\AuscultaForge",
            "user_data_dir": "C:\\Users\\User\\AppData\\Roaming\\AuscultaForge",
            "sessions_dir": "C:\\Users\\User\\AppData\\Roaming\\AuscultaForge\\sessions",
            "assets_dir": "C:\\Users\\User\\AppData\\Roaming\\AuscultaForge\\assets",
            "analysis_dir": "C:\\Users\\User\\AppData\\Roaming\\AuscultaForge\\analysis",
            "reports_dir": "C:\\Users\\User\\AppData\\Roaming\\AuscultaForge\\reports",
            "logs_dir": "C:\\Users\\User\\AppData\\Roaming\\AuscultaForge\\logs",
            "health_url": "http://127.0.0.1:58903/api/health"
        }"#;

        let payload: HandshakePayload = serde_json::from_str(python_json)
            .expect("Should deserialize actual Python handshake JSON without error");

        assert_eq!(payload.schema_version, "1.0.0");
        assert_eq!(payload.port, 58903);
        assert_eq!(payload.pid, 12344);
        assert_eq!(payload.resolved_storage_dir(), "C:\\Users\\User\\AppData\\Roaming\\AuscultaForge");
        assert_eq!(payload.status, "ready");
        assert!(payload.auth_token.is_some());
        assert_eq!(payload.auth_token.as_deref(), Some("8a3c8e7c10b7b6c5d4e3f2a109876543210fedcba9876543210fedcba9876543"));
    }

    #[test]
    fn test_handshake_deserialization_with_alias_and_null_token() {
        // Test fallback where only user_data_dir is present and auth_token is null
        let payload_json = r#"{
            "port": 50123,
            "pid": 9999,
            "user_data_dir": "C:\\AppData\\AuscultaForge",
            "auth_token": null
        }"#;

        let payload: HandshakePayload = serde_json::from_str(payload_json)
            .expect("Should deserialize payload using user_data_dir alias and null auth_token");

        assert_eq!(payload.port, 50123);
        assert_eq!(payload.pid, 9999);
        assert_eq!(payload.resolved_storage_dir(), "C:\\AppData\\AuscultaForge");
        assert_eq!(payload.schema_version, "1.0.0");
        assert_eq!(payload.auth_token, None);
    }

    #[test]
    fn test_handshake_malformed_json_rejected() {
        let malformed = "{ port: 58903, unquoted: true }";
        let res: Result<HandshakePayload, _> = serde_json::from_str(malformed);
        assert!(res.is_err(), "Malformed JSON must fail deserialization cleanly");
    }

    #[test]
    fn test_handshake_missing_required_port_rejected() {
        let incomplete = r#"{"pid": 1234, "storage_dir": "C:\\Data"}"#;
        let res: Result<HandshakePayload, _> = serde_json::from_str(incomplete);
        assert!(res.is_err(), "Missing port must fail deserialization");
    }

    #[test]
    fn test_handshake_deserialization_from_actual_python_process_execution() {
        let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let workspace_root = manifest_dir
            .parent().unwrap()
            .parent().unwrap()
            .parent().unwrap();

        let venv_python = if cfg!(windows) {
            workspace_root.join(".venv").join("Scripts").join("python.exe")
        } else {
            workspace_root.join(".venv").join("bin").join("python")
        };

        let python_cmd = if venv_python.exists() {
            venv_python
        } else {
            PathBuf::from("python")
        };

        let script_path = workspace_root.join("software").join("pcg_app").join("desktop_server.py");
        assert!(script_path.exists(), "desktop_server.py must exist at {:?}", script_path);

        let output = Command::new(&python_cmd)
            .current_dir(&workspace_root)
            .args(&[
                script_path.to_str().unwrap(),
                "--print-handshake",
                "--port",
                "59123",
                "--host",
                "127.0.0.1",
            ])
            .output();

        match output {
            Ok(out) => {
                assert!(out.status.success(), "Python execution failed: {:?}", String::from_utf8_lossy(&out.stderr));
                let stdout_str = String::from_utf8_lossy(&out.stdout);
                let ready_line = stdout_str
                    .lines()
                    .find(|line| line.starts_with("AUSCULTAFORGE_BACKEND_READY:"))
                    .expect("Output must contain AUSCULTAFORGE_BACKEND_READY header");

                let json_str = &ready_line["AUSCULTAFORGE_BACKEND_READY:".len()..];
                let payload: HandshakePayload = serde_json::from_str(json_str)
                    .expect("Rust HandshakePayload must deserialize the live Python output");

                assert_eq!(payload.schema_version, "1.0.0");
                assert_eq!(payload.port, 59123);
                assert_eq!(payload.host, "127.0.0.1");
                assert_eq!(payload.status, "ready");
                assert!(payload.pid > 0);
                assert!(!payload.resolved_storage_dir().is_empty());
                assert!(payload.auth_token.is_some());
                assert_eq!(payload.auth_token.as_ref().unwrap().len(), 64);
            }
            Err(e) => {
                eprintln!("Skipping live python process test (python not available): {}", e);
            }
        }
    }

    #[test]
    fn test_resolve_backend_command_succeeds_in_dev_workspace() {
        let mgr = BackendManager::new();
        let res = mgr.resolve_backend_command();
        assert!(res.is_ok(), "Backend resolution must succeed in workspace: {:?}", res.err());
        let (cmd, args) = res.unwrap();
        assert!(cmd.exists() || cmd.to_str().unwrap() == "python.exe", "Resolved binary or command must exist: {:?}", cmd);
        eprintln!("[Test] Resolved backend command: {:?} {:?}", cmd, args);
    }
}
