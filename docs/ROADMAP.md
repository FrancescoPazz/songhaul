# Roadmap: from YouTube to several platforms

Status: **phases 0A, 0B, 1 and 4 done** (26 November 2026). Phases 2 and 3 (Spotify) are [on hold](#decisions).

Goal: start from a link to a song or a playlist on YouTube, SoundCloud or Spotify and get audio files with consistent
names, tags and covers. It applies to the CLI, the desktop app and the Android app.

Out of scope: getting around DRM, previews or subscriptions. A protected track is skipped with an explanation or, for
Spotify, searched on a supported source.

> [`../ROADMAP.md`](../ROADMAP.md) is the previous roadmap (script → app), finished except for the checks on a real
> phone. This one comes next.

| Phase | Result | Version |
|---|---|---|
| [0A. Rename](#phase-0a--rename) ✅ | New name everywhere, existing updates and history safe | 0.6.0 |
| [0B. Common interface](#phase-0b--common-interface) ✅ | Separate sources, YouTube exactly as before | with 0.7.0 |
| [1. SoundCloud](#phase-1--soundcloud) ✅ | Tracks and sets, with titles; previews and DRM recognised | 0.7.0 |
| [2. Spotify, tracks](#phase-2--spotify-single-tracks) ⏸ | A Spotify link becomes the right song, or an honest "not found" | 0.8.0 |
| [3. Spotify, playlists](#phase-3--spotify-playlists) ⏸ | Playlists and albums, with a review of doubtful matches | 0.9.0 |
| [4. Polish](#phase-4--polish) ✅ | Unified tags, clear errors, documentation | 1.0.0 |

---

## 1. The project at 0.5.0

Paths, names and line numbers in this section and in [section 4](#4-rename) are those of commit `211bc5f` (0.5.0),
before the rename: `ytmpd/` is now `songhaul/`.

### Technology

| What | Detail |
|---|---|
| Language | Python ≥ 3.10, plus a little Dart in the Android extension |
| Download | `yt-dlp[default]>=2026.10.26`, used as a library. Brings `yt-dlp-ejs`, `mutagen`, `requests`, `certifi` |
| Conversion | FFmpeg for MP3 only; on the desktop it comes from `imageio-ffmpeg`. Not on Android: M4A only |
| Interface | `argparse` CLI (`cli.py`), Flet 1.1.2 desktop and Android app (`gui.py`) |
| Releases | `release.yml` on `v*` tags (Windows, macOS, Linux, signed APK); `yt-dlp-update.yml` every Monday |

### How a link is handled

1. `core.normalize_url()` (core.py:47): four YouTube hosts only. `list=` → playlist link, `v=` → video link, an endless
   mix (`RD…`) → the song. Any other link goes through unchanged.
2. `core.is_playlist_url()` (core.py:62): looks for `list=` in the text. Only used to show **Sync** in the history.
3. `core.list_playlist()` (core.py:321): yt-dlp with `extract_flat`; it's a playlist if the result has `entries`.
4. `core.download()` (core.py:345): hands yt-dlp the **whole** link; yt-dlp expands the playlist, numbers, filters
   (`playlist_items`) and skips archived tracks. A second pass retries the 403s.

The engine is already mostly generic. The ties to YouTube are at the edges:

| Where | Tie |
|---|---|
| core.py:22-24, 403-413 | JavaScript runtimes and the second pass after a 403 (harmless elsewhere) |
| core.py:42-63 | `is_mix`, `normalize_url`, `is_playlist_url` |
| core.py:86-92 | `archived_ids()` drops the platform name and keeps only the id |
| core.py:96-107 | Error reasons made of YouTube's phrases; DRM is missing |
| core.py:116-119 | `video_id_in()`: regex `[youtube] <11 characters>` |
| core.py:163-165 | M4A = `bestaudio[ext=m4a]`, meant for YouTube's AAC |
| core.py:171-206 | Clean titles and the 16:9 thumbnail crop |
| core.py:225-232 | Priority given to YouTube Music's tags |
| gui.py:72-80 | `link_in_text` and `link_from_route`: YouTube only; Flet's route loses the host |
| gui.py:168, 460, 552 | "YouTube" as the fallback playlist name |
| gui.py:374-377 | Clipboard links recognised only if YouTube |
| gui.py:703 | `cookies.txt` accepted only if it contains `youtube.com` |
| cli.py:35, 47, 71 | Description, help and the note on cookies |
| `i18n.py` | Texts with "YouTube"/"video" on 13 Italian lines (11, 15, 37-40, 42, 44, 45, 58, 60, 63, 68) and 12 English ones (105, 109, 131-134, 138, 139, 152, 154, 157, 162) |
| `pyproject.toml` | Description, Android intent filters for `youtube.com` |
| README, README.it | All the text, the badges, the questions |

### Tests

One file, `tests/test_core.py`: 26 `unittest` tests, no network, all green (0.8 s). They cover links, options, tags,
error reasons, archive, the 403 retry (with a fake `YoutubeDL`), clean titles, covers, versions, translations. They
don't cover the GUI, the CLI or the network. CI runs them only on tags and in the weekly update, not on every push.

### Defects already there, found while reading

Phase 0 doesn't change behaviour, so these aren't part of it; each one belongs to a phase.

| Defect | Phase |
|---|---|
| `youtu.be` isn't normalised: `youtu.be/<id>?list=RD…` stays an endless mix | 4 |
| `archived_ids()` mixes up ids of different platforms | 1 |
| `Covers`: with equal `preference` it tries the **smallest** thumbnails first (if the SoundCloud original is a PNG, the file gets a 16×16 one) | 1 |
| README, "Where to change things": the cover row mentions `writethumbnail`, no longer used | 4 |
| An empty playlist is listed as one track without a title: the playlist itself | 1 |
| "This video is unavailable" is explained as an unexpected error: only "Video unavailable" is recognised | 4 |

---

## 2. What the platforms allow

Documentation read and tests run on 25 November 2026 with yt-dlp 2026.10.26.

### SoundCloud

**yt-dlp supports it directly**: tracks, sets, private links with a token (`/s-…`), users, likes. With the current code
downloading a track **already works** from the CLI (tried with a CC-BY track, as MP3 and M4A). Several things are
missing:

| Aspect | What happens | Evidence |
|---|---|---|
| **Titles in a set** | The fast listing gives only ids and links: **title and duration are empty**, the GUI would show ids | Set "The Royal Concept EP": 6 rows of `None` |
| **Solution** | One bulk request to `api-v2/tracks?ids=…` gives title, duration, `full_duration`, `policy` and protocols | 7 tracks in 0.5 s |
| **DRM** | Many monetised tracks have only encrypted streams (`ctr-`/`cbc-encrypted-hls`): yt-dlp refuses them. Here they show as "Unexpected error" | **3 of 6** in the test set |
| **Go+ / 30 s preview** | `policy: SNIP`. As MP3, today **30 seconds would be downloaded as if they were the song**, and archived. As M4A the error says "Video removed" | "Makeba": 30 s of 249 |
| **Private tracks** | Only with the secret link or signed in (`oauth_token` cookie) | From yt-dlp's code, not tried |
| **Go+ with a subscription** | yt-dlp accepts the `oauth_token` cookie from the browser or `cookies.txt`; DRM stays out | From the code, not tried |
| **Quality** | AAC at 96 or 160 kbps (HLS). A 320 kbps MP3 adds nothing | Formats listed |
| **M4A without FFmpeg (Android)** | The file is created with tags and cover, but it's a fragmented MP4 with an index per segment: Android reads only the first, **10 s of 151**. Solved by joining the indexes (`mp4.py`) | Measured on the emulator |
| **Short links** `on.soundcloud.com` | They go through the generic extractor, which follows the redirect. They can also hide a profile, whose tracks would all be listed: they're resolved first | Tried with public links |

The official API isn't used: its [terms](https://developers.soundcloud.com/docs/api/terms-of-use) forbid saving
features and "stream ripping". yt-dlp uses the site's API. The terms of use still apply to the user: the README has to
say so, as it does for YouTube.

### Spotify

yt-dlp **refuses** `open.spotify.com` because it's DRM-protected, and rightly so. What's needed is the metadata, then a
search elsewhere.

#### State of the Web API

| Point | Current rule | Source |
|---|---|---|
| Premium | The owner of a development-mode app must have Premium; if it lapses, the app stops working | [Quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes), [Feb 2026 guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide) |
| Users | At most 5, on an allowlist; others get 403 | Quota modes |
| Client IDs | Up to 25 per developer since July 2026 (it was 1), but the quota is **per account** | [July 2026](https://developer.spotify.com/documentation/web-api/references/changes/july-2026) |
| Extended quota | Only organisations with at least 250,000 monthly active users: **out of reach** for this project | Quota modes |
| Limits | 30 s rolling window and a separate quota; values not published; 429 with `Retry-After` or `QUOTA_EXCEEDED` | [Rate limits](https://developer.spotify.com/documentation/web-api/concepts/rate-limits) |
| Tracks and albums | `GET /tracks/{id}` and `/albums/{id}` remain, one at a time (bulk requests were removed). ISRC still there | [Feb](https://developer.spotify.com/documentation/web-api/references/changes/february-2026) and [Mar 2026](https://developer.spotify.com/documentation/web-api/references/changes/march-2026) |
| **Public playlists** | **`GET /playlists/{id}/items` works only for owned or collaborative playlists, otherwise 403.** For the others only title and cover are available | [Reference](https://developer.spotify.com/documentation/web-api/reference/get-playlists-items) |
| Access | Client credentials for non-personal data; playlists need the user's sign-in. Redirect to `http://127.0.0.1:PORT` (not `localhost`). The refresh token lasts **6 months** and isn't renewed | [Client credentials](https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow), [refresh](https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens) |

Two consequences:

- The project **can't ship its own Client ID**: 5 users, and the terms forbid handing codes over. Each user creates
  their own Spotify app, with Premium.
- "Paste the link of any public playlist" is **no longer possible with the official API**. Someone with Spotify can
  still copy the songs into a playlist of their own and use that link.

#### What the terms say

To be decided knowingly (D2). This isn't legal advice. The [developer terms](https://developer.spotify.com/terms) and
[policy](https://developer.spotify.com/policy) (15 May 2025) forbid among other things: helping stream ripping and
permanent copies of Spotify content (IV.2.2.3), collecting data with automated tools, **playlists included**
(IV.2.4.1), keeping metadata and covers indefinitely (IV.3.1.1), creating products integrated with another service's
content (policy III.5), names starting with "Spot" (policy VI.2).

Spotify's audio is never touched here, but matching with YouTube is in tension with these clauses even through the
official API: Spotify could revoke a user's app. To lower the risk, Spotify can be used **only to search**, writing the
tags and cover of the song found into the files (D3).

#### Where to read the metadata

| Route | Pros | Cons |
|---|---|---|
| **A. Web API with the user's credentials** (recommended) | Documented, full data (album, duration, ISRC), no 100-track limit | Premium and an app to create; own playlists only; sign-in every 6 months |
| **B. Public `/embed` page** | No credentials; tried: title, artists, duration | Undocumented; no album or ISRC; the test playlist stopped at 100 tracks; against IV.2.4.1; can break without notice |
| **C. `spotipyFree`** (used by spotDL) | Public playlists without credentials | Reverse-engineered internal APIs; one maintainer, about 50 versions in eight months; brings `pymongo` along |
| **D. [oEmbed](https://developer.spotify.com/documentation/embeds/reference/oembed)** | Official, no sign-in | Title and cover only: without artist and duration the match isn't reliable |

#### Library or direct integration

| Option | Outcome |
|---|---|
| **spotDL 4.6.0** as a library | **No.** Python ≥ 3.11, 21 dependencies, including a web server (FastAPI, uvicorn) and compiled packages (pydantic, rapidfuzz): unworkable in the APK. Since 4.5.0 (May 2026) it uses `spotipyFree` precisely because of Spotify's restrictions. Useful as a reference |
| **spotipy 2.26** | **No.** It brings `redis` for three HTTP calls |
| **Direct calls** with `requests`, already there | **Yes**: token, track, album, playlist items |
| **`ytmusicapi`** for the search | **Yes**: MIT, pure Python, depends only on `requests`, 1 MB. Returns title, artists, album, duration, type. Tried: 0.4–1.4 s per search. Searching YouTube Music with yt-dlp gives only id and title; `ytsearch` gives videos, not songs |

### Matching Spotify → audio

**Search**: `artists + title` among YouTube Music **songs**; if needed, the ISRC as a second search (in two tries with
known ISRCs the first result was right, the others weren't: it always has to be confirmed). Official videos last, never
automatically.

**Comparison**, with the standard library only (`difflib`, `unicodedata`):

1. Normalised title: case, accents, "feat.", "Remastered 2011", punctuation.
2. At least the main artist in common.
3. **The same version words** in both titles: live, remix, acoustic, sped up, slowed, instrumental, karaoke, cover,
   edit, demo, extended. "Mr. Brightside" can't become "Mr. Brightside (Live…)" or the other way round.
4. Difference in duration.

| Outcome | Condition (initial thresholds, to be tuned) | What happens |
|---|---|---|
| **Safe** | 1, 2 and 3 hold, difference ≤ 3 s | Downloaded |
| **Doubtful** | Difference 3–15 s, or the title is only similar, or only a video | **Not** downloaded by itself: the candidates are shown with duration and album, and the user picks |
| **Missing** | No candidate | Skipped, reason "No match" |

The user's choice is remembered (`matches.json` in the data folder: Spotify id → YouTube id), so **Sync** doesn't ask
again. The log says where each file comes from.

---

## 3. Architecture

### Approaches considered

| Approach | Pros | Cons |
|---|---|---|
| **1. Sources that produce "jobs" for yt-dlp** (recommended) | YouTube and SoundCloud: one job, the whole link, as today. Spotify: one job per track. YouTube's path doesn't change | Two job granularities |
| 2. Everything track by track | One model | Rewrites numbering, archive, `--items`, retries: high risk for YouTube |
| 3. A yt-dlp plugin/extractor for Spotify | Little code in the engine | Depends on yt-dlp's internals; no place for choosing between doubtful matches |

### Structure

```text
songhaul/
├── core.py            engine: yt-dlp options, events, cancel, tags, covers
├── paths.py           app name, data and music folders                     [phase 0A]
├── matching.py        comparing a track with candidates (pure functions)   [phase 2]
└── sources/
    ├── __init__.py    SOURCES, source_for(url), link_in(text)              [phase 0B]
    ├── base.py        Source: the answers that fit any yt-dlp link         [phase 0B]
    ├── youtube.py     is_mix, normalize, playlist                          [phase 0B]
    ├── soundcloud.py  links, bulk titles, previews and DRM                 [phase 1]
    └── spotify.py     metadata, search, resolution                         [phases 2-3]
```

| `Source` method | Job |
|---|---|
| `matches(url)` | Recognises its own links. `source_for(url)` tries the sources in order; an unknown link goes to yt-dlp, as today |
| `normalize(url)` | Canonical form (drops `si=`, `intl-it`, resolves short links) |
| `is_playlist(url)` | For Sync, instead of looking for `list=` |
| `list(url)` | Title and tracks: `index`, `id`, `title`, `duration`, `thumbnail`, plus `artists`, `album`, `problem` (e.g. `drm`, `preview`) |
| `jobs(url, tracks)` | What to download: links for yt-dlp, position, tags to impose. Spotify resolves here, one track at a time |

Phase 0B has the first three, plus `reasons` and `track_id_in(message)` for errors. `list` comes with SoundCloud and
`jobs` with Spotify, the first platforms that need something different from yt-dlp's own.

`core.list_playlist()` and `core.download()` keep their signature and events: the CLI and the GUI don't notice.

### Recognising links

| Platform | Hosts | Forms |
|---|---|---|
| YouTube | `youtube.com`, `www.`, `m.`, `music.`, `youtu.be` | as today |
| SoundCloud | `soundcloud.com`, `www.`, `m.`, `on.soundcloud.com` | `/<user>/<track>[/s-…]`, `/<user>/sets/<name>[/s-…]` |
| Spotify | `open.spotify.com`, `spotify.link` | `[/intl-xx]/track`, `/album`, `/playlist` + a 22-character id; also `spotify:track:…` |

Profiles, artists, podcasts and likes: "This kind of link isn't supported", not a generic error.

The host is compared exactly (`urlparse`), never with "contains": `soundcloud.com.example.it` must not pass.

On Android, **Share** and the clipboard carry the whole link. No new "Open with" intents: Flet's route loses the host,
and SoundCloud's `/artist/track` couldn't be told apart reliably.

### Metadata and file names

| Field | YouTube | SoundCloud | Spotify |
|---|---|---|---|
| Title, artist, album | As today | `publisher_metadata.artist`, otherwise the uploader; album = set title | From the song found on YouTube Music (D3) |
| Track no. | Position in the playlist | Position in the set | Position in the playlist |
| Cover | Square thumbnail | Artwork (1000 px at most, JPEG) | YouTube Music's cover (D3) |

Spotify's file name: `NNN - Artist - Title`. Its titles are short ("Intro"): without the artist two different songs
would have the same name and `nooverwrites` would drop the second one **silently**. YouTube and SoundCloud stay
`NNN - Title`, unless D6 changes that.

Archive: same format, `platform id` per line; the whole pair is compared. For Spotify it's `spotify <id>`, without
yt-dlp's archive: two Spotify tracks can lead to the same video. Existing archives stay valid.

### Errors

- A track that fails gives `track_skipped` and the run goes on: already so for yt-dlp, to be extended to search and
  resolution.
- Only what concerns the whole playlist stops everything: invalid link, wrong credentials, quota used up.
- New reasons: `drm`, `preview`, `no_match`, `match_doubtful`, `rate_limited`, `credentials`, `not_owned`,
  `unsupported_link`. The translation test already forces an explanation in Italian and English.
- 429: wait for `Retry-After` up to 30 s, beyond that stop and explain. Never retry forever.
- Errors without an id are attributed to the current track, on every platform.

### Credentials

| What | Where |
|---|---|
| Spotify Client ID, secret and tokens | `spotify.json` in the data folder, next to `cookies.txt` (`%APPDATA%\…\data`, `~/.songhaul`, the app's private space on Android), with permissions 600 where they exist |
| CLI | `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`, which win over the file. Never as an argument: it would stay in the shell history |
| Cookies | `cookies.txt` as today; it will also accept `soundcloud.com` |
| Repository | `spotify.json` and `.env` in `.gitignore`; no credentials in CI: tests use recorded data |
| Reports | "Report a problem" and the logs must never contain tokens or secrets: with a test |

---

## 4. Rename

### The name: Songhaul

"A haul of songs": short, says songs and collection, no platform. Checked on 25 November 2026: free on PyPI and npm, 0
GitHub repositories. Not checked: the Play Store systematically, trademarks.

| Others considered | Why not |
|---|---|
| **Mixhaul** | Free everywhere, but it stresses playlists over songs |
| **Trackdock** | Free; SessionDock and Trackd exist, musical but different |
| **Brano** | Common word: 225 repositories contain it, hard to search for |
| **Fonoteca** | 33 repositories (one is `fonotecaDownloader`); the name of public institutions |

Discarded: `nastro`, `cratefill`, `linktune`, `tapedeck` (already on PyPI), `spulo` (close to Spowlo, a Spotify
downloader), anything starting with "Spot".

### What changes

| Where | What |
|---|---|
| `ytmpd/` | → `songhaul/` |
| `gui.py`, `update.py` | Window title, repository, User-Agent, `~/.songhaul`, Music folder, `SONGHAUL_URL`, log prefix |
| `paths.py` (new) | Name, old name, folders, one-time copy of the old data |
| `downloader.py`, `main.py`, `tests/` | Imports |
| `pyproject.toml` | `name`, `product`, **`bundle_id` fixed to the old value** |
| `release.yml` | Names of zip, tar, APK and exe |
| `version.sh`, `bump_ytdlp.py` | Path of `__init__.py` |
| README, README.it | Title, URLs, file names, folders, imports, layout |
| `ROADMAP.md` (root) | A note at the top: it's history |
| `DEVLOG.md` | Not rewritten: a new entry |
| `docs/screenshots/` | 10 PNGs, redone with the new name |

**Kept on purpose**

| What | Why |
|---|---|
| `.ytmpd-archive.txt` | It's already in the users' folders |
| `bundle_id` | Android updates, and the data folder on macOS and Linux |
| `ytmpd_android`, `ytmpd_qjs`, `YTMPD_*` secrets | Internal names nobody sees (D4) |
| `spike/android/` | Archived experiment, with the names of the time |

**Outside the repository**

| Where | Who | What |
|---|---|---|
| GitHub, repository name | Owner, from the site | → `songhaul`. GitHub redirects the old URLs: **never create another repository with the old name**, it would break the update notice of installed apps |
| GitHub, description and topics | Owner | "Download playlists from YouTube…" |
| Local remote | After the rename | `git remote set-url origin https://github.com/FrancescoPazz/songhaul.git` |
| Local folder | Owner, optional | Recreate `.venv` (it contains absolute paths) |
| Existing releases and tags | Nobody | They keep the old names |

### Three things the rename would break

1. **Android updates.** The app id derives from `name`: it's `io.github.francescopazz.yt_music_playlist_downloader`.
   Changing it, Android would install a **second app** and the first would never update again. Remedy: `bundle_id` fixed
   in `[tool.flet]`. There it also fixes the id on macOS and Linux, whose data folders depend on it.
2. **Settings and history on Windows.** They are in
   `%APPDATA%\Francesco Pazzaglia\YT Music Playlist Downloader\data`, which contains `product`. Remedy: the first start
   copies `history.json`, `cookies.txt` and `settings.json` once (the same for `~/.ytmpd`).
3. **Songs already downloaded.** If the default folder changes, the archives aren't found and **everything is downloaded
   again**; on Android the archive's file name depends on the folder too. Remedy: an existing old Music folder stays in
   use; the new name is for new installs. `.ytmpd-archive.txt` keeps its name.

---

## 5. Phases

Common rules: one branch per phase, green tests, a DEVLOG entry, READMEs in both languages, a check on Windows and on the
Android emulator, release with a tag. Network checks live in a manual script, never in CI.

### Phase 0A — Rename

| | |
|---|---|
| **Goal** | New name everywhere, without losing updates, settings or archives |
| **Files** | Those in the [table](#what-changes) |
| **New dependencies** | None |
| **Risks** | The three points above. File names in `release.yml` that don't match what Flet produces. Order: the repository is renamed on the site first, then the branch is merged |
| **How to test** | Existing tests plus one on copying the data. Manual run of `release.yml`. On the emulator: an older APK installed, then the new one **on top**, history still there. On Windows: an older version with a playlist downloaded, then the new one, Sync says "Nothing new". From 0.5.0 the update notice still arrives |
| **Done when** | `git grep` of the old name finds only the listed exceptions (archive, `bundle_id`, migration, history, D4 names) and the four checks pass |

### Phase 0B — Common interface

| | |
|---|---|
| **Goal** | `sources/` with YouTube as the first implementation; identical behaviour |
| **Files** | `sources/__init__.py` and `youtube.py` (new); `core.py`, `gui.py` (`link_in_text`, clipboard, `is_playlist`, fallback names); `tests/` |
| **New dependencies** | None |
| **Risks** | Changing numbering, archive or the 403 retry by accident. Circular imports between `core` and `sources` (options are passed as arguments) |
| **How to test** | The existing tests pass **without changing their assertions**. Before the refactoring, the output (events, file names, archive) of a song, a playlist and a song in a mix is recorded; afterwards it must match. GUI check on desktop and emulator |
| **Done when** | Identical output, no mention of YouTube in `core.py` outside the JavaScript runtimes and the 403 retry, `list_playlist()` and `download()` with the same signature |

### Phase 1 — SoundCloud

| | |
|---|---|
| **Goal** | Tracks and sets from CLI, desktop and Android, with real titles and no previews passed off as songs |
| **Files** | `sources/soundcloud.py` (new); `core.py` (error reasons, `archived_ids` with the platform, format choice, thumbnail order, cover resizing); `gui.py` (cookies, rows with a problem); `i18n.py`; `cli.py`; README |
| **New dependencies** | None |
| **Includes** | Titles, durations, previews and DRM in one request every 50 tracks; a filter that excludes `*_preview` formats; `drm` and `preview` shown **before** the download; short and private links; SoundCloud's `cookies.txt` |
| **Risks** | **M4A on Android**: tried first; it failed, and joining the indexes solved it. `_call_api` is internal to yt-dlp: if it changes, fall back to the list without titles. Many DRM tracks: to be said clearly in the README. 429 limits |
| **How to test** | Recorded responses: a set with normal, DRM and SNIP tracks; ids with the same number on two platforms; valid, private, short and deceptive links. Manual: a CC-BY track and a mixed set, MP3 and M4A, two runs in a row |
| **Done when** | A mixed set downloads the free tracks and lists the others with the right reason, the second run downloads nothing, no 30-second files; on Android the file has the right duration in a player |

### Phase 2 — Spotify (single tracks)

| | |
|---|---|
| **Goal** | From `open.spotify.com/track/…` to the matching song, or a clear reason |
| **Files** | `sources/spotify.py`, `matching.py`, `tests/test_matching.py`, `tests/fixtures/` (new); `core.py` (jobs with imposed tags); `gui.py` (credentials in Settings, choosing a candidate); `cli.py` (`--accept-doubtful`); `i18n.py`; `pyproject.toml`; `requirements.txt`; `.gitignore`; README (how to create the Spotify app) |
| **New dependencies** | `ytmusicapi`, **pinned**: 1.12.2 and 1.12.3 had bugs that made spotDL's downloads fail |
| **First step** | With a real Client ID, confirm that `GET /tracks/{id}` answers with client credentials in development mode: the documentation implies it but doesn't say so. If not, phase 3's user sign-in comes first |
| **Risks** | Spotify's rules (tightened three times between November 2024 and February 2026) and [terms](#what-the-terms-say). Wrong matches. `ytmusicapi` is unofficial and not covered by the weekly update: extend `bump_ytdlp.py`. Premium lapsed = feature stopped |
| **How to test** | About 50 recorded cases: original/live, remix, remaster, "feat.", non-Latin titles, same names, missing songs. Thresholds tuned on these. A test that no token ends up in logs or reports. Manual: 10 songs listened to |
| **Done when** | No wrong match among the "safe" ones of the 50 cases, at least 80% of existing songs recognised as "safe"; a doubtful one never downloads by itself; without credentials the message says what to do |

### Phase 3 — Spotify (playlists)

| | |
|---|---|
| **Goal** | Owned or collaborative playlists, and albums |
| **Files** | `sources/spotify.py` (user sign-in with PKCE, paging, albums), `core.py` (several jobs, one cancel, `spotify <id>` archive), `gui.py` (sign-in, review of the doubtful ones at the end, Sync), `cli.py`, `i18n.py`, README |
| **New dependencies** | None (PKCE and the local server with the standard library) |
| **Risks** | Other people's playlists: 403, explained with the suggestion of copying it into one's own. Sign-in on Android (from the browser back to the app): if the loopback doesn't hold, the token is imported from the desktop. Sign-in every 6 months. Unknown quota on long playlists. About 0.5–1.5 s of search per track. Local tracks, podcasts, removed tracks |
| **How to test** | Recorded pages with null items, episodes, local files and duplicates; simulated 403 and 429; cancel during the search; two Spotify tracks on the same video. Manual: playlists of 5 and 100+ tracks, twice |
| **Done when** | A playlist of 100 gets to the end with one missing and one doubtful track in the middle; the numbering follows Spotify; the second run searches and downloads nothing; Cancel stops within a few seconds |

### Phase 4 — Polish

| | |
|---|---|
| **Goal** | The same result from every platform, clear errors, complete documentation |
| **Files** | `core.py`, `sources/`, `gui.py`, `i18n.py`, `cli.py`, both READMEs, screenshots, `release.yml` |
| **New dependencies** | None |
| **Includes** | One tag writer with `mutagen` for MP3 and M4A (today FFmpeg also writes the whole description and the link into the MP3, the M4A only gets title, artist and album); track number; album of the set; `youtu.be`; possibly one naming scheme (D6); tests on every push; README rewritten per platform, with limits and terms |
| **Risks** | Changing YouTube's tags: to be announced in the notes. ID3v2.3 must stay |
| **How to test** | A table of cases per platform and format that reads the tags back from the file. Windows Explorer and an Android player |
| **Done when** | The same song from three platforms = the same fields filled in and the same naming scheme; every error reason has a text in two languages and a test; the READMEs don't promise what doesn't work |

---

## Decisions

### Taken (25 November 2026)

| | Question | Decision |
|---|---|---|
| **D1** | Which name? | **Songhaul** |
| **D4** | Rename the invisible internal names (`ytmpd_android`, `ytmpd_qjs`, `YTMPD_*` secrets)? | **No**, only the Python package. The others cost an NDK build, wheels and secrets to recreate, with no effect for users |
| **D5** | Keep the old Music folder for those who already have the app? | **Yes**, so nothing is downloaded again |
| **D8** | The old `ROADMAP.md`, and the language of this one? | **A note at the top** of the old one; this one **in English** like the other documents |
| **D7** | SoundCloud tracks with DRM: skipped, or searched on YouTube Music? | **Skipped** in phase 1, with the reason; matching can be added after phase 2 |
| **D6** | `Artist - Title` for YouTube and SoundCloud too? | **As an option**, off by default, and only when the title doesn't have the artist already |
| **D2** | Spotify: go on, knowing the limits and the terms, or stop at SoundCloud? | **Stop at SoundCloud** for now; phases 2 and 3 stay here as a plan |

### Open

| | Question | Recommendation |
|---|---|---|
| **D3** | If Spotify comes back: Tags and cover of Spotify songs: from the song found on YouTube Music or from Spotify? | From YouTube Music: consistent with the YouTube source, less code, less friction with the terms |
