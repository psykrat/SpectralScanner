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
from shlex import quote

# Create a thread pool executor
executor = ThreadPoolExecutor(max_workers=10)

def is_valid_ipv4(ip):
    """ Validate IP address """
    pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
    return bool(pattern.match(ip))

def run_command(command, output_file, timeout=None):
    with open(output_file, 'w') as f:
        try:
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

def run_tools(port_service, targetIP, output_file, config):
    port, service = port_service

    if service == 'http':
        targetURL = f"http://{targetIP}:{port}"
        logging.info(f"HTTP service found on port {port}. Running dirb and nikto...")
        run_command(f"dirb {quote(targetURL)}", f"{output_file}_dirb_{port}.txt", timeout=config['dirb']['timeout'])
        run_command(f"nikto -h {quote(targetURL)}", f"{output_file}_nikto_{port}.txt", timeout=config['nikto']['timeout'])

    elif service == 'ssh':
        targetURL = f"ssh://{targetIP}:{port}"
        logging.info(f"SSH service found on port {port}. Running hydra...")
        run_command(f"hydra -l {quote(config['hydra']['username'])} -P {quote(config['hydra']['passlist'])} {quote(targetURL)}", f"{output_file}_hydra_{port}.txt", timeout=config['hydra']['timeout'])

    elif service == 'smb' or service == 'netbios-ssn':
        logging.info("SMB service found. Running enum4linux...")
        run_command(f"enum4linux {quote(targetIP)}", f"{output_file}_enum4linux.txt", timeout=config['enum4linux']['timeout'])

def parse_nmap_output(file_path):
    services = []

    with open(file_path, 'r') as file:
        lines = file.readlines()

    for line in lines:
        if "/tcp" in line:
            service_info = line.split()
            port = service_info[0].split("/")[0]
            service = service_info[2]
            services.append((port, service))

    return services

def main(targetIP, projectName, dry_run=False, log_file='script.log'):
    # Load config
    with open('config.json') as f:
        config = json.load(f)

    # Setup logging
    log_level = logging.getLevelName(config.get('log_level', 'INFO'))
    logging.basicConfig(filename=log_file, level=log_level)

    # Validate target IP
    if not is_valid_ipv4(targetIP):
        logging.error("Invalid target IP. Exiting.")
        return

    # Define file names for output
    xmlOutput = f"{projectName}.xml"
    txtOutput = f"{projectName}.txt"
    output_prefix = f"{projectName}"

    # Check that required tools are installed
    required_tools = ['nmap', 'nbtscan', 'whois', 'theHarvester', 'dirb', 'nikto', 'hydra', 'enum4linux']
    for tool in required_tools:
        if not command_exists(tool):
            logging.error(f"Required tool {tool} is not installed. Please install it before running this script.")
            return

    # Run the nmap command
    logging.info("Running nmap command...")
    if not run_command(f"sudo nmap -T4 -sC -sV -oX {quote(xmlOutput)} {quote(targetIP)} > {quote(txtOutput)}", xmlOutput, timeout=config['nmap']['timeout']):
        logging.error("Nmap command failed. Exiting.")
        return

    # Parse the nmap output and run appropriate tools
    logging.info("Parsing nmap output and running appropriate tools...")
    services = parse_nmap_output(txtOutput)

    for port_service in services:
        executor.submit(run_tools, port_service, targetIP, output_prefix, config)

    # Wait for all threads to finish
    executor.shutdown(wait=True)

    logging.info("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Network scanning tool')
    parser.add_argument('targetIP', help='Target IP')
    parser.add_argument('projectName', help='Project name')
    parser.add_argument('--dry-run', action='store_true', help='Dry run: show commands without running them')
    parser.add_argument('--log-file', default='script.log', help='Log file location')
    args = parser.parse_args()

    main(args.targetIP, args.projectName, args.dry_run, args.log_file)
