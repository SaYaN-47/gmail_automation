import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main():
    creds = None

    # Load existing token
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    # Login if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    # Connect to Gmail
    service = build(
        "gmail",
        "v1",
        credentials=creds
    )

    # Get latest email
    results = service.users().messages().list(
        userId="me",
        maxResults=1
    ).execute()

    messages = results.get("messages", [])

    if not messages:
        print("No emails found.")
        return

    message_id = messages[0]["id"]

    # Get full email
    message = service.users().messages().get(
        userId="me",
        id=message_id
    ).execute()

    headers = message["payload"]["headers"]

    sender = ""
    subject = ""

    for header in headers:
        if header["name"].lower() == "from":
            sender = header["value"]

        if header["name"].lower() == "subject":
            subject = header["value"]

    snippet = message.get("snippet", "")

    print("\n===== LATEST EMAIL =====")
    print("From:", sender)
    print("Subject:", subject)
    print("Preview:", snippet)
    print("========================\n")


if __name__ == "__main__":
    main()