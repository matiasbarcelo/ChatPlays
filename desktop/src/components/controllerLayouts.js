function rect(x, y, w, h, canvasW, canvasH) {
  return {
    left: `${(x / canvasW) * 100}%`,
    top: `${(y / canvasH) * 100}%`,
    width: `${(w / canvasW) * 100}%`,
    height: `${(h / canvasH) * 100}%`,
  };
}

const GBA_CANVAS = { width: 411, height: 295 };
const XBOX_CANVAS = { width: 411, height: 295 };
const PS_CANVAS = { width: 421, height: 295 };

export const CONTROLLER_LAYOUTS = {
  GBA: {
    image: "controller.png",
    canvas: GBA_CANVAS,
    // Matches legacy Qt: GBA_display geometry in setup_test_ui.ui
    imageRect: { x: 40, y: 20, width: 331, height: 251 },
    buttons: {
      aButton: { ...rect(360, 100, 31, 31, GBA_CANVAS.width, GBA_CANVAS.height), label: "A" },
      bButton: { ...rect(350, 170, 31, 31, GBA_CANVAS.width, GBA_CANVAS.height), label: "B" },
      upButton: { ...rect(10, 80, 41, 31, GBA_CANVAS.width, GBA_CANVAS.height), label: "Up" },
      downButton: { ...rect(30, 200, 41, 31, GBA_CANVAS.width, GBA_CANVAS.height), label: "Down" },
      leftButton: { ...rect(20, 120, 41, 31, GBA_CANVAS.width, GBA_CANVAS.height), label: "Left" },
      rightButton: { ...rect(30, 160, 41, 31, GBA_CANVAS.width, GBA_CANVAS.height), label: "Right" },
      lButton: { ...rect(50, 20, 31, 31, GBA_CANVAS.width, GBA_CANVAS.height), label: "L" },
      rButton: { ...rect(330, 20, 31, 31, GBA_CANVAS.width, GBA_CANVAS.height), label: "R" },
      selectButton: { ...rect(200, 220, 41, 31, GBA_CANVAS.width, GBA_CANVAS.height), label: "Select" },
      startButton: { ...rect(90, 220, 41, 31, GBA_CANVAS.width, GBA_CANVAS.height), label: "Start" },
    },
  },
  "Xbox 360": {
    image: "labeled360.png",
    canvas: XBOX_CANVAS,
    // Matches legacy Qt: xboxController geometry in setup_test_ui.ui
    imageRect: { x: 0, y: -20, width: 391, height: 311 },
    buttons: {
      lStickButton: { ...rect(10, 130, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "Lstick" },
      upDpadButton: { ...rect(20, 160, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "UpDpad" },
      leftDpadButton: { ...rect(40, 190, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "LeftDpad" },
      downDpadButton: { ...rect(100, 220, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "DownDpad" },
      rightDpadButton: { ...rect(150, 200, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "RightDpad" },
      rStickButton: { ...rect(200, 230, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "Rstick" },
      aButton_2: { ...rect(310, 190, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "A" },
      xButton: { ...rect(320, 160, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "X" },
      bButton_2: { ...rect(320, 120, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "B" },
      yButton: { ...rect(300, 70, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "Y" },
      rbButton: { ...rect(280, 40, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "RB" },
      rtButton: { ...rect(240, 10, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "RT" },
      startButton_2: { ...rect(200, 30, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "Start" },
      homeButton: { ...rect(160, 50, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "Home" },
      backButton: { ...rect(130, 30, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "Back" },
      ltButton: { ...rect(80, 10, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "LT" },
      lbButton: { ...rect(50, 40, 75, 23, XBOX_CANVAS.width, XBOX_CANVAS.height), label: "LB" },
    },
  },
  PlayStation: {
    image: "PS.png",
    canvas: PS_CANVAS,
    // Matches legacy Qt: PS label geometry in setup_test_ui.ui
    imageRect: { x: 0, y: 0, width: 421, height: 261 },
    buttons: {
      l2Button: { ...rect(20, 30, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "L2" },
      l1Button: { ...rect(20, 60, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "L1" },
      upButton_2: { ...rect(10, 90, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "Up" },
      leftButton_2: { ...rect(10, 110, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "Left" },
      rightButton_2: { ...rect(10, 140, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "Right" },
      downButton_2: { ...rect(10, 170, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "Down" },
      lStickButton_2: { ...rect(20, 230, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "Lstick" },
      rStickButton_2: { ...rect(320, 230, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "Rstick" },
      xButton_2: { ...rect(330, 170, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "X" },
      sqButton: { ...rect(330, 140, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "Sq" },
      cirButton: { ...rect(330, 110, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "Cir" },
      triButton: { ...rect(330, 90, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "Tri" },
      r1Button: { ...rect(330, 60, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "R1" },
      selectButton_2: { ...rect(160, 20, 51, 23, PS_CANVAS.width, PS_CANVAS.height), label: "Select" },
      r2Button: { ...rect(330, 30, 75, 23, PS_CANVAS.width, PS_CANVAS.height), label: "R2" },
      startButton_3: { ...rect(210, 20, 51, 23, PS_CANVAS.width, PS_CANVAS.height), label: "Start" },
    },
  },
};
