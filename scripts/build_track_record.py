#!/usr/bin/env python3
"""Baut strategien/index.html (zeitversetzter Track Record) aus einem quantEnv-top_picks-HTML.

Veröffentlicht werden NUR abgeschlossene Halteperioden aus der Δ-MoM-Matrix.
Die aktuellen Top-Picks des Stichtags werden bewusst nicht übernommen.

Aufruf:  python3 scripts/build_track_record.py <pfad/zu/YYYYMMDD_top_picks.html>
"""
import html, math, re, sys
from datetime import date
from pathlib import Path

# Interne Strategienamen -> öffentliche Bezeichnung
LABELS = {
    "momentum_rs":         ("Momentum", "Nasdaq 100 · monatlich"),
    "xgboost_ls_qqq":      ("ML-Ranking USA", "S&P 500 · monatlich"),
    "xgboost_momentum_pw": ("ML-Momentum", "Nasdaq 100 · monatlich"),
    "fang_plus":           ("FANG+", "fester Korb · quartalsweise"),
    "xgboost_ls_qqq_ch":   ("ML-Ranking Schweiz", "SPI · monatlich"),
}

def parse(src):
    s = Path(src).read_text(encoding="utf-8")
    stich = re.search(r"Stichtag (\d\d\.\d\d\.\d{4})", s).group(1)
    m = s[s.index('<table class="mx">'):]
    m = m[:m.index("</table>")]
    heads = re.findall(r"<th>(.*?)</th>", m)[1:]
    keys = [re.sub(r"<[^>]+>", "", h.split("<span")[0]) for h in heads]
    freqs = [re.search(r"fq'>(\w+)<", h).group(1) for h in heads]
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", m)[1:]:
        cells = re.findall(r"<td class='([\w ]+)'(?: title='([^']*)')?>(.*?)</td>", tr)
        dt = cells[0][2]
        vals = []
        for cls, title, v in cells[1:]:
            if "na" in cls.split() or "open" in cls.split():
                vals.append(None)       # leer oder offene Periode -> nicht veröffentlichen
                continue
            per, _, basket = html.unescape(title).partition(" · ")
            vals.append({"r": float(v), "per": per, "basket": basket})
        rows.append((dt, vals))
    return stich, keys, freqs, rows

def fmt(x, d=1):
    return f"{x:+.{d}f}".replace(".", ",").replace("-", "−")

def build(src, out):
    stich, keys, freqs, rows = parse(src)
    n = len(keys)
    names = [LABELS.get(k, (k, ""))  for k in keys]

    # Kennzahlen je Strategie
    stats = []
    for j in range(n):
        rs = [r[j]["r"] for _, r in rows if r[j]]
        cum = math.prod(1 + x / 100 for x in rs) - 1
        hit = sum(x > 0 for x in rs) / len(rs)
        stats.append({"cum": cum * 100, "hit": hit * 100, "n": len(rs),
                      "best": max(rs), "worst": min(rs)})
    first, last = rows[0][0], rows[-1][0]

    # Letzte abgeschlossene Periode je Strategie
    lastp = []
    for j in range(n):
        for dt, r in reversed(rows):
            if r[j]:
                lastp.append(r[j]); break

    def cell(c):
        if not c: return "<td class='na'>·</td>"
        cls = "pos" if c["r"] >= 0 else "neg"
        t = html.escape(f'{c["per"]} · {c["basket"]}', quote=True)
        return f"<td class='{cls}' title='{t}' data-b='{t}' tabindex='0'>{fmt(c['r'])}</td>"

    thead = "".join(f"<th>{html.escape(a)}<span>{f}</span></th>" for (a, _), f in zip(names, freqs))
    body = "".join(f"<tr><td class='dt'>{dt}</td>{''.join(cell(c) for c in r)}</tr>"
                   for dt, r in reversed(rows))
    cards = ""
    for (a, b), st, lp in zip(names, stats, lastp):
        cls = "pos" if lp["r"] >= 0 else "neg"
        cards += f"""
      <div class="card">
        <div class="ct"><strong>{html.escape(a)}</strong><span>{html.escape(b)}</span></div>
        <div class="kpi"><b class="{'pos' if st['cum']>=0 else 'neg'}">{fmt(st['cum'],0)} %</b><span>kumuliert, {st['n']} Perioden</span></div>
        <div class="kpi"><b>{st['hit']:.0f} %</b><span>Perioden im Plus</span></div>
        <div class="last"><span>Zuletzt abgeschlossen ({html.escape(lp['per'])})</span>
          <em>{html.escape(lp['basket'])}</em> <b class="{cls}">{fmt(lp['r'])} %</b></div>
      </div>"""

    page = TEMPLATE.format(stich=stich, first=first, last=last, cards=cards,
                           thead=thead, body=body, built=date.today().strftime("%d.%m.%Y"))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(page, encoding="utf-8")
    print(f"geschrieben: {out}  (Perioden {first} … {last}, Stichtag {stich})")

TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Strategie-Track-Record – Karsten Steinberg</title>
<meta name="description" content="Zeitversetzter Track Record regelbasierter Aktienstrategien – nur abgeschlossene Halteperioden, simulierte Modellportfolios.">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
         background:#f7f5ec; color:#333; line-height:1.55; }}
  header {{ background:#0f2c26; color:#fff; padding:36px 16px 30px; text-align:center; }}
  header a {{ color:#f4a261; text-decoration:none; font-size:.9em; }}
  header h1 {{ font-size:1.9em; margin:8px 0 4px; }}
  header p {{ opacity:.85; font-size:.95em; }}
  main {{ max-width:1000px; margin:0 auto; padding:28px 16px 40px; }}
  section {{ background:#fff; border-radius:14px; padding:24px; margin-bottom:24px;
            box-shadow:0 2px 8px rgba(0,0,0,.08); }}
  h2 {{ color:#0f2c26; font-size:1.3em; margin-bottom:12px; border-left:4px solid #f4a261; padding-left:10px; }}
  .note {{ font-size:.88em; color:#666; margin-bottom:14px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; }}
  .card {{ border:1px solid #e3dfcc; border-radius:10px; padding:14px 16px; background:#fcfbf6; }}
  .ct strong {{ display:block; color:#0f2c26; }}
  .ct span {{ font-size:.82em; color:#777; }}
  .kpi {{ display:inline-block; margin:10px 18px 0 0; }}
  .kpi b {{ display:block; font-size:1.25em; font-variant-numeric:tabular-nums; }}
  .kpi span {{ font-size:.78em; color:#777; }}
  .last {{ margin-top:12px; padding-top:10px; border-top:1px dashed #e3dfcc; font-size:.85em; }}
  .last span {{ display:block; color:#777; font-size:.9em; }}
  .last em {{ font-style:normal; color:#333; }}
  b.pos, .pos {{ color:#1f7a3a; }}  b.neg, .neg {{ color:#b42323; }}
  .mxw {{ overflow-x:auto; }}
  table {{ border-collapse:collapse; font-size:.85em; font-variant-numeric:tabular-nums; width:100%; }}
  th {{ background:#0f2c26; color:#fff; padding:6px 8px; text-align:right; font-weight:600; vertical-align:bottom; }}
  th:first-child {{ text-align:left; }}
  th span {{ display:block; font-weight:400; opacity:.7; font-size:.85em; }}
  td {{ padding:4px 8px; text-align:right; border-bottom:1px solid #eee; white-space:nowrap; }}
  td.dt {{ text-align:left; font-weight:600; color:#555; }}
  td.pos {{ background:#e3f4e8; font-weight:600; cursor:pointer; }}
  td.neg {{ background:#fbe5e5; font-weight:600; cursor:pointer; }}
  td.na {{ color:#ccc; text-align:center; }}
  td.sel {{ outline:2px solid #f4a261; outline-offset:-2px; }}
  #info {{ min-height:1.5em; margin:10px 0 0; font-size:.88em; color:#0f2c26; }}
  .disc {{ font-size:.82em; color:#666; }}
  .disc p + p {{ margin-top:8px; }}
  footer {{ text-align:center; font-size:.8em; color:#888; padding:0 16px 30px; }}
</style>
</head>
<body>
<header>
  <a href="https://kieselstark.github.io/">← Startseite</a>
  <h1>Strategie-Track-Record</h1>
  <p>Regelbasierte Aktienstrategien · nur abgeschlossene Perioden · {first} bis {last}</p>
</header>
<main>
  <section>
    <h2>Überblick</h2>
    <p class="note">Simulierte Modellportfolios mit je drei Titeln (FANG+: fester Korb), gleichgewichtet, ohne Kosten und Steuern.
      Gezeigt werden ausschließlich Perioden, die bereits abgeschlossen sind – aktuelle Positionen werden nicht veröffentlicht.</p>
    <div class="cards">{cards}
    </div>
  </section>
  <section>
    <h2>Return je Halteperiode</h2>
    <p class="note">Zeile = Monat, in dem der Korb gewählt wurde; Zelle = Return dieses Korbs bis zum nächsten Rebalancing in %, nicht kumuliert.
      Quartalsstrategien haben nur jede dritte Zeile. Zelle antippen oder mit der Maus darüberfahren zeigt Zeitraum und Korb.</p>
    <div class="mxw"><table>
      <thead><tr><th>Monat</th>{thead}</tr></thead>
      <tbody>{body}</tbody>
    </table></div>
    <p id="info"></p>
  </section>
  <section class="disc">
    <h2>Wichtige Hinweise</h2>
    <p><strong>Keine Anlageberatung, keine Anlageempfehlung.</strong> Diese Seite dokumentiert rückblickend die Ergebnisse
      regelbasierter Modellportfolios. Sie ist keine Aufforderung zum Kauf oder Verkauf von Wertpapieren.</p>
    <p><strong>Simulierte Ergebnisse.</strong> Die Werte stammen aus Modellrechnungen, nicht aus einem real geführten Depot.
      Sie enthalten keine Transaktionskosten, Steuern oder Slippage. Vergangene oder simulierte Wertentwicklungen sind kein
      verlässlicher Indikator für künftige Ergebnisse; Verluste bis zum Totalverlust einzelner Positionen sind möglich.</p>
    <p><strong>Interessenkonflikt.</strong> Der Autor kann in einzelnen hier genannten Wertpapieren selbst investiert sein
      oder es zu einem späteren Zeitpunkt werden.</p>
  </section>
</main>
<footer>Stand der Daten: {stich} · erstellt am {built} · © Karsten Steinberg</footer>
<script>
  const info = document.getElementById('info');
  document.querySelectorAll('td[data-b]').forEach(td => {{
    const show = () => {{
      document.querySelectorAll('td.sel').forEach(x => x.classList.remove('sel'));
      td.classList.add('sel');
      const col = td.cellIndex, name = td.closest('table').querySelectorAll('th')[col].firstChild.textContent;
      info.textContent = name + ': ' + td.dataset.b + ' → ' + td.textContent + ' %';
    }};
    td.addEventListener('click', show); td.addEventListener('mouseenter', show);
    td.addEventListener('keydown', e => {{ if (e.key === 'Enter') show(); }});
  }});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    root = Path(__file__).resolve().parent.parent
    build(sys.argv[1], root / "strategien" / "index.html")
