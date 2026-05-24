#!/usr/bin/env bash
# Orchestrator for sermon-cuts skill.
#
# Modes:
#   pipeline.sh doctor                         # health-check the environment
#   pipeline.sh <source>                       # ingest + transcribe + vad + propose
#   pipeline.sh --propose-only <source>        # same as above (just clarity)
#   pipeline.sh --render-cut N --slug S        # render cut N for slug S
#   pipeline.sh --render-cuts N,M,P --slug S   # batch render
#   pipeline.sh --reburn-srt N --slug S        # only re-burn subtitles (no retracking)
#
# Render flags:
#   --skip-scrub        skip the 06b SRT lint pass (useful for CI / batch
#                       runs where no human is around to review suspects)
#
# Source can be a YouTube URL or a local .mp4/.mov path.

set -euo pipefail
SKILL_ROOT="$HOME/.claude/skills/sermon-cuts"
SCRIPTS="$SKILL_ROOT/scripts"
PY=python3

usage() {
  sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

[[ $# -eq 0 ]] && usage

# Short-circuit subcommands that don't need arg parsing.
case "${1:-}" in
  doctor)  exec $PY "$SCRIPTS/doctor.py" ;;
  ui)      shift; exec $PY "$SCRIPTS/ui.py" "$@" ;;
  nightly) shift; exec $PY "$SCRIPTS/nightly.py" "$@" ;;
  review)
    shift
    [[ $# -eq 0 ]] && { echo "usage: pipeline.sh review <slug>"; exit 1; }
    # review.py prints the chosen render command to stdout when the user
    # hits ENTER, then we eval it. If the user cancels (q/ESC) or marks
    # nothing, review.py exits non-zero and we stop here.
    CMD=$($PY "$SCRIPTS/review.py" "$1") || exit $?
    echo "→ executando: $CMD"
    exec bash -c "$CMD"
    ;;
esac

MODE="ingest_propose"
SOURCE=""
SLUG=""
CUTS=""
SKIP_SCRUB=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --propose-only) MODE="ingest_propose"; shift;;
    --render-cut)   MODE="render"; CUTS="$2"; shift 2;;
    --render-cuts)  MODE="render"; CUTS="$2"; shift 2;;
    --reburn-srt)   MODE="reburn"; CUTS="$2"; shift 2;;
    --slug)         SLUG="$2"; shift 2;;
    --skip-scrub)   SKIP_SCRUB=1; shift;;
    -h|--help)      usage;;
    *)              SOURCE="$1"; shift;;
  esac
done

# scrub() — runs 06b unless --skip-scrub was passed. Interactive when on a
# TTY (review suggestions y/n/edit/skip), otherwise falls through with
# --auto-apply so batch/CI runs still get the dictionary + high-confidence
# fixes without prompting.
scrub() {
  local idx="$1"
  if [[ "$SKIP_SCRUB" -eq 1 ]]; then
    echo "→ cut #$idx: scrub SRT [skipped — --skip-scrub]"
    return
  fi
  echo "→ cut #$idx: scrub SRT (review suspeitos)"
  if [[ -t 0 ]]; then
    $PY "$SCRIPTS/06b_scrub_srt.py" "$SLUG" "$idx" >/dev/null
  else
    $PY "$SCRIPTS/06b_scrub_srt.py" "$SLUG" "$idx" --auto-apply >/dev/null
  fi
}

case "$MODE" in
  ingest_propose)
    [[ -z "$SOURCE" ]] && { echo "source required"; exit 1; }
    echo "→ [1/4] ingest"
    INGEST_JSON=$($PY "$SCRIPTS/01_ingest.py" "$SOURCE")
    echo "$INGEST_JSON"
    SLUG=$(echo "$INGEST_JSON" | $PY -c "import json,sys; print(json.load(sys.stdin)['slug'])")
    echo "→ [2/4] transcribe (slug=$SLUG)"
    $PY "$SCRIPTS/02_transcribe.py" "$SLUG"
    echo "→ [3/4] VAD"
    $PY "$SCRIPTS/03_vad_segments.py" "$SLUG"
    echo "→ [4/4] propose-cuts input ready"
    $PY "$SCRIPTS/04_propose_cuts.py" "$SLUG"
    echo
    echo "Next: Claude reads propose_input.json + prompts/propose_cuts.md"
    echo "and writes memory/messages/$SLUG/cuts_proposed.json"
    ;;

  render)
    [[ -z "$SLUG" ]] && { echo "--slug required"; exit 1; }
    [[ -z "$CUTS" ]] && { echo "cut index required"; exit 1; }
    IFS=',' read -ra IDXS <<< "$CUTS"
    for IDX in "${IDXS[@]}"; do
      echo "→ cut #$IDX: validate"
      $PY "$SCRIPTS/05_validate_cut.py" "$SLUG" "$IDX" --write-back
      echo "→ cut #$IDX: build SRT"
      $PY "$SCRIPTS/06_build_srt.py" "$SLUG" "$IDX"
      scrub "$IDX"
      echo "→ cut #$IDX: render with tracking + burn legenda"
      $PY "$SCRIPTS/07_render_track.py" "$SLUG" "$IDX"
      echo "→ cut #$IDX: normalize audio"
      $PY "$SCRIPTS/08_audio_normalize.py" "$SLUG" "$IDX" --in-place
      echo "→ cut #$IDX: trim long silences (opt-in)"
      $PY "$SCRIPTS/09_trim_silences.py" "$SLUG" "$IDX" --in-place
    done
    ;;

  reburn)
    [[ -z "$SLUG" ]] && { echo "--slug required"; exit 1; }
    IFS=',' read -ra IDXS <<< "$CUTS"
    for IDX in "${IDXS[@]}"; do
      echo "→ cut #$IDX: rebuild SRT + reburn"
      $PY "$SCRIPTS/06_build_srt.py" "$SLUG" "$IDX"
      scrub "$IDX"
      $PY "$SCRIPTS/07_render_track.py" "$SLUG" "$IDX"
      $PY "$SCRIPTS/08_audio_normalize.py" "$SLUG" "$IDX" --in-place
      $PY "$SCRIPTS/09_trim_silences.py" "$SLUG" "$IDX" --in-place
    done
    ;;
esac
