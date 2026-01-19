from config import ELECTIONS_FILE
import os
import json
from flask import has_request_context, request

def route():
    if has_request_context():
        return request.endpoint
    return None  # or a default string like "no_request_context"



def get_election_data(current_election):
    print("____Get election:",current_election)
    CurrentElection = {}   # ✅ guarantee existence
    file_path = ELECTIONS_FILE.replace(".json",f"-{current_election}.json")
    print(f"____Reading CurrentElection under {route()} from File:{file_path}")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                CurrentElection = json.load(f)

            print(f"___get_election_data {current_election} Loaded Data: {CurrentElection }" )
        except Exception as e:
            print(f"❌ Failed to read {file_path} Election JSON: {e}")
    else:
        file_path = ELECTIONS_FILE.replace(".json",f"-DEMO.json")
        try:
            with open(file_path, 'r') as f:
                CurrentElection = json.load(f)
            print(f"___Loaded DEMO Election Data:{ current_election }: {CurrentElection }" )

        except Exception as e:
            print(f"❌ Failed to read {file_path} Election JSON: {e}")

    return CurrentElection

def get_tags_json(election_tags):
    valid_tags = election_tags
    task_tags = {}
    outcome_tags = {}
    for tag, description in valid_tags.items():
        if tag.startswith('L'):
            task_tags[tag] = description
        elif tag.startswith('M'):
            outcome_tags[tag] = description
    print(f"___Dash  Task Tags {valid_tags} Outcome Tags: {outcome_tags}")
    return task_tags, outcome_tags

# the general list of  election data files and proessing streams
