"""All-sky map of the internal CTAO dataset, in the style of the Fermi all-sky images.

Stacks every CTAO observation into one Aitoff projection centered on the Galactic
center, and plots the correlated significance. Counts and background accumulate
directly into whole-sky arrays instead of a MapDataset, which keeps memory flat
regardless of how many observations run.

The data is simulated, not real CTAO observations. Background comes from the IRF alone,
so this is an overview map rather than a basis for source detection or flux measurement.

    cd src && python plot_ctao_allsky.py
"""

import os
import time

import matplotlib

matplotlib.use("Agg")  # headless

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.nddata.utils import NoOverlapError
from astropy.visualization.wcsaxes.frame import EllipticalFrame
from matplotlib.colors import PowerNorm
from scipy import ndimage

from dotenv import load_dotenv

from gammapy.data import DataStore
from gammapy.datasets import MapDataset
from gammapy.makers import MapDatasetMaker, SafeMaskMaker
from gammapy.maps import Map, MapAxis, WcsGeom
from gammapy.stats import CashCountsStatistic

load_dotenv()

# observations to stack, sampled evenly if the dataset has more
N_OBSERVATIONS = 10000

CTAO_DATA_PATH = os.environ.get("CTAO_DATA_PATH")
if not CTAO_DATA_PATH:
    raise SystemExit("Set CTAO_DATA_PATH in .env to the DL3 DataStore, and run from src/.")
OUTPUT_PNG = "../plot/ctao_allsky.png"

# whole sky in Aitoff, Galactic center at the middle, with this pixel size in deg
BINSZ = 0.1

ENERGY_MIN, ENERGY_MAX = "1 TeV", "100 TeV"

# analysis cut on the offset from the pointing, well inside the 6 deg Prod5 IRF edge
OFFSET_MAX_DEG = 2.5
# generous, because Aitoff stretches longitude away from the center
CUTOUT_WIDTH_DEG = 2 * OFFSET_MAX_DEG + 3.0

# smoothing radius of the significance map
CORRELATION_RADIUS_DEG = 0.2
# color scale saturates here
VMAX = 25.0


def build_geometry():
    """Reference geometry and true-energy axis."""
    energy = MapAxis.from_energy_bounds(ENERGY_MIN, ENERGY_MAX, nbin=1)
    energy_true = MapAxis.from_energy_bounds(
        "0.5 TeV", "200 TeV", nbin=4, name="energy_true"
    )
    geom = WcsGeom.create(
        skydir=SkyCoord(0.0, 0.0, unit="deg", frame="galactic"),
        frame="galactic",
        proj="AIT",
        binsz=BINSZ,
        width=(360.0, 180.0),
        axes=[energy],
    )
    return geom, energy_true


def select_observations(datastore):
    """Every observation in the dataset, sampled evenly if capped."""
    table = datastore.obs_table
    obs_ids = np.asarray(table["OBS_ID"])
    livetime_h = np.asarray(table["LIVETIME"]) / 3600.0
    n_available = len(obs_ids)

    if n_available > N_OBSERVATIONS:
        # sorted by longitude, so the sample is spread over the sky
        pointings = SkyCoord(table["RA_PNT"], table["DEC_PNT"]).galactic
        order = np.argsort(pointings.l.deg)
        step = np.linspace(0, n_available - 1, N_OBSERVATIONS).astype(int)
        keep = order[step]
        return obs_ids[keep], n_available, livetime_h[keep].sum()

    return obs_ids, n_available, livetime_h.sum()


def stack_observations(datastore, obs_ids, geom, energy_true):
    """Add each observation into whole-sky counts and background maps."""
    counts = Map.from_geom(geom, dtype="float32")
    background = Map.from_geom(geom, dtype="float32")
    maker = MapDatasetMaker(selection=["counts", "background"])
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

        # drop everything outside the valid offset, then add into the whole-sky maps
        dataset.counts.data *= dataset.mask_safe.data
        dataset.background.data *= dataset.mask_safe.data
        counts.stack(dataset.counts)
        background.stack(dataset.background)
        n_used += 1

        del dataset, obs

        if i % 250 == 0 or i == len(obs_ids):
            print(f"  {i}/{len(obs_ids)}, {(time.time() - start) / 60:.1f} min")

    if n_skipped:
        print(f"  skipped {n_skipped} with no overlap")

    return counts, background, n_used


