import { InfoIcon } from "./InfoIcon";

export const CHAT_SOURCES = [
  { value: "sandbox", label: "Sandbox chat" },
  { value: "platform", label: "Platform chat" },
];

const POWER_TIP =
  "ChatPlays only takes inputs from your real live chat while it is On, " +
  "and it can only be turned On once your channel is verified in the main window. " +
  "The sandbox chat always works so you can test. " +
  "This is the same power button as in the main window.";

const NO_CHANNEL_POWER_TITLE = "Verify your channel in the main window to turn ChatPlays on";

export function hasVerifiedChannel(main) {
  return Boolean(main?.twitch_username_verified && main?.twitch_username?.trim());
}

export function ChatSourceSelect({ source, onSourceChange }) {
  return (
    <select
      className="chat-source-select"
      value={source}
      onChange={(e) => onSourceChange(e.target.value)}
      aria-label="Chat source"
    >
      {CHAT_SOURCES.map(({ value, label }) => (
        <option key={value} value={value}>
          {label}
        </option>
      ))}
    </select>
  );
}

export function PowerControl({ isOn, canTurnOn, onTogglePower }) {
  const blocked = !isOn && !canTurnOn;
  return (
    <div className="power-control">
      <InfoIcon tip={POWER_TIP} />
      <button
        type="button"
        className={`power-btn power-btn--small${isOn ? " power-btn--on" : " power-btn--off"}`}
        onClick={onTogglePower}
        disabled={blocked}
        title={
          blocked
            ? NO_CHANNEL_POWER_TITLE
            : isOn
              ? "ChatPlays is On. Click to turn off"
              : "ChatPlays is Off. Click to turn on"
        }
        aria-pressed={isOn}
      >
        <span className="power-btn__ring">
          <span className="icon power-btn__icon">power_settings_new</span>
        </span>
      </button>
      <span className={`power-control__status ${isOn ? "status-on" : "status-off"}`}>
        {isOn ? "ON" : "OFF"}
      </span>
    </div>
  );
}

// Twitch only serves the embed when `parent` matches the embedding page's host.
function twitchChatEmbedUrl(login, dark) {
  const params = new URLSearchParams({ parent: window.location.hostname || "localhost" });
  if (dark) params.set("darkpopout", "");
  return `https://www.twitch.tv/embed/${encodeURIComponent(login)}/chat?${params}`;
}

export function PlatformChat({ platform, login, dark }) {
  if (platform !== "twitch") {
    return (
      <div className="platform-chat platform-chat--empty">
        Platform chat is only available for Twitch right now.
      </div>
    );
  }
  if (!login) {
    return (
      <div className="platform-chat platform-chat--empty">
        Enter and verify your Twitch channel in the main window to see its chat here.
      </div>
    );
  }
  return (
    <div className="platform-chat">
      <iframe
        key={`${login}-${dark}`}
        className="platform-chat__frame"
        src={twitchChatEmbedUrl(login, dark)}
        title={`Twitch chat for ${login}`}
      />
    </div>
  );
}
