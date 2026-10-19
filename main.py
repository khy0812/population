import json
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="전국 고령화 단계구분도",
    page_icon="🗺️",
    layout="wide"
)

# 2. 제목 및 설명
st.title("🗺️ 전국 시군구 고령화 단계구분도")
st.markdown("2026년 최신 기준, 전국 시·군·구별 고령인구(65세 이상) 비율(%)을 지도로 확인해 보세요.")

# 3. 데이터 및 GeoJSON 캐싱 로드 함수
@st.cache_data
def load_geojson():
    # 시군구 경계 GeoJSON Raw URL
    geojson_url = "https://raw.githubusercontent.com/khy0812/population/main/sigungu_kr.geojson.txt"
    response = requests.get(geojson_url)
    geojson_data = response.json()
    
    # feature의 '코드' 속성을 문자열로 확실하게 변환
    for feature in geojson_data['features']:
        feature['properties']['코드'] = str(feature['properties']['코드']).zfill(5)
        
    return geojson_data

@st.cache_data
def load_and_process_population_data():
    # 인구 데이터 Zip Raw URL
    pop_url = "https://github.com/khy0812/population/raw/main/population_ts_yearly_gender%20(1).zip"
    
    # pandas로 압축 CSV 직접 읽기
    df = pd.read_csv(pop_url)
    
    # 2026년 데이터만 선택
    df_2026 = df[df['연도'] == 2026].copy()
    
    # 시군구 5자리 코드 생성 (문자열 변환 및 5자리 맞춰 채우기)
    df_2026['sigungu_code'] = df_2026['코드'].astype(str).str.zfill(8).str[:5]
    
    # 인구수 열 분류 ('계_'로 시작하는 열만 대상, 남_/여_ 열 제외)
    total_cols = [col for col in df_2026.columns if col.startswith('계_')]
    
    # 65세 이상 열 목록 생성
    age_65_plus_cols = [f"계_{i}세" for i in range(65, 100)] + ["계_100세 이상"]
    # 데이터 프레임에 존재하며 '계_'로 시작하는 65세 이상 열만 선택
    elderly_cols = [col for col in age_65_plus_cols if col in total_cols]
    
    # 각 동별 전체 인구 및 65세 이상 인구 합계
    df_2026['total_pop'] = df_2026[total_cols].sum(axis=1)
    df_2026['elderly_pop'] = df_2026[elderly_cols].sum(axis=1)
    
    # 시군구 5자리 코드로 그룹화하여 집계
    sigungu_df = df_2026.groupby('sigungu_code', as_index=False).agg({
        '시도': 'first',
        '시군구': 'first',
        'total_pop': 'sum',
        'elderly_pop': 'sum'
    })
    
    # 고령화율(%) 계산
    sigungu_df['aging_rate'] = (sigungu_df['elderly_pop'] / sigungu_df['total_pop']) * 100
    sigungu_df['aging_rate'] = sigungu_df['aging_rate'].round(1)
    
    # 풀 시군구 명칭 (예: 서울특별시 종로구)
    sigungu_df['full_name'] = sigungu_df['시도'] + " " + sigungu_df['시군구']
    
    return sigungu_df

# 데이터 불러오기
try:
    with st.spinner("지도 데이터 및 인구 데이터를 불러오는 중입니다..."):
        geojson_data = load_geojson()
        sigungu_df = load_and_process_population_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# 4. 요약 통계 카드 배치
col1, col2, col3, col4 = st.columns(4)

total_kr_pop = sigungu_df['total_pop'].sum()
total_kr_elderly = sigungu_df['elderly_pop'].sum()
avg_kr_aging_rate = (total_kr_elderly / total_kr_pop) * 100

super_aged_count = (sigungu_df['aging_rate'] >= 20.0).sum()
highest_row = sigungu_df.loc[sigungu_df['aging_rate'].idxmax()]

col1.metric("전국 총 인구", f"{total_kr_pop:,} 명")
col2.metric("전국 고령화율", f"{avg_kr_aging_rate:.1f} %")
col3.metric("초고령 시군구(20%+)", f"{super_aged_count} 개 지역")
col4.metric("최고 고령화 지역", f"{highest_row['full_name']}", f"{highest_row['aging_rate']}%")

st.markdown("---")

# 5. Plotly Choropleth (단계구분도) 생성
# 배경 지도(타일) 없이 경계만 표시, 진한 붉은 톤/오렌지 톤(Reds) 색상 적용
fig = px.choropleth(
    sigungu_df,
    geojson=geojson_data,
    locations='sigungu_code',
    featureidkey="properties.코드",
    color='aging_rate',
    color_continuous_scale="Reds",
    range_color=(10, 40),
    hover_name='full_name',
    hover_data={
        'sigungu_code': False,
        'aging_rate': ':.1f',
        'total_pop': ':,',
        'elderly_pop': ':,'
    },
    labels={
        'aging_rate': '고령화율 (%)',
        'total_pop': '전체 인구 (명)',
        'elderly_pop': '65세 이상 인구 (명)'
    }
)

# 지도 스타일 및 레이아웃 설정 (배경 타일 제거)
fig.update_geos(
    fitbounds="locations",
    visible=False,
    showcountries=False,
    showcoastlines=False,
    showland=False
)

fig.update_layout(
    height=750,
    margin={"r": 0, "t": 30, "l": 0, "b": 0},
    coloraxis_colorbar=dict(
        title="고령화율 (%)",
        thickness=15,
        len=0.8,
        ticksuffix="%"
    )
)

# 6. 지도 출력
st.plotly_chart(fig, use_container_width=True)

# 7. 하단 데이터 테이블 (선택 사항)
with st.expander("📊 시군구별 고령화율 상세 데이터 보기"):
    st.dataframe(
        sigungu_df[['sigungu_code', '시도', '시군구', 'total_pop', 'elderly_pop', 'aging_rate']]
        .sort_values(by='aging_rate', ascending=False)
        .rename(columns={
            'sigungu_code': '시군구코드',
            'total_pop': '총인구(명)',
            'elderly_pop': '65세이상인구(명)',
            'aging_rate': '고령화율(%)'
        }),
        use_container_width=True,
        hide_index=True
    )
