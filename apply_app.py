# -*- coding: utf-8 -*-
"""
지원자용 공개 앱 (홈 + 지원하기 + 연구실 소개 + FAQ)
이 파일은 카페/학과 홈페이지 등 '공개 링크'로 배포하는 용도입니다.
관리자 기능은 이 앱에 전혀 포함되어 있지 않습니다. (admin_app.py 참고)

회차(SURF/WURF)가 바뀌면 이 파일이 아니라 config.py의 값들을 고치세요.
"""
import re
import base64
import datetime
from pathlib import Path
import streamlit as st

import scoring
import gsheets
import config
import theme
import pdf_gen

st.set_page_config(page_title="POSTECH 화학과 연구참여 프로그램", page_icon=theme.mascot_icon(), layout="wide")
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


def _is_valid_ym(v: str) -> bool:
    """입학연월 형식(YYYY-MM) 검증. 월은 01~12만 허용."""
    return bool(re.match(r"^\d{4}-(0[1-9]|1[0-2])$", str(v).strip()))


# ══════════════════════════ 홈 ══════════════════════════
@st.dialog("소식 받기")
def _subscribe_dialog():
    st.caption("지원 여부와 상관없이, 원하시는 소식을 이메일로 받아보실 수 있어요.")
    with st.form("subscribe_form", border=False):
        sub_email = st.text_input("이메일", placeholder="example@school.ac.kr")
        sub_research = st.checkbox("연구참여 프로그램(SURF/WURF) 관련 소식 받기")
        sub_admission = st.checkbox("화학과 입시(설명회 등) 관련 정보 받기")
        # type="primary"로 Streamlit 기본 테마 색과 계속 충돌하던 문제를 피하려고,
        # 이 프로젝트에서 계속 안정적으로 먹혔던 '이름표 붙은 상자로 감싸서 그 이름표로
        # 스타일 주기' 방식으로 바꿨다. type은 기본값(secondary)으로 두고 색은 직접 입힌다.
        with st.container(key="subscribe_submit_wrap"):
            sub_submit = st.form_submit_button("신청", use_container_width=True)
    theme.inject_css(
        '.st-key-subscribe_submit_wrap button {'
        f'background-color:{config.BRAND["primary"]} !important; '
        f'border-color:{config.BRAND["primary"]} !important; color:#fff !important; }}'
        '.st-key-subscribe_submit_wrap button p { color:#fff !important; font-weight:600 !important; }'
        '.st-key-subscribe_submit_wrap button:hover {'
        f'background-color:{config.BRAND["primary_dark"]} !important; }}'
    )
    if sub_submit:
        if not _is_valid_email(sub_email):
            st.error("이메일 형식을 확인해주세요.")
        elif not (sub_research or sub_admission):
            st.error("받고 싶은 소식을 하나 이상 선택해주세요.")
        else:
            gsheets.add_subscriber(sub_email, sub_research, sub_admission)
            st.success("신청되었습니다. 감사합니다!")


def page_home():
    p = config.PROGRAM
    if theme.hero_with_cta(p["name"], p["intro"], "지원서 작성하기 →", "hero_cta"):
        st.session_state["submitted_ok"] = False
        st.session_state["view"] = "apply"
        st.rerun()

    theme.info_cards([
        ("모집대상", config.NOTICE_DETAIL["target_short"], "자세한 조건은 아래 모집공고를 확인하세요"),
        ("참여기간", p["period"], p.get("period_note")),
        ("접수마감", p["deadline"], p.get("deadline_note")),
        ("합격자 발표", p["announce"], p.get("announce_note")),
    ])

    theme.notice_detail_card(p, config.NOTICE_DETAIL)
    theme.notice_board(config.NOTICES, p)
    theme.program_history_table(config.PAST_PROGRAMS)


# ══════════════════════════ 연구실 소개 ══════════════════════════
def page_labs():
    theme.labs_grid(scoring.LABS)


