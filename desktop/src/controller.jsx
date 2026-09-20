import React from "react";
import ReactDOM from "react-dom/client";
import { ControllerOverlayApp } from "./ControllerOverlayApp";
import "./styles/global.css";

// OBS browser sources need a transparent page, not the app background.
document.documentElement.classList.add("overlay-root");
document.body.classList.add("overlay-body");

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ControllerOverlayApp />
  </React.StrictMode>
);
