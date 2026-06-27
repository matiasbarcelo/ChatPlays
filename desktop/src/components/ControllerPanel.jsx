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

export function ControllerPanel({ controller, buttonMap = {}, highlightInput = "", disabledInputs = [], onButtonPress }) {
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
        return (<button
          key={uiName}
          type="button"
          className={[
            "controller-hit",
            controller === "GBA" ? "controller-hit--round" : "",
            highlightInput && inputName === highlightInput ? "controller-hit--active" : "",
            isDisabled ? "controller-hit--disabled" : "",
            isUnavailable ? "controller-hit--unavailable" : "",
          ].filter(Boolean).join(" ")}
          style={position}
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
