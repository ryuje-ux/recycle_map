import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
import math
import sqlite3
import os

# 페이지 기본 설정
st.set_page_config(
    page_title="UpBox 전국 고객사 & 처리장 통합 분석 시스템",
    page_icon="🗺️",
    layout="wide"
)

# ==========================================
# 0. SQLite 데이터베이스(DB) 연동 및 관리
# ==========================================
DB_FILE = "upbox_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 고객사 테이블 생성
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            address TEXT,
            waste_type TEXT,
            partner_name TEXT,
            vehicle_type TEXT,
            work_volume REAL,
            monthly_volume REAL,
            latitude REAL,
            longitude REAL
        )
    ''')
    # 처리장 테이블 생성
    c.execute('''
        CREATE TABLE IF NOT EXISTS facilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility_name TEXT,
            address TEXT,
            waste_type TEXT,
            latitude REAL,
            longitude REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 전국 시/군/구 및 읍/면/동 상세 좌표 딕셔너리
REGION_COORDS = {
    '오남읍': (37.7121, 127.2065), '오남리': (37.7121, 127.2065), '진접읍': (37.7185, 127.2012), '화도읍': (37.6512, 127.3085),
    '불은면': (37.6835, 126.4789), '선원면': (37.7188, 126.4862), '청북읍': (37.0275, 126.9248), '송악읍': (36.9080, 126.6970),
    '한림면': (35.2985, 128.8152), '진례면': (35.2612, 128.7421), '대술면': (36.6542, 126.8921), '백암면': (37.1685, 127.3712),
    '양지면': (37.2341, 127.2842), '청산면': (36.3521, 127.7912), '온산읍': (35.4385, 129.3512), '향남읍': (37.1325, 126.9214),
    '장안면': (37.0785, 126.8285), '곤지암읍': (37.3512, 127.3485), '은현면': (37.8685, 127.0212), '통진읍': (37.6885, 126.5912),
    '정왕동': (37.3485, 126.7321), '학장동': (35.1435, 128.9852), '성곡동': (37.3112, 126.7785),
    '강남구': (37.5172, 127.0473), '서초구': (37.4837, 127.0324), '송파구': (37.5145, 127.1060), '강서구': (37.5509, 126.8495),
    '마포구': (37.5663, 126.9016), '영등포구': (37.5263, 126.8962), '노원구': (37.6542, 127.0568), '성동구': (37.5635, 127.0365),
    '수원시': (37.2636, 127.0286), '고양시': (37.6584, 126.8320), '용인시': (37.2410, 127.1775), '성남시': (37.4200, 127.1265),
    '부천시': (37.5034, 126.7660), '화성시': (37.1995, 126.8312), '안산시': (37.3219, 126.8309), '남양주시': (37.6360, 127.2165),
    '안양시': (37.3943, 126.9568), '평택시': (36.9921, 127.1129), '시흥시': (37.3802, 126.8029), '파주시': (37.7600, 126.7799),
    '의정부시': (37.7381, 127.0337), '김포시': (37.6153, 126.7156), '광명시': (37.4786, 126.8647), '광주시': (37.4087, 127.2582),
    '군포시': (37.3614, 126.9352), '이천시': (37.2723, 127.4350), '오산시': (37.1498, 127.0772), '하남시': (37.5393, 127.2148),
    '양주시': (37.7853, 127.0458), '구리시': (37.5943, 127.1295), '안성시': (37.0080, 127.2797), '포천시': (37.8949, 127.2003),
    '의왕시': (37.3447, 126.9682), '여주시': (37.2982, 127.6370), '양평군': (37.4917, 127.4875), '동두천시': (37.9035, 127.0607),
    '강화군': (37.7465, 126.4880), '남동구': (37.4469, 126.7315), '부평구': (37.5070, 126.7218), '사상구': (35.1526, 128.9912),
    '당진시': (36.8897, 126.6459), '김해시': (35.2285, 128.8894), '예산군': (36.6802, 126.8431), '옥천군': (36.3064, 127.5714),
    '청주시': (36.6424, 127.4890), '천안시': (36.8151, 127.1139), '대전': (36.3504, 127.3845), '부산': (35.1796, 129.0756),
    '울산': (35.5384, 129.3114), '대구': (35.8714, 128.6014), '광주': (35.1595, 126.8526), '제주': (33.4996, 126.5312)
}

