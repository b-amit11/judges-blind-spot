#!/bin/zsh
set -e
cd "$(dirname "$0")"
if [[ -x .venv/bin/python ]]; then
  demo_python="$PWD/.venv/bin/python"
elif [[ -x ../../work/venv/bin/python ]]; then
  demo_python="$PWD/../../work/venv/bin/python"
else
  echo 'Create the environment using README.md, then run this launcher again.'
  read
  exit 1
fi
if curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
  echo 'A Streamlit server is already running. Open http://127.0.0.1:8501'
  read
  exit 0
fi
echo 'Open http://127.0.0.1:8501 in your browser. Press Ctrl+C here to stop.'
"$demo_python" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
