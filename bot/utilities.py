#! /usr/bin/python

"""
utilities.py file contains supporting functions for bot.py
"""

import re
import requests
import os

spark_token = os.environ.get("SPARK_BOT_TOKEN")


#
# Supporting functions
#

# Return contents following a given command
def extract_message(command, text):
    cmd_loc = text.find(command)
    message = text[cmd_loc + len(command):]
    return message


# Check if user is cisco.com email address
def check_cisco_user(content):
    pattern = re.compile("^([a-zA-Z0-9_\-\.]+)@(cisco)\.(com)$")

    if pattern.match(content):
        return True
    else:
        return False


# Check if email is syntactically correct
def check_email_syntax(content):
    pattern = re.compile("^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$")

    if pattern.match(content):
        return True
    else:
        return False


# Match case number in string
def get_case_number(content):
    # Check if there is a case number in the incoming message content
    pattern = re.compile("(6[0-9]{8})")
    match = pattern.search(content)

    if match:
        case_number = match.group(0)
        return case_number
    else:
        return False

#
# Case API functions
#

# Get access-token for Case API
def get_access_token():
    client_id = os.environ.get("CASE_API_CLIENT_ID")
    client_secret = os.environ.get("CASE_API_CLIENT_SECRET")
    grant_type = "client_credentials"
    url = "https://cloudsso.cisco.com/as/token.oauth2"
    payload = "client_id="+client_id+"&grant_type=client_credentials&client_secret="+client_secret
    headers = {
        'accept': "application/json",
        'content-type': "application/x-www-form-urlencoded",
        'cache-control': "no-cache"
    }
    response = requests.request("POST", url, data=payload, headers=headers)
    if (response.status_code == 200):
        return response.json()['access_token']
    else:
        response.raise_for_status()


# Get case details from CASE API
def get_case_details(case_number):
    access_token = get_access_token()

    url = "https://api.cisco.com/case/v1.0/cases/details/case_ids/" + str(case_number)
    headers = {
        'authorization': "Bearer " + access_token,
        'cache-control': "no-cache"
    }
    response = requests.request("GET", url, headers=headers)

    if (response.status_code == 200):
        # Uncomment to debug
        # sys.stderr.write(response.text)

        # Check if case was found
        if response.json()['RESPONSE']['COUNT'] == 1:
            return response.json()
        else:
            return False
    else:
        response.raise_for_status()


#
# Spark functions
#

# Get all rooms name matching case number
def get_rooms(case_number):
    url = "https://api.ciscospark.com/v1/rooms/"

    headers = {
        'content-type': "application/json",
        'authorization': "Bearer " + spark_token,
        'cache-control': "no-cache"
    }

    response = requests.request("GET", url, headers=headers)

    if (response.status_code == 200):
        test = [x for x in response.json()['items'] if str(case_number) in x['title']]
        return test
    else:
        response.raise_for_status()


# Get Spark room name
def get_room_name(room_id):
    url = "https://api.ciscospark.com/v1/rooms/" + room_id

    headers = {
        'content-type': "application/json",
        'authorization': "Bearer " + spark_token,
        'cache-control': "no-cache"
    }

    response = requests.request("GET", url, headers=headers)
    if (response.status_code == 200):
        if 'errors' not in response.json():
            return response.json()['title']
        else:
            return False
    else:
        response.raise_for_status()


# Create Spark Room
def create_room(case_number):
    case_title = get_case_title(case_number)
    if case_title:
        data = "{ \"title\": \"SR " + case_number + ": " + case_title + "\" }"
    else:
        data = "{ \"title\": \"SR " + case_number + "\" }"

    url = "https://api.ciscospark.com/v1/rooms"

    headers = {
        'content-type': "application/json",
        'authorization': "Bearer " + spark_token,
        'cache-control': "no-cache"
    }

    response = requests.request("POST", url, headers=headers, data=data)
    if (response.status_code == 200):
        return response.json()['id']
    else:
        response.raise_for_status()


# Get room membership
def get_membership(room_id):
    url = "https://api.ciscospark.com/v1/memberships?roomId=" + room_id
    headers = {
        'content-type': "application/json",
        'authorization': "Bearer " + spark_token,
        'cache-control': "no-cache"
    }

    response = requests.request("GET", url, headers=headers)
    if (response.status_code == 200):
        return response.json()
    else:
        response.raise_for_status()


# Get person_id for email address
def get_person_id(email):
    if check_email_syntax(email):
        url = "https://api.ciscospark.com/v1/people?email=" + email
        headers = {
            'content-type': "application/json",
            'authorization': "Bearer " + spark_token,
            'cache-control': "no-cache"
        }

        response = requests.request("GET", url, headers=headers)
        if (response.status_code == 200):
            if response.json()['items']:
                return response.json()['items'][0]['id']
            else:
                return False
        else:
            response.raise_for_status()
    else:
        return False


# Get email address for provided personId
def get_email(person_id):
    url = "https://api.ciscospark.com/v1/people/" + person_id
    headers = {
        'content-type': "application/json",
        'authorization': "Bearer " + spark_token,
        'cache-control': "no-cache"
    }

    response = requests.request("GET", url, headers=headers)
    if (response.status_code == 200):
        return response.json()['emails'][0]
    else:
        response.raise_for_status()


# Create membership
def create_membership(person_id, new_room_id):
    data = "{ \"roomId\": \"" + new_room_id + "\", \"personId\": \"" + person_id + "\" }"

    url = "https://api.ciscospark.com/v1/memberships"

    headers = {
        'content-type': "application/json",
        'authorization': "Bearer " + spark_token,
        'cache-control': "no-cache"
    }

    response = requests.request("POST", url, headers=headers, data=data)
    if (response.status_code == 200):
        return response.json()['id']
    else:
        response.raise_for_status()


# Check if room already exists for case and  user
def room_exists_for_user(case_number, email):
    person_id = get_person_id(email)
    rooms = get_rooms(case_number)
    for r in rooms:
        room_memberships = get_membership(r['id'])
        for m in room_memberships['items']:
            if m['personId'] == person_id:
                return r['id']
            else:
                continue
