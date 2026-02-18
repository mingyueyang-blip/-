# -*- coding: utf-8 -*-
"""
本地 SQLite：消费记录，区间=工作日/周末（周一00:00～周五23:59 / 周六00:00～周日23:59）。
周复盘：总 + 工作日 + 周末 的 消费、热量、用餐次数。
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "records.db"


def _ensure_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            菜品名 TEXT NOT NULL,
            金额 REAL NOT NULL,
            热量 INTEGER NOT NULL,
            模式 TEXT NOT NULL,
            品类 TEXT NOT NULL,
            创建时间 TEXT NOT NULL,
            区间 TEXT
        )
        """
    )
    # 兼容旧表：若无 区间 列则添加
    try:
        conn.execute("ALTER TABLE records ADD COLUMN 区间 TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def _parse_weekday(dt_str: str) -> int:
    """0=周一, 6=周日。"""
    try:
        dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
        return dt.weekday()
    except Exception:
        return 0


def _interval(weekday: int) -> str:
    """0-4 工作日, 5-6 周末。"""
    return "工作日" if weekday <= 4 else "周末"


def save_record(菜品名: str, 金额: float, 热量: int, 模式: str, 品类: str) -> None:
    _ensure_db()
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    区间 = _interval(now.weekday())
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT INTO records (菜品名, 金额, 热量, 模式, 品类, 创建时间, 区间) VALUES (?,?,?,?,?,?,?)",
        (菜品名, 金额, 热量, 模式, 品类, now_str, 区间),
    )
    conn.commit()
    conn.close()


def _week_bounds():
    """本周一 00:00 与本周日 23:59。"""
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    start_ts = datetime.combine(week_start, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
    end_ts = datetime.combine(week_end, datetime.max.time().replace(microsecond=0)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    return start_ts, end_ts


def get_week_stats() -> dict:
    """
    根据本周每日记录汇总：总 / 工作日 / 周末 的 消费、热量、用餐次数。
    时间范围：本周一 00:00 至本周日 23:59，从 records 表按 创建时间 筛选后加总。
    """
    _ensure_db()
    start_ts, end_ts = _week_bounds()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT 金额, 热量, 区间, 创建时间
        FROM records
        WHERE 创建时间 >= ? AND 创建时间 <= ?
        ORDER BY 创建时间
        """,
        (start_ts, end_ts),
    )
    rows = cur.fetchall()
    conn.close()

    total_amount = total_cal = 0.0
    work_amount = work_cal = 0.0
    weekend_amount = weekend_cal = 0.0
    work_count = weekend_count = 0

    for r in rows:
        amt, cal = r["金额"], r["热量"]
        ival = (r["区间"] or "").strip()
        if not ival and r["创建时间"]:
            ival = _interval(_parse_weekday(r["创建时间"]))
        total_amount += float(amt)
        total_cal += int(cal)
        if ival == "工作日":
            work_amount += float(amt)
            work_cal += int(cal)
            work_count += 1
        else:
            weekend_amount += float(amt)
            weekend_cal += int(cal)
            weekend_count += 1

    # 统计范围用于页面展示，便于确认是“按周加总”
    week_start = datetime.strptime(start_ts[:10], "%Y-%m-%d").date()
    week_end = datetime.strptime(end_ts[:10], "%Y-%m-%d").date()
    range_str = f"{week_start.month}月{week_start.day}日 - {week_end.month}月{week_end.day}日"

    return {
        "总消费": round(total_amount, 2),
        "总热量": int(total_cal),
        "工作日消费": round(work_amount, 2),
        "工作日热量": int(work_cal),
        "周末消费": round(weekend_amount, 2),
        "周末热量": int(weekend_cal),
        "总用餐次数": len(rows),
        "工作日用餐次数": work_count,
        "周末用餐次数": weekend_count,
        "统计范围": range_str,
    }


def get_week_records() -> list:
    """本周内所有记录（含 id、创建时间等），按创建时间正序，用于明细展示与编辑/删除。"""
    _ensure_db()
    start_ts, end_ts = _week_bounds()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT id, 菜品名, 金额, 热量, 模式, 品类, 创建时间, 区间
        FROM records
        WHERE 创建时间 >= ? AND 创建时间 <= ?
        ORDER BY 创建时间
        """,
        (start_ts, end_ts),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_record_by_id(record_id: int):
    """按 id 取一条记录，不存在返回 None。"""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT id, 菜品名, 金额, 热量, 模式, 品类, 创建时间, 区间 FROM records WHERE id = ?", (record_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_record(record_id: int, 菜品名: str, 金额: float, 热量: int, 模式: str, 品类: str) -> None:
    """按 id 更新一条记录；区间按创建时间不变（不改写入日），仅改金额/热量等。"""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "UPDATE records SET 菜品名=?, 金额=?, 热量=?, 模式=?, 品类=? WHERE id=?",
        (菜品名, 金额, 热量, 模式, 品类, record_id),
    )
    conn.commit()
    conn.close()


def delete_record(record_id: int) -> None:
    """按 id 删除一条记录。"""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
