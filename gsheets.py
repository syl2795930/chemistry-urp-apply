# -*- coding: utf-8 -*-
"""
구글시트(지원자 데이터 저장) + 구글드라이브(첨부파일 저장) 연동.

- 구글시트는 서비스 계정으로 접근합니다. (시트는 서비스 계정으로도 문제없이 씁니다)
- 구글드라이브 업로드는 "서비스 계정 저장용량 0GB" 문제 때문에, 담당자님의 실제 구글 계정으로
  로그인(OAuth)해서 그 계정 소유로 업로드하는 방식을 씁니다. (get_refresh_token.py 참고)

st.secrets 에 아래 형태로 값이 있어야 합니다. (SETUP_GUIDE.md 참고)

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "xxx@xxx.iam.gserviceaccount.com"
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"

[google_oauth]
client_id = "OAuth 클라이언트 ID (Desktop app)"
client_secret = "OAuth 클라이언트 보안 비밀번호"
refresh_token = "get_refresh_token.py 실행 후 얻은 값"

[app]
sheet_id = "구글시트_ID"
drive_folder_id = "구글드라이브_루트폴더_ID"
admin_password = "관리자비밀번호"
"""
import io
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

# 드라이브는 "이 앱이 만든 파일에만 접근" 범위로 최소화 (내 드라이브 전체 접근 아님)
DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]

WORKSHEET_NAME = "지원자"

# 시트 컬럼 순서 (이 순서가 곧 구글시트의 실제 열 순서가 됩니다)
HEADERS = [
    "접수번호", "제출일시", "프로그램구분",
    "성명_한글", "성명_영문", "생년월일", "성별", "휴대폰번호", "이메일",
    "희망지도교수_1지망", "희망지도교수_2지망",
    "학교명", "전공명", "입학연월", "학년학기", "만점기준", "평점",
    "편입_전적학교", "편입_전공", "편입_입학연월", "편입_만점기준", "편입_평점",
    "대학군", "4.3환산", "환산성적",
    "관심분야", "대학원진학희망", "희망과정", "기숙사사용", "지원동기",
    "성적증명서_링크", "재학증명서_링크", "기타자료_링크", "증명사진_링크",
    "개인정보_필수", "개인정보_선택",
    "서류합격여부", "1지망선발여부", "비고",
]


@st.cache_resource(show_spinner=False)
def _get_creds():
    """구글시트 접근용 (서비스 계정)."""
    info = dict(st.secrets["gcp_service_account"])
    return Credentials.from_service_account_info(info, scopes=SCOPES)


@st.cache_resource(show_spinner=False)
def _get_gc():
    return gspread.authorize(_get_creds())


@st.cache_resource(show_spinner=False)
def _get_drive_creds():
    """구글드라이브 접근용 (담당자 개인 계정, OAuth refresh token 사용)."""
    o = st.secrets["google_oauth"]
    return UserCredentials(
        token=None,
        refresh_token=o["refresh_token"],
        client_id=o["client_id"],
        client_secret=o["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=DRIVE_SCOPES,
    )


@st.cache_resource(show_spinner=False)
def _get_drive():
    return build("drive", "v3", credentials=_get_drive_creds())



def _get_worksheet():
    gc = _get_gc()
    sh = gc.open_by_key(st.secrets["app"]["sheet_id"])
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=2000, cols=len(HEADERS) + 5)
    first_row = ws.row_values(1)
    if first_row != HEADERS:
        ws.update("A1", [HEADERS])
    return ws


def read_all_df() -> pd.DataFrame:
    ws = _get_worksheet()
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=HEADERS)
    df = pd.DataFrame(records)
    for c in HEADERS:
        if c not in df.columns:
            df[c] = ""
    return df[HEADERS]


