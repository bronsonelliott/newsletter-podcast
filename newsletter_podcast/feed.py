"""Keep the episode list, build the podcast feed and serve it on your own network."""

import json
import re
import secrets
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

EPISODE = re.compile(r"^episode-(\d{4}-\d{2}-\d{2})\.(mp3|txt|json)$")
ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"


def write_safely(path, text):
    """Write to a temporary file and swap it in, so a crash can't leave half a file."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def feed_token(folder):
    """A random word in the feed address, so other devices can't guess it."""
    path = folder / ".feed-token"
    if not path.exists():
        path.touch(mode=0o600)
        path.write_text(secrets.token_urlsafe(18))
    return path.read_text().strip()


def feed_address(config, folder):
    return f"{config['feed']['base_url'].rstrip('/')}/{feed_token(folder)}"


def save_episode(folder, date, seconds, issues, usage):
    details = {"date": date, "seconds": round(seconds), "made": datetime.now().timestamp(),
               "sources": [f"{issue.sender}: {issue.subject}" for issue in issues], "usage": usage}
    write_safely(folder / f"episode-{date}.json", json.dumps(details, indent=1))


def remove_old(folder, keep_days, today=None):
    """Delete this program's own episode files older than keep_days. Nothing else is touched."""
    oldest = ((today or datetime.now()) - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    removed = []
    for path in sorted(folder.iterdir()):
        match = EPISODE.match(path.name)
        if match and path.is_file() and match.group(1) < oldest:
            path.unlink()
            removed.append(path.name)
    return removed


def build_feed(folder, config):
    address = feed_address(config, folder)
    ET.register_namespace("itunes", ITUNES)
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    def add(parent, tag, text="", **attributes):
        ET.SubElement(parent, tag, attributes).text = text or None

    add(channel, "title", config["show"]["name"])
    add(channel, "link", address)
    add(channel, "description", "A private briefing made from my own newsletters.")
    add(channel, "language", "en-us")
    add(channel, f"{{{ITUNES}}}block", "Yes")      # ask podcast directories not to list it
    add(channel, f"{{{ITUNES}}}explicit", "false")
    for path in sorted(folder.glob("episode-*.json"), reverse=True):
        details = json.loads(path.read_text())
        date, mp3 = details["date"], path.with_suffix(".mp3")
        if not mp3.exists():
            continue
        item = ET.SubElement(channel, "item")
        day = datetime.strptime(date, "%Y-%m-%d")
        add(item, "title", f"{config['show']['name']}, {day:%B} {day.day}, {day.year}")
        add(item, "description", "Made from: " + "; ".join(details["sources"]))
        add(item, "enclosure", url=f"{address}/{mp3.name}", length=str(mp3.stat().st_size), type="audio/mpeg")
        add(item, "guid", f"newsletter-podcast-{date}", isPermaLink="false")
        add(item, "pubDate", formatdate(details["made"], localtime=True))
        add(item, f"{{{ITUNES}}}duration", str(details["seconds"]))
    ET.indent(rss)
    write_safely(folder / "feed.xml", '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode") + "\n")


def make_server(config, folder):
    """Serve feed.xml and the MP3s, and nothing else in the folder."""
    token = feed_token(folder)

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.reply(send_body=False)

        def do_GET(self):
            self.reply(send_body=True)

        def reply(self, send_body):
            parts = self.path.split("?")[0].strip("/").split("/")
            name = parts[1] if len(parts) == 2 and secrets.compare_digest(parts[0].encode(), token.encode()) else ""
            match = EPISODE.match(name)
            path = folder / name
            allowed = name == "feed.xml" or (match and match.group(2) == "mp3")
            if not allowed or not path.is_file():
                self.send_error(404)
                return
            size = path.stat().st_size
            start, end, status = 0, size - 1, 200
            # Podcast apps ask for pieces of a file so they can skip around in it.
            wanted = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
            if wanted and (wanted.group(1) or wanted.group(2)):
                first, last = wanted.groups()
                if first:
                    start, end = int(first), min(int(last), size - 1) if last else size - 1
                else:
                    start = max(size - int(last), 0)
                status = 206
                if start >= size or start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
            self.send_response(status)
            self.send_header("Content-Type", "audio/mpeg" if match else "application/rss+xml; charset=utf-8")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if send_body:
                left = end - start + 1
                with path.open("rb") as file:
                    file.seek(start)
                    while left > 0 and (chunk := file.read(min(65536, left))):
                        self.wfile.write(chunk)
                        left -= len(chunk)

        def log_message(self, pattern, *values):
            pass        # the address holds the secret word, so don't log it

    return ThreadingHTTPServer((config["feed"]["host"], config["feed"]["port"]), Handler)
