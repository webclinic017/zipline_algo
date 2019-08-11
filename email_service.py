from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path
import base64
from email.mime.text import MIMEText
import os
from sqlalchemy import create_engine
import pandas as pd

from apiclient import errors

SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send'
]


class EmailService:
    def initialize(self):
        """Shows basic usage of the Gmail API.
                Lists the user's Gmail labels.
                """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(os.path.join(str(Path.home()), 'token.pickle')):
            with open(os.path.join(str(Path.home()), 'token.pickle'), 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.path.join(str(Path.home()), 'credentials.json'), SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(os.path.join(str(Path.home()), 'token.pickle'), 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)

        self.engine = create_engine('sqlite:///{}'.format(os.path.join(str(Path.home()), 'algodb.db')))
        self.members = pd.read_sql("select * from member", self.engine)

    def SendMessage(self, subject, message_text):
        """Send an email message.

        Args:
          service: Authorized Gmail API service instance.
          user_id: User's email address. The special value "me"
          can be used to indicate the authenticated user.
          message: Message to be sent.

        Returns:
          Sent Message.
        """
        emails = ";".join(list(self.members[self.members['order_notification'] == 1]['email']))
        message = self.CreateMessage(emails, subject, message_text)

        try:
            message = (self.service.users().messages().send(userId="me", body=message)
                       .execute())
            print('Message Id: %s' % message['id'])
            return message
        except errors.HttpError as error:
            print('An error occurred: %s' % error)

    def SendNotifications(self, subject, message_text):
        """Send an email message.

        Args:
          service: Authorized Gmail API service instance.
          user_id: User's email address. The special value "me"
          can be used to indicate the authenticated user.
          message: Message to be sent.

        Returns:
          Sent Notifications.
        """
        emails = ";".join(list(self.members[self.members['daily_notification'] == 1]['email']))
        message = self.CreateMessage(emails, subject, message_text)

        try:
            message = (self.service.users().messages().send(userId="me", body=message)
                       .execute())
            print('Message Id: %s' % message['id'])
            return message
        except errors.HttpError as error:
            print('An error occurred: %s' % error)

    def CreateMessage(self, to, subject, message_text):
        """Create a message for an email.

        Args:
          sender: Email address of the sender.
          to: Email address of the receiver.
          subject: The subject of the email message.
          message_text: The text of the email message.

        Returns:
          An object containing a base64url encoded email object.
        """
        message = MIMEText(message_text)
        message['bcc'] = to
        message['from'] = 'denis@dariotis.com'
        message['subject'] = subject
        return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}


if __name__ == '__main__':
    email_service = EmailService()
    email_service.initialize()
    # email_service.SendMessage('order_placed', 'GOOG:SELL:10')
