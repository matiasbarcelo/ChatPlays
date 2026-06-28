import { useState, useEffect } from "react";
import logo from "@assets/logo.png";
import anarchyLogo from "@assets/anarchy.png";
import democracyLogo from "@assets/democracy.png";
import { api } from "./api";
import { useChatPlaysState } from "./hooks/useChatPlaysState";
import { openSetupWindow } from "./openSetupWindow";
import { KeyBindTable } from "./SetupApp";
import { InfoIcon } from "./components/InfoIcon";
import { EmulatorDetectField } from "./components/EmulatorDetectField";

function TwitchIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 28" fill="#9146ff" xmlns="http://www.w3.org/2000/svg">
      <path d="M2.149 0L0 6.5V24h6v4h3.5L13 24h4.5L24 17.5V0H2.149zM21 16.5L17 20.5h-4.5L9 24v-3.5H4V3h17v13.5z"/>
      <rect x="11" y="7" width="2.5" height="6" rx="1"/>
      <rect x="16" y="7" width="2.5" height="6" rx="1"/>
    </svg>
  );
}

export function MainApp() {
  const { ready, main, setup } = useChatPlaysState("main");
  const [copied, setCopied] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [emulatorScanning, setEmulatorScanning] = useState(false);
  const [globalTheme, setGlobalTheme] = useState(
    () => localStorage.getItem("chatplays-theme") || "light"
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", globalTheme);
  }, [globalTheme]);

  useEffect(() => {
    if (!ready) return;
    api.scanMainEmulator().catch(() => {});
  }, [ready]);

  const scanEmulator = () => {
    setEmulatorScanning(true);
    api
      .scanMainEmulator()
      .catch(() => {})
      .finally(() => setEmulatorScanning(false));
  };

  const applyTheme = (t) => {
    setGlobalTheme(t);
    localStorage.setItem("chatplays-theme", t);
  };

  if (!ready || !main) {
    return <div className="main-shell muted">Connecting to ChatPlays…</div>;
  }

  const isOn = main.program_status;
  const gov = main.government || "anarchy";
  const overlayUrl = "http://127.0.0.1:8765/overlay";

  const copyUrl = () => {
    navigator.clipboard.writeText(overlayUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <div className="main-shell">
      <img src={logo} alt="ChatPlays" className="main-logo" />

      <label className="col main-field">
        <span className="main-field-label">Streaming Platform</span>
        <div className="main-select-wrapper">
          <TwitchIcon size={18} />
          <select
            value={main.streaming_platform || "twitch"}
            onChange={(e) => api.updateMainSettings({ streaming_platform: e.target.value })}
          >
            <option value="twitch">twitch.tv</option>
          </select>
        </div>
      </label>

      <label className="col main-field">
        <span className="main-field-label">Username</span>
        <input
          defaultValue={main.twitch_username}
          placeholder="Username"
          onBlur={(e) => api.updateMainSettings({ twitch_username: e.target.value })}
        />
      </label>

      <div className="col main-field">
        <span className="main-field-label">
          OAuth Key
          <InfoIcon
            tip="Click to get your Twitch chat token at twitchtokengenerator.com (select chat:read + chat:edit)"
            onClick={() => window.open("https://twitchtokengenerator.com/?scope=chat:read+chat:edit", "_blank")}
          />
        </span>
        <input
          type="password"
          defaultValue={main.oauth_key}
          placeholder="oauth:..."
          autoComplete="off"
          onBlur={(e) => api.updateMainSettings({ oauth_key: e.target.value })}
        />
      </div>

      <div className="col main-field">
        <span className="main-field-label">Game/Emulator</span>
        <EmulatorDetectField
          windowOptions={main.emulator_window_options || []}
          windows={main.emulator_windows || []}
          selectedWindow={main.emulator_window}
          message={main.emulator_message}
          executablePath={main.emulator_executable_path}
          appName={main.emulator_app_name || "visualboyadvance-m.exe"}
          onScan={scanEmulator}
          onSelectWindow={(window) => api.selectMainEmulatorWindow(window).catch(() => {})}
          onListOtherWindows={async () => {
            const result = await api.listWindows();
            return result.windows || [];
          }}
          scanning={emulatorScanning}
        />
      </div>

      <div className="main-field">
        <span className="main-field-label main-field-label--center">
          {gov === "anarchy" ? "Anarchy" : "Democracy"}
        </span>
        <div className="main-gov-row">
          <img src={democracyLogo} alt="Democracy" className="main-gov-icon main-gov-icon--democracy" />
          <input
            type="range"
            className="main-gov-slider"
            min={0}
            max={100}
            step={100}
            value={gov === "anarchy" ? 100 : 0}
            onChange={(e) => {
              const next = Number(e.target.value) === 100 ? "anarchy" : "democracy";
              api.updateMainSettings({ government: next });
            }}
          />
          <img src={anarchyLogo} alt="Anarchy" className="main-gov-icon" />
        </div>
      </div>

      <div className="main-bottom-row">
        <div className="col main-power-col">
          <span className="main-field-label">Chatplays is</span>
          <button
            type="button"
            className={`power-btn${isOn ? " power-btn--on" : " power-btn--off"}`}
            onClick={() => api.togglePower()}
            title={isOn ? "Turn off" : "Turn on"}
          >
            <div className="power-btn__ring">
              <span className="icon power-btn__icon" style={{ fontSize: 52, lineHeight: 1 }}>power_settings_new</span>
            </div>
          </button>
          <span className={isOn ? "status-on" : "status-off"} style={{ fontSize: "1.3rem", fontWeight: 700 }}>
            {isOn ? "ON" : "OFF"}
          </span>
        </div>

        <div className="col main-overlay-col">
          <span className="main-field-label">Chat Overlay</span>

          <div className="main-overlay-grid">
            <button type="button" className="main-overlay-btn" onClick={copyUrl} title={overlayUrl}>
              <span className="main-overlay-btn__text">
                {overlayUrl.replace("http://", "").slice(0, 15) + "…"}
              </span>
              <span className="icon main-overlay-btn__icon">
                {copied ? "check" : "content_copy"}
              </span>
            </button>
            <InfoIcon tip="Browser source URL for OBS — overlay endpoint not yet implemented" />

            <button
              type="button"
              className="main-overlay-btn"
              onClick={() => {
                if (window.chatplays?.openMonitorWindow) {
                  window.chatplays.openMonitorWindow();
                } else {
                  const monitorUrl = window.location.origin + "/monitor.html";
                  window.open(monitorUrl, "chatmonitor", "width=520,height=680,menubar=no,toolbar=no,resizable=yes");
                }
              }}
            >
              <span className="main-overlay-btn__text">Chat Monitor</span>
              <span className="icon main-overlay-btn__icon">monitor</span>
            </button>
            <InfoIcon tip="Live view of the running chat — separate from the Setup/Test window" />

            <button type="button" className="main-overlay-btn" onClick={() => openSetupWindow()}>
              <span className="main-overlay-btn__text">Setup / Test</span>
              <span className="icon main-overlay-btn__icon">open_in_new</span>
            </button>
            <InfoIcon tip="Configure inputs and test things out while the app is running" />
          </div>
        </div>
      </div>

      <div className="main-settings-row">
        <button type="button" className="main-settings-link" onClick={() => setSettingsOpen(true)}>
          <span className="icon" style={{ fontSize: 18 }}>settings</span>
          settings
        </button>
      </div>

      {settingsOpen && (
        <div className="settings-dialog-backdrop" onClick={() => setSettingsOpen(false)}>
          <div className="settings-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="settings-dialog__header">
              <strong style={{ fontSize: "1.1rem" }}>Settings</strong>
              <button
                type="button"
                className="settings-dialog__close"
                onClick={() => setSettingsOpen(false)}
              >
                ✕
              </button>
            </div>

            <div className="settings-dialog__body">
            <label className="col">
              App Theme
              <div className="theme-toggle-row">
                <button
                  type="button"
                  className={`theme-toggle-btn theme-toggle-btn--light${globalTheme === "light" ? " theme-toggle-btn--active" : ""}`}
                  onClick={() => applyTheme("light")}
                >
                  Light
                </button>
                <button
                  type="button"
                  className={`theme-toggle-btn theme-toggle-btn--dark${globalTheme === "dark" ? " theme-toggle-btn--active" : ""}`}
                  onClick={() => applyTheme("dark")}
                >
                  Dark
                </button>
              </div>
            </label>

            {setup && (
              <label className="col">
                Controller
                <select
                  value={setup.controller}
                  onChange={(e) => api.updateSetupSettings({ controller: e.target.value })}
                >
                  <option value="GBA">GBA</option>
                  <option value="Xbox 360">Xbox 360</option>
                  <option value="PlayStation">PlayStation</option>
                </select>
              </label>
            )}

            {setup?.keyboard_map && Object.keys(setup.keyboard_map).length > 0 && (
              <KeyBindTable
                keyMap={setup.keyboard_map}
                disabledInputs={setup.disabled_inputs || []}
                bindingMode={setup.binding_mode || "keyboard"}
                virtualInputOptions={setup.virtual_input_options || []}
              />
            )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
