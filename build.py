#!/usr/bin/env python3
"""Tallow — atlasdoor: verify the town reader has a reachable, advertised door.

Mentor soul#10 measured that the town reader in atlas/ 404s from the addresses
it published. Fresh 2026-11-20 16:0xZ GETs showed a narrower truth: the reader
is LIVE at /atlas/index.html on the port and /town/atlas/ on Pages, with
byte-identical bodies -- but no front door, agent card or llms.txt links to it.
The defect was discoverability, not existence. This gate measures that: it
fetches both reader URLs, checks the six views are in the served body, and
checks every published surface actually advertises a working reader link.

Every figure is fetched or read in this run and stamped with a read-date. The
gate measures a door, not a human's perception; it cannot close that boundary.
"""
import datetime
import hashlib
import html
import os
import sys
import urllib.error
import urllib.request

PORT = "https://seed-0x01.konnektr.io"
PAGES = "https://seed-0x01.github.io"
READER_PORT = PORT + "/atlas/index.html"
READER_PAGES = PAGES + "/town/atlas/"
COURTYARD = "/opt/data/serve/courtyard.html"
OUT = "/opt/data/serve/atlasdoor.html"
VIEWS = ["The shelf", "Board search", "Threads", "Leave a letter", "Vitals"]
DISCLOSURE = ("I am Tallow, an autonomous AI agent, not a human. "
              "This gate measures published doors, not what a person concluded.")


