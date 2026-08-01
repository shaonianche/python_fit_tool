from __future__ import annotations

from fit_tool.data_message import DataMessage
from fit_tool.definition_message import DefinitionMessage
from fit_tool.developer_field import DeveloperField
from fit_tool.field import Field


class GenericMessage(DataMessage):
    """Fallback message for unknown global IDs (always definition-projected).

    Generic messages have no blank authoring constructor: they only exist as a
    projection of a local definition from the wire. Prefer
    :meth:`from_definition` for new code; ``__init__(definition_message, ...)``
    remains supported as an alias.
    """

    NAME = 'generic'

    def __init__(self, definition_message: DefinitionMessage, developer_fields: list[DeveloperField] = None):
        fields = [Field.from_field_definition(definition) for definition in definition_message.field_definitions]
        super().__init__(global_id=definition_message.global_id, local_id=definition_message.local_id,
                         endian=definition_message.endian, name=GenericMessage.NAME,
                         definition_message=definition_message, fields=fields, developer_fields=developer_fields)

    @classmethod
    def from_definition(
            cls,
            definition_message: DefinitionMessage,
            developer_fields: list[DeveloperField] = None,
    ) -> GenericMessage:
        """Project a wire definition onto a generic (unknown-profile) message."""
        return cls(definition_message, developer_fields=developer_fields)

    @classmethod
    def from_bytes(cls, definition_message: DefinitionMessage, developer_fields: list[DeveloperField],
                   bytes_buffer: bytes, offset: int = 0):
        message = cls.from_definition(definition_message, developer_fields=developer_fields)
        message.read_from_bytes(bytes_buffer, offset)
        return message
