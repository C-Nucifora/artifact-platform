#!/bin/sh
# Scaffold a new artifact folder: artifacts/<slug>/ with index.html + meta.json.
# Usage: scripts/new-artifact.sh <slug> ["Title"] ["Description"]
set -eu

usage() {
    printf 'usage: %s <slug> ["Title"] ["Description"]\n' "$0" >&2
    printf '  slug: lowercase letters, digits, and inner hyphens (e.g. world-clock)\n' >&2
    exit 2
}

[ "$#" -ge 1 ] || usage

slug=$1
title=${2:-$slug}
description=${3:-}

case $slug in
    '' | *[!a-z0-9-]* | -* | *-)
        printf 'error: invalid slug %s\n' "$slug" >&2
        printf 'slug must be lowercase letters, digits, and inner hyphens\n' >&2
        exit 1
        ;;
esac

# JSON string escaping: backslashes and quotes escaped, control whitespace
# flattened to spaces.
json_escape() {
    printf '%s' "$1" | tr '\n\r\t' '   ' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

repo_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
target="$repo_root/artifacts/$slug"

if [ -e "$target" ]; then
    printf 'error: %s already exists\n' "$target" >&2
    exit 1
fi

mkdir -p "$target"

esc_title=$(json_escape "$title")
esc_description=$(json_escape "$description")

cat > "$target/meta.json" <<EOF
{
  "title": "$esc_title",
  "description": "$esc_description"
}
EOF

cat > "$target/index.html" <<EOF
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>
  body {
    margin: 0;
    min-height: 100vh;
    display: grid;
    place-items: center;
    font: 18px/1.6 ui-sans-serif, system-ui, sans-serif;
    background: #f6f5f2;
    color: #1c1b1a;
  }
  @media (prefers-color-scheme: dark) {
    body { background: #16151a; color: #eceae7; }
  }
  main { text-align: center; padding: 2rem; }
  p { opacity: 0.65; }
</style>
</head>
<body>
<main>
  <h1>$title</h1>
  <p>Replace this placeholder with the real thing.</p>
</main>
</body>
</html>
EOF

printf 'Created %s\n' "$target"
printf 'It is live at /artifacts/%s/ immediately - no restart needed.\n' "$slug"
printf 'The next discovery pass will add it to manifest.json.\n'
