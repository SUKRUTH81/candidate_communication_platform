import os
import subprocess
import sys

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
cmd = ["node", "node_modules/next/dist/bin/next", "start", "-H", "0.0.0.0", "-p", "5173"]
proc = subprocess.Popen(cmd, cwd=frontend_dir)
try:
    proc.wait()
except KeyboardInterrupt:
    proc.terminate()

