"""Workout FILE_TYPE rules."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from fit_tool.data_message import DataMessage
from fit_tool.profile.profile_type import MesgNum, WorkoutStepDuration
from fit_tool.validation.file_types.common import require_fields_findings
from fit_tool.validation.report import ConformanceLevel, add_error

_REQUIRED_FILE_ID_FIELDS = ('type', 'manufacturer', 'product', 'serial_number', 'time_created')

_REQUIRED_FIELDS = {
    MesgNum.WORKOUT.value: ('num_valid_steps',),
    MesgNum.WORKOUT_STEP.value: (
        'message_index',
        'duration_type',
        'target_type',
    ),
}


def _workout_step_duration_value(duration_type: Any) -> int | None:
    """Normalize WorkoutStepDuration enum or raw int to its integer value."""
    if duration_type is None:
        return None
    if isinstance(duration_type, WorkoutStepDuration):
        return int(duration_type.value)
    try:
        return int(duration_type)
    except (TypeError, ValueError):
        return None


def _is_repeat_workout_step_duration(duration_type: Any) -> bool:
    """True for REPEAT_UNTIL_* meta-steps (not counted in ``num_valid_steps``)."""
    value = _workout_step_duration_value(duration_type)
    if value is None:
        return False
    return value >= int(WorkoutStepDuration.REPEAT_UNTIL_STEPS_CMPLT.value)


def collect_workout_file_findings(
        data_messages: Sequence[DataMessage],
        findings: list,
        data_message_indices: Mapping[int, int],
        message_counts: Counter,
) -> None:
    """Required fields for Workout FILE_TYPE (Garmin file-type + SDK samples).

    ``num_valid_steps`` is required on the workout message and is cross-checked
    against the count of non-repeat ``workout_step`` messages (repeat meta-steps
    are excluded). ``workout_session`` is optional (multi-sport only).

    Value-based ``duration_type`` values (everything except ``OPEN``) require a
    present ``duration_value`` / subfield payload.
    """
    require_fields_findings(
        findings,
        data_messages[0],
        _REQUIRED_FILE_ID_FIELDS,
        data_message_indices.get(0),
    )
    workout_count = message_counts[MesgNum.WORKOUT.value]
    if workout_count != 1:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            f'A workout FIT file requires exactly one workout message; found {workout_count}.',
        )
    if message_counts[MesgNum.WORKOUT_STEP.value] < 1:
        add_error(
            findings,
            ConformanceLevel.FILE_TYPE,
            'A workout FIT file requires at least one workout_step message.',
        )

    valid_step_count = 0
    for message_pos, message in enumerate(data_messages):
        field_names = _REQUIRED_FIELDS.get(message.global_id)
        if field_names is not None:
            require_fields_findings(
                findings,
                message,
                field_names,
                data_message_indices.get(message_pos),
            )

        if message.global_id != MesgNum.WORKOUT_STEP.value:
            continue

        record_index = data_message_indices.get(message_pos)
        duration_type = getattr(message, 'duration_type', None)
        duration_value = _workout_step_duration_value(duration_type)

        if not _is_repeat_workout_step_duration(duration_type):
            valid_step_count += 1

        # OPEN may omit duration_value; all other declared types need a value.
        if (
            duration_value is not None
            and duration_value != int(WorkoutStepDuration.OPEN.value)
        ):
            duration_payload = getattr(message, 'duration_value', None)
            if duration_payload is None:
                # Subfield getters (duration_time, etc.) may still surface a value.
                duration_payload = getattr(message, 'duration_time', None)
            if duration_payload is None:
                add_error(
                    findings,
                    ConformanceLevel.FILE_TYPE,
                    (
                        f'{message.name} duration_type requires duration_value '
                        f'(or a duration_* subfield); duration_type={duration_type!r}.'
                    ),
                    record_index,
                )

    for message_pos, message in enumerate(data_messages):
        if message.global_id != MesgNum.WORKOUT.value:
            continue
        declared = getattr(message, 'num_valid_steps', None)
        if declared is None:
            continue
        try:
            declared_int = int(declared)
        except (TypeError, ValueError):
            continue
        if declared_int != valid_step_count:
            add_error(
                findings,
                ConformanceLevel.FILE_TYPE,
                (
                    f'workout.num_valid_steps is {declared_int} but found '
                    f'{valid_step_count} non-repeat workout_step message(s) '
                    f'(repeat meta-steps excluded).'
                ),
                data_message_indices.get(message_pos),
            )
