# Case API wrapper class
class CaseDetail(object):
    def __init__(self, json):
        self._json = json
        super(CaseDetail, self).__init__()

    @property
    def count(self):
        return self._json['RESPONSE']['COUNT']

    @count.setter
    def count(self, count):
        if count == 0:
            raise CaseError("No case found")
        else:
            self._json['RESPONSE']['COUNT'] = count

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
        return self._json['RESPONSE']['CASES']['CASE_DETAIL']['RMAS']['ID']

    @rmas.setter
    def rmas(self, rmas):
        if self._json['RESPONSE']['CASES']['CASE_DETAIL']['RMAS']:
            return self._json['RESPONSE']['CASES']['CASE_DETAIL']['RMAS']['ID']
        else:
            return None

    def bugs(self):
        if self._json['RESPONSE']['CASES']['CASE_DETAIL']['BUGS']:
            return self._json['RESPONSE']['CASES']['CASE_DETAIL']['BUGS']['ID']
        else:
            return None

class Error(Exception):
    pass

class CaseError(Error):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)