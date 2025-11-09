from pathlib import Path
from typing import Any, List, Optional
from collections.abc import Callable
from instagrapi import Client
from datetime import timedelta
import threading
import time

from suffcal.media_types import MediaType


class DownloadedPhoto:
    def __init__(self, path: Path):
        self.path = path

    @property
    def name(self) -> str:
        """Returns the string name of the photo without the unique id suffix"""
        # it is possible that the name itself contains underscores
        # so we join all parts except the last one (the unique id)
        return "_".join(self.path.name.split("_")[:-1])

    @property
    def id(self) -> str:
        # remove suffix for proper id extraction
        return self.path.with_suffix("").name.split("_")[-1]


class MediaHandler:
    def __init__(
        self,
        download_path: Path,
        target_user: str,
        user: str,
        password: str,
        update_interval: timedelta = timedelta(hours=4),
        no_auto_update: bool = False,
    ):
        """Handles the downloading and processing of media files from Instagram. Automatically starts a background thread to periodically check for new posts.
        It should be instantiated only once, so use the init_handler and get_handler functions to manage the singleton instance.

        Args:
            download_path (Path): The path to the directory where downloaded media files will be saved.
            target_user (str): The username of the Instagram account to download media from.
            user (str): The username of the Instagram account to log in with.
            password (str): The password of the Instagram account to log in with.
            update_interval (timedelta, optional): The interval at which to check for new posts.
            no_auto_update (bool, optional): If true, does not start the automatic update proccess for pulling images
        """
        self.client = Client()
        self.client.login(user, password)
        self.user_id = self.client.user_id_from_username(target_user)

        self.download_path = download_path
        self.new_photos_dir = self.download_path / "new_photos"
        self.processed_photos_dir = self.download_path / "processed_photos"

        self.new_photos_dir.mkdir(parents=True, exist_ok=True)
        self.processed_photos_dir.mkdir(parents=True, exist_ok=True)

        self._on_new_photo_callback: List[Callable[[DownloadedPhoto], None]] = []

        self._stop_event = threading.Event()
        self._stop_event.clear()

        # Update the post once at creation to be up-to-date
        self.update_posts()
        self.update_thread = threading.Thread(
            target=self._update_worker,
            name=f"{__name__}:update_worker",
            args=(),
            kwargs={"interval": update_interval},
            daemon=False,
        )
        if not no_auto_update:
            self.update_thread.start()

    def __del__(self):
        self.client.logout()

    def get_photos_since_last_check(self) -> list[DownloadedPhoto]:
        """Photos are not marked as processed after being returned!

        Returns:
            list[DownloadedPhoto]: A list of unprocessed photos.
        """
        photos = self._get_unprocessed_photos()
        return photos

    def add_on_new_photo_callback(
        self, callback: Callable[[DownloadedPhoto], Any]
    ) -> None:
        """Registers a callback to be called when a new photo is downloaded.
        Automatically marks the photo as processed after the callback is called.

        Args:
            callback (Callable[[DownloadedPhoto], Any]): Function to call when a new photo is downloaded.
        """

        def marked_wrapper(photo: DownloadedPhoto):
            result = callback(photo)
            self.mark_photo_as_processed(photo)
            return result

        self._on_new_photo_callback.append(marked_wrapper)

    def update_posts(self, type: MediaType = MediaType.PHOTO, max_downloads: int = 20):
        """Downloads new posts of the specified type from the target user.
        Stops downloading when it reaches the latest downloaded post or the max_downloads limit.

        Args:
            type (MediaType, optional): The type of media to download.
            max_downloads (int, optional): The maximum number of posts to download.
        """
        latest_id: Optional[str] = None
        if self._get_unprocessed_photos(amount=1):
            latest_id = self._get_unprocessed_photos(amount=1)[0].id
        elif self._get_processed_photos(amount=1):
            latest_id = self._get_processed_photos(amount=1)[0].id

        posts = self.client.user_medias(self.user_id, amount=max_downloads)

        counter = 0
        for post in posts:
            if str(post.pk) == latest_id or counter >= max_downloads:
                break

            if post.media_type == type:
                self.client.photo_download(post.pk, folder=self.new_photos_dir)
                counter += 1

    def mark_photo_as_processed(self, photo: DownloadedPhoto) -> None:
        """This photo is marked as proccessed and can be delete in the future during some cleanup jobs"""
        photo.path.rename(self.processed_photos_dir / photo.path.name)

    def _get_unprocessed_photos(
        self, amount: Optional[int] = None
    ) -> list[DownloadedPhoto]:
        if amount:
            return [DownloadedPhoto(path) for path in self.new_photos_dir.glob("*")][
                :amount
            ]
        else:
            return [DownloadedPhoto(path) for path in self.new_photos_dir.glob("*")]

    def _get_processed_photos(
        self, amount: Optional[int] = None
    ) -> list[DownloadedPhoto]:
        if amount:
            return [
                DownloadedPhoto(path) for path in self.processed_photos_dir.glob("*")
            ][:amount]
        else:
            return [
                DownloadedPhoto(path) for path in self.processed_photos_dir.glob("*")
            ]

    def _update_worker(self, interval: timedelta):
        """Background worker to periodically update posts.
        Should be run in a separate thread."""
        while not self._stop_event.is_set():
            self.update_posts()
            time.sleep(interval.total_seconds())


# Singleton pattern
__handler_instance: Optional[MediaHandler] = None


def init_media_handler(*args, **kwargs) -> None:
    global __handler_instance
    if __handler_instance is not None:
        raise ValueError("Handler already initialized")
    __handler_instance = MediaHandler(*args, **kwargs)


def get_media_handler() -> MediaHandler:
    global __handler_instance
    if __handler_instance is None:
        raise ValueError("Handler not initialized")
    return __handler_instance
