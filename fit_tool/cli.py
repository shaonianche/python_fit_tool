"""
Command line interface for fit_tool.

Copyright (c) 2017 Stages Cycling. All rights reserved.
"""
import argparse
import logging
import os

from fit_tool.fit_file import FitFile
from fit_tool.utils.logging import logger


SUPPORTED_FORMATS = {"csv", "fit"}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Tool for managing FIT files."
    )
    parser.add_argument(
        'fitfile',
        metavar='FILE',
        help='FIT file to process'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='specify verbose output'
    )
    parser.add_argument("-o", "--output", help="Output filename.")
    parser.add_argument("-l", "--log", help="Log filename.")
    parser.add_argument(
        "-t", "--type",
        choices=sorted(SUPPORTED_FORMATS),
        help="Output format type. Options: csv, fit."
    )

    return parser.parse_args()


def resolve_format_type(args) -> str:
    if args.type:
        return args.type.lower()

    if args.output:
        _, out_ext = os.path.splitext(os.path.basename(args.output))
        inferred_type = out_ext.lstrip('.').lower()
        if inferred_type:
            if inferred_type not in SUPPORTED_FORMATS:
                raise ValueError(f'Unsupported output format "{inferred_type}". Supported formats: csv, fit.')
            return inferred_type

    return 'csv'


def main():
    """Main entry point."""
    args = parse_args()

    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s %(message)s")

    if args.log:
        handler = logging.FileHandler(args.log)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if args.verbose:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    logger.info(f'Loading fit file {args.fitfile}...')

    fit_file = FitFile.from_file(args.fitfile)

    format_type = resolve_format_type(args)

    basename_noext, _ = os.path.splitext(os.path.basename(args.fitfile))
    output_filename = args.output or f'{basename_noext}.{format_type}'

    logger.info(f'Exporting fit file to {output_filename} as format {format_type}...')

    if format_type == 'csv':
        fit_file.to_csv(output_filename)
    elif format_type == 'fit':
        fit_file.to_file(output_filename)


if __name__ == "__main__":
    main()
