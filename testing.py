import unittest
import bot.bot
import bot.utilities

class testcases(unittest.TestCase):
    def setUp(self):
        self.app = bot.bot.app.test_client()

    def test_002_get_access_token_is_unicode(self):
        test = bot.bot.get_access_token()
        self.assertIsInstance(test, unicode)

    def test_001_get(self):
        response = self.app.get("/")
        self.assertEqual(response.status_code, 405)

    def test_003_is_email(self):
        test = bot.utilities.check_email_syntax("notanemail")
        self.assertFalse(test)

    def test_004_is_email(self):
        test = bot.utilities.check_email_syntax("somename@cisco.com")
        self.assertTrue(test)

    def test_005_is_cisco_email(self):
        test = bot.utilities.check_cisco_user("somename@cisco.com")
        self.assertTrue(test)

    def test_006_is_cisco_email(self):
        test = bot.utilities.check_cisco_user("somename@yahoo.com")
        self.assertFalse(test)

unittest.main()