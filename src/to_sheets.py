import logging
import logging.handlers
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import dotenv
import pandas as pd
import requests
from dateutil import parser as date_parser
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from rich.logging import RichHandler

logger = logging.getLogger(__name__)
logging.getLogger("googleapiclient").setLevel(logging.WARNING)
logging.getLogger("oauth2client").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Reading environment variables
dotenv.load_dotenv()


def setup_logging(log_location: Path, log_level: str) -> None:
    default_fmt = "%(message)s"

    file_handler = logging.handlers.TimedRotatingFileHandler(log_location, when='W0')
    file_handler.formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')

    logging.basicConfig(
        level=log_level,
        format=default_fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            RichHandler(enable_link_path=False),
            file_handler
        ]
    )


@dataclass
class CurrentItem:
    """The current item as found online."""
    url: str
    last_modified: datetime
    filename: str = None

    def __post_init__(self):
        self.filename = self.url.split('/')[-1]


@dataclass
class GoogleDriveItem:
    """The item as found on Google Drive."""
    id: str | None
    last_modified: datetime | None
    filename: str


@dataclass
class ListUpdater:
    """Class to download a file from a weblocation and upload it to Google sheets if newer than the copy there."""
    google_drive_item: GoogleDriveItem
    current_item: CurrentItem
    drive: GoogleDrive

    def _download_list(self) -> None:
        """Download a list."""
        logger.debug(f"Downloading {self.current_item.url}")
        r = requests.get(url=self.current_item.url)
        with open(self.current_item.filename, 'wb') as f:
            f.write(r.content)

    def _is_list_newer(self) -> bool:
.        """Compare lists to see if downloaded list is newer than Google Drive list"""
        return self.current_item.last_modified > self.google_drive_item.last_modified

    def _upload_file(self) -> None:
        """Upload the sheet to Google drive."""
        logger.debug(f"Uploading {self.current_item.filename} to Google Drive as '{self.google_drive_item.filename}'")
        if self.google_drive_item.id:
            logger.info(
                f"Existing Google Drive file '{self.google_drive_item.filename}' found "
                f"({self.google_drive_item.id}), overwriting with newer file '{self.current_item.filename}'.")
            drive_item = self.drive.CreateFile({'id': self.google_drive_item.id})

        else:
            logger.info(f"Existing Google Drive file '{self.google_drive_item.filename}' not found, creating new from "
                        f"'{self.current_item.filename}'")
            drive_item = self.drive.CreateFile({'title': self.google_drive_item.filename})
        drive_item.SetContentFile(filename=self.current_item.filename)
        drive_item.Upload({'convert': True})

    def _delete_temp_xlsx(self):
        """Delete the temp xlsx file."""
        logger.debug(f"Removing tempfile {self.current_item.filename}")
        os.remove(self.current_item.filename)

    def run(self):
        """Download item. If newer than what is on Google Drive upload it there, overwriting the existing file."""
        if not self._is_list_newer():
            logger.info(f"Latest list already uploaded, exiting.")
            return
        self._download_list()
        self._upload_file()
        self._delete_temp_xlsx()


def _google_drive_login() -> GoogleDrive:
    """Authenticate to Google drive using the saved credentials, return a Google Drive object."""
    gauth = GoogleAuth()
    # Try to load saved client credentials
    gauth.LoadCredentialsFile("mycreds.json")
    if gauth.credentials is None:
        # Authenticate if they're not there
        # Force offline mode
        logger.debug("Credentials not there, authenticating")
        gauth.GetFlow()
        gauth.flow.params.update({'access_type': 'offline'})
        gauth.flow.params.update({'approval_prompt': 'force'})
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        logger.debug("Token expired, refreshing token")
        gauth.Refresh()
    else:
        # Initialize the saved creds
        logger.debug("Authorizing access")
        gauth.Authorize()
    # Save the current credentials to a file
    logger.debug("Saving credentials")
    gauth.SaveCredentialsFile("mycreds.json")
    drive = GoogleDrive(gauth)
    return drive


def get_google_drive_item(drive: GoogleDrive, google_drive_filename: str) -> GoogleDriveItem | None:
    """Get the item as found on Google Drive."""
    search_result = drive.ListFile({'q': f"title='{google_drive_filename}' and trashed=false"}).GetList()
    if not search_result:
        gd_id = None
        gd_last_updated = date_parser.parse('1971-01-01 0:00').astimezone()
    else:
        gd_id = search_result[0]['id']
        gd_last_updated = date_parser.parse(search_result[0]['modifiedDate']).astimezone()
    gd_item = GoogleDriveItem(id=gd_id, last_modified=gd_last_updated, filename=google_drive_filename)
    logger.debug(f"Item currently on Google Drive: {gd_item}")
    return gd_item


def get_current_item(url: str, item_filename_contains: str) -> CurrentItem:
    """Get the current item as found online."""
    logger.debug(f"Retrieving latest item from {url}")

    # Parsing the directory listing
    df = pd.read_html(url, extract_links='body')[0]
    df = df[df['Name'].notna()]
    _, df['Name'] = zip(*df['Name'])
    df['Last modified'], _ = zip(*df['Last modified'])
    df = df[df['Name'].notna()]

    df = df.loc[df['Name'].str.contains(item_filename_contains)]
    df = df.sort_values(by=['Last modified'][0], ascending=False)
    latest_item_row = df.iloc(0)[0]
    url = f"{url}{latest_item_row['Name']}"
    last_modified = date_parser.parse((latest_item_row['Last modified'])).astimezone()

    # Instantiating class
    current_item = CurrentItem(url=url, last_modified=last_modified)
    logger.debug(f"Newest item found: {current_item}")
    return current_item


def main():
    drive = _google_drive_login()

    lu = ListUpdater(
        current_item=get_current_item(url=os.getenv('LIST_LOCATION'), item_filename_contains='bowielist'),
        google_drive_item=get_google_drive_item(drive=drive, google_drive_filename='bowielist'),
        drive=drive
    )

    lu.run()


if __name__ == '__main__':
    setup_logging(log_location=Path('bowielist.log'), log_level=os.getenv('LOG_LEVEL'))
    main()
