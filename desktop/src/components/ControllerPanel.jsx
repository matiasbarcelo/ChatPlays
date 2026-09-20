import { useEffect, useRef, useState } from "react";
import gbaImage from "@assets/controller.png";
import xboxImage from "@assets/labeled360.png";
import psImage from "@assets/PS.png";
import { CONTROLLER_LAYOUTS } from "./controllerLayouts";

const IMAGES = {
  GBA: gbaImage,
  "Xbox 360": xboxImage,
  PlayStation: psImage,
};

const DEFAULT_BUTTON_MAPS = {
  GBA: {
    upButton: "up",
    downButton: "down",
    leftButton: "left",
    rightButton: "right",
    aButton: "a",
    bButton: "b",
    lButton: "l",
    rButton: "r",
    selectButton: "select",
    startButton: "start",
  },
};

function imageRectStyle(imageRect, canvas) {
  return {
    left: `${(imageRect.x / canvas.width) * 100}%`,
    top: `${(imageRect.y / canvas.height) * 100}%`,
    width: `${(imageRect.width / canvas.width) * 100}%`,
    height: `${(imageRect.height / canvas.height) * 100}%`,
  };
}

const ANALOG_INPUTS = new Set([
  "lstick", "rstick",
  "left_joystick_float", "right_joystick_float",
  "left_trigger_float", "right_trigger_float",
]);

const IS_MAC = /mac/i.test(navigator.platform);

// A press can be shorter than the round trip that clears it, so the flash is
// held for at least this long to stay visible on stream.
const MIN_FLASH_MS = 180;

/**
 * Tracks the input the backend is pressing right now. `executingSeq` bumps on
 * every press, so repeats of the same input restart the animation.
 *
 * Only the seq drives the effect: the backend clears the input name as soon as
 * the press ends, which can be sooner than MIN_FLASH_MS, and a dependency on
 * the name would cancel the pending reset and leave the button stuck lit.
 */
function useFiringInput(executingInput, executingSeq, executingDuration) {
  const [firing, setFiring] = useState({ input: "", seq: 0, ms: MIN_FLASH_MS });
  const latest = useRef({ input: "", ms: MIN_FLASH_MS, seq: 0 });

  if (executingInput && executingSeq !== latest.current.seq) {
    latest.current = {
      input: executingInput,
      ms: Math.max(MIN_FLASH_MS, Math.round((executingDuration || 0) * 1000)),
      seq: executingSeq,
    };
  }

  useEffect(() => {
    const { input, ms, seq } = latest.current;
    // seq must match, so a press whose name never reached us (both updates
    // batched into one render) does not light up the previous button instead.
    if (!executingSeq || !input || seq !== executingSeq) return undefined;
    setFiring({ input, seq: executingSeq, ms });
    const timer = setTimeout(() => setFiring({ input: "", seq: 0, ms }), ms);
    return () => clearTimeout(timer);
  }, [executingSeq]);

  return firing;
}

export function ControllerPanel({
  controller,
  buttonMap = {},
  highlightInput = "",
  disabledInputs = [],
  onButtonPress,
  executingInput = "",
  executingSeq = 0,
  executingDuration = 0,
}) {
  const firing = useFiringInput(executingInput, executingSeq, executingDuration);
  const layout = CONTROLLER_LAYOUTS[controller] || CONTROLLER_LAYOUTS.GBA;
  const image = IMAGES[controller] || gbaImage;
  const { canvas, imageRect } = layout;
  const effectiveMap =
    Object.keys(buttonMap).length > 0
      ? buttonMap
      : DEFAULT_BUTTON_MAPS[controller] || DEFAULT_BUTTON_MAPS.GBA;

  const buttons = Object.entries(layout.buttons).map(([uiName, config]) => {
    const inputName = effectiveMap[uiName];
    if (!inputName) return null;
    const { label, ...position } = config;
    return { uiName, inputName, label, position };
  }).filter(Boolean);

  return (
    <div
      className="controller-stage"
      style={{ width: canvas.width, height: canvas.height }}
    >
      <img
        className="controller-stage__image"
        src={image}
        alt={`${controller} controller`}
        draggable={false}
        style={imageRectStyle(imageRect, canvas)}
      />
      {buttons.map(({ uiName, inputName, label, position }) => {
        const isDisabled = disabledInputs.includes(inputName);
        const isUnavailable = IS_MAC && ANALOG_INPUTS.has(inputName);
        const isFiring = firing.input === inputName;
        return (<button
          // Remounting on each press restarts the CSS animation for repeats.
          key={isFiring ? `${uiName}-fire-${firing.seq}` : uiName}
          type="button"
          className={[
            "controller-hit",
            controller === "GBA" ? "controller-hit--round" : "",
            highlightInput && inputName === highlightInput ? "controller-hit--active" : "",
            isDisabled ? "controller-hit--disabled" : "",
            isUnavailable ? "controller-hit--unavailable" : "",
            isFiring ? "controller-hit--firing" : "",
          ].filter(Boolean).join(" ")}
          style={isFiring ? { ...position, animationDuration: `${firing.ms}ms` } : position}
          title={isUnavailable ? "Analog input — not supported on Mac" : inputName}
          aria-label={label}
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => !isDisabled && !isUnavailable && onButtonPress(inputName)}
        >
          <span className="controller-hit__label">{label}</span>
        </button>);
      })}
    </div>
  );
}
