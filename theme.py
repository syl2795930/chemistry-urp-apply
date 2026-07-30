# -*- coding: utf-8 -*-
"""
config.py의 BRAND 컬러를 이용해 Streamlit 기본 위젯 위에 커스텀 CSS를 입히는 공용 모듈.
apply_app.py, admin_app.py 양쪽에서 똑같이 불러다 씁니다.

100% 픽셀 단위로 React 미리보기와 동일하지는 않지만, 색상 톤 · 버튼 · 탭 · 카드
모양을 최대한 맞춥니다.
"""
import streamlit as st
import config


def inject():
    b = config.BRAND
    st.markdown(f"""
    <style>
    /* 전체 배경 */
    .stApp {{
        background-color: {b['page_bg']};
    }}

    /* 상단 헤더(툴바) 배경 투명화 */
    header[data-testid="stHeader"] {{
        background-color: transparent;
    }}

    /* 제목/헤더 색상 */
    h1, h2, h3 {{
        color: {b['primary_dark']} !important;
    }}

    /* 기본(primary) 버튼 - 지원서 제출, 저장 등 */
    .stButton>button[kind="primary"],
    .stFormSubmitButton>button[kind="primary"],
    button[kind="primary"] {{
        background-color: {b['primary']};
        border-color: {b['primary']};
        border-radius: 8px;
        font-weight: 600;
    }}
    .stButton>button[kind="primary"]:hover,
    .stFormSubmitButton>button[kind="primary"]:hover,
    button[kind="primary"]:hover {{
        background-color: {b['primary_dark']};
        border-color: {b['primary_dark']};
    }}

    /* 보조(secondary) 버튼 테두리 색 */
    .stButton>button[kind="secondary"] {{
        border-color: {b['primary_light']};
        border-radius: 8px;
        color: {b['primary_dark']};
    }}

    /* 탭 - 선택된 탭 밑줄/글자색 */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        color: {b['primary']};
        border-bottom-color: {b['primary']} !important;
        font-weight: 600;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        border-bottom: 1px solid {b['primary_light']};
    }}

    /* 카드형 컨테이너(metric, expander) */
    div[data-testid="stMetric"] {{
        background-color: #FFFFFF;
        border: 1px solid {b['primary_light']};
        border-radius: 10px;
        padding: 14px 16px;
    }}
    div[data-testid="stMetricValue"] {{
        color: {b['primary_dark']};
    }}

    .streamlit-expanderHeader, div[data-testid="stExpander"] {{
        border-radius: 8px;
    }}
    div[data-testid="stExpander"] {{
        border: 1px solid {b['primary_light']} !important;
        background-color: #FFFFFF;
    }}

    /* 링크 버튼 */
    .stLinkButton>a {{
        border-color: {b['primary_light']};
        color: {b['primary_dark']};
        border-radius: 8px;
    }}

    /* info/success 등 알림 박스 톤 맞추기 */
    div[data-testid="stAlertContainer"] {{
        border-radius: 8px;
    }}

    /* 구분선 색상 */
    hr {{
        border-color: {b['primary_light']};
    }}
    </style>
    """, unsafe_allow_html=True)


def hero(title: str, subtitle: str = ""):
    """홈 화면 상단 히어로 카드 (미리보기의 분홍 배경 인트로 박스와 유사한 스타일)."""
    b = config.BRAND
    sub_html = f"<p style='font-size:14px;color:#444;line-height:1.7;margin:10px 0 0;'>{subtitle}</p>" if subtitle else ""
    st.markdown(f"""
    <div style="background:{b['page_bg']};border:1px solid {b['primary_light']};
                border-radius:10px;padding:28px;margin-bottom:20px;">
        <div style="font-size:12px;font-weight:600;color:{b['primary']};
                    letter-spacing:0.04em;margin-bottom:8px;">🧪 POSTECH 화학과 연구참여 프로그램</div>
        <h1 style="font-size:24px;font-weight:700;margin:0 0 8px;color:{b['primary_dark']};">{title}</h1>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)
