# -*- coding: utf-8 -*-
"""
外卖扭蛋机（外卖减脂君）
首次模式选择弹窗 → 首页（扭蛋机区域背景图/红黑按钮）→ 扭蛋动画 → 结果弹窗 → 记录 → 本周总结独立页。
"""
import html as html_module
import json
import uuid
from pathlib import Path
from typing import Optional

import streamlit as st

from config.foods import draw
from db import save_record, get_week_stats, get_week_records, get_record_by_id, update_record, delete_record

_DRAW_CACHE = {}
CACHE_DIR = Path(__file__).resolve().parent / "data" / "draw_cache"
ASSETS = Path(__file__).resolve().parent / "assets"


def _save_draw_result(tid: str, result: dict) -> None:
    """抽卡结果写入文件，跳转后可从任意进程读取。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{tid}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)


def _load_draw_result(tid: str) -> Optional[dict]:
    """从文件读取抽卡结果；不在此处删文件，由关闭弹窗时清理（兼容 Python 3.7）。"""
    path = CACHE_DIR / f"{tid}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _delete_draw_result(tid: str) -> None:
    """删除某次抽卡的缓存文件。"""
    if not tid:
        return
    path = CACHE_DIR / f"{tid}.json"
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass

# 主色（方便后续修改）
TEAL = "#4ECDC4"
TEAL_LIGHT = "#E8F8F5"
RED = "#E74C3C"
RED_LIGHT = "#FADBD8"
BLACK = "#000000"
GRAY_TEXT = "#333333"
GRAY_SMALL = "#999999"
BUTTON_GRAY = "#EAECEE"  # 按钮未点击统一浅灰
SUBTITLE_YELLOW = "#F9E79F"  # 副标题暖黄


def inject_css():
    st.markdown(
        f"""
        <style>
        /* 整页背景：浅青绿 #E8F8F5 */
        .stApp {{ background: {TEAL_LIGHT}; font-family: "Comic Sans MS", "PingFang SC", "Microsoft YaHei", sans-serif; color: {BLACK}; line-height: 1.5; }}
        .main .block-container {{ max-width: 520px; padding: 0.5rem 1rem 1.5rem; }}
        /* 主标题「今天吃什么」：青绿 #4ECDC4，≥36px 加粗居中，圆润可爱 */
        h1 {{ color: {TEAL} !important; font-weight: 700; text-align: center; margin-bottom: 0.2rem; font-size: 2.5rem; font-family: "Comic Sans MS", "PingFang SC", sans-serif; }}
        /* 副标题：暖黄 20px 加粗居中 */
        .subtitle {{ text-align: center; color: {SUBTITLE_YELLOW}; font-size: 20px; font-weight: 700; margin-bottom: 0.5rem; }}
        .mode-badge {{ text-align: center; font-weight: 700; margin-bottom: 0.8rem; font-size: 1rem; color: {BLACK}; }}
        .recap-card {{ border-radius: 12px; padding: 1rem 1.2rem; margin: 0.5rem 0; font-size: 1.125rem; line-height: 1.5; color: {BLACK}; }}
        .recap-gray {{ background: #F5F5F5; border: 1px solid #e0e0e0; }}
        .recap-green {{ background: {TEAL_LIGHT}; border: 1px solid {TEAL}; }}
        .recap-yellow {{ background: #FFF8E1; border: 1px solid #e8d86a; }}
        .recap-count {{ margin-top: 0.5rem; color: {BLACK}; font-size: 1rem; }}
        /* 全站按钮默认：浅灰背景 + 深色字；统一点击/悬停交互 */
        [data-testid="stButton"] button {{
            background: {BUTTON_GRAY} !important; color: {GRAY_TEXT} !important; border: none !important;
            transition: background 0.2s, transform 0.15s, box-shadow 0.2s !important;
        }}
        [data-testid="stButton"] button:hover {{ filter: brightness(0.92); transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.12); }}
        [data-testid="stButton"] button:active {{ transform: translateY(0) scale(0.98); box-shadow: none; }}
        /* 模式切换链接按钮在下方用内联样式，此处仅统一样式 */
        .mode-btn-link {{ display: inline-block; padding: 0.5rem 1rem; border-radius: 0.5rem; text-decoration: none; font-weight: 600; text-align: center; transition: filter 0.2s, transform 0.15s; border: none; cursor: pointer; width: 48%; box-sizing: border-box; }}
        .mode-btn-link:hover {{ filter: brightness(1.1); transform: translateY(-1px); }}
        .mode-btn-link:active {{ transform: scale(0.98); }}
        /* 仅在这些包装内的按钮用黑底/红底白字（结果弹窗、总结页、记录页等） */
        .wrap-black-btn [data-testid="stButton"] button {{ background: {BLACK} !important; color: #fff !important; }}
        .wrap-red-btn [data-testid="stButton"] button {{ background: {RED} !important; color: #fff !important; }}
        /* 记录表单内「保存记录」为第一列按钮，按模式色 */
        .wrap-save-record-diet + div > div:nth-child(1) button {{ background: {TEAL} !important; color: #fff !important; }}
        .wrap-save-record-indulge + div > div:nth-child(1) button {{ background: {RED} !important; color: #fff !important; }}
        .recap-page h2 {{ font-size: 1.75rem; font-weight: 700; color: {BLACK}; text-align: center; }}
        /* 记录表单页：金额/热量标签强制深蓝字 + 浅蓝底（覆盖 Streamlit 白字） */
        .record-form-page ~ div label {{ background: #E3F2FD !important; color: #1565C0 !important; padding: 0.35rem 0.6rem !important; border-radius: 6px !important; font-weight: 700 !important; display: inline-block !important; }}
        .record-form-page ~ div [data-testid="stNumberInput"] label {{ background: #E3F2FD !important; color: #1565C0 !important; padding: 0.35rem 0.6rem !important; border-radius: 6px !important; font-weight: 700 !important; }}
        .record-form-page ~ div [data-testid="stNumberInput"] p {{ color: #1565C0 !important; font-weight: 600 !important; }}
        .record-form-page ~ div [data-testid="stNumberInput"] span {{ color: #1565C0 !important; }}
        /* 数字输入块内除 input 外所有文字强制蓝色 */
        .record-form-page ~ div [data-testid="stNumberInput"] *:not(input) {{ color: #1565C0 !important; }}
        /* 记录表单页：标记后所有块内文字（除输入框、按钮）强制蓝色，确保金额/热量标签可见 */
        .record-form-page ~ div *:not(input):not(button) {{ color: #1565C0 !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session():
    for k, v in [
        ("mode", "减脂"),
        ("result", None),
        ("show_modal", False),
        ("show_record_form", False),
        ("show_recap", False),
        ("success_message", False),
        ("animating", False),
        ("draw_tid", None),
        ("last_result_tid", None),  # 用于避免 show_result 后重复 rerun 死循环
        ("draw_tid_for_cleanup", None),  # 关闭弹窗时删对应缓存文件
        ("editing_record_id", None),   # 本周总结里正在编辑的记录 id
        ("delete_confirm_id", None),   # 待确认删除的记录 id
    ]:
        if k not in st.session_state:
            st.session_state[k] = v


def inject_mode_modal():
    """首次打开：模式选择弹窗，localStorage 控制只显示一次，选后跳转 ?mode= 同步服务端。"""
    st.markdown(
        """
        <div id="waimai-mode-modal" style="
            display: none;
            position: fixed; left: 0; right: 0; top: 0; bottom: 0;
            background: rgba(0,0,0,0.4); z-index: 10000;
            align-items: center; justify-content: center;
        ">
            <div style="
                background: #fff; border: 1px solid #000; border-radius: 12px;
                padding: 1.5rem; max-width: 320px; width: 90%; position: relative;
            ">
                <button id="waimai-mode-close" style="
                    position: absolute; right: 12px; top: 12px; background: none; border: none;
                    font-size: 1.2rem; cursor: pointer; color: #000;
                ">×</button>
                <p style="text-align: center; font-weight: 700; font-size: 1.1rem; margin-bottom: 1.2rem;">选择你的干饭模式</p>
                <div style="display: flex; flex-direction: column; gap: 0.6rem;">
                    <a id="waimai-btn-diet" href="#" style="
                        display: block; text-align: center; padding: 0.75rem;
                        background: #4ECDC4; color: #fff; font-weight: 600; border-radius: 8px; text-decoration: none;
                    ">🥗 减脂模式</a>
                    <a id="waimai-btn-indulge" href="#" style="
                        display: block; text-align: center; padding: 0.75rem;
                        background: #E74C3C; color: #fff; font-weight: 600; border-radius: 8px; text-decoration: none;
                    ">🍟 放纵模式</a>
                </div>
            </div>
        </div>
        <script>
        (function(){
            var key = 'waimai_mode_chosen';
            if (!localStorage.getItem(key)) {
                var el = document.getElementById('waimai-mode-modal');
                if (el) { el.style.display = 'flex'; }
            }
            function go(mode) {
                localStorage.setItem(key, mode);
                var u = new URL(window.location.href);
                u.searchParams.set('mode', mode);
                window.location.href = u.toString();
            }
            var diet = document.getElementById('waimai-btn-diet');
            var indulge = document.getElementById('waimai-btn-indulge');
            var close = document.getElementById('waimai-mode-close');
            if (diet) diet.onclick = function(e) { e.preventDefault(); go('diet'); };
            if (indulge) indulge.onclick = function(e) { e.preventDefault(); go('indulge'); };
            if (close) close.onclick = function() { go('diet'); };
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


def render_gashapon_animation_page(tid: str):
    ANIM_DURATION_MS = 2000
    tid_js = tid.replace("\\", "\\\\").replace('"', '\\"')
    st.markdown(
        f"""
        <div id="gashapon-wrap" style="
            position: fixed; left: 0; right: 0; top: 0; bottom: 0;
            background: linear-gradient(180deg, #4ECDC4 0%, #a8e8e4 50%, #ffffff 100%);
            z-index: 9999; display: flex; flex-direction: column; align-items: center; justify-content: center;
        ">
            <p style="color:#000;font-size:16px;margin-bottom:20px;">扭蛋中...</p>
            <div style="width: 200px; height: 260px; background: linear-gradient(145deg, #4ECDC4 0%, #7dd9d3 40%, #fff 100%);
                border-radius: 12px; position: relative; box-shadow: inset 0 0 0 4px rgba(255,255,255,0.5), 0 8px 24px rgba(78,205,196,0.35);">
                <div style="position: absolute; left: 50%; top: 12px; transform: translateX(-50%); width: 160px; height: 180px;
                    background: linear-gradient(180deg, #e8faf9 0%, #fff 100%); border-radius: 8px; overflow: hidden;">
                    <div id="egg" style="position: absolute; left: 50%; top: -40px; width: 36px; height: 36px; margin-left: -18px;
                        background: radial-gradient(circle at 30% 30%, #fff, transparent 45%), linear-gradient(135deg, #4ECDC4 0%, #FFE66D 100%);
                        border-radius: 50%; box-shadow: 0 2px 8px rgba(0,0,0,0.15); animation: eggDrop 2s ease-out forwards;"></div>
                </div>
                <div style="position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%); width: 120px; height: 12px; background: #4ECDC4; border-radius: 4px;"></div>
            </div>
        </div>
        <style>@keyframes eggDrop {{ 0% {{ top: -40px; transform: translateX(-50%) rotate(0deg); opacity: 1; }} 75% {{ top: 130px; transform: translateX(-50%) rotate(360deg); opacity: 1; }} 90% {{ top: 155px; transform: translateX(-50%) rotate(400deg); opacity: 1; }} 100% {{ top: 168px; transform: translateX(-50%) scale(1.3); opacity: 0; }} }}</style>
        <script>
        setTimeout(function(){{
            var w = document.getElementById('gashapon-wrap'); if (w) w.style.opacity = '0';
            setTimeout(function(){{
                var u = new URL(window.location.href); u.searchParams.set('show_result', '1'); u.searchParams.set('tid', "{tid_js}");
                (window.top || window).location.href = u.toString();
            }}, 350);
        }}, {ANIM_DURATION_MS});
        </script>
        """,
        unsafe_allow_html=True,
    )


def render_result_modal(r, is_diet):
    """结果弹窗：顶部用 emoji 点缀，就吃这个按模式青绿/红。"""
    title_small = "今天吃！" if is_diet else "快乐干饭！"
    dish_name = r["菜品名"]
    st.markdown('<div style="text-align:center;font-size:48px;">🥗</div>' if is_diet else '<div style="text-align:center;font-size:48px;">🍟</div>', unsafe_allow_html=True)

    if is_diet:
        notice_lines = "".join(
            f'<p style="margin:0.25rem 0;color:#000;font-size:16px;">{i+1}. {html_module.escape(x)}</p>'
            for i, x in enumerate(r["注意事项"][:5])
        )
        notice_html = f'<p style="color:{BLACK};font-weight:700;font-size:16px;margin:0.6rem 0 0.3rem;"># 注意事项</p><div style="background:{TEAL_LIGHT};border-left:4px solid {TEAL};padding:0.5rem 0.75rem;border-radius:0 8px 8px 0;margin:0.4rem 0;">{notice_lines}</div>'
    else:
        notice_html = f'<p style="color:{BLACK};font-weight:700;font-size:16px;margin:0.6rem 0 0.3rem;"># 快乐提示</p><div style="background:{RED_LIGHT};border-left:4px solid {RED};padding:0.5rem 0.75rem;border-radius:0 8px 8px 0;margin:0.4rem 0;"><p style="margin:0;color:#000;font-size:16px;">{html_module.escape(r["快乐提示"])}</p></div>'

    calorie_str = str(r.get("热量", ""))  # 热量为数字，转为字符串显示
    st.markdown(
        f'''
        <div style="width: 60%; max-width: 400px; margin: 0 auto 0; background: #FFFFFF; border: 1px solid #000; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1); overflow: hidden;">
            <div style="padding: 0 1.25rem 1rem; border-bottom: 1px solid #ddd;">
                <p style="margin:0;font-size:14px;color:{BLACK};">{html_module.escape(title_small)}</p>
                <p style="margin:0.25rem 0 0;font-size:24px;font-weight:700;color:{BLACK};">{html_module.escape(dish_name)}</p>
                <p style="margin:0.4rem 0 0;font-size:14px;color:{BLACK};">热量约 {html_module.escape(calorie_str)} kcal</p>
            </div>
            <div style="padding: 1rem 1.25rem;">
                <p style="color:{BLACK};font-weight:700;font-size:16px;margin:0 0 0.3rem;"># 推荐搭配</p>
                <p style="margin:0;color:{BLACK};font-size:16px;">{html_module.escape(r["搭配"])}</p>
                {notice_html}
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    rc0, rc1, rc2, rc3 = st.columns([2, 3, 3, 2])
    with rc1:
        if st.button("再抽一次", key="btn_again", use_container_width=True):
            _delete_draw_result(st.session_state.get("draw_tid_for_cleanup") or "")
            st.session_state.show_modal = False
            st.session_state.result = None
            st.session_state.draw_tid_for_cleanup = None
            st.session_state.last_result_tid = None
            st.rerun()
    with rc2:
        if st.button("就吃这个", key="btn_confirm", use_container_width=True):
            _delete_draw_result(st.session_state.get("draw_tid_for_cleanup") or "")
            st.session_state.show_modal = False
            st.session_state.draw_tid_for_cleanup = None
            st.session_state.last_result_tid = None
            st.session_state.show_record_form = True
            st.session_state.record_prefill = {"菜品名": r["菜品名"], "热量": r["热量"], "模式": r["模式"], "品类": r["品类"]}
            st.rerun()


def main():
    st.set_page_config(page_title="今天吃什么", page_icon="🍱", layout="centered", initial_sidebar_state="collapsed")
    inject_css()
    init_session()

    q = st.query_params
    if q.get("mode") == "diet":
        st.session_state.mode = "减脂"
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.rerun()
    if q.get("mode") == "indulge":
        st.session_state.mode = "放纵"
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.rerun()

    # 动画结束后浏览器跳转 ?show_result=1&tid=xxx；用 last_result_tid 避免同一 tid 重复 rerun 死循环
    if q.get("show_result") == "1":
        tid = (q.get("tid") or "").strip()
        if tid and st.session_state.get("last_result_tid") == tid:
            st.session_state.animating = False
        else:
            cached = _DRAW_CACHE.pop(tid, None) if tid else None
            if cached is None and tid:
                cached = _load_draw_result(tid)
            if cached is not None:
                st.session_state.result = cached
                st.session_state.show_modal = True
                st.session_state.draw_tid_for_cleanup = tid
                st.session_state.last_result_tid = tid
                st.session_state.animating = False
                st.rerun()
            else:
                st.session_state.animating = False

    inject_mode_modal()

    # 本周总结独立页：数据可改可删，可查看哪一天记录
    if st.session_state.get("show_recap"):
        st.markdown("<div class='recap-page' style='background:#E8F8F5;min-height:100vh;'>", unsafe_allow_html=True)
        st.subheader("本周总结")

        # 待删除确认
        if st.session_state.get("delete_confirm_id"):
            rid = st.session_state.delete_confirm_id
            st.warning("确认删除该条记录？")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("确认删除", key="confirm_del"):
                    delete_record(rid)
                    st.session_state.delete_confirm_id = None
                    st.rerun()
            with c2:
                if st.button("取消", key="cancel_del"):
                    st.session_state.delete_confirm_id = None
                    st.rerun()
            st.stop()

        # 正在编辑某条记录：显示编辑表单
        editing_id = st.session_state.get("editing_record_id")
        if editing_id:
            rec = get_record_by_id(editing_id)
            if rec:
                st.markdown("**编辑本条记录**")
                with st.form("edit_record_form"):
                    name = st.text_input("菜品/说明", value=rec["菜品名"], key="edit_name")
                    amount = st.number_input("金额（元）", value=float(rec["金额"]), min_value=0.0, step=0.1, format="%.1f", key="edit_amount")
                    calorie = st.number_input("热量（千卡）", value=int(rec["热量"]), min_value=0, step=10, key="edit_calorie")
                    mode = st.selectbox("模式", ["减脂", "放纵"], index=0 if rec["模式"] == "减脂" else 1, key="edit_mode")
                    submitted = st.form_submit_button("保存修改")
                    if submitted:
                        update_record(editing_id, name, float(amount), int(calorie), mode, rec["品类"])
                        st.session_state.editing_record_id = None
                        st.rerun()
                if st.button("取消编辑", key="cancel_edit"):
                    st.session_state.editing_record_id = None
                    st.rerun()
                st.markdown("---")
            else:
                st.session_state.editing_record_id = None

        # 每次进入都从数据库重新查询并加总
        stats = get_week_stats()
        range_str = stats.get("统计范围", "")
        n = stats["总用餐次数"]
        st.markdown(
            f'<p style="text-align:center;color:#333;font-size:0.9rem;margin-bottom:0.25rem;">以下数据由<strong>本地数据库</strong>中本周内每条记录<strong>实时加总</strong>得出，可编辑/删除</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="text-align:center;color:#666;font-size:0.85rem;margin-bottom:0.5rem;">统计范围 {range_str} · 参与汇总 {n} 条</p>',
            unsafe_allow_html=True,
        )
        if n == 0:
            st.info("暂无记录。在首页「记录今日外卖金额」或抽卡后「就吃这个」保存记录后，此处会显示汇总。")
        else:
            st.markdown(
                f'<div class="recap-card recap-gray"><strong>本周总消费</strong> ¥{stats["总消费"]}<br><strong>本周总热量</strong> {stats["总热量"]} kcal</div>',
                unsafe_allow_html=True,
            )
            r1, r2 = st.columns(2)
            with r1:
                body = "本周工作日暂无消费记录" if stats["工作日用餐次数"] == 0 else f'<strong>工作日</strong><br>消费 ¥{stats["工作日消费"]} · 热量 {stats["工作日热量"]} kcal'
                st.markdown(f'<div class="recap-card recap-green">{body}</div>', unsafe_allow_html=True)
            with r2:
                body = "本周周末暂无消费记录" if stats["周末用餐次数"] == 0 else f'<strong>周末</strong><br>消费 ¥{stats["周末消费"]} · 热量 {stats["周末热量"]} kcal'
                st.markdown(f'<div class="recap-card recap-yellow">{body}</div>', unsafe_allow_html=True)
            st.markdown(f'<p class="recap-count">用餐次数：本周 {stats["总用餐次数"]} 次（工作日 {stats["工作日用餐次数"]} 次，周末 {stats["周末用餐次数"]} 次）</p>', unsafe_allow_html=True)

            # 本周记录明细：显示哪一天记录的，可编辑/删除
            st.markdown("**本周记录明细**")
            records = get_week_records()
            for rec in records:
                try:
                    dt = rec["创建时间"][:10]  # 2025-02-16
                    y, m, d = dt.split("-")
                    day_str = f"{int(m)}月{int(d)}日"
                except Exception:
                    day_str = rec["创建时间"][:16]
                row = f"**{day_str}** · {rec['菜品名']} · ¥{rec['金额']} · {rec['热量']} kcal · {rec['模式']}"
                c1, c2, c3 = st.columns([3, 0.6, 0.6])
                with c1:
                    st.markdown(row)
                with c2:
                    if st.button("编辑", key=f"recap_edit_{rec['id']}"):
                        st.session_state.editing_record_id = rec["id"]
                        st.rerun()
                with c3:
                    if st.button("删除", key=f"recap_del_{rec['id']}"):
                        st.session_state.delete_confirm_id = rec["id"]
                        st.rerun()
                st.markdown("")

        st.markdown('<div class="wrap-black-btn">', unsafe_allow_html=True)
        col_back, col_refresh = st.columns(2)
        with col_back:
            if st.button("返回首页", key="btn_back"):
                st.session_state.show_recap = False
                st.session_state.success_message = False
                st.session_state.editing_record_id = None
                st.session_state.delete_confirm_id = None
                st.rerun()
        with col_refresh:
            if st.button("刷新数据", key="btn_refresh_recap"):
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    # 记录外卖消费表单（来自抽卡「就吃这个」或入口「记录今日外卖金额」）
    if st.session_state.get("show_record_form") and st.session_state.get("record_prefill"):
        pre = st.session_state.record_prefill
        st.markdown('<div class="record-form-page" style="display:none;" aria-hidden="true"></div>', unsafe_allow_html=True)
        st.subheader("记录外卖消费")
        amount = st.number_input(
            "请输入本次外卖金额（元）",
            min_value=0.0,
            max_value=9999.0,
            value=0.0,
            step=0.1,
            format="%.1f",
            help="≥0，最多 1 位小数",
        )
        calorie = st.number_input(
            "🔥 预估热量（千卡，可选）",
            min_value=0,
            max_value=5000,
            value=pre["热量"],
            step=10,
            help="减脂默认 150–350，放纵默认 500–1200，可改",
        )
        save_class = "wrap-save-record-diet" if pre["模式"] == "减脂" else "wrap-save-record-indulge"
        st.markdown(f'<div class="{save_class}" style="display:none;"></div>', unsafe_allow_html=True)
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("保存记录", key="btn_save", use_container_width=True):
                if amount < 0:
                    st.error("请输入有效的金额（≥0，最多 1 位小数）")
                else:
                    save_record(菜品名=pre["菜品名"], 金额=float(amount), 热量=int(calorie), 模式=pre["模式"], 品类=pre["品类"])
                    st.session_state.show_record_form = False
                    st.session_state.record_prefill = None
                    st.session_state.success_message = True
                    st.rerun()
        with col_cancel:
            if st.button("取消", key="btn_cancel_record", use_container_width=True):
                st.session_state.show_record_form = False
                st.session_state.record_prefill = None
                st.rerun()
        st.stop()

    if st.session_state.get("success_message"):
        st.markdown("<p style='text-align:center;font-size:1.2rem;font-weight:700;color:#000;'>保存成功</p>", unsafe_allow_html=True)
        st.markdown('<div class="wrap-black-btn">', unsafe_allow_html=True)
        if st.button("返回首页", key="btn_home_after_save"):
            st.session_state.success_message = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    # 抽卡结果弹窗
    if st.session_state.show_modal and st.session_state.result:
        r = st.session_state.result
        render_result_modal(r, r["模式"] == "减脂")
        st.stop()

    # 扭蛋动画中（有 draw_tid 即播动画，2 秒后跳转；结果由文件/内存缓存取回）
    if st.session_state.get("animating"):
        tid = st.session_state.get("draw_tid") or ""
        if tid:
            render_gashapon_animation_page(tid)
        else:
            st.session_state.animating = False
            st.rerun()
        st.stop()

    # 首页
    st.title("今天吃什么")
    st.markdown('<p class="subtitle">抽一抽，吃饭不纠结</p>', unsafe_allow_html=True)
    mode = st.session_state.mode
    st.markdown(f'<p class="mode-badge">当前模式：{mode}模式</p>', unsafe_allow_html=True)

    # 模式切换：用 HTML 链接当按钮，服务端直接输出颜色，选中=青色/红色、未选=灰
    bg_diet = TEAL if mode == "减脂" else BUTTON_GRAY
    color_diet = "#fff" if mode == "减脂" else GRAY_TEXT
    bg_indulge = RED if mode == "放纵" else BUTTON_GRAY
    color_indulge = "#fff" if mode == "放纵" else GRAY_TEXT
    st.markdown(
        f'''
        <div style="display:flex; gap:0.5rem; justify-content:center; margin-bottom:1rem;">
            <a class="mode-btn-link" href="?mode=diet" style="background:{bg_diet}; color:{color_diet};">
                🥗 减脂模式
            </a>
            <a class="mode-btn-link" href="?mode=indulge" style="background:{bg_indulge}; color:{color_indulge};">
                🍟 放纵模式
            </a>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # 抽卡按钮：上移至扭蛋机上方，按当前模式青绿/红（标记 + 相邻选择器）
    draw_class = "draw-diet" if mode == "减脂" else "draw-indulge"
    st.markdown(f'<div class="draw-marker {draw_class}" style="display:none;" aria-hidden="true"></div>', unsafe_allow_html=True)
    if st.button("点击抽取食物扭蛋！", key="btn_draw", use_container_width=True):
        result = draw(st.session_state.mode)
        tid = str(uuid.uuid4())
        _DRAW_CACHE[tid] = result
        _save_draw_result(tid, result)
        st.session_state["draw_tid"] = tid
        st.session_state["draw_tid_for_cleanup"] = tid
        st.session_state.result = result
        st.session_state.show_modal = True
        st.session_state.animating = False
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    # 扭蛋机区域：优先使用扭蛋机图片，无图时用渐变
    gashapon_img = ASSETS / "gashapon.png"
    if gashapon_img.exists():
        st.image(str(gashapon_img), use_container_width=True)
    else:
        st.markdown(
            f'<div style="min-height:240px;border-radius:16px;background:linear-gradient(180deg, {TEAL if mode == "减脂" else RED} 0%, {TEAL_LIGHT if mode == "减脂" else RED_LIGHT} 100%);display:flex;align-items:center;justify-content:center;color:#000;font-size:1.1rem;">扭蛋机</div>',
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)

    # 记录今日外卖金额：浅灰 #EAECEE + 黑字，点击后弹出记录表单
    if st.button("记录今日外卖金额", key="btn_manual_record", use_container_width=True):
        default_cal = 250 if mode == "减脂" else 850  # 减脂 150–350 / 放纵 500–1200 中值
        st.session_state.record_prefill = {
            "菜品名": "外卖消费",
            "热量": default_cal,
            "模式": mode,
            "品类": "其他",
        }
        st.session_state.show_record_form = True
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 底部功能区：查看本周总结，移至最底部，浅灰 #EAECEE + 黑字，点击切到本周总结（动态数据）
    if st.button("查看本周总结", key="btn_recap", use_container_width=True):
        stats = get_week_stats()
        if stats["总用餐次数"] == 0:
            st.warning("本周暂无消费记录哦～")
        else:
            st.session_state.show_recap = True
        st.rerun()


if __name__ == "__main__":
    main()