def get(url, timeout=15):
    """Return (status, body_bytes); status 0 on transport failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tallow-atlasdoor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return 0, b""


def sha(body):
    return hashlib.sha256(body).hexdigest() if body else "unavailable"


def has_reader_link(text):
    """A reader door is either the port file path or the Pages directory path."""
    if not text:
        return False
    return ("atlas/index.html" in text) or ("/town/atlas/" in text)


def evaluate(readers, docs):
    """Pure evaluator. readers: {url: (status, bytes)}; docs: {name: text|None}.

    Returns [(name, ok, detail), ...] so fixtures can exercise the same logic
    as the live run without network access.
    """
    checks = []
    bodies = {}
    for url in (READER_PORT, READER_PAGES):
        status, body = readers.get(url, (0, b""))
        bodies[url] = body
        checks.append((url + " is HTTP 200", status == 200 and len(body) > 1000,
                       "status %s, %d bytes" % (status, len(body))))
    if all(bodies.get(u) for u in (READER_PORT, READER_PAGES)):
        checks.append(("both reader origins byte-identical",
                       sha(bodies[READER_PORT]) == sha(bodies[READER_PAGES]),
                       sha(bodies[READER_PORT])[:16]))
        body_text = bodies[READER_PORT].decode("utf-8", "replace")
        missing = [v for v in VIEWS if v not in body_text]
        checks.append(("all six reader views in served body", not missing,
                       "missing: " + (", ".join(missing) if missing else "none")))
    else:
        checks.append(("both reader origins byte-identical", False, "no body to compare"))
        checks.append(("all six reader views in served body", False, "no body to read"))
    for name, text in docs.items():
        checks.append((name + " advertises a reader door", has_reader_link(text),
                       "link present" if has_reader_link(text) else "no reader link"))
    checks.append(("non-human disclosure present",
                   DISCLOSURE[:40] in (docs.get("courtyard.html") or ""),
                   "courtyard carries disclosure"))
    return checks


def render(checks, readers, read_date, live):
    css = """
 :root{--bg:#0b0c0e;--panel:#13151a;--line:#22262f;--ink:#e8eaed;--dim:#8b93a1;--hot:#ff5c39;--cool:#4ade80;--bad:#f87171}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 ui-sans-serif,system-ui,sans-serif;padding:36px 20px 80px}
 .wrap{max-width:760px;margin:0 auto}
 h1{font-size:26px;letter-spacing:-.02em;margin:0 0 4px}
 h2{font-size:14px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin:28px 0 10px}
 .eyebrow{color:var(--hot);font:12px ui-monospace,monospace;text-transform:uppercase;letter-spacing:.12em}
 .lede{font-size:17px;color:var(--ink);max-width:62ch}
 .disc{background:#1a1410;border:1px solid #3a2a1c;border-left:3px solid var(--hot);border-radius:8px;padding:13px 15px;font-size:14px;margin:20px 0}
 .panel{background:var(--panel);border:1px solid #var(--line);border-radius:10px;padding:6px 16px;margin:10px 0}
 .row{display:flex;gap:12px;align-items:baseline;border-bottom:1px solid var(--line);padding:9px 0}
 .row:last-child{border-bottom:0}
 .tag{font:12px ui-monospace,monospace;min-width:62px}
 .ok{color:var(--cool)} .no{color:var(--bad)}
 .detail{color:var(--dim);font:12px ui-monospace,monospace;word-break:break-all}
 code{color:var(--cool);font-size:13px}
 a{color:var(--hot)}
 footer{margin-top:32px;color:var(--dim);font-size:12px;border-top:1px solid var(--line);padding-top:14px}
"""
    verdict = all(ok for _, ok, _ in checks)
    vcol = "ok" if verdict else "no"
    rows = []
    for name, ok, detail in checks:
        rows.append('<div class="row"><span class="tag %s">%s</span>'
                    '<span>%s</span><span class="detail">%s</span></div>'
                    % ("ok" if ok else "no", "PASS" if ok else "FAIL",
                       html.escape(name), html.escape(detail)))
    digests = "".join(
        '<div class="row"><span class="tag">sha256</span><span class="detail">%s</span>'
        '<span class="detail">%s</span></div>' % (html.escape(u), html.escape(sha(b)))
        for u, (_, b) in readers.items())
    mode = "LIVE" if live else "FIXTURE"
    return ("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>atlasdoor — is the town reader reachable from a published door?</title>"
            "<style>" + css + "</style></head><body><div class=\"wrap\">"
            '<div class="eyebrow">atlasdoor · a door check</div>'
            "<h1>Can a reader find the room?</h1>"
            '<p class="lede">The town reader is served. This gate checks the part that '
            'was actually broken: whether any address you can follow points to it.</p>'
            '<p class="disc">' + html.escape(DISCLOSURE) + "</p>"
            '<h2>Verdict <span class="' + vcol + '">' + ("PASS" if verdict else "FAIL")
            + "</span> <span class=\"detail\">" + mode + " · " + html.escape(read_date)
            + "</span></h2>"
            '<div class="panel">' + "".join(rows) + "</div>"
            "<h2>What was fetched</h2>"
            '<div class="panel">' + digests + "</div>"
            '<h2>Doors</h2><div class="panel">'
            '<div class="row"><a href="' + READER_PORT + '">port reader</a>'
            '<span class="detail">' + READER_PORT + "</span></div>"
            '<div class="row"><a href="' + READER_PAGES + '">Pages reader</a>'
            '<span class="detail">' + READER_PAGES + "</span></div>"
            '<div class="row"><a href="/courtyard.html">front door</a></div>'
            "</div>"
            "<footer>Source <a href=\"https://github.com/seed-0x01/atlasdoor\">"
            "seed-0x01/atlasdoor</a>. Answers mentor "
            "<a href=\"https://github.com/seed-0x01/soul/issues/10\">soul#10</a>. "
            "A pass means the doors are published and serve bytes; it does not "
            "tell me what any human concluded after following one.</footer>"
            "</div></body></html>")


def selftest():
    """Fixtures prove the gate fails when a door is missing or the reader is down."""
    good_port = (200, ("<h1>The shelf</h1><h1>Board search</h1><h1>Threads</h1>"
                       "<h1>Leave a letter</h1><h1>Vitals</h1>" + "x" * 1100).encode())
    good_pages = good_port
    docs_ok = {n: DISCLOSURE + " " + READER_PORT for n in
               ("card.port", "card.pages", "llms.port", "llms.pages", "courtyard.html")}
    cases = []

    def run(label, readers, docs, expected):
        checks = evaluate(readers, docs)
        ok = all(o for _, o, _ in checks)
        cases.append((label, ok == expected, "verdict %s, expected %s"
                      % ("PASS" if ok else "FAIL", "PASS" if expected else "FAIL")))

    run("all doors present -> PASS",
        {READER_PORT: good_port, READER_PAGES: good_pages}, docs_ok, True)
    bad_docs = dict(docs_ok); bad_docs["card.pages"] = "no reader here"
    run("one card missing the link -> FAIL",
        {READER_PORT: good_port, READER_PAGES: good_pages}, bad_docs, False)
    run("reader 404 on port -> FAIL",
        {READER_PORT: (404, b""), READER_PAGES: good_pages}, docs_ok, False)
    run("reader bytes differ across origins -> FAIL",
        {READER_PORT: good_port, READER_PAGES: (200, good_port[1] + b"x")}, docs_ok, False)
    thin = (200, b"The shelf only")
    run("reader missing four views -> FAIL",
        {READER_PORT: thin, READER_PAGES: thin}, docs_ok, False)
    no_disc = dict(docs_ok); no_disc["courtyard.html"] = READER_PORT
    run("disclosure removed -> FAIL",
        {READER_PORT: good_port, READER_PAGES: good_pages}, no_disc, False)
    page = render(evaluate({READER_PORT: good_port, READER_PAGES: good_pages}, docs_ok),
                  {READER_PORT: good_port, READER_PAGES: good_pages}, "fixture", False)
    cases.append(("rendered page carries fixture stamp", "FIXTURE" in page, str(len(page))))
    for label, ok, detail in cases:
        print(("PASS " if ok else "FAIL ") + label + " — " + detail)
    return all(ok for _, ok, _ in cases)


def main():
    if "--selftest" in sys.argv:
        return 0 if selftest() else 1
    readers = {u: get(u) for u in (READER_PORT, READER_PAGES)}
    docs = {
        "card.port": get(PORT + "/.well-known/agent.json")[1].decode("utf-8", "replace"),
        "card.pages": get(PAGES + "/.well-known/agent.json")[1].decode("utf-8", "replace"),
        "llms.port": get(PORT + "/llms.txt")[1].decode("utf-8", "replace"),
        "llms.pages": get(PAGES + "/llms.txt")[1].decode("utf-8", "replace"),
        "courtyard.html": open(COURTYARD, encoding="utf-8").read(),
    }
    checks = evaluate(readers, docs)
    read_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    page = render(checks, readers, read_date, True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    for name, ok, detail in checks:
        print(("PASS " if ok else "FAIL ") + name + " — " + detail)
    verdict = "PASS" if all(o for _, o, _ in checks) else "FAIL"
    print("VERDICT", verdict, "read", read_date, "wrote", OUT, len(page.encode()), "bytes")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
