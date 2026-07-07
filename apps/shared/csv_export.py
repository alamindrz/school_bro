"""
Shared CSV Export Utilities

Eliminates the duplicated CSV-response boilerplate found in:
  - students/views/ajax.py (export_students, bulk_action)
  - staffs/views/staff.py  (ExportStaffView)
  - finance/views/staff.py (ExportTransactionsView)
  - attendance/views/staff.py (ExportReportView)
  - audit/views.py (ExportAuditView)

Usage:
    from apps.shared.csv_export import build_csv_response

    def get(self, request):
        rows = MySelector.list_items()
        return build_csv_response(
            filename="items",
            headers=["ID", "Name", "Status"],
            rows=[[r["id"], r["name"], r["status"]] for r in rows],
        )
"""

import csv
from datetime import date
from typing import Iterable, Sequence

from django.http import HttpResponse


def build_csv_response(
    *,
    filename: str,
    headers: Sequence[str],
    rows: Iterable[Sequence],
    date_suffix: bool = True,
) -> HttpResponse:
    """
    Build an ``HttpResponse`` containing a CSV file download.

    Args:
        filename:    Base filename (without extension). e.g. ``"staff"``.
        headers:     Column header row.
        rows:        Iterable of row sequences (lists/tuples).
        date_suffix: Append today's date to the filename (default True).

    Returns:
        ``HttpResponse`` with ``Content-Type: text/csv`` and a
        ``Content-Disposition`` header triggering a browser download.
    """
    if date_suffix:
        filename = f"{filename}_{date.today().isoformat()}"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'

    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    return response


def build_csv_response_from_dicts(
    *,
    filename: str,
    headers: Sequence[str],
    key_order: Sequence[str],
    rows: Iterable[dict],
    date_suffix: bool = True,
    default: str = "",
) -> HttpResponse:
    """
    Convenience wrapper when rows are dicts (common with selector results).

    Args:
        filename:   Base filename (without extension).
        headers:    Column header labels.
        key_order:  Dict keys in the order that columns should appear.
        rows:       Iterable of dicts.
        date_suffix: Append today's date to the filename (default True).
        default:    Default value for missing keys.
    """
    return build_csv_response(
        filename=filename,
        headers=headers,
        rows=([row.get(k, default) for k in key_order] for row in rows),
        date_suffix=date_suffix,
    )
