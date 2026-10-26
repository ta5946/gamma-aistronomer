"""Galactic plane skymap of the internal CTAO dataset, in the style of the HGPS figures.

Stacks CTAO observations along the plane, plots the correlated significance in three
strip panels, and circles the HGPS sources that have CTAO coverage.

The data is simulated, not real CTAO observations. Background comes from the IRF alone,
so this is an overview map rather than a basis for source detection or flux measurement.

    cd src && python plot_ctao_plane.py
"""

import csv
import os
import time

import matplotlib

matplotlib.use("Agg")  # headless

import astropy.units as u
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.nddata.utils import NoOverlapError
from astropy.visualization.wcsaxes import SphericalCircle
from matplotlib.colors import PowerNorm

from dotenv import load_dotenv

from gammapy.data import DataStore
from gammapy.datasets import MapDataset
from gammapy.estimators import ExcessMapEstimator
from gammapy.makers import MapDatasetMaker, SafeMaskMaker
from gammapy.maps import MapAxis, WcsGeom

load_dotenv()

# observations to stack, out of those that cover the plane
N_OBSERVATIONS = 1000

CTAO_DATA_PATH = os.environ.get("CTAO_DATA_PATH")
if not CTAO_DATA_PATH:
    raise SystemExit("Set CTAO_DATA_PATH in .env to the DL3 DataStore, and run from src/.")
HGPS_SOURCES_CSV = "../data/cache/hgps/sources.csv"
OUTPUT_PNG = "../plot/ctao_plane.png"

# map covers l = 300 through 0 to 60 at |b| < 4, drawn as three 40 deg panels
LON_CENTER, LON_SPAN, LAT_SPAN = 0.0, 120.0, 8.0
N_PANELS = 3
BINSZ = 0.02

ENERGY_MIN, ENERGY_MAX = "1 TeV", "100 TeV"

# analysis cut on the offset from the pointing, well inside the 6 deg Prod5 IRF edge
OFFSET_MAX_DEG = 2.5
CUTOUT_WIDTH_DEG = 2 * OFFSET_MAX_DEG + 1.0

# smoothing radius of the significance map
CORRELATION_RADIUS_DEG = 0.1
# color scale saturates here
VMAX = 25.0

# every source is circled and labeled, with a leader line for crowded regions
SOURCE_COLOR = "deepskyblue"
# clear longitude a name needs to sit centered in its panel
LABEL_MARGIN_DEG = 3.0
# labels sit in rows running outward from the plane, alternating above and below
LABEL_ROW_START_DEG = 2.0
LABEL_ROW_STEP_DEG = 0.4
N_LABEL_ROWS_PER_SIDE = 5
# calibrated to the figure width and fontsize 6 labels below
LABEL_CHAR_WIDTH_DEG = 0.22
LABEL_ROW_GAP_DEG = 0.3


def build_geometry():
    """Reference geometry and true-energy axis."""
    energy = MapAxis.from_energy_bounds(ENERGY_MIN, ENERGY_MAX, nbin=4)
    energy_true = MapAxis.from_energy_bounds(
        "0.5 TeV", "200 TeV", nbin=6, name="energy_true"
    )
    geom = WcsGeom.create(
        skydir=SkyCoord(LON_CENTER, 0.0, unit="deg", frame="galactic"),
        frame="galactic",
        proj="CAR",
        binsz=BINSZ,
        width=(LON_SPAN, LAT_SPAN),
        axes=[energy],
    )
    return geom, energy_true


def select_observations(datastore):
    """Observations whose field of view reaches into the map, sampled evenly."""
    table = datastore.obs_table
    obs_ids = np.asarray(table["OBS_ID"])
    pointings = SkyCoord(table["RA_PNT"], table["DEC_PNT"]).galactic

    dlon = np.abs((pointings.l.deg - LON_CENTER + 180.0) % 360.0 - 180.0)
    inside = (dlon < LON_SPAN / 2 + OFFSET_MAX_DEG) & (
        np.abs(pointings.b.deg) < LAT_SPAN / 2 + OFFSET_MAX_DEG
    )
    selected = obs_ids[inside]
    n_available = len(selected)

    if n_available > N_OBSERVATIONS:
        # sorted by longitude, so the sample is spread along the plane
        order = np.argsort(pointings.l.deg[inside])
        step = np.linspace(0, n_available - 1, N_OBSERVATIONS).astype(int)
        selected = selected[order][step]

    return selected, n_available


