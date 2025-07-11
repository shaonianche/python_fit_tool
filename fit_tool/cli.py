"""
Copyright (c) 2017 Stages Cycling. All rights reserved.

"""

import argparse
import logging
import logging.config
import os

from .fit_file import FitFile

# from pythonjsonlogger import jsonlogger


def parse_args():
    """
    Parse command line arguments.
    """

    parser = argparse.ArgumentParser(
        description="""
Tool for managing FIT files.

"""
    )
    parser.add_argument(
        "fitfile",
        metavar="FILE",
        type=argparse.FileType("r"),
        help="FIT file to process",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="specify verbose output")
    parser.add_argument("-o", "--output", help="Output filename.")
    parser.add_argument("-l", "--log", help="Log filename.")
    parser.add_argument("-t", "--type", help="Output format type. Options: csv, fit.")

    # parser.add_argument("--validate", action='store_true',
    #                     help="Validate file by reading and writing simultaneously.")

    # parser.add_argument('--include', nargs="+", type=int,
    #                     help="Records to include in output file.")
    # parser.add_argument('--exclude', nargs="+", type=int,
    #                     help="Records to exclude in output file.")

    return parser.parse_args()


def main():
    """
    Main
    """
    args = parse_args()

    logger = logging.getLogger("fit_tool")
    logger.handlers = []
    logger.addHandler(logging.NullHandler())
    logger.propagate = False

    # logging filename
    if args.log:
        handler = logging.FileHandler(args.log)
        formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # log to screen
    if args.verbose:
        handler = logging.StreamHandler()
        logger.addHandler(handler)

    logger.setLevel(logging.DEBUG)
    logger.info(f"Loading fit file {args.fitfile.name}...")
    fit_filename = args.fitfile.name

    # if args.validate:
    #     basename_noext, out_ext = os.path.splitext(
    #         os.path.basename(fit_filename))
    #     output_filename = args.output if args.output else basename_noext + '-out.fit'
    #     print('Read/Write fit file to {} as format..'.format(output_filename),
    #           file=print_file)
    #     FitFile.fromto_file(fit_filename, output_filename)
    #     return

    # Load the fit file
    fit_file = FitFile.from_file(fit_filename)

    if args.type:
        format_type = args.type
    elif args.output:
        basename_noext, out_ext = os.path.splitext(os.path.basename(args.output))
        format_type = out_ext
    else:
        format_type = "csv"

    basename_noext, out_ext = os.path.splitext(os.path.basename(fit_filename))
    output_filename = args.output if args.output else basename_noext + "." + format_type

    logger.info(f"Exporting fit file to {output_filename} as format {format_type}...")

    if format_type == "csv":
        # fit_file.to_csv(output_filename, include=args.include,
        #                exclude=args.exclude)
        fit_file.to_csv(output_filename)

    elif format_type == "fit":
        fit_file.to_file(output_filename)
        # fit_file.to_file(output_filename, include=args.include,
        #                 exclude=args.exclude)


if __name__ == "__main__":
    main()
