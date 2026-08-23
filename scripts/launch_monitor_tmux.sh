#!/bin/bash
# Launch a dual-pane tmux session: Live Dashboard on Top, Experiment Runner on Bottom
SESSION_NAME="tordial_telemetry"

tmux has-session -t $SESSION_NAME 2>/dev/null
if [ $? -eq 0 ]; then
  echo "[*] Killing existing session: $SESSION_NAME"
  tmux kill-session -t $SESSION_NAME
fi

echo "[*] Starting new tmux session: $SESSION_NAME"
tmux new-session -d -s $SESSION_NAME -n "Manifold"

# Pane 0 (Top): Live Telemetry Dashboard
tmux send-keys -t $SESSION_NAME:0 "cd ~/Tordial-GS && python3 scripts/live_dashboard.py" C-m

# Split pane vertically
tmux split-window -v -t $SESSION_NAME:0

# Pane 1 (Bottom): Ready to run benchmark suite
tmux send-keys -t $SESSION_NAME:0.1 "cd ~/Tordial-GS && sleep 1 && python3 scripts/run_replica_suite.py" C-m

# Attach to session
tmux attach-session -t $SESSION_NAME
