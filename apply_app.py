# -*- coding: utf-8 -*-
"""
지원자용 공개 앱 (홈 + 지원하기 + 연구실 소개 + FAQ)
이 파일은 카페/학과 홈페이지 등 '공개 링크'로 배포하는 용도입니다.
관리자 기능은 이 앱에 전혀 포함되어 있지 않습니다. (admin_app.py 참고)

회차(SURF/WURF)가 바뀌면 이 파일이 아니라 config.py의 값들을 고치세요.
"""
import re
import datetime
from pathlib import Path
import streamlit as st

import scoring
import gsheets
import config
import theme

st.set_page_config(page_title="POSTECH 화학과 연구참여 프로그램", page_icon="🧪", layout="wide")
theme.inject()

CONTACT_INFO = "syuri@postech.ac.kr"


# ══════════════════════════ 공통 유틸 ══════════════════════════
def _mime_of(uploaded_file):
    return uploaded_file.type if uploaded_file is not None else "application/octet-stream"


def _read_bytes(uploaded_file):
    return uploaded_file.read() if uploaded_file is not None else None


def _is_valid_phone(v: str) -> bool:
    return bool(re.match(r"^01[0-9]-\d{3,4}-\d{4}$", str(v).strip()))


def _is_valid_birth(v: str) -> bool:
    return bool(re.match(r"^\d{4}\.\d{2}\.\d{2}$", str(v).strip()))


def _is_valid_email(v: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(v).strip()))


# ══════════════════════════ 홈 ══════════════════════════
def page_home():
    p = config.PROGRAM
    theme.hero(p["name"], p["intro"])

    c1, c2, c3 = st.columns(3)
    for col, label, val, note in [
        (c1, "참여기간", p["period"], p.get("period_note")),
        (c2, "접수마감", p["deadline"], p.get("deadline_note")),
        (c3, "합격자 발표", p["announce"], p.get("announce_note")),
    ]:
        with col:
            st.metric(label, val)
            if note:
                st.caption(note)

    st.info("👉 위쪽 **[지원하기]** 탭을 눌러 지원서를 작성해주세요.")

    st.divider()
    st.subheader("📢 공지사항")
    for n in config.NOTICES:
        body = n["body"]
        if body is None:
            body = (f"{p['name']} 참여기간: {p['period']} / 접수마감: {p['deadline']} "
                    f"({p.get('deadline_note','')})")
        with st.expander(f"[{n['status']}] {n['title']}  —  {n['date']}"):
            st.write(body)

    st.divider()
    st.subheader("🗂 지난 프로그램 이력")
    st.dataframe(
        [{"프로그램": h["name"], "기간": h["period"], "인원": h["count"]} for h in config.PAST_PROGRAMS],
        use_container_width=True, hide_index=True,
    )

    st.caption(
        f"관련 사이트: [화학과 홈페이지]({config.SITE_LINKS.get('dept','')}) · "
        f"[대학원 입학]({config.SITE_LINKS.get('grad_admission','')})"
    )




# ══════════════════════════ 연구실 소개 ══════════════════════════
def page_labs():
    st.header("🔬 참여 연구실 안내")
    st.caption("희망지도교수 1·2지망을 정하실 때 참고해주세요.")
    for field, labs in scoring.LABS.items():
        st.subheader(field)
        for lab in labs:
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{lab['name']} 교수님** — {lab['lab']}")
            with c2:
                if lab.get("url"):
                    st.link_button("연구실 홈페이지", lab["url"], use_container_width=True)
        st.divider()


