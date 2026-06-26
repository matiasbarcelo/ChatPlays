import logo from "@assets/logo.png";
import anarchyLogo from "@assets/anarchy.png";
import democracyLogo from "@assets/democracy.png";
import powerOff from "@assets/powerOff.png";
import { api } from "./api";
import { useChatPlaysState } from "./hooks/useChatPlaysState";
import { isElectronApp, openSetupWindow } from "./openSetupWindow";

export function MainApp() {
  const { ready, main } = useChatPlaysState("main");

  if (!ready || !main) {
    return <div className="main-shell muted">Connecting to ChatPlays…</div>;
  }

  const isOn = main.program_status;
  const gov = main.government || "anarchy";

  return (
    <div className="main-shell panel">
      <img src={logo} alt="ChatPlays" className="main-logo" />

      <label className="col" style={{ textAlign: "left", marginTop: 8 }}>
        <span>Twitch Username</span>
        <input
          defaultValue={main.twitch_username}
          placeholder="Type in Twitch Username"
          onBlur={(event) =>
            api.updateMainSettings({ twitch_username: event.target.value })
          }
        />
      </label>

      <div className="main-gov-row">
        <img src={anarchyLogo} alt="Anarchy" />
        <div className="col" style={{ flex: 1 }}>
          <strong style={{ fontSize: "1.1rem" }}>
            {gov === "anarchy" ? "Anarchy" : "Democracy"}
          </strong>
          <input
            type="range"
            min={0}
            max={100}
            step={100}
            value={gov === "anarchy" ? 0 : 100}
            onChange={(event) => {
              const next = Number(event.target.value) === 0 ? "anarchy" : "democracy";
              api.updateMainSettings({ government: next });
            }}
          />
        </div>
        <img src={democracyLogo} alt="Democracy" />
      </div>

      <div className="row" style={{ justifyContent: "center", margin: "16px 0" }}>
        <button type="button" className="power-btn" onClick={() => api.togglePower()}>
          <img src={powerOff} alt={isOn ? "On" : "Off"} />
        </button>
      </div>

      <div
        className={isOn ? "status-on" : "status-off"}
        style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 12 }}
      >
        {isOn ? "ON" : "OFF"}
      </div>

      <button
        type="button"
        style={{ width: "100%", marginBottom: 12 }}
        onClick={() => openSetupWindow()}
      >
        Setup/Test Inputs
      </button>
      {!isElectronApp() && (
        <p className="muted" style={{ marginTop: -8, marginBottom: 12, fontSize: "0.85rem" }}>
          Browser dev mode — opens setup in a new tab. Use <code>npm run dev</code> for the native
          second window.
        </p>
      )}

      <label className="col" style={{ textAlign: "left" }}>
        <span style={{ textDecoration: "underline" }}>Democracy Time Limit:</span>
        <input
          type="number"
          min={1}
          max={90}
          defaultValue={main.democracy_time_limit}
          onBlur={(event) =>
            api.updateMainSettings({
              democracy_time_limit: Number(event.target.value) || 10,
            })
          }
        />
        <span className="muted">seconds</span>
      </label>
    </div>
  );
}
