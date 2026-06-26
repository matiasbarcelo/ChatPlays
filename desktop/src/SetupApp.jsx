import { useState } from "react";
import { api } from "./api";
import { useChatPlaysState } from "./hooks/useChatPlaysState";
import { ControllerPanel } from "./components/ControllerPanel";
import { AnarchyPanel, DemocracyPanel } from "./components/GovPanels";
import { closeSetupWindow } from "./openSetupWindow";

export function SetupApp() {
  const { ready, setup } = useChatPlaysState("setup");
  const [demMinutes, setDemMinutes] = useState(null);
  const [demSeconds, setDemSeconds] = useState(null);

  const minutes = demMinutes ?? setup?.democracy_minutes ?? 0;
  const seconds = demSeconds ?? setup?.democracy_seconds ?? 15;

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
      </header>

      <div className="setup-layout">
      <div className="card setup-layout__settings">
        <div className="row" style={{ alignItems: "flex-start" }}>
          <div className="col" style={{ flex: 1 }}>
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

            {setup.setup_link_mode === "automatic" ? (
              <div className="col setup-emulator-panel">
                <div className="setup-emulator-panel__status">
                  {setup.emulator_detected ? (
                    <>
                      <strong>{setup.emulator_name}</strong>
                      <span className="muted">Window: {setup.emulator_window}</span>
                    </>
                  ) : (
                    <strong className="muted">No emulator detected</strong>
                  )}
                  {setup.emulator_message && (
                    <span className="muted">{setup.emulator_message}</span>
                  )}
                  {setup.auto_link_status && (
                    <span className="pixel">{setup.auto_link_status}</span>
                  )}
                </div>
                <div className="row" style={{ flexWrap: "wrap" }}>
                  <button type="button" onClick={() => api.scanEmulator()}>
                    Scan for Emulator
                  </button>
                  <button
                    type="button"
                    onClick={() => api.autoLinkEmulator()}
                    disabled={setup.controller !== "GBA"}
                  >
                    Link with Emulator
                  </button>
                </div>
                {setup.controller !== "GBA" && (
                  <span className="muted">
                    Automatic linking currently supports GBA with VisualBoy Advance.
                  </span>
                )}
              </div>
            ) : (
              <>
                <div className="muted">
                  {setup.manual_setup_active
                    ? setup.manual_setup_prompt
                    : "Focus your emulator. Each button is pressed after the countdown so you can bind keys there."}
                </div>
                <div className="row" style={{ flexWrap: "wrap" }}>
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
              </>
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
      </div>

      <div className="card timing-row setup-layout__timing">
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

      <div className="card setup-layout__controller">
        <ControllerPanel
            controller={setup.controller}
            buttonMap={setup.button_map}
            highlightInput={setup.manual_setup_current_input}
            onButtonPress={(inputName) => api.controllerButton(inputName)}
          />
      </div>

      <section className="setup-layout__chat">
        {setup.government === "anarchy" ? (
          <AnarchyPanel
            queue={setup.anarchy_queue}
            onSubmit={(text) => api.submitInput(text)}
          />
        ) : (
          <DemocracyPanel
            queue={setup.democracy_queue}
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
          />
        )}
      </section>
      </div>
    </div>
  );
}
