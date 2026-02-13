import streamlit as st
import requests
import re
import itertools
import urllib3
import time
import urllib.parse
import google.generativeai as genai
from collections import Counter
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 🔑 API 金鑰設定 (雲端安全版)
# ==========================================
# 這裡會自動去抓雲端的密碼庫，不需要把密碼寫在程式碼裡
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    # 如果您在電腦本機跑，沒設 secrets，就用這個備用的
    GEMINI_API_KEY = "您的API金鑰" 

# ==========================================
# 📱 頁面設定
# ==========================================
st.set_page_config(
    page_title="Jarvis Mobile",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stChatInput {
        position: fixed;
        bottom: 0px;
        background-color: white;
        padding-bottom: 15px;
        z-index: 999;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
    .search-card {
        background-color: #262730;
        padding: 12px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #444;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    a {text-decoration: none; color: #4da6ff !important; font-weight: bold; font-size: 16px;}
    </style>
""", unsafe_allow_html=True)

# ... (以下核心邏輯保持不變，為了版面整潔，請直接使用上一版 v18.0 的 Class 內容) ...
# ... (請將 v18.0 的 WebSearcher, BingoAlgorithm, DirectInfo, get_model, jarvis_think 全部複製過來) ...

class WebSearcher:
    @staticmethod
    def decode_ddg_url(raw_url):
        try:
            if raw_data := re.search(r'uddg=([^&]+)', raw_url):
                return urllib.parse.unquote(raw_data.group(1))
            return raw_url if raw_url.startswith('http') else ""
        except: return ""
    @staticmethod
    def search_web(query):
        results_list = []
        snippets_text = []
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'}
        try:
            res = requests.get("https://zh.wikipedia.org/w/api.php", params={"action":"query","format":"json","list":"search","srsearch":query,"srlimit":2}, timeout=5)
            for item in res.json().get("query",{}).get("search",[]):
                t = item["title"]; s = re.sub(r'<[^>]+>','',item["snippet"])
                results_list.append({"title":f"📚 {t}","link":f"https://zh.wikipedia.org/wiki/{t}","snippet":s})
                snippets_text.append(f"Wiki: {t}-{s}")
        except: pass
        try:
            res = requests.get(f"https://html.duckduckgo.com/html/?q={query}", headers=headers, timeout=8)
            soup = BeautifulSoup(res.text, 'html.parser')
            for i, r in enumerate(soup.find_all('div', class_='result'), 1):
                if i>6: break
                ta = r.find('a', class_='result__a'); sa = r.find('a', class_='result__snippet')
                if ta:
                    t = ta.get_text(strip=True)
                    l = WebSearcher.decode_ddg_url(ta['href'])
                    s = sa.get_text(strip=True) if sa else ""
                    if l: results_list.append({"title":t,"link":l,"snippet":s}); snippets_text.append(f"{t}-{s}")
        except: pass
        return results_list, "\n".join(snippets_text[:5])

class BingoAlgorithm:
    @staticmethod
    def analyze_and_predict(stars=5):
        try:
            res = requests.get("https://www.pilio.idv.tw/bingo/list.asp", headers={'User-Agent':'Mozilla/5.0'}, timeout=10, verify=False)
            res.encoding='big5'
            soup = BeautifulSoup(res.text, 'html.parser')
            nums = []
            for tr in soup.find_all('tr'):
                txt = tr.get_text(strip=True)
                if re.search(r'11[0-9]\d{6}', txt):
                    n = [int(x) for x in re.findall(r'\d+', txt) if int(x)<=80][:20]
                    if len(n)==20: nums.extend(n)
            if not nums: return "❌ 來源阻擋", []
            hot = [n for n,c in Counter(nums).most_common(stars)]
            return f"🎱 **賓果 {stars} 星 (追熱)**\n🔥：**{sorted(hot)}**", []
        except: return "⚠️ 連線錯誤", []

class DirectInfo:
    @staticmethod
    def get_stock(code):
        try:
            ts = int(time.time()*1000)
            res = requests.get(f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{code}.tw|otc_{code}.tw&json=1&_={ts}", timeout=5, verify=False)
            d = res.json()
            if d['msgArray']:
                i = d['msgArray'][0]
                p = i.get('z','-'); p = i.get('b','-').split('_')[0] if p=='-' else p
                return f"📈 **{code} {i.get('n','')}**\n💰 {p}", []
            return "⚠️ 查無", []
        except: return "⚠️ 忙線", []

def get_model():
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash')
    except: return None

def jarvis_think(txt, model):
    txt = txt.lower()
    if "賓果" in txt or "星" in txt:
        s = 5
        if m := re.search(r'(\d+)\s*星', txt): s = int(m.group(1))
        cn = {'一':1,'二':2,'三':3,'四':4,'五':5}
        for k,v in cn.items(): 
            if k in txt: s = v
        return BingoAlgorithm.analyze_and_predict(s)
    if "股" in txt and (m:=re.search(r'\d{4,6}', txt)): return DirectInfo.get_stock(m.group(0))
    if any(k in txt for k in ["時間","日期","新聞","報名","多少","查","誰"]):
        res, raw = WebSearcher.search_web(txt)
        ans = "🔍 搜尋完畢"
        if raw and model:
            try: ans = model.generate_content(f"基於以下資料回答'{txt}'，簡短即可：\n{raw}").text
            except: pass
        return ans, res
    if model:
        try: return model.generate_content(txt).text, []
        except: pass
    return "🤖 請輸入指令", []

if "model" not in st.session_state: st.session_state.model = get_model()
if "msgs" not in st.session_state: st.session_state.msgs = []
if "res" not in st.session_state: st.session_state.res = []

st.title("🤖 Jarvis Mobile")
for role, txt in st.session_state.msgs:
    with st.chat_message(role): st.markdown(txt)
if st.session_state.res:
    st.markdown("---")
    st.caption("🌐 相關資訊 (點擊開啟)")
    for item in st.session_state.res:
        st.markdown(f"""
        <div class="search-card">
            <a href="{item['link']}" target="_blank">{item['title']}</a>
            <div style="color:#bbb;font-size:12px;margin-top:4px;">{item['snippet'][:60]}...</div>
        </div>
        """, unsafe_allow_html=True)
if prompt := st.chat_input("輸入指令..."):
    st.session_state.msgs.append(("user", prompt))
    st.rerun()
if st.session_state.msgs and st.session_state.msgs[-1][0] == "user":
    user_txt = st.session_state.msgs[-1][1]
    with st.chat_message("assistant"):
        with st.spinner("..."):
            ans, res = jarvis_think(user_txt, st.session_state.model)
            st.markdown(ans)
    st.session_state.msgs.append(("assistant", ans))
    st.session_state.res = res
    st.rerun()