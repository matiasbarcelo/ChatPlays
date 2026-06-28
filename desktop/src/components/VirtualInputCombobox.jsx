import { useEffect, useMemo, useRef, useState } from "react";

const ANALOG_INPUTS = new Set([
  "left_joystick_float",
  "right_joystick_float",
  "left_trigger_float",
  "right_trigger_float",
]);

function buildOptionGroups(options) {
  const digital = [];
  const analog = [];

  for (const option of options) {
    if (ANALOG_INPUTS.has(option)) {
      analog.push(option);
    } else {
      digital.push(option);
    }
  }

  const groups = [{ label: null, options: digital }];
  if (analog.length > 0) {
    groups.push({ label: "Analog", options: analog });
  }
  return groups;
}

export function VirtualInputCombobox({ value, options, onCommit, disabled = false }) {
  const [draft, setDraft] = useState(value);
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  const optionSet = useMemo(() => new Set(options), [options]);
  const optionGroups = useMemo(() => buildOptionGroups(options), [options]);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event) {
      if (!rootRef.current?.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  const filteredGroups = useMemo(() => {
    const query = draft.trim().toLowerCase();
    if (!query) return optionGroups;

    return optionGroups
      .map((group) => ({
        ...group,
        options: group.options.filter((option) => option.toLowerCase().includes(query)),
      }))
      .filter((group) => group.options.length > 0);
  }, [draft, optionGroups]);

  const isValidDraft = optionSet.has(draft.trim());

  const commit = (nextValue) => {
    const trimmed = nextValue.trim();
    if (!trimmed || !optionSet.has(trimmed)) {
      setDraft(value);
      setOpen(false);
      return;
    }
    setDraft(trimmed);
    setOpen(false);
    if (trimmed !== value) {
      onCommit(trimmed);
    }
  };

  const selectOption = (option) => {
    setDraft(option);
    commit(option);
  };

  return (
    <div
      className={`virtual-input-combobox${open ? " virtual-input-combobox--open" : ""}`}
      ref={rootRef}
    >
      <input
        type="text"
        className={`keybind-virtual-input virtual-input-combobox__input${
          draft.trim() && !isValidDraft ? " virtual-input-combobox__input--invalid" : ""
        }`}
        value={draft}
        spellCheck={false}
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        disabled={disabled}
        onChange={(event) => {
          setDraft(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => commit(draft)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            commit(draft);
          } else if (event.key === "Escape") {
            event.preventDefault();
            setDraft(value);
            setOpen(false);
            event.currentTarget.blur();
          } else if (event.key === "ArrowDown" && !open) {
            event.preventDefault();
            setOpen(true);
          }
        }}
      />
      <button
        type="button"
        className="virtual-input-combobox__toggle"
        aria-label="Show virtual inputs"
        disabled={disabled}
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => setOpen((prev) => !prev)}
      >
        ▾
      </button>
      {open && (
        <div className="virtual-input-combobox__list" role="listbox">
          {filteredGroups.length > 0 ? (
            filteredGroups.map((group) => (
              <div key={group.label || "digital"} className="virtual-input-combobox__group">
                {group.label && (
                  <div className="virtual-input-combobox__group-label">{group.label}</div>
                )}
                {group.options.map((option) => (
                  <button
                    key={option}
                    type="button"
                    role="option"
                    aria-selected={option === value}
                    className={`virtual-input-combobox__option${
                      option === value ? " virtual-input-combobox__option--selected" : ""
                    }`}
                    onMouseDown={(event) => {
                      event.preventDefault();
                      selectOption(option);
                    }}
                  >
                    {option}
                  </button>
                ))}
              </div>
            ))
          ) : (
            <div className="virtual-input-combobox__empty">No matching inputs</div>
          )}
        </div>
      )}
    </div>
  );
}
