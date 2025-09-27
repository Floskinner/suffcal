import argparse
from pathlib import Path
from suffcal.media.handler import init_handler
from suffcal.media.data_extractor import extract_latest_text


def main():
    args = argparse.ArgumentParser(
        description="Update your calender by posted instagram events"
    )
    args.add_argument(
        "download_path", type=Path, help="Path to store the download photos"
    )
    args.add_argument("target_user", type=str, help="Instagram user to track")
    args.add_argument("user", type=str, help="Instagram user to login")
    args.add_argument("password", type=str, help="Instagram password to login")

    args.add_argument(
        "--update-interval",
        type=int,
        default=60,
        help="Interval in minutes to check for new posts (default: 60)",
    )
    parsed_args = args.parse_args()

    init_handler(
        parsed_args.download_path,
        parsed_args.target_user,
        parsed_args.user,
        parsed_args.password,
    )

    for i, text in enumerate(extract_latest_text()):
        print("Extracted Text:", text)
        print("-" * 20)

        Path(f"{i}-out.txt").write_text(text)


if __name__ == "__main__":
    main()
