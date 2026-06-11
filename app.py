import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import requests

# --- [1] 한글 폰트 자동 설정 (가장 확실한 방법) ---
@st.cache_data
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
    # 전역 폰트 설정
    plt.rc('font', family=font_prop.get_name())
    plt.rcParams['axes.unicode_minus'] = False
except:
    st.warning("폰트 설정 중 문제가 발생했습니다.")

# --- [2] 데이터 로드 및 SQL 처리 ---
st.set_page_config(page_title="축제 방문객 분석", layout="wide")
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

    sql_query = """
    SELECT
        a.축제명, a.지역명, b.직전월_방문자수, a.개최월_방문자수,
        ROUND((CAST(a.개최월_방문자수 AS FLOAT) - b.직전월_방문자수) / b.직전월_방문자수 * 100, 1) AS 증감률
    FROM 개최월 AS a JOIN 직전월 AS b ON a.축제명 = b.축제명
    ORDER BY 증감률 DESC;
    """
    df_result = pd.read_sql_query(sql_query, conn)

    # --- [3] 데이터 그룹화 (빅3 vs 나머지) ---
    big3_names = ['해운대 모래축제', '해운대 빛축제', '대전 0시 축제']
    df_big3 = df_result[df_result['축제명'].isin(big3_names)].copy()
    df_others = df_result[~df_result['축제명'].isin(big3_names)].head(4).copy() # 상위 7개를 맞추기 위해 나머지 중 4개 선택

    # 시각화용 줄바꿈 처리 함수
    def wrap_text(text):
        return text.replace(' ', '\n')

    # --- [4] 차트 생성 함수 ---
    def draw_group_chart(df, title, color_active):
        df['축제명_display'] = df['축제명'].apply(wrap_text)
        fig, ax = plt.subplots(figsize=(10, 6))
        
        idx = range(len(df))
        bar_width = 0.35
        
        # 단위 변환: 만 명
        b_val = df['직전월_방문자수'] / 10000
        a_val = df['개최월_방문자수'] / 10000
        
        bar1 = ax.bar([i - bar_width/2 for i in idx], b_val, bar_width, label='Before(직전월)', color='#D3D3D3')
        bar2 = ax.bar([i + bar_width/2 for i in idx], a_val, bar_width, label='Active(개최월)', color=color_active)
        
        ax.set_title(title, fontproperties=font_prop, fontsize=15, pad=15)
        ax.set_ylabel("방문자 수 (단위: 만 명)", fontproperties=font_prop)
        ax.set_xticks(idx)
        ax.set_xticklabels(df['축제명_display'], fontproperties=font_prop)
        ax.legend(prop=font_prop)

        # 수치 및 증감률 표시
        for i in range(len(df)):
            # 개최월 막대 위 방문자수
            ax.text(i + bar_width/2, a_val.iloc[i], f"{a_val.iloc[i]:.1f}만", 
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
            # 증감률 표시
            rate = df['증감률'].iloc[i]
            rate_text = f"▲ +{rate}%"
            ax.text(i + bar_width/2, a_val.iloc[i] * 1.05, rate_text, 
                    ha='center', va='bottom', color='red' if rate >= 100 else 'indigo', 
                    fontweight='bold', fontproperties=font_prop, fontsize=11)
        
        return fig

    # --- [5] 화면 레이아웃 구성 ---
    st.subheader("📍 방문객 규모별 유입 효과 비교 (Grouped)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🚀 대규모 축제 (Big 3)")
        fig1 = draw_group_chart(df_big3, "주요 대형 축제 방문객 비교", "#636EFA")
        st.pyplot(fig1)
        
    with col2:
        st.markdown("#### 📈 지역 중소 규모 축제")
        fig2 = draw_group_chart(df_others, "지역 분산 효과 축제 비교", "#EF553B")
        st.pyplot(fig2)

    # --- [6] SQL 및 인사이트 출력 ---
    with st.expander("📝 사용된 SQL JOIN Query 확인"):
        st.code(sql_query, language='sql')

    # 인사이트 계산
    max_row = df_result.iloc[0]
    st.markdown("---")
    st.subheader("💡 데이터 분석 인사이트")
    
    insight_col1, insight_col2 = st.columns(2)
    with insight_col1:
        st.info(f"**인사이트 1 — '인구 펌프'로서의 실효성:**\n\n"
                f"축제는 외지인을 끌어당기는 강력한 트리거입니다. **{max_row['축제명']}**의 경우 "
                f"직전월 대비 방문자가 **{max_row['증감률']}%** 증가하며 실질적인 인구 유입 효과를 입증했습니다.")
    with insight_col2:
        st.success(f"**인사이트 2 — 단발성 유입의 한계:**\n\n"
                   f"유입 효과가 강력할수록 축제 종료 후에도 방문이 이어지도록 하는 '체류형 관광 인프라'와 "
                   f"교통망 연계 정책이 필수적임을 시사합니다.")
