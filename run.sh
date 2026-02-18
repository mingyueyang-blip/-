#!/bin/bash
cd "$(dirname "$0")"
# macOS 上通常没有 python 命令，请用 python3；若已安装 streamlit 可直接运行
if command -v python3 &>/dev/null; then
  exec python3 -m streamlit run app.py --server.headless true
else
  echo "未找到 python3，请先安装 Python 3 或使用: py -3 -m streamlit run app.py"
  exit 1
fi
