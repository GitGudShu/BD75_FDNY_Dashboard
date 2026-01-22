import inspect
import tabulate
import pandas as pd

def df_info(df, rows=5, shape=True, columns=False):
    callers_locals = inspect.currentframe().f_back.f_locals
    df_names = [name for name, val in callers_locals.items() if val is df]
    df_name = df_names[0] if df_names else "<unnamed DataFrame>"

    print(f"DataFrame: {df_name}")
    if shape:
        print(f"Shape: {df.shape}")
    if columns:
        print(f"Columns: {df.columns.tolist()}")
    print(tabulate.tabulate(df.head(rows), headers='keys', tablefmt='psql'))


def display_time_interval(df: pd.DataFrame, col: str = "INCIDENT_DATETIME") -> None:
    dt = pd.to_datetime(
        df[col],
        format="%m/%d/%Y %I:%M:%S %p",
        errors="coerce"
    )

    start = dt.min()
    end = dt.max()

    print(f"start: {start}")
    print(f"end: {end}")
    print(f"duration: {end - start}")


import pandas as pd

def compare_schema(
    ems: pd.DataFrame,
    fire: pd.DataFrame,
    include_dtypes: bool = True,
):
    ems_cols = set(ems.columns)
    fire_cols = set(fire.columns)

    common = sorted(ems_cols & fire_cols)
    only_fire = sorted(fire_cols - ems_cols)
    only_ems = sorted(ems_cols - fire_cols)

    out = {
        "common": common,
        "only_fire": only_fire,
        "only_ems": only_ems,
    }

    if include_dtypes:
        def dtypes_map(df, cols):
            return {c: str(df[c].dtype) for c in cols}

        out["common_dtypes"] = {
            "ems": dtypes_map(ems, common),
            "fire": dtypes_map(fire, common),
        }
        out["only_fire_dtypes"] = dtypes_map(fire, only_fire)
        out["only_ems_dtypes"] = dtypes_map(ems, only_ems)

        out["dtype_mismatches"] = {
            c: (str(ems[c].dtype), str(fire[c].dtype))
            for c in common
            if str(ems[c].dtype) != str(fire[c].dtype)
        }

    return out


def compare_schema_table(ems: pd.DataFrame, fire: pd.DataFrame) -> pd.DataFrame:
    ems_cols = set(ems.columns)
    fire_cols = set(fire.columns)
    all_cols = sorted(ems_cols | fire_cols)

    rows = []
    for c in all_cols:
        rows.append({
            "column": c,
            "in_ems": c in ems_cols,
            "in_fire": c in fire_cols,
            "ems_dtype": str(ems[c].dtype) if c in ems_cols else None,
            "fire_dtype": str(fire[c].dtype) if c in fire_cols else None,
        })
    return pd.DataFrame(rows).sort_values(["in_ems", "in_fire", "column"], ascending=[False, False, True])
