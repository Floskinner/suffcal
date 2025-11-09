import argparse
import os
from suffcal.handler import init_media_handler, get_media_handler
from suffcal.extractor import Extractor
from suffcal.remote_cal import RemoteCal
from suffcal.handler import DownloadedPhoto


def main():
    parser = argparse.ArgumentParser(
        description="Update your calender by posted instagram events"
    )

    # create a mutually exclusive group for flags (keep --init here)
    parser.add_argument(
        "--init",
        action="store_true",
        help="Only download all needed files to execute the app. Probably only needed for docker preperation. Exit after init",
    )

    insta_group = parser.add_argument_group(
        "Instagram Settings", "All needed settings for instagramm"
    )
    calendar_group = parser.add_argument_group("Calendar Settings")

    # Add Instagram related arguments to insta_group
    insta_group.add_argument(
        "--insta-download-path", help="Path where instagram images will be downloaded"
    )
    insta_group.add_argument(
        "--insta-target-user", help="Target instagram user to scan posts from"
    )
    insta_group.add_argument("--insta-user", help="Instagram login user")
    insta_group.add_argument("--insta-password", help="Instagram login password")
    insta_group.add_argument(
        "--update-interval", type=int, help="Interval in seconds between updates"
    )

    # Add Calendar related arguments to calendar_group
    calendar_group.add_argument("--calendar-user", help="Calendar username")
    calendar_group.add_argument("--calendar-password", help="Calendar password")
    calendar_group.add_argument("--calendar-url", help="Calendar URL")
    calendar_group.add_argument("--calendar-name", help="Calendar name to update")

    parsed_args = parser.parse_args()

    extractor = Extractor()

    if parsed_args.init:
        print("Exit after init the AI Extractor class")
        return 0

    # prefer explicit args; fall back to environment variables
    insta_user = parsed_args.insta_user or os.environ.get("INSTA_USER")
    insta_password = parsed_args.insta_password or os.environ.get("INSTA_PASSWORD")
    calendar_user = parsed_args.calendar_user or os.environ.get("CALENDAR_USER")
    calendar_password = parsed_args.calendar_password or os.environ.get(
        "CALENDAR_PASSWORD"
    )

    init_media_handler(
        parsed_args.insta_download_path,
        parsed_args.insta_target_user,
        insta_user,
        insta_password,
        update_interval=parsed_args.update_interval,
        no_auto_update=True,
    )
    calendar = RemoteCal(
        user=calendar_user,
        password=calendar_password,
        url=parsed_args.calendar_url,
        calendar_name=parsed_args.calendar_name,
    )

    def on_new_photo(photo: DownloadedPhoto):
        try:
            events = extractor.extract(photo.path)
            get_media_handler().mark_photo_as_processed(photo)
        except Exception as error:
            print(f"Unable do proccess {photo.path}: {error}")

        for event in events:
            if not event.date:
                print(f"Event got no date - skipping {event.title}")
                continue
            print(event)
            calendar.addEvent(event)

    get_media_handler().add_on_new_photo_callback(on_new_photo)


if __name__ == "__main__":
    main()
