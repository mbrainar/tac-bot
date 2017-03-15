#! /usr/bin/python

"""
utilities.py file contains supporting functions for bot.py
"""

import re

# Check if user is cisco.com email address
def check_cisco_user(content):
    pattern = re.compile("^([a-zA-Z0-9_\-\.]+)@(cisco)\.(com)$")

    if pattern.match(content):
        return True
    else:
        return False


