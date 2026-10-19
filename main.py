import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="👨‍👩‍👧‍👦",
    layout="centered"
)

# 2. 제목 및 설명
st.title("👨‍👩‍👧‍👦 동네별 인구 피라미드")
st.markdown("원하는 **시도 → 시군구 → 동**을 선택하여 연령별/성별 인구 구조를 확인해 보세요.")

# 3. 데이터 로드 (캐싱을 적용하여 속도 향상)
@st.cache_data
def load_data():
    # GitHub Zip 파일 URL
    url = "https://github.com/khy0812/population/raw/main/population_ts_yearly_gender%20(1).zip"
    
    # pandas는 zip 파일 내의 csv를 자동으로 압축 해제하여 읽습니다.
    df = pd.read_csv(url)
    
    # 데이터에 존재하는 가장 최신 연도만 추출
    latest_year = df['연도'].max()
    df_latest = df[df['연도'] == latest_year].copy()
    
    return df_latest, latest_year

# 데이터 불러오기
try:
    with st.spinner("데이터를 불러오는 중입니다..."):
        df, max_year = load_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

st.caption(f" 기준 연도: {max_year}년 데이터")

# 4. 지역 선택 드롭다운 (시도 -> 시군구 -> 동)
col1, col2, col3 = st.columns(3)

with col1:
    sido_list = sorted(df['시도'].dropna().unique())
    selected_sido = st.selectbox("시·도 선택", sido_list)

# 선택한 시도에 해당하는 시군구 목록 추출
df_sido = df[df['시도'] == selected_sido]

with col2:
    sigungu_list = sorted(df_sido['시군구'].dropna().unique())
    selected_sigungu = st.selectbox("시·군·구 선택", sigungu_list)

# 선택한 시군구에 해당하는 동 목록 추출
df_sigungu = df_sido[df_sido['시군구'] == selected_sigungu]

with col3:
    dong_list = sorted(df_sigungu['동'].dropna().unique())
    selected_dong = st.selectbox("읍·면·동 선택", dong_list)

# 최종 선택된 지역 데이터 1행 추출
selected_row = df_sigungu[df_sigungu['동'] == selected_dong]

if selected_row.empty:
    st.warning("선택한 지역의 데이터가 없습니다.")
    st.stop()

# 5. 연령별/성별 인구 데이터 정리 및 통계 계산
age_categories = [f"{i}세" for i in range(100)] + ["100세 이상"]

male_pop = []
female_pop = []
total_pop_by_age = []  # 각 나이별 총 인구수 (평균 연령 계산용)

row_data = selected_row.iloc[0]

# 연령별 데이터 추출
for age_idx, age in enumerate(age_categories):
    m_col = f"남_{age}"
    f_col = f"여_{age}"
    
    m_val = row_data[m_col] if m_col in row_data and pd.notna(row_data[m_col]) else 0
    f_val = row_data[f_col] if f_col in row_data and pd.notna(row_data[f_col]) else 0
    
    male_pop.append(m_val)
    female_pop.append(f_val)
    total_pop_by_age.append(m_val + f_val)

# 남성 인구수는 피라미드 좌측에 표시하기 위해 음수로 변환
male_pop_neg = [-val for val in male_pop]

# --- 핵심 주요 지표 계산 ---
total_population = sum(total_pop_by_age)  # 총인구

if total_population > 0:
    # 1) 평균 연령 계산 (가중 평균: 0~99세는 나이 값, 100세 이상은 100세로 계산)
    weighted_age_sum = sum(count * (idx if idx < 100 else 100) for idx, count in enumerate(total_pop_by_age))
    avg_age = weighted_age_sum / total_population

    # 2) 유소년(0~14세) 및 고령(65세 이상) 인구수 계산
    youth_pop = sum(total_pop_by_age[0:15])        # 0세~14세
    elderly_pop = sum(total_pop_by_age[65:])        # 65세 이상
    
    # 3) 비율 계산 (%)
    aging_rate = (elderly_pop / total_population) * 100
    youth_rate = (youth_pop / total_population) * 100
