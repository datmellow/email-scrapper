import datetime
import email
import imaplib
import logging
import typing

from email_scrapper.email_settings import Email
from email_scrapper.models import Order, Stores
from email_scrapper.readers.base_reader import BaseReader

logger = logging.getLogger(__name__)


class SmtpReader(BaseReader):

    def __init__(self, username: str, password: str, settings: Email = Email.GMAIL, email_address: str = None,
                 locations: typing.Dict[Stores, str] = None,
                 date_from: datetime.datetime = None):
        """

        :param username: The SMTP username to log in with
        :param password:  The SMTP password to log in with
        :param settings:  The SMTP settings. Defaults to GMAIL
        :param email_address: The email address that will be looked for using the TO header. Defaults to username if
            not specified
        :param locations: Optional labels to look under
        :param date_from: How far back to search emails from. Default to 7 days.
        """
        super(SmtpReader, self).__init__(date_from=date_from, user_email=email_address or username)
        self.username = username
        self._password = password
        self.mail = imaplib.IMAP4_SSL(*settings.value)
        self.email_locations = locations or {}

    def read_store_emails(self, store: Stores, subject: str = None) -> typing.Iterable[str]:
        location = self.email_locations.get(store)
        if location:
            self.mail.select(location)
        search_query = self.get_search_query(store, subject)
        result, amazon_data = self.mail.uid('search', None, search_query)
        for num in amazon_data[0].split():
            m, v = self.mail.uid("fetch", num, "(RFC822)")
            msg_body = email.message_from_bytes(v[0][1])
            yield msg_body

    def finish(self):
        self.mail.logout()

    def run(self) -> typing.List[Order]:
        self.mail.login(self.username, self._password)
        self.mail.select('inbox')
        return_data = []
        stores = [store for store in Stores]
        for store in stores:
            store_data = self.get_store(store)
            if store_data:
                return_data.extend(store_data)
        self.finish()
        return return_data
