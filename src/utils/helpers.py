import os
import platform
import subprocess
from datetime import datetime, timezone, timedelta
from src.utils.constants import TYPE_SHORT_LABELS


def format_datetime(iso_string: str) -> str:
    """Format ISO datetime string to Brazilian date format (SP timezone - UTC-3)."""
    if not iso_string:
        return "—"
    try:
        # Try multiple parsing approaches
        dt = None
        iso_clean = iso_string.strip()
        
        # Approach 1: Handle 'Z' (UTC) by replacing with +00:00
        if iso_clean.endswith("Z"):
            modified = iso_clean[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(modified)
            except ValueError:
                pass
        
        # Approach 2: Try with fractional seconds
        if not dt and "." in iso_clean:
            try:
                dt = datetime.fromisoformat(iso_clean)
            except ValueError:
                # Remove fractional part
                clean_no_millis = iso_clean.split(".")[0]
                if "Z" in iso_clean:
                    clean_no_millis = clean_no_millis.replace("Z", "+00:00")
                try:
                    dt = datetime.fromisoformat(clean_no_millis)
                except ValueError:
                    pass
        
        # Approach 3: Naive datetime, assume UTC
        if not dt:
            try:
                clean = iso_clean.split(".")[0].replace("Z", "")
                dt = datetime.fromisoformat(clean)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        
        # If still no dt, return original
        if not dt:
            return iso_string or "—"
        
        # Convert to Brazil/Sao_Paulo timezone (UTC-3)
        # First, ensure dt is timezone-aware (UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Try zoneinfo/pytz first, then fall back to manual -3 hours
        dt_brazil = None
        try:
            try:
                from zoneinfo import ZoneInfo
                brazil_tz = ZoneInfo("America/Sao_Paulo")
                dt_brazil = dt.astimezone(brazil_tz)
            except ImportError:
                from pytz import timezone as pytz_timezone
                brazil_tz = pytz_timezone("America/Sao_Paulo")
                dt_brazil = dt.astimezone(brazil_tz)
        except Exception:
            # Fallback: manual subtraction of 3 hours (UTC-3)
            dt_brazil = dt - timedelta(hours=3)
            
        return dt_brazil.strftime("%d/%m/%Y %H:%M")
    except (ValueError, AttributeError):
        return iso_string or "—"


def format_operation_type(op_type: str) -> str:
    """Return a short human-readable label for an operation type key."""
    return TYPE_SHORT_LABELS.get(op_type, op_type)


def get_downloads_path() -> str:
    """Return the user's Downloads folder (or home dir as fallback)."""
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    return downloads if os.path.isdir(downloads) else os.path.expanduser("~")


def get_pdf_save_path(operation_id: int, operation_name: str) -> str:
    """Build a default PDF file path inside the Downloads folder."""
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in operation_name)
    safe_name = safe_name.strip().replace(" ", "_")
    filename = f"operacao_{operation_id}_{safe_name}.pdf"
    return os.path.join(get_downloads_path(), filename)


def open_file(filepath: str) -> None:
    """Open a file with the default system application."""
    try:
        if platform.system() == "Windows":
            os.startfile(filepath)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.run(["open", filepath], check=False)
        else:
            subprocess.run(["xdg-open", filepath], check=False)
    except Exception:
        pass


def center_window(window, width: int, height: int) -> None:
    """Center a root window on the screen."""
    window.update_idletasks()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def center_toplevel(toplevel, width: int, height: int, parent=None) -> None:
    """Center a Toplevel relative to its parent window (or the screen)."""
    toplevel.update_idletasks()
    if parent:
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = max(0, px + (pw - width) // 2)
        y = max(0, py + (ph - height) // 2)
    else:
        sw = toplevel.winfo_screenwidth()
        sh = toplevel.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
    toplevel.geometry(f"{width}x{height}+{x}+{y}")


def truncate_text(text: str, max_len: int = 40) -> str:
    """Truncate a string and add ellipsis if needed."""
    if not text:
        return "—"
    return text if len(text) <= max_len else text[:max_len - 1] + "…"


def list_to_bullet(items: list[str]) -> str:
    """Convert a list of strings into a bullet-point string."""
    if not items:
        return "Nenhum"
    return "\n".join(f"• {item.capitalize()}" for item in items)
