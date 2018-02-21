#! /usr/bin/python
"""
    This Bot will use a provided Spark Account (identified by the Developer Token)
    and create a webhook to receive all messages sent to the account.   You will
    specify a set of command words that the Bot will "listen" for.  Any other message
    sent to the bot will result in the help message being sent back.

    The bot is designed to be deployed as a Docker Container, and can run on any
    platform supporting Docker Containers.  Mantl.io is one example of a platform
    that can be used to run the bot.

    There are several pieces of information needed to run this application.  These
    details can be provided as Environment Variables to the application.  The Spark
    token and email address can alternatively be provided/updated via an POST request to /config.

    If you are running the python application directly, you can set them like this:

    # Details on the Cisco Spark Account to Use
    export SPARK_BOT_EMAIL=myhero.demo@domain.com
    export SPARK_BOT_TOKEN=adfiafdadfadfaij12321kaf

    # Public Address and Name for the Spark Bot Application
    export SPARK_BOT_URL=http://myhero-spark.mantl.domain.com
    export SPARK_BOT_APP_NAME="imapex bot"

    If you are running the bot within a docker container, they would be set like this:
    docker run -it --name sparkbot \
    -e "SPARK_BOT_EMAIL=myhero.demo@domain.com" \
    -e "SPARK_BOT_TOKEN=adfiafdadfadfaij12321kaf" \
    -e "SPARK_BOT_URL=http://myhero-spark.mantl.domain.com" \
    -e "SPARK_BOT_APP_NAME='imapex bot'" \
    sparkbot

    In cases where storing the Spark Email and Token as Environment Variables could
    be a security risk, you can alternatively set them via a REST request.

    curl -X POST http://localhost:5000/config \
        -d "{\"SPARK_BOT_TOKEN\": \"<TOKEN>\", \"SPARK_BOT_EMAIL\": \"<EMAIL>"}"

    You can read the configuration details with this request

    curl http://localhost:5000/config

"""

from flask import Flask, request
from ciscosparkapi import CiscoSparkAPI
import os
import sys
import json
from datetime import datetime, timedelta
from utilities import check_cisco_user, verify_case_number, get_case_details, room_exists_for_user, create_membership, \
                        get_email, get_person_id, create_room, get_room_name, extract_message, get_case_number, \
                        invite_user, check_email_syntax
from case import CaseDetail, Note

# Create the Flask application that provides the bot foundation
app = Flask(__name__)


# ToDos:
    # todo accept multiple case numbers, loop through cases?
    # todo add test cases for low hanging fruit in testing.py
    # todo timezone for tac engineer
    # todo add security check to match domain of user to case contact
    # todo start PSTS engagement
    # todo last note created with "action plan" or "next steps" in note detail
    # todo add RMA API functions
    # todo monitor case and alert on changes


# The list of commands the bot listens for
# Each key in the dictionary is a command
# The value is the help message sent for the command
commands = {
    "/title": "Get title for TAC case.",
    "/description": "Get problem description for the TAC case.",
    "/owner": "Get case owner (TAC CSE) for TAC case.",
    "/contract": "Get contract number associated with the TAC case.",
    "/customer": "Get customer contact info for the TAC case.",
    "/status": "Get status and severity for the TAC case.",
    "/rma": "Get list of RMAs associated with TAC case.",
    "/bug": "Get list of Bugs associated with TAC case.",
    "/device": "Get serial number and hostname for the device on which the TAC case was opened",
    "/created": "Get the date on which the TAC case was created, and calculate the open duration",
    "/updated": "Get the date on which the TAC case was last updated, and calculate the time since last update",
    "/invite": "Invite new user to room by email (or keywords: cse=case owner)",
    "/link": "Get link to the case in Support Case Manager",
    "/feedback": "Sends feedback to development team; use this to submit feature requests and bugs",
    "/last-note": "Sends the contents of the last note attached to the case",
    "/action-plan": "Sends the last note containing \"action plan\"",
    # "/echo": "Reply back with the same message sent.",
    # "/test": "Print test message.",
    "/help": "Get help."
}


