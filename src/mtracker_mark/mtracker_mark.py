#!/usr/bin/env python3

'''
    M-Tracker mark, will leave an M-Tracker mark in the folder.
    Interactive tool.
'''
import uuid
import sys
import json
import os
import signal
from datetime import datetime

VERSION = "0.0.1"

# Exit codes
JSON_ENCODING_ERROR = 1
SIGINT_RECEIVED = 2
MARKER_WRITE_FAILED = 3
COLLISION_NOT_CONFIRMED = 4

MARKER_FILENAME = ".mtracker.mtr"

COMMON_RESOURCE_TYPES = {
    "1": "Video, Movies, TV Series",
    "2": "Music, Podcasts, Audio",
    "3": "Video game",
    "4": "Software",
    "5": "Books, Visual Novels, Comics, Manga",
    "0": "Custom (special case)"
}

# Codes from 6 to 49 are currently reserved
RESERVED_RESOURCE_TYPES = []
for i in range(6, 50):
    RESERVED_RESOURCE_TYPES.append(str(i))

def sigint_handler(_signal, _frame):
    '''SIGINT handler'''
    print("\n\nM-Tracker marker setup cancelled.")
    sys.exit(SIGINT_RECEIVED)

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

def get_resource_type():
    ''' Requesting current resource type '''
    while True:
        print("Enter the resource type, use one of the following volumes or a 0 to specify a special case")
        for code, description in COMMON_RESOURCE_TYPES.items():
            print(f" {code}: {description}")
        resource_code = input()

        if resource_code == '0':
            print("Special resource type requested")
            resource_code = input("Resource code:")
            if resource_code in COMMON_RESOURCE_TYPES or resource_code in RESERVED_RESOURCE_TYPES:
                print(f"Code {resource_code} not allowed to be used as a custom resource code\n")
                continue
            resource_description = input("Resource description:")
            return resource_code, resource_description

        if resource_code in RESERVED_RESOURCE_TYPES:
            print(f"Resource code {resource_code} is reserved, pick a different one\n")
            continue
        if resource_code not in COMMON_RESOURCE_TYPES:
            print(f"Unknown resource code {resource_code}, pick a different one\n")
            continue
        resource_description = COMMON_RESOURCE_TYPES[resource_code]
        return resource_code, resource_description

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

def set_resource_id(resource_name, resource_code):
    ''' Set resource ID '''
    proposed_resource_id = "".join([c for c in resource_name if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    proposed_resource_id = proposed_resource_id + '-' + resource_code
    proposed_resource_id = proposed_resource_id + '-' + str(uuid.uuid4())[:8]
    proposed_resource_id = proposed_resource_id.replace(' ', '')

    resource_id = input(f"Confirm or change the resource ID [{proposed_resource_id}]:")
    if resource_id == '':
        resource_id = proposed_resource_id

    return resource_id

def merge_marker_data(marker_data, resource_id, current_path, m_tracker_marker):
    ''' Merge marker data '''
    print(f"Collision detected, resource {resource_id} already tracked")
    print(json.dumps(marker_data[resource_id], indent=4))
    collision_confirm = input("Confirm overwrite (y/N)")
    if collision_confirm.lower() != 'y':
        print("\nM-Tracker marker cancelled by user!")
        sys.exit(COLLISION_NOT_CONFIRMED)
    add_path = True
    if 'path_history' in marker_data[resource_id]:
        for entry in marker_data[resource_id]['path_history']:
            try:
                resource_path = entry.split(',')[2]
                if resource_path == current_path:
                    add_path = False
                    break
            except IndexError:
                pass

    marker_data[resource_id] = m_tracker_marker
    if add_path:
        if 'path_history' in marker_data[resource_id]:
            marker_data[resource_id]['path_history'].append(datetime.now()
                                                            .strftime("%Y-%m-%d %H:%M:%S") + ',' + current_path)
        else:
            marker_data[resource_id]['path_history'] = [datetime.now().strftime("%Y-%m-%d %H:%M:%S") + \
                                                        ',' + current_path]

def main():
    ''' M-Tracker marker main()'''
    signal.signal(signal.SIGINT, sigint_handler)

    print(f"M-TRACKER MARK SYSTEM: Version v{VERSION}")
    # Getting current directory (will be added to tracker file)
    current_path = os.path.dirname(os.path.realpath(__file__))

    # Get current marker filename
    marker_file_name = current_path + '/' + MARKER_FILENAME
    marker_data = get_current_marker_data(marker_file_name)

    # Getting current resource type
    resource_code, resource_description = get_resource_type()

    # Requesting current resource name
    try:
        suggested_resource_name = current_path.split('/')[-1]
    except IndexError:
        suggested_resource_name = ''

    resource_name = input(f"Enter the name of the tracked resource [{suggested_resource_name}]: ")
    if resource_name == '':
        resource_name = suggested_resource_name

    # Generating resource ID
    resource_id = set_resource_id(resource_name, resource_code)

    # Convert the file path to Windows if on WSL
    os_check = os.popen('cat /proc/version').read()
    if 'WSL' in os_check:
        current_path = linux_path_to_windows_path(current_path)

    # Generate M-Tracker marker
    m_tracker_marker = {
        "resource_name": resource_name,
        "resource_code": resource_code,
        "resource_description": resource_description,
    }

    try:
        m_tracker_marker_json = json.dumps(m_tracker_marker, indent=4)
    except ValueError:
        print("Failed to create M-Tracker marker, JSON encoding error!")
        sys.exit(JSON_ENCODING_ERROR)

    # Merging marker data:
    if resource_id in marker_data:
        merge_marker_data(marker_data, resource_id, current_path, m_tracker_marker)
    else:
        m_tracker_marker['path_history'] = [datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ',' + current_path]
        marker_data[resource_id] = m_tracker_marker

    # Writing marker file
    with open(marker_file_name, 'w') as f:
        f.write(json.dumps(marker_data, indent=4))
        f.close()

    print()
    print(f"Marker created: {resource_id}")
    print(m_tracker_marker_json)


if __name__ == '__main__':
    main()
    sys.exit(0)
