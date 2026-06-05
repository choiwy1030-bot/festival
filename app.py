import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import os

# 한글 폰트 설정
def set_korean_font():
    import platform
    from matplotlib import font_manager, rc
    plt.rcParams['axes.unicode_minus'] = False
    try:
        if platform.system() == 'Windows':
            rc('font', family='Malgun Gothic')
        elif platform.system() == 'Darwin':
            rc('font', family='AppleGothic')
        else:
            rc('font', family='NanumGothic')
    except:
        pass

set_korean_font()

st.title("📊 지역 축제 방문객 유입 효과 분석")

# 데이터 로드 및 컬럼명 정리 함수
def load_and_clean_data():
    file_active = '축제 개최월 방문자수.xlsx'
    file_before = '축제 직전월 방문자수.xlsx'
    
    if not os.path.exists(file_active) or not os.path.exists(file_before):
        st.error("❌ 엑셀 파일이 폴더에 없습니다. 파일명을 확인해주세요!")
        return None, None
    
    df_active = pd.read_excel(file_active)
    df_before = pd.read_excel(file_before)
    
    # [핵심 수정!] 컬럼명의 띄어쓰기를 언더바(_)로 강제 변경
    # 예: '개최월 방문자수' -> '개최월_방문자수'
    df_active.columns = [c.replace(' ', '_') for c in df_active.columns]
    df_before.columns = [c.replace(' ', '_') for c in df_before.columns]
    
    return df_active, df_before

df_active, df_before = load_and_clean_data()

if df_active is not None:
    conn = sqlite3.connect(':memory:')
    df_active.to_sql('개최월', conn, index=False)
    df_before.to_sql('직전월', conn, index=False)

    # 이제 쿼리문의 '개최월_방문자수'와 데이터의 컬럼명이 완벽히 일치합니다!
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
    
    try:
        df_result = pd.read_sql_query(query, conn)
        
        # 차트 그리기 (상위 7개)
        df_top7 = df_result.head(7).copy()
        df_top7['축제명_display'] = df_top7['축제명'].apply(lambda x: x.replace(' ', '\n'))

        fig, ax = plt.subplots(figsize=(10, 6))
        bar_width = 0.35
        index = range(len(df_top7))

        ax.bar([i - bar_width/2 for i in index], df_top7['직전월_방문자수']/10000, bar_width, label='Before', color='#D3D3D3')
        ax.bar([i + bar_width/2 for i in index], df_top7['개최월_방문자수']/10000, bar_width, label='Active', color='#FF7F50')

        ax.set_title("지역 축제의 외지인 유입 효과: 직전월 vs 개최월", fontsize=15)
        ax.set_xticks(index)
        ax.set_xticklabels(df_top7['축제명_display'])
        ax.legend()

        # 증감률 표시
        for i, row in df_top7.iterrows():
            ax.text(i + bar_width/2, (row['개최월_방문자수']/10000), f"▲{row['증감률']}%", 
                    ha='center', va='bottom', fontweight='bold', color='red' if row['증감률'] >= 100 else 'black')

        st.pyplot(fig)

        # SQL 및 인사이트 출력
        st.info("### 📋 실행된 SQL Query")
        st.code(query, language='sql')

        max_row = df_result.iloc[0]
        st.markdown(f"""
        **💡 분석 인사이트 1**  
        {max_row['축제명']}의 경우 증감률이 **{max_row['증감률']}%**에 달해 지역 축제의 유입 효과를 입증합니다.
        
        **💡 분석 인사이트 2**  
        단발성 유입을 넘어선 체류형 관광 인프라 구축이 필요합니다.
        """)

    except Exception as e:
        st.error(f"SQL 실행 중 오류가 발생했습니다: {e}")
