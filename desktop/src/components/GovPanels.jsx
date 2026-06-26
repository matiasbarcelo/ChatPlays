import { useEffect, useRef } from "react";
import anarchyIcon from "@assets/anarchy.png";
import democracyIcon from "@assets/democracy.png";

export function GovHeader({ government }) {
  const isAnarchy = government === "anarchy";
  return (
    <div className="row chat-panel__header">
      <img src={isAnarchy ? anarchyIcon : democracyIcon} alt="" width={44} height={44} />
      <strong style={{ fontSize: "1.35rem" }}>
        {isAnarchy ? "Anarchy" : "Democracy"}
      </strong>
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
      <input name="command" placeholder="Type in Inputs" />
    </form>
  );
}

export function AnarchyPanel({ queue, onSubmit }) {
  return (
    <div className="chat-panel">
      <GovHeader government="anarchy" />
      <div className="chat-panel__body">
        <ChatQueue items={queue} />
      </div>
      <ChatInputForm onSubmit={onSubmit} />
    </div>
  );
}

export function DemocracyPanel({
  queue,
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
}) {
  return (
    <div className="chat-panel">
      <GovHeader government="democracy" />
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
        <ChatQueue items={queue} />
      </div>
      <ChatInputForm onSubmit={onSubmit} />
    </div>
  );
}
