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
        return self._json['caseDetail']['rmas']

    @property
    def bugs(self):
        return self._json['caseDetail']['bugs']

    @property
    def owner_name(self):
        return self._json['caseDetail']['owner_name']

    @property
    def owner_email(self):
        return self._json['caseDetail']['owner_email']

    @property
    def customer_name(self):
        return self._json['caseDetail']['contact_name']

    @property
    def customer_id(self):
        return self._json['caseDetail']['contact_user_id']

    @property
    def customer_email(self):
        # Returns LIST of emails
        return self._json['caseDetail']['contact_email_ids']

    @property
    def customer_business(self):
        return self._json['caseDetail']['contact_business_phone_numbers']

    @property
    def customer_mobile(self):
        return self._json['caseDetail']['contact_mobile_phone_numbers']

    '''
    # last-note in caseAPIv3 returns entire email threads and is too long for Spark
    # removing from new version
    @property
    def last_note(self):
        old_list = self._json['caseDetail']['notes']
        new_list = sorted(old_list, key=lambda k: k['creation_date'])
        return Note(new_list[-1])
    '''

    '''
    # action plan never really worked properly :-( 
    # Case api v3 doesn't provide enough data types to capture action plan
    # removing from new version
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
    '''

    # get last note
    # get note by date
    # get note by user
'''
# last-note in caseAPIv3 returns entire email threads and is too long for Spark
# removing from new version
class Note(object):
    def __init__(self, json):
        self._json = json

    @property
    def creator(self):
        return self._json['created_by']

    @property
    def note_detail(self):
        return self._json['note_detail']

    @property
    def creation_date(self):
        return self._json['creation_date']
'''