import sys
import time
import subprocess
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os

class ServerProcess:
    def __init__(self):
        self.process = None
        self.should_restart = threading.Event()

    def start(self):
        while True:
            print("\nStarting server...")
            # Use python executable from current environment
            python_exe = sys.executable
            self.process = subprocess.Popen([python_exe, 'app.py'])
            self.should_restart.wait()  # Wait for restart signal
            self.should_restart.clear()
            print("\nStopping server...")
            self.process.terminate()
            self.process.wait()

    def restart(self):
        self.should_restart.set()

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, server_process):
        self.server_process = server_process
        self.last_restart = 0
        self.restart_cooldown = 1  # Minimum seconds between restarts

    def on_any_event(self, event):
        # Ignore directory events and non-relevant files
        if event.is_directory or event.src_path.endswith('.pyc'):
            return

        # Check if enough time has passed since last restart
        current_time = time.time()
        if current_time - self.last_restart < self.restart_cooldown:
            return

        print(f"\nDetected change in {event.src_path}")
        self.last_restart = current_time
        self.server_process.restart()

def main():
    # Create and start server process
    server_process = ServerProcess()
    server_thread = threading.Thread(target=server_process.start)
    server_thread.daemon = True
    server_thread.start()

    # Set up file watching
    event_handler = ChangeHandler(server_process)
    observer = Observer()
    
    # Watch relevant directories
    paths_to_watch = [
        'templates',
        'static',
        '.'  # Watch Python files in root directory
    ]

    for path in paths_to_watch:
        if os.path.exists(path):
            observer.schedule(event_handler, path, recursive=True)
            print(f"Watching directory: {path}")

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server and file watcher...")
        observer.stop()
        if server_process.process:
            server_process.process.terminate()
            server_process.process.wait()
    
    observer.join()

if __name__ == "__main__":
    main() 