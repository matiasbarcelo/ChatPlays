import { useChatPlaysState } from "./hooks/useChatPlaysState";
import { ControllerPanel } from "./components/ControllerPanel";

/**
 * OBS browser source: the controller on its own, on a transparent background,
 * lighting up each input as the backend executes it.
 */
export function ControllerOverlayApp() {
  const { ready, setup } = useChatPlaysState("setup", { overlay: true });

  if (!ready || !setup) return <div className="controller-overlay" />;

  return (
    <div className="controller-overlay">
      <ControllerPanel
        controller={setup.controller}
        buttonMap={setup.button_map}
        disabledInputs={setup.disabled_inputs || []}
        onButtonPress={() => {}}
        executingInput={setup.executing_button || ""}
        executingSeq={setup.executing_button_seq || 0}
        executingDuration={setup.executing_button_duration || 0}
      />
    </div>
  );
}
