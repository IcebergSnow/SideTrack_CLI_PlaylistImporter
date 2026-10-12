import csv

import pytest

from playlist_importer.errors import InputError
from playlist_importer.files import playlist_id, read_csvs, video_id

A = "fJ9rUzIMcZQ"
B = "YQHsXMglC9A"


@pytest.mark.parametrize("value", [A, f"https://youtu.be/{A}?si=example", f"music.youtube.com/watch?v={A}&list=RD{A}", f"https://youtube.com/shorts/{A}", f"https://www.youtube.com/embed/{A}"])
def test_video_forms(value):
    assert video_id(value) == A


@pytest.mark.parametrize("value", ["Hello - Adele", "https://youtube.com.evil.test/watch?v=" + A, "https://youtube.com@evil.test/watch?v=" + A, "file:///watch?v=" + A, "https://youtube.com:8080/watch?v=" + A, "https://youtube.com/playlist?list=PL123456789012", f"https://youtube.com/watch?v={A}&v={B}", "bad"])
def test_invalid_song_links(value):
    with pytest.raises(InputError):
        video_id(value)


def test_csv_roundtrip_and_combining_preserves_exact_ids_and_order(tmp_path):
    first = tmp_path / "first.csv"
    with first.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["title", "artist", "url"])
        writer.writerow(['A song, with "quotes"', "Björk", f"https://youtube.com/watch?v={A}"])
        writer.writerow(["same ID", "different metadata", f"https://youtu.be/{A}"])
    second = tmp_path / "second.csv"
    second.write_text(f"video_id,title\n{B},Hello\n{A},Repeated\n", encoding="utf-8")
    result = read_csvs([first, second])
    assert [t.video_id for t in result.tracks] == [A, B]
    assert result.tracks[0].title == 'A song, with "quotes"'
    assert result.tracks[0].artist == "Björk"
    assert result.duplicates == 2


@pytest.mark.parametrize("text", ["", "title,artist\nHello,Adele\n", "url,url\na,b\n", "url,title\nonly-one-column\n", "url\na,b\n", "url\n\n", "url\nnot-a-song\n", f"video_id,url\n{A},https://youtu.be/{B}\n", 'url,title\n"unclosed,quote\n'])
def test_bad_csv_is_rejected_before_import(tmp_path, text):
    path = tmp_path / "bad.csv"
    path.write_text(text)
    with pytest.raises(InputError):
        read_csvs([path])


def test_ignores_whitespace_rows_and_normalizes_headers(tmp_path):
    path = tmp_path / "playlist.csv"
    path.write_text(f" URL , TITLE \n , \nhttps://youtu.be/{A}, Song \n")
    assert read_csvs([path]).tracks[0].title == "Song"


def test_txt_has_actionable_message(tmp_path):
    path = tmp_path / "songs.txt"
    path.write_text("Adele - Hello\n")
    with pytest.raises(InputError, match="CSV"):
        read_csvs([path])


def test_playlist_identifier():
    identifier = "PL1234567890abcdef"
    assert playlist_id(identifier) == identifier
    assert playlist_id(f"https://www.youtube.com/playlist?list={identifier}") == identifier
    with pytest.raises(InputError):
        playlist_id("https://evil.test/playlist?list=" + identifier)
