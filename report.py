"""Consolidate all round results into one ranked verdict table."""
import glob
import pandas as pd

frames = []
for f in sorted(glob.glob("round*_results.csv")):
    df = pd.read_csv(f)
    df["round"] = f.split("_")[0]
    frames.append(df)
allr = pd.concat(frames, ignore_index=True)
allr = allr[allr.get("note").isna()] if "note" in allr.columns else allr
allr = allr.sort_values(["verdict", "t_excess"], ascending=[True, False])

cols = ["round", "name", "start", "end", "excess_cagr", "sharpe", "bench_sharpe",
        "t_excess", "half1_ex", "half2_ex", "win12", "maxdd", "verdict"]
cols = [c for c in cols if c in allr.columns]
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
print(allr[cols].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

n_acc = (allr["verdict"] == "ACCEPT").sum()
n_ra = (allr["verdict"] == "RA-ONLY").sum()
n_rej = (allr["verdict"] == "REJECT").sum()
print(f"\nACCEPT: {n_acc}   RA-ONLY: {n_ra}   REJECT: {n_rej}")
allr.to_csv("all_results.csv", index=False)
