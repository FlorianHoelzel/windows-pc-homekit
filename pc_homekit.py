import socket
import threading
import urllib.error
import urllib.request

from pyhap.accessory import Accessory
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_TELEVISION


# ============================================================
# CONFIG
# ============================================================

from config import load_config

settings = load_config("controller")
PC_NAME = settings["PC_NAME"]
PC_IP = settings["PC_IP"]
PC_MAC = settings["PC_MAC"]
WOL_SOURCE_IP = settings["WOL_SOURCE_IP"]
WOL_BROADCAST_IP = settings["WOL_BROADCAST_IP"]
AGENT_PORT = settings["AGENT_PORT"]
AGENT_TOKEN = settings["AGENT_TOKEN"]
HOMEKIT_PORT = settings["HOMEKIT_PORT"]
PERSIST_FILE = settings["PERSIST_FILE"]
PINCODE = settings["PINCODE"].encode("ascii")
POLL_INTERVAL = settings["POLL_INTERVAL"]


# ============================================================
# WINDOWS AGENT
# ============================================================

def agent_request(path, method="GET"):
    url = f"http://{PC_IP}:{AGENT_PORT}/{path}"

    request = urllib.request.Request(
        url,
        method=method,
        headers={
            "X-PC-Token": AGENT_TOKEN
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=2
        ) as response:

            return 200 <= response.status < 300

    except (
        urllib.error.URLError,
        TimeoutError,
        ConnectionError
    ):
        return False


def pc_is_online():
    return agent_request("status")


def send_command(command):
    print(f"Sending command: {command}")

    success = agent_request(
        command,
        method="POST"
    )

    if success:
        print(f"Command successful: {command}")
    else:
        print(f"Command failed: {command}")

    return success


# ============================================================
# WAKE ON LAN
# ============================================================

def wake_pc():
    """
    Sendet ein Wake-on-LAN Magic Packet gezielt über
    die direkte Ethernet-Verbindung Raspberry Pi -> PC.
    """

    print("Sending Wake-on-LAN packet via Ethernet...")

    mac = (
        PC_MAC
        .replace(":", "")
        .replace("-", "")
        .replace(" ", "")
    )

    if len(mac) != 12:
        print("Invalid MAC address")
        return

    try:
        mac_bytes = bytes.fromhex(mac)

    except ValueError:
        print("Invalid MAC address")
        return

    magic_packet = (
        b"\xff" * 6
        + mac_bytes * 16
    )

    try:
        with socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        ) as sock:

            sock.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_BROADCAST,
                1
            )

            # Magic Packet ausdrücklich über Ethernet senden
            sock.bind(
                (WOL_SOURCE_IP, 0)
            )

            sock.sendto(
                magic_packet,
                (WOL_BROADCAST_IP, 9)
            )

        print(
            f"Wake-on-LAN packet sent via "
            f"{WOL_SOURCE_IP} -> {WOL_BROADCAST_IP}"
        )

    except OSError as error:
        print(f"Wake-on-LAN error: {error}")


# ============================================================
# HOMEKIT ACCESSORY
# ============================================================

class PCHomeKit(Accessory):

    category = CATEGORY_TELEVISION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.last_online = None

        self.set_info_service(
            manufacturer="Custom",
            model="Windows PC",
            serial_number="PC-001",
            firmware_revision="4.0"
        )

        # ====================================================
        # TELEVISION
        # ====================================================

        self.tv_service = self.add_preload_service(
            "Television",
            chars=[
                "Name"
            ]
        )

        self.tv_service.display_name = PC_NAME

        self.tv_service.configure_char(
            "Name",
            value=PC_NAME
        )

        self.tv_name_char = self.tv_service.configure_char(
            "ConfiguredName",
            value=PC_NAME,
            getter_callback=self.get_tv_name,
            setter_callback=self.set_tv_name
        )

        self.tv_service.configure_char(
            "SleepDiscoveryMode",
            value=1
        )

        self.active_char = self.tv_service.configure_char(
            "Active",
            value=0,
            setter_callback=self.set_power
        )

        self.set_primary_service(
            self.tv_service
        )

        # ====================================================
        # INITIAL STATUS
        # ====================================================

        online = pc_is_online()

        self.last_online = online

        self.active_char.set_value(
            1 if online else 0
        )

        print(
            "Initial PC status:",
            "online" if online else "offline"
        )


    # ========================================================
    # TV NAME
    # ========================================================

    def get_tv_name(self):
        return PC_NAME


    def set_tv_name(self, value):
        print(
            f"HomeKit tried to rename television "
            f"from '{PC_NAME}' to '{value}'"
        )

        if value != PC_NAME:
            self.tv_name_char.set_value(
                PC_NAME
            )


    # ========================================================
    # POWER
    # ========================================================

    def set_power(self, value):

        if value == 1:

            print("Power ON requested")

            threading.Thread(
                target=self.power_on,
                daemon=True
            ).start()

        else:

            print("Power OFF requested")

            threading.Thread(
                target=self.power_off,
                daemon=True
            ).start()


    def power_on(self):

        if pc_is_online():

            print("PC is already online")

            self.active_char.set_value(1)

            return

        # PC-Agent nicht erreichbar -> PC ist aus
        # -> Wake-on-LAN über direkte Ethernet-Verbindung
        wake_pc()


    def power_off(self):

        if not pc_is_online():

            print("PC is already offline")

            self.active_char.set_value(0)

            return

        send_command("shutdown")


    # ========================================================
    # STATUS MONITORING
    # ========================================================

    @Accessory.run_at_interval(POLL_INTERVAL)
    def run(self):

        online = pc_is_online()

        if online != self.last_online:

            print(
                "PC status changed:",
                "online" if online else "offline"
            )

            self.last_online = online

        new_value = 1 if online else 0

        if self.active_char.value != new_value:

            self.active_char.set_value(
                new_value
            )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    driver = AccessoryDriver(
        port=HOMEKIT_PORT,
        persist_file=PERSIST_FILE,
        pincode=PINCODE
    )

    accessory = PCHomeKit(
        driver,
        PC_NAME
    )

    driver.add_accessory(
        accessory
    )

    print("=" * 50)
    print("PC HomeKit Controller")
    print("=" * 50)
    print(f"Name:          {PC_NAME}")
    print(f"PC WLAN IP:    {PC_IP}")
    print(f"Agent port:    {AGENT_PORT}")
    print(f"HomeKit port:  {HOMEKIT_PORT}")
    print(f"WOL source:    {WOL_SOURCE_IP}")
    print(f"WOL broadcast: {WOL_BROADCAST_IP}")
    print("=" * 50)

    driver.start()
