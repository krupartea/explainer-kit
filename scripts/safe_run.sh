#!/bin/bash
# Run a heavy job without endangering the machine (it froze once: 30 GB RAM, no swap, global OOM):
#  - memory cap in its own cgroup scope: if the job exceeds MEM, only the job is OOM-killed
#  - pinned to CORES (default 0-11), so 4 of the 16 cores always stay free for interactive work
#  - lowest CPU priority, low IO priority
# usage: MEM=14G CORES=0-11 scripts/safe_run.sh <command> [args...]
MEM=${MEM:-14G}
CORES=${CORES:-0-11}
exec systemd-run --user --scope --quiet -p MemoryMax=$MEM -p MemorySwapMax=0 -- \
    taskset -c $CORES nice -n 19 ionice -c2 -n7 "$@"
