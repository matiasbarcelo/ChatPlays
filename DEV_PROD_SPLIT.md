# Dev / Prod split — design notes and open problems

Notes for whoever builds this next. Nothing below is implemented yet beyond the
UI renaming and the per-environment browser-source links; treat every section as
a problem to solve, not a description of working code.

## The model

Two parallel environments, each driving its own VisualBoy Advance-M instance:

- **dev** — the streamer's sandbox. Reached through the **Setup / Test (dev)**
  window. They tinker here while the stream keeps running.
- **prod** — what is on stream. Watched through the **Chat Monitor (prod)**
  window. Fed by real chat. OBS browser sources point here.

A **PUSH TO PROD** action copies the configuration the streamer has been working
on in dev over to prod. Runtime state is never copied.

## Problem 1 — isolation does not come from our code

A virtual gamepad is not addressed to a window. ViGEm plugs it in at the OS
level and *any* XInput application can read it. We cannot route dev inputs to
the dev emulator.

Separation is the emulator's job: each VBA-M instance has to be bound to one
specific pad. Everything below follows from that constraint.

## Problem 2 — XInput slot identity (the dangerous one)

Windows assigns XInput slots in plug order across all connected XInput devices.
If dev and prod ever swap slots, the streamer's tinkering drives the stream —
precisely the failure this feature exists to prevent.

Today this is fragile:

- `changeController()` (`SetupTestClass.py:83`) constructs a brand new
  `Controller` every time the controller type changes, which re-plugs the pad
  and can take a different slot.
- A real controller plugged in mid-session shifts every slot after it.

Directions worth considering:

- Create both pads exactly once at startup in a fixed order and never recreate
  them. `changeController` would swap *mappings* rather than devices.
- A one-time confirmation step — press a button, ask the user which emulator
  moved — rather than trusting slot order. Similar to "identify displays".
- Persist the answer and re-confirm when the device set changes.

## Problem 3 — two emulator instances need two configs

Two VBA-M instances reading the same `vbam.ini` get the same joypad binding, so
both respond to the same pad and there is no isolation at all.

The current code works against this:

- `write_vba_gba_keyboard_map()` (`emulator_support.py:1750`) writes bindings
  into **every discovered `vbam.ini`**, and `_all_vbam_configs()` exists
  specifically to enumerate them.
- The joypad section is hardcoded to `Joypad/1` throughout — see
  `emulator_support.py:1770`. Dev needs `Joypad/2`, or its own config file.

**Unverified and blocking:** does VBA-M accept a config-path argument? If not,
dev needs a separate portable install, which turns this from a feature into a
setup chore for users. `launch_vba_emulator()` (`emulator_support.py:1338`)
builds `command = [str(executable)]`, so there is a clean place to pass one.
**Verify this before committing to the design** — it is the cheapest thing that
can invalidate the whole approach.

## Problem 4 — state is a single flat object

`SetupTestState` is one dataclass and `SetupTestService` is a single instance
holding the queues, governments, timers and worker threads. The split needs two
of them. This is the bulk of the work; the second gamepad is the easy part.

Splits per environment (each env owns its own):

- `anarchy_queue`, `democracy_queue`, `vote_slots`, `latest_winner`
- democracy timer and countdown, chat-decides vote state
- `government` — the streamer may want to try democracy while prod runs anarchy
- `executing_button` and friends (`setup_test_service.py:122`) — the live
  controller animation
- emulator window/process, virtual pad, emulator config path
- `meta_mode`

Shared configuration, pushed dev → prod:

- `button_map`, `keyboard_map`, `disabled_inputs`
- timings (`tap_time`, `press_time`, `hold_time`, defaults, enabled modes)
- input rules (`allow_timing_prefixes`, `allow_input_repeat`,
  `allow_input_sequences`, `max_input_sequence_length`,
  `allow_custom_input_duration`, `max_input_duration`)

## Problem 5 — overlays must follow prod, never dev

`/controller` and `/overlay` currently read the single global state. Once dev
exists, they must read **prod** explicitly or the streamer's tinkering animates
live on stream.

The URLs already carry an `env` query parameter (`?env=prod`, `?env=dev`) so
that links already pasted into OBS keep working when the split lands. **Right
now both values resolve to the same state** — the parameter is a placeholder for
the routing, not working isolation.

## Problem 6 — PUSH TO PROD semantics

Payload is the shared-configuration list in Problem 4. Never the window target,
never queues or vote tallies.

Open questions:

- **In-flight queue.** If the button map changes while inputs are queued in
  prod, some queued text may no longer be valid. Drop them, let them run under
  the old map, or re-validate?
- **Atomicity.** Applying settings one at a time leaves prod briefly in a mixed
  state while live. Apply under one lock.
- **Confirmation.** It fires mid-stream, so it wants a diff preview — "4
  bindings changed, democracy timer 15s → 20s, `select` disabled" — not a bare
  button.

## Problem 7 — there is no prod chat yet

`Twitch_Connection` is imported at `ChatPlays.py:1` and **never instantiated**.
No live chat path exists. Every input today comes from the Setup/Test chat box,
the fake chat roll, or the API.

Until real chat is wired up, "prod" is just the stream-facing emulator with the
streamer typing into it, and the split buys much less than it will later.
Consider sequencing real chat first so there are genuinely two distinct inputs
to separate.

## Pre-existing bugs that touch this

- **Orphaned virtual gamepad.** `ChatPlays.__init__` creates
  `self.controller = GBAController()` (`ChatPlays.py:15`), which plugs in a
  `VX360Gamepad`, and nothing ever uses it — all input goes through
  `setupTest.controller`. `changeController()` leaks another on every controller
  switch. Any "two controllers" observed today is this, not a feature.
- **The power button gates nothing.** `ChatPlays.getStatus()`
  (`ChatPlays.py:72`) is never called, and `_program_live`
  (`setup_test_service.py:155`) is written three times and never read. Toggling
  power scans for the emulator and nothing else. Both Setup and Test modes drive
  the real emulator.
- **Automatic controller linking is unsolved** for VBA-M, which is why the
  Controller link control in Setup / Test (dev) is locked to Manual.

## Naming

"Setup" and "Test" are not dev and prod — they are a different axis entirely
(*am I binding buttons, or running the pipeline?*). The bindings made in the
Setup / Test window are the real ones. The `(dev)` and `(prod)` suffixes mark
the environment each window belongs to; they do not redefine what Setup and Test
mean.
