import { useEffect, useRef, useState } from "react";
import { useChatPlaysState } from "./hooks/useChatPlaysState";
import { ControllerPanel } from "./components/ControllerPanel";

function LiveQueue({ items }) {
  const listRef = useRef(null);

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    requestAnimationFrame(() => {
      list.scrollTop = list.scrollHeight;
    });
  }, [items]);

  return (
    <ul ref={listRef} className="monitor-queue">
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
      : setup.democracy_queue ?? [];

  const govLabel = setup.government === "anarchy" ? "Anarchy" : "Democracy";

  return (
    <div className="monitor-shell">
      <div className="monitor-section-header">{govLabel} — Live Chat</div>
      <LiveQueue items={queue} />

      <div className="monitor-divider" />

      <div className="monitor-section-header">Controller</div>
      <div className="monitor-controller-stage">
        <div style={{ position: "relative", display: "inline-block" }}>
          <ControllerPanel
            controller={setup.controller}
            buttonMap={setup.button_map}
            highlightInput={setup.manual_setup_current_input}
            disabledInputs={setup.disabled_inputs || []}
            onButtonPress={() => {}}
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
