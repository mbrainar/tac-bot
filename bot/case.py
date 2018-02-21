import re

# Case API wrapper class
class CaseDetail(object):
    def __init__(self, json):
        self._json = json
        super(CaseDetail, self).__init__()

    @property
    def count(self):
        return self._json['RESPONSE']['COUNT']

    @property
    def error(self):
        try:
            return self._json['caseDetail']['ErrorResponse']['APIError']['ErrorDescription']
        except:
            return None

    @property
    def title(self):
        return self._json['caseDetail']['title']

    # TODO find equivalent to problem description
    @property
    def description(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['PROBLEM_DESC']

    @property
    def serial(self):
        return self._json['caseDetail']['serial_number']

    '''
    # hostname doesn't exist in case api v3
    @property
    def hostname(self):
        try:
            return self._json['RESPONSE']['CASES']['CASE_DETAIL']['DEVICE_NAME']
        except:
            return None
    '''

    @property
    def contract(self):
        return self._json['caseDetail']['contract_id']

    @property
    def updated(self):
        return self._json['caseDetail']['updated_date']

    @property
    def created(self):
        return self._json['caseDetail']['creation_date']

    @property
    def status(self):
        return self._json['caseDetail']['status']

    @property
    def severity(self):
        return self._json['caseDetail']['severity']

    @property
    def rmas(self):
        try:
            return self._json['RESPONSE']['CASES']['CASE_DETAIL']['RMAS']['ID']
        except:
            return None

    @property
    def bugs(self):
        try:
            return self._json['RESPONSE']['CASES']['CASE_DETAIL']['BUGS']['ID']
        except:
            return None

    @property
    def owner_first(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['OWNER_FIRST_NAME']

    @property
    def owner_last(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['OWNER_LAST_NAME']

    @property
    def owner_id(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['OWNER_USER_ID']

    @property
    def owner_email(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['OWNER_EMAIL_ADDRESS']

    @property
    def customer_first(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['CONTACT_USER_FIRST_NAME']

    @property
    def customer_last(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['CONTACT_USER_LAST_NAME']

    @property
    def customer_first(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['CONTACT_USER_FIRST_NAME']

    @property
    def customer_id(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['CONTACT_USER_ID']

    @property
    def customer_email(self):
        try:
            return self._json['RESPONSE']['CASES']['CASE_DETAIL']['CONTACT_EMAIL_IDS']['ID']
        except:
            return None

    @property
    def customer_business(self):
        try:
            return self._json['RESPONSE']['CASES']['CASE_DETAIL']['CONTACT_BUSINESS_PHONE_NUMBERS']['ID']
        except:
            return None

    @property
    def customer_mobile(self):
        try:
            return self._json['RESPONSE']['CASES']['CASE_DETAIL']['CONTACT_MOBILE_PHONE_NUMBERS']['ID']
        except:
            return None

    @property
    def last_note(self):
        old_list = self._json['RESPONSE']['CASES']['CASE_DETAIL']['NOTES']['XXCTS_SCM_APIX_NOTE']
        new_list = sorted(old_list, key=lambda k: k['CREATION_DATE'])
        return Note(new_list[-1])

    @property
    def action_plan(self):
        _pattern = re.compile("action\ +plan", flags=re.IGNORECASE)
        old_list = self._json['RESPONSE']['CASES']['CASE_DETAIL']['NOTES']['XXCTS_SCM_APIX_NOTE']
        try:
            new_list = [n for n in old_list if _pattern.search(n['NOTE']) or _pattern.search(n['NOTE_DETAIL'])]
            sorted_list = sorted(new_list, key=lambda k: k['CREATION_DATE'])
            return Note(sorted_list[-1])
        except:
            return None

    # get last note
    # get note by date
    # get note by user

class Note(object):
    def __init__(self, json):
        self._json = json

    @property
    def creator(self):
        return self._json['CREATED_BY']

    @property
    def note(self):
        return self._json['NOTE']

    @property
    def note_detail(self):
        return self._json['NOTE_DETAIL']

    @property
    def creation_date(self):
        return self._json['CREATION_DATE']

    @property
    def updated_date(self):
        return self._json['UPDATED_DATE']
