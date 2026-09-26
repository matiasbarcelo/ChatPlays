import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { useChatPlaysState } from "./hooks/useChatPlaysState";
import { ControllerPanel } from "./components/ControllerPanel";
import { CONTROLLER_LAYOUTS } from "./components/controllerLayouts";
import { InfoIcon } from "./components/InfoIcon";
import { VirtualInputCombobox } from "./components/VirtualInputCombobox";
import { AnarchyPanel, DemocracyPanel, ChatDecidesPanel } from "./components/GovPanels";
import { EmulatorDetectField } from "./components/EmulatorDetectField";
import {
  ChatSourceSelect,
  PlatformChat,
  PowerControl,
  hasVerifiedChannel,
} from "./components/ChatSource";
import { closeSetupWindow } from "./openSetupWindow";
import {
  chatOverlayUrl,
  controllerOverlayUrl,
  overlayTitle,
  CHAT_OVERLAY_SIZE,
} from "./overlayLinks";

const VIGEM_BUS_DOCS_URL = "https://github.com/ViGEm/ViGEmBus";
const SANDBOX_USERNAME = "User";

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
const OVERLAY_URL = chatOverlayUrl();
const CONTROLLER_OVERLAY_URL = controllerOverlayUrl();

function getAvailableChatInputs(buttonMap, disabledInputs = [], government = "anarchy") {
  const disabled = new Set(disabledInputs);
  const inputs = [...new Set(Object.values(buttonMap || {}))]
    .filter((name) => name && !disabled.has(name))
    .sort((a, b) => a.localeCompare(b));
  inputs.push("wait");
  if (government === "chat_decides") {
    inputs.push("anarchy", "democracy");
  }
  return inputs;
}

function getEnabledTimingModes(setup) {
  return ["tap", "press", "hold"].filter((mode) => setup?.[`timing_${mode}_enabled`] !== false);
}

function buildTimingSettings(setup, overrides = {}) {
  const timing_tap_enabled =
    overrides.timing_tap_enabled ?? setup.timing_tap_enabled ?? true;
  const timing_press_enabled =
    overrides.timing_press_enabled ?? setup.timing_press_enabled ?? true;
  const timing_hold_enabled =
    overrides.timing_hold_enabled ?? setup.timing_hold_enabled ?? true;
  const enabled = {
    tap: timing_tap_enabled,
    press: timing_press_enabled,
    hold: timing_hold_enabled,
  };
  let default_time_length =
    overrides.default_time_length ?? setup.default_time_length ?? "press";
  if (!enabled[default_time_length]) {
    default_time_length = ["tap", "press", "hold"].find((mode) => enabled[mode]) ?? "press";
  }
  return {
    tap_time: overrides.tap_time ?? setup.tap_time,
    press_time: overrides.press_time ?? setup.press_time,
    hold_time: overrides.hold_time ?? setup.hold_time,
    default_time_length,
    timing_tap_enabled,
    timing_press_enabled,
    timing_hold_enabled,
  };
}

function buildChatInputPolicy(setup, overrides = {}) {
  return {
    allow_timing_prefixes:
      overrides.allow_timing_prefixes ?? setup.allow_timing_prefixes ?? true,
    allow_input_repeat: overrides.allow_input_repeat ?? setup.allow_input_repeat ?? true,
    allow_custom_input_duration:
      overrides.allow_custom_input_duration ?? setup.allow_custom_input_duration ?? false,
    max_input_duration: overrides.max_input_duration ?? setup.max_input_duration ?? 15,
    allow_input_sequences:
      overrides.allow_input_sequences ?? setup.allow_input_sequences ?? false,
    max_input_sequence_length:
      overrides.max_input_sequence_length ?? setup.max_input_sequence_length ?? 3,
  };
}

