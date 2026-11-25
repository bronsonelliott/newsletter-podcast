# Newsletter podcast

Turn the newsletters piling up in your inbox into one private podcast episode a day.

It reads one mailbox folder, gives Claude every newsletter in it, and asks for a script: the stories most of them cover, then the smaller ones worth knowing. Your own computer reads the script aloud. When several newsletters cover the same story, you hear it once. When one of them corrects the others, Claude is told to use the correction. It won't mention everything: 48 newsletters don't fit in 15 minutes.

- **Your newsletters, your show.** You choose the folder, the length, the topics that always get a section, and the voice. Two voices work out of the box or with one extra install, and you can also take the script as text and use your own. The show's instructions are in `prompt.md`, in plain English, for you to edit.
- **No newsletter is cut short.** Claude gets the full text of each one, minus links and footer lines. If there's too much, the program stops and tells you. Anything it doesn't send (your skip list, second copies, empty emails, emails over 10 MB) is listed when you run it.
- **Private, with one exception.** Episodes stay on your computer, and nothing is published. But Claude writes the script, so your newsletters' text goes to Anthropic. Your passwords don't.
- **Claude can't do anything but write.** It gets text, with no tools, files, web access or passwords.

**Hear one first:** [`sample/episode-kokoro.mp3`](sample/episode-kokoro.mp3) is a real episode from November 24, 2026 (about 15 minutes), made from 48 newsletters in my inbox and read by Kokoro, the optional voice. On GitHub, click the download button on that page. [Compare the two voices](#compare-the-two-voices) shows how to hear the other one, and [About the sample episode](#about-the-sample-episode) says what I checked.

## Why I made it

I subscribe to more AI newsletters than I can possibly read, and a lot of them cover the same top stories. This was a way to stay on top of the latest AI news in an easy to digest way. I listen to mine each morning on my walk.

My personal version has been running since April 2026, and [I wrote about building it](https://bronsonelliott.substack.com/p/i-built-a-daily-ai-podcast-that-runs). Parts of that article are out of date. Mine now uses Kokoro for the voice instead of Qwen3-TTS, runs from a script instead of Claude Cowork, and makes episodes of about 26 to 30 minutes instead of 8 to 10.

This repo is a new, simpler build of the same idea, so it isn't the code I run every day. See [What's been tested](#whats-been-tested) before you rely on it.

## Try it first, without your email

The repo comes with 12 made-up newsletters in `demo/`. Two of them bury a correction to a story the others got wrong: `newsletter-08.txt` limits a price cut, and `newsletter-11.txt` limits a launch. Listen for both. Every company and person in them is invented.

The demo calls Claude, so it costs about $0.22 with an API key, or counts against your Claude plan. See [What it costs](#what-it-costs).

### 1. Install

You need a Mac. (Linux may work, but it's untested and has no built-in voice.) You also need [Homebrew](https://brew.sh), which installs programs from Terminal. If `brew --version` prints a number, you have it. If not, follow the steps on that page first.

This installs two programs: `uv`, which runs Python, and `ffmpeg`, which makes the MP3.

```bash
brew install uv ffmpeg
```

Download the project and go into its folder. (If macOS offers to install its command line developer tools, accept, wait for it to finish, then run the `git clone` command again.)

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

Then pick one way to reach Claude.

**Option A: Claude Code.** This is the way I tested. Claude Code is a separate program from the Claude chat app. If this prints a number, you have it:

```bash
claude --version
```

You also have to be signed in to it. If you don't have it, [install it](https://code.claude.com/docs/en/setup) or use option B. It counts against your plan's limits. I tested with version 2.1.332. If a run stops with `unknown option`, run `claude update`.

This opens the settings file in TextEdit. Change `backend = "api"` to `backend = "claude-code"`, keeping the quotes, then save and close:

```bash
open -e config.toml
```

If you type any new quotes, first turn off **Edit > Substitutions > Smart Quotes**, because curly quotes break the settings file.

**Option B: an Anthropic API key.** You pay for what you use. I haven't tested this way with a real key. Get one at [console.anthropic.com](https://console.anthropic.com/settings/keys). This opens the file it goes in (`.env` is hidden, so you won't see it in Finder). Paste the key right after `ANTHROPIC_API_KEY=`, with no spaces or quotes, then save and close:

```bash
open -e .env
```

This way needs one more install, the `anthropic` package and about 15 small ones it needs:

```bash
uv pip install -r requirements.txt
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

To see the files, run this. It opens the folder in Finder. Double-click the `.mp3` to play the episode. The `.txt` is its script:

```bash
open output/demo
```

## Pick a voice

The voice is set by `engine`, under `[audio]` in `config.toml`:

| Engine | What you get | What it needs |
|---|---|---|
| `"mac"` | The voice your Mac is set to. This is the default, so you can try things right away. Apple's macOS license limits it to personal, non-commercial use | Nothing more |
| `"kokoro"` | A free voice model that runs on your computer and sounds more natural. **This is the one I'd use for a daily show** | The install below |
| `"none"` | The script as text, for any text-to-speech tool you like | Nothing more |

### Compare the two voices

Both of these read the same script, `sample/script.txt`, which Claude wrote from a real day of newsletters. Neither one calls Claude or costs anything, and neither needs Kokoro installed. Run them in the project folder, so do the `git clone` and `cd` steps in [Install](#1-install) first.

**Kokoro** (voice `am_echo`, normal speed). This opens the sample recording:

```bash
open sample/episode-kokoro.mp3
```

**Your Mac's voice**, at the speed this program uses. It starts talking right away. Press Control-C to stop:

```bash
say -r 175 -f sample/script.txt
```

There's no Mac recording in this repo because Apple's macOS license doesn't allow recordings of its voices to be shared publicly. Running the command is also the fairer test, because it uses the voice your own Mac is set to, which may not be the same as mine. The one difference from a real episode is that the program also evens out the loudness.

### About the sample episode

It's one real day, unedited. It is an AI summary of what newsletters said, and it isn't a fact-checked news report. I looked up about 45 of its claims in the newsletters themselves, and all were there. I then checked six of its most serious stories against news coverage. Two have a problem that came from a newsletter:

- **Anthropic co-founders' share sales.** One newsletter said each of the seven sold $2 billion. [News coverage](https://247wallst.com/investing/2026/11/24/dario-and-daniela-amodei-each-sold-280-million-of-anthropic-stock-in-the-ipo/) puts it at about $280 million each, or about $2 billion for all seven. The episode gives both figures and tells you to treat them carefully.
- **OpenRouter and Together AI.** The episode says OpenRouter dropped Together AI, as a newsletter did. [Together AI says it wasn't removed](https://www.bleepingcomputer.com/news/security/openrouter-drops-ai-providers-over-leaked-prompts-and-secrets/). The episode also credits OpenRouter with the finding, which came from security firm Dragos.

The people named in legal cases are accused, not convicted.

Thank you to the newsletters it names: AI Daily Brief, AI Secret, AI Valley, AlphaSignal, The AI Report, The Deep View, Intelligence by Intent, Latent Space, Model Radar, The Neuron, The Rundown, Techpresso, TLDR, TLDR AI and World of AI. They did the reporting and the thinking, so go read them. If you write one of them and want this sample taken down, open an issue and I'll remove it.

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

**Switch to it.** Open the settings, set `engine = "kokoro"` under `[audio]`, then save and close:

```bash
open -e config.toml
```

Then check it. This costs nothing:

```bash
uv run podcast.py check
```

Look for `OK   voice: kokoro`. If you haven't set up your mailbox yet, the mail line says `FIX`, and that's expected. The check doesn't download the voice file. Your first recording does.

Kokoro's default here is `am_echo`. To use another, put its name in `voice`, also under `[audio]`. The [list is here](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md).

**About trust.** Ninety-one packages is a lot of other people's code. The list pins each one to an exact version and checks its fingerprint (a hash), so you get the same files I listed. The voice runs as a separate program that is handed only the script. Even so, any program running under your account could open the `.env` file, so install only what you're comfortable with.

**The voice file isn't checked.** The fingerprints cover the packages, not Kokoro's voice file, which comes from the Kokoro account on Hugging Face, a site that hosts AI models. In November 2026, [researchers took over that account](https://www.bleepingcomputer.com/news/security/researchers-hijack-hugging-face-account-for-popular-kokoro-ai-model/) to show it could be done. They say they never uploaded a changed file. A changed file could make the voice say something other than the script.

### Change the demo's voice

To hear today's demo in a different voice, change `engine` as above. Then run `open output/demo`, drag the `.mp3` to the Trash, and make the demo again. It reuses the script if you do it the same day, so you don't pay twice:

```bash
uv run podcast.py demo
```

## Use your own newsletters

### 1. Put them in one folder

**Tip: let a label do the sorting.** Make one Gmail label just for newsletters, and have Gmail add it as they arrive. The program looks only at mail with that label, so you never have to list your newsletters here. When you subscribe to a new one, add its sender to the filter, and that's all you have to change.

For Gmail:

1. Search for a sender you want, click the sliders icon in the search box, then **Create filter**.
2. Tick **Apply the label** and choose or make a label called `Newsletters` (plain English letters only).
3. Tick **Also apply filter to matching conversations**, or only future mail gets the label.
4. Leave **Delete it** unticked, then save the filter.
5. Repeat for each sender, or put several in one filter with `OR` between them.
6. Open the gear icon, then **See all settings > Labels**, and check that **Show in IMAP** is ticked for that label. (IMAP is the standard way programs read mail.)

If your filter already deletes newsletters on arrival, you can keep it that way and set `include_trash = true` in step 3 below. Gmail keeps the label on them, but a program reading the label won't see them without that setting.

**Not on Gmail?** Look for a rule or filter that moves newsletters into a folder of their own, and use that folder's name for `folder` in step 3. The program reads folders. A Gmail label counts as one, but in some other mail services a tag or category doesn't, and the program can't see it. You also need to set `host` to your mail service's IMAP server. Services that support IMAP with a password should work, but I've only tested Gmail. Outlook.com won't, because Microsoft [ended that kind of sign-in](https://support.microsoft.com/en-us/topic/c5d65390-9676-4763-b41f-d7986499a90d) in September 2024.

### 2. Give the program a password

For Gmail, this is an app password: a 16-letter password made for one program.

**Know what you're granting first.** An app password can open your whole mailbox. This program opens only the folder you name (and Trash, if you turn that on), and opens it read-only, but the password itself isn't limited to that. If that bothers you, forward your newsletters to a separate mailbox and use that one. You can delete the app password at any time on the page where you make it.

Your Google account needs 2-Step Verification on. Create the password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). Then open the file it goes in, paste it right after `IMAP_PASSWORD=` without the spaces Google shows, and save:

```bash
open -e .env
```

### 3. Edit config.toml

```bash
open -e config.toml
```

Under `[mail]`, set `user` to your email address and `folder` to your label, spelled exactly as it is in Gmail. Keep the quotes. The other settings have notes beside them. Most people will want `minutes`, `listener` and `skip`. For example, `skip = ["webinar", "job alert"]` leaves out any email with those words in its sender or subject. If you get few newsletters, lower `minimum_issues`: with fewer than that in the window, the program stops.

### 4. Check the setup

```bash
uv run podcast.py check
```

This checks your install, your voice, your settings and the mailbox sign-in, says what to fix, and costs nothing. It doesn't test the Claude side, which the first run does. When it ends with `Ready.`, you can make an episode.

**Before you do:** this sends your newsletters' text to Anthropic. A day with 48 newsletters works out to about $0.82 with an API key, or about $25 a month if you run it daily. With Claude Code it counts against your plan instead.

```bash
uv run podcast.py run
```

It covers the last 24 hours. To see the episode:

```bash
open output
```

Running it again the same day does nothing unless you add `--force`, which makes a new script and costs again. So to cover three days when today's episode already exists:

```bash
uv run podcast.py run --hours 72 --force
```

If only the recording failed, running it again reuses the script. Episodes older than 14 days are deleted (`keep_days` in `config.toml`). That means files in the output folder named `episode-` plus a date, ending in `.mp3`, `.txt` or `.json`. Nothing else is deleted.

## Listen in a podcast app

The MP3s are ordinary files, so the simplest way to get them on your phone is to set `folder` under `[output]` to a folder that syncs to it, such as one in Dropbox. With an iCloud Drive folder, macOS may block the scheduled run; I haven't tried it.

If you'd rather use a podcast app, this command offers your episodes as a feed. It prints a `Feed:` address and works only while this command is running, so leave the window open and press Control-C to stop. The daily schedule below doesn't start it. Add `--demo` to serve the demo episode:

```bash
uv run podcast.py serve
```

As it comes, only the same computer can reach it. To reach it from a phone on your home Wi-Fi, change two lines under `[feed]` in `config.toml`: set `host` to `"0.0.0.0"`, and put your computer's network name or address in `base_url`, such as `"http://my-mac.local:8765"`. This prints the name. Add `.local` to the end of it:

```bash
scutil --get LocalHostName
```

Click **Allow** if macOS asks about incoming connections. Start `serve` again, then add the printed feed address to an app that accepts a feed URL. Away from home your phone can't reach it, so download the episode before you leave.

The address contains a long random word, and anyone who has it can listen. The connection isn't encrypted, so keep it on a network you trust and don't open it to the internet.

**Please don't publish the feed.** The episodes are built from other people's writing, much of it paid for. (The sample here is one day, shared to show how the voices sound.)

## Run it every morning (Mac)

Do this only after `uv run podcast.py run` has worked once by hand. I've checked that the schedule file is valid, but I haven't left it running.

This writes a schedule file for 5:00 AM. Nothing runs yet:

```bash
uv run podcast.py schedule 05:00
```

Copy and run the `launchctl bootstrap` command it prints to start it. It prints nothing when it works. To confirm, run this, which shows one line if the schedule is on:

```bash
launchctl list | grep newsletter-podcast
```

To test it without waiting for morning, this starts it now. If today's episode already exists, it does nothing and costs nothing. If not, it makes one and costs the same as `run`:

```bash
launchctl kickstart gui/$(id -u)/com.example.newsletter-podcast
```

Then look at what it did:

```bash
cat ~/Library/Logs/newsletter-podcast.log
```

The Mac has to be on, and you have to be logged in. If it's asleep at 5:00, the episode gets made when it wakes up. If a run fails, you should get a Mac notification, and the details are in that log. If the log shows permission errors, move the project out of Documents or Desktop.

**A late run can miss newsletters.** Each episode covers the 24 hours before it starts. If yesterday's ran at 5:00 and today's runs at 8:00, anything that arrived between 5:00 and 8:00 yesterday is in neither. Raising `hours` under `[mail]` closes the gap, but you may hear some stories twice.

To stop the schedule, copy this exactly (`com.example.newsletter-podcast` is its real name):

```bash
launchctl bootout gui/$(id -u)/com.example.newsletter-podcast && rm ~/Library/LaunchAgents/com.example.newsletter-podcast.plist
```

To change the time, or if you move the project folder, stop the schedule and make it again.

## What it costs

Recording is free with either voice, because it happens on your computer. Writing the script costs whatever Claude charges for the text it reads and writes. At Claude Opus 5.5's list price in November 2026 ($4 per million tokens read, $20 per million written), the demo works out to about $0.22. A real day with 48 newsletters (146,419 tokens read, 11,565 written) works out to about $0.82. Sonnet 5.5 is about half that: set `model = "claude-sonnet-5-5"`. These are calculations from token counts, so check your own bill.

## How it stays safe

Newsletters are text from strangers, and some emails contain hidden instructions meant for AI. Here's what stands in the way:

- The mailbox is opened read-only, and the mail server's certificate is checked.
- Your own computer fetches the mail. Claude never touches the mailbox.
- Claude gets no tools. With Claude Code, every tool is switched off and it runs from an empty folder without your passwords.
- A newsletter can't close its own wrapper and pose as instructions.
- A newsletter can't pull in a file from your computer. Claude Code reads a file when it sees `@` and a path, so that feature is turned off and every `@` is swapped for a look-alike. I tested each guard alone.
- Everything the program writes is readable by your account only, and very large or malformed emails can't stall it or break the feed.
- If Claude refuses, stops early or writes almost nothing, no episode is made. A safety filter stopped my personal version on two days heavy with hacking or biology stories. With an API key, the program asks Anthropic to retry on another Claude model. With Claude Code it doesn't. Setting `model = "claude-sonnet-5-5"` and running it again may get through.
- The voice is handed the script and no passwords.

What's left is that a hostile newsletter could still try to change the words you hear. In one test with hidden instructions added to a newsletter, the script ignored them and warned the listener. One test isn't a guarantee, so treat an episode like the newsletters it came from: check anything that matters.

## What's been tested

| Piece | Tested? |
|---|---|
| Demo script, with Claude Code on an Apple silicon Mac | Yes, with Opus 5.5. Both buried corrections were in the script |
| Mac voice and Kokoro | Yes, on that script. Kokoro ran from a fresh install. In 11 Mac voice recordings on one day, one finished but never exited. The program now stops a stuck Mac voice after 10 minutes and tries once more |
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
| `config.example.toml`, `.env.example` | The settings files you copy in step 2 |
| `requirements.txt` | The one package the API key way needs |
| `tests/` | The automatic tests |
| `demo/` | The made-up newsletters |
| `sample/` | One real episode, read by Kokoro, and its script |
| `output/` | Your episodes, made on the first run. Git ignores it |

## License

MIT. Kokoro and its packages aren't included and have their own licenses. (Kokoro's is Apache 2.0.) The sample recording was made with it. The sample script and recording summarize other people's newsletters and aren't covered by the MIT license. Your Mac's voice is covered by Apple's macOS license.
