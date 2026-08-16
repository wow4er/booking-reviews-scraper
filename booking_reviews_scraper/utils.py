from urllib.parse import urlparse


def load_proxies(path: str) -> list[str]:
    """
    Reads a proxies file, one proxy per line, format host:port or user:pass@host:port.
    Blank lines and lines starting with # are skipped.
    Raises FileNotFoundError if the path doesn't exist, ValueError if the file has no usable proxies.
    """
    proxies = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            proxies.append(line)

    if not proxies:
        raise ValueError(f"No proxies found in {path}, add at least one proxy per line")

    return proxies


def clean_url(raw_url: str) -> str:
    """
    Strips query params and trailing junk from a booking.com hotel URL,
    keeping only scheme, host and path.
    """
    parsed = urlparse(raw_url.strip())
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
