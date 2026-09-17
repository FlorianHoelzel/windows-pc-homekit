import ctypes
import http.server
import os
import subprocess
import threading
import time
import webbrowser


# ============================================================
# CONFIG
# ============================================================

from config import load_config

settings = load_config("agent")
PORT = settings["AGENT_PORT"]
TOKEN = settings["AGENT_TOKEN"]


# ============================================================
# PC ACTIONS
# ============================================================

def delayed_action(function):
    """
    Wartet kurz, damit die HTTP-Antwort noch gesendet werden kann,
    bevor z. B. Shutdown, Neustart oder Standby ausgeführt wird.
    """

    def worker():
        time.sleep(0.5)
        function()

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


def shutdown_pc():
    print("Shutting down PC...")

    subprocess.run([
        "shutdown",
        "/s",
        "/f",
        "/t",
        "0"
    ])


def restart_pc():
    print("Restarting PC...")

    subprocess.run([
        "shutdown",
        "/r",
        "/f",
        "/t",
        "0"
    ])


def sleep_pc():
    print("Putting PC to sleep...")

    ctypes.windll.powrprof.SetSuspendState(
        False,
        True,
        False
    )


def lock_pc():
    print("Locking PC...")

    ctypes.windll.user32.LockWorkStation()


def launch_steam():
    print("Launching Steam Big Picture...")

    os.startfile("steam://open/bigpicture")


def launch_spotify():
    print("Launching Spotify...")

    os.startfile("spotify:")


def launch_browser():
    print("Launching browser...")

    webbrowser.open("https://www.google.com")


# ============================================================
# HTTP SERVER
# ============================================================

class PCRequestHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format_string, *args):
        # Standard-HTTP-Logging deaktivieren
        return

    def authorized(self):
        return self.headers.get("X-PC-Token") == TOKEN

    def send_text(self, status, text):
        data = text.encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(data))
        )
        self.end_headers()

        self.wfile.write(data)

    def do_GET(self):
        if not self.authorized():
            self.send_text(403, "Forbidden")
            return

        if self.path == "/status":
            self.send_text(200, "online")
            return

        self.send_text(404, "Not found")

    def do_POST(self):
        if not self.authorized():
            self.send_text(403, "Forbidden")
            return

        print(f"Received command: {self.path}")

        if self.path == "/shutdown":
            self.send_text(200, "shutdown")
            delayed_action(shutdown_pc)

        elif self.path == "/restart":
            self.send_text(200, "restart")
            delayed_action(restart_pc)

        elif self.path == "/sleep":
            self.send_text(200, "sleep")
            delayed_action(sleep_pc)

        elif self.path == "/lock":
            self.send_text(200, "lock")
            delayed_action(lock_pc)

        elif self.path == "/launch/steam":
            launch_steam()
            self.send_text(200, "steam")

        elif self.path == "/launch/spotify":
            launch_spotify()
            self.send_text(200, "spotify")

        elif self.path == "/launch/browser":
            launch_browser()
            self.send_text(200, "browser")

        else:
            self.send_text(404, "Not found")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    server = http.server.ThreadingHTTPServer(
        ("0.0.0.0", PORT),
        PCRequestHandler
    )

    print("=" * 50)
    print("PC Agent")
    print("=" * 50)
    print(f"Listening on port {PORT}")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nStopping PC Agent...")

    finally:
        server.server_close()