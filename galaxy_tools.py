# galaxy_tools.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ---------- constants you can reuse ----------
DT_COLS_COMMON = [
    "INCIDENT_DATETIME",
    "FIRST_ASSIGNMENT_DATETIME",
    "FIRST_ON_SCENE_DATETIME",
    "INCIDENT_CLOSE_DATETIME",
]
DT_COLS_EMS_EXTRA = [
    "FIRST_HOSP_ARRIVAL_DATETIME",
    "FIRST_TO_HOSP_DATETIME",
]
MEASURE_COLS_SHARED = [
    "DISPATCH_RESPONSE_SECONDS_QY",
    "INCIDENT_RESPONSE_SECONDS_QY",
    "INCIDENT_TRAVEL_TM_SECONDS_QY",
]
LOC_COLS = [
    "BOROUGH_NORM",
    "ZIPCODE",
    "POLICEPRECINCT",
    "CITYCOUNCILDISTRICT",
    "COMMUNITYDISTRICT",
    "COMMUNITYSCHOOLDISTRICT",
    "CONGRESSIONALDISTRICT",
]


# ---------- helpers ----------
def parse_dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%m/%d/%Y %I:%M:%S %p", errors="coerce")


def clean_seconds(s: pd.Series) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    x = x.mask(x < 0, np.nan)
    x = x.mask(x >= 999, np.nan)  # sentinel cap
    return x


