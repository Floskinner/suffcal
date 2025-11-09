# https://cloud.floskinner.de/remote.php/dav/calendars/Floskinner/feste/
from caldav.davclient import DAVClient
from suffcal.extractor import Event
import datetime


class RemoteCal:
    def __init__(self, user: str, password: str, url: str, calendar_name: str):
        self.client = DAVClient(
            url=url,
            username=user,
            password=password,
        )
        principal = self.client.principal()
        print([c.name for c in principal.calendars()])
        self.calendar = principal.calendar(name=calendar_name)

    def __del__(self):
        self.client.close()

    def addEvent(self, event: Event):
        if event.date < datetime.datetime.now():
            print(f"Not adding event, it is in the past: {event.date}")
            return

        self.calendar.save_event(
            summary=event.title,
            dtstart=event.date,
            dtend=event.date,
            description=f"Original text: {event.original_text}",
            location=event.location,
        )