def append_applicant(row: dict) -> str:
    """
    지원자 행을 시트에 추가하고, 실제로 저장된 행 위치를 기준으로 접수번호를 확정해서 반환한다.

    기존 방식(제출 전에 '현재까지 몇 명인지 세어서 +1')은 두 학생이 거의 동시에 제출하면
    같은 접수번호가 배정될 수 있는 문제가 있었다. 이 함수는 구글시트 append가 끝난 '이후',
    실제로 배정된 행 번호를 기준으로 접수번호를 매기기 때문에 동시 제출에도 안전하다.
    (구글시트 API의 append는 동시 요청이 와도 서로 다른 행을 순서대로 배정하도록 보장한다.)
    """
    import re
    ws = _get_worksheet()
    year = str(row.get("제출일시", ""))[:4] or __import__("datetime").datetime.now().strftime("%Y")
    values = [str(row.get(h, "")) for h in HEADERS]
    resp = ws.append_row(values, value_input_option="USER_ENTERED")

    receipt_no = row.get("접수번호", "")
    updated_range = (resp or {}).get("updates", {}).get("updatedRange", "")
    m = re.search(r"![A-Z]+(\d+)", updated_range)
    if m:
        row_idx = int(m.group(1))
        date_col = HEADERS.index("제출일시") + 1
        # 헤더(1행) 다음부터, 방금 저장된 이 행까지의 제출일시 값을 읽는다.
        # append가 끝난 시점에는 이 행의 제출일시도 이미 저장돼 있으므로 동시 제출이어도 안전하게 카운트된다.
        dates_so_far = ws.col_values(date_col)[1:row_idx]
        seq = sum(1 for d in dates_so_far if str(d).startswith(year)) or 1
        receipt_no = f"{year}-{seq:04d}"
        ws.update_cell(row_idx, HEADERS.index("접수번호") + 1, receipt_no)
    return receipt_no


def update_fields(receipt_no: str, updates: dict):
    """접수번호로 행을 찾아 지정된 컬럼들만 갱신."""
    ws = _get_worksheet()
    cell = ws.find(str(receipt_no), in_column=HEADERS.index("접수번호") + 1)
    if cell is None:
        raise ValueError(f"접수번호 {receipt_no} 를 찾을 수 없습니다.")
    row_idx = cell.row
    for key, val in updates.items():
        if key not in HEADERS:
            continue
        col_idx = HEADERS.index(key) + 1
        ws.update_cell(row_idx, col_idx, str(val))


# ── 구글드라이브 파일 저장 ──────────────────────────────────────────

def _find_or_create_subfolder(name: str, parent_id: str) -> str:
    drive = _get_drive()
    q = (f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' "
         f"and '{parent_id}' in parents and trashed = false")
    res = drive.files().list(
        q=q, fields="files(id, name)",
        supportsAllDrives=True, includeItemsFromAllDrives=True, corpora="allDrives"
    ).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    folder = drive.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    return folder["id"]


def upload_applicant_file(receipt_no: str, applicant_name: str, filename: str,
                           file_bytes: bytes, mimetype: str) -> str:
    """지원자별 하위 폴더에 파일 업로드 후 webViewLink 반환."""
    drive = _get_drive()
    root_id = st.secrets["app"]["drive_folder_id"]
    folder_name = f"{receipt_no}_{applicant_name}"
    folder_id = _find_or_create_subfolder(folder_name, root_id)
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mimetype, resumable=False)
    meta = {"name": filename, "parents": [folder_id]}
    f = drive.files().create(body=meta, media_body=media, fields="id, webViewLink", supportsAllDrives=True).execute()
    return f.get("webViewLink", "")


def download_file_bytes_from_link(view_link: str) -> bytes:
    """webViewLink (또는 file id)로부터 파일 바이트 다운로드."""
    drive = _get_drive()
    file_id = view_link
    if "/d/" in view_link:
        file_id = view_link.split("/d/")[1].split("/")[0]
    request = drive.files().get_media(fileId=file_id, supportsAllDrives=True)
    buf = io.BytesIO()
    from googleapiclient.http import MediaIoBaseDownload
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def get_file_name_from_link(view_link: str) -> str:
    drive = _get_drive()
    file_id = view_link
    if "/d/" in view_link:
        file_id = view_link.split("/d/")[1].split("/")[0]
    meta = drive.files().get(fileId=file_id, fields="name", supportsAllDrives=True).execute()
    return meta.get("name", "file")


# ── 연도별 아카이브 / 삭제 (용량 관리 + 개인정보 보유기간 준수) ──────

