# =========================================================
# CM 체크리스트 관리 웹앱
# 구조 개선 버전
#
# 주요 변경사항
# 1. 점검사항 1건을 기준으로 전체 업무를 관리합니다.
# 2. 별도의 조치사항 등록 페이지를 두지 않고,
#    각 점검사항 상세 화면 안에서 조치 의견과 증빙을 등록합니다.
# 3. 조치자가 '조치 완료 확인 요청'을 올리면
#    상태를 '조치확인요청'으로 변경할 수 있습니다.
# 4. 담당자는 확인 후 상태를 '완료'로 변경할 수 있습니다.
# 5. 점검사항 전체조회 페이지를 따로 두었습니다.
# 6. 캘린더에는 상태 요약이 아니라 점검사항 제목만 표시합니다.
# 7. 모든 알림 문구는 경어체로 작성했습니다.
#
# 주의사항
# - 현재 버전은 st.session_state 기반 임시 저장 구조입니다.
# - 앱을 완전히 종료하면 데이터가 초기화됩니다.
# - 영구 저장은 다음 단계에서 엑셀 또는 외부 DB를 연결하면 됩니다.
# =========================================================

# -----------------------------
# 1. 라이브러리 불러오기
# -----------------------------
import calendar
from datetime import date, datetime

import pandas as pd
import streamlit as st


# -----------------------------
# 2. 웹페이지 기본 설정
# -----------------------------
st.set_page_config(
    page_title="CM 체크리스트 관리 웹앱",
    layout="wide"
)


