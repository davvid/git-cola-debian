# -*- encoding: utf-8 -*-
import unittest

import cola.app

class ColaApplicationTestCase(unittest.TestCase):
    """Test cases for the ColaApplication class"""

    def test_translates_noun(self):
        """Test that strings with @@noun are translated
        """
        app = cola.app.ColaApplication([], locale='ja_JP', gui=False)
        self.assertEqual(app.translate('??', 'Commit@@noun'), u'コミット')

    def test_translates_verb(self):
        """Test that strings with @@verb are translated
        """
        app = cola.app.ColaApplication([], locale='de_DE', gui=False)
        self.assertEqual(app.translate('??', 'Commit@@verb'), 'Eintragen')

    def test_translates_english_noun(self):
        """Test that English strings with @@noun are properly handled
        """
        app = cola.app.ColaApplication([], locale='en_US.UTF-8', gui=False)
        self.assertEqual(app.translate('??', 'Commit@@noun'), 'Commit')

    def test_translates_english_verb(self):
        """Test that English strings with @@verb are properly handled
        """
        app = cola.app.ColaApplication([], locale='en_US.UTF-8', gui=False)
        self.assertEqual(app.translate('??', 'Commit@@verb'), 'Commit')

    def test_translates_random_english(self):
        """Test that random English strings are passed through as-is
        """
        app = cola.app.ColaApplication([], locale='en_US.UTF-8', gui=False)
        self.assertEqual(app.translate('??', 'Random'), 'Random')


if __name__ == '__main__':
    unittest.main()
