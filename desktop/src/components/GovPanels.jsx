import { useEffect, useRef } from "react";
import anarchyIcon from "@assets/anarchy.png";
import democracyIcon from "@assets/democracy.png";

export function GovHeader({ government, chatTheme, onThemeToggle }) {
  const isAnarchy = government === "anarchy";
  return (
    <div className="chat-panel__header">
      {onThemeToggle && (
        <button
          type="button"
          className="chat-panel__theme-btn"
          onClick={onThemeToggle}
        >
          {chatTheme === "dark" ? "Dark" : "Light"}
        </button>
      )}
      <div className="chat-panel__gov-label">
        <img
          src={isAnarchy ? anarchyIcon : democracyIcon}
          alt=""
          width={44}
          height={44}
          className={isAnarchy ? "" : "gov-icon--democracy"}
        />
        <strong className="chat-panel__gov-title">
          {isAnarchy ? "Anarchy" : "Democracy"}
        </strong>
      </div>
    </div>
  );
}

function ChatQueue({ items }) {
  const listRef = useRef(null);

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    requestAnimationFrame(() => {
      list.scrollTop = list.scrollHeight;
    });
  }, [items]);

  return (
    <ul ref={listRef} className="chat-panel__queue">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

function ChatInputForm({ onSubmit }) {
  return (
    <form
      className="chat-panel__form"
      onSubmit={(event) => {
        event.preventDefault();
        const input = event.currentTarget.elements.namedItem("command");
        onSubmit(input.value);
        input.value = "";
      }}
    >
      <input
        name="command"
        placeholder="Type in Inputs"
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        spellCheck={false}
      />
    </form>
  );
}

export function AnarchyPanel({ queue, countdownLine, flashLine, onSubmit, chatTheme = "dark", onThemeToggle }) {
  const items = countdownLine ? [countdownLine] : (flashLine ? [flashLine] : queue);
  return (
    <div className={`chat-panel${chatTheme === "light" ? " chat-panel--light" : ""}`}>
      <GovHeader government="anarchy" chatTheme={chatTheme} onThemeToggle={onThemeToggle} />
      <div className="chat-panel__body">
        <ChatQueue items={items} />
      </div>
      <ChatInputForm onSubmit={onSubmit} />
    </div>
  );
}

export function DemocracyPanel({
  queue,
  countdownLine,
  flashLine,
  voteSlots,
  countdownLabel,
  latestWinner,
  minutes,
  seconds,
  timerRunning,
  onSubmit,
  onMinutesChange,
  onSecondsChange,
  onUpdateTime,
  onToggleTimer,
  chatTheme = "dark",
  onThemeToggle,
}) {
  return (
    <div className={`chat-panel${chatTheme === "light" ? " chat-panel--light" : ""}`}>
      <GovHeader government="democracy" chatTheme={chatTheme} onThemeToggle={onThemeToggle} />
      <div className="chat-panel__controls col">
        <div className="row pixel" style={{ justifyContent: "space-between" }}>
          <label>
            Minutes
            <input
              value={minutes}
              onChange={(event) => onMinutesChange(Number(event.target.value) || 0)}
              style={{ width: 48, marginLeft: 6 }}
            />
          </label>
          <label>
            Seconds
            <input
              value={seconds}
              onChange={(event) => onSecondsChange(Number(event.target.value) || 0)}
              style={{ width: 48, marginLeft: 6 }}
            />
          </label>
        </div>
        <div className="pixel">{countdownLabel}</div>
        <button type="button" onClick={onUpdateTime}>
          Apply timer length
        </button>
        <button type="button" onClick={onToggleTimer}>
          {timerRunning ? "Stop timer" : "Start timer"}
        </button>
        <div className="pixel">Latest Winner: {latestWinner}</div>
        <div className="card">
          {voteSlots.map((slot, index) => (
            <div key={index} className="row" style={{ justifyContent: "space-between" }}>
              <span className="pixel">{slot.input_text}</span>
              <span className="pixel">{slot.votes}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="chat-panel__body">
        <ChatQueue items={countdownLine ? [countdownLine] : (flashLine ? [flashLine] : queue)} />
      </div>
      <ChatInputForm onSubmit={onSubmit} />
    </div>
  );
}
