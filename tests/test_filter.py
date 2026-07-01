"""
Unit tests for axios_filter. All offline (article-page fetches are monkeypatched).
Run:  python tests/test_filter.py   (or)   python -m pytest -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import axios_filter as af  # noqa: E402

FIXTURE = (Path(__file__).parent / "fixtures" / "sample_feed.xml").read_text(encoding="utf-8")


def _fake_fetch(url):
    """Serve the fixture for the feed URL and fake article pages for items."""
    if url.rstrip("/").endswith("api.axios.com/feed"):
        return FIXTURE
    if "sample-politics" in url:
        return '<html><head><meta name="category" content="Politics &amp; Policy"></head></html>'
    if "sample-tech" in url:
        return '<html><head><meta name="category" content="Technology"></head></html>'
    return "<html></html>"


# --------------------------------------------------------------------------- #
# Feed surgery
# --------------------------------------------------------------------------- #
def test_split_feed():
    head, items, tail = af.split_feed(FIXTURE)
    assert len(items) == 2
    assert "<channel>" in head and "<title>Axios</title>" in head
    assert tail.strip().endswith("</channel></rss>")
    assert all(b.startswith("<item>") and b.endswith("</item>") for b in items)


def test_item_key_and_link():
    _, items, _ = af.split_feed(FIXTURE)
    assert af.item_key(items[0]) == "https://www.axios.com/2026/07/01/sample-politics"
    assert af.item_link(items[1]) == "https://www.axios.com/2026/07/01/sample-tech"


def test_is_dropped():
    assert af.is_dropped("Politics & Policy", ["politics"]) is True
    assert af.is_dropped("Technology", ["politics"]) is False
    assert af.is_dropped("World", ["politics", "world"]) is True
    assert af.is_dropped("", ["politics"]) is False   # unknown -> keep


def test_adjust_head_removes_builddate_and_sets_title_and_self():
    head, _, _ = af.split_feed(FIXTURE)
    out = af.adjust_head(head, "Axios (no Politics)", "https://x.github.io/axios/feed.xml")
    assert "lastBuildDate" not in out
    assert "<title>Axios (no Politics)</title>" in out
    assert '<atom:link href="https://x.github.io/axios/feed.xml" rel="self"' in out
    assert "api.axios.com/feed" not in out.split("<item")[0]  # old self href replaced


# --------------------------------------------------------------------------- #
# End-to-end filtering
# --------------------------------------------------------------------------- #
def test_run_drops_politics_keeps_rest(tmp_path=None):
    import tempfile, os
    d = tempfile.mkdtemp()
    out, state = os.path.join(d, "feed.xml"), os.path.join(d, "state.json")
    af.fetch = _fake_fetch
    af.main(["--feed-url", "https://api.axios.com/feed/", "--drop", "politics",
             "--delay", "0", "--out", out, "--state", state, "--title", "Axios (no Politics)"])
    result = Path(out).read_text(encoding="utf-8")

    assert "sample-tech" in result          # kept
    assert "sample-politics" not in result  # dropped
    assert result.count("<item>") == 1
    # fidelity: CDATA / media / content preserved verbatim for the kept item
    assert "<![CDATA[" in result and "media:content" in result and "dc:creator" in result
    # section cache populated (each article fetched at most once)
    import json
    sec = json.loads(Path(state).read_text())["section"]
    assert sec["https://www.axios.com/2026/07/01/sample-politics"] == "Politics & Policy"
    assert sec["https://www.axios.com/2026/07/01/sample-tech"] == "Technology"


def test_run_is_deterministic_no_churn():
    import tempfile, os, hashlib
    d = tempfile.mkdtemp()
    out, state = os.path.join(d, "feed.xml"), os.path.join(d, "state.json")
    af.fetch = _fake_fetch
    args = ["--feed-url", "https://api.axios.com/feed/", "--drop", "politics",
            "--delay", "0", "--out", out, "--state", state]
    af.main(args)
    h1 = hashlib.md5(Path(out).read_bytes()).hexdigest()
    af.main(args)                      # second run, same upstream feed
    h2 = hashlib.md5(Path(out).read_bytes()).hexdigest()
    assert h1 == h2                    # identical bytes -> no commit churn


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL  {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    raise SystemExit(1 if failed else 0)
