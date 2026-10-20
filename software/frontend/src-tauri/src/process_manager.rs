use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendConfig {
    pub port: u16,
    pub auth_token: String,
    pub pid: u32,
    pub storage_dir: String,
    pub status: String,
    pub http_base_url: String,
    pub ws_url: String,
}

#[derive(Debug, Deserialize)]
struct HandshakePayload {
    port: u16,
    auth_token: String,
    pid: u32,
    storage_dir: String,
    status: String,
}

pub struct BackendManager {
    child: Option<Child>,
    #[cfg(windows)]
    job_handle: Option<HANDLE>,
    pub config: Option<BackendConfig>,
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
        }
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

    /// Locate the backend executable or fallback to Python dev environment
    fn resolve_backend_command() -> Result<(PathBuf, Vec<String>), String> {
        let current_exe = std::env::current_exe().unwrap_or_default();
        let exe_dir = current_exe.parent().unwrap_or(Path::new(""));

        // 1. Check relative to current exe (Packaged production installation)
        let candidate_bundled = exe_dir.join("auscultaforge-backend").join("auscultaforge-backend.exe");
        if candidate_bundled.exists() {
            return Ok((candidate_bundled, Vec::new()));
        }

        // 2. Check resources directory in Tauri package
        let candidate_resource = exe_dir.join("resources").join("auscultaforge-backend").join("auscultaforge-backend.exe");
        if candidate_resource.exists() {
            return Ok((candidate_resource, Vec::new()));
        }

        // 3. Check workspace dist_backend folder (Local dev/build workspace)
        let candidate_dist = PathBuf::from("..")
            .join("dist_backend")
            .join("auscultaforge-backend")
            .join("auscultaforge-backend.exe");
        if candidate_dist.exists() {
            return Ok((candidate_dist, Vec::new()));
        }

        // 4. Also check two levels up (for target/debug/ execution)
        let candidate_dist_up = PathBuf::from("..")
            .join("..")
            .join("dist_backend")
            .join("auscultaforge-backend")
            .join("auscultaforge-backend.exe");
        if candidate_dist_up.exists() {
            return Ok((candidate_dist_up, Vec::new()));
        }

        // 5. Fallback: Python interpreter with pcg_app.desktop_server module
        let venv_python = PathBuf::from("..").join("..").join(".venv").join("Scripts").join("python.exe");
        if venv_python.exists() {
            return Ok((
                venv_python,
                vec!["-m".to_string(), "pcg_app.desktop_server".to_string()],
            ));
        }

        let sys_python = PathBuf::from("python.exe");
        Ok((
            sys_python,
            vec!["-m".to_string(), "pcg_app.desktop_server".to_string()],
        ))
    }

    pub fn start(&mut self) -> Result<BackendConfig, String> {
        let (cmd_path, mut initial_args) = Self::resolve_backend_command()?;
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
                        eprintln!("[Desktop] Warning: AssignProcessToJobObject returned 0");
                    }
                }
                self.job_handle = Some(job);
            }
        }

        let stdout = child.stdout.take().ok_or("Failed to capture backend stdout")?;
        let stderr = child.stderr.take();

        // Read stdout line by line until handshake line is found
        let mut reader = BufReader::new(stdout);
        let start_time = Instant::now();
        let timeout = Duration::from_secs(20);
        let mut handshake: Option<BackendConfig> = None;

        let mut captured_lines = Vec::new();

        while start_time.elapsed() < timeout {
            // Check if child exited prematurely
            if let Ok(Some(status)) = child.try_wait() {
                let mut err_msg = format!("Backend exited prematurely with status: {:?}", status);
                if let Some(mut err_pipe) = stderr {
                    use std::io::Read;
                    let mut err_str = String::new();
                    let _ = err_pipe.read_to_string(&mut err_str);
                    if !err_str.trim().is_empty() {
                        err_msg.push_str(&format!("\nBackend Stderr:\n{}", err_str));
                    }
                }
                return Err(err_msg);
            }

            let mut line = String::new();
            match reader.read_line(&mut line) {
                Ok(0) => {
                    // EOF reached
                    std::thread::sleep(Duration::from_millis(50));
                }
                Ok(_) => {
                    let trimmed = line.trim();
                    captured_lines.push(trimmed.to_string());
                    if let Some(payload_str) = trimmed.strip_prefix("AUSCULTAFORGE_BACKEND_READY:") {
                        match serde_json::from_str::<HandshakePayload>(payload_str) {
                            Ok(payload) => {
                                let http_base_url = format!("http://127.0.0.1:{}", payload.port);
                                let ws_url = format!("ws://127.0.0.1:{}/ws?token={}", payload.port, payload.auth_token);
                                handshake = Some(BackendConfig {
                                    port: payload.port,
                                    auth_token: payload.auth_token,
                                    pid: payload.pid,
                                    storage_dir: payload.storage_dir,
                                    status: payload.status,
                                    http_base_url,
                                    ws_url,
                                });
                                break;
                            }
                            Err(e) => {
                                eprintln!("[Desktop] Error parsing handshake JSON: {}", e);
                            }
                        }
                    }
                }
                Err(_) => {
                    std::thread::sleep(Duration::from_millis(50));
                }
            }
        }

        let config = handshake.ok_or_else(|| {
            format!(
                "Backend handshake timed out after 20s. Captured output:\n{}",
                captured_lines.join("\n")
            )
        })?;

        eprintln!(
            "[Desktop] Backend successfully bound to port {}, PID {}",
            config.port, config.pid
        );

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