def stack_observations(datastore, obs_ids, geom, energy_true):
    """Stack observations into the reference geometry."""
    stacked = MapDataset.create(geom, energy_axis_true=energy_true, name="stacked")
    maker = MapDatasetMaker(selection=["counts", "background", "exposure"])
    safe_mask = SafeMaskMaker(
        methods=["offset-max", "aeff-default"], offset_max=f"{OFFSET_MAX_DEG} deg"
    )

    start = time.time()
    n_used = n_skipped = 0

    for i, obs_id in enumerate(obs_ids, start=1):
        obs = datastore.get_observations([obs_id], required_irf=["aeff", "bkg"])[0]

        try:
            cutout = geom.cutout(
                position=obs.get_pointing_icrs(obs.tmid),
                width=f"{CUTOUT_WIDTH_DEG} deg",
            )
        except (NoOverlapError, ValueError):
            n_skipped += 1
            continue

        dataset = MapDataset.create(cutout, energy_axis_true=energy_true)
        dataset = maker.run(dataset, obs)
        dataset = safe_mask.run(dataset, obs)
        stacked.stack(dataset)
        n_used += 1

        if i % 50 == 0 or i == len(obs_ids):
            print(f"  {i}/{len(obs_ids)}, {(time.time() - start) / 60:.1f} min")

    if n_skipped:
        print(f"  skipped {n_skipped} with no overlap")

    return stacked, n_used


def significance_map(stacked):
    """Correlated sqrt(TS), blank outside the observed footprint."""
    image = stacked.to_image()
    maps = ExcessMapEstimator(
        f"{CORRELATION_RADIUS_DEG} deg", selection_optional=[]
    ).run(image)

    sqrt_ts = maps["sqrt_ts"]
    sqrt_ts.data[..., ~image.mask_safe.data.any(axis=0)] = np.nan
    return sqrt_ts


def load_sources():
    """HGPS sources with CTAO coverage that fall inside the map."""
    with open(HGPS_SOURCES_CSV) as f:
        covered = [r for r in csv.DictReader(f) if r["in_ctao"] == "yes"]

    sources = []
    for row in covered:
        # point sources have catalog size 0, a floor keeps them visible
        row["radius"] = max(float(row["size_deg"]), 0.12)
        offset = abs((float(row["glon"]) - LON_CENTER + 180.0) % 360.0 - 180.0)
        if offset <= LON_SPAN / 2 + row["radius"]:
            sources.append(row)

    return sources, len(covered)


def draw_sources(ax, sources, panel_center, half_width):
    """Circle every source in the panel and label it via a leader line."""
    transform = ax.get_transform("galactic")

    # rows to hold labels, nearest to the plane first, alternating above/below
    label_rows = []
    for i in range(N_LABEL_ROWS_PER_SIDE):
        d = LABEL_ROW_START_DEG + i * LABEL_ROW_STEP_DEG
        label_rows += [d, -d]
    row_spans = {row: [] for row in label_rows}

    in_panel = []
    for row in sources:
        lon, lat = float(row["glon"]), float(row["glat"])
        radius = row["radius"]

        offset = (lon - panel_center + 180.0) % 360.0 - 180.0
        if abs(offset) > half_width + radius:
            continue

        ax.add_patch(
            SphericalCircle(
                (lon * u.deg, lat * u.deg),
                radius * u.deg,
                transform=transform,
                edgecolor=SOURCE_COLOR,
                facecolor="none",
                linewidth=0.8,
                alpha=0.85,
            )
        )
        if abs(offset) <= half_width:
            in_panel.append((offset, lon, lat, radius, row["name"]))

    # left to right, each label claims the first row with room, or the least
    # crowded row if none has room
    in_panel.sort(key=lambda item: item[0])
    for offset, lon, lat, radius, name in in_panel:
        half_text = len(name) * LABEL_CHAR_WIDTH_DEG / 2 + LABEL_ROW_GAP_DEG
        lo, hi = offset - half_text, offset + half_text

        free_rows = [
            r for r in label_rows if all(hi < s0 or lo > s1 for s0, s1 in row_spans[r])
        ]
        if free_rows:
            target_row = free_rows[0]
        else:
            target_row = min(label_rows, key=lambda r: len(row_spans[r]))
        row_spans[target_row].append((lo, hi))

        # longitude decreases left to right, so a positive offset is on the left.
        # names close to a panel edge are anchored so they run inward
        if abs(offset) > half_width - LABEL_MARGIN_DEG:
            align = "left" if offset > 0 else "right"
        else:
            align = "center"

        sign = 1 if target_row > 0 else -1
        ax.plot(
            [lon, lon],
            [lat + sign * radius, target_row],
            transform=transform,
            color=SOURCE_COLOR,
            linewidth=0.5,
            alpha=0.6,
        )
        ax.text(
            lon,
            target_row,
            name,
            transform=transform,
            color=SOURCE_COLOR,
            fontsize=6,
            ha=align,
            va="bottom" if sign > 0 else "top",
            clip_on=True,
            path_effects=[pe.withStroke(linewidth=1.6, foreground="black")],
        )