# ══════════════════════════ FAQ ══════════════════════════
def page_faq():
    st.header("❓ 자주 묻는 질문")
    for item in config.FAQ_ITEMS:
        with st.expander(item["q"]):
            st.write(item["a"])

    st.divider()
    st.subheader("💬 문의하기")
    st.caption("자주 묻는 질문에 없는 내용은 아래에 남겨주세요. 답변이 등록되면 이 페이지에서 확인하실 수 있습니다.")

    with st.form("qna_form", clear_on_submit=True):
        q_name = st.text_input("이름 (선택, 비워두면 '익명'으로 표시됩니다)")
        q_pw = st.text_input("비밀번호 (본인 확인용, 4자리 이상 권장)", type="password")
        q_text = st.text_area("문의 내용 *", height=120)
        q_submitted = st.form_submit_button("문의 등록", use_container_width=True)

    if q_submitted:
        if not q_text.strip():
            st.error("문의 내용을 입력해주세요.")
        elif not q_pw.strip():
            st.error("비밀번호를 입력해주세요.")
        else:
            gsheets.append_question(q_name.strip(), q_pw.strip(), q_text.strip())
            st.success("문의가 등록되었습니다.")
            st.rerun()

    st.divider()
    st.subheader("📋 문의 내역")
    try:
        qdf = gsheets.read_all_questions()
    except Exception:
        qdf = None

    if qdf is None or qdf.empty:
        st.info("등록된 문의가 없습니다.")
    else:
        for _, r in qdf.sort_values("등록일시", ascending=False).iterrows():
            status = "✅ 답변완료" if str(r.get("답변여부")) == "Y" else "⏳ 답변대기"
            with st.expander(f"[{status}] {r.get('이름') or '익명'} — {r.get('등록일시')}"):
                st.write(r.get("질문", ""))
                if str(r.get("답변여부")) == "Y":
                    st.markdown("**➡ 답변**")
                    st.write(r.get("답변", ""))


