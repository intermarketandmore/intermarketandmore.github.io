# IntermarketAndMore.it

Sito di IntermarketAndMore: home, categoria video **Focus Mercati** e le ultime analisi del blog.

- `scripts/build.py` legge il feed del blog su FinanzaOnline e il canale YouTube e rigenera `index.html` e `focus-mercati/index.html`.
- `.github/workflows/aggiorna-sito.yml` lo esegue ogni ora e pubblica il sito su GitHub Pages.
- `data/` conserva l'archivio di articoli e video.
- Nessun cookie né tracciamento; font ospitati in `assets/fonts` (licenza SIL OFL); i video YouTube si caricano solo al clic.
