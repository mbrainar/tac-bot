#! /usr/bin/python

"""
utilities.py file contains supporting functions for bot.py
"""

import re
import requests
import os
from ciscosparkapi import CiscoSparkAPI
from case import CaseDetail

spark_token = os.environ.get("SPARK_BOT_TOKEN")
spark = CiscoSparkAPI(access_token=spark_token)


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
def verify_case_number(content):
    # Check if there is a case number in the incoming message content
    pattern = re.compile("(6[0-9]{8})")
    match = pattern.search(content)

    if match:
        case_number = match.group(0)
        return case_number
    else:
        return False


# Check for case number in message content, if none check in room name
def get_case_number(content, room_id):
    case_number = verify_case_number(content)
    if case_number:
        return case_number
    else:
        room_name = get_room_name(room_id)
        case_number = verify_case_number(room_name)
        if case_number:
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

        return response.json()
    else:
        response.raise_for_status()


#
# Spark functions
#

# Get all rooms name matching case number
def get_rooms(case_number):
    rooms = spark.rooms.list()
    matches = [x for x in rooms if str(case_number) in x.title]
    return matches


# Get Spark room name using CiscoSparkAPI
def get_room_name(room_id):
    room_name = spark.rooms.get(room_id).title
    return room_name


# Create Spark Room
def create_room(case_number):
    case = CaseDetail(get_case_details(case_number))
    title = case.title
    if title:
        data = "SR {}: {}".format(case_number, title)
    else:
        data = "SR {}".format(case_number)

    new_room = spark.rooms.create(data)
    return new_room.id


# Get room membership
def get_membership(room_id):
    memberships= spark.memberships.list(roomId=room_id)
    return memberships


# Get person_id for email address
def get_person_id(email):
    if check_email_syntax(email):
        person = spark.people.list(email=email)

        # Future capabilities of Spark allow for multiple emails.
        # Today, iterating through GeneratorContainer created by CiscoSparkAPI will yield only one personId.
        # This may break in the future if GeneratorContainer returns multiple items
        for p in person:
            person_id = p.id
        return person_id
    else:
        return False


# Get email address for provided personId
def get_email(person_id):
    # Future capabilities of Spark allow for multiple emails.
    # Today, iterating through GeneratorContainer created by CiscoSparkAPI will yield only one personId.
    # This may break in the future if GeneratorContainer returns multiple items
    email = spark.people.get(person_id).emails[0]
    return email


# Create membership
def create_membership(person_id, new_room_id):
    new_membership = spark.memberships.create(new_room_id, personId=person_id)
    return new_membership.id


# Check if room already exists for case and  user
def room_exists_for_user(case_number, email):
    person_id = get_person_id(email)
    rooms = get_rooms(case_number)
    for r in rooms:
        room_memberships = get_membership(r.id)
        for m in room_memberships:
            if m.personId == person_id:
                return r.id
            else:
                continue
