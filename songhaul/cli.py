"""Command line: prints the core's events in Italian."""

import argparse
import sys
from pathlib import Path

from yt_dlp.utils import format_bytes, formatSeconds

from . import core
from .i18n import STRINGS


def explain(message):
    """The reason in plain words, then yt-dlp's own message."""
    return f"{STRINGS['it']['reason_' + core.reason_kind(message)]}\n    {message}"


def print_event(e):
    kind = e["type"]
    if kind == "track_started":
        number = f"{e['index']:03d}" if e["index"] else "---"
        print(f"\n[{number}] {e['title']}")
    elif kind == "progress":
        percent = f"{e['percent']:5.1f}%" if e["percent"] is not None else "    ?"
        speed = f"{format_bytes(e['speed'])}/s" if e["speed"] else ""
        eta = formatSeconds(e["eta"]) if e["eta"] is not None else ""
        print(f"\r{percent:>8} | {speed:>12} | ETA {eta:>6}", end="", flush=True)
    elif kind == "track_done":
        print(f"\n  Salvato: {Path(e['path']).name}")
    elif kind == "track_skipped":
        print(f"\n  Saltato: {e['title'] or e['id'] or ''} {explain(e['reason'])}", file=sys.stderr)
    elif kind == "warning":
        print(f"\n  Attenzione: {e['message']}", file=sys.stderr)
    elif kind == "finished":
        status = "Download annullato" if e["cancelled"] else "Download completato"
        print(f"\n{status}: {e['done']} scaricati, {e['skipped']} saltati.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Scarica una playlist, o un singolo brano, da YouTube, YouTube Music o SoundCloud in MP3 o M4A."
    )
    parser.add_argument("url", help="URL della playlist o del brano")
    parser.add_argument("-o", "--output", default="downloads", help="Cartella di output (default: downloads)")
    parser.add_argument("-f", "--format", choices=core.FORMATS, default="mp3",
                        help="mp3 (richiede FFmpeg) o m4a (audio originale, senza FFmpeg). Default: mp3")
    parser.add_argument("-b", "--bitrate", choices=core.BITRATES, default="192",
                        help="Bitrate MP3 (default: 192). Ignorato con m4a.")
    parser.add_argument("--browser", choices=core.BROWSERS, default="none",
                        help="Browser da cui leggere i cookie. Usa 'none' per non usare cookie. Default: none.")
    parser.add_argument("--items", help="Solo questi brani, per posizione: es. 1,3,5-8")
    parser.add_argument("--list", action="store_true", help="Elenca i brani della playlist senza scaricarli")
    parser.add_argument("--covers", action="store_true", help="Inserisce la copertina nel file")
    parser.add_argument("--clean-titles", action="store_true",
                        help="Toglie \"(Official Video)\", \"[VISUALIZER]\" e simili da titolo e nome del file")
    parser.add_argument("--artist-names", action="store_true",
                        help="Mette l'artista nel nome del file, se il titolo non lo contiene già")
    args = parser.parse_args(argv)

    if args.list:
        try:
            playlist = core.list_playlist(args.url, args.browser)
        except Exception as exc:
            print(f"Errore: {explain(str(exc))}", file=sys.stderr)
            return 1
        print(playlist["title"] or "")
        for t in playlist["tracks"]:
            duration = f"{int(t['duration']) // 60}:{int(t['duration']) % 60:02d}" if t["duration"] else "?"
            problem = f"  [{STRINGS['it']['reason_' + t['problem']]}]" if t["problem"] else ""
            print(f"{t['index']:03d}  {duration:>8}  {t['title'] or t['id']}{problem}")
        return 0

    if args.format == "mp3" and not core.ffmpeg_available():
        print("ERRORE: FFmpeg non è presente nel PATH.\n"
              "Installa FFmpeg e riapri il terminale, oppure usa -f m4a.", file=sys.stderr)
        return 2

    try:
        link = core.normalize_url(args.url)
    except ValueError as exc:
        print(f"Errore: {explain(str(exc))}", file=sys.stderr)
        return 1
    print(f"Link:     {link}")
    print(f"Output:   {Path(args.output).resolve()}")
    print(f"Formato:  {args.format}" + (f" {args.bitrate} kbps" if args.format == "mp3" else ""))
    print(f"Browser:  {args.browser}")
    if args.browser != "none":
        print("\nNota: yt-dlp leggerà i cookie della sessione del browser. Per i video con limite d'età "
              "devi essere normalmente autenticato sul sito nel browser scelto.")

    try:
        result = core.download(args.url, args.output, args.format, args.bitrate, args.browser, args.items,
                               on_event=print_event, covers=args.covers, clean_titles=args.clean_titles,
                               artist_names=args.artist_names)
    except Exception as exc:
        print(f"\nErrore: {explain(str(exc))}", file=sys.stderr)
        return 1
    return 1 if result["skipped"] else 0
