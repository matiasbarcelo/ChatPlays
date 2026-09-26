import anarchyIcon from "@assets/anarchy.png";
import democracyIcon from "@assets/democracy.png";

function governmentLabel(government) {
  if (government === "chat_decides") return "Chat Decides";
  if (government === "democracy") return "Democracy";
  return "Anarchy";
}

export function GovHeader({ government, chatTheme, onThemeToggle, subtitle }) {
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
        <div className="chat-panel__gov-title-wrap">
          <strong className="chat-panel__gov-title">
            {governmentLabel(government)}
          </strong>
          {subtitle && (
            <span className="chat-panel__gov-subtitle pixel">{subtitle}</span>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Renders the queue in backend order. The backend already decides direction:
 * anarchy appends (oldest first — it is a play queue), democracy prepends
 * (newest first — latest vote on top). Do not re-sort here.
 */
function ChatQueue({ items, users, username }) {
  const fallbackUsername = username?.trim() || "";

  return (
    <ul className="chat-panel__queue">
      {items.map((item, index) => {
        const displayUsername = users?.[index] || fallbackUsername;
        return (
          <li key={`${item}-${index}`} className="chat-panel__queue-item">
            {displayUsername && (
              <span className="chat-panel__queue-user">{displayUsername}</span>
            )}
            <span className="chat-panel__queue-input">{item}</span>
          </li>
        );
      })}
    </ul>
  );
}

function ChatInputForm({ onSubmit, username }) {
  const displayUsername = username?.trim() || "";

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
      <div className="chat-panel__form-row">
        {displayUsername && (
          <span className="chat-panel__form-user">{displayUsername}</span>
        )}
        <input
          name="command"
          placeholder="Type in Inputs"
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
        />
      </div>
    </form>
  );
}

export function AnarchyPanel({
  queue,
  queueUsers,
  countdownLine,
  flashLine,
  onSubmit,
  username,
  chatTheme = "dark",
  onThemeToggle,
  displayOnly = false,
}) {
  const items = countdownLine ? [countdownLine] : (flashLine ? [flashLine] : queue);
  return (
    <div className={`chat-panel${chatTheme === "light" ? " chat-panel--light" : ""}`}>
      <GovHeader
        government="anarchy"
        chatTheme={chatTheme}
        onThemeToggle={displayOnly ? undefined : onThemeToggle}
      />
      <div className="chat-panel__body">
        <ChatQueue items={items} users={items === queue ? queueUsers : undefined} username={username} />
      </div>
      {!displayOnly && <ChatInputForm onSubmit={onSubmit} username={username} />}
    </div>
  );
}

export function DemocracyPanel({
  queue,
  queueUsers,
  countdownLine,
  flashLine,
  voteSlots,
  countdownLabel,
  latestWinner,
  minutes,
  seconds,
  timerRunning,
  onSubmit,
  username,
  onMinutesChange,
  onSecondsChange,
  onUpdateTime,
  onToggleTimer,
  chatTheme = "dark",
  onThemeToggle,
  displayOnly = false,
}) {
  return (
    <div className={`chat-panel${chatTheme === "light" ? " chat-panel--light" : ""}`}>
      <GovHeader
        government="democracy"
        chatTheme={chatTheme}
        onThemeToggle={displayOnly ? undefined : onThemeToggle}
      />
      <div className="chat-panel__controls col">
        {!displayOnly && (
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
        )}
        <div className="pixel chat-panel__countdown-label">{countdownLabel}</div>
        {!displayOnly && (
          <>
            <button type="button" onClick={onUpdateTime}>
              Apply timer length
            </button>
            <button type="button" onClick={onToggleTimer}>
              {timerRunning ? "Stop timer" : "Start timer"}
            </button>
          </>
        )}
        <div className="pixel chat-panel__latest-winner">Latest Winner: {latestWinner}</div>
        <div className="card">
          {(voteSlots ?? []).map((slot, index) => (
            <div key={index} className="row" style={{ justifyContent: "space-between" }}>
              <span className="pixel">{slot.input_text}</span>
              <span className="pixel">{slot.votes}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="chat-panel__body">
        <ChatQueue
          items={countdownLine ? [countdownLine] : (flashLine ? [flashLine] : queue)}
          users={countdownLine || flashLine ? undefined : queueUsers}
          username={username}
        />
      </div>
      {!displayOnly && <ChatInputForm onSubmit={onSubmit} username={username} />}
    </div>
  );
}

function ChatDecidesBar({ democracyPercent, thresholdPercent, activeGovernment, lastVote }) {
  const position = Math.max(0, Math.min(100, democracyPercent));
  const threshold = Math.max(51, Math.min(99, thresholdPercent));
  const lowerThreshold = 100 - threshold;
  const arrow =
    lastVote === "anarchy" ? "<" : lastVote === "democracy" ? ">" : "";

  return (
    <div className="chat-decides-bar-block pixel">
      <div className="chat-decides-bar-grid">
        <span
          className={`chat-decides-bar__label${
            activeGovernment === "anarchy" ? " chat-decides-bar__label--active" : ""
          }`}
        >
          Anarchy
        </span>
        <div className="chat-decides-bar" aria-hidden="true">
          {activeGovernment === "democracy" && (
            <span
              className="chat-decides-bar__threshold"
              style={{ left: `${lowerThreshold}%` }}
            />
          )}
          {activeGovernment === "anarchy" && (
            <span
              className="chat-decides-bar__threshold chat-decides-bar__threshold--upper"
              style={{ left: `${threshold}%` }}
            />
          )}
          <span className="chat-decides-bar__position-line" style={{ left: `${position}%` }} />
          {arrow && (
            <span
              className={`chat-decides-bar__pointer chat-decides-bar__pointer--${
                lastVote === "democracy" ? "right" : "left"
              }`}
              style={{ left: `${position}%` }}
            >
              {arrow}
            </span>
          )}
        </div>
        <span
          className={`chat-decides-bar__label${
            activeGovernment === "democracy" ? " chat-decides-bar__label--active" : ""
          }`}
        >
          Democracy
        </span>
        <div className="chat-decides-bar__percent-track">
          <span className="chat-decides-bar__percent" style={{ left: `${position}%` }}>
            {Math.round(democracyPercent)}%
          </span>
        </div>
      </div>
    </div>
  );
}

export function ChatDecidesPanel({
  activeGovernment,
  anarchyVotes,
  democracyVotes,
  democracyPercent,
  lastVote,
  defaultGov,
  switchThreshold,
  voteTtlMinutes,
  onSettingsChange,
  queue,
  queueUsers,
  countdownLine,
  flashLine,
  voteSlots,
  countdownLabel,
  latestWinner,
  minutes,
  seconds,
  timerRunning,
  onSubmit,
  username,
  onMinutesChange,
  onSecondsChange,
  onUpdateTime,
  onToggleTimer,
  chatTheme = "dark",
  onThemeToggle,
  displayOnly = false,
}) {
  const activeLabel = activeGovernment === "democracy" ? "Democracy" : "Anarchy";
  const items = countdownLine ? [countdownLine] : (flashLine ? [flashLine] : queue);

  return (
    <div className={`chat-panel${chatTheme === "light" ? " chat-panel--light" : ""}`}>
      <GovHeader
        government="chat_decides"
        subtitle={`Active: ${activeLabel}`}
        chatTheme={chatTheme}
        onThemeToggle={displayOnly ? undefined : onThemeToggle}
      />
      <div className="chat-panel__controls col chat-decides-controls">
        <ChatDecidesBar
          democracyPercent={democracyPercent}
          thresholdPercent={switchThreshold}
          activeGovernment={activeGovernment}
          lastVote={lastVote}
        />
        {!displayOnly && (
        <div className="chat-decides-settings row pixel">
          <label>
            Starts with
            <select
              value={defaultGov}
              onChange={(event) => onSettingsChange({ chat_decides_default_gov: event.target.value })}
            >
              <option value="anarchy">Anarchy</option>
              <option value="democracy">Democracy</option>
            </select>
          </label>
          <label>
            Threshold
            <input
              type="number"
              min={51}
              max={99}
              value={switchThreshold}
              onChange={(event) =>
                onSettingsChange({
                  chat_decides_switch_threshold: Number(event.target.value) || 51,
                })
              }
              className="chat-decides-settings__threshold-input"
              style={{ marginLeft: 6 }}
            />
            %
          </label>
          <label>
            Vote TTL
            <input
              type="number"
              min={1}
              max={1440}
              value={voteTtlMinutes}
              onChange={(event) =>
                onSettingsChange({
                  chat_decides_vote_ttl_minutes: Number(event.target.value) || 1,
                })
              }
              style={{ width: 56, marginLeft: 6 }}
            />
            min
          </label>
        </div>
        )}
        <div className="card chat-decides-votes">
          <div className="pixel chat-decides-votes__title">Votes</div>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span className="pixel">anarchy</span>
            <span className="pixel">{anarchyVotes}</span>
          </div>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span className="pixel">democracy</span>
            <span className="pixel">{democracyVotes}</span>
          </div>
        </div>
        {activeGovernment === "democracy" && (
          <>
            {!displayOnly && (
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
            )}
            <div className="pixel chat-panel__countdown-label">{countdownLabel}</div>
            {!displayOnly && (
              <>
                <button type="button" onClick={onUpdateTime}>
                  Apply timer length
                </button>
                <button type="button" onClick={onToggleTimer}>
                  {timerRunning ? "Stop timer" : "Start timer"}
                </button>
              </>
            )}
            <div className="pixel chat-panel__latest-winner">Latest Winner: {latestWinner}</div>
            <div className="card">
              {(voteSlots ?? []).map((slot, index) => (
                <div key={index} className="row" style={{ justifyContent: "space-between" }}>
                  <span className="pixel">{slot.input_text}</span>
                  <span className="pixel">{slot.votes}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
      <div className="chat-panel__body">
        <ChatQueue items={items} users={items === queue ? queueUsers : undefined} username={username} />
      </div>
      {!displayOnly && <ChatInputForm onSubmit={onSubmit} username={username} />}
    </div>
  );
}
