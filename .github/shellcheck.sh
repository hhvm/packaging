#!/bin/bash
shellcheck "$0"
FAILURES=()
for FILE in bin/*; do
  read -r FIRST_LINE < "$FILE"
  if [ "${FIRST_LINE}" = "#!/bin/sh" ] || [ "${FIRST_LINE}" = "#!/bin/bash" ]; then
    echo "::group::${FILE}"
    if ! shellcheck --color=always "$FILE"; then
      FAILURES+=("$FILE")
      # Re-run, but take JSON and convert it to the format documented here:
      # https://docs.github.com/en/actions/learn-github-actions/workflow-commands-for-github-actions#setting-an-error-message
      shellcheck -f json "$FILE" | jq -r '.[] | "::error file=\(.file),line=\(.line),col=\(.column),endColumn=\(.endColumn),title=SC\(.code): \(.message)::For more information, see https://www.shellcheck.org/wiki/SC\(.code)"'
    else
      echo "No errors."
    fi
    echo "::endgroup::"
  else
    echo "::debug::Skipping $FILE, not a shell script."
  fi
done

if [ "${#FAILURES[@]}" -ne 0 ]; then
  echo "Failures found in the following files:"
  for FILE in "${FAILURES[@]}"; do
    echo "  $FILE"
  done
  exit 1
fi

echo "No shellcheck errors."
