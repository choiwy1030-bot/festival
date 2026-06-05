import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import os
import koreanize_matplotlib  # ✨ 이 줄이 한글 깨짐을 마법처럼 해결해줍니다!

# 페이지 설정
st.set_page_config(page_title="축제 방문객 대시보드", layout="wide")
st.title("📊 지역 축제 방문객 유입 효과 분석")

# 1. 데이터 로드 및 전처리
def load_data():
    file_active = '축제 개최월 방문자수.xlsx'
    file_before = '축제 직전월 방문자수.xlsx'
    
    if not os.path.exists(file_active) or not os.path.exists(file_before):
        st.error("❌ 엑셀 파일을 찾을 수 없습니다. 파일명을 확인해 주세요.")
        return None, None
    
    df_active = pd.read_excel(file_active)
    df_before = pd.read_excel(file_before)
    
    # SQL에서 에러가 나지 않도록 컬럼명 공백 제거
    df_active.columns = [c.replace(' ', '_') for c in df_active.columns]
    df_before.columns = [c.replace(' ', '_') for c in df_before.columns]
    
    return df_active, df_before

df_active, df_before = load_data()

if df_active is not None:
    # 2. SQL JOIN 수행
    conn = sqlite3.connect(':memory:')
    df_active.to_sql('개최월', conn, index=False)
    df_before.to_sql('직전월', conn, index=False)

    # 요구사항에 따른 SQL 문
    sql_query = """
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
    
    df_result = pd.read_sql_query(sql_query, conn)
    df_top7 = df_result.head(7).copy()
    
    # 축제명 줄바꿈 처리
    df_top7['축제명_display'] = df_top7['축제명'].apply(lambda x: x.replace(' ', '\n'))

    # 3. 차트 시각화
    st.subheader("📍 TOP 7 축제 방문객 유입 비교")
    
    # 스타일 설정
    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(12, 7))
    
    bar_width = 0.35
    index = range(len(df_top7))
    
    # 방문자 수 단위 변경 (명 -> 만 명)
    before_unit = df_top7['직전월_방문자수'] / 10000
    active_unit = df_top7['개최월_방문자수'] / 10000
    
    # 막대 그래프 (Before: 연한 회색, Active: 코랄색)
    bar1 = ax.bar([i - bar_width/2 for i in index], before_unit, bar_width, 
                  label='Before (직전월)', color='#D3D3D3')
    bar2 = ax.bar([i + bar_width/2 for i in index], active_unit, bar_width, 
                  label='Active (개최월)', color='#FF7F50')
    
    # 차트 꾸미기
    ax.set_title("지역 축제의 외지인 유입 효과: 직전월 vs 개최월 방문자 수 비교", fontsize=16, pad=20)
    ax.set_ylabel("방문자 수 (단위: 만 명)", fontsize=12)
    ax.set_xticks(index)
    ax.set_xticklabels(df_top7['축제명_display'], fontsize=10)
    ax.legend()

    # --- 정확한 방문자 수(만 명)와 증감률 표시 ---
    for i in range(len(df_top7)):
        # 직전월 수치 표시
        ax.text(i - bar_width/2, before_unit.iloc[i], f"{before_unit.iloc[i]:.1f}", 
                ha='center', va='bottom', fontsize=9, color='gray')
        # 개최월 수치 표시
        ax.text(i + bar_width/2, active_unit.iloc[i], f"{active_unit.iloc[i]:.1f}", 
                ha='center', va='bottom', fontsize=9, color='black', fontweight='bold')
        
        # 증감률 표시 (▲ +XXX%)
        rate = df_top7['증감률'].iloc[i]
        rate_color = 'red' if rate >= 100 else '#333333'
        ax.text(i + bar_width/2, active_unit.iloc[i] + (active_unit.max() * 0.05), 
                f"▲ +{rate}%", ha='center', va='bottom', 
                fontsize=11, fontweight='bold', color=rate_color)

    st.pyplot(fig)

    # 4. SQL 쿼리 출력
    with st.expander("📝 사용된 SQL JOIN Query 확인"):
        st.code(sql_query, language='sql')

    # 5. 인사이트 자동 출력
    max_row = df_result.iloc[0]
    st.markdown("---")
    st.subheader("💡 데이터 분석 인사이트")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**인사이트 1 — '인구 펌프'로서의 실효성 입증:**\n\n"
                f"평소 지방을 찾지 않던 외지인 인구가 '축제'라는 트리거를 통해 일시적으로 대규모 유입되는 현상을 확인할 수 있습니다. "
                f"**{max_row['축제명']}**의 경우 직전월 대비 개최월 방문자 수가 **{max_row['증감률']}%** 증가하며, "
                f"지역 축제의 외지인 유입 효과가 실질적임을 입증합니다.")
    
    with col2:
        st.success(f"**인사이트 2 — 단발성 유입의 한계와 정책적 시사점:**\n\n"
                   f"유입 효과가 강력할수록 '왜 축제 기간에만 방문하는가?'라는 역설적 질문을 던집니다. "
                   f"이는 체류형 관광 인프라 구축 및 교통망 연계 정책이 수반되어야 지속적인 지역 분산 효과를 달성할 수 있음을 시사합니다.")
