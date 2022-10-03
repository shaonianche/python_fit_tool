import datetime
import unittest

from fit_tool.base_type import BaseType
from fit_tool.developer_field import DeveloperField
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.developer_data_id_message import DeveloperDataIdMessage
from fit_tool.profile.messages.field_description_message import FieldDescriptionMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.profile_type import FileType, Manufacturer


class TestWriteActivityFile(unittest.TestCase):

    def setUp(self):
        super().setUp()

    def shortDescription(self):
        return None

    def test_write_activity_with_developer_data_fields(self):
        """Test encoding an activity with developer data fields.
        """
        # Set auto_define to true, so that the builder creates the required Definition Messages for us.
        builder = FitFileBuilder(auto_define=True, min_string_size=50)

        message = FileIdMessage()
        message.type = FileType.ACTIVITY
        message.manufacturer = Manufacturer.DEVELOPMENT.value
        message.product = 1231
        message.time_created = round(datetime.datetime.now().timestamp() * 1000)
        message.serial_number = 0x12345678
        builder.add(message)

        developer_data_index = 0
        message = DeveloperDataIdMessage()
        message.application_id = b'123456'
        message.developer_data_index = developer_data_index
        builder.add(message)

        # Define the developer field
        doughnuts_earned_field_name = 'doughnuts_earned'
        doughnuts_earned_field_units = 'doughnuts'
        message = FieldDescriptionMessage()
        message.developer_data_index = developer_data_index
        message.field_definition_number = 0
        message.fit_base_type_id = BaseType.SINT8
        message.field_name = doughnuts_earned_field_name
        message.units = doughnuts_earned_field_units
        builder.add(message)

        # Add a record message with an addition doughnuts earned developer field
        dev_field = DeveloperField(developer_data_index=developer_data_index, field_id=0, size=1)
        dev_field.set_value(0, 5)

        message = RecordMessage(developer_fields=[dev_field])
        message.distance = 0
        message.power = 100
        builder.add(message)

        # Finally build the FIT file object and write it to a file
        fit_file = builder.build()

        out_path = '../tests/out/activity_with_developer_data.fit'

        fit_file.to_file(out_path)
        csv_path = '../tests/out/activity_with_developer_data.csv'
        fit_file.to_csv(csv_path)

        # read back the file
        with open(out_path, 'rb') as file_object:
            bytes_buffer = file_object.read()
            fit_file = FitFile.from_bytes(bytes_buffer)
            for row in fit_file.to_rows():
                print(row)
            for record in fit_file.records:
                message = record.message
                if isinstance(message, RecordMessage):
                    self.assertEqual(message.developer_fields[0].name, doughnuts_earned_field_name)
                    self.assertEqual(message.developer_fields[0].get_value(0), 5)
                    self.assertEqual(message.developer_fields[0].units, doughnuts_earned_field_units)

