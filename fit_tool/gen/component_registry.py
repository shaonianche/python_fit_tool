"""Extract main-field component definitions from Profile.xlsx for code generation.

Subfield-gated components (empty Field Def # with Ref Field Name) are intentionally
omitted — those ship with subfield resolution (Multica D / Stage 2).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ComponentSpec:
    """One component destination extracted from a Profile source field."""

    field_id: int
    accumulate: bool
    bits: int
    scale: float
    offset: float
    dest_name: str


@dataclass(frozen=True)
class SourceFieldComponents:
    """Components declared on a main (non-subfield) Profile field."""

    message_name: str
    message_number: int
    source_field_id: int
    source_field_name: str
    components: tuple[ComponentSpec, ...]


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == '')


def _split_csv(value: Any) -> list[str]:
    if _is_blank(value):
        return []
    if isinstance(value, (int, float)):
        return [str(value)]
    return [part.strip() for part in str(value).split(',') if part.strip() != '']


def _parse_float(value: str | None, default: float) -> float:
    if value is None or value == '':
        return default
    return float(value)


def _parse_int(value: str | None, default: int = 0) -> int:
    if value is None or value == '':
        return default
    return int(float(value))


def _parse_bool_flag(value: str | None) -> bool:
    if value is None or value == '':
        return False
    try:
        return int(float(value)) != 0
    except ValueError:
        return str(value).strip().lower() in {'1', 'true', 'yes'}


def load_main_field_components(xlsx_path: str | Path) -> list[SourceFieldComponents]:
    """Load main-field component tables from a Garmin Profile spreadsheet."""
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ImportError(
            "Reading Garmin Profile spreadsheets requires the optional gen dependencies. "
            "Install with: pip install 'fit-tool[gen]'  or  uv sync --extra gen --group dev"
        ) from exc

    wb = load_workbook(filename=str(xlsx_path), read_only=True, data_only=True)

    mesg_num: dict[str, int] = {}
    current_type: str | None = None
    for index, row in enumerate(wb['Types'].rows):
        if index == 0:
            continue
        type_name = row[0].value
        if type_name:
            current_type = type_name
        if current_type != 'mesg_num':
            continue
        value_name = row[2].value
        if not value_name:
            continue
        raw_value = row[3].value
        if isinstance(raw_value, str):
            raw_value = int(raw_value, 0)
        mesg_num[str(value_name)] = int(raw_value)

    # First pass: field name → id per message (main fields only).
    fields_by_name: dict[tuple[str, str], int] = {}
    current_message: str | None = None
    for index, row in enumerate(wb['Messages'].rows):
        if index == 0:
            continue
        message_name = row[0].value
        if message_name:
            current_message = str(message_name)
            continue
        if current_message is None:
            continue
        field_id = row[1].value
        field_name = row[2].value
        if _is_blank(field_id) or _is_blank(field_name):
            continue
        fields_by_name[(current_message, str(field_name))] = int(field_id)

    results: list[SourceFieldComponents] = []
    current_message = None
    for index, row in enumerate(wb['Messages'].rows):
        if index == 0:
            continue
        message_name = row[0].value
        if message_name:
            current_message = str(message_name)
            continue
        if current_message is None:
            continue

        field_id = row[1].value
        field_name = row[2].value
        components_cell = row[5].value
        if _is_blank(components_cell):
            continue
        # Subfield rows have no Field Def # — deferred to subfield resolution (D).
        if _is_blank(field_id) or _is_blank(field_name):
            continue

        dest_names = _split_csv(components_cell)
        if not dest_names:
            continue

        scales = _split_csv(row[6].value)
        offsets = _split_csv(row[7].value)
        bits_list = _split_csv(row[9].value)
        accumulate_list = _split_csv(row[10].value)

        components: list[ComponentSpec] = []
        for i, dest_name in enumerate(dest_names):
            dest_id = fields_by_name.get((current_message, dest_name))
            if dest_id is None:
                raise KeyError(
                    f'Component destination {dest_name!r} not found on message '
                    f'{current_message!r} (source field {field_name!r})'
                )
            scale = _parse_float(scales[i] if i < len(scales) else None, 1.0)
            offset = _parse_float(offsets[i] if i < len(offsets) else None, 0.0)
            bits = _parse_int(bits_list[i] if i < len(bits_list) else None, 0)
            accumulate = _parse_bool_flag(
                accumulate_list[i] if i < len(accumulate_list) else None
            )
            components.append(
                ComponentSpec(
                    field_id=dest_id,
                    accumulate=accumulate,
                    bits=bits,
                    scale=scale,
                    offset=offset,
                    dest_name=dest_name,
                )
            )

        message_number = mesg_num[current_message]
        results.append(
            SourceFieldComponents(
                message_name=current_message,
                message_number=message_number,
                source_field_id=int(field_id),
                source_field_name=str(field_name),
                components=tuple(components),
            )
        )

    results.sort(key=lambda item: (item.message_number, item.source_field_id))
    return results


def render_component_registry(
        sources: Sequence[SourceFieldComponents],
        *,
        sdk_version: str,
) -> str:
    """Render a Python module defining PROFILE_COMPONENTS from extracted specs."""
    lines: list[str] = [
        '# Autogenerated. Do not modify.',
        '#',
        f'# Profile: {sdk_version}',
        '# Main-field components only (subfield-gated components omitted — see Stage 2 D).',
        '"""Profile component registry for decode-time expansion.',
        '',
        'Generated from the bundled Garmin Profile spreadsheet by ``gen-profile``.',
        'Key: ``(global_message_number, source_field_id)`` → component tuple (LSB first).',
        '"""',
        '',
        'from __future__ import annotations',
        '',
        'from fit_tool.field_component import FieldComponent',
        '',
        '# Coverage: every main-field component source in Profile Messages sheet.',
        'PROFILE_COMPONENT_SOURCE_COUNT = ' + str(len(sources)),
        '',
        'PROFILE_COMPONENTS: dict[tuple[int, int], tuple[FieldComponent, ...]] = {',
    ]

    for source in sources:
        dest_names = ', '.join(c.dest_name for c in source.components)
        lines.append(
            f'    # {source.message_name}.{source.source_field_name} '
            f'(field {source.source_field_id}) → {dest_names}'
        )
        lines.append(
            f'    ({source.message_number}, {source.source_field_id}): ('
        )
        for component in source.components:
            lines.append(
                '        FieldComponent('
                f'field_id={component.field_id}, '
                f'accumulate={component.accumulate!r}, '
                f'bits={component.bits}, '
                f'scale={component.scale!r}, '
                f'offset={component.offset!r}'
                '),'
            )
        lines.append('    ),')

    lines.append('}')
    lines.append('')
    lines.append(
        'PROFILE_COMPONENT_KEYS: frozenset[tuple[int, int]] = frozenset(PROFILE_COMPONENTS)'
    )
    lines.append('')
    return '\n'.join(lines) + '\n'


def write_component_registry(
        output_path: str | Path,
        *,
        xlsx_path: str | Path,
        sdk_version: str,
) -> list[SourceFieldComponents]:
    """Extract components from *xlsx_path* and write *output_path*."""
    sources = load_main_field_components(xlsx_path)
    text = render_component_registry(sources, sdk_version=sdk_version)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return list(sources)


def coverage_summary(sources: Iterable[SourceFieldComponents]) -> dict[str, Any]:
    """Return high-level coverage stats for docs / tests."""
    sources = list(sources)
    messages = sorted({s.message_name for s in sources})
    accumulate_sources = sum(
        1 for s in sources if any(c.accumulate for c in s.components)
    )
    nested_edges = 0
    source_ids = {(s.message_name, s.source_field_id) for s in sources}
    for s in sources:
        for c in s.components:
            if (s.message_name, c.field_id) in source_ids:
                nested_edges += 1
    return {
        'main_field_sources': len(sources),
        'messages': messages,
        'message_count': len(messages),
        'sources_with_accumulate': accumulate_sources,
        'nested_edges': nested_edges,
    }