def get_fast_coordinates(addr):
    if not isinstance(addr, str) or addr == '주소 미입력':
        return 36.5, 127.5
    tokens = addr.split()
    for token in reversed(tokens):
        if token in REGION_COORDS:
            return REGION_COORDS[token]
    for key, (lat, lng) in REGION_COORDS.items():
        if key in addr:
            return lat, lng
            
    base_lat, base_lng = 36.5, 127.5
    if '서울' in addr: base_lat, base_lng = 37.5665, 126.9780
    elif '경기' in addr: base_lat, base_lng = 37.4138, 127.5183
    elif '인천' in addr: base_lat, base_lng = 37.4563, 126.7052
    elif '충북' in addr or '충청북도' in addr: base_lat, base_lng = 36.6357, 127.4912
    elif '충남' in addr or '충청남도' in addr: base_lat, base_lng = 36.5184, 126.8000
    elif '경남' in addr or '경상남도' in addr: base_lat, base_lng = 35.4606, 128.2132
    elif '부산' in addr: base_lat, base_lng = 35.1796, 129.0756
    
    hash_offset = (hash(addr) % 1000) / 100000.0
    return base_lat + hash_offset, base_lng + hash_offset

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# DB 조회 함수
def get_db_customers():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM customers", conn)
    conn.close()
    return df

def get_db_facilities():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM facilities", conn)
    conn.close()
    return df

st.title("🗺️ UpBox 운영 분석 & 처리장 동선 추천 시스템")

# 메인 탭 구성
tab1, tab2 = st.tabs(["🗺️ 1. 고객사 히트맵 & 작업량 분석", "🚚 2. 신규 업장 ➔ 최단 처리장 동선 추천"])

