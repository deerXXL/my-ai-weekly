from app.services.file_writer import write_json
from app.services.report_builder import build_report


def save_report(cards, items=None):
    """Backward-compatible wrapper that writes the standard weekly JSON file."""
    report = build_report(items=items or [], signals=cards)
    write_json(report)
    return report
