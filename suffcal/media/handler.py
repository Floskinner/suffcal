from pathlib import Path
from typing import Optional
from instagrapi import Client

from suffcal.media.types import MediaType

MAX_DOWNLOADS = 20


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


class __Handler:
    def __init__(self, download_path: Path, target_user: str, user: str, password: str):
        self.client = Client()
        self.client.login(user, password)
        self.user_id = self.client.user_id_from_username(target_user)

        self.download_path = download_path
        self.new_photos_dir = self.download_path / "new_photos"
        self.processed_photos_dir = self.download_path / "processed_photos"

        self.new_photos_dir.mkdir(parents=True, exist_ok=True)
        self.processed_photos_dir.mkdir(parents=True, exist_ok=True)

    def __del__(self):
        self.client.logout()

    def get_photos_since_last_check(self) -> list[DownloadedPhoto]:
        return self._get_new_photos()

    def update_posts(
        self, type: MediaType = MediaType.PHOTO, max_downloads: int = MAX_DOWNLOADS
    ):
        latest_id: Optional[str] = None
        if self._get_new_photos(amount=1):
            latest_id = self._get_new_photos(amount=1)[0].id
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
        photo.path.rename(self.processed_photos_dir / photo.path.name)

    def _get_new_photos(self, amount: Optional[int] = None) -> list[DownloadedPhoto]:
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


# Singleton pattern
__handler_instance: Optional[__Handler] = None


def init_handler(
    download_path: Path, target_user: str, user: str, password: str
) -> None:
    global __handler_instance
    if __handler_instance is not None:
        raise ValueError("Handler already initialized")
    __handler_instance = __Handler(download_path, target_user, user, password)


def get_handler() -> __Handler:
    global __handler_instance
    if __handler_instance is None:
        raise ValueError("Handler not initialized")
    return __handler_instance
