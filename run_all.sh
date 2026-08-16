#!/bin/bash
# One-shot pipeline: fetch data from Yahoo, run all rounds, log everything.
cd "$(dirname "$0")"
python3 -c "import pandas, numpy; print('pandas', pandas.__version__, 'numpy', numpy.__version__)" | tee env.log
find data -name '*.csv' -size -2k -delete 2>/dev/null   # clear junk (HTML challenge pages), keep good files for resume
python3 fetch_yahoo.py > fetch.log 2>&1
# plan B if direct Yahoo is blocked: yfinance (installs to --user site-packages)
if [ ! -s data/spy.us.csv ]; then
  python3 -c "import yfinance" 2>/dev/null || python3 -m pip install --user --quiet yfinance
  python3 fetch_yf.py > fetch_yf.log 2>&1 || true
fi
python3 fetch_fallback.py > fetch_fb.log 2>&1
echo "=== fetch issues (yahoo) ==="
grep -v ",ok$" data/MANIFEST.txt | grep -v "^DONE" | head -20 || echo "(none)"
tail -1 fetch.log
echo "=== fallback source ==="
cat data/MANIFEST_FB.txt
echo "=== adjustment check: SPY first rows (should be ~\$24-27 if div-adjusted, launched at \$43.94 raw) ==="
head -3 data/spy.us.csv 2>/dev/null; tail -1 data/spy.us.csv 2>/dev/null
for r in 1 2 3 4 5 6 7 8 9 10 11; do
  python3 round${r}.py > round${r}.log 2>&1 && echo "round${r} OK" || echo "round${r} FAILED"
done
python3 report.py > report.log 2>&1 && echo "report OK" || echo "report FAILED"
echo "=== DONE ==="
