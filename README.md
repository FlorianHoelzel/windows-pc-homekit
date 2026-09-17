# PC HomeKit

Control a Windows PC from Apple Home using a Python HomeKit controller and
a small Windows agent. The PC appears as a television accessory: switching it
on sends Wake-on-LAN, and switching it off asks the Windows agent to shut down.

## How it works

The controller runs on a Raspberry Pi or another Linux host. It polls the
Windows agent over HTTP every five seconds. An unreachable agent is reported
as offline, even if Windows itself is running.

Wake-on-LAN is sent through a configured local Ethernet address. The original
setup uses a direct Ethernet cable between the Pi and PC, with Wi-Fi carrying
agent requests. Configure the source and broadcast addresses for your network.
Wake-on-LAN must be enabled in the PC's firmware and Ethernet adapter settings.

The current HomeKit interface offers power control only. The agent also has
restart, sleep, lock and application-launch endpoints; these are not exposed by
the current controller. Shutdown and restart force applications to close.

## Controller setup

From the project directory on the Pi:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp config.example.json config.local.json
chmod 600 config.local.json
```

Fill in the local configuration:

| Key | Purpose | Default |
| --- | --- | --- |
| `PC_NAME` | HomeKit accessory name | `PC` |
| `PC_IP` | Windows address reachable by the controller | Required |
| `PC_MAC` | Windows Ethernet adapter MAC address | Required |
| `WOL_SOURCE_IP` | Ethernet address assigned to the controller host | Required |
| `WOL_BROADCAST_IP` | Broadcast address of the Ethernet subnet | Required |
| `AGENT_PORT` | Agent HTTP listener port | `8765` |
| `AGENT_TOKEN` | Shared secret, identical on both machines | Required |
| `HOMEKIT_PORT` | HomeKit listener port | `51831` |
| `PINCODE` | Private HomeKit pairing code in `XXX-XX-XXX` format | Required |
| `PERSIST_FILE` | Local HomeKit identity and pairings | `pc_homekit.state` |
| `POLL_INTERVAL` | Seconds between agent status requests | `5` |

For a new installation, generate a shared token with
`python3 -c 'import secrets; print(secrets.token_urlsafe(32))'` and put it in
both machines' local configurations. Keep an existing installation's token
unless updating both sides together. Choose your own HomeKit pairing code.

```sh
.venv/bin/python pc_homekit.py
```

Use the displayed pairing information to add the accessory in Apple Home.
Keep the controller running and allow HomeKit discovery on your local network.

## Windows agent setup

Install Python on Windows. The agent uses only the Python standard library.
Copy `pc_agent.py`, `config.py` and `agent.config.example.json` into the same
directory on the PC. Copy `agent.config.example.json` to `config.local.json`,
then set the same `AGENT_TOKEN` and `AGENT_PORT` as the controller.

Run `python pc_agent.py` once from that directory to check configuration.
The agent listens on all interfaces. Its token is sent over plain HTTP, so
use it on a trusted local network and restrict the Windows firewall rule for
the agent port to the controller's address. Do not expose it to the internet.

### Start with Task Scheduler

The original installation starts the agent using Windows Task Scheduler.
The existing task was not included in this repository; the following is a
setup guide, not an export of that task.

1. Create a task with an **At log on** trigger for your Windows user.
2. Select **Run only when user is logged on** if you use the agent's desktop
   features, such as locking or launching apps.
3. Add a **Start a program** action. Set **Program/script** to the full path
   of your `python.exe` (or `pythonw.exe` to hide the console).
4. Set **Add arguments** to the quoted full path of `pc_agent.py` and
   **Start in** to its directory.
5. Disable any automatic time limit that would stop the long-running agent.
   Configure restart on failure and avoid starting a second instance.
6. Run the task and check that HomeKit reports the PC as online.

If you already have a working task, retain its settings. When replacing the
old single-file agent, also deploy `config.py` and `config.local.json` before
restarting the task. The controller-side migration does not change files on
your Windows PC.

## Configuration and private files

Both scripts read `config.local.json` beside `config.py`, independently of
Task Scheduler's working directory. Environment variables prefixed with
`PCH_` override individual settings, for example `PCH_AGENT_TOKEN`.
`.env` files are not loaded automatically.

Never commit the local configuration, tokens or HomeKit state. Git ignores
these files, state backups, the virtual environment and the legacy controller.
Preserve the state file to retain existing HomeKit pairings. Custom state
files should use a `.state` extension or live outside the repository.
Share a Git checkout instead of an archive of the entire working directory.

## Troubleshooting

- **Always offline:** ensure the scheduled task is running, both tokens and
  ports match, and the firewall permits access from the controller.
- **Cannot wake:** check the Ethernet MAC address, Wake-on-LAN settings,
  source IP assignment and broadcast address.
- **Cannot pair:** check local HomeKit discovery and the listener port. Keep
  the existing state when restarting or updating an already paired controller.
- **Agent fails after updating:** ensure `config.py` and the private local
  configuration were copied along with `pc_agent.py`.

The HAP-python dependency version matches the original local environment.
