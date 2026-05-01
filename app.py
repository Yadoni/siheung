import streamlit as st
import pandas as pd
import plotly.express as px
import json

# 페이지 레이아웃 설정
st.set_page_config(layout="wide", page_title="시흥시 의료이용 지표 대시보드")

@st.cache_data
def load_data():
    # 1. 통합 데이터 로드
    df = pd.read_csv("total_df_all.csv", encoding='cp949')
    # 2. GeoJSON 로드
    with open("siheung_emd.geojson", encoding='utf-8') as f:
        geojson = json.load(f)
    return df, geojson

df, geojson = load_data()

# 사이드바: 필터링 도구
st.sidebar.header("📊 분석 필터")
target_label = st.sidebar.selectbox("지표 선택", df['VAR_LABEL'].unique())
target_sex = st.sidebar.selectbox("성별", ["전체", "남", "여"])
target_year = st.sidebar.select_slider("지도 표시 연도", options=sorted(df['year'].unique()), value=2024)

# 데이터 필터링 로직
filtered = df[df['VAR_LABEL'] == target_label].copy()
if target_sex != "전체":
    filtered = filtered[filtered['SEX_TYPE_NM'] == target_sex]

# 이용률 계산 (예시: 이벤트수/대상자수 * 100)
filtered['rate'] = (filtered['EVNT_CNT'] / filtered['OBJTR_CNT'] * 100).round(2)

# 메인 화면 구성
st.title(f"시흥시 {target_label} 시각화 리포트")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📅 연도별 추이 (행정동별)")
    # Plotly 대화형 선 그래프
    fig_line = px.line(filtered, x='year', y='rate', color='EMD_NM', markers=True,
                       labels={'rate': '이용률 (%)', 'year': '연도'})
    st.plotly_chart(fig_line, use_container_width=True)

with col2:
    st.subheader(f"📍 {target_year}년 행정동별 분포")
    map_data = filtered[filtered['year'] == target_year]
    # Plotly 지도 시각화
    fig_map = px.choropleth_mapbox(
        map_data, geojson=geojson, color="rate",
        locations="EMD_NM", featureidkey="properties.EMD_NM",
        center={"lat": 37.38, "lon": 126.80},
        mapbox_style="carto-positron", zoom=10, opacity=0.6,
        labels={'rate': '이용률 (%)'}
    )
    st.plotly_chart(fig_map, use_container_width=True)

st.divider()

# 하단: 상세 통계 표
st.subheader("📑 상세 통계 테이블")
st.dataframe(filtered.sort_values(['year', 'EMD_NM']), use_container_width=True)
