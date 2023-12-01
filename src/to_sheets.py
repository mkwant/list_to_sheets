import logging
import logging.handlers
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

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
class CurrentBowieList:
    """The current Bowie list as found online."""
    url: str
    last_modified: datetime
    filename: str = None

    def __post_init__(self):
        self.filename = self.url.split('/')[-1]


@dataclass
class GoogleDriveBowieList:
    """The Bowie list as found on Google Drive."""
    id: str
    last_modified: datetime


@dataclass
class ListUpdater:
    """Class to update a list."""
    google_drive_list: GoogleDriveBowieList
    current_list: CurrentBowieList
    drive: GoogleDrive
    tempfile_name: str = 'tmpfile.xlsx'
    google_drive_filename: str = 'bowielist'

    def _download_list(self) -> None:
        """Download a list."""
        logger.debug(f"Downloading {self.current_list.url} as {self.tempfile_name}")
        r = requests.get(url=self.current_list.url)
        with open(self.tempfile_name, 'wb') as f:
            f.write(r.content)

    def _is_list_newer(self) -> bool:
        return self.current_list.last_modified > self.google_drive_list.last_modified

    def _upload_file(self) -> None:
        """Upload the sheet to Google drive."""
        logger.debug(f"Uploading {self.tempfile_name} to Google Drive as '{self.google_drive_filename}'")
        if self.google_drive_list:
            if self._is_list_newer():
                logger.info(
                    f"Existing Google Drive file '{self.google_drive_filename}' found ({self.google_drive_list.id}), "
                    f"overwriting with newer file '{self.current_list.filename}'.")
                bowielist = self.drive.CreateFile({'id': self.google_drive_list.id})
            else:
                logger.info(f"Latest list already uploaded, exiting.")
                exit(0)
        else:
            logger.info(f"Existing Google Drive file '{self.google_drive_filename}' not found, creating new from "
                        f"'{self.current_list.filename}'")
            bowielist = self.drive.CreateFile({'title': self.google_drive_filename})
        bowielist.SetContentFile(filename=self.tempfile_name)
        bowielist.Upload({'convert': True})

    def _delete_temp_xlsx(self):
        """Delete the temp xlsx file."""
        logger.debug(f"Removing tempfile {self.tempfile_name}")
        os.remove(self.tempfile_name)

    def run(self):
        """Download Bowie-list. If newer than what is on Google Drive upload it there, overwriting the existing file."""
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


def get_google_drive_list(drive: GoogleDrive, google_drive_filename: str = 'bowielist') -> GoogleDriveBowieList | None:
    """Get the Bowie list as found on Google Drive."""
    search_result = drive.ListFile({'q': f"title='{google_drive_filename}' and trashed=false"}).GetList()
    if not search_result:
        return None
    gd_id = search_result[0]['id']
    gd_last_updated = date_parser.parse(search_result[0]['modifiedDate']).astimezone()
    gd_bowielist = GoogleDriveBowieList(id=gd_id, last_modified=gd_last_updated)
    logger.debug(f"List currently on Google Drive: {gd_bowielist}")
    return gd_bowielist


def get_current_list(url: str = 'http://ceruliz.nl/maarten/backup/') -> CurrentBowieList:  # noqa
    """Get the current Bowie list as found online."""
    logger.debug(f"Retrieving latest list from {url}")
    df = pd.read_html(url)[0]
    df = df[df['Name'].notna()]
    df = df.loc[df["Name"].str.contains('bowielist')]
    df = df.sort_values(by=['Last modified'], ascending=False)
    latest_list_row = df.iloc(0)[0]
    url = f"{url}{latest_list_row['Name']}"
    last_modified = date_parser.parse((latest_list_row['Last modified'])).astimezone()
    current_list = CurrentBowieList(url=url, last_modified=last_modified)
    logger.debug(f"Newest list found: {current_list}")
    return current_list


def main():
    drive = _google_drive_login()

    lu = ListUpdater(
        current_list=get_current_list(),
        google_drive_list=get_google_drive_list(drive=drive),
        drive=drive
    )

    lu.run()


if __name__ == '__main__':
    setup_logging(log_location=Path('bowielist.log'), log_level=os.getenv('LOG_LEVEL'))
    main()
