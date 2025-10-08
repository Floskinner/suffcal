import argparse
from pathlib import Path
from suffcal.handler import init_media_handler, get_media_handler
from suffcal.extractor import Extractor


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
        default=120,
        help="Interval in minutes to check for new posts (default: 120)",
    )
    parsed_args = args.parse_args()

    init_media_handler(
        parsed_args.download_path,
        parsed_args.target_user,
        parsed_args.user,
        parsed_args.password,
        update_interval=parsed_args.update_interval,
        no_auto_update=True,
    )

    processedPhotos = get_media_handler()._get_processed_photos()
    extractor = Extractor()
    for photo in processedPhotos:
        event = extractor.extract(photo.path)
        print(event)


if __name__ == "__main__":
    main()
