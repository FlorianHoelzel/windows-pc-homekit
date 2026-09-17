import http.server
import subprocess
import threading
import time


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
    bevor der PC heruntergefahren wird.
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
