from pathlib import Path

from fit_tool.fit_file import FitFile


def main():
    """ The following code reads all the bytes from a FIT formatted file and then decodes these bytes to
        create a FIT file object. We then convert the FIT data to a human-readable CSV file.
    """
    root = Path(__file__).resolve().parents[2]
    path = root / 'fit_tool' / 'tests' / 'data' / 'sdk' / 'Activity.fit'
    fit_file = FitFile.from_file(str(path))

    out_path = root / 'fit_tool' / 'tests' / 'out' / 'Activity.csv'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fit_file.to_csv(str(out_path))


if __name__ == "__main__":
    main()
