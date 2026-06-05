import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import requests

# --- [강력한 한글 해결책] 폰트 자동 다운로드 설정 ---
@st.cache_data # 매번 다운로드하지 않도록 캐싱합니다.
def download_font():
    url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        res = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(res.content)
    return font_path

try:
    font_path = download_font()
    font_prop = fm.FontProperties(fname=font_path)
    plt.rc('font', family=font_prop.get_name())
    plt.rcParams['axes.unicode_minus'] = False # 마이너스 기호 깨짐 방지
except:
    st.warning("폰트 로드 중 에러가 발생했습니다. 기본 폰트로 표시합니다.")

# --- 대시보드 시작 ---
st.set_page_config(page_title="지역 축제 분석", layout="wide")
st.title("📊 지역 축제 방문객 유입 효과 분석")

def load_data():
    f_active = '축제 개최월 방문자수.xlsx'
    f_before = '축제 직전월 방문자수.xlsx'
    if not os.path.exists(f_active) or not os.path.exists(f_before):
        st.error("❌ 엑셀 파일이 없습니다. 파일명을 확인해 주세요.")
        return None, None
    df1 = pd.read_excel(f_active)
    df2 = pd.read_excel(f_before)
    df1.columns = [c.replace(' ', '_') for c in df1.columns]
    df2.columns = [c.replace(' ', '_') for c in df2.columns]
    return df1, df2

df_active, df_before = load_data()

if df_active is not None:
    conn = sqlite3.connect(':memory:')
    df_active.to_sql('개최월', conn, index=False)
    df_before.to_sql('직전월', conn, index=False)

    query = """
    SELECT
        a.축제명, a.지역명, b.직전월_방문자수, a.개최월_방문자수,
        ROUND((CAST(a.개최월_방문자수 AS FLOAT) - b.직전월_방문자수) / b.직전월_방문자수 * 100, 1) AS 증감률
    FROM 개최월 AS a JOIN 직전월 AS b ON a.축제명 = b.축제명
    ORDER BY 증감률 DESC;
    """
    
    df_result = pd.read_sql_query(query, conn)
    df_top7 = df_result.head(7).copy()
    df_top7['축제명_display'] = df_top7['축제명'].apply(lambda x: x.replace(' ', '\n'))

    st.subheader("📍 TOP 7 축제 방문객 유입 비교")
    
    fig, ax = plt.subplots(figsize=(12, 7))
    bar_width = 0.35
    idx = range(len(df_top7))
    
    # 단위: 만 명
    b_val = df_top7['직전월_방문자수'] / 10000
    a_val = df_top7['개최월_방문자수'] / 10000
    
    bar1 = ax.bar([i - bar_width/2 for i in idx], b_val, bar_width, label='직전월', color='#D3D3D3')
    bar2 = ax.bar([i + bar_width/2 for i in idx], a_val, bar_width, label='개최월', color='#FF7F50')
    
    # 텍스트 설정 (폰트 프로퍼티 명시)
    ax.set_title("지역 축제의 외지인 유입 효과 비교", fontproperties=font_prop, fontsize=18, pad=20)
    ax.set_ylabel("방문자 수 (단위: 만 명)", fontproperties=font_prop, fontsize=12)
    ax.set_xticks(idx)
    ax.set_xticklabels(df_top7['축제명_display'], fontproperties=font_prop, fontsize=10)
    ax.legend(prop=font_prop)

    # 수치 및 증감률 표시
    for i in range(len(df_top7)):
        ax.text(i - bar_width/2, b_val.iloc[i], f"{b_val.iloc[i]:.1f}", ha='center', va='bottom', fontsize=8)
        ax.text(i + bar_width/2, a_val.iloc[i], f"{a_val.iloc[i]:.1f}", ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        rate = df_top7['증감률'].iloc[i]
        ax.text(i + bar_width/2, a_val.iloc[i] + (a_val.max()*0.05), f"▲{rate}%", 
                ha='center', va='bottom', color='red' if rate >= 100 else 'black', fontweight='bold', fontproperties=font_prop)

    st.pyplot(fig)

    # SQL 및 인사이트
    st.code(query, language='sql')
    max_f = df_result.iloc[0]
    st.info(f"**인사이트:** {max_f['축제명']}은 증감률 {max_f['증감률']}%로 가장 강력한 유입을 보였습니다.")
