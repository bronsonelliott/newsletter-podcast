"""Read newsletters from one mailbox folder. The folder is opened read-only, so
nothing is marked as read, moved or deleted."""

import email
import email.policy
import imaplib
import re
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path

from . import PodcastError

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
FOOTER = re.compile(r"unsubscribe|view (this email )?in (your )?browser|manage (your )?preferences|update your profile", re.I)
INVISIBLE = re.compile("[­͏​-‏ -‮⁠-⁤﻿]")


@dataclass
class Issue:
    sender: str
    subject: str
    received: float     # seconds since 1970
    text: str
    message_id: str = ""


class TextFromHTML(HTMLParser):
    """Keep the words of an HTML email. Only scripts and styles are dropped:
    hiding more than that risks losing real text in badly built emails."""

    BREAKS = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "table", "blockquote", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipping = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skipping = True
        elif tag in self.BREAKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skipping = False
        elif tag in self.BREAKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(re.sub(r"\s+", " ", data))


def tidy(text):
    """Remove web addresses, invisible characters, short footer lines and blank runs."""
    text = INVISIBLE.sub("", text).replace("\xa0", " ")
    text = re.sub(r"\(\s*<?https?://[^\s)]*>?\s*\)?", "", text)      # a link in brackets, with its brackets
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^\s*(View image:|Follow image link:|Caption:)", "", text, flags=re.M)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if not (len(line) < 120 and FOOTER.search(line))]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def part_text(part):
    try:
        return part.get_content()
    except (LookupError, UnicodeDecodeError):      # unknown or wrong character set
        return (part.get_payload(decode=True) or b"").decode("utf-8", errors="replace")


def body_text(message):
    """Many newsletters send a stub as plain text ("view in browser"), so use
    whichever version has more words in it."""
    plain, page = "", ""
    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            continue
        kind = part.get_content_type()
        if kind == "text/plain":
            plain += part_text(part) + "\n"
        elif kind == "text/html":
            parser = TextFromHTML()
            parser.feed(part_text(part))
            parser.close()
            page += "".join(parser.parts) + "\n"
    plain, page = tidy(plain), tidy(page)
    return plain if len(plain) >= 0.8 * len(page) else page


def read_message(raw, received):
    message = email.message_from_bytes(raw, policy=email.policy.default)
    return Issue(sender=str(message.get("From", "")), subject=str(message.get("Subject", "")),
                 received=received, text=body_text(message),
                 message_id=str(message.get("Message-ID", "")).strip())


def imap_date(moment):
    return f"{moment.day:02d}-{MONTHS[moment.month - 1]}-{moment.year}"


def open_folder(mail, password, connect=imaplib.IMAP4_SSL):
    """Log in and open the folder read-only. Returns the connection and the message count."""
    if not password:
        raise PodcastError("IMAP_PASSWORD is missing from .env")
    if not mail["folder"].isascii():
        raise PodcastError("The mail folder name can only use plain English letters, numbers and symbols")
    try:
        # Python doesn't check the mail server's certificate unless asked to.
        box = connect(mail["host"], mail["port"], timeout=60, ssl_context=ssl.create_default_context())
        box.login(mail["user"], password)
        name = mail["folder"].replace("\\", "\\\\").replace('"', '\\"')
        status, data = box.select(f'"{name}"', readonly=True)
    except (imaplib.IMAP4.error, OSError) as problem:
        raise PodcastError(f"Could not read the mailbox at {mail['host']}: {problem}")
    if status != "OK":
        raise PodcastError(f"Could not open the mail folder \"{mail['folder']}\". In Gmail this is the label name.")
    return box, int(data[0])


def gmail_trash(box):
    """The name of Gmail's Trash folder, which depends on the account's language."""
    status, folders = box.list()
    for line in folders if status == "OK" else []:
        line = line.decode() if isinstance(line, bytes) else str(line)
        if "\\Trash" in line:
            return line.rsplit(' "/" ', 1)[-1]
    raise PodcastError("include_trash works only with Gmail, and no Trash folder was found")


def fetch_issues(mail, password, hours, connect=imaplib.IMAP4_SSL):
    """Every message received in the last `hours` hours."""
    oldest = time.time() - hours * 3600
    box, _ = open_folder(mail, password, connect)
    try:
        # SINCE only understands whole days and the server's time zone, so ask
        # for an extra day and check the exact time below.
        since = imap_date(datetime.fromtimestamp(oldest) - timedelta(days=1))
        issues = read_since(box, since, oldest)
        if mail["include_trash"]:
            # A Gmail filter that deletes newsletters on arrival keeps the label
            # but moves them to Trash, where the label's own folder can't see them.
            status, _ = box.select(gmail_trash(box), readonly=True)
            if status != "OK":
                raise PodcastError("Could not open Gmail's Trash folder")
            label = mail["folder"].replace(" ", "-").replace('"', "")
            issues += read_since(box, since, oldest, "X-GM-RAW", f'"label:{label}"')
        return issues
    except (imaplib.IMAP4.error, OSError) as problem:
        raise PodcastError(f"The mailbox connection failed: {problem}")
    finally:
        try:
            box.logout()
        except (imaplib.IMAP4.error, OSError):
            pass


def read_since(box, since, oldest, *also):
    """The messages in the open folder received after `oldest`."""
    status, data = box.search(None, "SINCE", since, *also)
    if status != "OK":
        raise PodcastError("The mailbox search failed")
    issues = []
    for number in data[0].split():
        status, reply = box.fetch(number, "(INTERNALDATE BODY.PEEK[])")
        found = [item for item in reply if isinstance(item, tuple)]
        if status != "OK" or not found:
            raise PodcastError("The mailbox stopped partway through. Try again.")
        stamp = imaplib.Internaldate2tuple(found[0][0])
        received = time.mktime(stamp) if stamp else time.time()
        if received >= oldest:
            issues.append(read_message(found[0][1], received))
    return issues


def choose_issues(issues, skip):
    """Drop skipped senders, empty messages and second copies. Returns (kept, dropped),
    where dropped is a list of (issue, reason)."""
    kept, dropped, seen = [], [], set()
    for issue in sorted(issues, key=lambda item: item.received):
        label = f"{issue.sender} {issue.subject}".lower()
        match = next((word for word in skip if word.strip() and word.lower() in label), None)
        same = (issue.sender.lower(), issue.subject.lower(), issue.text[:500])
        if match:
            dropped.append((issue, f'skip list: "{match}"'))
        elif not issue.text:
            dropped.append((issue, "no text"))
        elif (issue.message_id and issue.message_id in seen) or same in seen:
            dropped.append((issue, "second copy"))
        else:
            kept.append(issue)
            seen.update({same, issue.message_id} - {""})
    return kept, dropped


def demo_issues(folder):
    """The made-up newsletters in demo/. The first line of each file is its title."""
    issues = []
    for path in sorted(Path(folder).glob("newsletter-*.txt")):
        title, _, text = path.read_text().partition("\n")
        issues.append(Issue(sender=title.strip(), subject="Sample issue", received=time.time(), text=tidy(text)))
    return issues