# Not strictly needed for most bots, but this allows for requests to be sent
# to the bot from other web sites.  "CORS" Requests
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers',
                         'Content-Type,Authorization,Key')
    response.headers.add('Access-Control-Allow-Methods',
                         'GET,PUT,POST,DELETE,OPTIONS')
    return response


# Entry point for Spark Webhooks
@app.route('/', methods=["GET", "POST"])
def process_webhook():
    if request.method == "GET":
        return "up"

    # Check if the Spark connection has been made
    if spark is None:
        sys.stderr.write("Bot not ready.  \n")
        return "Spark Bot not ready.  "

    post_data = request.get_json(force=True)
    # Uncomment to debug
    # sys.stderr.write("Webhook content:" + "\n")
    # sys.stderr.write(str(post_data) + "\n")

    # Take the posted data and send to the processing function
    process_incoming_message(post_data)
    return ""


# Config Endpoint to set Spark Details
@app.route('/config', methods=["GET", "POST"])
def config_bot():
    if request.method == "POST":
        post_data = request.get_json(force=True)
        # Verify that a token and email were both provided
        if "SPARK_BOT_TOKEN" not in post_data.keys() or "SPARK_BOT_EMAIL" not in post_data.keys():
            return "Error: POST Requires both 'SPARK_BOT_TOKEN' and 'SPARK_BOT_EMAIL' to be provided."

        # Setup Spark
        spark_setup(post_data["SPARK_BOT_EMAIL"], post_data["SPARK_BOT_TOKEN"])

    # Return the config detail to API requests
    config_data = {
        "SPARK_BOT_EMAIL": bot_email,
        "SPARK_BOT_TOKEN": spark_token,
        "SPARK_BOT_URL": bot_url,
        "SPARKBOT_APP_NAME": bot_app_name
    }
    config_data["SPARK_BOT_TOKEN"] = "REDACTED"     # Used to hide the token from requests.
    return json.dumps(config_data)


# Quick REST API to have bot send a message to a user
@app.route("/hello/<email>", methods=["GET"])
def message_email(email):
    """
    Kickoff a 1 on 1 chat with a given email
    :param email:
    :return:
    """
    # Check if the Spark connection has been made
    if spark is None:
        sys.stderr.write("Bot not ready.  \n")
        return "Spark Bot not ready.  "

    # send_message_to_email(email, "Hello!")
    spark.messages.create(toPersonEmail=email, markdown="Hello!")
    return "Message sent to " + email


# Health Check
@app.route("/health", methods=["GET"])
def health_check():
    """
    Notify if bot is up
    :return:
    """
    return "Up and healthy"


# REST API for room creation
@app.route("/create/<provided_case_number>/<email>", methods=["GET"])
def create(provided_case_number, email):
    """
    Start new room for case number and user
    :param provided_case_number, email:
    :return:
    """
    # Check if the Spark connection has been made
    if spark is None:
        sys.stderr.write("Bot not ready.  \n")
        return "Spark Bot not ready.  "

    # Check if provided case number is valid
    case_number = verify_case_number(provided_case_number)
    if case_number:
        # Get person ID for email provided
        person_id = get_person_id(email)
        if person_id:
            #sys.stderr.write("Person ID for email ("+email+"): "+person_id+"\n")

            # Check if room already exists for case and  user
            room_id = room_exists_for_user(case_number, email)
            if room_id:
                message = "Room already exists with  "+case_number+" in the title and "+email+" already a member.\n"
                sys.stderr.write(message)
                sys.stderr.write("roomId: "+room_id+"\n")
            else:
                # Create the new room
                room_id = create_room(case_number)
                message = "Created roomId: "+room_id+"\n"
                sys.stderr.write(message)

                # Add user to the room
                membership_id = create_membership(person_id, room_id)
                membership_message = email+" added to the room.\n"
                sys.stderr.write(membership_message)
                sys.stderr.write("membershipId: "+membership_id+"\n")
                message = message+membership_message

            # Print Welcome message to room
            spark.messages.create(roomId=room_id, markdown=send_help(False))
            welcome_message = "Welcome message (with help command) sent to the room.\n"
            sys.stderr.write(welcome_message)
            message = message+welcome_message
        else:
            message = "No user found with the email address: "+email
            sys.stderr.write(message)
    else:
        message = provided_case_number+" is not a valid case number"
        sys.stderr.write(message)

    return message


