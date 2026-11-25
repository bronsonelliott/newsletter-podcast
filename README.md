# Newsletter podcast

Turn the newsletters piling up in your inbox into one private podcast episode a day.

It reads one mailbox folder, asks Claude to write a script that covers everything in it, and reads the script aloud on your own computer. When several newsletters cover the same story, you hear it once. When one of them corrects the others, you hear the correction.

- **Your newsletters, your show.** You choose the folder, the length, the topics that always get a section, and the voice. Two voices work out of the box or with one extra install, and you can also take the script as text and use your own. The show's instructions are in `prompt.md`, in plain English, for you to edit.
- **No newsletter is cut short.** Claude gets the full text of each one, minus links and footer lines. If there's too much, the program stops and tells you. Anything it leaves out (your skip list, second copies, empty emails) is listed when you run it.
- **Private.** Episodes stay on your computer. Nothing is published.
- **Claude can't do anything but write.** It gets text, with no tools, files, web access or passwords.

I've had a personal version of this running daily since at least April 2026, and [wrote about it here](https://bronsonelliott.substack.com/p/i-built-a-daily-ai-podcast-that-runs). This is a new, simpler build of the same idea. See [What's been tested](#whats-been-tested) before you rely on it.

## Try it first, without your email

The repo comes with 12 made-up newsletters in `demo/`. Two of them bury a correction to a story the others got wrong: `newsletter-08.txt` limits a price cut, and `newsletter-11.txt` limits a launch. Listen for both. Every company and person in them is invented.

The demo calls Claude, so it costs about $0.22 with an API key, or counts against your Claude plan. See [What it costs](#what-it-costs).

### 1. Install

You need a Mac. (Linux may work, but it's untested and has no built-in voice.) With [Homebrew](https://brew.sh), this installs two programs: `uv`, which runs Python, and `ffmpeg`, which makes the MP3.

```bash
brew install uv ffmpeg
```

Download the project and go into its folder. (If macOS offers to install its command line developer tools, accept, then run the first command again.)

```bash
git clone https://github.com/bronsonelliott/newsletter-podcast.git
```

```bash
cd newsletter-podcast
```

Run every command from here on in this folder. Give the project its own Python, which every `uv run` command then uses:

```bash
uv venv --python 3.12
```

### 2. Choose how to reach Claude

Make your own copies of the two settings files. Git ignores both, so they never get uploaded:

```bash
cp config.example.toml config.toml
```

```bash
cp .env.example .env && chmod 600 .env
```

`chmod 600` means only your account can read `.env`, which holds your passwords. The program refuses to start if other accounts can read it.

Then pick one:

- **Claude Code**, if you already have it installed and signed in. This is the way I tested. In `config.toml`, change `backend = "api"` to `backend = "claude-code"`, keeping the quotes. It counts against your plan's limits. I tested with version 2.1.332. If a run stops with `unknown option`, run `claude update`.
- **An Anthropic API key.** Get one at [console.anthropic.com](https://console.anthropic.com/settings/keys) and paste it in `.env` right after `ANTHROPIC_API_KEY=`, with no spaces or quotes. You pay for what you use. This way needs one more install, the `anthropic` package and about 15 small ones it needs:

  ```bash
  uv pip install -r requirements.txt
  ```

These open the two files in TextEdit. (`.env` is hidden, so you won't see it in Finder.) Save and close when you're done. If you type any new quotes, first turn off **Edit > Substitutions > Smart Quotes**, because curly quotes break the settings file:

```bash
open -e config.toml
```

```bash
open -e .env
```

### 3. Make the demo episode

```bash
uv run podcast.py demo
```

It takes a minute or two. You should see something like this:

```
12 newsletters, 79,682 characters
Writing the script with claude-opus-5-5 ...
  2,164 words (25,962 tokens in, 5,701 out)
Recording with the mac voice ...
Episode: .../output/demo/episode-2026-11-24.mp3 (11 min 44 s)
```

To see the files, run this. It opens the folder in Finder. The `.mp3` is the episode and the `.txt` is its script:

```bash
open output/demo
```

## Pick a voice

Set `engine` under `[audio]` in `config.toml`:

| Engine | What you get | What it needs |
|---|---|---|
| `"mac"` | The voice built into your Mac. This is the default, so you can try things right away | Nothing more |
| `"kokoro"` | A free voice model that runs on your computer and sounds more natural. **This is the one I'd use for a daily show** | The install below |
| `"none"` | The script as text, for any text-to-speech tool you like | Nothing more |

To hear today's demo in a different voice, change `engine`, delete the `.mp3` in `output/demo`, and run `uv run podcast.py demo` again. It reuses the script, so you don't pay twice.

### Install Kokoro (optional)

[Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) isn't part of this project. These two commands give it a folder of its own, apart from everything else. They've been tested on an Apple silicon Mac only:

```bash
uv venv --python 3.12 voices/kokoro/.venv
```

```bash
uv pip install --python voices/kokoro/.venv/bin/python --require-hashes -r voices/kokoro/requirements.txt
```

On a Mac, the second command installs 91 packages (about 240 MB to download, 780 MB once unpacked), mostly for running AI models. The first recording also downloads Kokoro's voice, about 330 MB, and shows nothing while it does, so give it a few minutes. Voice packages print warnings while they install; they're harmless.

Keep the project in a folder with a fairly short path. Part of Kokoro can't read paths longer than 159 characters, and the program tells you if yours is.

Kokoro's default here is `am_echo`. To use another, put its name in `voice`. The [list is here](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md).

**About trust.** Ninety-one packages is a lot of other people's code. The list pins each one to an exact version and checks its fingerprint (a hash), so you get the same files I listed. The voice runs as a separate program that is handed only the script. Even so, any program running under your account could open the `.env` file, so install only what you're comfortable with.

## Use your own newsletters

### 1. Put them in one folder

In Gmail, search for a sender you want, click the sliders icon in the search box, then **Create filter**. Tick **Apply the label** and choose or make a label called `Newsletters` (plain English letters only). Tick **Also apply filter to matching conversations**, or only future mail gets the label. Leave **Delete it** unticked. (If your filter already deletes newsletters on arrival, set `include_trash = true` in `config.toml`. Gmail keeps the label on them, but a program reading the label won't see them without it.) Repeat for each sender, or put several in one filter with `OR` between them. Then open the gear icon, then **See all settings > Labels**, and check that **Show in IMAP** is ticked for that label. (IMAP is the standard way programs read mail.) Other mail services that support IMAP with a password should work too.

### 2. Give the program a password

For Gmail, this is an app password: a 16-letter password made for one program. Your Google account needs 2-Step Verification on. Create one at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), and paste it in `.env` right after `IMAP_PASSWORD=`, without the spaces Google shows.

**Know what you're granting.** An app password can open your whole mailbox. This program opens only the folder you name, and opens it read-only, but the password itself isn't limited to that. If that bothers you, forward your newsletters to a separate mailbox and use that one. You can delete the app password at any time on the same page.

### 3. Edit config.toml

Under `[mail]`, set `user` to your email address and `folder` to your label, keeping the quotes. The other settings have notes beside them. Most people will want `minutes`, `listener` and `skip`. For example, `skip = ["webinar", "job alert"]` leaves out any email with those words in its sender or subject. If you get few newsletters, lower `minimum_issues`: with fewer than that in the window, the program stops.

### 4. Check the setup

```bash
uv run podcast.py check
```

This checks your install, your voice, your settings and the mailbox sign-in, says what to fix, and costs nothing. It doesn't test the Claude side, which the first run does. When it ends with `Ready.`, make an episode:

```bash
uv run podcast.py run
```

It covers the last 24 hours and lands in the `output` folder. Running it again the same day does nothing unless you add `--force`, which makes a new script and costs again. So to cover three days when today's episode already exists:

```bash
uv run podcast.py run --hours 72 --force
```

If only the recording failed, running it again reuses the script. Episodes older than 14 days are deleted (`keep_days` in `config.toml`).

## Listen in a podcast app

The MP3s are ordinary files, so the simplest way to get them on your phone is to set `folder` under `[output]` to a folder that syncs to it, such as one in Dropbox. With an iCloud Drive folder, macOS may block the scheduled run; I haven't tried it.

If you'd rather use a podcast app, this command offers your episodes as a feed. It prints a `Feed:` address and keeps running, so leave the window open and press Control-C to stop. Add `--demo` to serve the demo episode:

```bash
uv run podcast.py serve
```

As it comes, only the same computer can reach it. To reach it from a phone on your home Wi-Fi, change two lines under `[feed]` in `config.toml`: set `host` to `"0.0.0.0"`, and put your computer's network name or address in `base_url`, such as `"http://my-mac.local:8765"`. The name is in **System Settings > General > Sharing**. Click **Allow** if macOS asks about incoming connections. Then add the printed feed address to an app that accepts a feed URL.

The address contains a long random word, and anyone who has it can listen. The connection isn't encrypted, so keep it on a network you trust and don't open it to the internet.

**Please don't publish the feed.** The episodes are built from other people's writing, much of it paid for.

## Run it every morning (Mac)

This writes a schedule file for 5:00 AM. Nothing runs yet:

```bash
uv run podcast.py schedule 05:00
```

Copy and run the `launchctl bootstrap` command it prints to start it. If the Mac is asleep at that time, the episode gets made when it wakes up. The Mac has to be on, and you have to be logged in. If a run fails, you should get a Mac notification, and the details are in `~/Library/Logs/newsletter-podcast.log`. If the log shows permission errors, move the project out of Documents or Desktop.

To stop the schedule, copy this exactly (`com.example.newsletter-podcast` is its real name):

```bash
launchctl bootout gui/$(id -u)/com.example.newsletter-podcast && rm ~/Library/LaunchAgents/com.example.newsletter-podcast.plist
```

If you move the project folder, stop the schedule and make it again.

## What it costs

Recording is free with either voice, because it happens on your computer. Writing the script costs whatever Claude charges for the text it reads and writes. At Claude Opus 5.5's list price in November 2026 ($4 per million tokens read, $20 per million written), the demo works out to about $0.22. A real day with 48 newsletters (146,419 tokens read, 11,565 written) works out to about $0.82. Sonnet 5.5 is about half that: set `model = "claude-sonnet-5-5"`. These are calculations from token counts, so check your own bill.

Your newsletters' text is sent to Anthropic. Your passwords aren't.

## How it stays safe

Newsletters are text from strangers, and some emails contain hidden instructions meant for AI. Here's what stands in the way:

- The mailbox is opened read-only, and the mail server's certificate is checked.
- Your own computer fetches the mail. Claude never touches the mailbox.
- Claude gets no tools. With Claude Code, every tool is switched off and it runs from an empty folder without your passwords.
- A newsletter can't close its own wrapper and pose as instructions.
- A newsletter can't pull in a file from your computer. Claude Code reads a file when it sees `@` and a path, so that feature is turned off and every `@` is swapped for a look-alike. I tested each guard alone.
- Everything the program writes is readable by your account only, and very large or malformed emails can't stall it or break the feed.
- If Claude refuses, stops early or writes almost nothing, no episode is made.
- The voice is handed the script and no passwords.

What's left is that a hostile newsletter could still try to change the words you hear. In one test with hidden instructions added to a newsletter, the script ignored them and warned the listener. One test isn't a guarantee, so treat an episode like the newsletters it came from: check anything that matters.

## What's been tested

| Piece | Tested? |
|---|---|
| Demo script, with Claude Code on an Apple silicon Mac | Yes, with Opus 5.5. Both buried corrections were in the script |
| Mac voice and Kokoro | Yes, on that script. Kokoro ran from a fresh install |
| Installing Kokoro from scratch | Yes, in a new folder on one Mac that already had the 330 MB voice file |
| Mail reading | Yes, on one real Gmail account: 48 newsletters in one run. About 45 specific claims in that episode were looked up, and all were in the newsletters |
| Anthropic API | Only with a stand-in. Not yet with a real key |
| Feed | Address, skipping ahead and file format, with command-line tools. Not yet in a podcast app |
| Daily schedule | The file is valid. Not yet left running |
| Linux | No |

To run the automatic tests, which end with `OK` and cost nothing:

```bash
uv run -m unittest discover tests
```

## Files

| File | What it does |
|---|---|
| `podcast.py` | The commands |
| `prompt.md` | Claude's instructions for the show. Edit this to change how it sounds |
| `newsletter_podcast/mail.py` | Reads the mailbox folder and turns emails into text |
| `newsletter_podcast/writer.py` | Sends the text to Claude and checks what comes back |
| `newsletter_podcast/speak.py` | Runs the voice you picked and makes the MP3 |
| `voices/kokoro/` | The small program that runs Kokoro, and its package list |
| `newsletter_podcast/feed.py` | Keeps the episode list, builds the feed, serves it, deletes old episodes |
| `newsletter_podcast/settings.py` | Reads `config.toml` and `.env` |
| `demo/` | The made-up newsletters |
| `output/` | Your episodes, made on the first run. Git ignores it |

## License

MIT. Kokoro and its packages aren't included and have their own licenses.
