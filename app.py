# =========================================================
# CM 체크리스트 관리 웹앱
# - 단순한 인터페이스 버전
# - 홈 / 점검사항 등록 / 조치사항 등록 / 캘린더 / 부서 페이지 포함
# - 현재는 로그인 기능 없이 "관리자 모드"로 동작
# - 따라서 점검사항, 조치사항 모두 등록 / 삭제 가능
# =========================================================

# -----------------------------
# 1. 필요한 라이브러리 불러오기
# -----------------------------
import streamlit as st              # 웹앱 화면 구성용
import pandas as pd                # 표 데이터 처리용
import calendar                    # 월간 달력 생성용
from datetime import date          # 오늘 날짜 처리용


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
# 너무 복잡하지 않게 최소한의 스타일만 적용
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1.5rem;
    }

    .simple-nav-box {
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 14px;
        background-color: #111111;
    }

    .section-box {
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        background-color: #0f1116;
    }

    .calendar-wrapper {
        border: 1px solid #2a2a2a;
        border-radius: 14px;
        overflow: hidden;
        background-color: #0f1116;
    }

    .calendar-header {
        padding: 12px 14px;
        font-size: 20px;
        font-weight: 700;
        border-bottom: 1px solid #2a2a2a;
        background-color: #111111;
    }

    .calendar-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }

    .calendar-table th {
        border: 1px solid #2a2a2a;
        padding: 8px;
        text-align: center;
        background-color: #151515;
        font-size: 14px;
    }

    .calendar-table td {
        border: 1px solid #2a2a2a;
        height: 105px;
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

    .small-line {
        font-size: 12px;
        line-height: 1.45;
        margin-bottom: 2px;
    }

    .red-text {
        color: #ff6b6b;
        font-weight: 700;
    }

    .green-text {
        color: #51cf66;
        font-weight: 700;
    }

    .gray-text {
        color: #bdbdbd;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# -----------------------------
# 4. 공통 컬럼 정의
# -----------------------------
# 점검사항 / 조치사항을 같은 구조로 관리하기 위해 공통 컬럼 사용
COMMON_COLUMNS = [
    "id",
    "구분",
    "제목",
    "부서",
    "위치",
    "담당자",
    "등록일",
    "기한일",
    "상태",
    "비고",
]


# -----------------------------
# 5. 세션 상태 초기화
# -----------------------------
# 세션 상태: 앱이 켜져 있는 동안 임시로 데이터 저장
def init_session_state():
    # 현재 사용자를 관리자처럼 취급
    # 나중에 로그인 기능 추가 시 True/False로 제어 가능
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = True

    # 점검사항 저장 리스트
    if "inspection_items" not in st.session_state:
        st.session_state.inspection_items = []

    # 조치사항 저장 리스트
    if "action_items" not in st.session_state:
        st.session_state.action_items = []

    # 점검사항 ID 자동 증가용
    if "inspection_next_id" not in st.session_state:
        st.session_state.inspection_next_id = 1

    # 조치사항 ID 자동 증가용
    if "action_next_id" not in st.session_state:
        st.session_state.action_next_id = 1

    # 달력 표시용 현재 연/월
    if "current_year" not in st.session_state:
        st.session_state.current_year = date.today().year

    if "current_month" not in st.session_state:
        st.session_state.current_month = date.today().month


init_session_state()


# -----------------------------
# 6. 데이터프레임 반환 함수
# -----------------------------
def get_df_from_store(store_name):
    """
    세션 상태에 저장된 리스트를 DataFrame으로 변환
    데이터가 없으면 빈 표를 반환
    """
    raw_list = st.session_state[store_name]

    if len(raw_list) == 0:
        return pd.DataFrame(columns=COMMON_COLUMNS)

    df = pd.DataFrame(raw_list, columns=COMMON_COLUMNS)
    df["등록일"] = pd.to_datetime(df["등록일"]).dt.date
    df["기한일"] = pd.to_datetime(df["기한일"]).dt.date
    return df


def get_all_items_df():
    """
    점검사항 + 조치사항을 합친 전체 데이터 표 생성
    """
    df_inspection = get_df_from_store("inspection_items")
    df_action = get_df_from_store("action_items")

    if df_inspection.empty and df_action.empty:
        return pd.DataFrame(columns=COMMON_COLUMNS)

    return pd.concat([df_inspection, df_action], ignore_index=True)


# -----------------------------
# 7. 등록 함수
# -----------------------------
def add_item(store_name, next_id_name, item_type, title, dept, location, assignee, due_date, status, note):
    """
    입력받은 내용을 세션 상태 리스트에 저장
    """
    new_id = st.session_state[next_id_name]

    st.session_state[store_name].append(
        {
            "id": new_id,
            "구분": item_type,
            "제목": title.strip(),
            "부서": dept.strip(),
            "위치": location.strip(),
            "담당자": assignee.strip(),
            "등록일": date.today(),
            "기한일": due_date,
            "상태": status,
            "비고": note.strip(),
        }
    )

    # 다음 ID 증가
    st.session_state[next_id_name] += 1


# -----------------------------
# 8. 삭제 함수
# -----------------------------
def delete_item_by_id(store_name, item_id):
    """
    선택한 ID의 항목을 삭제
    """
    new_list = [
        item for item in st.session_state[store_name]
        if item["id"] != item_id
    ]
    st.session_state[store_name] = new_list


# -----------------------------
# 9. 달 이동 함수
# -----------------------------
def move_month(delta):
    """
    이전달 / 다음달 이동
    delta = -1 이면 이전달
    delta = +1 이면 다음달
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
# 10. 월간 달력 HTML 생성 함수
# -----------------------------
def build_month_calendar_html(year, month, df):
    """
    월간 달력 HTML 생성
    - 점검사항/조치사항 개수 표시
    - 미완료/완료 개수 표시
    """
    cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
    weeks = cal.monthdatescalendar(year, month)
    today = date.today()

    html_parts = []
    html_parts.append('<div class="calendar-wrapper">')
    html_parts.append(f'<div class="calendar-header">{year}년 {month}월</div>')
    html_parts.append('<table class="calendar-table">')

    # 요일 헤더
    html_parts.append("<thead><tr>")
    for day_name in ["일", "월", "화", "수", "목", "금", "토"]:
        html_parts.append(f"<th>{day_name}</th>")
    html_parts.append("</tr></thead>")

    # 날짜 셀
    html_parts.append("<tbody>")
    for week in weeks:
        html_parts.append("<tr>")

        for day in week:
            # 해당 날짜의 항목들만 추출
            day_df = df[df["기한일"] == day].copy()

            # 다른 달 날짜는 흐리게 표시
            other_class = "day-other-month" if day.month != month else ""

            # 오늘 날짜는 파란 테두리
            today_class = "today-cell" if day == today else ""

            cell_class = f"{other_class} {today_class}".strip()

            html_parts.append(f'<td class="{cell_class}">')
            html_parts.append(f'<div class="day-number">{day.day}</div>')

            # 현재 달에 속한 날짜만 상세 표시
            if day.month == month and not day_df.empty:
                inspection_count = len(day_df[day_df["구분"] == "점검사항"])
                action_count = len(day_df[day_df["구분"] == "조치사항"])
                open_count = len(day_df[day_df["상태"] != "완료"])
                done_count = len(day_df[day_df["상태"] == "완료"])

                html_parts.append(
                    f'<div class="small-line gray-text">점검 {inspection_count} / 조치 {action_count}</div>'
                )
                html_parts.append(
                    f'<div class="small-line red-text">미완료 {open_count}</div>'
                )
                html_parts.append(
                    f'<div class="small-line green-text">완료 {done_count}</div>'
                )

            html_parts.append("</td>")

        html_parts.append("</tr>")
    html_parts.append("</tbody>")
    html_parts.append("</table></div>")

    return "".join(html_parts)


# -----------------------------
# 11. 간단 목록 출력 함수
# -----------------------------
def render_simple_list(title, df, empty_message):
    """
    우측 요약 영역에 간단 목록 출력
    """
    st.markdown(f"#### {title}")

    if df.empty:
        st.info(empty_message)
        return

    # 최신/중요 순으로 최대 5개만 출력
    for _, row in df.head(5).iterrows():
        with st.container(border=True):
            st.write(f"**{row['제목']}**")
            st.write(f"- 구분: {row['구분']}")
            st.write(f"- 부서: {row['부서']}")
            st.write(f"- 담당자: {row['담당자']}")
            st.write(f"- 기한일: {row['기한일']}")
            st.write(f"- 상태: {row['상태']}")


# -----------------------------
# 12. 삭제용 선택 박스 출력 함수
# -----------------------------
def render_delete_box(df, store_name, item_type_label):
    """
    현재 페이지의 항목 삭제 UI
    """
    if not st.session_state.is_admin:
        st.warning("현재 사용자는 삭제 권한이 없습니다.")
        return

    if df.empty:
        return

    st.markdown("##### 삭제")

    # 삭제용 표시 문자열 생성
    option_map = {
        f"[ID {row['id']}] {row['제목']} / {row['기한일']}": row["id"]
        for _, row in df.iterrows()
    }

    selected_label = st.selectbox(
        f"삭제할 {item_type_label} 선택",
        options=["선택 안 함"] + list(option_map.keys()),
        key=f"delete_select_{store_name}"
    )

    if st.button(f"{item_type_label} 삭제", key=f"delete_button_{store_name}"):
        if selected_label == "선택 안 함":
            st.warning("삭제할 항목을 선택하세요.")
        else:
            target_id = option_map[selected_label]
            delete_item_by_id(store_name, target_id)
            st.success(f"{item_type_label} 삭제 완료")
            st.rerun()


# -----------------------------
# 13. 상단 제목
# -----------------------------
st.title("CM 체크리스트 관리 웹앱")


# -----------------------------
# 14. 상단 메뉴바
# -----------------------------
# 왼쪽: 메뉴
# 오른쪽: 로그인 자리 비워둠
nav_left, nav_right = st.columns([8, 2])

with nav_left:
    page = st.radio(
        "메뉴",
        options=["홈", "점검사항 등록", "조치사항 등록", "캘린더", "부서"],
        horizontal=True,
        label_visibility="collapsed"
    )

with nav_right:
    # 로그인 자리용 빈 공간
    st.markdown(
        """
        <div class="simple-nav-box" style="height: 48px;"></div>
        """,
        unsafe_allow_html=True
    )


# -----------------------------
# 15. 공통 데이터 준비
# -----------------------------
all_df = get_all_items_df()

# 날짜 정렬이 필요할 때 대비
if not all_df.empty:
    all_df = all_df.sort_values(by=["기한일", "구분", "id"]).reset_index(drop=True)


# =========================================================
# 16. 페이지별 화면 구성
# =========================================================

# -----------------------------
# [홈] 페이지
# -----------------------------
if page == "홈":
    st.subheader("홈")

    # 요약 수치 계산
    if all_df.empty:
        total_count = 0
        open_count = 0
        overdue_count = 0
        done_count = 0
    else:
        total_count = len(all_df)
        open_count = len(all_df[all_df["상태"] != "완료"])
        overdue_count = len(all_df[(all_df["상태"] != "완료") & (all_df["기한일"] < date.today())])
        done_count = len(all_df[all_df["상태"] == "완료"])

    # 상단 요약 카드
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 항목", total_count)
    c2.metric("미완료 항목", open_count)
    c3.metric("기한초과 항목", overdue_count)
    c4.metric("완료 항목", done_count)

    left_col, right_col = st.columns([2.1, 1.0], gap="large")

    with left_col:
        st.markdown("### 월간 캘린더")

        move_col1, move_col2, move_col3 = st.columns([1, 3, 1])

        with move_col1:
            if st.button("◀ 이전달", key="home_prev_month", use_container_width=True):
                move_month(-1)

        with move_col2:
            st.markdown(
                f"#### {st.session_state.current_year}년 {st.session_state.current_month}월"
            )

        with move_col3:
            if st.button("다음달 ▶", key="home_next_month", use_container_width=True):
                move_month(1)

        calendar_html = build_month_calendar_html(
            st.session_state.current_year,
            st.session_state.current_month,
            all_df
        )
        st.markdown(calendar_html, unsafe_allow_html=True)

    with right_col:
        unresolved_df = all_df[all_df["상태"] != "완료"].sort_values("기한일") if not all_df.empty else all_df
        overdue_df = all_df[(all_df["상태"] != "완료") & (all_df["기한일"] < date.today())].sort_values("기한일") if not all_df.empty else all_df
        recent_done_df = all_df[all_df["상태"] == "완료"].sort_values("등록일", ascending=False) if not all_df.empty else all_df

        render_simple_list("미완료 항목", unresolved_df, "현재 미완료 항목이 없습니다.")
        render_simple_list("기한초과 항목", overdue_df, "현재 기한초과 항목이 없습니다.")
        render_simple_list("최근 완료 항목", recent_done_df, "최근 완료 항목이 없습니다.")


# -----------------------------
# [점검사항 등록] 페이지
# -----------------------------
elif page == "점검사항 등록":
    st.subheader("점검사항 등록")

    # 점검사항 등록 폼
    with st.form("inspection_form"):
        col1, col2 = st.columns(2)

        with col1:
            inspection_title = st.text_input("제목")
            inspection_dept = st.text_input("부서")
            inspection_location = st.text_input("위치")

        with col2:
            inspection_assignee = st.text_input("담당자")
            inspection_due_date = st.date_input("기한일", value=date.today())
            inspection_status = st.selectbox("상태", ["미조치", "조치중", "완료"])

        inspection_note = st.text_area("비고")
        inspection_submit = st.form_submit_button("점검사항 등록")

        if inspection_submit:
            if inspection_title.strip() == "":
                st.error("제목은 비워둘 수 없습니다.")
            else:
                add_item(
                    store_name="inspection_items",
                    next_id_name="inspection_next_id",
                    item_type="점검사항",
                    title=inspection_title,
                    dept=inspection_dept,
                    location=inspection_location,
                    assignee=inspection_assignee,
                    due_date=inspection_due_date,
                    status=inspection_status,
                    note=inspection_note,
                )
                st.success("점검사항 등록 완료")
                st.rerun()

    st.divider()

    # 현재 등록된 점검사항 목록
    st.markdown("### 현재 등록된 점검사항")
    inspection_df = get_df_from_store("inspection_items")

    if inspection_df.empty:
        st.info("등록된 점검사항이 없습니다.")
    else:
        inspection_df = inspection_df.sort_values(by=["기한일", "id"]).reset_index(drop=True)
        st.dataframe(
            inspection_df[["id", "제목", "부서", "위치", "담당자", "등록일", "기한일", "상태", "비고"]],
            use_container_width=True
        )

    # 삭제 기능
    render_delete_box(inspection_df, "inspection_items", "점검사항")


# -----------------------------
# [조치사항 등록] 페이지
# -----------------------------
elif page == "조치사항 등록":
    st.subheader("조치사항 등록")

    # 조치사항 등록 폼
    with st.form("action_form"):
        col1, col2 = st.columns(2)

        with col1:
            action_title = st.text_input("제목")
            action_dept = st.text_input("부서")
            action_location = st.text_input("위치")

        with col2:
            action_assignee = st.text_input("담당자")
            action_due_date = st.date_input("기한일", value=date.today())
            action_status = st.selectbox("상태", ["미조치", "조치중", "완료"])

        action_note = st.text_area("비고")
        action_submit = st.form_submit_button("조치사항 등록")

        if action_submit:
            if action_title.strip() == "":
                st.error("제목은 비워둘 수 없습니다.")
            else:
                add_item(
                    store_name="action_items",
                    next_id_name="action_next_id",
                    item_type="조치사항",
                    title=action_title,
                    dept=action_dept,
                    location=action_location,
                    assignee=action_assignee,
                    due_date=action_due_date,
                    status=action_status,
                    note=action_note,
                )
                st.success("조치사항 등록 완료")
                st.rerun()

    st.divider()

    # 현재 등록된 조치사항 목록
    st.markdown("### 현재 등록된 조치사항")
    action_df = get_df_from_store("action_items")

    if action_df.empty:
        st.info("등록된 조치사항이 없습니다.")
    else:
        action_df = action_df.sort_values(by=["기한일", "id"]).reset_index(drop=True)
        st.dataframe(
            action_df[["id", "제목", "부서", "위치", "담당자", "등록일", "기한일", "상태", "비고"]],
            use_container_width=True
        )

    # 삭제 기능
    render_delete_box(action_df, "action_items", "조치사항")


# -----------------------------
# [캘린더] 페이지
# -----------------------------
elif page == "캘린더":
    st.subheader("캘린더")

    left_col, right_col = st.columns([2.1, 1.0], gap="large")

    with left_col:
        move_col1, move_col2, move_col3 = st.columns([1, 3, 1])

        with move_col1:
            if st.button("◀ 이전달", key="calendar_prev_month", use_container_width=True):
                move_month(-1)

        with move_col2:
            st.markdown(
                f"#### {st.session_state.current_year}년 {st.session_state.current_month}월"
            )

        with move_col3:
            if st.button("다음달 ▶", key="calendar_next_month", use_container_width=True):
                move_month(1)

        calendar_html = build_month_calendar_html(
            st.session_state.current_year,
            st.session_state.current_month,
            all_df
        )
        st.markdown(calendar_html, unsafe_allow_html=True)

    with right_col:
        st.markdown("### 월간 항목 요약")

        if all_df.empty:
            st.info("현재 등록된 항목이 없습니다.")
        else:
            current_year = st.session_state.current_year
            current_month = st.session_state.current_month

            month_df = all_df[
                (pd.to_datetime(all_df["기한일"]).dt.year == current_year) &
                (pd.to_datetime(all_df["기한일"]).dt.month == current_month)
            ].sort_values("기한일")

            if month_df.empty:
                st.info("선택한 월에 해당하는 항목이 없습니다.")
            else:
                st.dataframe(
                    month_df[["구분", "제목", "부서", "담당자", "기한일", "상태"]],
                    use_container_width=True
                )


# -----------------------------
# [부서] 페이지
# -----------------------------
elif page == "부서":
    st.subheader("부서")

    if all_df.empty:
        st.info("현재 등록된 항목이 없습니다.")
    else:
        dept_options = ["전체"] + sorted(
            [dept for dept in all_df["부서"].dropna().unique().tolist() if str(dept).strip() != ""]
        )

        selected_dept = st.selectbox("부서 선택", dept_options)

        if selected_dept == "전체":
            dept_df = all_df.copy()
        else:
            dept_df = all_df[all_df["부서"] == selected_dept].copy()

        # 부서별 요약
        c1, c2, c3 = st.columns(3)
        c1.metric("전체 건수", len(dept_df))
        c2.metric("미완료 건수", len(dept_df[dept_df["상태"] != "완료"]))
        c3.metric("완료 건수", len(dept_df[dept_df["상태"] == "완료"]))

        st.dataframe(
            dept_df[["구분", "제목", "부서", "위치", "담당자", "등록일", "기한일", "상태", "비고"]],
            use_container_width=True
        )