# ══════════════════════════ FAQ ══════════════════════════
def page_faq():
    st.header("FAQ · Q&A")
    st.caption("자주 묻는 질문과, 지원자분들이 남긴 문의를 한 페이지에서 확인하실 수 있어요.")

    theme.faq_accordion(config.FAQ_ITEMS)

    st.markdown("**1:1 문의 게시판**")
    # 안에 뭔가 입력/체크된 상태면(이름/비밀번호설정/문의내용) 펼쳐진 채로 유지한다.
    # 안 그러면 체크박스 하나만 눌러도 재실행되면서 펼침이 기본값(닫힘)으로 되돌아가버린다.
    _qna_open = bool(st.session_state.get("q_name")) or st.session_state.get("q_set_pw", False) \
        or bool(st.session_state.get("q_text"))
    with st.expander("문의 작성하기", expanded=_qna_open):
        q_name = st.text_input("이름 *", key="q_name")
        set_pw = st.checkbox("비밀번호를 설정하시겠어요? (선택, 나중에 본인 글만 확인할 때 사용)", key="q_set_pw")
        q_pw = st.text_input("비밀번호", type="password", key="q_pw") if set_pw else ""
        q_text = st.text_area("문의 내용 *", height=120, key="q_text")

        if st.button("문의 등록", use_container_width=True, key="q_submit_btn"):
            if not q_name.strip():
                st.error("이름을 입력해주세요.")
            elif not q_text.strip():
                st.error("문의 내용을 입력해주세요.")
            else:
                gsheets.append_question(q_name.strip(), q_pw.strip(), q_text.strip())
                for k in ["q_name", "q_set_pw", "q_pw", "q_text"]:
                    st.session_state.pop(k, None)
                st.success("문의가 등록되었습니다.")
                st.rerun()

    try:
        qdf = gsheets.read_all_questions()
    except Exception:
        qdf = None

    if qdf is None or qdf.empty:
        st.info("등록된 문의가 없습니다.")
    else:
        for _, r in qdf.sort_values("등록일시", ascending=False).iterrows():
            qid = str(r.get("id"))
            has_pw = bool(str(r.get("비밀번호", "")).strip())
            status = "✅ 답변완료" if str(r.get("답변여부")) == "Y" else "⏳ 답변대기"
            unlock_key = f"qna_unlocked_{qid}"
            with st.expander(f"[{status}] {r.get('이름')} — {r.get('등록일시')}",
                              expanded=st.session_state.get(unlock_key, False)):
                if not has_pw or st.session_state.get(unlock_key):
                    st.write(r.get("질문", ""))
                    if str(r.get("답변여부")) == "Y":
                        st.markdown("**➡ 답변**")
                        st.write(r.get("답변", ""))
                else:
                    st.caption("본인이 남긴 문의인 경우, 등록하신 비밀번호를 입력하면 내용을 볼 수 있어요.")
                    pw_try = st.text_input("비밀번호", type="password", key=f"pw_try_{qid}")
                    if st.button("확인", key=f"pw_check_{qid}"):
                        if pw_try == str(r.get("비밀번호", "")):
                            st.session_state[unlock_key] = True
                            st.rerun()
                        else:
                            st.error("비밀번호가 일치하지 않습니다.")


