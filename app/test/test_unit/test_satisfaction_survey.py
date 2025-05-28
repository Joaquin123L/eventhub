from django.test import TestCase
from app.views import parse_survey_data

class ParseSurveyDataTest(TestCase):
    def setUp(self):
        self.valid_post = {
            'satisfaction_level': '5',
            'ease_of_search': '4',
            'payment_experience': '3',
            'received_ticket': 'on',
            'would_recommend': '2',
            'additional_comments': '   Muy bien   '
        }
        self.missing_field_post = {
            'satisfaction_level': '3',
            'payment_experience': '2',
            'would_recommend': '1'
        }
        self.non_numeric_post = {
            'satisfaction_level': 'no-num',
            'ease_of_search': '4',
            'payment_experience': '3',
            'received_ticket': 'on',
            'would_recommend': '5',
        }

    def test_parse_valid_data_successfully(self):
        result = parse_survey_data(self.valid_post)
        self.assertEqual(result['satisfaction_level'], 5)
        self.assertEqual(result['ease_of_search'], 4)
        self.assertEqual(result['payment_experience'], 3)
        self.assertTrue(result['received_ticket'])
        self.assertEqual(result['would_recommend'], 2)
        self.assertEqual(result['additional_comments'], 'Muy bien')

    def test_parse_checkbox_absent_is_false(self):
        post = {
            'satisfaction_level': '1',
            'ease_of_search': '1',
            'payment_experience': '1',
            # 'received_ticket' ausente
            'would_recommend': '1',
            'additional_comments': ''
        }
        result = parse_survey_data(post)
        self.assertFalse(result['received_ticket'])
        self.assertEqual(result['additional_comments'], '')

    def test_missing_field_raises_value_error(self):
        self.assertRaises(
            ValueError,
            parse_survey_data,
            self.missing_field_post
        )

    def test_non_numeric_value_raises_value_error(self):
        self.assertRaises(
            ValueError,
            parse_survey_data,
            self.non_numeric_post
        )

