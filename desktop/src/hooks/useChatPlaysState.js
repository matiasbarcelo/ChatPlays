import { useEffect, useState } from "react";
import { api, connectStateSocket } from "../api";

/** `overlay: true` uses the token-free, redacted feed meant for OBS browser sources. */
export function useChatPlaysState(scope = "all", { overlay = false } = {}) {
  const [state, setState] = useState({ setup: null, main: null });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;

    (overlay ? api.getOverlayState() : api.getState())
      .then((data) => {
        if (active) {
          setState(data);
          setReady(true);
        }
      })
      .catch((error) => {
        console.error("Failed to load state", error);
      });

    const disconnect = connectStateSocket((message) => {
      if (message.type === "state") {
        setState((prev) => ({
          setup: message.setup ?? prev.setup,
          main: message.main ?? prev.main,
        }));
        setReady(true);
      }
    }, { overlay });

    return () => {
      active = false;
      disconnect();
    };
  }, [overlay]);

  if (scope === "setup") return { ready, setup: state.setup, main: state.main };
  if (scope === "main") return { ready, main: state.main, setup: state.setup };
  return { ready, ...state };
}