def plot(sqrt_ts, sources, n_covered, n_used, n_available):
    """Three strip panels on one page."""
    norm = PowerNorm(gamma=0.5, vmin=0.0, vmax=VMAX)  # sqrt stretch
    cmap = plt.get_cmap("afmhot").copy()
    cmap.set_bad("black")  # unobserved sky
    panel_width = LON_SPAN / N_PANELS

    fig = plt.figure(figsize=(20, 3.4 * N_PANELS + 1.0))
    image = None

    for i in range(N_PANELS):
        # longitude decreases left to right within a panel
        center = (LON_CENTER + LON_SPAN / 2 - (i + 0.5) * panel_width) % 360.0
        cutout = sqrt_ts.cutout(
            position=SkyCoord(center, 0.0, unit="deg", frame="galactic"),
            width=(panel_width * u.deg, LAT_SPAN * u.deg),
        )

        ax = fig.add_subplot(N_PANELS, 1, i + 1, projection=cutout.geom.wcs)
        image = ax.imshow(
            np.ma.masked_invalid(np.squeeze(cutout.data)),
            origin="lower",
            cmap=cmap,
            norm=norm,
            interpolation="nearest",
        )

        lon_axis, lat_axis = ax.coords[0], ax.coords[1]
        lon_axis.set_axislabel(
            "Galactic longitude (deg)" if i == N_PANELS - 1 else "", fontsize=10
        )
        lat_axis.set_axislabel("Galactic latitude (deg)", fontsize=9)
        lon_axis.set_ticks(spacing=10.0 * u.deg)
        lat_axis.set_ticks(spacing=2.0 * u.deg)
        lon_axis.set_ticklabel(fontsize=9)
        lat_axis.set_ticklabel(fontsize=9)

        draw_sources(ax, sources, center, panel_width / 2)

    depth = (
        f"sample of {n_used} of {n_available} observations"
        if n_used < n_available
        else f"all {n_used} observations"
    )
    fig.suptitle(
        "CTAO internal simulated dataset, Galactic plane\n"
        f"correlated significance, {ENERGY_MIN} to {ENERGY_MAX}, IRF background only\n"
        f"{depth}",
        fontsize=12,
        y=1.0,
    )

    cbar = fig.colorbar(
        image, ax=fig.axes, orientation="vertical", pad=0.015, shrink=0.55, aspect=30
    )
    cbar.set_label(r"$\sqrt{TS}$", fontsize=11)
    cbar.ax.tick_params(labelsize=9)

    fig.text(
        0.5,
        0.0,
        f"{len(sources)} of {n_covered} HGPS sources with CTAO coverage fall in these "
        f"panels, each circled and labeled.",
        ha="center",
        fontsize=9,
        color="0.35",
    )

    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUTPUT_PNG}  ({len(sources)} sources)")


def main():
    datastore = DataStore.from_dir(CTAO_DATA_PATH)

    geom, energy_true = build_geometry()
    obs_ids, n_available = select_observations(datastore)
    print(
        f"stacking {len(obs_ids)} of {n_available} observations, geom {geom.data_shape}"
    )

    stacked, n_used = stack_observations(datastore, obs_ids, geom, energy_true)
    sources, n_covered = load_sources()
    plot(significance_map(stacked), sources, n_covered, n_used, n_available)


if __name__ == "__main__":
    main()