def find_applicant_folder_id(receipt_no: str, applicant_name: str):
    """지원자 폴더가 있으면 id 반환, 없으면 None."""
    drive = _get_drive()
    root_id = st.secrets["app"]["drive_folder_id"]
    folder_name = f"{receipt_no}_{applicant_name}"
    q = (f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' "
         f"and '{root_id}' in parents and trashed = false")
    res = drive.files().list(
        q=q, fields="files(id, name)",
        supportsAllDrives=True, includeItemsFromAllDrives=True, corpora="allDrives"
    ).execute()
    files = res.get("files", [])
    return files[0]["id"] if files else None


def trash_applicant_folder(receipt_no: str, applicant_name: str):
    """지원자 폴더를 휴지통으로 이동 (30일간 복구 가능, 완전삭제 아님)."""
    folder_id = find_applicant_folder_id(receipt_no, applicant_name)
    if folder_id:
        drive = _get_drive()
        drive.files().update(fileId=folder_id, body={"trashed": True}, supportsAllDrives=True).execute()


def delete_applicant_row(receipt_no: str):
    """시트에서 해당 접수번호 행을 삭제."""
    ws = _get_worksheet()
    cell = ws.find(str(receipt_no), in_column=HEADERS.index("접수번호") + 1)
    if cell is not None:
        ws.delete_rows(cell.row)


def archive_and_delete_year(df: "pd.DataFrame", year: str, progress_cb=None):
    """
    지정한 연도(접수번호 접두어 기준)의 지원자 전체를
    - 구글드라이브 폴더는 휴지통으로 이동
    - 구글시트 행은 삭제
    (호출 전에 반드시 UI에서 백업 ZIP을 먼저 다운로드하도록 안내할 것)
    """
    targets = df[df["접수번호"].astype(str).str.startswith(f"{year}-")]
    # 시트 행 인덱스가 삭제할수록 밀리므로, 접수번호가 큰 것부터(뒤에서부터) 처리
    targets = targets.sort_values("접수번호", ascending=False)
    total = len(targets)
    for i, (_, row) in enumerate(targets.iterrows()):
        trash_applicant_folder(row["접수번호"], row["성명_한글"])
        delete_applicant_row(row["접수번호"])
        if progress_cb:
            progress_cb(i + 1, total)
    return total


# ── FAQ · Q&A 문의 게시판 (별도 워크시트) ────────────────────────────
QNA_WORKSHEET_NAME = "문의"
QNA_HEADERS = ["id", "등록일시", "이름", "비밀번호", "질문", "답변", "답변여부"]


def _get_qna_worksheet():
    gc = _get_gc()
    sh = gc.open_by_key(st.secrets["app"]["sheet_id"])
    try:
        ws = sh.worksheet(QNA_WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=QNA_WORKSHEET_NAME, rows=1000, cols=len(QNA_HEADERS) + 2)
    first_row = ws.row_values(1)
    if first_row != QNA_HEADERS:
        ws.update("A1", [QNA_HEADERS])
    return ws


def read_all_questions() -> pd.DataFrame:
    ws = _get_qna_worksheet()
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=QNA_HEADERS)
    df = pd.DataFrame(records)
    for c in QNA_HEADERS:
        if c not in df.columns:
            df[c] = ""
    return df[QNA_HEADERS]


def append_question(name: str, pw: str, text: str) -> str:
    """질문 등록. 고유 id(문자열, 타임스탬프 기반)를 반환."""
    import datetime
    ws = _get_qna_worksheet()
    qid = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([qid, now, name or "익명", pw, text, "", "N"], value_input_option="USER_ENTERED")
    return qid


def answer_question(qid: str, answer_text: str):
    """관리자 답변 등록."""
    ws = _get_qna_worksheet()
    cell = ws.find(str(qid), in_column=QNA_HEADERS.index("id") + 1)
    if cell is None:
        raise ValueError(f"문의 id {qid} 를 찾을 수 없습니다.")
    row_idx = cell.row
    ws.update_cell(row_idx, QNA_HEADERS.index("답변") + 1, answer_text)
    ws.update_cell(row_idx, QNA_HEADERS.index("답변여부") + 1, "Y")


def delete_question(qid: str):
    ws = _get_qna_worksheet()
    cell = ws.find(str(qid), in_column=QNA_HEADERS.index("id") + 1)
    if cell is not None:
        ws.delete_rows(cell.row)

