import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
import math

# 페이지 기본 설정
st.set_page_config(
    page_title="UpBox 전국 고객사 & 처리장 분석 시스템",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ UpBox 운영 분석 & 처리장 동선 추천 시스템")

# 주요 지역 좌표 딕셔너리
REGION_COORDS = {
    '서울': (37.5665, 126.9780), '강남구': (37.5172, 127.0473), '서초구': (37.4837, 127.0324),
    '송파구': (37.5145, 127.1060), '영등포구': (37.5263, 126.8962), '마포구': (37.5663, 126.9016),
    '중구': (37.5641, 126.9979), '종로구': (37.5730, 126.9794), '성동구': (37.5635, 127.0365),
    '경기': (37.4138, 127.5183), '수원시': (37.2636, 127.0286), '성남시': (37.4200, 127.1265),
    '고양시': (37.6584, 126.8320), '용인시': (37.2410, 127.1775), '화성시': (37.1995, 126.8312),
    '평택시': (36.9921, 127.1129), '인천': (37.4563, 126.7052), '부평구': (37.5070, 126.7218),
    '대전': (36.3504, 127.3845), '대구': (35.8714, 128.6014), '부산': (35.1796, 129.0756),
    '광주': (35.1595, 126.8526), '울산': (35.5384, 129.3114), '세종': (36.4800, 127.2890),
    '충북': (36.6357, 127.4912), '청주시': (36.6424, 127.4890), '충남': (36.5184, 126.8000),
    '천안시': (36.8151, 127.1139), '전북': (35.7175, 127.1530), '경북': (36.5760, 128.5056),
    '경남': (35.4606, 128.2132), '제주': (33.4996, 126.5312)
}

def get_fast_coordinates(addr):
    if not isinstance(addr, str) or addr == '주소 미입력':
        return 36.5, 127.5
    tokens = addr.split()
    for token in reversed(tokens[:3]):
        if token in REGION_COORDS:
            return REGION_COORDS[token]
    for key, (lat, lng) in REGION_COORDS.items():
        if key in addr:
            return lat, lng
    return 36.5, 127.5

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# 메인 탭 구성
tab1, tab2 = st.tabs(["🗺️ 1. 고객사 히트맵 & 작업량 분석", "🚚 2. 신규 업장 ➔ 최단 처리장 동선 추천"])

# ==========================================
# TAB 1: 고객사 히트맵 & 분석
# ==========================================
with tab1:
    st.subheader("📊 전국 고객사 배출 작업량 히트맵 분석")
    cust_file = st.file_uploader("📂 [고객사 데이터] 엑셀 파일(.xlsx)을 업로드하세요", type=["xlsx", "xls"], key="cust_upload")

    @st.cache_data
    def load_customer_data(file):
        df = pd.read_excel(file)
        addr_col = '✔️배출계약_Master - 고객사ID → 고객사 주소' if '✔️배출계약_Master - 고객사ID → 고객사 주소' in df.columns else df.columns[1]
        
        df['고객사명'] = df[df.columns[0]].astype(str).str.strip()
        df[addr_col] = df[addr_col].fillna('주소 미입력')
        df['차량종류'] = df['차량종류'].fillna('미지정') if '차량종류' in df.columns else '미지정'
        df['운영파트너명'] = df['운영파트너명'].fillna('미지정') if '운영파트너명' in df.columns else '미지정'
        df['폐기물종류소분류'] = df['폐기물종류소분류'].fillna('미지정') if '폐기물종류소분류' in df.columns else '미지정'
        
        vol_col = '작업량의 합계' if '작업량의 합계' in df.columns else df.columns[-1]
        df['작업량의 합계'] = pd.to_numeric(df[vol_col], errors='coerce').fillna(0)
        df['월평균수거량'] = (df['작업량의 합계'] / 12).round(1)
        
        coords = [get_fast_coordinates(a) for a in df[addr_col]]
        df['latitude'] = [c[0] for c in coords]
        df['longitude'] = [c[1] for c in coords]
        return df, addr_col

    if cust_file is not None:
        df, addr_col = load_customer_data(cust_file)
        
        st.sidebar.header("🔍 [탭1] 고객사 필터링")
        search_query = st.sidebar.text_input("고객사명 / 주소 검색", "", key="search_cust")
        
        all_partners = ["전체"] + sorted(df['운영파트너명'].unique().tolist())
        selected_partner = st.sidebar.selectbox("운영파트너 선택", all_partners)
        
        all_wastes = ["전체"] + sorted(df['폐기물종류소분류'].unique().tolist())
        selected_waste = st.sidebar.selectbox("폐기물종류 선택", all_wastes)
        
        all_vehicles = ["전체"] + sorted(df['차량종류'].unique().tolist())
        selected_vehicle = st.sidebar.selectbox("차량종류 선택", all_vehicles)
        
        map_mode = st.sidebar.radio("지도 표시 형태", ["월평균 작업량 히트맵", "고객사 위치 포인트(클러스터)", "전체 레이어 함께 보기"])

        filtered_df = df.copy()
        if selected_partner != "전체":
            filtered_df = filtered_df[filtered_df['운영파트너명'] == selected_partner]
        if selected_waste != "전체":
            filtered_df = filtered_df[filtered_df['폐기물종류소분류'] == selected_waste]
        if selected_vehicle != "전체":
            filtered_df = filtered_df[filtered_df['차량종류'] == selected_vehicle]
            
        if search_query:
            filtered_df = filtered_df[
                filtered_df['고객사명'].str.contains(search_query, case=False) |
                filtered_df[addr_col].str.contains(search_query, case=False)
            ]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("선택된 고객사 수", f"{filtered_df['고객사명'].nunique():,} 개")
        col2.metric("선택된 계약 건수", f"{len(filtered_df):,} 건")
        col3.metric("월평균 수거량 합계", f"{filtered_df['월평균수거량'].sum():,.1f} kg/월")
        col4.metric("12개월 누적 총 작업량", f"{filtered_df['작업량의 합계'].sum():,} kg")

        st.markdown("---")

        valid_coords_df = filtered_df.dropna(subset=['latitude', 'longitude'])
        center_lat = valid_coords_df['latitude'].mean() if not valid_coords_df.empty else 36.5
        center_lng = valid_coords_df['longitude'].mean() if not valid_coords_df.empty else 127.5

        m1 = folium.Map(location=[center_lat, center_lng], zoom_start=7, tiles="cartodbpositron")

        if map_mode in ["월평균 작업량 히트맵", "전체 레이어 함께 보기"]:
            heat_data = [[row['latitude'], row['longitude'], row['월평균수거량']] for _, row in valid_coords_df.iterrows() if row['월평균수거량'] > 0]
            if heat_data:
                HeatMap(heat_data, radius=25, blur=15, max_zoom=10).add_to(m1)

        if map_mode in ["고객사 위치 포인트(클러스터)", "전체 레이어 함께 보기"]:
            marker_cluster = MarkerCluster().add_to(m1)
            customer_summary = valid_coords_df.groupby(['고객사명', addr_col, 'latitude', 'longitude']).agg(
                total_monthly_vol=('월평균수거량', 'sum')
            ).reset_index()

            for _, row in customer_summary.iterrows():
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=f"<b>{row['고객사명']}</b><br>월평균: {row['total_monthly_vol']:,.1f} kg/월",
                    tooltip=row['고객사명']
                ).add_to(marker_cluster)

        map_data1 = st_folium(m1, width="100%", height=500, returned_objects=["last_object_clicked_tooltip"], key="map1")

        clicked_customer = map_data1.get("last_object_clicked_tooltip")
        if clicked_customer:
            st.subheader(f"📍 선택한 업장 상세 정보: [{clicked_customer}]")
            display_df = filtered_df[filtered_df['고객사명'] == clicked_customer]
        else:
            st.subheader("📊 선택 조건 전체 데이터 목록")
            display_df = filtered_df

        st.dataframe(display_df[['고객사명', addr_col, '폐기물종류소분류', '운영파트너명', '차량종류', '월평균수거량', '작업량의 합계']], use_container_width=True)
    else:
        st.info("👆 위에 보유하고 계신 [고객사 데이터 엑셀 파일]을 업로드해주세요.")


