# -*- coding: utf-8 -*-
import os, sys, json, importlib
import streamlit as st
import base64
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import requests

# حمّل المفتاح من Secrets أولاً إن وُجد (آمن، لا يُعرض)
if "FOOTBALL_DATA_API_KEY" in st.secrets and st.secrets["FOOTBALL_DATA_API_KEY"]:
    os.environ["FOOTBALL_DATA_API_KEY"] = st.secrets["FOOTBALL_DATA_API_KEY"]
if "FD_MIN_INTERVAL_SEC" in st.secrets and st.secrets["FD_MIN_INTERVAL_SEC"]:
    os.environ["FD_MIN_INTERVAL_SEC"] = str(st.secrets["FD_MIN_INTERVAL_SEC"])

st.set_page_config(page_title="FD Predictor — Mobile", page_icon="⚽", layout="wide")

# حالة المظهر (افتراضياً: فاتح) + مفاتيح افتراضية للملء التلقائي
if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "فاتح"
st.session_state.setdefault("team1", "")
st.session_state.setdefault("team2", "")
st.session_state.setdefault("team1_home", True)
st.session_state.setdefault("comp_code", "PL")  # افتراضياً PL

def inject_css(theme="فاتح"):
    if theme == "فاتح":
        css = """
        <style>
        :root{
          --bg:#f7fafc; --fg:#0f172a; --muted:#475569;
          --card:#ffffff; --border:#e5e7eb;
          --primary:#2563eb; --ok:#16a34a; --warn:#f59e0b; --err:#ef4444;
          --chip:#f3f4f6; --chip-fg:#111827;
        }
        .stApp { background: radial-gradient(1200px at 10% -10%, #eef2ff 0%, #f7fafc 45%, #f7fafc 100%) !important; }
        .block-container { max-width: 1180px; }
        .hero h1 { color: var(--fg); letter-spacing:.3px; }
        .card { background: var(--card); border:1px solid var(--border); border-radius:14px; padding:14px 16px; box-shadow: 0 6px 14px rgba(16,24,40,.06) }
        .chip { display:inline-flex; gap:8px; align-items:center; background:var(--chip); color:var(--chip-fg);
                border:1px solid var(--border); border-radius:999px; padding:6px 10px; margin:4px 6px 0 0; font-size:.92em }
        .prob .lbl { color:var(--muted); font-size:.95em; margin-bottom:6px }
        .prob .bar { height:12px; border-radius:999px; overflow:hidden; background:#e5e7eb; border:1px solid #e2e8f0 }
        .prob .fill { height:100%; transition:width .5s ease }
        .prob.home .fill { background: linear-gradient(90deg, #22c55e, #16a34a); }
        .prob.draw .fill { background: linear-gradient(90deg, #f59e0b, #d97706); }
        .prob.away .fill { background: linear-gradient(90deg, #ef4444, #b91c1c); }
        .stButton>button { background:linear-gradient(135deg, #2563eb, #1d4ed8); color:#fff; border:0; border-radius:12px; padding:10px 16px }
        [data-testid="metric-container"] { background:#f8fafc; border:1px solid var(--border); border-radius:12px; padding:12px }
        </style>
        """
    else:  # داكن
        css = """
        <style>
        :root{
          --bg:#0b1020; --fg:#eaf2ff; --muted:#a3b1c6;
          --card:#121a2a; --border:#1e2a3b;
          --primary:#4fa3ff; --ok:#22c55e; --warn:#fbbf24; --err:#f87171;
          --chip:#0f1626; --chip-fg:#dfeaff;
        }
        .stApp { background: radial-gradient(1200px at 15% -10%, #0c1626 0%, #0b1020 45%, #0a0e18 100%) !important; }
        .block-container { max-width: 1180px; }
        .hero h1 { background: linear-gradient(90deg, #4fa3ff, #00d2d3, #c084fc); -webkit-background-clip:text; background-clip:text; color:transparent; letter-spacing:.3px; }
        .card { background: rgba(18,26,42,.78); border:1px solid rgba(109,116,136,.22); border-radius:14px; padding:14px 16px; box-shadow: 0 12px 28px rgba(0,0,0,.35) }
        .chip { display:inline-flex; gap:8px; align-items:center; background:var(--chip); color:var(--chip-fg);
                border:1px solid var(--border); border-radius:999px; padding:6px 10px; margin:4px 6px 0 0; font-size:.92em }
        .prob .lbl { color:var(--muted); font-size:.95em; margin-bottom:6px }
        .prob .bar { height:12px; border-radius:999px; overflow:hidden; background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.08) }
        .prob .fill { height:100%; transition:width .5s ease }
        .prob.home .fill { background: linear-gradient(90deg, #22c55e, #16a34a); }
        .prob.draw .fill { background: linear-gradient(90deg, #f59e0b, #d97706); }
        .prob.away .fill { background: linear-gradient(90deg, #ef4444, #b91c1c); }
        .stButton>button { background:linear-gradient(135deg, #4fa3ff, #2563eb); color:#fff; border:0; border-radius:12px; padding:10px 16px; box-shadow: 0 8px 20px rgba(37,99,235,.25) }
        [data-testid="metric-container"] { background:rgba(12,18,32,.7); border:1px solid rgba(255,255,255,.06); border-radius:12px; padding:12px }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)

inject_css(st.session_state.ui_theme)

# استيراد fd_predictor بعد ضبط المفتاح
def import_fd():
    if "fd_predictor" in sys.modules:
        del sys.modules["fd_predictor"]
    return importlib.import_module("fd_predictor")

# شريط علوي بسيط مع اختيار المظهر
c_top_l, c_top_r = st.columns([3,1])
with c_top_l:
    st.markdown("<div class='hero'><h1>Best Odds,Best Vision  ⚽</h1></div>", unsafe_allow_html=True)
with c_top_r:
    theme = st.selectbox("المظهر", ["فاتح","داكن"], index=(0 if st.session_state.ui_theme=="فاتح" else 1))
    if theme != st.session_state.ui_theme:
        st.session_state.ui_theme = theme
        inject_css(theme)

# قسم مفتاح API — آمن
with st.expander("إعداد مفتاح API (Football-Data.org)", expanded=True):
    api_set = bool(os.getenv("FOOTBALL_DATA_API_KEY"))
    st.write("الحالة:", "✅ تم الضبط عبر Secrets/الجلسة" if api_set else "❌ غير مضبوط")
    with st.form("api_form"):
        api_in = st.text_input("أدخل/حدّث المفتاح (لن يُعرض أو يُحفظ)", value="", type="password", placeholder="ألصق المفتاح هنا")
        save_api = st.form_submit_button("حفظ المفتاح للجلسة")
        if save_api:
            if api_in.strip():
                os.environ["FOOTBALL_DATA_API_KEY"] = api_in.strip()
                st.success("تم حفظ المفتاح لهذه الجلسة بنجاح.")
            else:
                st.warning("لم يتم إدخال مفتاح.")
    st.caption("تلميح: على Streamlit Cloud استخدم Settings → Secrets لحفظ المفتاح بأمان. لا تضعه في الكود أو الريبو.")

# -------------------------------------------------------------------
# اختيار من البطولات والمباريات (جلب من API وتعبئة تلقائية)
# -------------------------------------------------------------------

# خريطة البطولات لعرض أسماء ودّية
COMP_MAP = {
    "PL":  "الدوري الإنجليزي الممتاز — PL",
    "PD":  "الدوري الإسباني — LaLiga — PD",
    "SA":  "الدوري الإيطالي — Serie A — SA",
    "BL1": "الدوري الألماني — Bundesliga — BL1",
    "FL1": "الدوري الفرنسي — Ligue 1 — FL1",
    "CL":  "دوري أبطال أوروبا — CL",
    "DED": "الدوري الهولندي — Eredivisie — DED",
    "PPL": "الدوري البرتغالي — PPL",
    "BSA": "الدوري البرازيلي — BSA",
    "ELC": "التشامبيونشيب — ELC",
}

def _fmt_local(utc_iso: str) -> str:
    try:
        # تحويل وقت UTC إلى التوقيت المحلي
        local_tz = datetime.now().astimezone().tzinfo
        dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00")).astimezone(local_tz)
        return dt.strftime("%a %d %b %H:%M")
    except Exception:
        return utc_iso

@st.cache_data(ttl=90)
def fetch_matches_api(comp_code: str, date_from: datetime.date, date_to: datetime.date, status: str = "SCHEDULED"):
    token = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not token:
        raise RuntimeError("FOOTBALL_DATA_API_KEY غير مضبوط.")
    base = "https://api.football-data.org/v4/matches"
    params = {
        "competitions": comp_code,
        "dateFrom": date_from.strftime("%Y-%m-%d"),
        "dateTo": date_to.strftime("%Y-%m-%d"),
        "status": status  # SCHEDULED, TIMED, LIVE, IN_PLAY, FINISHED
    }
    headers = {"X-Auth-Token": token}
    r = requests.get(base, headers=headers, params=params, timeout=20)
    if r.status_code != 200:
        try:
            msg = r.json()
        except Exception:
            msg = r.text
        raise RuntimeError(f"API {r.status_code}: {msg}")
    data = r.json() or {}
    matches = []
    for m in data.get("matches", []):
        matches.append({
            "id": m.get("id"),
            "utcDate": m.get("utcDate"),
            "competition": (m.get("competition") or {}).get("code") or comp_code,
            "matchday": m.get("matchday"),
            "status": m.get("status"),
            "home": (m.get("homeTeam") or {}).get("name"),
            "away": (m.get("awayTeam") or {}).get("name"),
        })
    matches.sort(key=lambda x: (x.get("utcDate") or "", x.get("home") or ""))
    return matches

# واجهة اختيار البطولات والمباريات
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.subheader("اختيار من البطولات والمباريات")

colA, colB, colC = st.columns([1.6, 1.1, 1.0])

# تحديد المؤشر الافتراضي لقائمة البطولات
_comp_keys = list(COMP_MAP.keys())
_default_comp_key = st.session_state.get("comp_select", st.session_state.comp_code)
_default_index = _comp_keys.index(_default_comp_key) if _default_comp_key in _comp_keys else 0

with colA:
    comp_sel = st.selectbox(
        "اختر البطولة",
        options=_comp_keys,
        format_func=lambda c: COMP_MAP.get(c, c),
        index=_default_index,
        key="comp_select",
    )
with colB:
    status_sel = st.selectbox(
        "الحالة",
        options=["SCHEDULED", "TIMED", "LIVE", "IN_PLAY", "FINISHED"],
        index=0,
        key="status_select"
    )
with colC:
    range_sel = st.selectbox(
        "الفترة",
        options=["اليوم", "3 أيام", "أسبوع", "شهر", "مخصص"],
        index=2,
        key="range_select"
    )

today = datetime.now().date()
if st.session_state.range_select == "مخصص":
    d1, d2 = st.columns(2)
    with d1:
        date_from = st.date_input("من", value=st.session_state.get("date_from", today), key="date_from")
    with d2:
        date_to = st.date_input("إلى", value=st.session_state.get("date_to", today + timedelta(days=7)), key="date_to")
else:
    if st.session_state.range_select == "اليوم":
        date_from, date_to = today, today
    elif st.session_state.range_select == "3 أيام":
        date_from, date_to = today, today + timedelta(days=3)
    elif st.session_state.range_select == "أسبوع":
        date_from, date_to = today, today + timedelta(days=7)
    else:  # "شهر"
        date_from, date_to = today, today + timedelta(days=30)
    st.session_state["date_from"] = date_from
    st.session_state["date_to"] = date_to

matches = []
if os.getenv("FOOTBALL_DATA_API_KEY"):
    try:
        matches = fetch_matches_api(st.session_state.comp_select, date_from, date_to, st.session_state.status_select)
    except Exception as e:
        st.warning(f"تعذّر جلب المباريات: {e}")
else:
    st.info("اضبط مفتاح FOOTBALL_DATA_API_KEY لجلب المباريات تلقائيًا.")

selected_match = None
if matches:
    labels = [
        f"{_fmt_local(m['utcDate'])} — {m['home']} vs {m['away']}  (MD {m.get('matchday') or '-'})"
        for m in matches
    ]
    idx = st.selectbox(
        "اختر مباراة",
        options=list(range(len(matches))),
        format_func=lambda i: labels[i],
        key="match_pick"
    )
    if isinstance(idx, int) and 0 <= idx < len(matches):
        selected_match = matches[idx]
        st.caption(f"الحالة: {selected_match['status']} · المسابقة: {selected_match['competition']} · Matchday: {selected_match.get('matchday') or '-'}")

    c1, c2 = st.columns([1,1])
    with c1:
        lock_fields = st.checkbox("قفل الحقول بعد الاختيار", value=True, key="lock_match_fields")
    with c2:
        if st.button("استخدام هذه المباراة لتعبئة الحقول", type="primary"):
            st.session_state["team1"] = selected_match["home"]
            st.session_state["team2"] = selected_match["away"]
            st.session_state["team1_home"] = True
            st.session_state["comp_code"] = selected_match["competition"]
            st.success(f"تم اختيار: {selected_match['home']} vs {selected_match['away']}")
            try:
                st.rerun()
            except Exception:
                st.experimental_rerun()
else:
    st.info("لا توجد مباريات ضمن النطاق المحدد.")

st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------------------------
# المدخلات
# -------------------------------------------------------------------
with st.form("predict_form"):
    c1, c2 = st.columns(2)

    # تعطيل الحقول إذا تم اختيار مباراة وقُفلَت
    disabled_fields = bool(st.session_state.get("lock_match_fields")) and bool(st.session_state.get("team1")) and bool(st.session_state.get("team2"))

    with c1:
        team1 = st.text_input("الفريق 1 (قد يكون صاحب الأرض)", key="team1", disabled=disabled_fields)
        team1_home = st.checkbox("هل الفريق 1 صاحب الأرض؟", key="team1_home", disabled=disabled_fields)
        comp_code = st.selectbox(
            "كود المسابقة (اختياري)",
            options=["","CL","PD","PL","SA","BL1","FL1","DED","PPL","BSA","ELC"],
            key="comp_code"  # سيتم ضبطه تلقائياً عند اختيار مباراة
        )
    with c2:
        team2 = st.text_input("الفريق 2", key="team2", disabled=disabled_fields)
        max_goals = st.text_input("حجم شبكة الأهداف (فارغ = ديناميكي)", key="max_goals")

    with st.expander("خيارات عرض البيانات الإضافية"):
        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1: show_players = st.checkbox("إظهار السكواد", value=False)
        with cc2: show_recent = st.checkbox("إظهار آخر المباريات", value=True)
        with cc3: show_scorers = st.checkbox("إظهار هدّافي المسابقة", value=False)
        with cc4: show_upcoming = st.checkbox("إظهار المباريات القادمة", value=False)
        rr1, rr2, rr3, rr4 = st.columns(4)
        with rr1: recent_days = st.number_input("عدد الأيام للمباريات الأخيرة", min_value=30, max_value=720, value=180)
        with rr2: recent_limit = st.number_input("عدد المباريات الأخيرة", min_value=1, max_value=20, value=5)
        with rr3: recent_all_comps = st.checkbox("من كل المسابقات", value=False)
        with rr4: scorers_limit = st.number_input("عدد الهدّافين", min_value=5, max_value=100, value=20)

    with st.expander("إعدادات متقدمة"):
        odds_json = st.text_area("أودز (JSON) لحساب كيللي", height=90, placeholder='{"1x2":{"home":2.1,"draw":3.4,"away":3.2}}')
        extras_json = st.text_area("Extras (JSON) مثل التشكيلات/الطقس/الإصابات", height=120, placeholder='{"formations":{"home":"4-3-3","away":"4-2-3-1"},"context":{"weather":"rain"}}')

    submitted = st.form_submit_button("⚡ توقّع الآن")

# بطاقة تعليمية إن لم يُنقر زر التوقع
if not submitted:
    st.markdown("<div class='card'>أدخل الفريقين أو اختر مباراة من البطولات أعلاه ثم اضغط “⚡ توقّع الآن”. أول تشغيل قد يستغرق بضع ثوانٍ لتفادي Rate Limit.</div>", unsafe_allow_html=True)

# عند الضغط
if submitted:
    if not os.getenv("FOOTBALL_DATA_API_KEY"):
        st.error("يجب ضبط FOOTBALL_DATA_API_KEY قبل التوقّع (Secrets أو الحقل أعلاه).")
        st.stop()
    try:
        fd = import_fd()
    except Exception as e:
        st.exception(e)
        st.stop()

    # تجهيز المدخلات المتقدمة
    mg = None
    try:
        mg = int(max_goals) if str(max_goals).strip() else None
    except Exception:
        mg = None

    try:
        odds = json.loads(odds_json) if str(odds_json).strip() else None
    except Exception as e:
        st.warning(f"خطأ في odds JSON: {e}")
        odds = None

    try:
        extras = json.loads(extras_json) if str(extras_json).strip() else None
    except Exception as e:
        st.warning(f"خطأ في extras JSON: {e}")
        extras = None

    comp = comp_code if comp_code else None

    with st.spinner("جارِ الحساب وجلب البيانات (لتفادي 429 قد يستغرق بضع ثواني)..."):
        try:
            res = fd.predict_match(
                team1, team2,
                team1_is_home=team1_home,
                competition_code_override=comp,
                odds=odds,
                max_goals=mg,
                extras=extras,
                scorers_limit=int(scorers_limit or fd.SCORERS_LIMIT_DEFAULT),
            )
            if any([show_players, show_recent, show_scorers, show_upcoming]):
                res = fd.enrich_with_free_stats(
                    res,
                    include_players=show_players,
                    include_recent=show_recent,
                    include_scorers=show_scorers,
                    include_upcoming=show_upcoming,
                    recent_days=int(recent_days or 180),
                    recent_limit=int(recent_limit or 5),
                    recent_all_comps=recent_all_comps,
                    scorers_limit=int(scorers_limit or fd.SCORERS_LIMIT_DEFAULT),
                )
        except Exception as e:
            st.exception(e)
            st.stop()

    # عرض النتائج — بطاقات واضحة
    probs = res.get("probabilities", {}).get("1x2", {})
    lamb = res.get("lambdas", {})
    meta = res.get("meta", {}) or {}
    top = res.get("probabilities", {}).get("top_scorelines", [])
    mkts = res.get("probabilities", {}).get("markets", {})
    kelly = res.get("kelly", {}) or {}

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("احتمالات 1×2")
    colp1, colp2, colp3 = st.columns(3)

    def prob_block(label, val, kind):
        try:
            val = float(val or 0.0)
        except:
            val = 0.0
        bar_html = f"""
        <div class='prob {kind}'>
          <div class='lbl'>{label} — <b>{val:.2f}%</b></div>
          <div class='bar'><div class='fill' style='width:{max(0,min(100,val))}%;'></div></div>
        </div>"""
        st.markdown(bar_html, unsafe_allow_html=True)

    with colp1: prob_block("صاحب الأرض", probs.get("home", 0), "home")
    with colp2: prob_block("التعادل", probs.get("draw", 0), "draw")
    with colp3: prob_block("الضيف", probs.get("away", 0), "away")
    st.markdown(f"<span class='chip'>DC rho: {meta.get('dc_rho')}</span> <span class='chip'>شبكة: {meta.get('max_goals_grid')}</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("معدل الأهداف (λ)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("منزل — النهائي", lamb.get("home_final"))
    m2.metric("منزل — الأساس", lamb.get("home_base"))
    m3.metric("ضيف — النهائي", lamb.get("away_final"))
    m4.metric("ضيف — الأساس", lamb.get("away_base"))
    st.caption(f"المسابقة: {(meta.get('competition') or {}).get('code')} · العيّنة: {(meta.get('samples') or {}).get('matches_used')}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("أعلى النتائج المتوقعة")
    if top:
        chips = " ".join([f"<span class='chip'>{t.get('score')} — {t.get('prob')}%</span>" for t in top])
        st.markdown(chips, unsafe_allow_html=True)
    else:
        st.info("لا توجد نتائج عالية مرجّحة ضمن الشبكة.")
    st.markdown("</div>", unsafe_allow_html=True)

    cL, cR = st.columns(2)
    with cL:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("الأسواق الإضافية")
        st.write(mkts)
        st.markdown("</div>", unsafe_allow_html=True)
    with cR:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("اقتراحات كيللي")
        st.write(kelly)
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("الإخراج الكامل (JSON)"):
        # عرض الشجرة الافتراضي
        st.json(res)

        # نص JSON جاهز للنسخ/التنزيل
        try:
            json_str = json.dumps(res, ensure_ascii=False, indent=2)
        except Exception:
            json_str = json.dumps(res, default=str, ensure_ascii=False, indent=2)

        # زر تنزيل الملف
        st.download_button(
            "⬇️ تنزيل JSON",
            data=json_str,
            file_name="prediction.json",
            mime="application/json",
            key="dl_json",
        )

        # زر نسخ إلى الحافظة — باستخدام components.html
        b64 = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
        components.html("""
        <div style="margin-top:8px;">
          <button id="copy-json"
                  style="cursor:pointer; padding:10px 14px; border-radius:10px; border:0;
                         background:linear-gradient(135deg,#2563eb,#1d4ed8); color:#fff; font-weight:600;">
            📋 نسخ JSON
          </button>
        </div>
        <script>
          const data = atob('%s');
          const btn = document.getElementById('copy-json');
          btn.addEventListener('click', async () => {
            try {
              await navigator.clipboard.writeText(data);
              btn.textContent = '✔ تم النسخ';
            } catch (e) {
              const ta = document.createElement('textarea');
              ta.value = data;
              document.body.appendChild(ta);
              ta.select();
              document.execCommand('copy');
              document.body.removeChild(ta);
              btn.textContent = '✔ تم النسخ';
            }
            setTimeout(() => btn.textContent = '📋 نسخ JSON', 1600);
          });
        </script>
        """ % b64, height=60)
