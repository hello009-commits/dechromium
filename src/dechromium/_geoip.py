"""GeoIP database manager — maps proxy IPs to geographic data."""

from __future__ import annotations

import dataclasses
import gzip
import json
import logging
import os
import socket
import tempfile
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_META_FILE = ".geoip_meta.json"
_DB_NAME = "dbip-city-lite.mmdb"
_STALE_DAYS = 35


@dataclasses.dataclass(frozen=True, slots=True)
class GeoInfo:
    """Geographic information for an IP address."""

    country_code: str  # "US", "JP", "DE"
    timezone: str  # "America/New_York"
    latitude: float  # 40.7128
    longitude: float  # -74.0060
    city: str  # "New York"


def download(data_dir: Path, *, progress: bool = True) -> Path:
    """Download DB-IP City Lite MMDB to ``{data_dir}/data/geoip/``.

    Tries current month first, falls back to previous month.
    Uses atomic write via tmpfile + ``os.replace()``.

    Returns:
        Path to the downloaded MMDB file.
    """
    dest_dir = data_dir / "data" / "geoip"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / _DB_NAME

    now = datetime.now(UTC)
    candidates = [
        now.strftime("%Y-%m"),
        (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m"),
    ]

    last_err: Exception | None = None
    for month in candidates:
        url = f"https://download.db-ip.com/free/dbip-city-lite-{month}.mmdb.gz"
        if progress:
            print(f"  Downloading GeoIP database ({month})...")

        try:
            req = Request(url, headers={"User-Agent": "dechromium"})
            with urlopen(req, timeout=60) as resp:
                compressed = resp.read()
        except HTTPError as exc:
            last_err = exc
            if progress:
                print(f"  {month} not available, trying previous month...")
            continue

        data = gzip.decompress(compressed)

        # Atomic write
        fd, tmp_path = tempfile.mkstemp(dir=dest_dir, suffix=".mmdb.tmp")
        try:
            os.write(fd, data)
            os.close(fd)
            os.replace(tmp_path, dest)
        except BaseException:
            os.close(fd) if not os.get_inheritable(fd) else None
            with _suppress():
                os.unlink(tmp_path)
            raise

        # Write metadata
        meta = {"downloaded_at": now.isoformat(), "month": month, "size": len(data)}
        (dest_dir / _META_FILE).write_text(json.dumps(meta, indent=2) + "\n")

        if progress:
            print(f"  GeoIP database saved ({len(data) / 1024 / 1024:.1f} MB)")
        return dest

    msg = f"Failed to download GeoIP database: {last_err}"
    raise OSError(msg)


def get_reader(data_dir: Path):
    """Get a maxminddb Reader, downloading the database if missing.

    Warns if the database is older than 35 days.

    Returns:
        ``maxminddb.Reader`` instance.
    """
    import maxminddb

    db_path = data_dir / "data" / "geoip" / _DB_NAME
    if not db_path.exists():
        download(data_dir, progress=False)

    # Check staleness
    meta_path = db_path.parent / _META_FILE
    if meta_path.exists():
        with _suppress():
            meta = json.loads(meta_path.read_text())
            downloaded = datetime.fromisoformat(meta["downloaded_at"])
            age = datetime.now(UTC) - downloaded
            if age > timedelta(days=_STALE_DAYS):
                warnings.warn(
                    f"GeoIP database is {age.days} days old. "
                    "Run `dechromium download-geoip` to update.",
                    UserWarning,
                    stacklevel=2,
                )

    return maxminddb.open_database(str(db_path))


def lookup(ip: str, data_dir: Path) -> GeoInfo | None:
    """Look up geographic info for an IP address.

    Returns:
        ``GeoInfo`` or ``None`` if the IP is not found.
    """
    try:
        reader = get_reader(data_dir)
    except Exception:
        logger.debug("GeoIP lookup failed: could not open database", exc_info=True)
        return None

    try:
        record = reader.get(ip)
    except Exception:
        logger.debug("GeoIP lookup failed for %s", ip, exc_info=True)
        return None

    if not record or not isinstance(record, dict):
        return None

    country = record.get("country", {})
    country_code = country.get("iso_code", "")
    if not country_code:
        return None

    location = record.get("location", {})
    timezone = location.get("time_zone", "")
    latitude = location.get("latitude")
    longitude = location.get("longitude")

    if latitude is None or longitude is None:
        return None

    city_data = record.get("city", {})
    names = city_data.get("names", {})
    city = names.get("en", "")

    return GeoInfo(
        country_code=country_code,
        timezone=timezone,
        latitude=float(latitude),
        longitude=float(longitude),
        city=city,
    )


def resolve_proxy_ip(proxy: str) -> str:
    """Extract hostname from proxy URL and resolve to IP address.

    Args:
        proxy: Proxy URL like ``socks5://host:1080`` or ``http://user:pass@host:8080``.

    Returns:
        Resolved IP address string.

    Raises:
        OSError: If DNS resolution fails.
    """
    parsed = urlparse(proxy)
    hostname = parsed.hostname
    if not hostname:
        msg = f"Cannot extract hostname from proxy URL: {proxy}"
        raise ValueError(msg)

    # Fast path: already an IP address
    try:
        socket.inet_pton(socket.AF_INET, hostname)
        return hostname
    except OSError:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, hostname)
        return hostname
    except OSError:
        pass

    # DNS resolution
    results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    if not results:
        msg = f"Could not resolve proxy hostname: {hostname}"
        raise OSError(msg)

    return results[0][4][0]


class _suppress:
    """Minimal context manager that suppresses all exceptions."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return True