function formatInputsForClipboard(inputs, settings = {}) {
  const {
    defaultTimeLength = "press",
    tapTime = 0.3,
    pressTime = 0.5,
    holdTime = 1,
    controller = "GBA",
    allowCustomInputDuration = false,
    maxInputDuration = 15,
    allowTimingPrefixes = true,
    allowInputRepeat = true,
    allowInputSequences = false,
    maxInputSequenceLength = 3,
    enabledTimingModes = ["tap", "press", "hold"],
    government = "anarchy",
    chatDecidesSwitchThreshold = 75,
    chatDecidesVoteTtlMinutes = 5,
  } = settings;

  const timingLabels = {
    tap: `tap ${tapTime}s`,
    press: `press ${pressTime}s`,
    hold: `hold ${holdTime}s`,
  };
  const activeTimingModes = enabledTimingModes.filter((mode) => timingLabels[mode]);
  const defaultLabel = timingLabels[defaultTimeLength] ?? defaultTimeLength;

  const list = inputs.join(", ");
  const lines = [
    "ChatPlays — Available Chat Inputs",
    "",
    `Controller: ${controller}`,
    `Inputs: ${list}`,
    "",
    "How to play:",
    "• Send a button name in chat (example: a or start)",
    "• Capitalization doesn't matter (example: START, Start, and start are the same)",
    "• Use wait to pause without pressing a button (example: wait or (2)wait)",
  ];

  if (allowInputSequences) {
    lines.push(
      `• Chain multiple inputs with commas (example: a,b,start, max ${maxInputSequenceLength} per sequence)`
    );
  }

  if (allowTimingPrefixes && activeTimingModes.length > 1) {
    const shortPrefixes = activeTimingModes.map((mode) => mode[0]).join(", ");
    lines.push(
      `• Prefix ${activeTimingModes.join(", ")} (or ${shortPrefixes}) before a button`
    );
  }

  if (allowCustomInputDuration) {
    lines.push(
      `• Custom duration in seconds before the button (example: (1.6)a, max ${maxInputDuration}s)`
    );
  }

  if (allowTimingPrefixes || !allowCustomInputDuration) {
    const timingParts = activeTimingModes.map((mode) => timingLabels[mode]).join(", ");
    lines.push(
      `• Default timing: ${defaultLabel}${timingParts ? ` (${timingParts})` : ""}`
    );
  }

  if (allowInputRepeat) {
    lines.push("• Add 1–9 at the end to repeat (example: a3)");
  }

  lines.push(
    "",
    "Anarchy: each valid input is queued and played in order.",
    "Democracy: type an input to vote. The most popular vote wins when the timer ends."
  );

  if (government === "chat_decides") {
    lines.splice(
      lines.length - 2,
      0,
      `• Chat Decides: anarchy and democracy are listed with other inputs; votes queue like everything else and the bar switches at the ${chatDecidesSwitchThreshold}% / ${100 - chatDecidesSwitchThreshold}% lines (votes expire after ${chatDecidesVoteTtlMinutes} min)`
    );
  }

  return lines.join("\n");
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

function SetupControllerFooter({
  buttonMap,
  disabledInputs = [],
  defaultTimeLength,
  tapTime,
  pressTime,
  holdTime,
  controller,
  allowCustomInputDuration,
  maxInputDuration,
  allowTimingPrefixes,
  allowInputRepeat,
  allowInputSequences,
  maxInputSequenceLength,
  enabledTimingModes,
  government,
  chatDecidesSwitchThreshold,
  chatDecidesVoteTtlMinutes,
}) {
  const [copiedInputs, setCopiedInputs] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const inputs = getAvailableChatInputs(buttonMap, disabledInputs, government);
  const inputsText = formatInputsForClipboard(inputs, {
    defaultTimeLength,
    tapTime,
    pressTime,
    holdTime,
    controller,
    allowCustomInputDuration,
    maxInputDuration,
    allowTimingPrefixes,
    allowInputRepeat,
    allowInputSequences,
    maxInputSequenceLength,
    enabledTimingModes,
    government,
    chatDecidesSwitchThreshold,
    chatDecidesVoteTtlMinutes,
  });
  const controllerLayout = CONTROLLER_LAYOUTS[controller] || CONTROLLER_LAYOUTS.GBA;
  const { width: obsWidth, height: obsHeight } = controllerLayout.canvas;

  return (
    <div className="setup-controller-footer">
      <button
        type="button"
        className="main-overlay-btn"
        title={inputsText}
        onClick={() => copyToClipboard(inputsText, setCopiedInputs)}
      >
        <span className="main-overlay-btn__text">Copy chat inputs & instructions</span>
        <span className="icon main-overlay-btn__icon">
          {copiedInputs ? "check" : "content_copy"}
        </span>
      </button>
      <button
        type="button"
        className="main-overlay-btn"
        title={overlayTitle(CONTROLLER_OVERLAY_URL, `${obsWidth} x ${obsHeight}`)}
        onClick={() => copyToClipboard(CONTROLLER_OVERLAY_URL, setCopiedUrl)}
      >
        <span className="main-overlay-btn__text">
          {copiedUrl ? "Copied!" : "Controller Browser Source"}
        </span>
        <span className="icon main-overlay-btn__icon">
          {copiedUrl ? "check" : "content_copy"}
        </span>
      </button>
    </div>
  );
}

export function SetupApp() {
  const { ready, setup, main } = useChatPlaysState("setup");
  const [demMinutes, setDemMinutes] = useState(null);
  const [demSeconds, setDemSeconds] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [copiedChatOverlay, setCopiedChatOverlay] = useState(false);
  const [linkFlash, setLinkFlash] = useState("");
  const [emulatorScanning, setEmulatorScanning] = useState(false);
  const [chatTheme, setChatTheme] = useState("dark");
  const [chatSource, setChatSource] = useState("sandbox");
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
  const enabledTimingModes = getEnabledTimingModes(setup);
  const toggleTimingMode = (name) => {
    const field = `timing_${name}_enabled`;
    const isEnabled = setup[field] !== false;
    if (isEnabled && enabledTimingModes.length <= 1) {
      return;
    }
    pushSettings(buildTimingSettings(setup, { [field]: !isEnabled }));
  };
  // Automatic linking of the virtual controller to VisualBoyAdvance is not
  // solved yet, so the control is locked to Manual until it is.
  const linkMode = "manual";

  return (
    <div className="setup-shell panel">
      <header className="setup-topbar">
        <div className="setup-topbar__left">
          <button type="button" className="setup-back-btn" onClick={() => closeSetupWindow()}>
            ← Back
          </button>
          <span className="setup-topbar__title muted">Setup / Test</span>
          <button type="button" onClick={() => setSettingsOpen(true)}>
            Settings
          </button>
          <PowerControl
            isOn={Boolean(main?.program_status)}
            canTurnOn={hasVerifiedChannel(main)}
            onTogglePower={() => api.togglePower().catch(() => {})}
          />
        </div>
        <div className="setup-topbar__chat">
          <ChatSourceSelect source={chatSource} onSourceChange={setChatSource} />
          <button
            type="button"
            className="main-overlay-btn setup-obs-link-btn"
            title={overlayTitle(OVERLAY_URL, CHAT_OVERLAY_SIZE)}
            onClick={() => copyToClipboard(OVERLAY_URL, setCopiedChatOverlay)}
          >
            <span className="main-overlay-btn__text">
              {copiedChatOverlay ? "Copied!" : "Chat Browser Source"}
            </span>
            <span className="icon main-overlay-btn__icon">
              {copiedChatOverlay ? "check" : "content_copy"}
            </span>
          </button>
        </div>
      </header>

      <div className="setup-layout">
      <div
        className={`card setup-layout__settings${
          setup.meta_mode === "setup" ? " setup-layout__settings--setup-mode" : ""
        }`}
      >
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
                value="manual"
                disabled
                title="Automatic linking is not supported yet — link the controller manually."
                onChange={() => {}}
              >
                <option value="manual">Manual</option>
              </select>
            </label>

            {setup.controller === "GBA" && linkMode === "manual" && (
              <label className="col">
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
                  disabled
                />
              </label>
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
                <option value="chat_decides">Chat Decides</option>
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

        {setup.meta_mode === "setup" && linkMode === "manual" && (
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

        {setup.meta_mode === "test" ? (
          <div className="setup-link-content setup-link-content--test">
            <p className="timing-options-header">
              Double-click tap, press, or hold to enable or disable it. At least one must stay active.
            </p>
            <div className="timing-row">
              {[
                ["tap", setup.tap_time],
                ["press", setup.press_time],
                ["hold", setup.hold_time],
              ].map(([name, value]) => {
                const isEnabled = setup[`timing_${name}_enabled`] !== false;
                return (
                  <div
                    key={name}
                    className={`timing-group${isEnabled ? "" : " timing-group--disabled"}`}
                    onDoubleClick={(event) => {
                      event.preventDefault();
                      toggleTimingMode(name);
                    }}
                    title={
                      isEnabled
                        ? "Double-click to disable this timing option"
                        : "Double-click to enable this timing option"
                    }
                  >
                    <input
                      type="radio"
                      name="defaultTime"
                      checked={setup.default_time_length === name}
                      disabled={!isEnabled}
                      onChange={() =>
                        pushSettings(buildTimingSettings(setup, { default_time_length: name }))
                      }
                    />
                    <span className="pixel timing-group__label" style={{ textTransform: "capitalize" }}>
                      {name}
                    </span>
                    <div className="timing-value-wrap">
                      <input
                        type="number"
                        step="0.1"
                        value={value}
                        disabled={!isEnabled}
                        onChange={(event) => {
                          const numeric = Number(event.target.value) || 0;
                          pushSettings(
                            buildTimingSettings(setup, { [`${name}_time`]: numeric })
                          );
                        }}
                      />
                      <span className="timing-unit">s</span>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="setup-chat-duration-options">
              <label className="setup-chat-duration-options__check">
                <input
                  type="checkbox"
                  checked={setup.allow_timing_prefixes !== false}
                  onChange={(event) =>
                    pushSettings(
                      buildChatInputPolicy(setup, {
                        allow_timing_prefixes: event.target.checked,
                      })
                    )
                  }
                />
                <span>Allow tap / press / hold</span>
              </label>
              <label className="setup-chat-duration-options__check">
                <input
                  type="checkbox"
                  checked={setup.allow_input_repeat !== false}
                  onChange={(event) =>
                    pushSettings(
                      buildChatInputPolicy(setup, {
                        allow_input_repeat: event.target.checked,
                      })
                    )
                  }
                />
                <span>Allow repeat</span>
              </label>
              <label className="setup-chat-duration-options__check">
                <input
                  type="checkbox"
                  checked={!!setup.allow_custom_input_duration}
                  onChange={(event) =>
                    pushSettings(
                      buildChatInputPolicy(setup, {
                        allow_custom_input_duration: event.target.checked,
                      })
                    )
                  }
                />
                <span>Allow custom input duration</span>
              </label>
              {setup.allow_custom_input_duration && (
                <label className="setup-chat-duration-options__max">
                  <span>Max time</span>
                  <input
                    type="number"
                    min={1}
                    max={99}
                    value={setup.max_input_duration ?? 15}
                    onChange={(event) =>
                      pushSettings(
                        buildChatInputPolicy(setup, {
                          allow_custom_input_duration: true,
                          max_input_duration: Number(event.target.value) || 1,
                        })
                      )
                    }
                  />
                  <span className="timing-unit">s</span>
                </label>
              )}
              <label className="setup-chat-duration-options__check">
                <input
                  type="checkbox"
                  checked={!!setup.allow_input_sequences}
                  onChange={(event) =>
                    pushSettings(
                      buildChatInputPolicy(setup, {
                        allow_input_sequences: event.target.checked,
                      })
                    )
                  }
                />
                <span>Allow input sequences</span>
              </label>
              {setup.allow_input_sequences && (
                <label className="setup-chat-duration-options__max">
                  <span>Max sequence length</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={setup.max_input_sequence_length ?? 3}
                    onChange={(event) =>
                      pushSettings(
                        buildChatInputPolicy(setup, {
                          allow_input_sequences: true,
                          max_input_sequence_length: Number(event.target.value) || 1,
                        })
                      )
                    }
                  />
                </label>
              )}
            </div>
            <div className="setup-fake-chat-row">
              <button
                type="button"
                disabled={setup.fake_chat_running}
                onClick={() => api.startFakeChatRoll().catch(() => {})}
              >
                {setup.government === "democracy"
                  ? "Roll fake votes"
                  : setup.government === "chat_decides"
                    ? "Roll fake chat / votes"
                    : "Roll fake chat"}
              </button>
              {setup.fake_chat_running && (
                <button type="button" onClick={() => api.stopFakeChatRoll().catch(() => {})}>
                  Stop
                </button>
              )}
              {(setup.government === "democracy" || setup.government === "chat_decides") &&
                !setup.democracy_timer_running &&
                !setup.fake_chat_running &&
                (setup.government !== "chat_decides" ||
                  setup.chat_decides_active_gov === "democracy") && (
                <span className="muted setup-fake-chat-hint">Starts vote timer</span>
              )}
            </div>
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
            executingInput={setup.executing_button || ""}
            executingSeq={setup.executing_button_seq || 0}
            executingDuration={setup.executing_button_duration || 0}
          />
        <SetupControllerFooter
          buttonMap={setup.button_map}
          disabledInputs={setup.disabled_inputs || []}
          defaultTimeLength={setup.default_time_length}
          tapTime={setup.tap_time}
          pressTime={setup.press_time}
          holdTime={setup.hold_time}
          controller={setup.controller}
          allowCustomInputDuration={setup.allow_custom_input_duration}
          maxInputDuration={setup.max_input_duration}
          allowTimingPrefixes={setup.allow_timing_prefixes !== false}
          allowInputRepeat={setup.allow_input_repeat !== false}
          allowInputSequences={!!setup.allow_input_sequences}
          maxInputSequenceLength={setup.max_input_sequence_length ?? 3}
          enabledTimingModes={enabledTimingModes}
          government={setup.government}
          chatDecidesSwitchThreshold={setup.chat_decides_switch_threshold ?? 75}
          chatDecidesVoteTtlMinutes={setup.chat_decides_vote_ttl_minutes ?? 5}
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
        {chatSource === "platform" ? (
          <PlatformChat
            platform={main?.streaming_platform}
            login={main?.twitch_username_verified ? main.twitch_username.trim().toLowerCase() : ""}
            dark={chatTheme === "dark"}
          />
        ) : setup.government === "anarchy" ? (
          <AnarchyPanel
            queue={setup.anarchy_queue}
            queueUsers={setup.anarchy_queue_users}
            countdownLine={setup.setup_countdown_line}
            flashLine={linkFlash}
            username={SANDBOX_USERNAME}
            onSubmit={(text) => api.submitInput(text)}
            chatTheme={chatTheme}
            onThemeToggle={() => setChatTheme(t => t === "dark" ? "light" : "dark")}
          />
        ) : setup.government === "chat_decides" ? (
          <ChatDecidesPanel
            activeGovernment={setup.chat_decides_active_gov}
            anarchyVotes={setup.chat_decides_anarchy_votes}
            democracyVotes={setup.chat_decides_democracy_votes}
            democracyPercent={setup.chat_decides_democracy_percent ?? 50}
            lastVote={setup.chat_decides_last_vote ?? ""}
            defaultGov={setup.chat_decides_default_gov ?? "anarchy"}
            switchThreshold={setup.chat_decides_switch_threshold ?? 75}
            voteTtlMinutes={setup.chat_decides_vote_ttl_minutes ?? 5}
            onSettingsChange={(payload) => pushSettings(payload)}
            queue={
              setup.chat_decides_active_gov === "democracy"
                ? setup.democracy_queue
                : setup.anarchy_queue
            }
            queueUsers={
              setup.chat_decides_active_gov === "democracy"
                ? setup.democracy_queue_users
                : setup.anarchy_queue_users
            }
            countdownLine={setup.setup_countdown_line}
            flashLine={linkFlash}
            voteSlots={setup.vote_slots}
            countdownLabel={setup.democracy_countdown_label}
            latestWinner={setup.latest_winner}
            minutes={minutes}
            seconds={seconds}
            timerRunning={setup.democracy_timer_running}
            username={SANDBOX_USERNAME}
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
        ) : (
          <DemocracyPanel
            queue={setup.democracy_queue}
            queueUsers={setup.democracy_queue_users}
            countdownLine={setup.setup_countdown_line}
            flashLine={linkFlash}
            voteSlots={setup.vote_slots}
            countdownLabel={setup.democracy_countdown_label}
            latestWinner={setup.latest_winner}
            minutes={minutes}
            seconds={seconds}
            timerRunning={setup.democracy_timer_running}
            username={SANDBOX_USERNAME}
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