# ==========================================
# TAB 1: 고객사 히트맵 & 분석
# ==========================================
with tab1:
    st.subheader("📊 전국 고객사 배출 작업량 히트맵 분석")
    
    with st.expander("📥 고객사 데이터 관리 (신규 직접 등록 / 엑셀 업로드)"):
        c1, c2 = st.columns([1, 1])
        
        with c1:
            st.markdown("##### ✍️ 웹에서 신규 고객사 직접 추가")
            with st.form("add_cust_form", clear_on_submit=True):
                new_name = st.text_input("고객사명", "롯데쇼핑(주) 신규점")
                new_addr = st.text_input("고객사 주소", "서울 강남구 테헤란로 100")
                new_waste = st.text_input("폐기물 종류", "[51-03-01]폐합성수지류")
                new_partner = st.text_input("운영파트너명", "UpBox강남")
                new_vehicle = st.text_input("차량 종류", "[50]집게차")
                new_vol = st.number_input("최근 12개월 누적 작업량 (kg)", value=120000.0)
                
                submitted = st.form_submit_button("💾 데이터베이스에 저장")
                if submitted:
                    monthly = round(new_vol / 12.0, 1)
                    lat, lng = get_fast_coordinates(new_addr)
                    
                    conn = sqlite3.connect(DB_FILE)
                    cur = conn.cursor()
                    cur.execute('''
                        INSERT INTO customers (customer_name, address, waste_type, partner_name, vehicle_type, work_volume, monthly_volume, latitude, longitude)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (new_name, new_addr, new_waste, new_partner, new_vehicle, new_vol, monthly, lat, lng))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ '{new_name}' 데이터가 DB에 성공적으로 저장되었습니다!")
                    st.rerun()

        with c2:
            st.markdown("##### 📂 엑셀 파일 데이터 일괄 저장 (DB Import)")
            cust_file = st.file_uploader("고객사 엑셀 파일(.xlsx) Upload", type=["xlsx", "xls"], key="cust_db_import")
            if cust_file is not None and st.button("📥 DB로 일괄 저장하기"):
                df_excel = pd.read_excel(cust_file)
                addr_col = '✔️배출계약_Master - 고객사ID → 고객사 주소' if '✔️배출계약_Master - 고객사ID → 고객사 주소' in df_excel.columns else df_excel.columns[1]
                vol_col = '작업량의 합계' if '작업량의 합계' in df_excel.columns else df_excel.columns[-1]
                
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()
                for _, row in df_excel.iterrows():
                    c_name = str(row[df_excel.columns[0]]).strip()
                    c_addr = str(row[addr_col]) if pd.notnull(row[addr_col]) else '주소 미입력'
                    c_waste = str(row['폐기물종류소분류']) if '폐기물종류소분류' in df_excel.columns and pd.notnull(row['폐기물종류소분류']) else '미지정'
                    c_partner = str(row['운영파트너명']) if '운영파트너명' in df_excel.columns and pd.notnull(row['운영파트너명']) else '미지정'
                    c_vehicle = str(row['차량종류']) if '차량종류' in df_excel.columns and pd.notnull(row['차량종류']) else '미지정'
                    
                    w_vol = pd.to_numeric(row[vol_col], errors='coerce')
                    w_vol = 0.0 if pd.isna(w_vol) else float(w_vol)
                    m_vol = round(w_vol / 12.0, 1)
                    lat, lng = get_fast_coordinates(c_addr)
                    
                    cur.execute('''
                        INSERT INTO customers (customer_name, address, waste_type, partner_name, vehicle_type, work_volume, monthly_volume, latitude, longitude)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (c_name, c_addr, c_waste, c_partner, c_vehicle, w_vol, m_vol, lat, lng))
                conn.commit()
                conn.close()
                st.success("🎉 엑셀 데이터가 DB로 일괄 저장되었습니다!")
                st.rerun()

    # DB에서 최신 데이터 가져오기
    df_cust = get_db_customers()

    if not df_cust.empty:
        st.sidebar.header("🔍 [탭1] 고객사 필터링")
        search_query = st.sidebar.text_input("고객사명 / 주소 검색", "", key="search_cust")
        
        all_partners = ["전체"] + sorted(df_cust['partner_name'].dropna().unique().tolist())
        selected_partner = st.sidebar.selectbox("운영파트너 선택", all_partners)
        
        all_wastes = ["전체"] + sorted(df_cust['waste_type'].dropna().unique().tolist())
        selected_waste = st.sidebar.selectbox("폐기물종류 선택", all_wastes)
        
        all_vehicles = ["전체"] + sorted(df_cust['vehicle_type'].dropna().unique().tolist())
        selected_vehicle = st.sidebar.selectbox("차량종류 선택", all_vehicles)
        
        map_mode = st.sidebar.radio("지도 표시 형태", ["월평균 작업량 히트맵", "고객사 위치 포인트(클러스터)", "전체 레이어 함께 보기"])

        filtered_df = df_cust.copy()
        if selected_partner != "전체":
            filtered_df = filtered_df[filtered_df['partner_name'] == selected_partner]
        if selected_waste != "전체":
            filtered_df = filtered_df[filtered_df['waste_type'] == selected_waste]
        if selected_vehicle != "전체":
            filtered_df = filtered_df[filtered_df['vehicle_type'] == selected_vehicle]
            
        if search_query:
            filtered_df = filtered_df[
                filtered_df['customer_name'].str.contains(search_query, case=False) |
                filtered_df['address'].str.contains(search_query, case=False)
            ]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("선택된 고객사 수", f"{filtered_df['customer_name'].nunique():,} 개")
        col2.metric("선택된 계약 건수", f"{len(filtered_df):,} 건")
        col3.metric("월평균 수거량 합계", f"{filtered_df['monthly_volume'].sum():,.1f} kg/월")
        col4.metric("12개월 누적 총 작업량", f"{filtered_df['work_volume'].sum():,.0f} kg")

        st.markdown("---")

        valid_coords_df = filtered_df.dropna(subset=['latitude', 'longitude'])
        center_lat = valid_coords_df['latitude'].mean() if not valid_coords_df.empty else 36.5
        center_lng = valid_coords_df['longitude'].mean() if not valid_coords_df.empty else 127.5

        m1 = folium.Map(location=[center_lat, center_lng], zoom_start=7, tiles="cartodbpositron")

        if map_mode in ["월평균 작업량 히트맵", "전체 레이어 함께 보기"]:
            heat_data = [[row['latitude'], row['longitude'], row['monthly_volume']] for _, row in valid_coords_df.iterrows() if row['monthly_volume'] > 0]
            if heat_data:
                HeatMap(heat_data, radius=25, blur=15, max_zoom=10).add_to(m1)

        if map_mode in ["고객사 위치 포인트(클러스터)", "전체 레이어 함께 보기"]:
            marker_cluster = MarkerCluster().add_to(m1)
            customer_summary = valid_coords_df.groupby(['customer_name', 'address', 'latitude', 'longitude']).agg(
                total_monthly_vol=('monthly_volume', 'sum')
            ).reset_index()

            for _, row in customer_summary.iterrows():
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=f"<b>{row['customer_name']}</b><br>월평균: {row['total_monthly_vol']:,.1f} kg/월",
                    tooltip=row['customer_name']
                ).add_to(marker_cluster)

        map_data1 = st_folium(m1, width="100%", height=500, returned_objects=["last_object_clicked_tooltip"], key="map1")

        clicked_customer = map_data1.get("last_object_clicked_tooltip")
        if clicked_customer:
            st.subheader(f"📍 선택한 업장 상세 정보: [{clicked_customer}]")
            display_df = filtered_df[filtered_df['customer_name'] == clicked_customer]
        else:
            st.subheader("📊 선택 조건 전체 DB 데이터 목록")
            display_df = filtered_df

        st.dataframe(
            display_df[['id', 'customer_name', 'address', 'waste_type', 'partner_name', 'vehicle_type', 'monthly_volume', 'work_volume']],
            use_container_width=True
        )
    else:
        st.info("💡 등록된 고객사 데이터가 없습니다. 상단 [고객사 데이터 관리]를 눌러 신규 추가하거나 엑셀을 업로드해주세요.")


