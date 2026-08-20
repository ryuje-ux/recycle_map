import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# 페이지 기본 설정
st.set_page_config(
    page_title="전국 고객사 작업량 분석 히트맵",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ 전국 고객사 작업량 분석 대시보드")

# 사이드바 설정
st.sidebar.header("📁 데이터 업로드 및 필터")
uploaded_file = st.sidebar.file_uploader("엑셀 파일(.xlsx)을 업로드하세요", type=["xlsx", "xls"])

@st.cache_data
def load_data(file):
    df = pd.read_excel(file)
    addr_col = '✔️배출계약_Master - 고객사ID → 고객사 주소'
    
    # 결측치 및 데이터 타입 정밀 전처리
    df['고객사명'] = df['고객사명'].astype(str).str.strip()
    df[addr_col] = df[addr_col].fillna('주소 미입력')
    df['차량종류'] = df['차량종류'].fillna('미지정')
    df['운영파트너명'] = df['운영파트너명'].fillna('미지정')
    df['폐기물종류소분류'] = df['폐기물종류소분류'].fillna('미지정')
    df['작업량의 합계'] = pd.to_numeric(df['작업량의 합계'], errors='coerce').fillna(0)
    
    return df, addr_col

@st.cache_data
def geocode_addresses(addresses):
    geolocator = Nominatim(user_agent="upbox_heatmap_app_v1")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=0.1)
    
    coords = {}
    for addr in set(addresses):
        if addr == '주소 미입력' or not str(addr).strip():
            continue
        try:
            location = geocode(str(addr))
            if location:
                coords[addr] = (location.latitude, location.longitude)
        except Exception:
            pass
    return coords

if uploaded_file is not None:
    df, addr_col = load_data(uploaded_file)
    
    unique_addrs = df[addr_col].dropna().unique()
    with st.spinner("주소 데이터를 위도/경도 좌표로 변환 중입니다... (최초 1회 소요)"):
        coords = geocode_addresses(unique_addrs)
    
    df['latitude'] = df[addr_col].map(lambda x: coords.get(x, (None, None))[0])
    df['longitude'] = df[addr_col].map(lambda x: coords.get(x, (None, None))[1])
    
    # 사이드바 필터링 옵션
    st.sidebar.subheader("🔍 조건 필터링")
    
    search_query = st.sidebar.text_input("고객사명 / 주소 검색", "")
    
    all_partners = sorted(df['운영파트너명'].unique().tolist())
    selected_partners = st.sidebar.multiselect("운영파트너 선택", all_partners, default=all_partners)
    
    all_wastes = sorted(df['폐기물종류소분류'].unique().tolist())
    selected_wastes = st.sidebar.multiselect("폐기물종류 선택", all_wastes, default=all_wastes)
    
    all_vehicles = sorted(df['차량종류'].unique().tolist())
    selected_vehicles = st.sidebar.multiselect("차량종류 선택", all_vehicles, default=all_vehicles)
    
    map_mode = st.sidebar.radio("지도 표시 형태", ["작업량 히트맵", "고객사 위치 포인트(클러스터)", "전체 레이어 함께 보기"])

    filtered_df = df[
        (df['운영파트너명'].isin(selected_partners)) &
        (df['폐기물종류소분류'].isin(selected_wastes)) &
        (df['차량종류'].isin(selected_vehicles))
    ]
    
    if search_query:
        filtered_df = filtered_df[
            filtered_df['고객사명'].str.contains(search_query, case=False) |
            filtered_df[addr_col].str.contains(search_query, case=False)
        ]

    # 주요 지표 (KPI)
    col1, col2, col3 = st.columns(3)
    col1.metric("선택된 고객사 수", f"{filtered_df['고객사명'].nunique():,} 개")
    col2.metric("선택된 데이터 건수", f"{len(filtered_df):,} 건")
    col3.metric("총 작업량 합계", f"{filtered_df['작업량의 합계'].sum():,} kg")

    st.markdown("---")

    # 지도 렌더링
    valid_coords_df = filtered_df.dropna(subset=['latitude', 'longitude'])
    
    if not valid_coords_df.empty:
        center_lat = valid_coords_df['latitude'].mean()
        center_lng = valid_coords_df['longitude'].mean()
    else:
        center_lat, center_lng = 36.5, 127.5

    m = folium.Map(location=[center_lat, center_lng], zoom_start=7, tiles="cartodbpositron")

    # 1) 히트맵 레이어
    if map_mode in ["작업량 히트맵", "전체 레이어 함께 보기"]:
        heat_data = [
            [row['latitude'], row['longitude'], row['작업량의 합계']]
            for _, row in valid_coords_df.iterrows()
            if row['작업량의 합계'] > 0
        ]
        if heat_data:
            HeatMap(heat_data, radius=25, blur=15, max_zoom=10).add_to(m)

    # 2) 클러스터링 및 팝업 마커 레이어
    if map_mode in ["고객사 위치 포인트(클러스터)", "전체 레이어 함께 보기"]:
        marker_cluster = MarkerCluster().add_to(m)
        
        customer_summary = valid_coords_df.groupby(['고객사명', addr_col, 'latitude', 'longitude']).agg(
            total_volume=('작업량의 합계', 'sum'),
            partners=('운영파트너명', lambda x: ", ".join(set(x))),
            waste_types=('폐기물종류소분류', lambda x: ", ".join(set(x)))
        ).reset_index()

        for _, row in customer_summary.iterrows():
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; width:220px;">
                <h4 style="margin-bottom:5px;">{row['고객사명']}</h4>
                <p style="font-size:12px; color:gray; margin-top:0;">📍 {row[addr_col]}</p>
                <hr style="margin:5px 0;">
                <p><b>총 작업량:</b> {row['total_volume']:,} kg</p>
                <p><b>운영파트너:</b> {row['partners']}</p>
                <p><b>폐기물 종류:</b> {row['waste_types']}</p>
            </div>
            """
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=row['고객사명']
            ).add_to(marker_cluster)

    st_folium(m, width="100%", height=600)

    with st.expander("📊 선택된 데이터 목록 보기"):
        st.dataframe(filtered_df[['고객사명', addr_col, '폐기물종류소분류', '운영파트너명', '차량종류', '작업량의 합계']])

else:
    st.info("👈 좌측 사이드바에서 보유하고 계신 엑셀 파일(.xlsx)을 업로드해주세요.")
