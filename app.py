import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

# 1. 페이지 레이아웃 설정
st.set_page_config(layout="wide", page_title="시흥시 의료이용지표 비교 대시보드")

@st.cache_data
def load_data():
    # 데이터 로드 (인코딩 CP949 적용)
    df = pd.read_csv("total_df_all.csv", encoding='cp949')
    with open("siheung_emd.geojson", encoding='utf-8') as f:
        geojson = json.load(f)
    
    # GeoJSON에서 각 동의 중심점(Centroid) 좌표 추출
    centroids = []
    for feature in geojson['features']:
        name = feature['properties']['EMD_NM']
        geometry = feature['geometry']
        if geometry['type'] == 'MultiPolygon':
            coords = geometry['coordinates'][0][0]
        else:
            coords = geometry['coordinates'][0]
        
        lon = sum(p[0] for p in coords) / len(coords)
        lat = sum(p[1] for p in coords) / len(coords)
        centroids.append({'EMD_NM': name, 'lat': lat, 'lon': lon})
    centroid_df = pd.DataFrame(centroids)
    
    return df, geojson, centroid_df

df, geojson, centroid_df = load_data()

# --- 사이드바: 동적 필터링 시스템 ---
st.sidebar.header("📊 분석 지표 선택")

# [수정] VAR_CODE 순으로 정렬하여 지표 리스트 생성
indicator_df = df[['VAR_CODE', 'VAR_LABEL']].drop_duplicates().sort_values('VAR_CODE')
indicator_list = indicator_df['VAR_LABEL'].tolist()
target_label = st.sidebar.selectbox("지표 선택", indicator_list)

# 선택된 지표의 데이터만 추출
df_indicator = df[df['VAR_LABEL'] == target_label]

st.sidebar.divider()
st.sidebar.header("⚙️ 유효 데이터 필터")

# 성별 선택: 선택된 지표에 실제로 존재하는 성별만 추출
raw_sex = df_indicator['SEX_TYPE_NM'].dropna().astype(str).unique()
sex_opts = ["전체"] + sorted([x for x in raw_sex if any(k in x for k in ['남', '여'])])
target_sex = st.sidebar.selectbox("성별", sex_opts)

# 연령대 선택: 선택된 지표에 실제로 존재하는 연령대만 추출
raw_age = df_indicator['AGEGRP_NM'].dropna().astype(str).unique()
age_opts = ["전체"] + sorted([x for x in raw_age if any(k in x for k in ['대', '세', '이상', '미만'])])
target_age = st.sidebar.selectbox("연령대", age_opts)

st.sidebar.divider()
st.sidebar.header("📅 비교 연도 설정")
year_list = sorted(df_indicator['year'].unique())
# 연도가 하나뿐일 경우를 대비한 인덱스 설정
year_left = st.sidebar.selectbox("왼쪽 지도 연도", year_list, index=0)
year_right = st.sidebar.selectbox("오른쪽 지도 연도", year_list, index=len(year_list)-1)

# --- 데이터 필터링 및 전처리 ---
filtered = df_indicator.copy()
if target_sex != "전체":
    filtered = filtered[filtered['SEX_TYPE_NM'].astype(str) == target_sex]
if target_age != "전체":
    filtered = filtered[filtered['AGEGRP_NM'].astype(str) == target_age]

filtered['EMD_NM'] = filtered['EMD_NM'].str.strip()
group_cols = ['year', 'EMD_NM', 'SEX_TYPE_NM', 'AGEGRP_NM']
filtered = filtered.groupby(group_cols).agg({'EVNT_CNT': 'sum', 'OBJTR_CNT': 'sum'}).reset_index()
filtered['rate'] = (filtered['EVNT_CNT'] / filtered['OBJTR_CNT'] * 100).fillna(0).round(2)

# --- 메인 화면 구성 ---
st.title(f"📍 시흥시 {target_label} 연도별 비교")
st.info(f"선택 필터: 성별({target_sex}), 연령대({target_age})")

# 지도를 위한 함수 정의
def create_comparison_map(target_year, data, geo_json, centers):
    map_data = data[data['year'] == target_year].copy()
    exclude_list = ['전체', '남성', '여성', '남', '여']
    map_data = map_data[~map_data['EMD_NM'].isin(exclude_list)]
    
    if map_data.empty:
        return None

    # 단계구분도 레이어
    fig = px.choropleth_mapbox(
        map_data, geojson=geo_json, color="rate",
        locations="EMD_NM", featureidkey="properties.EMD_NM",
        center={"lat": 37.38, "lon": 126.80},
        mapbox_style="carto-positron", zoom=9.5, opacity=0.7,
        color_continuous_scale="Reds",
        range_color=[filtered['rate'].min(), filtered['rate'].max()], 
        labels={'rate': '이용률(%)'}
    )
    
    # 중심점 텍스트 레이어 추가
    text_data = pd.merge(map_data, centers, on='EMD_NM')
    fig.add_trace(go.Scattermapbox(
        lat=text_data['lat'],
        lon=text_data['lon'],
        mode='text',
        text=text_data['EMD_NM'],
        textfont={'size': 11, 'color': 'black'},
        hoverinfo='none'
    ))
    
    fig.update_layout(margin={"r":0,"t":30,"l":0,"b":0}, showlegend=False)
    return fig

# 두 개의 컬럼으로 지도 배치
col_map1, col_map2 = st.columns(2)

with col_map1:
    st.subheader(f"⬅️ {year_left}년")
    fig_left = create_comparison_map(year_left, filtered, geojson, centroid_df)
    if fig_left:
        st.plotly_chart(fig_left, use_container_width=True, key="map_left")
    else:
        st.warning(f"{year_left}년 해당 필터의 데이터가 없습니다.")

with col_map2:
    st.subheader(f"➡️ {year_right}년")
    fig_right = create_comparison_map(year_right, filtered, geojson, centroid_df)
    if fig_right:
        st.plotly_chart(fig_right, use_container_width=True, key="map_right")
    else:
        st.warning(f"{year_right}년 해당 필터의 데이터가 없습니다.")

st.divider()

# --- 하단 시계열 추이 및 상세 데이터 ---
st.subheader("📅 행정동별 연도별 추이")
fig_line = px.line(filtered, x='year', y='rate', color='EMD_NM', markers=True, height=400)
st.plotly_chart(fig_line, use_container_width=True, key="line_chart")

st.subheader("📑 상세 통계 데이터")
display_df = filtered.sort_values(['year', 'EMD_NM'], ascending=[False, True]).copy()
display_df['year'] = display_df['year'].astype(str)
display_df.columns = ['연도', '행정동', '성별', '연령대', '발생건수', '대상자수', 'RATE(%)']

# DT(DataTable) 형태의 인터랙티브 테이블
st.dataframe(display_df, use_container_width=True, hide_index=True)
