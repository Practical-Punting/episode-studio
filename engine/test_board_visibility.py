"""THE BOARD MUST NOT LOOK STUCK WHILE THE ENGINE IS WORKING. (D1.)

The board already has two guards and NEITHER covers the real case:

  · the asset links carry a hash OF THE BYTES (stamp_assets.py, test_asset_stamp.py),
    so a stale board is not stale CODE;
  · a 30-second poll backs up the realtime socket.

But a HIDDEN TAB throttles that poll to roughly once a minute and can freeze it
entirely, and a WebSocket that dies while hidden reconnects only when asked. Come back
to the tab and the board shows what it knew when you left.

    THAT IS INDISTINGUISHABLE FROM A STOPPED ENGINE — the same class of lie as 28 Jul
    2026, when this board said "Working for 1 d 1 hr" while the engine was dead. Same
    fault, sides swapped: it now hides work that IS happening.

Asserted by reading app.js, the way test_hand_steps and test_landing_block assert their
guarantees: a behaviour proved once and then deleted is not a guarantee.

Run: python engine/test_board_visibility.py
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APP = pathlib.Path(__file__).resolve().parent.parent / "app.js"
SRC = APP.read_text(encoding="utf-8", errors="replace")
FAILED = []


def check(name, cond, why=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   <- {why}" if not cond else ""))
    if not cond:
        FAILED.append(name)


print("\ncoming back to the tab shows the truth")

check("the board listens for the tab becoming visible again",
      'addEventListener("visibilitychange"' in SRC,
      "without this a hidden tab's throttled timer decides how stale the board gets")

m = re.search(r'addEventListener\("visibilitychange".*?\n\}\);', SRC, re.S)
body = m.group(0) if m else ""
check("the handler was found", bool(body))
check("it refetches on return", "loadAll()" in body, body[:200])
check("it re-subscribes rather than trusting a dead socket",
      "subscribeRealtime()" in body, body[:200])
check("it checks the channel is really joined, not merely set",
      '"joined"' in body, body[:300])
check("a socket that died is dropped before re-subscribing",
      "removeChannel" in body, body[:300])
check("it does nothing while hidden",
      'visibilityState !== "visible"' in body, body[:200])
check("and nothing when signed out", "!SESSION" in body, body[:200])

print("\nthe guards it must not replace")
check("the 30-second safety net is still there", "}, 30000);" in SRC)
check("realtime is still subscribed normally", "subscribeRealtime()" in SRC)

print("\n" + ("ALL PASS" if not FAILED else f"{len(FAILED)} FAILED: {FAILED}"))
sys.exit(1 if FAILED else 0)
