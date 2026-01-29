
import unittest
from fit_tool.data_message import DataMessage
from fit_tool.developer_field import DeveloperField

class TestDeveloperFields(unittest.TestCase):

    def setUp(self):
        self.message = DataMessage()
        self.message.developer_fields = [
            DeveloperField(field_id=1, developer_data_index=0, name='dev_field_1'),
            DeveloperField(field_id=2, developer_data_index=0, name='dev_field_2'),
            DeveloperField(field_id=1, developer_data_index=1, name='dev_field_3'),
        ]

    def test_get_developer_field_found(self):
        # Test finding first element
        field = self.message.get_developer_field(developer_data_index=0, field_id=1)
        self.assertIsNotNone(field)
        self.assertEqual(field.name, 'dev_field_1')

        # Test finding middle element
        field = self.message.get_developer_field(developer_data_index=0, field_id=2)
        self.assertIsNotNone(field)
        self.assertEqual(field.name, 'dev_field_2')

        # Test finding last element
        field = self.message.get_developer_field(developer_data_index=1, field_id=1)
        self.assertIsNotNone(field)
        self.assertEqual(field.name, 'dev_field_3')

    def test_get_developer_field_not_found(self):
        # Test non-existent field id
        field = self.message.get_developer_field(developer_data_index=0, field_id=999)
        self.assertIsNone(field)

        # Test non-existent developer data index
        field = self.message.get_developer_field(developer_data_index=99, field_id=1)
        self.assertIsNone(field)

    def test_get_developer_field_by_name_found(self):
        field = self.message.get_developer_field_by_name('dev_field_1')
        self.assertIsNotNone(field)
        self.assertEqual(field.developer_data_index, 0)
        self.assertEqual(field.field_id, 1)

    def test_get_developer_field_by_name_not_found(self):
        field = self.message.get_developer_field_by_name('non_existent_field')
        self.assertIsNone(field)
