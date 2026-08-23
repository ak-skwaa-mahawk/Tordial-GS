#!/bin/bash
SESSION_NAME="tordial_telemetry"

tmux has-session -t $SESSION_NAME 2>/dev/null
if [ $? -eq 0 ]; then
  tmux kill-session -t $SESSION_NAME
fi

# Launch session in detached state with bash shell
tmux new-session -d -s $SESSION_NAME -n "Manifold" "bash"

# Pane 0 (Top): Live Telemetry Dashboard
tmux send-keys -t $SESSION_NAME:0 "python3 scripts/live_dashboard.py" C-m

# Split pane vertically for execution runner
tmux split-window -v -t $SESSION_NAME:0 "bash"

# Pane 1 (Bottom): Launch replica benchmark suite
tmux send-keys -t $SESSION_NAME:0.1 "sleep 1 && python3 scripts/run_replica_suite.py" C-m

# Attach to session
tmux attach-session -t $SESSION_NAME