# Room counter - returns the number of rooms for which TAC bot is a member
# Useful for tracking utilization of TAC bot
@app.route("/rooms", methods=["GET"])
def room_count():
    """
    Notify if bot is up
    :return:
    """
    return "{}\n".format(sum(1 for x in spark.rooms.list()))


# Function to Setup the WebHook for the bot
def setup_webhook(name, targeturl):
    # Get a list of current webhooks
    webhooks = spark.webhooks.list()

    # Look for a Webhook for this bot_name
    # Need try block because if there are NO webhooks it throws an error
    try:
        for h in webhooks:  # Efficiently iterates through returned objects
            if h.name == name:
                sys.stderr.write("Found existing webhook.  Updating it.\n")
                wh = spark.webhooks.update(webhookId=h.id, name=name, targetUrl=targeturl)
                # Stop searching
                break
        # If there wasn't a Webhook found
        if wh is None:
            sys.stderr.write("Creating new webhook.\n")
            wh = spark.webhooks.create(name=name, targetUrl=targeturl, resource="messages", event="created")
    except:
        sys.stderr.write("Creating new webhook.\n")
        wh = spark.webhooks.create(name=name, targetUrl=targeturl, resource="messages", event="created")

    return wh


# Function to take action on incoming message
def process_incoming_message(post_data):
    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message = spark.messages.get(message_id)
    # Uncomment to debug
    # sys.stderr.write("Message content:" + "\n")
    # sys.stderr.write(str(message) + "\n")

    # First make sure not processing a message from the bot
    if message.personEmail in spark.people.me().emails:
        # Uncomment to debug
        # sys.stderr.write("Message from bot recieved." + "\n")
        return ""

    # Log details on message
    sys.stderr.write("Message from {}: {}\n".format(message.personEmail, message.text))

    # Find the command that was sent, if any
    command = ""
    for c in commands.items():
        if message.text.find(c[0]) != -1:
            command = c[0]
            sys.stderr.write("Found command: " + command + "\n")
            # If a command was found, stop looking for others
            break

    reply = ""
    # Take action based on command
    # If no command found, send help
    if command in ["", "/help"]:
        reply = send_help(post_data)
        sys.stderr.write("Sent help message")
    # elif command in ["/echo"]:
        # reply = send_echo(message)
    # elif command in ["/test"]:
        # reply = send_test()
    elif command in ["/title"]:
        reply = send_title(post_data)
        sys.stderr.write("Replied to {} with:\n{}\n".format(message.personEmail, reply))
    elif command in ["/owner"]:
        reply = send_owner(post_data)
        sys.stderr.write("Replied to {} with:\n{}\n".format(message.personEmail, reply))
    elif command in ["/description"]:
        reply = send_description(post_data)
        sys.stderr.write("Replied to {} with:\n{}\n".format(message.personEmail, reply))
    elif command in ["/contract"]:
        reply = send_contract(post_data)
        sys.stderr.write("Replied to {} with:\n{}\n".format(message.personEmail, reply))
    elif command in ["/customer"]:
        reply = send_customer(post_data)
        sys.stderr.write("Replied to {} with:\n{}\n".format(message.personEmail, reply))
    elif command in ["/status"]:
        reply = send_status(post_data)
        sys.stderr.write("Replied to {} with:\n{}\n".format(message.personEmail, reply))
    elif command in ["/rma"]:
        reply = send_rma_numbers(post_data)
        sys.stderr.write("Replied to {} with:\n{}\n".format(message.personEmail, reply))
    elif command in ["/feedback"]:
        # If feedback is blank, dont send it
        feedback = send_feedback(post_data, "feedback")
        feedback_room = os.environ.get("FEEDBACK_ROOM")
        if feedback is not None:
            spark.messages.create(roomId=feedback_room, markdown=feedback)
            reply = send_feedback(post_data, "reply")
        else:
            reply = "Sorry, cannot submit blank feedback"
    elif command in ["/created"]:
        reply = send_created(post_data)
        sys.stderr.write("Replied to {} with:\n{}\n".format(message.personEmail, reply))
    elif command in ["/updated"]:
        reply = send_updated(post_data)
        sys.stderr.write("Replied to {} with:\n{}\n".format(message.personEmail, reply))
    elif command in ["/device"]:
        reply = send_device(post_data)
        sys.stderr.write("Replied to {} with:\n{}\n".format(message.personEmail, reply))
    elif command in ["/bug"]:
        reply = send_bug(post_data)
        sys.stderr.write("Replied to {} with:\n{}\n".format(message.personEmail, reply))
    elif command in ["/link"]:
        reply = send_link(post_data)
    elif command in ["/invite"]:
        reply = send_invite(post_data)
    elif command in ["/last-note"]:
        reply = send_last_note(post_data)
    elif command in ["/action-plan"]:
        reply = send_action_plan(post_data)

    # send_message_to_room(room_id, reply)
    spark.messages.create(roomId=room_id, markdown=reply)


