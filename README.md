# Network Scanning Tool

This script is a network scanning tool developed in Python that scans a target IP and automatically runs different tools based on the services found. The script runs nmap, dirb, nikto, hydra, and enum4linux based on the services detected on the target machine.

## Requirements

- Python 3.x
- nmap
- dirb
- nikto
- hydra
- enum4linux

You can check the installation of these tools using the `command_exists` function in the script.

## Configuration

A JSON configuration file (`config.json`) is used to set parameters for the tools:

```json
{
    "hydra": {
        "username": "user",
        "passlist": "passlist.txt",
        "timeout": 600
    },
    "nmap": {
        "timeout": 600
    },
    "dirb": {
        "timeout": 600
    },
    "nikto": {
        "timeout": 600
    },
    "enum4linux": {
        "timeout": 600
    },
    "log_level": "INFO"
}
```

## Usage

```bash
python3 network_scan.py [target IP] [project name] [--dry-run]
```

- `target IP` is the IP address of the target machine.
- `project name` is the name of the current project. It is used to prefix the output files.
- `--dry-run` (optional) if used, the script will only print the commands that would be executed, without actually running them.

## Note

This script is intended for educational and legitimate network auditing purposes only. Always obtain the necessary permissions and operate within the law when performing network scans and penetration testing. Unauthorized scanning or testing can lead to legal issues.

---

Please tailor this `README.md` to your specific project's needs.