# ==========================================
# TAB 2: 신규 업장 ➔ 최단 처리장 동선 추천
# ==========================================
with tab2:
    st.subheader("🚚 신규 운영 검토 업장 ➔ 최단 동선 처리장 추천")
    
    with st.expander("📥 처리장 데이터 관리 (신규 등록 / 엑셀 업로드)"):
        fc1, fc2 = st.columns([1, 1])
        
        with fc1:
            st.markdown("##### ✍️ 웹에서 신규 처리장 직접 추가")
            with st.form("add_facility_form", clear_on_submit=True):
                f_name = st.text_input("처리장명", "UpBox 남양주 리싸이클링")
                f_addr = st.text_input("처리장 주소", "경기 남양주시 오남읍 양지로 20")
                f_type = st.text_input("폐기물 구분/종류", "[51-28]폐지류 / 재활용")
                
                f_submitted = st.form_submit_button("💾 처리장 DB에 저장")
                if f_submitted:
                    f_lat, f_lng = get_fast_coordinates(f_addr)
                    conn = sqlite3.connect(DB_FILE)
                    cur = conn.cursor()
                    cur.execute('''
                        INSERT INTO facilities (facility_name, address, waste_type, latitude, longitude)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (f_name, f_addr, f_type, f_lat, f_lng))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ 처리장 '{f_name}' 저장 완료!")
                    st.rerun()

        with fc2:
            st.markdown("##### 📂 처리장 엑셀 파일 일괄 저장")
            facility_file = st.file_uploader("처리장 엑셀 파일 Upload", type=["xlsx", "xls"], key="facility_db_import")
            if facility_file is not None and st.button("📥 처리장 DB 일괄 저장"):
                raw_f_df = pd.read_excel(facility_file)
                name_col = 'company_name' if 'company_name' in raw_f_df.columns else ('처리장명' if '처리장명' in raw_f_df.columns else raw_f_df.columns[0])
                addr_col = 'working_spot_address' if 'working_spot_address' in raw_f_df.columns else ('주소' if '주소' in raw_f_df.columns else raw_f_df.columns[1])
                type_col = 'waste_type' if 'waste_type' in raw_f_df.columns else ('구분' if '구분' in raw_f_df.columns else raw_f_df.columns[-1])
                
                conn = sqlite3.connect(DB_FILE)
                cur = conn.cursor()
                for _, row in raw_f_df.iterrows():
                    fn = str(row[name_col]).strip()
                    fa = str(row[addr_col]) if pd.notnull(row[addr_col]) else '주소 미입력'
                    ft = str(row[type_col]) if pd.notnull(row[type_col]) else '미지정'
                    flat, flng = get_fast_coordinates(fa)
                    
                    cur.execute('''
                        INSERT INTO facilities (facility_name, address, waste_type, latitude, longitude)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (fn, fa, ft, flat, flng))
                conn.commit()
                conn.close()
                st.success("🎉 처리장 데이터가 DB로 일괄 저장되었습니다!")
                st.rerun()

    col_input, col_info = st.columns([1, 1])
    with col_input:
        target_address = st.text_input("신규 검토 업장 주소 입력 후 엔터", "경기 남양주시 오남읍 오남리 554-2")
        top_k = st.slider("추천받을 최단 거리 처리장 수", min_value=3, max_value=20, value=10)

    # DB에서 처리장 목록 읽기
    df_fac = get_db_facilities()

    if not df_fac.empty:
        target_lat, target_lng = get_fast_coordinates(target_address)

        df_fac['직선거리_km'] = [
            haversine_distance(target_lat, target_lng, row['latitude'], row['longitude'])
            for _, row in df_fac.iterrows()
        ]

        top_facilities = df_fac.sort_values(by='직선거리_km').head(top_k).reset_index(drop=True)
        top_facilities['순위'] = top_facilities.index + 1

        st.markdown("---")
        st.markdown(f"### 🗺️ [{target_address}] 기준 최단 거리 처리장 Top {top_k} 동선 지도")
        
        m2 = folium.Map(location=[target_lat, target_lng], zoom_start=9, tiles="cartodbpositron")

        # 출발지
        folium.Marker(
            location=[target_lat, target_lng],
            popup=f"<b>🏢 신규 검토 업장</b><br>{target_address}",
            tooltip="🏢 신규 검토 업장 (출발지)",
            icon=folium.Icon(color="green", icon="play", prefix="fa")
        ).add_to(m2)

        # 도착지 및 동선
        for _, row in top_facilities.iterrows():
            f_lat, f_lng = row['latitude'], row['longitude']
            rank = row['순위']
            dist = row['직선거리_km']
            
            folium.Marker(
                location=[f_lat, f_lng],
                popup=f"<b>{rank}위: {row['facility_name']}</b><br>📍 {row['address']}<br>📏 거리: <b>{dist} km</b><br>폐기물: {row['waste_type']}",
                tooltip=f"{rank}위. {row['facility_name']} ({dist}km)",
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(m2)

            folium.PolyLine(
                locations=[[target_lat, target_lng], [f_lat, f_lng]],
                color="#e74c3c" if rank == 1 else "#3498db",
                weight=3 if rank == 1 else 1.5,
                opacity=0.8 if rank == 1 else 0.5,
                dash_array='5, 5'
            ).add_to(m2)

        st_folium(m2, width="100%", height=500, key="map2")

        st.subheader(f"📊 최단 거리 처리장 추천 목록 (가장 가까운 순서)")
        st.dataframe(
            top_facilities[['순위', 'facility_name', '직선거리_km', 'address', 'waste_type']],
            use_container_width=True
        )
    else:
        st.info("💡 등록된 처리장 DB 데이터가 없습니다. 상단 [처리장 데이터 관리]를 열어 엑셀 업로드 또는 직접 등록을 먼저 해주세요.")