#
# Command functions
#

# Sends feedback to Bot developers and replies with confirmation
def send_feedback(post_data, type):
    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/feedback", message_in.text)

    # Get personId of the person submitting feedback
    person_id = post_data["data"]["personId"]

    if type == "feedback":
        email = get_email(person_id)
        if content:
            message = "User {} provided the following feedback:<br>{}".format(email, content)
        else:
            message = None
    elif type == "reply":
        message = "Thank you. Your feedback has been sent to developers"
    else:
        message = None

    return message


# Sends feedback to Bot developers and replies with confirmation
def send_link(post_data):
    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/link", message_in.text)

    # Get personId of the person submitting feedback
    person_id = post_data["data"]["personId"]

    external_link_url = "https://mycase.cloudapps.cisco.com/"
    internal_link_url = "http://www-tac.cisco.com/Teams/ks/c3/casekwery.php?Case="

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        message = "* Externally accessible link: {}{}\n".format(external_link_url, case_number)
        message = message + "* Internal link: {}{}".format(internal_link_url, case_number)
    else:
        message = "Invalid case number"

    return message


# Returns case title for provided case number
def send_title(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]


    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/title", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if not case.error:
            case_title = case.title
            message = "Title for SR {} is: {}".format(case_number, case_title)
        else:
            message = "{}".format(case.error)
    else:
        message = "Invalid case number"

    return message


# Returns case title for provided case number
def send_device(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]


    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/device", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if not case.error:
            # Get device info from case
            device_serial = case.serial
            # hostname doesn't exist in case api v3
            # device_hostname = case.hostname
            if device_serial != "":
                message = "Device serial number for SR {} is: {}".format(case_number, device_serial)
            else:
                message = "Device serial number for SR {} is not provided".format(case_number)
        else:
            message = "{}".format(case.error)
    else:
        message = "Invalid case number"

    return message


