from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import os
import time
import signal

class RestartOnChange(FileSystemEventHandler):
    def __init__(self, command):
        self.command = command
        self.process = None
        self.start_process()

    def start_process(self):
        if self.process:
            print("🔁 Restarting Flask app...")
            os.kill(self.process.pid, signal.SIGTERM)
        self.process = subprocess.Popen(self.command, shell=True)

    def on_modified(self, event):
        if event.src_path.endswith(".py") or event.src_path.endswith(".json"):
            print(f"📦 Change detected in {event.src_path}")
            self.start_process()

if __name__ == "__main__":
    watch_path = "."  # Current folder
    flask_command = "python serve.py"

    event_handler = RestartOnChange(flask_command)
    observer = Observer()
    observer.schedule(event_handler, path=watch_path, recursive=True)
    observer.start()
    print("👀 Watching for file changes...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
