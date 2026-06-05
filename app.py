import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import os

# 1. 한글 폰트 설정 (초보자분들이 가장 어려워하는 부분이에요!)
def set_korean_font():
    import platform
    from matplotlib import font_manager, rc
    
    plt.rcParams['axes.unicode_minus'] = False
    try:
        if platform.system() == 'Windows':
            path = "c:/Windows/Fonts/malgun.ttf"
            font_name = font_manager.FontProperties(fname=path).get_name()
            rc('font', family=font_name)
        elif platform.system() == 'Darwin': # Mac
            rc('font', family='AppleGothic')
        else: # Linux (Streamlit Cloud 등)
            rc('font', family='NanumGothic')
    except:
        st.warning("한글 폰트 설정 중 오류가 발생했습니다. 차트 내 한글이 깨질 수 있습니다.")

set_korean_font()

# 페이지 설정
st.set_page_config(page_title="축제 방문객 분석 대시보드", layout="wide")
st.title("📊 지역 축제 방문객 유입 효과 분석")
st.markdown("---")

# 2. 데이터 불러오기 함수
def load_data():
    file_active = '축제 개최월 방문자수.xlsx'
    file_before = '축제 직전월 방문자수.xlsx'
    
    if not os.path.exists(file_active) or not os.path.exists(file_before):
        st.error(f"❌ 데이터 파일이 없습니다! '{file_active}'와 '{file_before}' 파일을 확인해주세요.")
        return None, None
    
    df_active = pd.read_excel(file_active)
    df_before = pd.read_excel(file_before)
    return df_active, df_before

df_active, df_before = load_data()

if df_active is not None:
    # 3. SQL JOIN 수행
    # Pandas 데이터를 SQLite 임시 메모리에 저장합니다.
    conn = sqlite3.connect(':memory:')
    df_active.to_sql('개최월', conn, index=False)
    df_before.to_sql('직전월', conn, index=False)

    query = """
    SELECT 
        a.축제명,
        a.지역명,
        b.직전월_방문자수,
        a.개최월_방문자수,
        ROUND((CAST(a.개최월_방문자수 AS FLOAT) - b.직전월_방문자수) 
              / b.직전월_방문자수 * 100, 1) AS 증감률
    FROM 개최월 AS a
    JOIN 직전월 AS b ON a.축제명 = b.축제명
    ORDER BY 증감률 DESC;
    """
    
    df_result = pd.read_sql_query(query, conn)
    
    # 상위 7개 데이터 추출
    df_top7 = df_result.head(7).copy()
    
    # 차트용 축제명 줄바꿈 처리 (가독성을 위해)
    df_top7['축제명_display'] = df_top7['축제명'].apply(lambda x: x.replace(' ', '\n'))

    # 4. 차트 시각화 (Before & After 비교)
    st.subheader("📍 TOP 7 축제 방문객 유입 비교")
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 막대 위치 설정
    bar_width = 0.35
    index = range(len(df_top7))
    
    # 막대 그리기
    bar1 = ax.bar([i - bar_width/2 for i in index], df_top7['직전월_방문자수'] / 10000, 
                  bar_width, label='Before (직전월)', color='#D3D3D3') # 연한 회색
    bar2 = ax.bar([i + bar_width/2 for i in index], df_top7['개최월_방문자수'] / 10000, 
                  bar_width, label='Active (개최월)', color='#636EFA') # 선명한 인디고 블루
    
    # 차트 꾸미기
    ax.set_title("지역 축제의 외지인 유입 효과: 직전월 vs 개최월 방문자 수 비교", fontsize=16, pad=20)
    ax.set_ylabel("방문자 수 (단위: 만 명)", fontsize=12)
    ax.set_xticks(index)
    ax.set_xticklabels(df_top7['축제명_display'], fontsize=10)
    ax.legend()
    
    # 증감률 텍스트 표시
    for i, row in df_top7.iterrows():
        rate = row['증감률']
        color = 'red' if rate >= 100 else 'black'
        ax.text(i + bar_width/2, (row['개최월_방문자수']/10000) + 0.5, 
                f"▲ +{rate}%", ha='center', va='bottom', 
                fontsize=11, fontweight='bold', color=color)

    st.pyplot(fig)

    # 5. SQL 쿼리 및 인사이트 출력
    st.markdown("### 🔍 데이터 분석 로그 (SQL)")
    st.code(query, language='sql')

    # 인사이트 자동 계산
    max_row = df_result.iloc[0]
    best_festival = max_row['축제명']
    max_rate = max_row['증감률']

    st.markdown("---")
    st.subheader("💡 분석 인사이트")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**인사이트 1 — '인구 펌프'로서의 실효성 입증:**\n\n"
                f"평소 지방을 찾지 않던 외지인 인구가 '축제'라는 트리거를 통해 일시적으로 대규모 유입되는 현상을 확인할 수 있습니다. "
                f"**{best_festival}**의 경우 직전월 대비 개최월 방문자 수가 **{max_rate}%** 증가하며, "
                f"지역 축제의 외지인 유입 효과가 실질적임을 입증합니다.")
        
    with col2:
        st.success(f"**인사이트 2 — 단발성 유입의 한계와 정책적 시사점:**\n\n"
                   f"유입 효과가 강력할수록 '왜 축제 기간에만 방문하는가?'라는 역설적 질문을 던집니다. "
                   f"이는 체류형 관광 인프라 구축 및 교통망 연계 정책이 수반되어야 지속적인 지역 분산 효과를 달성할 수 있음을 시사합니다.")

    # 데이터 테이블 보여주기
    with st.expander("전체 데이터 보기"):
        st.dataframe(df_result)