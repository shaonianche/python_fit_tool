"""
Command line interface for fit_tool.

Copyright (c) 2017 Stages Cycling. All rights reserved.
"""
import argparse
import logging
import os

from fit_tool.fit_file import FitFile
from fit_tool.utils.logging import logger


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
        help="Output format type. Options: csv, fit."
    )

    return parser.parse_args()


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

    if args.type:
        format_type = args.type
    elif args.output:
        _, out_ext = os.path.splitext(os.path.basename(args.output))
        format_type = out_ext.lstrip('.')
    else:
        format_type = 'csv'

    basename_noext, _ = os.path.splitext(os.path.basename(args.fitfile))
    output_filename = args.output or f'{basename_noext}.{format_type}'

    logger.info(f'Exporting fit file to {output_filename} as format {format_type}...')

    if format_type == 'csv':
        fit_file.to_csv(output_filename)
    elif format_type == 'fit':
        fit_file.to_file(output_filename)


if __name__ == "__main__":
    main()
