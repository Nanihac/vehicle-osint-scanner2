#!/usr/bin/env python3

# ============================================================
# FIREWALL BREAKER - VEHICLE INFO
# Created by: Gunja Rahul
# YouTube: Gunja Rahul
# Version: 2.0 PRO
# ============================================================

"""
DISCLAIMER:
This tool is for lawful, educational and authorized use only.

Only query vehicle information when you have a legitimate reason
and are authorized to access the data. Do not use this tool for
unauthorized tracking, surveillance, harassment, or privacy abuse.
"""

import sys
import os
import json
import time
import hashlib
import re
import requests

from urllib.parse import urlencode
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.align import Align


# ============================================================
# CONFIGURATION
# ============================================================

API_BASE = "https://vehicleinfobyterabaap.vercel.app/lookup"
VERSION = "2.0 PRO"

console = Console()


# ============================================================
# DIRECTORIES
# ============================================================

RESULTS_DIR = "results"
LOGS_DIR = "logs"
CACHE_DIR = "cache"


def ensure_dirs():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)


# ============================================================
# SCREEN
# ============================================================

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def slow_print(text, delay=0.02):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


# ============================================================
# LOGGING
# ============================================================

def log(message):
    try:
        with open(
            os.path.join(LOGS_DIR, "firewall.log"),
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"{message}\n"
            )

    except Exception:
        pass


# ============================================================
# RC NUMBER
# ============================================================

def normalize_rc(rc):
    """
    Convert an RC number to a consistent format.

    Example:
        TS 05 ED 5022
        ts05ed5022

    becomes:

        TS05ED5022
    """

    if not rc:
        return ""

    rc = rc.strip().upper()

    # Remove spaces, hyphens and other separators
    rc = re.sub(r"[\s\-]", "", rc)

    return rc


def validate_rc(rc):
    """
    Basic Indian vehicle registration validation.

    This is intentionally not overly strict because different
    registration formats can exist.
    """

    if not rc:
        return False

    if len(rc) < 6 or len(rc) > 15:
        return False

    if not re.match(r"^[A-Z0-9]+$", rc):
        return False

    return True


def get_rc_input():

    console.print(
        "\n[bold cyan]Enter Vehicle RC number:[/bold cyan] ",
        end=""
    )

    rc = input().strip()

    rc = normalize_rc(rc)

    if not validate_rc(rc):

        console.print(
            "\n[bold red]Invalid RC format.[/bold red]"
        )

        console.print(
            "[yellow]Example:[/yellow] TS05ED5022\n"
        )

        return None

    return rc


# ============================================================
# CACHE
# ============================================================

def cache_path(rc):

    rc_hash = hashlib.sha256(
        rc.encode("utf-8")
    ).hexdigest()

    return os.path.join(
        CACHE_DIR,
        f"{rc_hash}.json"
    )