# ==========================================
# TAB 2: 신규 업장 ➔ 최단 처리장 동선 추천
# ==========================================
with tab2:
    st.subheader("🚚 신규 운영 검토 업장 ➔ 최단 동선 처리장 추천")
    
    col_input, col_facility = st.columns([1, 1])
    
    with col_input:
        st.markdown("#### 1️⃣ 신규 검토 업장 정보")
        target_address = st.text_input("신규 검토 업장 주소 입력 후 엔터", "경기 화성시 장안면 북부마을길 42")
        top_k = st.slider("추천받을 최단 거리 처리장 수", min_value=3, max_value=20, value=10)

    with col_facility:
        st.markdown("#### 2️⃣ [처리장 전용 데이터] 등록")
        facility_file = st.file_uploader("📂 처리장 목록 엑셀(.xlsx) 업로드", type=["xlsx", "xls"], key="facility_upload")

    # 처리장 데이터 자동 인식 로직
    if facility_file is not None:
        raw_f_df = pd.read_excel(facility_file)
        
        # 컬럼명 유연성 매핑 (영문/한글 모두 자동 대응)
        name_col = 'company_name' if 'company_name' in raw_f_df.columns else ('처리장명' if '처리장명' in raw_f_df.columns else raw_f_df.columns[0])
        addr_col = 'working_spot_address' if 'working_spot_address' in raw_f_df.columns else ('주소' if '주소' in raw_f_df.columns else raw_f_df.columns[1])
        type_col = 'waste_type' if 'waste_type' in raw_f_df.columns else ('구분' if '구분' in raw_f_df.columns else raw_f_df.columns[-1])
        
        facility_df = pd.DataFrame({
            '처리장명': raw_f_df[name_col],
            '주소': raw_f_df[addr_col],
            '구분': raw_f_df[type_col]
        })
    else:
        facility_data = [
            {"처리장명": "UpBox 화성 처리장", "주소": "경기 화성시 장안면", "구분": "소각/재활용"},
            {"처리장명": "UpBox 청주 리싸이클링", "주소": "충북 청주시 흥덕구", "구분": "재활용"},
            {"처리장명": "UpBox 하남 자원", "주소": "경기 하남시 풍산동", "구분": "수집운반/선별"},
            {"처리장명": "설성리싸이클링센터", "주소": "경기 이천시 설성면", "구분": "재활용"},
            {"처리장명": "표준산업 처리장", "주소": "경기 평택시 고덕면", "구분": "파쇄/소각"}
        ]
        facility_df = pd.DataFrame(facility_data)

    f_coords = [get_fast_coordinates(a) for a in facility_df['주소']]
    facility_df['latitude'] = [c[0] for c in f_coords]
    facility_df['longitude'] = [c[1] for c in f_coords]

    target_lat, target_lng = get_fast_coordinates(target_address)

    facility_df['직선거리_km'] = [
        haversine_distance(target_lat, target_lng, row['latitude'], row['longitude'])
        for _, row in facility_df.iterrows()
    ]

    top_facilities = facility_df.sort_values(by='직선거리_km').head(top_k).reset_index(drop=True)
    top_facilities['순위'] = top_facilities.index + 1

    st.markdown("---")
    st.markdown(f"### 🗺️ [{target_address}] 기준 최단 거리 처리장 Top {top_k} 동선 지도")
    
    m2 = folium.Map(location=[target_lat, target_lng], zoom_start=9, tiles="cartodbpositron")

    folium.Marker(
        location=[target_lat, target_lng],
        popup=f"<b>🏢 신규 검토 업장</b><br>{target_address}",
        tooltip="🏢 신규 검토 업장 (출발지)",
        icon=folium.Icon(color="green", icon="play", prefix="fa")
    ).add_to(m2)

    for _, row in top_facilities.iterrows():
        f_lat, f_lng = row['latitude'], row['longitude']
        rank = row['순위']
        dist = row['직선거리_km']
        
        folium.Marker(
            location=[f_lat, f_lng],
            popup=f"<b>{rank}위: {row['처리장명']}</b><br>📍 {row['주소']}<br>📏 거리: <b>{dist} km</b><br>폐기물: {row['구분']}",
            tooltip=f"{rank}위. {row['처리장명']} ({dist}km)",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m2)

        folium.PolyLine(
            locations=[[target_lat, target_lng], [f_lat, f_lng]],
            color="#e74c3c" if rank == 1 else "#3498db",
            weight=3 if rank == 1 else 1.5,
            opacity=0.8 if rank == 1 else 0.4,
            dash_array='5, 5'
        ).add_to(m2)

    st_folium(m2, width="100%", height=500, key="map2")

    st.subheader(f"📊 최단 거리 처리장 추천 목록 (가장 가까운 순서)")
    st.dataframe(
        top_facilities[['순위', '처리장명', '직선거리_km', '주소', '구분']],
        use_container_width=True
    )
