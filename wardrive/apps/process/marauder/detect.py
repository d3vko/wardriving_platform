"""
Dialect detection for Marauder/Flipper log files.
Re-exports detect_dialect from the shared _wigle_canonical pipeline.
"""

from apps.process._wigle_canonical.detect import detect_dialect

__all__ = ["detect_dialect"]
