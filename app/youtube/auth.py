import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from app.config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

class YouTubeAuth:
    def __init__(self):
        self.credentials_dir = settings.CREDENTIALS_DIR
        self.token_file = self.credentials_dir / "youtube_token.json"
        self.client_secret_file = self.credentials_dir / "google_client_secret.json"


    def get_authenticated_service(self):
        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)

        if not creds or not creds.valid:
            if self.client_secret_file.exists():
                logger.info(f"Authenticating via YouTube OAuth client secrets file: {self.client_secret_file}")
                flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secret_file), SCOPES)
                creds = flow.run_local_server(port=0)
                with open(self.token_file, "w") as token:
                    token.write(creds.to_json())
            else:
                logger.warning(
                    "No google_client_secret.json found in credentials directory. "
                    "YouTube uploads require OAuth authorization."
                )
                return None

        return build("youtube", "v3", credentials=creds)

youtube_auth = YouTubeAuth()
