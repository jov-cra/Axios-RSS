# Axios (filtered)

Ein persönlicher, **gefilterter** Axios-RSS-Feed — standardmäßig **ohne Politik**, alles andere bleibt drin. Läuft kostenlos per GitHub Actions, erzeugt eine `feed.xml`, die du in **Tapestry**, Readwise Reader oder jedem RSS-Reader abonnierst.

## Warum das nötig ist

Der Axios-Feed (`api.axios.com/feed/`) ist ein einziger Firehose. Das einzige `<category>`-Feld pro Item ist „top" (eine Prominenz-Markierung), also lässt sich **weder im Feed noch in Tapestry** nach Thema filtern. Das echte Ressort steht erst auf der **Artikelseite**: `<meta name="category" content="Politics & Policy">` (plus Breadcrumb-Link auf `axios.com/<section>`).

Deshalb macht dieses Tool den Schritt, den ein Reader nicht kann:

1. Axios-Feed ziehen.
2. Pro Item **einmal** die Artikelseite laden und die Section auslesen (pro `guid` gecacht → jeder Artikel wird höchstens einmal abgerufen).
3. Items mit passender Section (Default: alles mit „politics") **rauswerfen**.
4. Den Feed **byte-treu** neu zusammensetzen — die übrigen `<item>`-Blöcke bleiben unverändert (Bilder, `content:encoded`, Autoren etc. erhalten).

Deterministisch und gratis: kein KI-Modell, kein API-Key.

## Setup

Dateien in ein **öffentliches** Repo, dann *Settings → Pages → Deploy from branch `main` / root*. Der Workflow (`.github/workflows/feed.yml`) läuft alle 30 Minuten und committet `feed.xml` + `state.json`.

Feed abonnieren:
```
https://jov-cra.github.io/axios-filtered/feed.xml
```

## Konfiguration (im Workflow unter `env:`)

| ENV | Default | Bedeutung |
|-----|---------|-----------|
| `AX_DROP` | `politics` | Komma-Liste von Section-Teilstrings, die rausfliegen (z. B. `politics,world`) |
| `AX_TITLE` | `Axios (filtered)` | Feed-Titel |
| `AX_FEED_URL` | `https://api.axios.com/feed/` | Quell-Feed |
| `AX_FEED_SELF` | – | öffentliche Feed-URL (atom:self) |
| `AX_FETCH_MAX` | `120` | max. Artikel-Abrufe pro Lauf (begrenzt den ersten Durchlauf) |
| `AX_FETCH_DELAY` | `0.4` | Sekunden Pause zwischen Abrufen (Höflichkeit) |

**Welche Sections gibt es?** `python axios_filter.py --report` (oder der `--report`-Lauf im Workflow) listet im Log alle real vorkommenden Sections mit Anzahl und ob sie `keep`/`DROP` sind. So siehst du genau, was du zusätzlich filtern könntest.

**Unbekannte Section → wird behalten.** Wenn eine Artikelseite mal nicht ladbar/lesbar ist, wird das Item **nicht** verworfen (kein versehentliches Löschen; wird beim nächsten Lauf erneut versucht).

## Tests

```bash
pip install -r requirements.txt
python tests/test_filter.py
```
Deckt Feed-Zerlegung, Section-Drop-Logik, Head-Anpassung, End-to-End-Filtern und byte-identische Ausgabe (kein Commit-Churn) ab — alles offline.