# ══════════════════════════ 지원하기 ══════════════════════════
def page_apply():
    st.header("지원서 작성")
    theme.program_badge(config.PROGRAM["round_key"])

    if st.session_state.get("submitted_ok"):
        with st.container(key="apply_box"):
            theme.submission_success_card(CONTACT_INFO)
            pdf_bytes = st.session_state.get("submitted_pdf")
            if pdf_bytes:
                st.write("")
                theme.pdf_view_button(base64.b64encode(pdf_bytes).decode(),
                                       label="제출하신 내용 확인하기 (새 탭에서 열기)", key="submitted_pdf_btn")
                st.caption("성적증명서·재학증명서 등 첨부서류는 포함되어 있지 않아요.")
        return

    with st.container(key="apply_box"):
        st.subheader("1. 기본 정보")
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            name_kr = st.text_input("성명 (한글) *", placeholder="예) 홍길동", key="f_name_kr")
        with r1c2:
            name_en = st.text_input("성명 (영문) *", placeholder="예) Hong, Gil-Dong", key="f_name_en")

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            birth = st.text_input("생년월일 *", placeholder="예) 2002.01.01", key="f_birth")
            if birth.strip() and not _is_valid_birth(birth):
                theme.inline_error("생년월일 형식이 올바르지 않습니다. 예) 2002.01.01")
        with r2c2:
            email = st.text_input("이메일 *", placeholder="예) example@school.ac.kr", key="f_email")
            if email.strip() and not _is_valid_email(email):
                theme.inline_error("이메일 형식이 올바르지 않습니다.")

        r3c1, r3c2 = st.columns(2)
        with r3c1:
            gender = st.selectbox("성별 *", ["남", "여"], index=None, placeholder="선택하세요", key="f_gender")
        with r3c2:
            phone = st.text_input("휴대폰번호 *", placeholder="예) 010-1234-5678", key="f_phone")
            if phone.strip() and not _is_valid_phone(phone):
                theme.inline_error("휴대폰번호 형식이 올바르지 않습니다. 예) 010-1234-5678")

        with st.form("apply_form", clear_on_submit=False, border=False):
            st.subheader("2. 희망 지도교수")
            c3, c4 = st.columns(2)
            with c3:
                prof1 = st.selectbox("희망지도교수 (1지망) *", scoring.PROFESSORS_GROUPED,
                                      index=None, placeholder="선택하세요")
            with c4:
                prof2 = st.selectbox("희망지도교수 (2지망) *", scoring.PROFESSORS_GROUPED,
                                      index=None, placeholder="선택하세요")

            st.subheader("3. 학력")
            c5, c6, c7 = st.columns(3)
            with c5:
                school = st.text_input("학사 학교명 *", placeholder="예) 포항공과대학교")
            with c6:
                major = st.text_input("학사 전공명 *", placeholder="예) 화학과")
            with c7:
                admit_ym = st.text_input("입학 연월 *", placeholder="예) 2022-03")
                if admit_ym.strip() and not _is_valid_ym(admit_ym):
                    theme.inline_error("입학 연월 형식이 올바르지 않습니다. 예) 2022-03")

            c8, c9, c10 = st.columns(3)
            with c8:
                semester = st.selectbox("학년 학기 *", ["3학년 1학기", "3학년 2학기", "4학년 1학기", "4학년 2학기"],
                                         index=None, placeholder="선택하세요")
            with c9:
                scale = st.selectbox("기준평점(만점) *", ["4.5 만점", "4.3 만점"], index=None, placeholder="선택하세요")
            with c10:
                gpa = st.text_input("평점 *", placeholder="예) 3.953")

            with st.expander("편입생인 경우에만 입력"):
                c11, c12, c13 = st.columns(3)
                with c11:
                    t_school = st.text_input("전적 학사 학교명", placeholder="예) 포항공과대학교")
                    t_scale = st.selectbox("전적 기준평점(만점)", ["", "4.5 만점", "4.3 만점"])
                with c12:
                    t_major = st.text_input("전적 학사 전공명", placeholder="예) 화학과")
                    t_gpa = st.text_input("전적 평점", placeholder="예) 3.953")
                with c13:
                    t_admit_ym = st.text_input("전적 학교 입학 연월", placeholder="예) 2022-03")
                    if t_admit_ym.strip() and not _is_valid_ym(t_admit_ym):
                        theme.inline_error("입학 연월 형식이 올바르지 않습니다. 예) 2022-03")

            st.subheader("4. 관심분야 및 지원동기")
            st.markdown("관심분야 *")
            interest_options = ["유기화학", "무기화학", "물리화학", "분석화학", "고분자화학", "생화학"]
            ic1, ic2, ic3 = st.columns(3)
            interest_cols = [ic1, ic2, ic3, ic1, ic2, ic3]
            interests = []
            for opt, col in zip(interest_options, interest_cols):
                with col:
                    if st.checkbox(opt, key=f"interest_{opt}"):
                        interests.append(opt)
            motivation = st.text_area("자기소개 및 지원동기 * (최대 2000자)", max_chars=2000, height=180)

            c14, c15 = st.columns(2)
            with c14:
                grad_wish = st.selectbox("대학원 진학 희망 여부 *", ["희망하지 않음", "석사", "통합", "박사"],
                                          index=None, placeholder="선택하세요")
            with c15:
                dorm = st.selectbox("생활관(기숙사) 사용 여부 *", ["O", "X"], index=None, placeholder="선택하세요")

            st.subheader("5. 서류 제출")
            c16, c17 = st.columns(2)
            with c16:
                f_transcript = st.file_uploader("성적증명서 (PDF) *", type=["pdf"])
                f_enrollment = st.file_uploader("재학증명서 (PDF, 최근 1개월 이내 발급) *", type=["pdf"])
            with c17:
                f_etc_list = st.file_uploader(
                    "기타 우수성 입증 증빙 (선택, PDF, 여러 개 첨부 가능)",
                    type=["pdf"], accept_multiple_files=True)
                f_photo = st.file_uploader("증명사진 (3.5*4.5) *", type=["jpg", "jpeg", "png"])

            st.subheader("6. 개인정보 수집·이용 동의")
            st.markdown(
                '<div style="font-size:12.5px;color:#777;line-height:1.7;background:#F9F1F6;'
                'border-radius:6px;padding:10px 14px;margin-bottom:8px;">'
                '<b>개인정보 수집·이용 안내</b><br>'
                '· 수집 항목: 성명, 생년월일, 성별, 휴대폰번호, 이메일, 학교·전공·학점 정보'
                '(편입생의 경우 전적학교 정보 포함), 자기소개 및 지원동기, 증명사진, '
                '성적증명서·재학증명서·기타 증빙 등 제출 서류<br>'
                '· 수집 목적: 연구참여 프로그램(SURF/WURF) 지원자 심사 및 선발, 선발 후 프로그램 운영·연락<br>'
                '· 보유 및 이용 기간: 접수일로부터 1년간 보관 후 파기<br>'
                '· 위 개인정보 수집·이용에 동의하지 않으실 경우, 지원 접수가 제한됩니다.'
                '</div>',
                unsafe_allow_html=True,
            )
            consent_required = st.radio("개인정보 수집·이용에 동의합니다 *", ["예", "아니오"], horizontal=True, index=None)

            with st.container(key="submit_btn_wrap"):
                submitted = st.form_submit_button("지원서 제출", use_container_width=True, type="primary")
            theme.inject_css(
                '.st-key-submit_btn_wrap button {'
                f'background-color:{config.BRAND["primary"]} !important; '
                f'border-color:{config.BRAND["primary"]} !important; color:#fff !important; }}'
                '.st-key-submit_btn_wrap button p { color:#fff !important; font-weight:600 !important; }'
                '.st-key-submit_btn_wrap button:hover {'
                f'background-color:{config.BRAND["primary_dark"]} !important; }}'
            )

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
    for label, val in [
        ("성별", gender), ("1지망 교수님", prof1), ("2지망 교수님", prof2),
        ("학년 학기", semester), ("기준평점(만점)", scale),
        ("대학원 진학 희망 여부", grad_wish), ("기숙사 사용 여부", dorm),
    ]:
        if val is None:
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
    if str(admit_ym).strip() and not _is_valid_ym(admit_ym):
        required_missing.append("입학 연월 형식 (예: 2022-03)")
    if str(t_admit_ym).strip() and not _is_valid_ym(t_admit_ym):
        required_missing.append("전적 학교 입학 연월 형식 (예: 2022-03)")
    if scoring.is_group_header(prof1) or scoring.is_group_header(prof2):
        required_missing.append("희망지도교수 (분야 제목이 아닌 교수님을 선택해주세요)")

    if required_missing:
        st.error("다음 항목을 확인해주세요: " + ", ".join(required_missing))
        return

    with st.spinner("제출 처리 중입니다... (파일 업로드에 시간이 걸릴 수 있어요)"):
        # 회차별 상위 폴더 (예: "2026_SURF") - 구글드라이브 안에서 회차별로 자동으로 나뉩니다.
        round_name = config.PROGRAM["round_key"]

        def _short_prof(p):
            return str(p).split(" 교수님")[0].strip()

        # 지원자 폴더명: "이름_1.교수님_2.교수님" + 동명이인 방지용 짧은 시각 태그
        folder_key = (f"{name_kr}_1.{_short_prof(prof1)}_2.{_short_prof(prof2)}"
                      f"_{gsheets.now_kst().strftime('%H%M%S')}")

        group, score43, grade = scoring.compute_score(school, scale, gpa)
        doc_pass = "합격" if scoring.is_document_pass(grade) else "미달"

        t_group = t_score43 = t_grade = ""
        if t_school.strip():
            t_group, t_score43, t_grade = scoring.compute_score(t_school, t_scale, t_gpa)

        now = gsheets.now_kst().strftime("%Y-%m-%d %H:%M:%S")
        row = {
            "접수번호": "", "제출일시": now, "프로그램구분": config.PROGRAM["round_key"],
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
            "개인정보_필수": consent_required, "개인정보_선택": "",
            "서류합격여부": doc_pass, "1지망선발여부": "", "비고": "",
            "편입_대학군": t_group, "편입_4.3환산": t_score43, "편입_환산성적": t_grade,
        }

        # 파일 업로드 (구글드라이브)
        transcript_bytes = _read_bytes(f_transcript)
        enrollment_bytes = _read_bytes(f_enrollment)
        photo_bytes = _read_bytes(f_photo)

        row["성적증명서_링크"] = gsheets.upload_applicant_file(
            round_name, folder_key, f"성적증명서{Path(f_transcript.name).suffix}", transcript_bytes, _mime_of(f_transcript))
        row["재학증명서_링크"] = gsheets.upload_applicant_file(
            round_name, folder_key, f"재학증명서{Path(f_enrollment.name).suffix}", enrollment_bytes, _mime_of(f_enrollment))

        # 제출과 동시에 AI로 서류(성적증명서·재학증명서)를 확인해서 결과를 저장해둔다.
        # (관리자가 나중에 한 명씩 눌러서 확인할 필요 없이, 확인이 필요한 사람만 바로 걸러낼 수 있게)
        doc_notes = []
        doc_check_failed = False
        try:
            for label, fbytes, fname in [
                ("성적증명서", transcript_bytes, f_transcript.name),
                ("재학증명서", enrollment_bytes, f_enrollment.name),
            ]:
                text = gsheets.ocr_document_text(fbytes, fname)
                for n in scoring.check_document_text(text, school, gpa):
                    doc_notes.append(f"[{label}] {n}")
        except Exception:
            # AI 확인은 부가 기능이므로, 실패해도 접수 자체는 정상 진행한다.
            # 다만 "검사했는데 문제없음"과 "애초에 검사가 안 됨(예: 결제 미설정)"은 구분해서
            # 저장한다 — 안 그러면 관리자 화면에서 둘 다 '확인완료'로 보여서 놓치기 쉽다.
            doc_check_failed = True
        if doc_check_failed:
            row["서류확인_AI"] = "미확인(검사 실패)"
        else:
            row["서류확인_AI"] = " / ".join(doc_notes) if doc_notes else "확인완료"

        etc_links = []
        etc_bytes_list = []
        for i, f_etc in enumerate(f_etc_list or [], start=1):
            eb = _read_bytes(f_etc)
            etc_bytes_list.append(eb)
            link = gsheets.upload_applicant_file(
                round_name, folder_key, f"기타증빙_{i}{Path(f_etc.name).suffix}", eb, _mime_of(f_etc))
            etc_links.append(link)
        row["기타자료_링크"] = "\n".join(etc_links)

        row["증명사진_링크"] = gsheets.upload_applicant_file(
            round_name, folder_key, f"증명사진{Path(f_photo.name).suffix}", photo_bytes, _mime_of(f_photo))

        receipt_no = gsheets.append_applicant(row)
        row["접수번호"] = receipt_no

        try:
            # 관리자 보관용(구글드라이브 병합본)에는 접수번호를 남기고,
            admin_pdf = pdf_gen.generate_application_pdf(row, photo_bytes=photo_bytes, show_receipt_no=True)
            # 학생이 화면에서 바로 보는 PDF에는 접수번호를 빼서 몇 번째 지원자인지 유추할 수 없게 한다.
            student_pdf = pdf_gen.generate_application_pdf(row, photo_bytes=photo_bytes, show_receipt_no=False)
        except Exception:
            admin_pdf = None
            student_pdf = None

        # 표지 + 성적증명서 + 재학증명서 + 기타증빙을 하나로 병합해서 드라이브에도 저장
        # (관리자님이 매번 화면에서 따로 생성 안 해도, 폴더에서 바로 받을 수 있게)
        if admin_pdf:
            try:
                merged_pdf = pdf_gen.merge_pdfs(
                    [admin_pdf, transcript_bytes, enrollment_bytes] + etc_bytes_list)
                gsheets.upload_applicant_file(
                    round_name, folder_key, "지원서_전체(병합본).pdf", merged_pdf, "application/pdf")
            except Exception:
                pass

    st.session_state["submitted_ok"] = True
    st.session_state["submitted_pdf"] = student_pdf
    st.session_state["submitted_name"] = name_kr
    st.session_state["_force_scroll_top"] = True
    st.rerun()


