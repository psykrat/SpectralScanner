import json
import os
import subprocess
import xml.etree.ElementTree as ET
import threading
import logging
import sys
import argparse
import re
from concurrent.futures import ThreadPoolExecutor

# Create a thread pool executor
executor = ThreadPoolExecutor(max_workers=10)

def is_valid_ipv4(ip):
    """ Validate IP address """
    pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
    return bool(pattern.match(ip))

def run_command(command, output_file, timeout=None):
    with open(output_file, 'w') as f:
        try:
            if dry_run:
                print(f"Dry-run: {command}")
                return True
            else:
                process = subprocess.Popen(command, shell=True, stdout=f, stderr=subprocess.STDOUT)
                process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            logging.error(f"Command '{command}' timed out. Terminating process.")
            process.terminate()
        except Exception as e:
            logging.error(f"Failed to run command '{command}'. Error: {str(e)}")
            return False
        return process.returncode == 0

def command_exists(command):
    return subprocess.call("type " + command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

def run_tools(service, targetURL, output_file):
    if service == 'http':
        logging.info("HTTP service found. Running dirb and nikto...")
        executor.submit(run_command, f"dirb {targetURL}", f"{output_file}_dirb.txt", timeout=config['dirb']['timeout'])
        executor.submit(run_command, f"nikto -h {targetURL}", f"{output_file}_nikto.txt", timeout=config['nikto']['timeout'])

    elif service == 'ssh':
        logging.info("SSH service found. Running hydra...")
        executor.submit(run_command, f"hydra -l {config['hydra']['username']} -P {config['hydra']['passlist']} ssh://{targetURL}", f"{output_file}_hydra.txt", timeout=config['hydra']['timeout'])

    elif service == 'smb' or service == 'netbios-ssn':
        logging.info("SMB service found. Running enum4linux...")
        executor.submit(run_command, f"enum4linux {targetIP}", f"{output_file}_enum4linux.txt", timeout=config['enum4linux']['timeout'])

def main(targetIP, projectName, dry_run):
    # Load config
    with open('config.json') as f:
        config = json.load(f)

    # Setup logging
    log_level = logging.getLevelName(config.get('log_level', 'INFO'))
    logging.basicConfig(filename='script.log', level=log_level)

    # Validate target IP
    if not is_valid_ipv4(targetIP):
        logging.error("Invalid target IP. Exiting.")
        return

    # Define file names for output
    xmlOutput = f"{projectName}.xml"
    output_prefix = f"{projectName}"

    # Define the URL for tools
    targetURL = f"http://{targetIP}"

    # Check that required tools are installed
    required_tools = ['nmap', 'nbtscan', 'whois', 'theHarvester', 'dirb', 'nikto', 'hydra', 'enum4linux']
    for tool in required_tools:
        if not command_exists(tool):
            logging.error(f"Required tool {tool} is not installed. Please install it before running this script.")
            return

    # Run the nmap command
    logging.info("Running nmap command...")
    if not run_command(f"sudo nmap -T4 -sC -sV -p- --min-rate=1000 -oX {xmlOutput} {targetIP}", xmlOutput, timeout=config['nmap']['timeout']):
        logging.error("Nmap command failed. Exiting.")
        return

    # Parse the nmap XML output to check for services
    logging.info("Parsing nmap output and running appropriate tools...")
    tree = ET.parse(xmlOutput)
    root = tree.getroot()

    for host in root.iter('host'):
        for ports in host.iter('ports'):
            for port in ports.iter('port'):
                service = port.find('service').get('name')
                executor.submit(run_tools, service, targetURL, output_prefix)

    # Wait for all threads to finish
    executor.shutdown(wait=True)

    logging.info("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Network scanning tool')
    parser.add_argument('targetIP', help='Target IP')
    parser.add_argument('projectName', help='Project name')
    parser.add_argument('--dry-run', action='store_true', help='Dry run: show commands without running them')
    args = parser.parse_args()

    main(args.targetIP, args.projectName, args.dry_run)
