import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import vbamFallback from "@assets/vbam.png";

function isUsableIconSrc(src) {
  return typeof src === "string" && src.length > 0;
}

function formatWindowLabel(windowTitle, appName = "visualboyadvance-m.exe") {
  if (!windowTitle) {
    return `[${appName}]`;
  }
  return `[${appName}]: ${windowTitle}`;
}

function resolveWindowEntries(windowOptions, windows, selectedWindow, appName) {
  if (windowOptions?.length) {
    return windowOptions.map((option) => ({
      id: option.id,
      title: option.title,
      label: option.label || formatWindowLabel(option.title, appName),
    }));
  }

  const fallbackWindows = windows.length > 0 ? windows : selectedWindow ? [selectedWindow] : [];
  return fallbackWindows.map((title, index) => ({
    id: title,
    title,
    label: formatWindowLabel(title, appName),
    key: `${title}-${index}`,
  }));
}

export function EmulatorDetectField({
  windowOptions = [],
  windows = [],
  selectedWindow = "",
  message,
  executablePath,
  appName = "visualboyadvance-m.exe",
  onScan,
  onSelectWindow,
  onListOtherWindows,
  scanning = false,
  notDetectedMessage,
  compact = false,
}) {
  const rootRef = useRef(null);
  const ignoreTriggerClickRef = useRef(false);
  const keepOpenRef = useRef(false);
  const [iconSrc, setIconSrc] = useState(vbamFallback);
  const [otherWindows, setOtherWindows] = useState([]);
  const [otherLoading, setOtherLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const entries = useMemo(
    () => resolveWindowEntries(windowOptions, windows, selectedWindow, appName),
    [windowOptions, windows, selectedWindow, appName]
  );

  const hasEmulatorWindows = entries.length > 0;
  const isEmulatorSelection = hasEmulatorWindows && entries.some((entry) => entry.id === selectedWindow);
  const isOtherSelection = Boolean(selectedWindow && !isEmulatorSelection);

  const [pickerMode, setPickerMode] = useState(isOtherSelection ? "other" : "emulator");

  const loadOtherWindows = useCallback(async () => {
    if (!onListOtherWindows) {
      return;
    }
    setOtherLoading(true);
    try {
      const options = await onListOtherWindows();
      setOtherWindows(Array.isArray(options) ? options : []);
    } catch {
      setOtherWindows([]);
    } finally {
      setOtherLoading(false);
    }
  }, [onListOtherWindows]);

  useEffect(() => {
    if (isOtherSelection) {
      setPickerMode("other");
    }
  }, [isOtherSelection, selectedWindow]);

  useEffect(() => {
    if (pickerMode === "other") {
      loadOtherWindows();
    }
  }, [pickerMode, loadOtherWindows]);

  useEffect(() => {
    if (!open) {
      return;
    }
    function onPointerDown(event) {
      if (keepOpenRef.current || ignoreTriggerClickRef.current) {
        return;
      }
      if (!rootRef.current?.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  useEffect(() => {
    let cancelled = false;

    async function loadIcon() {
      if (pickerMode === "other") {
        if (!cancelled) {
          setIconSrc("");
        }
        return;
      }

      if (executablePath && window.chatplays?.getFileIcon) {
        try {
          const dataUrl = await window.chatplays.getFileIcon(executablePath);
          if (!cancelled && isUsableIconSrc(dataUrl) && dataUrl.startsWith("data:")) {
            setIconSrc(dataUrl);
            return;
          }
        } catch {
          /* fall through to bundled icon */
        }
      }
      if (!cancelled) {
        setIconSrc(vbamFallback);
      }
    }

    loadIcon();
    return () => {
      cancelled = true;
    };
  }, [executablePath, pickerMode]);

  const displayLabel = useMemo(() => {
    if (isEmulatorSelection) {
      const entry = entries.find((item) => item.id === selectedWindow);
      return entry?.label || selectedWindow;
    }
    if (isOtherSelection) {
      const entry = otherWindows.find((item) => item.id === selectedWindow);
      return entry?.label || selectedWindow;
    }
    if (!hasEmulatorWindows) {
      return "No emulator found";
    }
    return "Select detected window…";
  }, [
    isEmulatorSelection,
    isOtherSelection,
    entries,
    otherWindows,
    selectedWindow,
    hasEmulatorWindows,
  ]);

  const hint =
    pickerMode === "other"
      ? message || "Choose any open window. Refresh to update the list."
      : !hasEmulatorWindows && notDetectedMessage
        ? notDetectedMessage
        : hasEmulatorWindows && message
          ? message
          : !hasEmulatorWindows
            ? "Open VisualBoy Advance-M or choose another window from the list."
            : message || "";

  const refreshing = pickerMode === "other" ? otherLoading : scanning;
  const listDisabled = pickerMode === "other" && otherLoading && otherWindows.length === 0;

  function handleRefresh() {
    if (pickerMode === "other") {
      loadOtherWindows();
      return;
    }
    onScan?.();
  }

  function switchToOtherMode(event) {
    event.preventDefault();
    event.stopPropagation();
    keepOpenRef.current = true;
    ignoreTriggerClickRef.current = true;
    setPickerMode("other");
    setOpen(true);
    window.setTimeout(() => {
      keepOpenRef.current = false;
      ignoreTriggerClickRef.current = false;
    }, 100);
  }

  function switchToEmulatorMode(event) {
    event.preventDefault();
    event.stopPropagation();
    keepOpenRef.current = true;
    ignoreTriggerClickRef.current = true;
    setPickerMode("emulator");
    setOpen(true);
    window.setTimeout(() => {
      keepOpenRef.current = false;
      ignoreTriggerClickRef.current = false;
    }, 100);
  }

  function selectWindow(windowId) {
    setOpen(false);
    onSelectWindow?.(windowId);
  }

  return (
    <div ref={rootRef} className={`window-picker${compact ? " window-picker--compact" : ""}`}>
      {!compact ? <span className="window-picker__label">Window</span> : null}
      <div className="window-picker__row">
        <div
          className={`window-picker__select-wrap${
            pickerMode === "other" ? " window-picker__select-wrap--other" : ""
          }${open ? " window-picker__select-wrap--open" : ""}`}
        >
          {pickerMode === "emulator" && iconSrc ? (
            <img
              src={iconSrc}
              alt=""
              className="window-picker__icon"
              onError={() => {
                if (iconSrc !== vbamFallback) {
                  setIconSrc(vbamFallback);
                }
              }}
            />
          ) : null}
          <button
            type="button"
            className={`window-picker__trigger${
              hasEmulatorWindows || isOtherSelection ? "" : " window-picker__trigger--empty"
            }${pickerMode === "other" ? " window-picker__trigger--other" : ""}`}
            aria-haspopup="listbox"
            aria-expanded={open}
            aria-label={pickerMode === "other" ? "All application windows" : "Detected game window"}
            onMouseDown={(event) => event.preventDefault()}
            onClick={(event) => {
              event.stopPropagation();
              if (ignoreTriggerClickRef.current) {
                return;
              }
              setOpen((prev) => !prev);
            }}
          >
            <span className="window-picker__trigger-label">{displayLabel}</span>
            <span className="window-picker__caret" aria-hidden="true">
              ▾
            </span>
          </button>
          {open ? (
            <div
              className="window-picker__list"
              role="listbox"
              onMouseDown={(event) => event.stopPropagation()}
            >
              <div className="window-picker__panel" hidden={pickerMode !== "emulator"}>
                {!hasEmulatorWindows ? (
                  <div className="window-picker__status">No emulator found</div>
                ) : null}
                {entries.map((entry) => (
                  <button
                    key={entry.id}
                    type="button"
                    role="option"
                    aria-selected={entry.id === selectedWindow}
                    className={`window-picker__option${
                      entry.id === selectedWindow ? " window-picker__option--selected" : ""
                    }`}
                    onMouseDown={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      selectWindow(entry.id);
                    }}
                  >
                    {entry.label}
                  </button>
                ))}
                <button
                  type="button"
                  className="window-picker__option window-picker__option--action"
                  onMouseDown={switchToOtherMode}
                >
                  Select another window…
                </button>
              </div>
              <div className="window-picker__panel" hidden={pickerMode !== "other"}>
                {hasEmulatorWindows ? (
                  <button
                    type="button"
                    className="window-picker__option window-picker__option--action"
                    onMouseDown={switchToEmulatorMode}
                  >
                    ← Detected emulators
                  </button>
                ) : null}
                {otherLoading ? (
                  <div className="window-picker__status">Loading windows…</div>
                ) : null}
                {!otherLoading && otherWindows.length === 0 ? (
                  <div className="window-picker__status">No windows found</div>
                ) : null}
                {otherWindows.map((entry) => (
                  <button
                    key={entry.id}
                    type="button"
                    role="option"
                    aria-selected={entry.id === selectedWindow}
                    className={`window-picker__option${
                      entry.id === selectedWindow ? " window-picker__option--selected" : ""
                    }`}
                    onMouseDown={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      selectWindow(entry.id);
                    }}
                  >
                    {entry.label}
                  </button>
                ))}
                {isOtherSelection &&
                selectedWindow &&
                !otherWindows.some((entry) => entry.id === selectedWindow) ? (
                  <button
                    type="button"
                    role="option"
                    aria-selected
                    className="window-picker__option window-picker__option--selected"
                    onMouseDown={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      selectWindow(selectedWindow);
                    }}
                  >
                    {selectedWindow}
                  </button>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
        <button
          type="button"
          className="window-picker__refresh"
          title={pickerMode === "other" ? "Refresh all windows" : "Refresh window list"}
          aria-label={pickerMode === "other" ? "Refresh all windows" : "Refresh window list"}
          onClick={handleRefresh}
          disabled={refreshing || listDisabled}
        >
          <span
            className={`icon window-picker__refresh-icon${
              refreshing ? " window-picker__refresh-icon--spin" : ""
            }`}
          >
            refresh
          </span>
        </button>
      </div>
      {hint && !compact ? <p className="window-picker__hint muted">{hint}</p> : null}
    </div>
  );
}
