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

export function ControllerPanel({ controller, buttonMap = {}, highlightInput = "", onButtonPress }) {
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
      {buttons.map(({ uiName, inputName, label, position }) => (
        <button
          key={uiName}
          type="button"
          className={`controller-hit ${controller === "GBA" ? "controller-hit--round" : ""}${
            highlightInput && inputName === highlightInput ? " controller-hit--active" : ""
          }`}
          style={position}
          title={inputName}
          aria-label={label}
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => onButtonPress(inputName)}
        >
          <span className="controller-hit__label">{label}</span>
        </button>
      ))}
    </div>
  );
}