# Returns case description for provided case number
def send_description(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/description", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if case.count > 0:
            # Get case description
            case_description = case.description
            message = "Problem description for SR {} is: <br>{}".format(case_number, case_description)
        else:
            message = "No case data found matching {}".format(case_number)
    else:
        message = "Invalid case number"

    return message


# Returns the owner of the TAC case number provided
def send_owner(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/owner", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if case.count > 0:
            # Get owner info from case
            owner_id = case.owner_id
            owner_first = case.owner_first
            owner_last = case.owner_last
            owner_email = case.owner_email

            message = "Case owner for SR {} is: {} {} ({})".format(case_number, owner_first, owner_last, owner_email)
        else:
            message = "No case data found matching {}".format(case_number)
    else:
        message = "Invalid case number"

    return message


# Returns contract number for provided case number
def send_contract(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/contract", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if not case.error:
            # Get case description
            case_contract = case.contract
            message = "The contract number used to open SR {} is: {}".format(case_number, case_contract)
        else:
            message = "{}".format(case.error)
    else:
        message = "Invalid case number"

    return message


# Returns the owner of the TAC case number provided
def send_customer(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/customer", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if case.count > 0:
            # Get owner info from case
            customer_id = case.customer_id
            customer_first = case.customer_first
            customer_last = case.customer_last
            customer_email = case.customer_email
            customer_business = case.customer_business
            customer_mobile = case.customer_mobile

            message = "Customer contact for SR {} is: **{} {}**".format(case_number, customer_first, customer_last)
            message = message + "<br>CCO ID: {}".format(customer_id)
            message = message + "<br>Email: {}".format(customer_email) if customer_email else message
            message = message + "<br>Business phone: {}".format(customer_business) if customer_business else message
            message = message + "<br>Mobile phone: {}".format(customer_mobile) if customer_mobile else message
        else:
            message = "No case data found matching {}".format(case_number)
    else:
        message = "Invalid case number"

    return message


# Returns case status and severity for provided case number
def send_status(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/title", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if case.count > 0:
            # Get case status and severity
            case_status = case.status
            case_severity = case.severity
            if "Closed" in case_status:
                message = "Status for SR {} is {}".format(case_number, case_status)
            else:
                message = "Status for SR {} is {} and Severity is {}".format(case_number, case_status, case_severity)
        else:
            message = "No case data found matching {}".format(case_number)
    else:
        message = "Invalid case number"

    return message


# Returns the RMA numbers if any are associated with the case
def send_rma_numbers(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/rma", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    # Define URL for RMA lookup link
    rma_url = "http://msvodb.cloudapps.cisco.com/support/serviceordertool/orderDetails.svo?orderNumber="

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if case.count > 0:
            # Get RMAs from case
            rmas = case.rmas
            if rmas is not None:
                if type(rmas) is list:
                    message = "The RMAs for SR {} are:\n".format(case_number)
                    for r in rmas:
                        message = message + "* <a href=\"{}{}\">{}</a>\n".format(rma_url, r, r)
                else:
                    message = "The RMA for SR {} is: <a href=\"{}{}\">{}</a>".format(case_number, rma_url, rmas,
                                                                                     rmas)
            else:
                message = "There are no RMAs for SR {}".format(case_number)
        else:
            message = "No case data found matching {}".format(case_number)
    else:
        message = "Invalid case number"

    return message


# Returns the Bug IDs if any are associated with the case
def send_bug(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/bug", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    # Define URL for RMA lookup link
    bug_url = "https://bst.cloudapps.cisco.com/bugsearch/bug/"
    internal_bug_url = "http://cdets.cisco.com/apps/dumpcr?&content=summary&format=html&identifier="

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if case.count > 0:
            # Get Bugs from case
            bugs = case.bugs
            if bugs is not None:
                if type(bugs) is list:
                    message = "The Bugs for SR {} are:\n".format(case_number)
                    for b in bugs:
                        message = message + "* {} (<a href=\"{}{}\">external</a> | <a href=\"{}{}\">internal</a>)\n".format(b,bug_url, b, internal_bug_url, b)
                else:
                    message = "The Bug for SR {} is: {} (<a href=\"{}{}\">external</a> | <a href=\"{}{}\">internal</a>)".format(case_number, bugs, bug_url, bugs, internal_bug_url, bugs)
            else:
                message = "There are no Bugs for SR {}".format(case_number)
        else:
            message = "No case data found matching {}".format(case_number)
    else:
        message = "Invalid case number"

    return message


# Returns case creation date for provided case number, and if case is still open return open duration as well
def send_created(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]


    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/created", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if not case.error:
            # Get the creation datetime from the case details
            case_create_date = case.created
            case_create_date = datetime.strptime(case_create_date, '%Y-%m-%dT%H:%M:%SZ')
            message = "Creation date for SR {} is: {}".format(case_number, case_create_date)

            # Get time delta between creation and now; if case is still open, append with open duration
            current_time = datetime.now()
            current_time = current_time.replace(microsecond=0)
            time_delta = current_time - case_create_date
            status = case.status
            if "Closed" not in status:
                message = message + "<br>Case has been open for {}".format(time_delta)
            else:
                message = message + "<br>Case is now Closed"
        else:
            message = "{}".format(case.error)
    else:
        message = "Invalid case number"

    return message


# Returns case last updated date for provided case number, and if case is still open return duration since update as well
def send_updated(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/updated", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if not case.error:
            # Get the update datetime from the case details
            case_update_date = case.updated
            case_update_date = datetime.strptime(case_update_date, '%Y-%m-%dT%H:%M:%SZ')
            message = "Last update for SR {} was: {}".format(case_number, case_update_date)

            # Get time delta between last updated and now
            current_time = datetime.now()
            current_time = current_time.replace(microsecond=0)
            time_delta = current_time - case_update_date
            status = case.status
            if "Closed" in status:
                message = message + "<br>Case is now Closed, {} since case closure".format(time_delta)
            else:
                # If case hasn't been updated in 3 days, make the text bold
                if time_delta > timedelta(3):
                    message = message + "<br>**{} since last update**".format(time_delta)
                else:
                    message = message + "<br>{} since last update".format(time_delta)
        else:
            message = "{}".format(case.error)
    else:
        message = "Invalid case number"

    return message


# Invite user by email or keyword
def send_invite(post_data):
    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/invite ", message_in.text)

    # Check for keywords
    if content == "cse" or content == "CSE":
        case_number = get_case_number(content, room_id)
        case = CaseDetail(get_case_details(case_number))
        if case.count > 0:
            owner_email = case.owner_email
            owner_first = case.owner_first
            owner_last = case.owner_last
            new_membership = invite_user(room_id, owner_email)
            if new_membership:
                message = "Case owner {} {} has been added to the room".format(owner_first, owner_last)
            else:
                message = "Unable to add Case owner to the room at this time"
        else:
            message = "Unable to add Case owner to the room at this time"
    else:
        email = check_email_syntax(content)
        if email:
            new_membership = invite_user(room_id, content)
            if new_membership:
                message = "User {} has been added to the room".format(content)
            else:
                message = "Unable to add user {} to the room".format(content)
        else:
            message = "Error, not a valid email address"

    return message


# Returns the last note attached to the case
def send_last_note(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/last-note", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if case.count > 0:
            # Get case description
            n = case.last_note
            created = datetime.strptime(n.creation_date, '%Y-%m-%dT%H:%M:%SZ')
            note = n.note
            if note == "Please refer to the note detail":
                note = n.note_detail
            message = "The last note on SR {}, updated {} is: <br>{}".format(case_number, created, note)
        else:
            message = "No case data found matching {}".format(case_number)
    else:
        message = "Invalid case number"

    return message


# Returns the last note attached to the case
def send_action_plan(post_data):
    """
    Due to the potentially sensitive nature of TAC case data, it is necessary (for the time being) to limit CASE API
    access to Cisco employees and contractors, until such time as a more appropriate authentication method can be added
    """
    # Check if user is cisco.com
    person_id = post_data["data"]["personId"]
    email = get_email(person_id)
    if not check_cisco_user(email):
        return "Sorry, CASE API access is limited to Cisco Employees for the time being"

    # Determine the Spark Room to send reply to
    room_id = post_data["data"]["roomId"]

    # Get the details about the message that was sent.
    message_id = post_data["data"]["id"]
    message_in = spark.messages.get(message_id)
    content = extract_message("/action-plan", message_in.text)

    # Find case number
    case_number = get_case_number(content, room_id)

    if case_number:
        # Create case object
        case = CaseDetail(get_case_details(case_number))
        if case.count > 0:
            # Get case description
            n = case.action_plan
            if n:
                created = datetime.strptime(n.creation_date, '%Y-%m-%dT%H:%M:%SZ')
                note = n.note
                if note == "Please refer to the note detail":
                    note = n.note_detail
                message = "The last action plan on SR {}, updated {} is: <br>{}".format(case_number, created, note)
            else:
                message = "No action plan found for SR {}".format(case_number)
        else:
            message = "No case data found matching {}".format(case_number)
    else:
        message = "Invalid case number"

    return message


# Sample command function that just echos back the sent message
def send_echo(incoming):
    # Get sent message
    message = extract_message("/echo", incoming.text)
    return message


# Construct a help message for users.
def send_help(post_data):
    message = "Hello!  "
    message = message + "I understand the following commands.  \n"
    message = message + "If case number is provided with the command, I will use that case number. \
                        If none is provided, I will look in the Spark room name for a case number to use. \n"
    for c in commands.items():
        message = message + "* **%s**: %s \n" % (c[0], c[1])
    return message


# Test command function that prints a test string
def send_test():
    message = "This is a test message."
    return message


#
# Bot functions
#

# Setup the Spark connection and WebHook
def spark_setup(email, token):
    # Update the global variables for config details
    globals()["spark_token"] = token
    globals()["bot_email"] = email

    sys.stderr.write("Spark Bot Email: " + bot_email + "\n")
    sys.stderr.write("Spark Token: REDACTED\n")

    # Setup the Spark Connection
    globals()["spark"] = CiscoSparkAPI(access_token=globals()["spark_token"])
    globals()["webhook"] = setup_webhook(globals()["bot_app_name"], globals()["bot_url"])
    sys.stderr.write("Configuring Webhook. \n")
    sys.stderr.write("Webhook ID: " + globals()["webhook"].id + "\n")


if __name__ == '__main__':
    # Entry point for bot
    # Retrieve needed details from environment for the bot
    bot_email = os.getenv("SPARK_BOT_EMAIL")
    spark_token = os.getenv("SPARK_BOT_TOKEN")
    bot_url = os.getenv("SPARK_BOT_URL")
    bot_app_name = os.getenv("SPARK_BOT_APP_NAME")

    # bot_url and bot_app_name must come in from Environment Variables
    if bot_url is None or bot_app_name is None:
            sys.exit("Missing required argument.  Must set 'SPARK_BOT_URL' and 'SPARK_BOT_APP_NAME' in ENV.")

    # Write the details out to the console
    sys.stderr.write("Spark Bot URL (for webhook): " + bot_url + "\n")
    sys.stderr.write("Spark Bot App Name: " + bot_app_name + "\n")

    # Placeholder variables for spark connection objects
    spark = None
    webhook = None

    # Check if the token and email were set in ENV
    if spark_token is None or bot_email is None:
        sys.stderr.write("Spark Config is missing, please provide via API.  Bot not ready.\n")
    else:
        spark_setup(bot_email, spark_token)
        spark = CiscoSparkAPI(access_token=spark_token)

    app.run(debug=True, host='0.0.0.0', port=int("5001"))
