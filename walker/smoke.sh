#!/usr/bin/env bash
# Headless smoke test for the Wanderer Godot project.
# Imports resources, then runs the main scene for a few seconds and
# captures any script/runtime errors.
set -u
GODOT="$1"          # path to the godot editor binary
PROJ="/home/user/walker/godot"

echo "=== godot version ==="
"$GODOT" --version
echo

echo "=== import resources (headless) ==="
"$GODOT" --headless --path "$PROJ" --import 2>&1 | tail -40
echo "import_exit=$?"
echo

echo "=== run main scene headless for 600 frames ==="
"$GODOT" --headless --path "$PROJ" --quit-after 600 2>&1 | tail -60
echo "run_exit=$?"
