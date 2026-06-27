import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { useChatPlaysState } from "./hooks/useChatPlaysState";
import { ControllerPanel } from "./components/ControllerPanel";
import { AnarchyPanel, DemocracyPanel } from "./components/GovPanels";
import { closeSetupWindow } from "./openSetupWindow";

function keyEventToString(event) {
  const { key, code } = event;
  if (key === "Escape") return null;
  const specials = {
    ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right",
    Enter: "enter", Backspace: "backspace", Tab: "tab", " ": "space", Escape: "escape",
  };
  if (specials[key]) return specials[key];
  if (key.length === 1) return key.toLowerCase();
  // function keys, etc.
  const fMatch = code.match(/^Key([A-Z])$/);
  if (fMatch) return fMatch[1].toLowerCase();
  return key.toLowerCase();
}

function KeyBindTable({ keyMap, disabledInputs = [] }) {
  const [capturing, setCapturing] = useState(null);
  const rowRef = useRef(null);

  useEffect(() => {
    if (!capturing) return;
    function onKey(event) {
      event.preventDefault();
      event.stopPropagation();
      const keyStr = keyEventToString(event);
      if (keyStr) {
        api.updateKeyBinding(capturing, keyStr).catch(() => {});
      }
      setCapturing(null);
    }
    window.addEventListener("keydown", onKey, { capture: true });
    return () => window.removeEventListener("keydown", onKey, { capture: true });
  }, [capturing]);

  return (
    <div className="col">
      <span style={{ fontWeight: 600 }}>Mac Key Bindings</span>
      <table className="keybind-table" ref={rowRef}>
        <thead>
          <tr>
            <th>
              <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                Button
                <span className="keybind-info-icon">
                  i
                  <span className="keybind-tooltip">double click to disable</span>
                </span>
              </span>
            </th>
            <th>
              <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                Key
                <span className="keybind-info-icon">
                  i
                  <span className="keybind-tooltip">click a key to rebind it</span>
                </span>
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(keyMap).map(([input, key]) => {
            const isDisabled = disabledInputs.includes(input);
            return (
              <tr
                key={input}
                className={isDisabled ? "keybind-row--disabled" : ""}
              >
                <td
                  className="keybind-btn-cell"
                  onDoubleClick={() => api.toggleDisabledInput(input).catch(() => {})}
                >{input}</td>
                <td>
                  <button
                    type="button"
                    className={`keybind-cell${capturing === input ? " keybind-cell--capturing" : ""}`}
                    onClick={() => setCapturing(capturing === input ? null : input)}
                  >
                    {capturing === input ? "Press a key…" : key}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function SetupApp() {
  const { ready, setup } = useChatPlaysState("setup");
  const [demMinutes, setDemMinutes] = useState(null);
  const [demSeconds, setDemSeconds] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [linkFlash, setLinkFlash] = useState("");
  const [chatTheme, setChatTheme] = useState("dark");
  const [globalTheme, setGlobalTheme] = useState("light");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", globalTheme);
  }, [globalTheme]);

  const minutes = demMinutes ?? setup?.democracy_minutes ?? 0;
  const seconds = demSeconds ?? setup?.democracy_seconds ?? 15;

  useEffect(() => {
    if (!ready || setup?.setup_link_mode !== "automatic" || setup?.controller !== "GBA") {
      return;
    }
    api.scanEmulator().catch(() => {});
  }, [ready, setup?.setup_link_mode, setup?.controller, setup?.setup_emulator]);

  useEffect(() => {
    if (!setup?.auto_link_status) return;
    setLinkFlash(setup.auto_link_status);
    const timer = setTimeout(() => setLinkFlash(""), 8000);
    return () => clearTimeout(timer);
  }, [setup?.auto_link_status]);

  if (!ready || !setup) {
    return <div className="panel muted" style={{ padding: 24 }}>Connecting to ChatPlays backend…</div>;
  }

  const pushSettings = (payload) => api.updateSetupSettings(payload);

  return (
    <div className="setup-shell panel">
      <header className="setup-topbar">
        <button type="button" className="setup-back-btn" onClick={() => closeSetupWindow()}>
          ← Back
        </button>
        <span className="setup-topbar__title muted">Test / Setup</span>
        <button type="button" onClick={() => setSettingsOpen(true)}>
          Settings
        </button>
      </header>

      <div className="setup-layout">
      <div className="card setup-layout__settings">
        <div className="row" style={{ alignItems: "flex-start" }}>
          <div className="col" style={{ flex: 1, alignSelf: "stretch" }}>
            <label className="col">
              Setup or Test?
              <select
                value={setup.meta_mode}
                onChange={(event) => pushSettings({ meta_mode: event.target.value })}
              >
                <option value="setup">Setup</option>
                <option value="test">Test</option>
              </select>
            </label>
            <label className="col">
              Controller link
              <select
                value={setup.setup_link_mode || "manual"}
                onChange={(event) =>
                  pushSettings({ setup_link_mode: event.target.value })
                }
              >
                <option value="manual">Manual</option>
                <option value="automatic">Automatic</option>
              </select>
            </label>

            {setup.setup_link_mode === "automatic" && (
              <label className="col">
                Emulator
                <select
                  value={setup.setup_emulator || "visualboyadvance"}
                  onChange={(event) =>
                    pushSettings({ setup_emulator: event.target.value })
                  }
                >
                  <option value="visualboyadvance">Visual Boy Advance</option>
                </select>
              </label>
            )}

            {setup.setup_link_mode === "manual" && (
              <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 6 }}>
                <button
                  type="button"
                  disabled={setup.manual_setup_active}
                  onClick={() => api.manualSetup()}
                >
                  Start Manual Setup
                </button>
                {setup.manual_setup_active && (
                  <button type="button" onClick={() => api.cancelManualSetup()}>
                    Cancel
                  </button>
                )}
              </div>
            )}
          </div>
          <div className="col" style={{ flex: 1 }}>
            <label className="col">
              Government
              <select
                value={setup.government}
                onChange={(event) => pushSettings({ government: event.target.value })}
              >
                <option value="anarchy">Anarchy</option>
                <option value="democracy">Democracy</option>
              </select>
            </label>
            <label className="col">
              Controller
              <select
                value={setup.controller}
                onChange={(event) => pushSettings({ controller: event.target.value })}
              >
                <option value="GBA">GBA</option>
                <option value="Xbox 360">Xbox 360</option>
                <option value="PlayStation">PlayStation</option>
              </select>
            </label>
            <label className="col">
              Setup countdown (seconds)
              <input
                type="number"
                min={0}
                value={setup.countdown_seconds}
                onChange={(event) =>
                  pushSettings({ countdown_seconds: Number(event.target.value) || 0 })
                }
              />
            </label>
          </div>
        </div>

        {setup.meta_mode === "test" ? (
          <div className="setup-link-content timing-row" style={{ flexDirection: "row", flexWrap: "nowrap" }}>
            {[
              ["tap", setup.tap_time],
              ["press", setup.press_time],
              ["hold", setup.hold_time],
            ].map(([name, value]) => (
              <label key={name} className="timing-group">
                <input
                  type="radio"
                  name="defaultTime"
                  checked={setup.default_time_length === name}
                  onChange={() =>
                    pushSettings({
                      tap_time: setup.tap_time,
                      press_time: setup.press_time,
                      hold_time: setup.hold_time,
                      default_time_length: name,
                    })
                  }
                />
                <span className="pixel" style={{ textTransform: "capitalize" }}>
                  {name}
                </span>
                <input
                  type="number"
                  step="0.1"
                  value={value}
                  onChange={(event) => {
                    const numeric = Number(event.target.value) || 0;
                    pushSettings({
                      tap_time: name === "tap" ? numeric : setup.tap_time,
                      press_time: name === "press" ? numeric : setup.press_time,
                      hold_time: name === "hold" ? numeric : setup.hold_time,
                      default_time_length: setup.default_time_length,
                    });
                  }}
                />
              </label>
            ))}
          </div>
        ) : (
          setup.setup_link_mode === "automatic" && (
            <div className="setup-link-content">
              <div className="setup-emulator-panel__status">
                {setup.emulator_detected ? (
                  <>
                    <strong>{setup.emulator_name}</strong>
                    <span className="muted">Window: {setup.emulator_window}</span>
                  </>
                ) : (
                  <span className="muted">
                    VisualBoy Advance-M is not running. Link will launch it and open joypad settings.
                  </span>
                )}
                {setup.emulator_message && setup.emulator_detected && (
                  <span className="muted">{setup.emulator_message}</span>
                )}
              </div>
              <button
                type="button"
                onClick={() => api.autoLinkEmulator()}
              >
                Link with Emulator
              </button>
            </div>
          )
        )}
      </div>

      <div className="card setup-layout__controller">
        <ControllerPanel
            controller={setup.controller}
            buttonMap={setup.button_map}
            highlightInput={setup.manual_setup_current_input}
            disabledInputs={setup.disabled_inputs || []}
            onButtonPress={(inputName) => api.controllerButton(inputName)}
          />
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

            <label className="col">
              App Theme
              <div className="theme-toggle-row">
                <button
                  type="button"
                  className={`theme-toggle-btn theme-toggle-btn--light${globalTheme === "light" ? " theme-toggle-btn--active" : ""}`}
                  onClick={() => setGlobalTheme("light")}
                >
                  Light
                </button>
                <button
                  type="button"
                  className={`theme-toggle-btn theme-toggle-btn--dark${globalTheme === "dark" ? " theme-toggle-btn--active" : ""}`}
                  onClick={() => setGlobalTheme("dark")}
                >
                  Dark
                </button>
              </div>
            </label>

            <label className="col">
              Controller
              <select
                value={setup.controller}
                onChange={(e) => pushSettings({ controller: e.target.value })}
              >
                <option value="GBA">GBA</option>
                <option value="Xbox 360">Xbox 360</option>
                <option value="PlayStation">PlayStation</option>
              </select>
            </label>

            {setup.keyboard_map && Object.keys(setup.keyboard_map).length > 0 && (
              <KeyBindTable keyMap={setup.keyboard_map} disabledInputs={setup.disabled_inputs || []} />
            )}
          </div>
        </div>
      )}

      <section className="setup-layout__chat">
        {setup.government === "anarchy" ? (
          <AnarchyPanel
            queue={setup.anarchy_queue}
            countdownLine={setup.setup_countdown_line}
            flashLine={linkFlash}
            onSubmit={(text) => api.submitInput(text)}
            chatTheme={chatTheme}
            onThemeToggle={() => setChatTheme(t => t === "dark" ? "light" : "dark")}
          />
        ) : (
          <DemocracyPanel
            queue={setup.democracy_queue}
            countdownLine={setup.setup_countdown_line}
            flashLine={linkFlash}
            voteSlots={setup.vote_slots}
            countdownLabel={setup.democracy_countdown_label}
            latestWinner={setup.latest_winner}
            minutes={minutes}
            seconds={seconds}
            timerRunning={setup.democracy_timer_running}
            onSubmit={(text) => api.submitInput(text)}
            onMinutesChange={setDemMinutes}
            onSecondsChange={setDemSeconds}
            onUpdateTime={() =>
              pushSettings({ democracy_minutes: minutes, democracy_seconds: seconds })
            }
            onToggleTimer={() => api.toggleDemocracyTimer()}
            chatTheme={chatTheme}
            onThemeToggle={() => setChatTheme(t => t === "dark" ? "light" : "dark")}
          />
        )}

      </section>
      </div>
    </div>
  );
}
