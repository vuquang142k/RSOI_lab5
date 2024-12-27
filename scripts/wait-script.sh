#!/usr/bin/env bash

IFS="," read -ra PORTS <<<"$WAIT_PORTS"

PIDs=()
for port in "${PORTS[@]}"; do
  ./scripts/wait-for.sh -t 10 "localhost:$port" -- echo "Host localhost:$port is active" &
  PIDs+=($!)
done

for pid in "${PIDs[@]}"; do
  if ! wait "${pid}"; then
    exit 1
  fi
done