def significance_map(counts, background):
    """Correlated sqrt(TS), blank where nothing was observed."""
    radius_pix = CORRELATION_RADIUS_DEG / BINSZ
    size = int(2 * radius_pix) + 1
    y, x = np.mgrid[:size, :size] - (size - 1) / 2
    disk = (x**2 + y**2 <= radius_pix**2).astype("float32")

    n_on = ndimage.convolve(counts.data[0], disk, mode="constant")
    mu_bkg = ndimage.convolve(background.data[0], disk, mode="constant")

    with np.errstate(invalid="ignore", divide="ignore"):
        sqrt_ts = CashCountsStatistic(n_on, mu_bkg).sqrt_ts

    sqrt_ts[mu_bkg <= 0] = np.nan  # never observed
    return Map.from_geom(counts.geom.to_image(), data=sqrt_ts)


def plot(sqrt_ts, n_used, n_available, livetime_h):
    """One Aitoff panel covering the whole sky."""
    norm = PowerNorm(gamma=0.5, vmin=0.0, vmax=VMAX)  # sqrt stretch
    cmap = plt.get_cmap("afmhot").copy()
    cmap.set_bad("black")  # unobserved sky

    fig = plt.figure(figsize=(16, 8.2))
    ax = fig.add_subplot(projection=sqrt_ts.geom.wcs, frame_class=EllipticalFrame)
    fig.subplots_adjust(left=0.01, right=0.88, top=0.9, bottom=0.08)
    ax.set_facecolor("black")
    image = ax.imshow(
        np.ma.masked_invalid(sqrt_ts.data),
        origin="lower",
        cmap=cmap,
        norm=norm,
        interpolation="nearest",
    )

    # the elliptical frame has no side to anchor axis labels to, so only tick
    # numbers are shown, in white to read against the black background inside
    lon_axis, lat_axis = ax.coords[0], ax.coords[1]
    lon_axis.set_ticks(spacing=30.0 * u.deg)
    lat_axis.set_ticks(spacing=30.0 * u.deg)
    lon_axis.set_ticklabel(fontsize=8, color="white")
    lat_axis.set_ticklabel(fontsize=8, color="white")
    lat_axis.set_ticks_position("all")
    lat_axis.set_ticklabel_position("all")
    ax.coords.grid(color="white", alpha=0.25, linestyle="dotted")

    depth = (
        f"sample of {n_used} of {n_available} observations"
        if n_used < n_available
        else f"all {n_used} observations"
    )
    fig.suptitle(
        "CTAO internal simulated dataset, whole sky, correlated significance\n"
        f"{ENERGY_MIN} to {ENERGY_MAX}, IRF background only, {depth}, "
        f"{livetime_h:.0f} h livetime",
        fontsize=12,
    )

    # a fixed colorbar axes, since fig.colorbar(ax=ax) would shrink ax on top of
    # the margins already reserved by subplots_adjust above
    cax = fig.add_axes([0.89, 0.25, 0.015, 0.5])
    cbar = fig.colorbar(image, cax=cax)
    cbar.set_label(r"$\sqrt{TS}$", fontsize=11)
    cbar.ax.tick_params(labelsize=9)

    fig.text(
        0.5,
        0.02,
        "Black is sky the observing plan never visited. Livetime varies by a factor of "
        "tens across fields.",
        ha="center",
        fontsize=9,
        color="0.35",
    )

    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)

    # bbox_inches="tight" miscrops this combination of elliptical frame and
    # colorbar, cutting off part of the ellipse, so the plain figure is saved
    fig.savefig(OUTPUT_PNG, dpi=150)
    plt.close(fig)
    print(f"wrote {OUTPUT_PNG}")


def main():
    datastore = DataStore.from_dir(CTAO_DATA_PATH)

    geom, energy_true = build_geometry()
    obs_ids, n_available, livetime_h = select_observations(datastore)
    print(
        f"stacking {len(obs_ids)} of {n_available} observations, geom {geom.data_shape}"
    )

    counts, background, n_used = stack_observations(
        datastore, obs_ids, geom, energy_true
    )
    plot(significance_map(counts, background), n_used, n_available, livetime_h)


if __name__ == "__main__":
    main()