else:
    avg_age = 0.0
    aging_rate = 0.0
    youth_rate = 0.0

# 6. 그래프 위에 지표 카드 3개 표시 (총인구, 평균연령, 고령화율)
m1, m2, m3 = st.columns(3)

m1.metric("총 인구수", f"{total_population:,} 명")
m2.metric("평균 연령", f"{avg_age:.1f} 세")

# 고령화율 20% 이상 시 초고령사회 주의 표시 (⚠️)
if aging_rate >= 20.0:
    m3.metric("고령화율 (65세+)", f"{aging_rate:.1f} %", delta="⚠️ 초고령 (20% 이상)", delta_color="inverse")
else:
    m3.metric("고령화율 (65세+)", f"{aging_rate:.1f} %")

st.markdown("---")

# 7. Plotly 인구 피라미드 시각화
fig = go.Figure()

MALE_COLOR = '#E07A5F'    # 코랄 브라운 톤
FEMALE_COLOR = '#F4A261'  # 피치 오렌지 톤

# 남성 가로 막대그래프 (왼쪽)
fig.add_trace(go.Bar(
    y=age_categories,
    x=male_pop_neg,
    name='남성',
    orientation='h',
    marker=dict(color=MALE_COLOR),
    customdata=male_pop,
    hovertemplate='<b>%{y}</b><br>남성 인구: %{customdata:,}명<extra></extra>'
))

# 여성 가로 막대그래프 (오른쪽)
fig.add_trace(go.Bar(
    y=age_categories,
    x=female_pop,
    name='여성',
    orientation='h',
    marker=dict(color=FEMALE_COLOR),
    hovertemplate='<b>%{y}</b><br>여성 인구: %{x:,}명<extra></extra>'
))

# x축 눈금 양수 변환
max_val = max(max(male_pop), max(female_pop)) if (male_pop and female_pop) else 100
step = max(1, int(max_val / 4))
tick_vals = list(range(-((max_val // step + 1) * step), (max_val // step + 2) * step, step))
tick_text = [f"{abs(v):,}" for v in tick_vals]

fig.update_layout(
    title=dict(
        text=f"<b>{selected_sido} {selected_sigungu} {selected_dong}</b> 인구 피라미드",
        font=dict(size=18)
    ),
    barmode='overlay',
    bargap=0.1,
    xaxis=dict(
        title="인구 수 (명)",
        tickmode='array',
        tickvals=tick_vals,
        ticktext=tick_text,
        gridcolor='#F0F0F0'
    ),
    yaxis=dict(
        title="연령",
        # 0세가 맨 아래, 100세 이상이 맨 위로 순서 고정
        type='category',
        categoryorder='array',
        categoryarray=age_categories,
        showgrid=False
    ),
    plot_bgcolor='white',
    paper_bgcolor='white',
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    height=750,
    margin=dict(l=60, r=40, t=80, b=50)
)

st.plotly_chart(fig, use_container_width=True)

# 8. 피라미드 하단 자동 한 줄 설명 (아이가 많은지 vs 어르신이 많은지)
if aging_rate >= 20.0 and youth_rate < 10.0:
    summary_text = "👴 **어르신 비중이 매우 높은 동네입니다.** (고령화율 20% 이상 초고령 지역)"
elif aging_rate > youth_rate:
    summary_text = "👵 **아이보다 어르신 비중이 더 높은 동네입니다.**"
elif youth_rate > aging_rate:
    summary_text = "👶 **어르신보다 아이 비중이 더 높은 젊은 동네입니다.**"
else:
    summary_text = "⚖️ **아이와 어르신 비중이 균형을 이루고 있는 동네입니다.**"

st.info(f"💡 **이 동네는 어떤가요?** {summary_text} (유소년 {youth_rate:.1f}% / 고령인구 {aging_rate:.1f}%)")
