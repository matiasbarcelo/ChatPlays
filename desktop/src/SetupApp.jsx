import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { useChatPlaysState } from "./hooks/useChatPlaysState";
import { ControllerPanel } from "./components/ControllerPanel";
import { InfoIcon } from "./components/InfoIcon";
import { VirtualInputCombobox } from "./components/VirtualInputCombobox";
import { AnarchyPanel, DemocracyPanel } from "./components/GovPanels";
import { EmulatorDetectField } from "./components/EmulatorDetectField";
import { closeSetupWindow } from "./openSetupWindow";

const VIGEM_BUS_DOCS_URL = "https://github.com/ViGEm/ViGEmBus";

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

export function KeyBindTable({
  keyMap,
  disabledInputs = [],
  bindingMode = "keyboard",
  virtualInputOptions = [],
}) {
  const isVirtual = bindingMode === "virtual";
  const [capturing, setCapturing] = useState(null);
  const rowRef = useRef(null);

  useEffect(() => {
    if (isVirtual || !capturing) return;
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
  }, [capturing, isVirtual]);

  const commitVirtualInput = (input, value) => {
    if (!value || value === keyMap[input]) return;
    api.updateKeyBinding(input, value).catch(() => {});
  };

  const handleReset = () => {
    if (!isVirtual) return;
    api.resetVirtualBindings().catch(() => {});
  };

  return (
    <div className="col keybind-table-wrap">
      <div className="keybind-table-toolbar">
        <span style={{ fontWeight: 600 }}>
          {isVirtual ? "Virtual Controller Bindings" : "Mac Key Bindings"}
        </span>
        {isVirtual && (
          <button type="button" className="keybind-reset-btn" onClick={handleReset}>
            Reset to defaults
          </button>
        )}
      </div>
      <div className="keybind-table-frame">
        <table className="keybind-table keybind-table--head">
          <colgroup>
            <col className="keybind-table__col-btn" />
            <col className="keybind-table__col-input" />
          </colgroup>
          <thead>
            <tr>
              <th>
                <span className="keybind-table__th-label">
                  Button
                  <InfoIcon tip="Double click to disable" fixedOnHover />
                </span>
              </th>
              <th>
                <span className="keybind-table__th-label">
                  {isVirtual ? "Virtual input" : "Key"}
                  {isVirtual ? (
                    <InfoIcon
                      href={VIGEM_BUS_DOCS_URL}
                      tip="Click here for documentation and available inputs."
                      fixedOnHover
                    />
                  ) : (
                    <InfoIcon tip="Click a key to rebind it" fixedOnHover />
                  )}
                </span>
              </th>
            </tr>
          </thead>
        </table>
        <div className="keybind-table-scroll">
          <table className="keybind-table keybind-table--body" ref={rowRef}>
            <colgroup>
              <col className="keybind-table__col-btn" />
              <col className="keybind-table__col-input" />
            </colgroup>
            <tbody>
          {Object.entries(keyMap).map(([input, binding]) => {
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
                  {isVirtual ? (
                    <VirtualInputCombobox
                      value={binding}
                      options={virtualInputOptions}
                      disabled={isDisabled}
                      onCommit={(value) => commitVirtualInput(input, value)}
                    />
                  ) : (
                    <button
                      type="button"
                      className={`keybind-cell${capturing === input ? " keybind-cell--capturing" : ""}`}
                      onClick={() => setCapturing(capturing === input ? null : input)}
                    >
                      {capturing === input ? "Press a key…" : binding}
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const IS_WIN = /win/i.test(navigator.platform);
const COMMANDS_LIST_URL = "http://127.0.0.1:8765/commands";

function getAvailableChatInputs(buttonMap, disabledInputs = []) {
  const disabled = new Set(disabledInputs);
  return [...new Set(Object.values(buttonMap || {}))]
    .filter((name) => name && !disabled.has(name))
    .sort((a, b) => a.localeCompare(b));
}

function formatInputsForClipboard(inputs) {
  const list = inputs.join(", ");
  return `Available chat inputs: ${list}\n!commands ${list}`;
}

async function copyToClipboard(text, setCopied) {
  try {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  } catch {
    /* clipboard unavailable */
  }
}

function SetupControllerFooter({ buttonMap, disabledInputs = [] }) {
  const [copiedInputs, setCopiedInputs] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const inputs = getAvailableChatInputs(buttonMap, disabledInputs);
  const inputsText = formatInputsForClipboard(inputs);
  const urlLabel = `${COMMANDS_LIST_URL.replace("http://", "").slice(0, 18)}…`;

  return (
    <div className="setup-controller-footer">
      <button
        type="button"
        className="main-overlay-btn"
        title={inputsText}
        onClick={() => copyToClipboard(inputsText, setCopiedInputs)}
      >
        <span className="main-overlay-btn__text">Copy chat inputs</span>
        <span className="icon main-overlay-btn__icon">
          {copiedInputs ? "check" : "content_copy"}
        </span>
      </button>
      <button
        type="button"
        className="main-overlay-btn"
        title={COMMANDS_LIST_URL}
        onClick={() => copyToClipboard(COMMANDS_LIST_URL, setCopiedUrl)}
      >
        <span className="main-overlay-btn__text">{urlLabel}</span>
        <span className="icon main-overlay-btn__icon">
          {copiedUrl ? "check" : "content_copy"}
        </span>
      </button>
    </div>
  );
}

export function SetupApp() {
  const { ready, setup } = useChatPlaysState("setup");
  const [demMinutes, setDemMinutes] = useState(null);
  const [demSeconds, setDemSeconds] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [linkFlash, setLinkFlash] = useState("");
  const [emulatorScanning, setEmulatorScanning] = useState(false);
  const [chatTheme, setChatTheme] = useState("dark");
  const [globalTheme, setGlobalTheme] = useState(
    () => localStorage.getItem("chatplays-theme") || "light"
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", globalTheme);
    localStorage.setItem("chatplays-theme", globalTheme);
  }, [globalTheme]);

  const minutes = demMinutes ?? setup?.democracy_minutes ?? 0;
  const seconds = demSeconds ?? setup?.democracy_seconds ?? 15;

  useEffect(() => {
    if (!ready || setup?.controller !== "GBA") {
      return;
    }
    api.scanEmulator().catch(() => {});
  }, [ready, setup?.controller]);

  const scanEmulator = () => {
    setEmulatorScanning(true);
    api
      .scanEmulator()
      .catch(() => {})
      .finally(() => setEmulatorScanning(false));
  };

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
  const autoLinkAvailable = setup.automatic_link_available ?? false;
  const linkMode =
    setup.setup_link_mode === "automatic" && autoLinkAvailable
      ? "automatic"
      : "manual";

  return (
    <div className="setup-shell panel">
      <header className="setup-topbar">
        <button type="button" className="setup-back-btn" onClick={() => closeSetupWindow()}>
          ← Back
        </button>
        <span className="setup-topbar__title muted">Setup / Test</span>
        <button type="button" onClick={() => setSettingsOpen(true)}>
          Settings
        </button>
      </header>

      <div className="setup-layout">
      <div className="card setup-layout__settings">
        <div className="setup-panel-inner">
        <div className="row setup-settings-row">
          <div className="col setup-settings-col">
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
                value={linkMode}
                onChange={(event) =>
                  pushSettings({ setup_link_mode: event.target.value })
                }
              >
                <option value="manual">Manual</option>
                <option value="automatic" disabled={!autoLinkAvailable}>
                  Automatic
                </option>
              </select>
            </label>

            {setup.controller === "GBA" && linkMode === "manual" && (
              <div className="col">
                <span>Game/Emulator</span>
                <EmulatorDetectField
                  compact
                  windowOptions={setup.emulator_window_options || []}
                  windows={setup.emulator_windows || []}
                  selectedWindow={setup.emulator_window}
                  executablePath={setup.emulator_executable_path}
                  appName={setup.emulator_app_name || "visualboyadvance-m.exe"}
                  onScan={scanEmulator}
                  onSelectWindow={(window) => api.selectSetupEmulatorWindow(window).catch(() => {})}
                  onListOtherWindows={async () => {
                    const result = await api.listWindows();
                    return result.windows || [];
                  }}
                  scanning={emulatorScanning}
                />
              </div>
            )}

            {linkMode === "manual" && (
              <div className="setup-manual-actions">
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
          <div className="col setup-settings-col">
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
                <div style={{ position: "relative", display: "inline-flex", alignItems: "center" }}>
                  <input
                    type="number"
                    step="0.1"
                    value={value}
                    style={{ paddingRight: 20 }}
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
                  <span style={{ position: "absolute", right: 7, fontSize: "0.8rem", color: "var(--app-muted)", pointerEvents: "none", userSelect: "none" }}>s</span>
                </div>
              </label>
            ))}
          </div>
        ) : (
          linkMode === "automatic" && (
            <div className="setup-link-content">
              <div className="setup-emulator-panel__status">
                {setup.emulator_detected ? (
                  <strong>{setup.emulator_name || "VisualBoy Advance-M"}</strong>
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
      </div>

      <div className="card setup-layout__controller">
        <div className="setup-panel-inner">
        <ControllerPanel
            controller={setup.controller}
            buttonMap={setup.button_map}
            highlightInput={
              setup.manual_setup_active ? setup.manual_setup_current_input : ""
            }
            disabledInputs={setup.disabled_inputs || []}
            onButtonPress={(inputName) => api.controllerButton(inputName)}
          />
        <SetupControllerFooter
          buttonMap={setup.button_map}
          disabledInputs={setup.disabled_inputs || []}
        />
        </div>
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
              <KeyBindTable
                keyMap={setup.keyboard_map}
                disabledInputs={setup.disabled_inputs || []}
                bindingMode={setup.binding_mode || (IS_WIN ? "virtual" : "keyboard")}
                virtualInputOptions={setup.virtual_input_options || []}
              />
            )}
            </div>
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
