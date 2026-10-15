
#!/usr/bin/env python3
# ============================================================
# FIREWALL BREAKER - VEHICLE INFO
# Created by: Gunja Rahul
# YouTube: Gunja Rahul
# Version: 2.1 PRO
# ============================================================

import sys
import os
import json
import time
import re
import hashlib
import argparse
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.align import Align

API_BASE = "https://vehicleinfobyterabaap.vercel.app/lookup"
VERSION = "2.1 PRO"
CACHE_TTL = 3600
TIMEOUT = 20

RESULTS_DIR = "results"
LOGS_DIR = "logs"
CACHE_DIR = "cache"

console = Console()


def ensure_dirs():
    for directory in (RESULTS_DIR, LOGS_DIR, CACHE_DIR):
        os.makedirs(directory, exist_ok=True)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def log(message):
    """Log operational events without logging registration numbers."""
    try:
        path = os.path.join(LOGS_DIR, "firewall.log")
        timestamp = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )
        with open(path, "a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass


def normalize_rc(rc):
    """Normalize spaces and hyphens in a registration number."""
    return re.sub(r"[\s-]+", "", (rc or "").strip().upper())


def validate_rc(rc):
    """Basic format validation, not proof of a valid registration."""
    return bool(
        rc
        and 6 <= len(rc) <= 15
        and re.fullmatch(r"[A-Z0-9]+", rc)
        and re.search(r"[A-Z]", rc)
        and re.search(r"\d", rc)
    )


def get_rc_input():
    return normalize_rc(
        console.input(
            "\n[bold cyan]Enter vehicle RC number: [/bold cyan]"
        )
    )


def cache_path(rc):
    # Hash the filename so the registration is not visible in the path.
    digest = hashlib.sha256(rc.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{digest}.json")


def load_cache(rc):
    path = cache_path(rc)

    try:
        with open(path, "r", encoding="utf-8") as file:
            entry = json.load(file)

        if not isinstance(entry, dict):
            return None

        saved_at = entry.get("_cached_at")
        data = entry.get("data")

        if not isinstance(saved_at, (int, float)):
            return None

        if time.time() - saved_at > CACHE_TTL:
            return None

        if not isinstance(data, dict) or "error" in data:
            return None

        return data

    except (OSError, ValueError, TypeError):
        return None


def save_cache(rc, data):
    if not isinstance(data, dict) or "error" in data:
        return

    path = cache_path(rc)
    temporary_path = path + ".tmp"

    try:
        with open(temporary_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "_cached_at": time.time(),
                    "data": data,
                },
                file,
                indent=2,
                ensure_ascii=False,
            )

        os.replace(temporary_path, path)

    except (OSError, TypeError, ValueError) as error:
        log(f"Cache save failed: {type(error).__name__}")
        try:
            os.remove(temporary_path)
        except OSError:
            pass


def banner():
    console.rule()

    console.print(
        Align.center(
            f"[bold red]FIREWALL BREAKER[/bold red]"
            f" • [yellow]{VERSION}[/yellow]"
        )
    )

    console.print(
        Align.center(
            "[green]Created by: G.Rahul • YouTube: Gunja Rahul[/green]"
        )
    )

    console.rule()

    console.print(
        Panel(
            "[bold white]Authorized vehicle-information lookups only[/bold white]\n"
            "Use a legitimate data source and respect privacy.",
            border_style="yellow",
            expand=False,
        )
    )


def fetch_vehicle_data(rc, refresh=False):
    if not refresh:
        cached = load_cache(rc)
        if cached is not None:
            return cached, True

    start = time.monotonic()
    log("Vehicle lookup started")

    try:
        response = requests.get(
            API_BASE,
            params={"rc": rc},
            timeout=TIMEOUT,
            headers={
                "Accept": "application/json",
                "User-Agent": "FirewallBreaker/2.1",
            },
        )

    except requests.exceptions.Timeout:
        return {
            "error": "The API request timed out.",
            "_status": "TIMEOUT",
        }, False

    except requests.exceptions.ConnectionError:
        return {
            "error": "Connection failed. Check your internet and API availability.",
            "_status": "CONNECTION_ERROR",
        }, False

    except requests.exceptions.RequestException as error:
        log(f"Request failed: {type(error).__name__}")
        return {
            "error": "The HTTP request failed.",
            "_status": "REQUEST_ERROR",
        }, False

    elapsed_ms = round((time.monotonic() - start) * 1000, 2)
    status = response.status_code

    if status != 200:
        messages = {
            400: "The API rejected the request.",
            401: "The API requires authentication.",
            403: "The API denied access.",
            404: "No record was returned, or the endpoint was not found.",
            429: "Rate limit reached. Try again later.",
        }

        if status >= 500:
            message = "The API server encountered an error."
        else:
            message = messages.get(
                status, f"Unexpected HTTP status: {status}"
            )

        log(f"Lookup failed: HTTP {status}")

        return {
            "error": message,
            "_status": status,
            "_api_time": elapsed_ms,
        }, False

    try:
        data = response.json()
    except ValueError:
        return {
            "error": "The API returned invalid JSON.",
            "_status": status,
            "_api_time": elapsed_ms,
        }, False

    if not isinstance(data, dict):
        data = {"vehicle_data": data}

    if "error" in data:
        return {
            "error": str(data["error"]),
            "_status": status,
            "_api_time": elapsed_ms,
        }, False

    data["_status"] = status
    data["_api_time"] = elapsed_ms

    save_cache(rc, data)
    log("Lookup completed")

    return data, False


def export_json(rc, data):
    # The validated RC contains only letters and digits.
    path = os.path.join(RESULTS_DIR, f"{rc}.json")
    temporary_path = path + ".tmp"

    try:
        with open(temporary_path, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )

        os.replace(temporary_path, path)
        return path

    except (OSError, TypeError, ValueError) as error:
        log(f"Export failed: {type(error).__name__}")

        try:
            os.remove(temporary_path)
        except OSError:
            pass

        return None


def print_results(rc, data, from_cache):
    if "error" in data:
        console.print(
            Panel(
                f"[bold red]{data['error']}[/bold red]\n\n"
                f"Status: {data.get('_status', 'ERROR')}\n"
                f"Response time: {data.get('_api_time', 'N/A')} ms",
                title="Lookup Failed",
                border_style="red",
            )
        )
        return

    console.print(
        Panel(
            f"[green]HTTP Status: {data.get('_status', 'N/A')}[/green]\n"
            f"Cached: {'YES' if from_cache else 'NO'}\n"
            f"Response time: {data.get('_api_time', 'N/A')} ms",
            title="API Status",
            border_style="green",
        )
    )

    table = Table(
        title=f"Vehicle Information — {rc}",
        box=box.ROUNDED,
        show_lines=True,
    )

    table.add_column("Field", style="bold cyan")
    table.add_column("Value", overflow="fold")

    for key, value in data.items():
        if key.startswith("_"):
            continue

        if isinstance(value, (dict, list)):
            value = json.dumps(
                value,
                indent=2,
                ensure_ascii=False,
            )

        table.add_row(str(key).replace("_", " ").title(), str(value))

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Firewall Breaker PRO — authorized vehicle lookup"
    )
    parser.add_argument(
        "--rc",
        help="Vehicle registration number, e.g. TS05ED5022",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Skip the cache and query the API again",
    )
    args = parser.parse_args()

    ensure_dirs()
    clear_screen()
    banner()

    rc = normalize_rc(args.rc) if args.rc else get_rc_input()

    if not validate_rc(rc):
        console.print(
            "[bold red]Invalid registration format.[/bold red]\n"
            "[yellow]Example: TS05ED5022[/yellow]"
        )
        sys.exit(1)

    console.print(f"\n[cyan]Searching:[/cyan] [bold green]{rc}[/bold green]")

    data, from_cache = fetch_vehicle_data(
        rc,
        refresh=args.refresh,
    )

    print_results(rc, data, from_cache)

    if "error" not in data:
        output_file = export_json(rc, data)

        if output_file:
            console.print(
                f"\n[bold yellow]Saved result: {output_file}[/bold yellow]"
            )

    console.print("\n[bold green]Done.[/bold green]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(130)
    except Exception as error:
        log(f"Unexpected error: {type(error).__name__}")
        console.print(
            f"\n[bold red]Unexpected error: {type(error).__name__}[/bold red]"
        )
        sys.exit(1)
