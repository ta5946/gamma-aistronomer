"""Download the HGPS catalogue and paper, and build sources.csv from the catalogue.

cd src && python match_ctao_sources.py
"""

import csv
import os
import urllib.request

from astropy.coordinates import SkyCoord
from astropy.table import Table
import astropy.units as u
from dotenv import load_dotenv

load_dotenv()

HGPS_CATALOG_FITS = "../data/cache/hgps/hgps_catalog_v1.fits.gz"
HGPS_CATALOG_URL = (
    "https://www.mpi-hd.mpg.de/hfm/HESS/hgps/data/hgps_catalog_v1.fits.gz"
)
HGPS_PAPER_PDF = "../data/cache/hgps/1804.02432.pdf"
HGPS_PAPER_URL = "https://arxiv.org/pdf/1804.02432"
HGPS_SOURCES_CSV = "../data/cache/hgps/sources.csv"

# Prod5 IRFs are valid up to 6 deg offset, but sensitivity degrades before that. Tightened
# below 2.5 deg (env_and_dataset_check.ipynb) and below the 6 deg edge.
OFFSET_YES_MAX_DEG = 2.0
OFFSET_MAYBE_MAX_DEG = 5.0

# download the HGPS catalogue and paper into data/cache/hgps/ if not already there
for path, url in [
    (HGPS_CATALOG_FITS, HGPS_CATALOG_URL),
    (HGPS_PAPER_PDF, HGPS_PAPER_URL),
]:
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, path)

# the catalogue and paper don't need the CTAO data, the pointing match below does
if not os.environ.get("CTAO_DATA_PATH"):
    raise SystemExit(
        "HGPS catalogue and paper ready. Set CTAO_DATA_PATH in .env to build sources.csv."
    )
CTAO_OBS_INDEX = f"{os.environ['CTAO_DATA_PATH']}/obs-index.fits.gz"

# trim the HGPS catalogue to the columns we use. `id` is ours, a 1-based catalogue index.
# HGPS masks some fields (e.g. Size for point sources), kept here as 0.0
catalog = Table.read(HGPS_CATALOG_FITS, hdu="HGPS_SOURCES").filled(0.0)
sources = []
for i, s in enumerate(catalog, start=1):
    if s["Spectral_Model"] == "ECPL":
        flux_1tev_diff = s["Flux_Spec_ECPL_Diff_1TeV"]
    else:
        flux_1tev_diff = s["Flux_Spec_PL_Diff_1TeV"]
    sources.append(
        {
            "id": i,
            "name": s["Source_Name"],
            "source_class": s["Source_Class"],
            "ra_j2000": float(s["RAJ2000"]),
            "dec_j2000": float(s["DEJ2000"]),
            "glon": float(s["GLON"]),
            "glat": float(s["GLAT"]),
            "spatial_model": s["Spatial_Model"],
            "size_deg": float(s["Size"]),
            "rspec_deg": float(s["RSpec"]),
            "spectral_model": s["Spectral_Model"],
            "flux_1tev_diff": float(flux_1tev_diff),
        }
    )

source_coords = SkyCoord(
    ra=[s["ra_j2000"] for s in sources] * u.deg,
    dec=[s["dec_j2000"] for s in sources] * u.deg,
)

obs_table = Table.read(CTAO_OBS_INDEX)
pointing_coords = SkyCoord(ra=obs_table["RA_PNT"], dec=obs_table["DEC_PNT"])

# nearest observation pointing per source
_, sep2d, _ = source_coords.match_to_catalog_sky(pointing_coords)
offsets_deg = sep2d.to(u.deg).value


def classify(offset):
    if offset <= OFFSET_YES_MAX_DEG:
        return "yes"
    elif offset <= OFFSET_MAYBE_MAX_DEG:
        return "maybe"
    return "no"


counts = {"yes": 0, "maybe": 0, "no": 0}

for source, offset in zip(sources, offsets_deg):
    in_ctao = classify(offset)
    source["in_ctao"] = in_ctao
    source["min_offset_deg"] = float(offset)
    counts[in_ctao] += 1

    print(
        f"{source['name']:<20} in_ctao={in_ctao:<6} min_offset_deg={source['min_offset_deg']:.5f}"
    )

print()
print(
    f"total: {len(sources)} sources -> yes={counts['yes']}, maybe={counts['maybe']}, no={counts['no']}"
)

# in_ctao before min_offset_deg
fieldnames = [c for c in sources[0].keys() if c not in ("in_ctao", "min_offset_deg")]
fieldnames += ["in_ctao", "min_offset_deg"]

with open(HGPS_SOURCES_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(sources)