# ══════════════════════════ 라우팅 (관리자 탭 없음) ══════════════════════════
if "view" not in st.session_state:
    st.session_state["view"] = "home"

if st.query_params.get("nav") == "home":
    st.session_state["view"] = "home"
    st.query_params.clear()
    st.rerun()

new_view, sub_clicked, nav_pressed = theme.top_nav_simple(st.session_state["view"])
if new_view != st.session_state["view"]:
    if new_view == "apply":
        # '지원하기' 탭을 새로 눌러서 들어올 때는 완료 화면을 초기화해서 새 폼이 뜨게 한다.
        # (중복 지원은 관리자 화면에서 골라 지울 수 있으니, 여기서 막지는 않는다)
        st.session_state["submitted_ok"] = False
    st.session_state["view"] = new_view
    st.rerun()
elif nav_pressed:
    # 이미 활성화된 탭을 다시 눌렀을 때 — 뷰는 안 바뀌지만, 아래로 스크롤해둔 상태였다면
    # 화면이 중간부터 보이는 것처럼 보이니 이때도 맨 위로 스크롤시킨다.
    st.session_state["_force_scroll_top"] = True
if sub_clicked:
    _subscribe_dialog()

view = st.session_state["view"]
if st.session_state.get("_last_view") != view or st.session_state.pop("_force_scroll_top", False):
    theme.scroll_to_top()
    st.session_state["_last_view"] = view

if view == "apply":
    page_apply()
elif view == "labs":
    page_labs()
elif view == "faq":
    page_faq()
else:
    page_home()

theme.footer()
