from fit_tool.definition_message import DefinitionMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.profile_type import WorkoutStepDuration


def test_data_message_conversions():
    dm1 = WorkoutStepMessage()
    dm1.workout_step_name = "test"
    assert "test" == dm1.workout_step_name

    bytes1 = dm1.to_bytes()

    definition_message = DefinitionMessage.from_data_message(dm1)
    dm2 = WorkoutStepMessage(definition_message=definition_message)
    dm2.read_from_bytes(bytes1)
    bytes2 = dm2.to_bytes()

    assert "test" == dm2.workout_step_name

    assert bytes2 == bytes1


def test_to_row():
    dm1 = WorkoutStepMessage()
    dm1.workout_step_name = "test"
    dm1.duration_type = WorkoutStepDuration.DISTANCE

    row = dm1.to_row()
    print(row)
