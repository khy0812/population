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
    
    # pandas는 zip 파일 내의 csv를 자동으로 압축 해제하여 읽을 수 있습니다.
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

# 5. 연령별/성별 인구 데이터 정리
# '남_0세', '여_0세' ~ '남_100세 이상', '여_100세 이상' 라벨 목록 생성
age_categories = [f"{i}세" for i in range(100)] + ["100세 이상"]

male_pop = []
female_pop = []

# 해당 행에서 연령별 남/여 인구수 추출
row_data = selected_row.iloc[0]

for age in age_categories:
    m_col = f"남_{age}"
    f_col = f"여_{age}"
    
    # 값이 없거나 결측치일 경우 0 처리
    m_val = row_data[m_col] if m_col in row_data and pd.notna(row_data[m_col]) else 0
    f_val = row_data[f_col] if f_col in row_data and pd.notna(row_data[f_col]) else 0
    
    male_pop.append(m_val)
    female_pop.append(f_val)

# 남성 인구수는 피라미드 좌측에 표시하기 위해 음수로 변환
male_pop_neg = [-val for val in male_pop]

# 6. Plotly 인구 피라미드 시각화
fig = go.Figure()

# 따뜻한 톤 칼라 설정 (남성: 따뜻한 코랄/오렌지계열, 여성: 따뜻한 피치/핑크계열)
# (취향에 맞게 조정 가능합니다)
MALE_COLOR = '#E07A5F'    # 코랄 브라운 / 오렌지 톤
FEMALE_COLOR = '#F4A261'  # 피치 오렌지 톤

# 남성 가로 막대그래프 (왼쪽)
fig.add_trace(go.Bar(
    y=age_categories,
    x=male_pop_neg,
    name='남성',
    orientation='h',
    marker=dict(color=MALE_COLOR),
    # 마우스 오버 시 실제 양수 값 표시
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
    hovertemplate='<b>%{y}</b><br>여성 인구: %{female_pop:,}명<extra></extra>'.replace('%{female_pop:,}', '%{x:,}')
))

# 그래프 레이아웃 설정
# x축 눈금 표시를 절대값(양수)으로 변환하기 위한 처리
max_val = max(max(male_pop), max(female_pop)) if (male_pop and female_pop) else 100
# 적절한 눈금 간격 계산
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
        # 축 뒤집기(autorange="reversed")나 값 크기 정렬 없이, 
        # categoryarray로 '0세'가 맨 아래, '100세 이상'이 맨 위로 오도록 완전 고정
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

# 7. 화면에 그래프 및 주요 통계 출력
st.plotly_chart(fig, use_container_width=True)

# 요약 데이터 카드
tot_m = sum(male_pop)
tot_f = sum(female_pop)
tot_all = tot_m + tot_f

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("총 인구수", f"{tot_all:,} 명")
col_m2.metric("남성 인구수", f"{tot_m:,} 명")
col_m3.metric("여성 인구수", f"{tot_f:,} 명")
