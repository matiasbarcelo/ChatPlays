# Chat input rules

What a chat message may contain, the default limits, and where each rule is
enforced. The same rules apply to live Twitch chat, the Setup/Test sandbox, and
the fake chat roll: every message is parsed and validated by `InputSequence` in
[input.py](input.py).

## Syntax

| Form | Example | Setting that enables it | Default |
|---|---|---|---|
| Button name | `a`, `start` | always on | on |
| Wait (pause, no button) | `wait`, `(2)wait` | always on | on |
| Timing prefix | `tap a`, `hold up`, `t b` | Allow tap / press / hold | on |
| Custom duration (seconds) | `(1.5)a` | Allow custom input duration | **off** |
| Repeat (1–9) | `a3` | Allow repeat | on |
| Sequence (comma-separated) | `up,up,a` | Allow input sequences | **off** |

Spaces and capitalization are ignored (`Hold A` is `holda`). A timing prefix and
a custom duration can't be combined on the same input, and `wait` can't repeat.
Each tap/press/hold mode can be switched off individually; at least one stays on.

## Limits

| Limit | Default | Allowed range | Enforced in |
|---|---|---|---|
| Max custom duration per input | 15 s | 1–99 s | [SetupTestClass.py](SetupTestClass.py) `setMaxTimeLength` |
| Max inputs per sequence | 3 | 1–10 | [SetupTestClass.py](SetupTestClass.py) `setMaxInputSequenceLength` |
| Max repeat | 9 | fixed | the one-digit repeat in the input pattern, [input.py](input.py) |
| **Max total time per message** | 30 s | fixed (see below) | [input.py](input.py) `MAX_MESSAGE_SECONDS` |

### Total time per message

Durations, repeats and sequence parts multiply, so without a cap one message
such as `(15)a9,(15)b9,(15)up9` would hold the controller for about 6¾ minutes
and block everyone else's inputs in Anarchy.

A message's total time is the sum, over its parts, of
`duration × repeats + 0.1 s × (repeats − 1)`. The 0.1 s is the pause the
controller leaves between repeats. The duration of each part is its custom
duration, else its tap/press/hold time, else the default timing.

A message over the cap is rejected like any other invalid message: in live chat
it is silently ignored. The cap is `MAX_MESSAGE_SECONDS` (30 s), raised to the
max custom duration when custom durations are on and that setting is higher, so
a single `(60)a` still works when the max duration is 60.

## Other rules for live chat

- Live chat is only read while ChatPlays is **On**, which needs a verified channel.
- Viewers can't run sandbox commands such as `clear`.
- Messages are only queued in Test mode and are ignored while a Setup countdown
  or manual setup is running.

## Telling viewers

**Copy chat inputs & instructions** in Setup/Test copies a viewer-facing
summary of these rules, generated from the current settings, including the
per-message time limit when repeats, custom durations or sequences are on.
