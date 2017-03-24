# Case API wrapper class
class CaseDetail(object):
    def __init__(self, json):
        self._json = json
        super(CaseDetail, self).__init__()

    @property
    def count(self):
        return self._json['RESPONSE']['COUNT']

    @property
    def title(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['TITLE']

    @title.setter
    def title(self, title):
        if isinstance(title, str):
            self._json['RESPONSE']['CASES']['CASE_DETAIL']['TITLE'] = title
        else:
            raise TypeError("title must be of type str")

    @property
    def description(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['PROBLEM_DESC']

    @property
    def serial(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['SERIAL_NUMBER']

    @property
    def hostname(self):
        try:
            return self._json['RESPONSE']['CASES']['CASE_DETAIL']['DEVICE_NAME']
        except:
            return None

    @property
    def contract(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['CONTRACT_ID']

    @property
    def updated(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['UPDATED_DATE']

    @property
    def created(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['CREATION_DATE']

    @property
    def status(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['STATUS']

    @property
    def severity(self):
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['SEVERITY']

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