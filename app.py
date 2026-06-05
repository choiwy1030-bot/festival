import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import os

# 1. 한글 폰트 설정 (더 강력한 버전)
def set_korean_font():
    import platform
    from matplotlib import font_manager, rc
    
    plt.rcParams['axes.unicode_minus'] = False
    
    system_name = platform.system()
    try:
        if system_name == 'Windows':
            # 윈도우: 맑은 고딕
            rc('font', family='Malgun Gothic')
        elif system_name == 'Darwin':
            # 맥: 애플 고딕
            rc('font', family='AppleGothic')
        else:
            # 리눅스/Streamlit Cloud: 나눔고딕 설치 여부 확인 후 설정
            # 시스템에 설치된 폰트 중 'Nanum'이 포함된 폰트를 찾습니다.
            font_list = font_manager.findSystemFonts(fontpaths=None, fontext='ttf')
            nanum_font = [f for f in font_list if 'Nanum' in f]
            if nanum_font:
                font_name = font_manager.FontProperties(fname=nanum_font[0]).get_name()
                rc('font', family=font_name)
            else:
                # 폰트가 없을 경우의 대비책
                st.warning("⚠️ 한글 폰트(나눔고딕)를 찾을 수 없습니다. 리포지토리에 폰트 파일을 포함하는 것을 권장합니다.")
    except Exception as e:
        st.error(f"폰트 설정 중 오류 발생: {e}")

set_korean_font()

st.title("📊 지역 축제 방문객 유입 효과 분석")

# 2. 데이터 로드 및 전처리
def load_and_clean_data():
    file_active = '축제 개최월 방문자수.xlsx'
    file_before = '축제 직전월 방문자수.xlsx'
    
    if not os.path.exists(file_active) or not os.path.exists(file_before):
        st.error("❌ 엑셀 파일이 없습니다! 파일명을 확인해주세요.")
        return None, None
    
    df_active = pd.read_excel(file_active)
    df_before = pd.read_excel(file_before)
    
    # 컬럼명 공백 제거 (SQL 에러 방지)
    df_active.columns = [c.replace(' ', '_') for c in df_active.columns]
    df_before.columns = [c.replace(' ', '_') for c in df_before.columns]
    
    return df_active, df_before

df_active, df_before = load_and_clean_data()

if df_active is not None:
    # SQL JOIN
    conn = sqlite3.connect(':memory:')
    df_active.to_sql('개최월', conn, index=False)
    df_before.to_sql('직전월', conn, index=False)

    query = """
    SELECT 
        a.축제명, a.지역명,
        b.직전월_방문자수,
        a.개최월_방문자수,
        ROUND((CAST(a.개최월_방문자수 AS FLOAT) - b.직전월_방문자수) / b.직전월_방문자수 * 100, 1) AS 증감률
    FROM 개최월 AS a
    JOIN 직전월 AS b ON a.축제명 = b.축제명
    ORDER BY 증감률 DESC;
    """
    
    df_result = pd.read_sql_query(query, conn)
    df_top7 = df_result.head(7).copy()
    df_top7['축제명_display'] = df_top7['축제명'].apply(lambda x: x.replace(' ', '\n'))

    # 3. 차트 시각화
    st.subheader("📍 TOP 7 축제 방문객 유입 비교")
    
    fig, ax = plt.subplots(figsize=(12, 8))
    bar_width = 0.35
    index = range(len(df_top7))

    # 데이터 단위 변경 (명 -> 만 명)
    before_vals = df_top7['직전월_방문자수'] / 10000
    active_vals = df_top7['개최월_방문자수'] / 10000

    bar1 = ax.bar([i - bar_width/2 for i in index], before_vals, bar_width, label='Before (직전월)', color='#D3D3D3')
    bar2 = ax.bar([i + bar_width/2 for i in index], active_vals, bar_width, label='Active (개최월)', color='#FF7F50')

    # 차트 제목 및 라벨 (한글 적용 확인)
    ax.set_title("지역 축제의 외지인 유입 효과: 직전월 vs 개최월 방문자 수 비교", fontsize=18, pad=20)
    ax.set_ylabel("방문자 수 (단위: 만 명)", fontsize=13)
    ax.set_xticks(index)
    ax.set_xticklabels(df_top7['축제명_display'], fontsize=11)
    ax.legend()

    # --- [수정사항] 막대 위에 정확한 수치(만 명) 표시 ---
    def add_value_labels(bars):
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.1f}만', ha='center', va='bottom', fontsize=9, color='#555555')

    add_value_labels(bar1)
    add_value_labels(bar2)

    # --- [수정사항] 개최월 막대 상단에 증감률 표시 ---
    for i, row in df_top7.iterrows():
        rate = row['증감률']
        color = 'red' if rate >= 100 else 'black'
        # 증감률 기호 추가 (▲)
        ax.text(i + bar_width/2, active_vals[i] + (active_vals[i]*0.1), 
                f"▲ {rate}%", ha='center', va='bottom', 
                fontsize=11, fontweight='bold', color=color)

    st.pyplot(fig)

    # SQL 출력
    st.markdown("#### 💻 사용된 SQL 쿼리")
    st.code(query, language='sql')

    # 인사이트 자동 계산
    max_row = df_result.iloc[0]
    st.markdown("---")
    st.subheader("💡 분석 인사이트")
    
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**인사이트 1 — '인구 펌프' 효과:**\n\n"
                f"**{max_row['축제명']}**의 경우 직전월 대비 방문자가 **{max_row['증감률']}%** 증가하며 "
                f"축제가 강력한 인구 유입 트리거임을 증명했습니다.")
    with c2:
        st.success(f"**인사이트 2 — 정책적 시사점:**\n\n"
                   f"단기 유입 인구를 정주 인구 또는 재방문자로 전환하기 위한 '체류형 관광 콘텐츠' 확충이 필요합니다.")
