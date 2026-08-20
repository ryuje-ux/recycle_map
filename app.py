import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium

# 페이지 기본 설정
st.set_page_config(
    page_title="전국 고객사 작업량 분석 히트맵",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ 전국 고객사 작업량 분석 대시보드")

# 주요 지역/시군구 기준 좌표 딕셔너리
REGION_COORDS = {
    '서울': (37.5665, 126.9780), '강남구': (37.5172, 127.0473), '서초구': (37.4837, 127.0324),
    '송파구': (37.5145, 127.1060), '영등포구': (37.5263, 126.8962), '마포구': (37.5663, 126.9016),
    '중구': (37.5641, 126.9979), '종로구': (37.5730, 126.9794), '성동구': (37.5635, 127.0365),
    '광진구': (37.5385, 127.0823), '동대문구': (37.5744, 127.0400), '중랑구': (37.6066, 127.0927),
    '성북구': (37.5894, 127.0167), '강북구': (37.6396, 127.0257), '도봉구': (37.6688, 127.0471),
    '노원구': (37.6542, 127.0568), '은평구': (37.6027, 126.9291), '서대문구': (37.5791, 126.9368),
    '양천구': (37.5169, 126.8665), '강서구': (37.5509, 126.8495), '구로구': (37.4954, 126.8874),
    '금천구': (37.4568, 126.8952), '동작구': (37.5124, 126.9393), '관악구': (37.4784, 126.9516),
    '강동구': (37.5301, 127.1238), '경기': (37.4138, 127.5183), '수원시': (37.2636, 127.0286),
    '성남시': (37.4200, 127.1265), '고양시': (37.6584, 126.8320), '용인시': (37.2410, 127.1775),
    '부천시': (37.5034, 126.7660), '안산시': (37.3219, 126.8309), '안양시': (37.3943, 126.9568),
    '남양주시': (37.6360, 127.2165), '화성시': (37.1995, 126.8312), '평택시': (36.9921, 127.1129),
    '의정부시': (37.7381, 127.0337), '파주시': (37.7600, 126.7799), '시흥시': (37.3802, 126.8029),
    '김포시': (37.6153, 126.7156), '광명시': (37.4786, 126.8647), '광주시': (37.4087, 127.2582),
    '군포시': (37.3614, 126.9352), '이천시': (37.2723, 127.4350), '오산시': (37.1498, 127.0772),
    '하남시': (37.5393, 127.2148), '양주시': (37.7853, 127.0458), '구리시': (37.5943, 127.1295),
    '안성시': (37.0080, 127.2797), '포천시': (37.8949, 127.2003), '의왕시': (37.3447, 126.9682),
    '여주시': (37.2982, 127.6370), '양평군': (37.4917, 127.4875), '동두천시': (37.9035, 127.0607),
    '인천': (37.4563, 126.7052), '부평구': (37.5070, 126.7218), '대전': (36.3504, 127.3845),
    '서구': (36.3551, 127.3838), '대구': (35.8714, 128.6014), '부산': (35.1796, 129.0756),
    '광주': (35.1595, 126.8526), '울산': (35.5384, 129.3114), '세종': (36.4800, 127.2890),
    '강원': (37.8228, 128.1555), '원주시': (37.3422, 127.9201), '충북': (36.6357, 127.4912),
    '청주시': (36.6424, 127.4890), '충남': (36.5184, 126.8000), '천안시': (36.8151, 127.1139),
    '전북': (35.7175, 127.1530), '전주': (35.8242, 127.1480), '전남': (34.8679, 126.9910),
    '경북': (36.5760, 128.5056), '포항': (36.0190, 129.3435), '경남': (35.4606, 128.2132),
    '창원': (35.2280, 128.6811), '제주': (33.4996, 126.5312)
}

def get_fast_coordinates(addr):
    if not isinstance(addr, str) or addr == '주소 미입력':
        return None, None
    tokens = addr.split()
    for token in reversed(tokens[:3]):
        if token in REGION_COORDS:
            return REGION_COORDS[token]
    for key, (lat, lng) in REGION_COORDS.items():
        if key in addr:
            return lat, lng
    return 36.5, 127.5

st.sidebar.header("📁 데이터 업로드 및 필터")
uploaded_file = st.sidebar.file_uploader("엑셀 파일(.xlsx)을 업로드하세요", type=["xlsx", "xls"])

@st.cache_data
def load_data(file):
    df = pd.read_excel(file)
    addr_col = '✔️배출계약_Master - 고객사ID → 고객사 주소'
    
    df['고객사명'] = df['고객사명'].astype(str).str.strip()
    df[addr_col] = df[addr_col].fillna('주소 미입력')
    df['차량종류'] = df['차량종류'].fillna('미지정')
    df['운영파트너명'] = df['운영파트너명'].fillna('미지정')
    df['폐기물종류소분류'] = df['폐기물종류소분류'].fillna('미지정')
    
    # 누적 작업량 및 월평균 수거량 계산 (12개월 기준)
    df['작업량의 합계'] = pd.to_numeric(df['작업량의 합계'], errors='coerce').fillna(0)
    df['월평균수거량'] = (df['작업량의 합계'] / 12).round(1)
    
    # 좌표 매핑
    coords = [get_fast_coordinates(a) for a in df[addr_col]]
    df['latitude'] = [c[0] for c in coords]
    df['longitude'] = [c[1] for c in coords]
    
    return df, addr_col

if uploaded_file is not None:
    df, addr_col = load_data(uploaded_file)
    
    st.sidebar.subheader("🔍 조건 필터링")
    search_query = st.sidebar.text_input("고객사명 / 주소 검색", "")
    
    all_partners = sorted(df['운영파트너명'].unique().tolist())
    selected_partners = st.sidebar.multiselect("운영파트너 선택", all_partners, default=all_partners)
    
    all_wastes = sorted(df['폐기물종류소분류'].unique().tolist())
    selected_wastes = st.sidebar.multiselect("폐기물종류 선택", all_wastes, default=all_wastes)
    
    all_vehicles = sorted(df['차량종류'].unique().tolist())
    selected_vehicles = st.sidebar.multiselect("차량종류 선택", all_vehicles, default=all_vehicles)
    
    map_mode = st.sidebar.radio("지도 표시 형태", ["월평균 작업량 히트맵", "고객사 위치 포인트(클러스터)", "전체 레이어 함께 보기"])

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

    # 상단 지표 (KPI) - 월평균 수거량 강조
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("선택된 고객사 수", f"{filtered_df['고객사명'].nunique():,} 개")
    col2.metric("선택된 계약 건수", f"{len(filtered_df):,} 건")
    col3.metric("월평균 수거량 합계", f"{filtered_df['월평균수거량'].sum():,.1f} kg/월")
    col4.metric("12개월 누적 총 작업량", f"{filtered_df['작업량의 합계'].sum():,} kg")

    st.markdown("---")

    valid_coords_df = filtered_df.dropna(subset=['latitude', 'longitude'])
    
    if not valid_coords_df.empty:
        center_lat = valid_coords_df['latitude'].mean()
        center_lng = valid_coords_df['longitude'].mean()
    else:
        center_lat, center_lng = 36.5, 127.5

    m = folium.Map(location=[center_lat, center_lng], zoom_start=7, tiles="cartodbpositron")

    # 1) 히트맵 레이어 (월평균 수거량 기준)
    if map_mode in ["월평균 작업량 히트맵", "전체 레이어 함께 보기"]:
        heat_data = [
            [row['latitude'], row['longitude'], row['월평균수거량']]
            for _, row in valid_coords_df.iterrows()
            if row['월평균수거량'] > 0
        ]
        if heat_data:
            HeatMap(heat_data, radius=25, blur=15, max_zoom=10).add_to(m)

    # 2) 클러스터 및 팝업 마커
    if map_mode in ["고객사 위치 포인트(클러스터)", "전체 레이어 함께 보기"]:
        marker_cluster = MarkerCluster().add_to(m)
        
        # 고객사별 집계 데이터 (월평균 수거량 합계 + 폐기물별 배출량)
        customer_summary = valid_coords_df.groupby(['고객사명', addr_col, 'latitude', 'longitude']).agg(
            total_monthly_vol=('월평균수거량', 'sum'),
            total_annual_vol=('작업량의 합계', 'sum'),
            partners=('운영파트너명', lambda x: ", ".join(set(x))),
            waste_types=('폐기물종류소분류', lambda x: ", ".join(set(x)))
        ).reset_index()

        for _, row in customer_summary.iterrows():
            # 고객사별 세부 폐기물 배출량 목록 렌더링
            cust_items = valid_coords_df[valid_coords_df['고객사명'] == row['고객사명']]
            details_html = ""
            for _, item in cust_items.iterrows():
                details_html += f"<li><b>{item['폐기물종류소분류']}</b>: 약 {item['월평균수거량']:,.1f} kg/월 ({item['운영파트너명']})</li>"

            popup_html = f"""
            <div style="font-family: Arial, sans-serif; width:260px; line-height:1.4;">
                <h4 style="margin:0 0 5px 0; color:#1f77b4;">🏢 {row['고객사명']}</h4>
                <p style="font-size:12px; color:gray; margin:0 0 8px 0;">📍 {row[addr_col]}</p>
                
                <div style="background-color:#f8f9fa; padding:8px; border-radius:5px; margin-bottom:8px;">
                    <p style="margin:0; font-size:14px;"><b>📦 월평균 배출량:</b> <span style="color:#d62728; font-weight:bold;">{row['total_monthly_vol']:,.1f} kg/월</span></p>
                    <p style="margin:3px 0 0 0; font-size:11px; color:gray;">(최근 12개월 누적: {row['total_annual_vol']:,} kg)</p>
                </div>
                
                <p style="margin:4px 0; font-size:12px;"><b>🚚 운영파트너:</b> {row['partners']}</p>
                <hr style="margin:6px 0;">
                <p style="margin:4px 0; font-size:12px;"><b>📋 폐기물별 월평균 수거량:</b></p>
                <ul style="margin:4px 0 0 0; padding-left:18px; font-size:11px;">
                    {details_html}
                </ul>
            </div>
            """
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=f"{row['고객사명']} (월 {row['total_monthly_vol']:,.1f}kg)"
            ).add_to(marker_cluster)

    st_folium(m, width="100%", height=600)

    with st.expander("📊 선택된 상세 데이터 목록 보기"):
        st.dataframe(filtered_df[['고객사명', addr_col, '폐기물종류소분류', '운영파트너명', '차량종류', '월평균수거량', '작업량의 합계']])

else:
    st.info("👈 좌측 사이드바에서 보유하고 계신 엑셀 파일(.xlsx)을 업로드해주세요.")