# ══════════════════════════ 지원하기 ══════════════════════════
def page_apply():
    st.header("📝 지원서 작성")

    if st.session_state.get("submitted_ok"):
        st.success("지원이 정상적으로 완료되었습니다.")
        st.info(f"문의사항은 {CONTACT_INFO} 로 연락 부탁드립니다.")
        if st.button("새 지원서 작성"):
            del st.session_state["submitted_ok"]
            st.rerun()
        return

    with st.form("apply_form", clear_on_submit=False):
        st.subheader("1. 기본 정보")
        c1, c2 = st.columns(2)
        with c1:
            name_kr = st.text_input("성명 (한글) *", placeholder="예) 홍길동")
            birth = st.text_input("생년월일 *", placeholder="예) 2002.01.01")
            gender = st.selectbox("성별 *", ["남", "여"])
            phone = st.text_input("휴대폰번호 *", placeholder="예) 010-1234-5678")
        with c2:
            name_en = st.text_input("성명 (영문) *", placeholder="예) Hong, Gil-Dong")
            email = st.text_input("이메일 *", placeholder="예) example@school.ac.kr")

        st.subheader("2. 희망 지도교수")
        c3, c4 = st.columns(2)
        with c3:
            prof1 = st.selectbox("희망지도교수 (1지망) *", scoring.PROFESSORS)
        with c4:
            prof2 = st.selectbox("희망지도교수 (2지망) *", scoring.PROFESSORS,
                                  index=min(1, len(scoring.PROFESSORS) - 1))

        st.subheader("3. 학력")
        c5, c6, c7 = st.columns(3)
        with c5:
            school = st.text_input("학사 학교명 *", placeholder="예) 포항공과대학교")
        with c6:
            major = st.text_input("학사 전공명 *", placeholder="예) 화학과")
        with c7:
            admit_ym = st.text_input("입학 연월 *", placeholder="예) 2022-03")

        c8, c9, c10 = st.columns(3)
        with c8:
            semester = st.selectbox("학년 학기 *", ["3학년 1학기", "3학년 2학기", "4학년 1학기", "4학년 2학기"])
        with c9:
            scale = st.selectbox("기준평점(만점) *", ["4.5 만점", "4.3 만점"])
        with c10:
            gpa = st.text_input("평점 *", placeholder="예) 3.953")

        with st.expander("편입생인 경우에만 입력"):
            c11, c12, c13 = st.columns(3)
            with c11:
                t_school = st.text_input("전적 학사 학교명")
                t_scale = st.selectbox("전적 기준평점(만점)", ["", "4.5 만점", "4.3 만점"])
            with c12:
                t_major = st.text_input("전적 학사 전공명")
                t_gpa = st.text_input("전적 평점")
            with c13:
                t_admit_ym = st.text_input("전적 학교 입학 연월")

        st.subheader("4. 관심분야 및 지원동기")
        interests = st.multiselect("관심분야 *", ["유기화학", "무기화학", "물리화학", "분석화학", "고분자화학", "생화학"])
        motivation = st.text_area("자기소개 및 지원동기 * (최대 2000자)", max_chars=2000, height=180)

        c14, c15 = st.columns(2)
        with c14:
            grad_wish = st.selectbox("대학원 진학 희망 여부 *", ["희망하지 않음", "석사", "통합", "박사"])
        with c15:
            dorm = st.selectbox("생활관(기숙사) 사용 여부 *", ["O", "X"])

        st.subheader("5. 서류 제출")
        c16, c17 = st.columns(2)
        with c16:
            f_transcript = st.file_uploader("성적증명서 (PDF, 문서확인번호 포함) *", type=["pdf"])
            f_enrollment = st.file_uploader("재학증명서 (PDF, 2026년 3월 이후 발급) *", type=["pdf"])
        with c17:
            f_etc_list = st.file_uploader(
                "기타 우수성 입증 증빙 (선택, PDF, 여러 개 첨부 가능)",
                type=["pdf"], accept_multiple_files=True)
            f_photo = st.file_uploader("증명사진 (3.5*4.5) *", type=["jpg", "jpeg", "png"])

        st.subheader("6. 개인정보 수집·이용 동의")
        st.markdown("""
> **개인정보 수집·이용 안내**
> - **수집 항목**: 성명, 생년월일, 성별, 휴대폰번호, 이메일, 학교·전공·학점 정보, 자기소개 및 지원동기, 증명사진, 성적증명서·재학증명서 등 제출 서류
> - **수집 목적**: 연구참여 프로그램(SURF/WURF) 지원자 심사 및 선발, 선발 후 프로그램 운영·연락
> - **보유 및 이용 기간**: 접수일로부터 1년간 보관 후 파기 (구글드라이브 휴지통 경유 완전삭제)
> - 위 개인정보 수집·이용에 동의하지 않으실 경우, 지원 접수가 제한될 수 있습니다.
        """)
        consent_required = st.radio("개인정보 수집·이용 동의 (필수) *", ["예", "아니오"], horizontal=True, index=None)
        consent_optional = st.radio("개인정보 수집·이용 동의 (선택, 편입/기타증빙 해당자만)", ["예", "아니오"], horizontal=True, index=None)

        submitted = st.form_submit_button("지원서 제출", use_container_width=True, type="primary")

    if not submitted:
        return

    # ── 필수값 검증 ──
    required_missing = []
    for label, val in [
        ("성명(한글)", name_kr), ("성명(영문)", name_en), ("생년월일", birth), ("휴대폰번호", phone),
        ("이메일", email), ("학교명", school), ("전공명", major), ("입학연월", admit_ym), ("평점", gpa),
        ("지원동기", motivation),
    ]:
        if not str(val).strip():
            required_missing.append(label)
    if not interests:
        required_missing.append("관심분야")
    if consent_required != "예":
        required_missing.append("개인정보 수집·이용 동의(필수) - '예' 선택 필요")
    if f_transcript is None:
        required_missing.append("성적증명서 파일")
    if f_enrollment is None:
        required_missing.append("재학증명서 파일")
    if f_photo is None:
        required_missing.append("증명사진 파일")

    # ── 형식 검증 ──
    if str(phone).strip() and not _is_valid_phone(phone):
        required_missing.append("휴대폰번호 형식 (예: 010-1234-5678)")
    if str(birth).strip() and not _is_valid_birth(birth):
        required_missing.append("생년월일 형식 (예: 2002.01.01)")
    if str(email).strip() and not _is_valid_email(email):
        required_missing.append("이메일 형식")

    if required_missing:
        st.error("다음 항목을 확인해주세요: " + ", ".join(required_missing))
        return

    with st.spinner("제출 처리 중입니다... (파일 업로드에 시간이 걸릴 수 있어요)"):
        # 회차별 상위 폴더 (예: "2026_SURF") - 구글드라이브 안에서 회차별로 자동으로 나뉩니다.
        round_name = f"{datetime.datetime.now().year}_{config.PROGRAM['short_name']}"

        def _short_prof(p):
            return str(p).split(" 교수님")[0].strip()

        # 지원자 폴더명: "이름_1.교수님2.교수님" + 동명이인 방지용 짧은 시각 태그
        folder_key = (f"{name_kr}_1.{_short_prof(prof1)}2.{_short_prof(prof2)}"
                      f"_{datetime.datetime.now().strftime('%H%M%S')}")

        group, score43, grade = scoring.compute_score(school, scale, gpa)
        doc_pass = "합격" if scoring.is_document_pass(grade) else "미달"

        t_group = t_score43 = t_grade = ""
        if t_school.strip():
            t_group, t_score43, t_grade = scoring.compute_score(t_school, t_scale, t_gpa)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = {
            "접수번호": "", "제출일시": now, "프로그램구분": config.PROGRAM["short_name"],
            "성명_한글": name_kr, "성명_영문": name_en, "생년월일": birth, "성별": gender,
            "휴대폰번호": phone, "이메일": email,
            "희망지도교수_1지망": prof1, "희망지도교수_2지망": prof2,
            "학교명": school, "전공명": major, "입학연월": admit_ym, "학년학기": semester,
            "만점기준": scale, "평점": gpa,
            "편입_전적학교": t_school, "편입_전공": t_major, "편입_입학연월": t_admit_ym,
            "편입_만점기준": t_scale, "편입_평점": t_gpa,
            "대학군": group, "4.3환산": score43, "환산성적": grade,
            "관심분야": ", ".join(interests), "대학원진학희망": grad_wish, "희망과정": grad_wish,
            "기숙사사용": dorm, "지원동기": motivation,
            "개인정보_필수": consent_required, "개인정보_선택": consent_optional or "",
            "서류합격여부": doc_pass, "1지망선발여부": "", "비고": "",
        }

        # 파일 업로드 (구글드라이브)
        transcript_bytes = _read_bytes(f_transcript)
        enrollment_bytes = _read_bytes(f_enrollment)
        photo_bytes = _read_bytes(f_photo)

        row["성적증명서_링크"] = gsheets.upload_applicant_file(
            round_name, folder_key, f"성적증명서{Path(f_transcript.name).suffix}", transcript_bytes, _mime_of(f_transcript))
        row["재학증명서_링크"] = gsheets.upload_applicant_file(
            round_name, folder_key, f"재학증명서{Path(f_enrollment.name).suffix}", enrollment_bytes, _mime_of(f_enrollment))

        etc_links = []
        for i, f_etc in enumerate(f_etc_list or [], start=1):
            link = gsheets.upload_applicant_file(
                round_name, folder_key, f"기타증빙_{i}{Path(f_etc.name).suffix}", _read_bytes(f_etc), _mime_of(f_etc))
            etc_links.append(link)
        row["기타자료_링크"] = "\n".join(etc_links)

        row["증명사진_링크"] = gsheets.upload_applicant_file(
            round_name, folder_key, f"증명사진{Path(f_photo.name).suffix}", photo_bytes, _mime_of(f_photo))

        gsheets.append_applicant(row)

    st.session_state["submitted_ok"] = True
    st.rerun()


# ══════════════════════════ 라우팅 (관리자 탭 없음) ══════════════════════════
tab_home, tab_apply, tab_labs, tab_faq = st.tabs(["홈", "  지원하기  ", "연구실", "FAQ"])
with tab_home:
    page_home()
with tab_apply:
    page_apply()
with tab_labs:
    page_labs()
with tab_faq:
    page_faq()
