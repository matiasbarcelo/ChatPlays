import { useChatPlaysState } from "./hooks/useChatPlaysState";
import { AnarchyPanel, DemocracyPanel, ChatDecidesPanel } from "./components/GovPanels";

/**
 * OBS browser source: the chat panel on its own, sized to whatever the browser
 * source is set to. Same markup as Setup/Test, minus the operator controls and
 * the test input box, so it matches the panel in the app exactly.
 *
 * `?theme=light` renders the light variant; the default is dark.
 * `?user=Name` prefixes each line with a name, as the panel does in the app.
 */
export function ChatOverlayApp() {
  const { ready, setup, main } = useChatPlaysState("setup");
  const params = new URLSearchParams(window.location.search);
  const chatTheme = params.get("theme") === "light" ? "light" : "dark";
  const username =
    params.get("user") ??
    (main?.twitch_display_name?.trim() || main?.twitch_username?.trim() || "");

  if (!ready || !setup) return <div className="chat-overlay" />;

  const shared = {
    countdownLine: setup.setup_countdown_line,
    username,
    chatTheme,
    displayOnly: true,
    onSubmit: () => {},
  };

  let panel;
  if (setup.government === "anarchy") {
    panel = <AnarchyPanel {...shared} queue={setup.anarchy_queue} />;
  } else if (setup.government === "chat_decides") {
    panel = (
      <ChatDecidesPanel
        {...shared}
        activeGovernment={setup.chat_decides_active_gov}
        anarchyVotes={setup.chat_decides_anarchy_votes}
        democracyVotes={setup.chat_decides_democracy_votes}
        democracyPercent={setup.chat_decides_democracy_percent ?? 50}
        lastVote={setup.chat_decides_last_vote ?? ""}
        switchThreshold={setup.chat_decides_switch_threshold ?? 75}
        voteTtlMinutes={setup.chat_decides_vote_ttl_minutes ?? 5}
        queue={
          setup.chat_decides_active_gov === "democracy"
            ? setup.democracy_queue
            : setup.anarchy_queue
        }
        voteSlots={setup.vote_slots}
        countdownLabel={setup.democracy_countdown_label}
        latestWinner={setup.latest_winner}
      />
    );
  } else {
    panel = (
      <DemocracyPanel
        {...shared}
        queue={setup.democracy_queue}
        voteSlots={setup.vote_slots}
        countdownLabel={setup.democracy_countdown_label}
        latestWinner={setup.latest_winner}
      />
    );
  }

  return <div className="chat-overlay">{panel}</div>;
}
