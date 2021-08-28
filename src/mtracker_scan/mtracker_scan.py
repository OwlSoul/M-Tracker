#!/usr/bin/env python3

'''
    M-Tracker scan, will scan the folder for tracker files.
'''

import json
import sys
import os
from datetime import datetime
import argparse

VERSION = "0.0.1"

MARKER_FILENAME = ".mtracker.mtr"

def get_current_marker_data(marker_file_name):
    ''' Try to load the current marker, if present '''
    marker_data = {}
    if os.path.exists(marker_file_name) and os.path.isfile(marker_file_name):
        try:
            with open(marker_file_name, "r") as f:
                data = f.read()
            marker_data = json.loads(data)
        except (IOError, IndexError):
            pass
    return marker_data

def write_marker_data(marker_file_name, marker_data):
    ''' Writes marker data to a file'''
    with open(marker_file_name, 'w') as f:
        f.write(json.dumps(marker_data, indent=4))
        f.close()

def linux_path_to_windows_path(linux_path):
    ''' Converts WSL Linux path to Windows path'''
    if not linux_path.startswith('/mnt/'):
        return linux_path
    try:
        drive_letter = linux_path.split("/")[2]
    except IndexError:
        return linux_path
    if len(drive_letter) > 1:
        return linux_path
    return linux_path.replace(f'/mnt/{drive_letter}', f'{drive_letter}:').replace('/', '\\')

def process_marker(marker_path, marker_filename, device_marker):
    ''' Process marker'''
    print(f"M-TRACKER MARKER: {marker_path}")
    marker_data = get_current_marker_data(marker_filename)
    if not marker_data:
        print(f"Marker file {marker_path} is corrupted")
        return

    # Correct path history
    for resource_id, marker_data_entry in marker_data.items():
        print("  {0:<10} {1:<40} {2:<40} {3:<40}".format(f"[{device_marker}]",
                                                         f"[{resource_id}]",
                                                         marker_data_entry.get('resource_name',
                                                                               'RESOURCE_NAME_MISSING'),
                                                         marker_data_entry.get('resource_description',
                                                                               'RESOURCE_DESCRIPTION_MISSING')))
        if 'path_history' in marker_data_entry:
            add_path = True
            for entry in marker_data_entry['path_history']:
                try:
                    path = entry.split(',')[1]
                    if path == marker_path:
                        add_path = False
                except IndexError:
                    return
            if add_path:
                marker_data[resource_id]['path_history'].append(datetime.now()
                                                                .strftime("%Y-%m-%d %H:%M:%S") + \
                                                                ',' + marker_path)
    write_marker_data(marker_filename, marker_data)
    print()

def main():
    ''' M-Tracker scan main()'''
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--scan_path',
                        help='Path to scan')
    parser.add_argument('--device_marker', default='',
                        help='Device marker (optional)')

    args = parser.parse_args()

    scan_path = args.scan_path
    device_marker = args.device_marker

    if args.scan_path is None:
        scan_path = os.popen('pwd').readline().strip()
    print(f"M-TRACKER SCAN SYSTEM: Version v{VERSION}")
    print("Scan path:", scan_path, "\n")

    for root, _dirs, _files in os.walk("."):
        marker_path = root.replace(".", scan_path, 1)
        marker_filename = marker_path + '/' + MARKER_FILENAME
        # Convert the file path to Windows if on WSL
        os_check = os.popen('cat /proc/version').read()
        if 'WSL' in os_check:
            marker_path = linux_path_to_windows_path(marker_path)
        # Traverse all directories
        if os.path.isfile(marker_filename):
            process_marker(marker_path, marker_filename, device_marker)

if __name__ == '__main__':
    main()
    sys.exit(0)
