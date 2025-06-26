from fit_tool.definition_message import DefinitionMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.record import Record, RecordHeader


def test_normal_record_header():
    """Test packing and unpacking of normal record header."""
    expected_rh = RecordHeader(is_definition=True, local_id=RecordHeader.MAX_NORMAL_LOCAL_ID)

    bytes1 = expected_rh.to_bytes()

    rh = RecordHeader.from_bytes(bytes1)
    bytes2 = rh.to_bytes()

    assert bytes2 == bytes1
    assert rh == expected_rh


def test_compressed_timestamp_record_header():
    """Test packing and unpacking of a compressed timestamp header."""
    expected_rh = RecordHeader(is_time_compressed=True, local_id=3, time_offset_seconds=10)

    bytes1 = expected_rh.to_bytes()

    rh = RecordHeader.from_bytes(bytes1)
    bytes2 = rh.to_bytes()

    assert bytes2 == bytes1


def test_record_pack_unpack():
    """Test packing and unpacking of a record"""
    local_id = 15
    dm1 = WorkoutStepMessage(local_id=local_id)
    dm1.workout_step_name = "test"

    record1 = Record.from_message(dm1)

    bytes1 = record1.to_bytes()

    definition_message = DefinitionMessage.from_data_message(dm1)
    record2 = Record.from_bytes(definition_messages={local_id: definition_message}, bytes_buffer=bytes1)
    bytes2 = record2.to_bytes()

    assert bytes2 == bytes1


def test_record_to_row():
    """Test record to_row"""
    local_id = 15
    dm1 = WorkoutStepMessage(local_id=local_id)
    dm1.workout_step_name = "test"

    record1 = Record.from_message(dm1)

    print(record1.to_row())
