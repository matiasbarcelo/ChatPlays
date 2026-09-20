import { useEffect, useState } from "react";
import { useChatPlaysState } from "./hooks/useChatPlaysState";
import { ControllerPanel } from "./components/ControllerPanel";
import { CONTROLLER_LAYOUTS } from "./components/controllerLayouts";
import {
  chatOverlayUrl,
  controllerOverlayUrl,
  overlayTitle,
  copyOverlayUrl,
  CHAT_OVERLAY_SIZE,
} from "./overlayLinks";

/** Copy button for a browser source, sat on a section header row. */
function OverlayLink({ url, size }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="monitor-obs-btn"
      title={overlayTitle(url, size)}
      onClick={() => copyOverlayUrl(url, setCopied)}
    >
      <span className="monitor-obs-btn__text">
        {copied ? "Copied!" : `Browser source (${size.replace(/ /g, "")})`}
      </span>
      <span className="icon monitor-obs-btn__icon">
        {copied ? "check" : "content_copy"}
      </span>
    </button>
  );
}

function LiveQueue({ items }) {
  return (
    <ul className="monitor-queue">
      {items.map((item, i) => (
        <li key={`${item}-${i}`}>{item}</li>
      ))}
    </ul>
  );
}

function useSystemTheme() {
  const [theme, setTheme] = useState(
    () => localStorage.getItem("chatplays-theme") || "light"
  );

  useEffect(() => {
    const apply = (t) => {
      setTheme(t);
      document.documentElement.setAttribute("data-theme", t);
    };

    apply(localStorage.getItem("chatplays-theme") || "light");

    const onStorage = (e) => {
      if (e.key === "chatplays-theme" && e.newValue) apply(e.newValue);
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return theme;
}

export function MonitorApp() {
  useSystemTheme();
  const { ready, setup } = useChatPlaysState("setup");

  if (!ready || !setup) {
    return (
      <div className="monitor-shell">
        <span style={{ padding: 24, opacity: 0.5 }}>Connecting…</span>
      </div>
    );
  }

  const queue =
    setup.government === "anarchy"
      ? setup.anarchy_queue ?? []
      : setup.government === "chat_decides"
        ? (setup.chat_decides_active_gov === "democracy"
            ? setup.democracy_queue
            : setup.anarchy_queue) ?? []
        : setup.democracy_queue ?? [];

  const controllerCanvas = (
    CONTROLLER_LAYOUTS[setup.controller] || CONTROLLER_LAYOUTS.GBA
  ).canvas;

  const govLabel =
    setup.government === "chat_decides"
      ? `Chat Decides (${setup.chat_decides_active_gov === "democracy" ? "Democracy" : "Anarchy"})`
      : setup.government === "anarchy"
        ? "Anarchy"
        : "Democracy";

  return (
    <div className="monitor-shell">
      <div className="monitor-section-header">
        <span>{govLabel} — Live Chat</span>
        <OverlayLink url={chatOverlayUrl()} size={CHAT_OVERLAY_SIZE} />
      </div>
      <LiveQueue items={queue} />

      <div className="monitor-divider" />

      <div className="monitor-section-header">
        <span>Controller</span>
        <OverlayLink
          url={controllerOverlayUrl()}
          size={`${controllerCanvas.width} x ${controllerCanvas.height}`}
        />
      </div>
      <div className="monitor-controller-stage">
        <div style={{ position: "relative", display: "inline-block" }}>
          <ControllerPanel
            controller={setup.controller}
            buttonMap={setup.button_map}
            highlightInput={
              setup.manual_setup_active ? setup.manual_setup_current_input : ""
            }
            disabledInputs={setup.disabled_inputs || []}
            onButtonPress={() => {}}
            executingInput={setup.executing_button || ""}
            executingSeq={setup.executing_button_seq || 0}
            executingDuration={setup.executing_button_duration || 0}
          />
          <div style={{
            position: "absolute",
            inset: 0,
            zIndex: 10,
            cursor: "default",
          }} />
        </div>
      </div>
    </div>
  );
}
