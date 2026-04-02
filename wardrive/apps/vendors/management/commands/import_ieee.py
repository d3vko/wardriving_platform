import csv
import io
import sys
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional, Tuple

import requests
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.regex import BLANK_RE, HEX_LINE_RE
from apps.vendors.models import Vendors

IEEE_OUI_TXT = "https://standards-oui.ieee.org/oui/oui.txt"
IEEE_OUI_CSV = "https://standards-oui.ieee.org/oui/oui.csv"

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)


@dataclass
class ParsedOui:
    registry: str  # "MA-L"
    assignment: str  # "286FB9"
    org_name: str
    org_address: str


def _http_get(url: str, timeout: int = 60) -> Tuple[int, bytes]:
    headers = {
        "User-Agent": UA,
        "Accept": "text/plain,text/csv,*/*;q=0.9",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Connection": "keep-alive",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    return resp.status_code, resp.content


def _normalize_assignment(hex_with_dashes: str) -> str:
    # "28-6F-B9" -> "286FB9"
    return hex_with_dashes.replace("-", "").upper()


def parse_oui_txt(content: str) -> Iterator[ParsedOui]:
    """
    Block parser for the classic format:
      XX-XX-XX (hex)  Organization Name
          Address line 1
          Address line 2
          ...
    """
    lines = content.splitlines()

    current_hex: Optional[str] = None
    current_name: Optional[str] = None
    addr_lines: list[str] = []

    def flush():
        nonlocal current_hex, current_name, addr_lines
        if current_hex and current_name:
            yield ParsedOui(
                registry="MA-L",
                assignment=_normalize_assignment(current_hex),
                org_name=current_name.strip(),
                org_address="\n".join([l.rstrip() for l in addr_lines]).strip(),
            )
        current_hex = None
        current_name = None
        addr_lines = []

    for line in lines:
        m = HEX_LINE_RE.match(line)
        if m:
            # If we were in a block, close it
            yield from flush()

            current_hex = m.group(1)
            current_name = m.group(2)
            addr_lines = []
            continue

        # Inside a block: capture address lines until blank line
        if current_hex and current_name:
            if BLANK_RE.match(line):
                yield from flush()
            else:
                # oui.txt often has indented lines; preserve them
                addr_lines.append(line.strip("\r"))

    # Last block
    yield from flush()


def parse_oui_csv(content: str) -> Iterator[ParsedOui]:
    """
    Official headers:
      Registry,Assignment,Organization Name,Organization Address
    """
    # CSV may contain quotes and commas in the address field
    f = io.StringIO(content)
    reader = csv.DictReader(f)
    # Soft header validation
    required = {"Registry", "Assignment", "Organization Name", "Organization Address"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError(
            f"CSV: missing columns: {sorted(missing)}; headers={reader.fieldnames}"
        )

    for row in reader:
        registry = (row.get("Registry") or "").strip()
        assignment = (row.get("Assignment") or "").strip().replace("-", "").upper()
        org = (row.get("Organization Name") or "").strip()
        addr = (row.get("Organization Address") or "").strip()

        # This command focuses on MA-L (OUI 24-bit)
        if registry != "MA-L":
            continue

        if not assignment or not org:
            continue

        yield ParsedOui(
            registry="MA-L",
            assignment=assignment,
            org_name=org,
            org_address=addr,
        )


def registry_to_prefix_bits(registry: str) -> int:
    # For this case: MA-L (OUI 24-bit)
    if registry == "MA-L":
        return 24
    # If you add other registries later: MA-M -> 28, MA-S -> 36, etc.
    return 24


class Command(BaseCommand):
    help = "Import IEEE OUI (MA-L) from oui.txt (fallback to oui.csv) into the Vendors table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            default=IEEE_OUI_TXT,
            help="Source URL (default: IEEE oui.txt).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Batch size for bulk_create.",
        )
        parser.add_argument(
            "--use-csv",
            action="store_true",
            help="Force use of CSV (oui.csv) even if txt responds.",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete MA-L records before importing (use with care).",
        )

    def handle(self, *args, **opts):
        url = opts["url"]
        batch_size = opts["batch_size"]
        use_csv = opts["use_csv"]
        truncate = opts["truncate"]

        self.stdout.write(self.style.NOTICE(f"📥 Downloading: {url}"))

        parsed_iter: Iterable[ParsedOui]

        if use_csv:
            status, raw = _http_get(IEEE_OUI_CSV)
            if status != 200:
                raise RuntimeError(f"CSV download failed: status={status}")
            content = raw.decode("utf-8", errors="replace")
            parsed_iter = parse_oui_csv(content)
            source_url = IEEE_OUI_CSV
        else:
            status, raw = _http_get(url)

            # Common block: 418/403. Automatic fallback to CSV.
            if status in (403, 418) or status != 200:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  TXT not available (status={status}). Fallback to CSV: {IEEE_OUI_CSV}"
                    )
                )
                status2, raw2 = _http_get(IEEE_OUI_CSV)
                if status2 != 200:
                    raise RuntimeError(
                        f"Fallback CSV download failed: txt_status={status} csv_status={status2}"
                    )
                content = raw2.decode("utf-8", errors="replace")
                parsed_iter = parse_oui_csv(content)
                source_url = IEEE_OUI_CSV
            else:
                content = raw.decode("utf-8", errors="replace")
                parsed_iter = parse_oui_txt(content)
                source_url = url

        if truncate:
            self.stdout.write(self.style.WARNING("🧨 Truncating MA-L rows..."))
            Vendors.objects.filter(registry="MA-L").delete()

        created_total = 0
        seen_total = 0

        buffer: list[Vendors] = []

        @transaction.atomic
        def flush_batch(batch: list[Vendors]) -> int:
            # ignore_conflicts=True avoids failing on UniqueConstraint
            Vendors.objects.bulk_create(
                batch, ignore_conflicts=True, batch_size=len(batch)
            )
            return len(batch)

        for item in parsed_iter:
            seen_total += 1

            prefix_bits = registry_to_prefix_bits(item.registry)
            obj = Vendors(
                registry=item.registry,
                assignment=item.assignment,
                prefix_bits=prefix_bits,
                normalized_prefix=item.assignment,
                organization_name=item.org_name,
                organization_address=item.org_address,
                source="ieee",
                source_url=source_url,
            )
            buffer.append(obj)

            if len(buffer) >= batch_size:
                created_total += flush_batch(buffer)
                self.stdout.write(
                    f"✅ batch insert: {created_total} (seen={seen_total})"
                )
                buffer = []

        if buffer:
            created_total += flush_batch(buffer)

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 Import finished. insert_attempts={created_total} seen={seen_total} source={source_url}"
            )
        )
