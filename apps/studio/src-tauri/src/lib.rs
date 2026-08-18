use std::sync::Mutex;
use tauri::{path::BaseDirectory, Manager, RunEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

const KEYRING_SERVICE: &str = "com.inupedia.hydropilot";
struct ApiProcess(Mutex<Option<CommandChild>>);

fn validate_secret_name(name: &str) -> Result<(), String> {
    if name.is_empty() || name.len() > 160 || !name.chars().all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, ':' | '.' | '_' | '-')) {
        return Err("invalid secret name".into());
    }
    Ok(())
}
fn keyring_entry(name: &str) -> Result<keyring::Entry, String> {
    validate_secret_name(name)?;
    keyring::Entry::new(KEYRING_SERVICE, name).map_err(|error| error.to_string())
}
#[tauri::command]
fn secret_get(name: String) -> Result<Option<String>, String> {
    let entry = keyring_entry(&name)?;
    match entry.get_password() { Ok(value) => Ok(Some(value)), Err(keyring::Error::NoEntry) => Ok(None), Err(error) => Err(error.to_string()) }
}
#[tauri::command]
fn secret_set(name: String, value: String) -> Result<(), String> {
    if value.trim().is_empty() { return Err("secret value is required".into()); }
    keyring_entry(&name)?.set_password(value.trim()).map_err(|error| error.to_string())
}
#[tauri::command]
fn secret_remove(name: String) -> Result<(), String> {
    let entry = keyring_entry(&name)?;
    match entry.delete_credential() { Ok(()) | Err(keyring::Error::NoEntry) => Ok(()), Err(error) => Err(error.to_string()) }
}
fn start_packaged_api(app: &tauri::App) -> Result<CommandChild, String> {
    let fixture = app.path().resolve("data/demo/sacramento_v0_1.json", BaseDirectory::Resource).map_err(|error| error.to_string())?;
    let command = app.shell().sidecar("hydropilot-api").map_err(|error| error.to_string())?
        .env("HYDROPILOT_API_HOST", "127.0.0.1")
        .env("HYDROPILOT_API_PORT", "8000")
        .env("HYDROPILOT_DEMO_FIXTURE_PATH", fixture.to_string_lossy().to_string());
    let (_events, child) = command.spawn().map_err(|error| error.to_string())?;
    Ok(child)
}
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![secret_get, secret_set, secret_remove])
        .setup(|app| {
            let child = if cfg!(debug_assertions) { None } else { Some(start_packaged_api(app)?) };
            app.manage(ApiProcess(Mutex::new(child)));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building HydroPilot");
    app.run(|handle, event| {
        if matches!(event, RunEvent::Exit) {
            if let Some(state) = handle.try_state::<ApiProcess>() {
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(child) = guard.take() { let _ = child.kill(); }
                }
            }
        }
    });
}
