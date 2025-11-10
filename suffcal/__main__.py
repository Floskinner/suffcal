import argparse
import os
import signal
from datetime import timedelta
from suffcal.handler import init_media_handler, get_media_handler
from suffcal.extractor import Extractor
from suffcal.remote_cal import RemoteCal
from suffcal.handler import DownloadedPhoto


def sigint_handler(signum, frame):
    print("SIGINT received, shutting down...")
    handler = get_media_handler()
    handler.stop_worker()
    print("Shutdown complete.")
    exit(0)


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
    cache_group = parser.add_argument_group(
        "Cache Settings - Hint for paddle ocr: You have to set PADDLE_OCR_BASE_DIR environment variable accordingly"
    )

    # Add Instagram related arguments to insta_group
    insta_group.add_argument(
        "--insta-target-user", help="Target instagram user to scan posts from"
    )
    insta_group.add_argument("--insta-user", help="Instagram login user")
    insta_group.add_argument("--insta-password", help="Instagram login password")
    insta_group.add_argument(
        "--update-interval",
        type=int,
        help="Interval in minutes between updates",
        default=240,
    )

    # Add Calendar related arguments to calendar_group
    calendar_group.add_argument("--calendar-user", help="Calendar username")
    calendar_group.add_argument("--calendar-password", help="Calendar password")
    calendar_group.add_argument("--calendar-url", help="Calendar URL")
    calendar_group.add_argument("--calendar-name", help="Calendar name to update")

    cache_group.add_argument(
        "--model-cache-path",
        help="Path to cache directory for downloaded models",
        default="./downloads/models",
    )
    cache_group.add_argument(
        "--insta-cache-path",
        help="Path to cache directory for instagram data",
        default="./downloads/instagram",
    )

    parsed_args = parser.parse_args()

    # Helper to choose CLI arg or environment variable
    def arg_or_env(arg_value, env_key):
        return arg_value if arg_value is not None else os.environ.get(env_key)

    # Resolve all inputs (Environment variable names documented here for clarity)
    insta_target_user = arg_or_env(parsed_args.insta_target_user, "INSTA_TARGET_USER")
    insta_user = arg_or_env(parsed_args.insta_user, "INSTA_USER")
    insta_password = arg_or_env(parsed_args.insta_password, "INSTA_PASSWORD")
    insta_update_interval = arg_or_env(
        parsed_args.update_interval, "INSTA_UPDATE_INTERVAL"
    )

    calendar_user = arg_or_env(parsed_args.calendar_user, "CALENDAR_USER")
    calendar_password = arg_or_env(parsed_args.calendar_password, "CALENDAR_PASSWORD")
    calendar_url = arg_or_env(parsed_args.calendar_url, "CALENDAR_URL")
    calendar_name = arg_or_env(parsed_args.calendar_name, "CALENDAR_NAME")

    model_cache_path = arg_or_env(parsed_args.model_cache_path, "MODEL_CACHE_PATH")
    insta_cache_path = arg_or_env(parsed_args.insta_cache_path, "INSTA_CACHE_PATH")

    # Convert update interval seconds (int) to timedelta; fallback to default (4h)
    try:
        update_interval_td = timedelta(minutes=int(insta_update_interval))
    except (ValueError, TypeError):
        print(
            f"Invalid update interval '{insta_update_interval}' provided; falling back to 240 minutes"
        )
        update_interval_td = timedelta(minutes=240)

    # TODO: check if all required params are provided
    def check_required(param, name):
        if param is None:
            raise ValueError(f"Missing required parameter: {name}")

    # Check required insta params
    check_required(insta_target_user, "insta_target_user")
    check_required(insta_user, "insta_user")
    check_required(insta_password, "insta_password")
    check_required(update_interval_td, "update_interval")
    # Check required calendar params
    check_required(calendar_user, "calendar_user")
    check_required(calendar_password, "calendar_password")
    check_required(calendar_url, "calendar_url")
    check_required(calendar_name, "calendar_name")
    # Check required cache params
    check_required(insta_cache_path, "insta_cache_path")
    check_required(model_cache_path, "model_cache_path")

    extractor = Extractor(mistral_models_folder=model_cache_path)

    if parsed_args.init:
        print("Exit after init the AI Extractor class")
        return 0

    init_media_handler(
        insta_cache_path,
        insta_target_user,
        insta_user,
        insta_password,
        update_interval=update_interval_td,
    )
    calendar = RemoteCal(
        user=calendar_user,
        password=calendar_password,
        url=calendar_url,
        calendar_name=calendar_name,
    )

    def on_new_photo(photo: DownloadedPhoto):
        events = []
        try:
            events = extractor.extract(photo.path)
        except Exception as error:
            print(f"Unable do proccess {photo.path}: {error}")

        for event in events:
            if not event.date:
                print(f"Event got no date - skipping {event.title}")
                continue
            print(event)
            calendar.addEvent(event)

    signal.signal(signal.SIGINT, sigint_handler)

    get_media_handler().add_on_new_photo_callback(on_new_photo)
    get_media_handler().trigger_new_photo_callbacks()

    # Keep the main thread alive to allow background updates
    print("Suffcal is running. Press Ctrl+C to exit.")
    try:
        signal.pause()
    except KeyboardInterrupt:
        sigint_handler(signal.SIGINT, None)
    return 0


if __name__ == "__main__":
    main()
