import threading
from flask import Flask

import os
import json
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from twilio.rest import Client
from dotenv import load_dotenv


# ============================================================
# SETTINGS
# ============================================================

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CHECK_INTERVAL = 30          # Check Gmail every 30 seconds
STATE_FILE = "gmail_state.json"


# ============================================================
# FLASK WEB SERVER
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Gmail to WhatsApp service is running!"


@app.route("/health")
def health():
    return "OK", 200


def start_web_server():

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )


# ============================================================
# TWILIO
# ============================================================

load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_whatsapp = os.getenv("TWILIO_WHATSAPP_NUMBER")
to_whatsapp = os.getenv("MY_WHATSAPP_NUMBER")


twilio_client = Client(
    account_sid,
    auth_token
)


# ============================================================
# GMAIL AUTHENTICATION
# ============================================================

def get_gmail_service():

    print("Starting Gmail authentication...", flush=True)

    creds = None

    if os.path.exists("token.json"):

        print(
            "token.json found.",
            flush=True
        )

        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    else:

        print(
            "token.json not found.",
            flush=True
        )

    if not creds or not creds.valid:

        print(
            "Gmail credentials are not valid.",
            flush=True
        )

        if creds and creds.expired and creds.refresh_token:

            print(
                "Access token expired. Refreshing using refresh token...",
                flush=True
            )

            creds.refresh(Request())

            print(
                "Token refreshed successfully.",
                flush=True
            )

        else:

            print(
                "Starting OAuth authorization...",
                flush=True
            )

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(
                port=0
            )

        with open("token.json", "w") as token:

            token.write(
                creds.to_json()
            )

            print(
                "Updated token.json.",
                flush=True
            )

    else:

        print(
            "Existing Gmail credentials are valid.",
            flush=True
        )

    print(
        "Building Gmail API service...",
        flush=True
    )

    service = build(
        "gmail",
        "v1",
        credentials=creds
    )

    print(
        "Gmail API service created.",
        flush=True
    )

    return service


# ============================================================
# STATE
# ============================================================

def load_state():

    if not os.path.exists(STATE_FILE):

        print(
            "No Gmail state file found. Creating initial state.",
            flush=True
        )

        return {
            "initialized": False,
            "processed_ids": []
        }

    with open(STATE_FILE, "r") as file:

        state = json.load(file)

    print(
        "Gmail state loaded.",
        flush=True
    )

    return state


def save_state(state):

    with open(STATE_FILE, "w") as file:

        json.dump(
            state,
            file,
            indent=4
        )

    print(
        "Gmail state saved.",
        flush=True
    )


# ============================================================
# GET EMAIL INFORMATION
# ============================================================

def get_email(service, message_id):

    message = service.users().messages().get(
        userId="me",
        id=message_id
    ).execute()

    headers = message["payload"]["headers"]

    sender = ""
    subject = ""

    for header in headers:

        name = header["name"].lower()

        if name == "from":

            sender = header["value"]

        elif name == "subject":

            subject = header["value"]

    snippet = message.get(
        "snippet",
        ""
    )

    return {
        "id": message_id,
        "sender": sender,
        "subject": subject,
        "snippet": snippet
    }


# ============================================================
# SEND WHATSAPP
# ============================================================

def send_whatsapp(email):

    text = (
        "📧 NEW EMAIL\n\n"
        f"From: {email['sender']}\n\n"
        f"Subject: {email['subject']}\n\n"
        f"Preview:\n{email['snippet']}"
    )

    print(
        "Sending WhatsApp message...",
        flush=True
    )

    message = twilio_client.messages.create(
        from_=from_whatsapp,
        to=to_whatsapp,
        body=text
    )

    print(
        "WhatsApp sent!",
        flush=True
    )

    print(
        "SID:",
        message.sid,
        flush=True
    )


# ============================================================
# CHECK FOR NEW EMAILS
# ============================================================

def check_for_new_emails(service, state):

    print(
        "Checking Gmail...",
        flush=True
    )

    results = service.users().messages().list(
        userId="me",
        maxResults=20
    ).execute()

    messages = results.get(
        "messages",
        []
    )

    print(
        f"Gmail returned {len(messages)} messages.",
        flush=True
    )

    if not messages:

        print(
            "No emails found.",
            flush=True
        )

        return

    processed_ids = set(
        state["processed_ids"]
    )


    # --------------------------------------------------------
    # FIRST RUN
    # --------------------------------------------------------

    if not state["initialized"]:

        print(
            "First Gmail check.",
            flush=True
        )

        for message in messages:

            processed_ids.add(
                message["id"]
            )

        state["processed_ids"] = list(
            processed_ids
        )

        state["initialized"] = True

        save_state(state)

        print(
            "Initial Gmail state saved.",
            flush=True
        )

        print(
            "Existing emails will not be forwarded.",
            flush=True
        )

        return


    # --------------------------------------------------------
    # FIND NEW EMAILS
    # --------------------------------------------------------

    new_messages = []

    for message in messages:

        message_id = message["id"]

        if message_id not in processed_ids:

            new_messages.append(
                message
            )


    # Gmail returns newest first.
    # Reverse them so multiple new emails
    # are sent oldest → newest.

    new_messages.reverse()


    print(
        f"New emails detected: {len(new_messages)}",
        flush=True
    )


    # --------------------------------------------------------
    # SEND NEW EMAILS
    # --------------------------------------------------------

    for message in new_messages:

        message_id = message["id"]

        try:

            email = get_email(
                service,
                message_id
            )

            print(
                "New email detected!",
                flush=True
            )

            print(
                "From:",
                email["sender"],
                flush=True
            )

            print(
                "Subject:",
                email["subject"],
                flush=True
            )

            send_whatsapp(
                email
            )

            processed_ids.add(
                message_id
            )

        except Exception as error:

            print(
                "Error processing email:",
                flush=True
            )

            print(
                error,
                flush=True
            )


    # --------------------------------------------------------
    # SAVE STATE
    # --------------------------------------------------------

    state["processed_ids"] = list(
        processed_ids
    )

    # Keep only the most recent 100 IDs

    state["processed_ids"] = (
        state["processed_ids"][-100:]
    )

    save_state(state)


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    # --------------------------------------------------------
    # START FLASK SERVER
    # --------------------------------------------------------

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()


    # --------------------------------------------------------
    # GMAIL → WHATSAPP
    # --------------------------------------------------------

    print(
        "==============================",
        flush=True
    )

    print(
        " Gmail → WhatsApp Forwarder",
        flush=True
    )

    print(
        "==============================",
        flush=True
    )

    print(
        "Connecting to Gmail...",
        flush=True
    )

    service = get_gmail_service()

    print(
        "Gmail connected.",
        flush=True
    )

    print(
        flush=True
    )

    print(
        f"Checking Gmail every {CHECK_INTERVAL} seconds...",
        flush=True
    )

    print(
        "Press CTRL+C to stop.",
        flush=True
    )

    print(
        flush=True
    )

    state = load_state()


    # --------------------------------------------------------
    # CONTINUOUS LOOP
    # --------------------------------------------------------

    while True:

        try:

            check_for_new_emails(
                service,
                state
            )

        except Exception as error:

            print(
                "ERROR:",
                flush=True
            )

            print(
                error,
                flush=True
            )

        time.sleep(
            CHECK_INTERVAL
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()