def norm_text(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().str.upper()


def norm_borough(s: pd.Series) -> pd.Series:
    x = norm_text(s)
    return x.replace(
        {
            "RICHMOND / STATEN ISLAND": "STATEN ISLAND",
            "RICHMOND": "STATEN ISLAND",
            "STATEN ISLAND": "STATEN ISLAND",
        }
    )


def date_key_from_dt(s: pd.Series) -> pd.Series:
    d = s.dt.floor("D")
    return (d.dt.year * 10000 + d.dt.month * 100 + d.dt.day).astype("Int32")


def export_csv(df: pd.DataFrame, out_path: str | Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

# ---------- staging step ----------
def make_staging(
    ems: pd.DataFrame,
    fire: pd.DataFrame,
    *,
    dt_cols_common: List[str] = DT_COLS_COMMON,
    dt_cols_ems_extra: List[str] = DT_COLS_EMS_EXTRA,
    measures_shared: List[str] = MEASURE_COLS_SHARED,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    ems_c = ems.copy()
    fire_c = fire.copy()

    # borough normalization into a shared column name
    ems_c["BOROUGH_NORM"] = norm_borough(ems_c["BOROUGH"]) if "BOROUGH" in ems_c.columns else pd.NA
    fire_c["BOROUGH_NORM"] = norm_borough(fire_c["INCIDENT_BOROUGH"]) if "INCIDENT_BOROUGH" in fire_c.columns else pd.NA

    # parse datetimes
    for c in dt_cols_common + dt_cols_ems_extra:
        if c in ems_c.columns:
            ems_c[c] = parse_dt(ems_c[c])
    for c in dt_cols_common:
        if c in fire_c.columns:
            fire_c[c] = parse_dt(fire_c[c])

    # clean shared measures into *_CLEAN
    for c in measures_shared:
        if c in ems_c.columns:
            ems_c[c + "_CLEAN"] = clean_seconds(ems_c[c])
        if c in fire_c.columns:
            fire_c[c + "_CLEAN"] = clean_seconds(fire_c[c])

    return ems_c, fire_c


# ---------- dimensions ----------
def build_dim_time(
    ems_c: pd.DataFrame,
    fire_c: pd.DataFrame,
    *,
    datetime_cols: List[str],
) -> pd.DataFrame:
    dts = []
    for df in (ems_c, fire_c):
        for c in datetime_cols:
            if c in df.columns:
                dts.append(df[c])

    all_dt = (
        pd.concat(dts, ignore_index=True)
        .dropna()
        .dt.floor("D")
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    dim = pd.DataFrame({"date": all_dt})
    dim["date_key"] = (dim["date"].dt.year * 10000 + dim["date"].dt.month * 100 + dim["date"].dt.day).astype("int32")
    dim["year"] = dim["date"].dt.year.astype("int16")
    dim["month"] = dim["date"].dt.month.astype("int8")
    dim["day"] = dim["date"].dt.day.astype("int8")
    dim["weekday"] = dim["date"].dt.weekday.astype("int8")  # 0=Mon
    dim["week"] = dim["date"].dt.isocalendar().week.astype("int16")
    return dim


def build_dim_location(
    ems_c: pd.DataFrame,
    fire_c: pd.DataFrame,
    *,
    loc_cols: List[str] = LOC_COLS,
) -> pd.DataFrame:
    parts = []
    for df in (ems_c, fire_c):
        use = [c for c in loc_cols if c in df.columns]
        parts.append(df[use].copy())

    dim = pd.concat(parts, ignore_index=True).drop_duplicates()

    for c in dim.columns:
        if c != "BOROUGH_NORM":
            dim[c] = pd.to_numeric(dim[c], errors="coerce").astype("Int64")
        else:
            dim[c] = dim[c].astype("string")

    dim = dim.sort_values(dim.columns.tolist(), na_position="last").reset_index(drop=True)
    dim.insert(0, "location_key", (np.arange(len(dim)) + 1).astype("int32"))
    return dim


def build_dim_firehouse(firehouses: pd.DataFrame) -> pd.DataFrame:
    fh = firehouses.copy()
    if "Borough" in fh.columns:
        fh["Borough_Norm"] = norm_borough(fh["Borough"])
    dim = fh.drop_duplicates().reset_index(drop=True)
    dim.insert(0, "firehouse_key", (np.arange(len(dim)) + 1).astype("int32"))
    return dim


def build_small_dims(ems_c: pd.DataFrame, fire_c: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    dims: Dict[str, pd.DataFrame] = {}

    def build(df: pd.DataFrame, col: str, key: str) -> Optional[pd.DataFrame]:
        if col not in df.columns:
            return None
        dim = (
            pd.DataFrame({col: norm_text(df[col])})
            .dropna()
            .drop_duplicates()
            .sort_values(col)
            .reset_index(drop=True)
        )
        dim.insert(0, key, (np.arange(len(dim)) + 1).astype("int32"))
        return dim

    # EMS
    for name, col, key in [
        ("dim_ems_initial_call_type", "INITIAL_CALL_TYPE", "ems_initial_call_type_key"),
        ("dim_ems_final_call_type", "FINAL_CALL_TYPE", "ems_final_call_type_key"),
        ("dim_ems_initial_severity", "INITIAL_SEVERITY_LEVEL_CODE", "ems_initial_severity_key"),
        ("dim_ems_final_severity", "FINAL_SEVERITY_LEVEL_CODE", "ems_final_severity_key"),
        ("dim_ems_disposition", "INCIDENT_DISPOSITION_CODE", "ems_disposition_key"),
    ]:
        d = build(ems_c, col, key)
        if d is not None:
            dims[name] = d

    # FIRE
    for name, col, key in [
        ("dim_fire_class_group", "INCIDENT_CLASSIFICATION_GROUP", "fire_class_group_key"),
        ("dim_fire_class", "INCIDENT_CLASSIFICATION", "fire_class_key"),
        ("dim_fire_alarm_source", "ALARM_SOURCE_DESCRIPTION_TX", "fire_alarm_source_key"),
        ("dim_fire_alarm_level", "ALARM_LEVEL_INDEX_DESCRIPTION", "fire_alarm_level_key"),
    ]:
        d = build(fire_c, col, key)
        if d is not None:
            dims[name] = d

    return dims


# ---------- facts ----------
def attach_location_key(
    df: pd.DataFrame,
    dim_location: pd.DataFrame,
    *,
    loc_cols: List[str] = LOC_COLS,
) -> pd.Series:
    use = [c for c in loc_cols if c in df.columns]
    left = df[use].copy()

    for c in left.columns:
        if c != "BOROUGH_NORM":
            left[c] = pd.to_numeric(left[c], errors="coerce").astype("Int64")
        else:
            left[c] = left[c].astype("string")

    right_cols = [c for c in loc_cols if c in dim_location.columns]
    right = dim_location[right_cols + ["location_key"]].copy()

    on_cols = [c for c in right_cols if c in left.columns]
    return left.merge(right, on=on_cols, how="left")["location_key"]


def attach_dim_key(
    df: pd.DataFrame,
    dim: Optional[pd.DataFrame],
    col: str,
    key_col: str,
) -> pd.Series:
    if dim is None or col not in df.columns:
        return pd.Series(pd.array([pd.NA] * len(df), dtype="Int32"))
    tmp = pd.DataFrame({col: norm_text(df[col])})
    return tmp.merge(dim[[col, key_col]], on=col, how="left")[key_col].astype("Int32")


def build_fact_ems(
    ems_c: pd.DataFrame,
    dim_location: pd.DataFrame,
    dims_other: Dict[str, pd.DataFrame],
    *,
    measures_shared: List[str] = MEASURE_COLS_SHARED,
) -> pd.DataFrame:
    fact = pd.DataFrame(
        {
            "ems_incident_id": ems_c["CAD_INCIDENT_ID"].astype("int64"),
            "incident_datetime": ems_c["INCIDENT_DATETIME"],
            "incident_date_key": date_key_from_dt(ems_c["INCIDENT_DATETIME"]),
        }
    )
    fact["location_key"] = attach_location_key(ems_c, dim_location)

    # measures
    for c in measures_shared:
        cc = c + "_CLEAN"
        if cc in ems_c.columns:
            fact[c.lower() + "_seconds"] = ems_c[cc]

    # FKs to small dims
    if "dim_ems_initial_call_type" in dims_other:
        fact["ems_initial_call_type_key"] = attach_dim_key(
            ems_c, dims_other["dim_ems_initial_call_type"], "INITIAL_CALL_TYPE", "ems_initial_call_type_key"
        )
    if "dim_ems_final_call_type" in dims_other:
        fact["ems_final_call_type_key"] = attach_dim_key(
            ems_c, dims_other["dim_ems_final_call_type"], "FINAL_CALL_TYPE", "ems_final_call_type_key"
        )
    if "dim_ems_initial_severity" in dims_other:
        fact["ems_initial_severity_key"] = attach_dim_key(
            ems_c, dims_other["dim_ems_initial_severity"], "INITIAL_SEVERITY_LEVEL_CODE", "ems_initial_severity_key"
        )
    if "dim_ems_final_severity" in dims_other:
        fact["ems_final_severity_key"] = attach_dim_key(
            ems_c, dims_other["dim_ems_final_severity"], "FINAL_SEVERITY_LEVEL_CODE", "ems_final_severity_key"
        )
    if "dim_ems_disposition" in dims_other:
        fact["ems_disposition_key"] = attach_dim_key(
            ems_c, dims_other["dim_ems_disposition"], "INCIDENT_DISPOSITION_CODE", "ems_disposition_key"
        )

    # flags stay as degenerate attributes (simple slices)
    for flag in ["HELD_INDICATOR", "REOPEN_INDICATOR", "SPECIAL_EVENT_INDICATOR", "STANDBY_INDICATOR", "TRANSFER_INDICATOR"]:
        if flag in ems_c.columns:
            fact[flag.lower()] = norm_text(ems_c[flag]).replace({"TRUE": "1", "FALSE": "0", "Y": "1", "N": "0"}).astype("string")

    return fact


def build_fact_fire(
    fire_c: pd.DataFrame,
    dim_location: pd.DataFrame,
    dims_other: Dict[str, pd.DataFrame],
    *,
    measures_shared: List[str] = MEASURE_COLS_SHARED,
) -> pd.DataFrame:
    fact = pd.DataFrame(
        {
            "fire_incident_id": fire_c["STARFIRE_INCIDENT_ID"].astype("string"),
            "incident_datetime": fire_c["INCIDENT_DATETIME"],
            "incident_date_key": date_key_from_dt(fire_c["INCIDENT_DATETIME"]),
        }
    )
    fact["location_key"] = attach_location_key(fire_c, dim_location)

    for c in measures_shared:
        cc = c + "_CLEAN"
        if cc in fire_c.columns:
            fact[c.lower() + "_seconds"] = fire_c[cc]

    for c in ["ENGINES_ASSIGNED_QUANTITY", "LADDERS_ASSIGNED_QUANTITY", "OTHER_UNITS_ASSIGNED_QUANTITY"]:
        if c in fire_c.columns:
            fact[c.lower()] = pd.to_numeric(fire_c[c], errors="coerce")

    # small dim FKs
    if "dim_fire_class_group" in dims_other:
        fact["fire_class_group_key"] = attach_dim_key(
            fire_c, dims_other["dim_fire_class_group"], "INCIDENT_CLASSIFICATION_GROUP", "fire_class_group_key"
        )
    if "dim_fire_class" in dims_other:
        fact["fire_class_key"] = attach_dim_key(
            fire_c, dims_other["dim_fire_class"], "INCIDENT_CLASSIFICATION", "fire_class_key"
        )
    if "dim_fire_alarm_source" in dims_other:
        fact["fire_alarm_source_key"] = attach_dim_key(
            fire_c, dims_other["dim_fire_alarm_source"], "ALARM_SOURCE_DESCRIPTION_TX", "fire_alarm_source_key"
        )
    if "dim_fire_alarm_level" in dims_other:
        fact["fire_alarm_level_key"] = attach_dim_key(
            fire_c, dims_other["dim_fire_alarm_level"], "ALARM_LEVEL_INDEX_DESCRIPTION", "fire_alarm_level_key"
        )

    # alarm box fields are good degenerate attributes
    for c in ["ALARM_BOX_NUMBER", "ALARM_BOX_LOCATION", "ALARM_BOX_BOROUGH", "HIGHEST_ALARM_LEVEL"]:
        if c in fire_c.columns:
            fact[c.lower()] = fire_c[c]

    return fact