def save_cache(rc, data):

    try:

        with open(
            cache_path(rc),
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as error:

        log(f"Cache save failed: {error}")


def load_cache(rc):

    path = cache_path(rc)

    if not os.path.exists(path):
        return None

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        log(f"Cache load failed: {error}")

        return None


# ============================================================
# BANNER
# ============================================================

def loading_animation():

    console.print(
        "\n[bold green]Initializing Firewall Breaker...[/bold green]\n"
    )

    steps = [
        "Booting modules",
        "Checking network",
        "Loading UI",
        "Starting engine"
    ]

    for step in steps:

        console.print(
            f"[bold cyan]>> {step}...[/bold cyan]"
        )

        time.sleep(0.25)

    time.sleep(0.3)


def banner():

    console.rule()

    console.print(
        Align.center(
            f"[bold red]FIREWALL BREAKER[/bold red]"
            f"  •  "
            f"[yellow]{VERSION}[/yellow]"
        )
    )

    console.print(
        Align.center(
            "[green]Created by: G.Rahul • YouTube: Gunja Rahul[/green]"
        )
    )

    console.rule()

    disclaimer = (
        "[bold white on red] DISCLAIMER [/bold white on red]\n"
        "This tool is for lawful, educational and authorized use only."
    )

    console.print(
        Panel(
            disclaimer,
            style="red",
            expand=False
        )
    )

    console.rule()


# ============================================================
# API REQUEST
# ============================================================

def fetch_vehicle_data(rc):

    # --------------------------------------------------------
    # Check cache first
    # --------------------------------------------------------

    cached = load_cache(rc)

    if cached:

        cached["_from_cache"] = True

        return cached, True


    # --------------------------------------------------------
    # Build API URL
    # --------------------------------------------------------

    params = {
        "rc": rc
    }

    url = f"{API_BASE}?{urlencode(params)}"

    start_time = time.time()

    log(
        f"Query started. RC length={len(rc)}"
    )


    # --------------------------------------------------------
    # HTTP REQUEST
    # --------------------------------------------------------

    try:

        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(X11; Linux x86_64) "
                    "AppleWebKit/537.36 "
                    "Chrome/140 Safari/537.36"
                ),
                "Accept": "application/json",
            }
        )

    except requests.exceptions.Timeout:

        return {
            "error": "API request timed out.",
            "_status": "TIMEOUT"
        }, False

    except requests.exceptions.ConnectionError:

        return {
            "error": (
                "Could not connect to the vehicle API. "
                "Check your internet connection or API server."
            ),
            "_status": "CONNECTION_ERROR"
        }, False

    except requests.exceptions.RequestException as error:

        return {
            "error": f"Request failed: {error}",
            "_status": "REQUEST_ERROR"
        }, False


    # --------------------------------------------------------
    # RESPONSE TIME
    # --------------------------------------------------------

    response_time = round(
        (time.time() - start_time) * 1000,
        2
    )


    # --------------------------------------------------------
    # HTTP 404
    # --------------------------------------------------------

    if response.status_code == 404:

        try:
            error_data = response.json()

            message = error_data.get(
                "error",
                "No vehicle data found for this RC number."
            )

        except ValueError:

            message = (
                "No vehicle data found for this RC number."
            )

        log(
            f"API returned 404. Response time={response_time}ms"
        )

        return {
            "error": message,
            "_status": 404,
            "_api_time": response_time
        }, False


    # --------------------------------------------------------
    # HTTP 429
    # --------------------------------------------------------

    if response.status_code == 429:

        log("API rate limit reached.")

        return {
            "error": (
                "API rate limit reached. "
                "Please try again later."
            ),
            "_status": 429,
            "_api_time": response_time
        }, False


    # --------------------------------------------------------
    # HTTP 500+
    # --------------------------------------------------------

    if response.status_code >= 500:

        log(
            f"API server error: HTTP {response.status_code}"
        )

        return {
            "error": (
                f"Vehicle API server error: "
                f"HTTP {response.status_code}"
            ),
            "_status": response.status_code,
            "_api_time": response_time
        }, False


    # --------------------------------------------------------
    # Other HTTP errors
    # --------------------------------------------------------

    if response.status_code != 200:

        try:
            error_body = response.text[:500]
        except Exception:
            error_body = "No response body."

        return {
            "error": (
                f"API returned HTTP "
                f"{response.status_code}: "
                f"{error_body}"
            ),
            "_status": response.status_code,
            "_api_time": response_time
        }, False


    # --------------------------------------------------------
    # JSON RESPONSE
    # --------------------------------------------------------

    try:

        data = response.json()

    except ValueError:

        return {
            "error": (
                "API returned an invalid JSON response."
            ),
            "_status": 200,
            "_api_time": response_time
        }, False


    # --------------------------------------------------------
    # Add metadata
    # --------------------------------------------------------

    if isinstance(data, dict):

        data["_api_time"] = response_time

        data["_status"] = 200

    else:

        data = {
            "vehicle_data": data,
            "_api_time": response_time,
            "_status": 200
        }


    # --------------------------------------------------------
    # Save cache
    # --------------------------------------------------------

    save_cache(rc, data)

    log(
        f"API success. Response time={response_time}ms"
    )

    return data, False


# ============================================================
# EXPORT
# ============================================================

def export_json(rc, data):

    path = os.path.join(
        RESULTS_DIR,
        f"{rc}.json"
    )

    try:

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        return path

    except Exception as error:

        log(f"Export failed: {error}")

        return None


