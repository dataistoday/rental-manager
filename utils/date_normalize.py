"""
utils/date_normalize.py

Sheets-tolerant date parsing.

Backfilled rows in Google Sheets often have abbreviated dates like "2/2" or
"1/24" with no year. pandas parses these as year 0001, which then drops them
out of any year-based filter.

`normalize_date_column` parses the column normally, then for any row whose
parsed year is unreasonably small (< 2020) it falls back to the year of the
`timestamp` column (which is always set automatically when the row is written).
"""

from __future__ import annotations
import datetime
import pandas as pd


def normalize_date_column(
    df: pd.DataFrame,
    date_col: str = "date",
    timestamp_col: str = "timestamp",
    min_reasonable_year: int = 2020,
    default_year: int | None = None,
) -> pd.DataFrame:
    """Return a copy of df with `date_col` parsed and year-corrected.

    Year-fixing strategy when the parsed year is below `min_reasonable_year`
    (e.g. backfilled "2/2" rows that pandas reads as year 0001):
      1. Use the year from `timestamp_col` if it parses.
      2. Else use `default_year` (defaults to today's year).

    Rows whose date column is completely unparseable are left as NaT.
    """
    if df is None or df.empty or date_col not in df.columns:
        return df

    if default_year is None:
        default_year = datetime.date.today().year

    out = df.copy()
    parsed = pd.to_datetime(out[date_col], errors="coerce")
    ts = (
        pd.to_datetime(out[timestamp_col], errors="coerce")
        if timestamp_col in out.columns
        else pd.Series([pd.NaT] * len(out), index=out.index)
    )

    bad_mask = parsed.notna() & (parsed.dt.year < min_reasonable_year)
    if bad_mask.any():
        new_values = []
        for p, t in zip(parsed[bad_mask], ts[bad_mask]):
            year = t.year if pd.notna(t) else default_year
            new_values.append(p.replace(year=year))
        parsed.loc[bad_mask] = new_values

    out[date_col] = parsed
    return out