# -----------------------------
# 3. 기본 스타일(CSS)
# -----------------------------
# 너무 번잡하지 않게 화면을 단순하게 보이도록 최소 스타일만 적용합니다.
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.1rem;
        padding-bottom: 1.6rem;
    }

    .calendar-wrapper {
        border: 1px solid #2b2b2b;
        border-radius: 14px;
        overflow: hidden;
        background-color: #0f1116;
    }

    .calendar-header {
        padding: 12px 14px;
        font-size: 19px;
        font-weight: 700;
        border-bottom: 1px solid #2b2b2b;
        background-color: #151922;
    }

    .calendar-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }

    .calendar-table th {
        border: 1px solid #2b2b2b;
        padding: 8px;
        text-align: center;
        background-color: #171717;
        font-size: 14px;
    }

    .calendar-table td {
        border: 1px solid #2b2b2b;
        height: 120px;
        vertical-align: top;
        padding: 6px;
    }

    .day-number {
        font-weight: 700;
        margin-bottom: 6px;
        font-size: 14px;
    }

    .day-other-month {
        opacity: 0.25;
    }

    .today-cell {
        outline: 2px solid #4f8cff;
        outline-offset: -2px;
    }

    .calendar-item {
        font-size: 12px;
        line-height: 1.45;
        margin-bottom: 3px;
        padding: 3px 5px;
        border-radius: 6px;
        background-color: #1c2433;
        color: #d9e5ff;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .small-muted {
        font-size: 12px;
        color: #b9c0cc;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# 4. 세션 상태 초기화
# -----------------------------
def init_session_state():
    """
    앱 실행 중 사용할 기본 저장공간을 준비합니다.
    현재는 로그인 기능이 없으므로 관리자 권한을 True로 두었습니다.
    """
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = True

    # 점검사항 저장 리스트
    if "issues" not in st.session_state:
        st.session_state.issues = []

    # 점검사항 ID 자동 증가값
    if "next_issue_id" not in st.session_state:
        st.session_state.next_issue_id = 1

    # 조치 의견 ID 자동 증가값
    if "next_log_id" not in st.session_state:
        st.session_state.next_log_id = 1

    # 달력 표시용 현재 연/월
    if "current_year" not in st.session_state:
        st.session_state.current_year = date.today().year

    if "current_month" not in st.session_state:
        st.session_state.current_month = date.today().month


init_session_state()


# -----------------------------
# 5. 공통 보조 함수
# -----------------------------
def get_issue_by_id(issue_id: int):
    """
    issue_id에 해당하는 점검사항 딕셔너리를 반환합니다.
    없으면 None을 반환합니다.
    """
    for issue in st.session_state.issues:
        if issue["id"] == issue_id:
            return issue
    return None


def get_issues_df() -> pd.DataFrame:
    """
    세션에 저장된 점검사항 리스트를 DataFrame으로 변환합니다.
    표 출력, 필터링, 통계 계산에 사용합니다.
    """
    if len(st.session_state.issues) == 0:
        return pd.DataFrame(
            columns=[
                "id", "제목", "부서", "위치", "담당자", "등록자",
                "등록일", "기한일", "상태", "상세내용", "의견수"
            ]
        )

    rows = []
    for issue in st.session_state.issues:
        rows.append(
            {
                "id": issue["id"],
                "제목": issue["title"],
                "부서": issue["department"],
                "위치": issue["location"],
                "담당자": issue["manager"],
                "등록자": issue["reporter"],
                "등록일": issue["created_date"],
                "기한일": issue["due_date"],
                "상태": issue["status"],
                "상세내용": issue["description"],
                "의견수": len(issue["action_logs"]),
            }
        )

    df = pd.DataFrame(rows)
    df["등록일"] = pd.to_datetime(df["등록일"]).dt.date
    df["기한일"] = pd.to_datetime(df["기한일"]).dt.date
    return df.sort_values(by=["기한일", "id"]).reset_index(drop=True)


def add_issue(title, department, location, manager, reporter, due_date, description):
    """
    새로운 점검사항을 등록합니다.
    등록 시 기본 상태는 '미조치'입니다.
    """
    new_issue = {
        "id": st.session_state.next_issue_id,
        "title": title.strip(),
        "department": department.strip(),
        "location": location.strip(),
        "manager": manager.strip(),
        "reporter": reporter.strip(),
        "created_date": date.today(),
        "due_date": due_date,
        "status": "미조치",
        "description": description.strip(),
        "action_logs": [],
    }

    st.session_state.issues.append(new_issue)
    st.session_state.next_issue_id += 1


def delete_issue(issue_id: int):
    """
    선택한 점검사항 1건을 삭제합니다.
    """
    st.session_state.issues = [
        issue for issue in st.session_state.issues
        if issue["id"] != issue_id
    ]


def update_issue_status(issue_id: int, new_status: str):
    """
    점검사항 상태를 변경합니다.
    허용 상태:
    - 미조치
    - 조치중
    - 조치확인요청
    - 완료
    """
    issue = get_issue_by_id(issue_id)
    if issue is not None:
        issue["status"] = new_status


def add_action_log(issue_id: int, writer: str, comment: str, request_review: bool, uploaded_files):
    """
    선택한 점검사항에 조치 의견(댓글)과 증빙 파일을 추가합니다.

    request_review = True 이면 상태를 '조치확인요청'으로 바꿉니다.
    request_review = False 이고 현재 상태가 '미조치'라면 상태를 '조치중'으로 바꿉니다.
    """
    issue = get_issue_by_id(issue_id)
    if issue is None:
        return

    saved_files = []

    # 업로드한 파일을 바이트 형태로 세션에 저장합니다.
    # 현재 버전은 세션 기반이므로 앱을 완전히 종료하면 파일도 함께 사라집니다.
    if uploaded_files:
        for file in uploaded_files:
            saved_files.append(
                {
                    "name": file.name,
                    "type": file.type if file.type else "application/octet-stream",
                    "bytes": file.getvalue(),
                }
            )

    log_item = {
        "log_id": st.session_state.next_log_id,
        "writer": writer.strip(),
        "comment": comment.strip(),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "request_review": request_review,
        "files": saved_files,
    }

    issue["action_logs"].append(log_item)
    st.session_state.next_log_id += 1

    if request_review:
        issue["status"] = "조치확인요청"
    else:
        if issue["status"] == "미조치":
            issue["status"] = "조치중"


def delete_action_log(issue_id: int, log_id: int):
    """
    선택한 점검사항 내부의 특정 조치 의견 1건을 삭제합니다.
    """
    issue = get_issue_by_id(issue_id)
    if issue is None:
        return

    issue["action_logs"] = [
        log for log in issue["action_logs"]
        if log["log_id"] != log_id
    ]


def move_month(delta: int):
    """
    이전달/다음달 이동 함수입니다.
    delta = -1 이면 이전달, +1 이면 다음달입니다.
    """
    year = st.session_state.current_year
    month = st.session_state.current_month + delta

    if month == 0:
        st.session_state.current_year = year - 1
        st.session_state.current_month = 12
    elif month == 13:
        st.session_state.current_year = year + 1
        st.session_state.current_month = 1
    else:
        st.session_state.current_month = month


# -----------------------------
# 6. 월간 달력 HTML 생성 함수
# -----------------------------
def build_month_calendar_html(year: int, month: int, df: pd.DataFrame) -> str:
    """
    월간 달력을 HTML로 생성합니다.

    중요:
    - 캘린더에는 완료/미완료 개수를 표시하지 않습니다.
    - 각 날짜 칸에는 해당 날짜의 점검사항 제목만 표시합니다.
    """
    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdatescalendar(year, month)
    today = date.today()

    html_parts = []
    html_parts.append('<div class="calendar-wrapper">')
    html_parts.append(f'<div class="calendar-header">{year}년 {month}월</div>')
    html_parts.append('<table class="calendar-table">')

    html_parts.append("<thead><tr>")
    for day_name in ["일", "월", "화", "수", "목", "금", "토"]:
        html_parts.append(f"<th>{day_name}</th>")
    html_parts.append("</tr></thead>")

    html_parts.append("<tbody>")
    for week in weeks:
        html_parts.append("<tr>")

        for day in week:
            day_df = pd.DataFrame()
            if not df.empty:
                day_df = df[df["기한일"] == day].copy()

            other_class = "day-other-month" if day.month != month else ""
            today_class = "today-cell" if day == today else ""
            cell_class = f"{other_class} {today_class}".strip()

            html_parts.append(f'<td class="{cell_class}">')
            html_parts.append(f'<div class="day-number">{day.day}</div>')

            if day.month == month and not day_df.empty:
                preview_df = day_df.head(3)

                for _, row in preview_df.iterrows():
                    title = str(row["제목"])
                    html_parts.append(f'<div class="calendar-item">{title}</div>')

                if len(day_df) > 3:
                    remain_count = len(day_df) - 3
                    html_parts.append(f'<div class="calendar-item">... 외 {remain_count}건</div>')

            html_parts.append("</td>")

        html_parts.append("</tr>")
    html_parts.append("</tbody></table></div>")

    return "".join(html_parts)


# -----------------------------
# 7. 홈 우측 요약 목록 함수
# -----------------------------
def render_summary_list(title: str, df: pd.DataFrame, empty_message: str):
    """
    홈 화면 우측에 간단한 목록을 출력합니다.
    """
    st.markdown(f"#### {title}")

    if df.empty:
        st.info(empty_message)
        return

    for _, row in df.head(5).iterrows():
        with st.container(border=True):
            st.write(f"**{row['제목']}**")
            st.write(f"- 부서: {row['부서']}")
            st.write(f"- 담당자: {row['담당자']}")
            st.write(f"- 기한일: {row['기한일']}")
            st.write(f"- 상태: {row['상태']}")


# -----------------------------
# 8. 점검사항 상세 표시 함수
# -----------------------------
def render_issue_detail(issue_id: int):
    """
    선택한 점검사항의 상세 정보, 조치 의견, 상태 변경,
    삭제 기능을 한 화면에 출력합니다.
    """
    issue = get_issue_by_id(issue_id)

    if issue is None:
        st.warning("선택한 점검사항을 찾을 수 없습니다.")
        return

    st.markdown("### 점검사항 상세")

    # ---------------------------------
    # 기본 정보 박스
    # ---------------------------------
    with st.container(border=True):
        st.write(f"**제목:** {issue['title']}")
        st.write(f"**상태:** {issue['status']}")
        st.write(f"**부서:** {issue['department']}")
        st.write(f"**위치:** {issue['location']}")
        st.write(f"**담당자:** {issue['manager']}")
        st.write(f"**등록자:** {issue['reporter']}")
        st.write(f"**등록일:** {issue['created_date']}")
        st.write(f"**기한일:** {issue['due_date']}")
        st.write(f"**상세내용:** {issue['description'] if issue['description'] else '입력된 상세내용이 없습니다.'}")

    st.markdown("### 상태 관리")

    # ---------------------------------
    # 담당자 상태 변경 구역
    # ---------------------------------
    status_options = ["미조치", "조치중", "조치확인요청", "완료"]

    status_col1, status_col2 = st.columns([2, 1])

    with status_col1:
        selected_status = st.selectbox(
            "변경할 상태를 선택해 주십시오.",
            options=status_options,
            index=status_options.index(issue["status"]),
            key=f"status_select_{issue_id}"
        )

    with status_col2:
        st.write("")
        st.write("")
        if st.button("상태를 저장합니다", key=f"status_save_{issue_id}", use_container_width=True):
            update_issue_status(issue_id, selected_status)
            st.success("상태가 저장되었습니다.")
            st.rerun()

    if issue["status"] == "조치확인요청":
        st.info("조치자가 완료 확인을 요청한 상태입니다. 담당자께서 확인 후 완료 처리해 주시면 됩니다.")

    if issue["status"] != "완료":
        if st.button("담당자 확인 후 완료로 변경합니다", key=f"complete_btn_{issue_id}"):
            update_issue_status(issue_id, "완료")
            st.success("점검사항 상태가 완료로 변경되었습니다.")
            st.rerun()

    st.divider()

    # ---------------------------------
    # 조치 의견 등록 구역
    # ---------------------------------
    st.markdown("### 조치 의견 등록")

    with st.form(f"action_log_form_{issue_id}"):
        writer = st.text_input("조치자명")
        comment = st.text_area("의견(댓글)")
        uploaded_files = st.file_uploader(
            "사진 또는 파일 증빙을 첨부해 주십시오.",
            accept_multiple_files=True,
            key=f"uploader_{issue_id}"
        )
        request_review = st.checkbox("조치 완료 확인을 요청합니다.")
        submit_log = st.form_submit_button("의견을 등록합니다")

        if submit_log:
            has_comment = comment.strip() != ""
            has_files = uploaded_files is not None and len(uploaded_files) > 0

            if writer.strip() == "":
                st.error("조치자명을 입력해 주십시오.")
            elif not has_comment and not has_files:
                st.error("의견 또는 첨부파일 중 하나 이상을 입력해 주십시오.")
            else:
                add_action_log(
                    issue_id=issue_id,
                    writer=writer,
                    comment=comment,
                    request_review=request_review,
                    uploaded_files=uploaded_files,
                )
                st.success("조치 의견이 등록되었습니다.")
                st.rerun()

    st.divider()

    # ---------------------------------
    # 조치 의견 이력 표시
    # ---------------------------------
    st.markdown("### 조치 의견 이력")

    if len(issue["action_logs"]) == 0:
        st.info("등록된 조치 의견이 없습니다.")
    else:
        sorted_logs = sorted(
            issue["action_logs"],
            key=lambda x: x["log_id"],
            reverse=True
        )

        for log in sorted_logs:
            with st.container(border=True):
                st.write(f"**작성자:** {log['writer']}")
                st.write(f"**작성시각:** {log['created_at']}")

                if log["request_review"]:
                    st.write("**확인 요청 여부:** 조치 완료 확인 요청")
                else:
                    st.write("**확인 요청 여부:** 일반 의견")

                if log["comment"]:
                    st.write(f"**의견 내용:** {log['comment']}")
                else:
                    st.write("**의견 내용:** 입력된 의견이 없습니다.")

                if len(log["files"]) == 0:
                    st.write("**첨부파일:** 첨부된 파일이 없습니다.")
                else:
                    st.write("**첨부파일:**")
                    for file_idx, saved_file in enumerate(log["files"]):
                        st.download_button(
                            label=f"파일 다운로드: {saved_file['name']}",
                            data=saved_file["bytes"],
                            file_name=saved_file["name"],
                            mime=saved_file["type"],
                            key=f"download_{issue_id}_{log['log_id']}_{file_idx}"
                        )

                if st.session_state.is_admin:
                    if st.button(
                        "이 의견을 삭제합니다",
                        key=f"delete_log_{issue_id}_{log['log_id']}"
                    ):
                        delete_action_log(issue_id, log["log_id"])
                        st.success("조치 의견이 삭제되었습니다.")
                        st.rerun()

    st.divider()

    # ---------------------------------
    # 점검사항 삭제 구역
    # ---------------------------------
    if st.session_state.is_admin:
        st.markdown("### 점검사항 삭제")
        st.warning("아래 버튼을 누르면 현재 점검사항과 연결된 조치 의견이 모두 삭제됩니다.")
        if st.button("현재 점검사항을 삭제합니다", key=f"delete_issue_{issue_id}"):
            delete_issue(issue_id)
            st.success("점검사항이 삭제되었습니다.")
            st.rerun()


# -----------------------------
# 9. 상단 제목 및 메뉴
# -----------------------------
st.title("CM 체크리스트 관리 웹앱")

menu_left, menu_right = st.columns([8, 2])

with menu_left:
    page = st.radio(
        "메뉴",
        options=["홈", "점검사항 등록", "점검사항 전체조회", "캘린더", "부서"],
        horizontal=True,
        label_visibility="collapsed"
    )

with menu_right:
    st.write("")
    st.caption("관리자 모드")


# -----------------------------
# 10. 공통 데이터 준비
# -----------------------------
issues_df = get_issues_df()

if not issues_df.empty:
    issues_df = issues_df.sort_values(by=["기한일", "id"]).reset_index(drop=True)


# =========================================================
# 11. 페이지별 화면 구성
# =========================================================

# -----------------------------
# [홈] 페이지
# -----------------------------
if page == "홈":
    st.subheader("홈")

    if issues_df.empty:
        total_count = 0
        open_count = 0
        review_count = 0
        done_count = 0
    else:
        total_count = len(issues_df)
        open_count = len(issues_df[issues_df["상태"].isin(["미조치", "조치중"])])
        review_count = len(issues_df[issues_df["상태"] == "조치확인요청"])
        done_count = len(issues_df[issues_df["상태"] == "완료"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 점검사항", total_count)
    c2.metric("미완료 점검사항", open_count)
    c3.metric("확인요청 점검사항", review_count)
    c4.metric("완료 점검사항", done_count)

    left_col, right_col = st.columns([2.1, 1.0], gap="large")

    with left_col:
        st.markdown("### 월간 캘린더")

        nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])

        with nav_col1:
            if st.button("◀ 이전달", key="home_prev_month", use_container_width=True):
                move_month(-1)

        with nav_col2:
            st.markdown(f"#### {st.session_state.current_year}년 {st.session_state.current_month}월")

        with nav_col3:
            if st.button("다음달 ▶", key="home_next_month", use_container_width=True):
                move_month(1)

        calendar_html = build_month_calendar_html(
            st.session_state.current_year,
            st.session_state.current_month,
            issues_df,
        )
        st.markdown(calendar_html, unsafe_allow_html=True)

    with right_col:
        if issues_df.empty:
            unresolved_df = issues_df.copy()
            review_df = issues_df.copy()
            recent_done_df = issues_df.copy()
        else:
            unresolved_df = issues_df[issues_df["상태"].isin(["미조치", "조치중"])].sort_values("기한일")
            review_df = issues_df[issues_df["상태"] == "조치확인요청"].sort_values("기한일")
            recent_done_df = issues_df[issues_df["상태"] == "완료"].sort_values("등록일", ascending=False)

        render_summary_list("미완료 점검사항", unresolved_df, "현재 미완료 점검사항이 없습니다.")
        render_summary_list("확인요청 점검사항", review_df, "현재 확인요청 점검사항이 없습니다.")
        render_summary_list("최근 완료 점검사항", recent_done_df, "최근 완료 점검사항이 없습니다.")


# -----------------------------
# [점검사항 등록] 페이지
# -----------------------------
elif page == "점검사항 등록":
    st.subheader("점검사항 등록")

    with st.form("issue_register_form"):
        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input("제목")
            department = st.text_input("부서")
            location = st.text_input("위치")

        with col2:
            manager = st.text_input("담당자")
            reporter = st.text_input("등록자")
            due_date = st.date_input("기한일", value=date.today())

        description = st.text_area("상세내용")
        submit_issue = st.form_submit_button("점검사항을 등록합니다")

        if submit_issue:
            if title.strip() == "":
                st.error("제목을 입력해 주십시오.")
            else:
                add_issue(
                    title=title,
                    department=department,
                    location=location,
                    manager=manager,
                    reporter=reporter,
                    due_date=due_date,
                    description=description,
                )
                st.success("점검사항이 등록되었습니다.")
                st.rerun()

    st.divider()
    st.markdown("### 최근 등록된 점검사항")

    if issues_df.empty:
        st.info("등록된 점검사항이 없습니다.")
    else:
        recent_df = issues_df.sort_values(by=["id"], ascending=False).head(10)
        st.dataframe(
            recent_df[["id", "제목", "부서", "담당자", "등록자", "등록일", "기한일", "상태"]],
            use_container_width=True,
        )


# -----------------------------
# [점검사항 전체조회] 페이지
# -----------------------------
elif page == "점검사항 전체조회":
    st.subheader("점검사항 전체조회")

    if issues_df.empty:
        st.info("등록된 점검사항이 없습니다.")
    else:
        # -------------------------
        # 필터 영역
        # -------------------------
        filter_col1, filter_col2, filter_col3 = st.columns(3)

        with filter_col1:
            status_filter = st.selectbox(
                "상태 필터",
                ["전체", "미조치", "조치중", "조치확인요청", "완료"]
            )

        with filter_col2:
            dept_options = ["전체"] + sorted(
                [d for d in issues_df["부서"].dropna().unique().tolist() if str(d).strip() != ""]
            )
            dept_filter = st.selectbox("부서 필터", dept_options)

        with filter_col3:
            keyword = st.text_input("제목 검색")

        filtered_df = issues_df.copy()

        if status_filter != "전체":
            filtered_df = filtered_df[filtered_df["상태"] == status_filter]

        if dept_filter != "전체":
            filtered_df = filtered_df[filtered_df["부서"] == dept_filter]

        if keyword.strip() != "":
            filtered_df = filtered_df[
                filtered_df["제목"].str.contains(keyword.strip(), case=False, na=False)
            ]

        st.markdown("### 점검사항 목록")

        if filtered_df.empty:
            st.info("조건에 해당하는 점검사항이 없습니다.")
        else:
            st.dataframe(
                filtered_df[["id", "제목", "부서", "위치", "담당자", "등록자", "등록일", "기한일", "상태", "의견수"]],
                use_container_width=True,
            )

            # -------------------------
            # 상세 조회 선택 영역
            # -------------------------
            select_options = {
                f"[ID {row['id']}] {row['제목']} / {row['상태']} / {row['기한일']}": row["id"]
                for _, row in filtered_df.iterrows()
            }

            selected_label = st.selectbox(
                "상세 조회할 점검사항을 선택해 주십시오.",
                options=list(select_options.keys())
            )

            selected_issue_id = select_options[selected_label]
            render_issue_detail(selected_issue_id)


# -----------------------------
# [캘린더] 페이지
# -----------------------------
elif page == "캘린더":
    st.subheader("캘린더")

    left_col, right_col = st.columns([2.0, 1.0], gap="large")

    with left_col:
        nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])

        with nav_col1:
            if st.button("◀ 이전달", key="calendar_prev_month", use_container_width=True):
                move_month(-1)

        with nav_col2:
            st.markdown(f"#### {st.session_state.current_year}년 {st.session_state.current_month}월")

        with nav_col3:
            if st.button("다음달 ▶", key="calendar_next_month", use_container_width=True):
                move_month(1)

        calendar_html = build_month_calendar_html(
            st.session_state.current_year,
            st.session_state.current_month,
            issues_df,
        )
        st.markdown(calendar_html, unsafe_allow_html=True)

    with right_col:
        st.markdown("### 월간 등록 목록")

        if issues_df.empty:
            st.info("현재 등록된 점검사항이 없습니다.")
        else:
            current_year = st.session_state.current_year
            current_month = st.session_state.current_month

            month_df = issues_df[
                (pd.to_datetime(issues_df["기한일"]).dt.year == current_year) &
                (pd.to_datetime(issues_df["기한일"]).dt.month == current_month)
            ].sort_values("기한일")

            if month_df.empty:
                st.info("선택한 월에 해당하는 점검사항이 없습니다.")
            else:
                st.dataframe(
                    month_df[["제목", "부서", "담당자", "기한일", "상태"]],
                    use_container_width=True,
                )


# -----------------------------
# [부서] 페이지
# -----------------------------
elif page == "부서":
    st.subheader("부서")

    if issues_df.empty:
        st.info("현재 등록된 점검사항이 없습니다.")
    else:
        dept_options = ["전체"] + sorted(
            [d for d in issues_df["부서"].dropna().unique().tolist() if str(d).strip() != ""]
        )

        selected_dept = st.selectbox("부서를 선택해 주십시오.", dept_options)

        if selected_dept == "전체":
            dept_df = issues_df.copy()
        else:
            dept_df = issues_df[issues_df["부서"] == selected_dept].copy()

        c1, c2, c3 = st.columns(3)
        c1.metric("전체 점검사항", len(dept_df))
        c2.metric("미완료 점검사항", len(dept_df[dept_df["상태"].isin(["미조치", "조치중", "조치확인요청"])]))
        c3.metric("완료 점검사항", len(dept_df[dept_df["상태"] == "완료"]))

        st.dataframe(
            dept_df[["id", "제목", "부서", "위치", "담당자", "등록자", "등록일", "기한일", "상태", "의견수"]],
            use_container_width=True,
        )
