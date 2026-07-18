#!/usr/bin/env bash
# Destination in your repo: .claude/hooks/check-okf-version.sh
# No chmod needed: settings.json invokes this via `bash`.
#
# SessionStart hook: compares the OKF version this repo declares in its stamp
# file (docs/index.md by default; relocatable via the layout block in
# docs/okf-map.yml, ADR 0018) against the latest spec version published on the
# OKF main branch, and the kit_version it declares against the kit's published
# VERSION file. When either differs, it injects a note into Claude's context;
# the "OKF version policy" and "Kit version policy" sections in the repo
# playbook tell the agent what to do. It also counts ADRs still proposed
# (frontmatter status:, a "- Status:" bullet, or a "# Status" section) so the
# owner's review inbox stays visible at session start (offline, local scan
# only).
# Fails silent (exit 0, no output) when offline, when the stamp file is absent
# or declares no okf_version / kit_version, or if upstream layouts change.

SPEC_URL="https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md"
KIT_VERSION_URL="https://raw.githubusercontent.com/lilabrooks/claude-okf-repo-kit/main/VERSION"
ROOT="${CLAUDE_PROJECT_DIR:-${CODEX_PROJECT_DIR:-.}}"

MAP_FILE=""
for map_candidate in "$ROOT/docs/okf-map.yml" "$ROOT/okf-map.yml"; do
  if [ -f "$map_candidate" ]; then
    MAP_FILE="$map_candidate"
    break
  fi
done

# Minimal copy of the scripts/okf layout parser (ADR 0018), kept inline so an
# unmodified copy of this hook still works when mirrored into another agent's
# config without scripts/okf beside it.
layout_value() {
  key="$1"
  default="$2"
  value=""
  if [ -n "$MAP_FILE" ]; then
    value="$(awk -v key="$key" '
      function clean(s) {
        gsub(/#.*/, "", s)
        gsub(/^[[:space:]"'\'']+/, "", s)
        gsub(/[[:space:]"'\'']+$/, "", s)
        return s
      }
      /^layout:/ { in_layout = 1; next }
      /^[^[:space:]#]/ { in_layout = 0 }
      in_layout {
        line = $0
        sub(/^[[:space:]]+/, "", line)
        if (index(line, key ":") == 1) {
          sub(key ":", "", line)
          print clean(line)
          exit
        }
      }
    ' "$MAP_FILE")"
  fi
  if [ -n "$value" ]; then
    printf '%s\n' "${value%/}"
  else
    printf '%s\n' "$default"
  fi
}

STAMP_REL="$(layout_value stamp_file docs/index.md)"
ADR_DIR_REL="$(layout_value adr_dir docs/adr)"
STAMP="$ROOT/$STAMP_REL"

notes=""

append_note() {
  if [ -n "$notes" ]; then
    notes="$notes $1"
  else
    notes="$1"
  fi
}

# No stamp file, or no okf_version declared in it, means the policy is
# inactive and the check stays silent — the same contract kit_version has
# always had. Brownfield repos that keep no bundle root are not nagged every
# session (ADR 0018). The network fetch is skipped entirely in that case.
declared=$(grep -m1 -oE 'okf_version:[[:space:]]*"?[0-9]+\.[0-9]+"?' "$STAMP" 2>/dev/null \
  | grep -oE '[0-9]+\.[0-9]+')

if [ -n "$declared" ]; then
  latest=$(curl -fsSL --max-time 5 "$SPEC_URL" 2>/dev/null \
    | grep -m1 -oE 'Version [0-9]+\.[0-9]+' | grep -oE '[0-9]+\.[0-9]+')
  if [ -n "$latest" ] && [ "$latest" != "$declared" ]; then
    append_note "OKF version check: the latest OKF spec version on the official main branch is $latest. This repo's $STAMP_REL declares okf_version $declared. The OKF version policy in the repo playbook (CLAUDE.md; AGENTS.md if present) applies."
  fi
fi

kit_declared=$(grep -m1 -oE 'kit_version:[[:space:]]*"?[0-9]+\.[0-9]+\.[0-9]+"?' "$STAMP" 2>/dev/null \
  | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')

if [ -n "$kit_declared" ]; then
  kit_latest=$(curl -fsSL --max-time 5 "$KIT_VERSION_URL" 2>/dev/null \
    | grep -m1 -oE '[0-9]+\.[0-9]+\.[0-9]+')
  if [ -n "$kit_latest" ] && [ "$kit_latest" != "$kit_declared" ]; then
    append_note "Kit version check: this repo's $STAMP_REL says it was installed from claude-okf-repo-kit $kit_declared and the published kit version is $kit_latest. The Kit version policy in the repo playbook (CLAUDE.md; AGENTS.md if present) applies."
  fi
fi

# ADR review inbox: count ADRs whose status is `proposed`, skipping the index
# and installer-written numbered review candidates — the same files
# `scripts/okf pending` lists, with the same tolerant status detection
# (frontmatter `status:`, then a `- Status:` bullet, then a `# Status`
# section, normalized to the lowercased first word; ADR 0018).
pending_count=0
for adr in "$ROOT/$ADR_DIR_REL"/*.md; do
  [ -e "$adr" ] || continue
  case "$(basename "$adr")" in
    index.md|*.[0-9].md|*.[0-9][0-9].md) continue ;;
  esac
  status=$(grep -m1 -E '^status:' "$adr" 2>/dev/null | sed -E 's/^status:[[:space:]]*//; s/[[:space:]]+$//')
  if [ -z "$status" ]; then
    status=$(grep -m1 -E '^[-*][[:space:]]*[Ss]tatus:' "$adr" 2>/dev/null | sed -E 's/^[-*][[:space:]]*[Ss]tatus:[[:space:]]*//; s/[[:space:]]+$//')
  fi
  if [ -z "$status" ]; then
    status=$(awk 'found && NF { print; exit } /^#+[[:space:]]*[Ss]tatus[[:space:]]*$/ { found = 1 }' "$adr" 2>/dev/null)
  fi
  status=$(printf '%s' "$status" | awk '{ print tolower($1) }' | sed -E 's/[^a-z]+$//')
  [ "$status" = "proposed" ] && pending_count=$((pending_count + 1))
done

if [ "$pending_count" -gt 0 ]; then
  append_note "ADR review inbox: $pending_count ADR(s) are status: proposed awaiting the owner's review. List them with: bash scripts/okf pending. The decision policy in the repo playbook applies."
fi

if [ -n "$notes" ]; then
  cat <<EOF
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "$notes"}}
EOF
fi

exit 0