# ============================================================
# RESULTS
# ============================================================

def print_results(rc, data, from_cache):

    console.print(
        Panel(
            "[bold magenta]Firewall Breaker PRO[/bold magenta]"
            "  •  "
            "[bold magenta]by G.Rahul[/bold magenta]",
            style="magenta",
            expand=False
        )
    )


    # --------------------------------------------------------
    # Error
    # --------------------------------------------------------

    if "error" in data:

        status = data.get("_status", "ERROR")

        api_time = data.get(
            "_api_time",
            "N/A"
        )

        console.print(
            Panel(
                f"[bold red]Error:[/bold red]\n"
                f"{data['error']}\n\n"
                f"[yellow]HTTP Status:[/yellow] {status}\n"
                f"[yellow]Response Time:[/yellow] "
                f"{api_time} ms",
                style="red"
            )
        )

        return


    # --------------------------------------------------------
    # API STATUS
    # --------------------------------------------------------

    api_time = data.get(
        "_api_time",
        "N/A"
    )

    status_code = data.get(
        "_status",
        200
    )

    console.print(
        Panel(
            f"[bold green]API: OK[/bold green]\n"
            f"HTTP Status: {status_code}\n"
            f"Cached: {'YES' if from_cache else 'NO'}\n"
            f"Response Time: {api_time} ms",
            style="green",
            expand=False
        )
    )


    # --------------------------------------------------------
    # Vehicle information table
    # --------------------------------------------------------

    table = Table(
        title=f"Vehicle Information — {rc}",
        box=box.ROUNDED,
        show_lines=True
    )

    table.add_column(
        "Field",
        style="bold cyan",
        no_wrap=True
    )

    table.add_column(
        "Value",
        style="white"
    )


    for key, value in data.items():

        # Don't display internal metadata
        if key.startswith("_"):
            continue

        if isinstance(value, (dict, list)):

            value = json.dumps(
                value,
                indent=2,
                ensure_ascii=False
            )

        table.add_row(
            str(key)
            .replace("_", " ")
            .title(),

            str(value)
        )


    console.print(table)


# ============================================================
# MAIN
# ============================================================

def main():

    ensure_dirs()

    clear_screen()

    loading_animation()

    banner()


    # --------------------------------------------------------
    # Command-line RC
    # --------------------------------------------------------

    if (
        len(sys.argv) > 1
        and sys.argv[1].startswith("--rc=")
    ):

        rc = sys.argv[1].replace(
            "--rc=",
            "",
            1
        )

        rc = normalize_rc(rc)

    else:

        rc = get_rc_input()


    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if not rc:

        console.print(
            "\n[bold red]No valid RC entered.[/bold red]"
        )

        sys.exit(1)


    if not validate_rc(rc):

        console.print(
            "\n[bold red]Invalid RC number.[/bold red]"
        )

        console.print(
            "[yellow]Example:[/yellow] TS05ED5022"
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Query
    # --------------------------------------------------------

    console.print(
        f"\n[bold cyan]Searching:[/bold cyan] "
        f"[bold green]{rc}[/bold green]\n"
    )


    data, from_cache = fetch_vehicle_data(rc)


    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print_results(
        rc,
        data,
        from_cache
    )


    # --------------------------------------------------------
    # Export successful results
    # --------------------------------------------------------

    if "error" not in data:

        output_file = export_json(
            rc,
            data
        )

        if output_file:

            console.print(
                "\n[bold yellow]"
                f"Result saved: {output_file}"
                "[/bold yellow]"
            )

            log(
                "Result exported successfully."
            )


    # --------------------------------------------------------
    # Finish
    # --------------------------------------------------------

    console.print(
        "\n[bold green]Done.[/bold green]"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        console.print(
            "\n[bold red]"
            "Interrupted by user — exiting."
            "[/bold red]"
        )

        sys.exit(0)

    except Exception as error:

        console.print(
            "\n[bold red]"
            f"Unexpected error: {error}"
            "[/bold red]"
        )

        log(
            f"Unexpected error: {error}"
        )

        sys.exit(1)
