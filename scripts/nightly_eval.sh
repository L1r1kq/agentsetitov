#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m agentse eval-llm
python3 -m agentse eval-agent
python3 -m agentse consolidate
echo "nightly eval done"
