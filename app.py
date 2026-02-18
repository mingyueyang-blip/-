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
FOOD_ICONS = ASSETS / "food-icons"


def _asset_data_uri(relative_path: str) -> Optional[str]:
    """将 assets 下图片读为 data URI，便于嵌入 HTML 无需静态服务。"""
    path = ASSETS / relative_path
    if not path.exists():
        return None
    try:
        raw = path.read_bytes()
        ext = path.suffix.lower()
        mime = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        import base64
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


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
        /* 整页背景 + 禁止任何上下滑动，单屏静态 */
        .stApp {{ background: {TEAL_LIGHT}; font-family: "Comic Sans MS", "PingFang SC", "Microsoft YaHei", sans-serif; color: {BLACK}; line-height: 1.5; overflow: hidden !important; height: 100vh !important; max-height: 100vh !important; touch-action: none !important; }}
        section[data-testid="stAppViewContainer"] {{ overflow: hidden !important; height: 100vh !important; max-height: 100vh !important; min-height: 0 !important; }}
        .main {{ overflow: hidden !important; height: 100% !important; }}
        .main .block-container {{ max-width: 520px; padding: 0.25rem 1rem 0.5rem; overflow: hidden !important; height: 100vh !important; max-height: 100vh !important; }}
        /* 首页扭蛋机：全宽大页面，禁止套娃——只保留最后一个 iframe 且占满视口 */
        .main .block-container:has(iframe) {{
            max-width: 100% !important;
            width: 100% !important;
            display: grid !important;
            grid-template-rows: 100vh !important;
            grid-template-columns: 1fr !important;
            padding: 0 !important;
}}
        .main .block-container:has(iframe) > * {{
            grid-row: 1 !important; grid-column: 1 !important;
            min-height: 0 !important; height: 100vh !important; max-height: 100vh !important;
            overflow: hidden !important;
            align-self: start !important; justify-self: stretch !important;
}}
        .main .block-container:has(iframe) > *:not(:last-child) {{
            display: none !important; visibility: hidden !important; pointer-events: none !important;
            height: 0 !important; min-height: 0 !important; max-height: 0 !important; overflow: hidden !important;
            margin: 0 !important; padding: 0 !important;
}}
        .main .block-container:has(iframe) > *:last-child {{ z-index: 1 !important; }}
        .main .block-container iframe {{ height: 100% !important; min-height: 100vh !important; max-height: 100vh !important; display: block !important; }}
        .main .block-container > div {{ overflow: hidden !important; max-height: 100% !important; }}
        section[data-testid="stAppViewContainer"] > div {{ overflow: hidden !important; height: 100% !important; }}
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
        /* 首页「点击抽取」：橘红 3D 风格，与 iframe 内一致 */
        .wrap-red-btn.wrap-draw-btn [data-testid="stButton"] button {{
            background: linear-gradient(180deg, #ffb347 0%, #ff9f43 30%, #ee5a24 100%) !important;
            color: #fff !important; font-weight: 700 !important; font-size: 1.1rem !important;
            box-shadow: 0 6px 0 #c0392b, 0 8px 20px rgba(0,0,0,0.25) !important;
            border-radius: 999px !important; padding: 14px 36px !important;
        }}
        .wrap-red-btn.wrap-draw-btn [data-testid="stButton"] button:hover {{ filter: brightness(1.06); }}
        .wrap-red-btn.wrap-draw-btn [data-testid="stButton"] button:active {{
            transform: translateY(4px) scale(0.98); box-shadow: 0 2px 0 #c0392b !important;
        }}
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
        /* 隐藏 Streamlit 顶栏/工具栏，消除黑色链条 */
        header[data-testid="stHeader"] {{ display: none !important; }}
        .stDeployButton {{ display: none !important; }}
        footer {{ visibility: hidden !important; }}
        #MainMenu {{ visibility: hidden !important; }}
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
    """扭蛋动画：小球快速滚动 → 减速 → 一颗滚出出口，约 1.8 秒后跳转结果页。"""
    ANIM_DURATION_MS = 1800
    tid_js = tid.replace("\\", "\\\\").replace('"', '\\"')
    st.markdown(
        f"""
        <div id="gashapon-wrap" style="
            position: fixed; left: 0; right: 0; top: 0; bottom: 0;
            background: linear-gradient(180deg, #4ECDC4 0%, #a8e8e4 50%, #ffffff 100%);
            z-index: 9999; display: flex; flex-direction: column; align-items: center; justify-content: center;
        ">
            <p style="color:#000;font-size:16px;margin-bottom:16px;font-weight:600;">扭蛋中，请稍候...</p>
            <div class="gashapon-machine" style="
                width: 200px; height: 280px; background: linear-gradient(145deg, #4ECDC4 0%, #7dd9d3 45%, #fff 100%);
                border-radius: 16px; position: relative; box-shadow: inset 0 0 0 4px rgba(255,255,255,0.5), 0 10px 28px rgba(78,205,196,0.4);
            ">
                <div class="ball-tank" style="position: absolute; left: 50%; top: 14px; transform: translateX(-50%); width: 164px; height: 170px; background: linear-gradient(180deg, #e8faf9 0%, #fff 100%); border-radius: 10px; overflow: hidden;">
                    <div class="ball b1"></div><div class="ball b2"></div><div class="ball b3"></div><div class="ball b4"></div><div class="ball b5"></div><div class="ball b6"></div>
                    <div id="exit-ball" class="ball exit-ball"></div>
                </div>
                <div class="exit-chute" style="position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); width: 100px; height: 14px; background: #2ab5ab; border-radius: 6px;"></div>
            </div>
            <p style="margin-top:20px; font-size:14px; color:#333;">约 2 秒后自动跳转，或 <a href="?show_result=1&tid={tid_js}" style="color:#1565C0; font-weight:600;">点击此处查看结果</a></p>
        </div>
        <style>
        .ball {{ position: absolute; width: 22px; height: 22px; border-radius: 50%; box-shadow: 0 2px 6px rgba(0,0,0,0.2); }}
        .b1 {{ left: 12px; top: 20px; background: linear-gradient(135deg, #FF6B6B, #ee5a5a); animation: shake 0.9s ease-in-out infinite; }}
        .b2 {{ left: 52px; top: 14px; background: linear-gradient(135deg, #4ECDC4, #3dbdb5); animation: shake 0.9s ease-in-out 0.1s infinite; }}
        .b3 {{ left: 92px; top: 24px; background: linear-gradient(135deg, #FFE66D, #e6d85c); animation: shake 0.9s ease-in-out 0.2s infinite; }}
        .b4 {{ left: 28px; top: 58px; background: linear-gradient(135deg, #95E1D3, #7dd1c3); animation: shake 0.9s ease-in-out 0.15s infinite; }}
        .b5 {{ left: 72px; top: 52px; background: linear-gradient(135deg, #DDA0DD, #cc8fcc); animation: shake 0.9s ease-in-out 0.25s infinite; }}
        .b6 {{ left: 118px; top: 60px; background: linear-gradient(135deg, #87CEEB, #76bddb); animation: shake 0.9s ease-in-out 0.05s infinite; }}
        .exit-ball {{ left: 71px; top: 140px; background: linear-gradient(135deg, #4ECDC4, #FFE66D); opacity: 0; animation: ballExit 1.8s ease-out forwards; }}
        @keyframes shake {{
            0%, 100% {{ transform: translate(0,0) rotate(0deg); }}
            25% {{ transform: translate(3px,-2px) rotate(5deg); }}
            50% {{ transform: translate(-2px,2px) rotate(-5deg); }}
            75% {{ transform: translate(-3px,-1px) rotate(3deg); }}
        }}
        @keyframes ballExit {{
            0% {{ opacity: 0; transform: translate(0,0) scale(0.8); }}
            35% {{ opacity: 0; }}
            40% {{ opacity: 1; transform: translate(0,-10px) scale(1); }}
            55% {{ transform: translate(0,30px) scale(1); }}
            70% {{ transform: translate(0,65px) scale(1); }}
            85% {{ transform: translate(0,95px) scale(1); }}
            100% {{ opacity: 1; transform: translate(0,118px) scale(1); }}
        }}
        </style>
        <script>
        (function(){{
            var tid = "{tid_js}";
            setTimeout(function(){{
                var w = document.getElementById('gashapon-wrap');
                if (w) w.style.opacity = '0';
                setTimeout(function(){{
                    var u = new URL(window.location.href);
                    u.searchParams.set('show_result', '1');
                    u.searchParams.set('tid', tid);
                    (window.top || window).location.href = u.toString();
                }}, 400);
            }}, {ANIM_DURATION_MS});
        }})();
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
            result_new = draw(st.session_state.mode)
            tid_new = str(uuid.uuid4())
            _DRAW_CACHE[tid_new] = result_new
            _save_draw_result(tid_new, result_new)
            st.session_state["draw_tid"] = tid_new
            st.session_state["draw_tid_for_cleanup"] = tid_new
            st.session_state.show_modal = False
            st.session_state.result = None
            st.session_state.last_result_tid = None
            st.session_state["gashapon_animate"] = (result_new, tid_new)
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


def _gashapon_html(mode: str, result: Optional[dict] = None, tid: str = "", machine_src: str = "", ball_src: str = "", ball_left_src: str = "", ball_right_src: str = "", food_icon_src: str = "", hide_draw_btn: bool = False, mode_label: str = "减脂", bg_diet: str = "", color_diet: str = "", bg_indulge: str = "", color_indulge: str = "") -> str:
    """生成整页 HTML（标题+模式+扭蛋机）放入单 iframe，避免重复渲染。"""
    if not machine_src:
        _svg = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="260"><rect width="200" height="260" rx="16" fill="#4ECDC4"/><text x="100" y="140" text-anchor="middle" fill="#fff" font-size="18">扭蛋机</text></svg>'
        machine_src = "data:image/svg+xml," + html_module.escape(_svg)
    if not ball_src:
        ball_src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='48' height='48'%3E%3Ccircle cx='24' cy='24' r='22' fill='%234ECDC4'/%3E%3C/svg%3E"
    if not ball_left_src:
        ball_left_src = ball_src
    if not ball_right_src:
        ball_right_src = ball_src
    result_json = ""
    if result:
        payload = {k: v for k, v in result.items() if isinstance(v, (str, int, float, list)) or v is None}
        if food_icon_src:
            payload["foodIconUrl"] = food_icon_src
        result_json = json.dumps(payload, ensure_ascii=False)
    confirm_url = html_module.escape(f"?record=1&tid={tid}", quote=True) if tid else "#"
    redraw_url = "?draw=1"
    result_icon_style = "" if food_icon_src else "display:none;"

    template_path = ASSETS / "gashapon_template.html"
    if not template_path.exists():
        return "<p>扭蛋机模板未找到</p>"
    html = template_path.read_text(encoding="utf-8")
    html = html.replace("__MACHINE_SRC__", html_module.escape(machine_src))
    html = html.replace("__BALL_SRC__", html_module.escape(ball_src))
    html = html.replace("__BALL_LEFT_SRC__", html_module.escape(ball_left_src))
    html = html.replace("__BALL_RIGHT_SRC__", html_module.escape(ball_right_src))
    html = html.replace("__FOOD_ICON_SRC__", html_module.escape(food_icon_src) if food_icon_src else "")
    html = html.replace("__RESULT_ICON_STYLE__", result_icon_style)
    html = html.replace("__REDRAW_URL__", redraw_url)
    html = html.replace("__CONFIRM_URL__", confirm_url)
    html = html.replace("__RESULT_JSON__", json.dumps(result_json) if result_json else '""')
    html = html.replace("__HIDE_DRAW_BTN__", "display:none" if hide_draw_btn else "")
    html = html.replace("__MODE__", html_module.escape(mode_label))
    mode_icon = "🥗" if mode_label == "减脂" else "🍟"
    mode_color = "#2d8a7a" if mode_label == "减脂" else "#d35400"
    html = html.replace("__MODE_ICON__", mode_icon)
    html = html.replace("__MODE_COLOR__", mode_color)
    html = html.replace("__BG_DIET__", html_module.escape(bg_diet))
    html = html.replace("__COLOR_DIET__", html_module.escape(color_diet))
    html = html.replace("__BG_INDULGE__", html_module.escape(bg_indulge))
    html = html.replace("__COLOR_INDULGE__", html_module.escape(color_indulge))
    return html


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

    # iframe 内底部「记录今日外卖金额」点击 → ?action=record
    if q.get("action") == "record":
        default_cal = 250 if st.session_state.mode == "减脂" else 850
        st.session_state.record_prefill = {
            "菜品名": "外卖消费",
            "热量": default_cal,
            "模式": st.session_state.mode,
            "品类": "其他",
        }
        st.session_state.show_record_form = True
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.rerun()
    # iframe 内底部「查看本周总结」点击 → ?action=recap
    if q.get("action") == "recap":
        st.session_state.show_recap = True
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.rerun()

    # 点击「点击抽取」链接会打开 ?draw=1：执行一次抽卡并展示新扭蛋动画（不跳转）
    if q.get("draw") == "1":
        result = draw(st.session_state.mode)
        tid = str(uuid.uuid4())
        _DRAW_CACHE[tid] = result
        _save_draw_result(tid, result)
        st.session_state["draw_tid"] = tid
        st.session_state["draw_tid_for_cleanup"] = tid
        st.session_state["gashapon_animate"] = (result, tid)
        try:
            st.query_params.pop("draw")
        except Exception:
            pass
        st.rerun()

    # 弹窗内「就吃这个」跳转 ?record=1&tid=xxx：直接进入记录表单，不再出现第二组结果页按钮
    if q.get("record") == "1":
        tid = (q.get("tid") or "").strip()
        if tid:
            cached = _DRAW_CACHE.pop(tid, None) or _load_draw_result(tid)
            if cached:
                st.session_state.show_record_form = True
                st.session_state.record_prefill = {
                    "菜品名": cached.get("菜品名") or "外卖消费",
                    "热量": int(cached.get("热量") or 0),
                    "模式": cached.get("模式") or st.session_state.mode,
                    "品类": cached.get("品类") or "其他",
                }
                try:
                    st.query_params.clear()
                except Exception:
                    pass
                st.rerun()

    # 动画结束后跳转 ?show_result=1&tid=xxx（兼容旧链接，仍进入结果弹窗）
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
        st.markdown("<p style='text-align:center;font-size:1.2rem;font-weight:700;color:#000;'>记录成功</p>", unsafe_allow_html=True)
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

    # 首页：只渲染一个 iframe，整页（标题+模式+扭蛋+底部记录/查看）全在 iframe 内，绝不追加任何 Streamlit 按钮
    mode = st.session_state.mode
    bg_diet = TEAL if mode == "减脂" else BUTTON_GRAY
    color_diet = "#fff" if mode == "减脂" else GRAY_TEXT
    bg_indulge = RED if mode == "放纵" else BUTTON_GRAY
    color_indulge = "#fff" if mode == "放纵" else GRAY_TEXT
    animate_data = st.session_state.pop("gashapon_animate", None)
    machine_src = _asset_data_uri("machine.png") or _asset_data_uri("gashapon.png")
    ball_src = _asset_data_uri("ball.png")
    ball_left_src = _asset_data_uri("ball-left.png") or ball_src
    ball_right_src = _asset_data_uri("ball-right.png") or ball_src
    if animate_data:
        result, tid = animate_data
        food_icon_src = ""
        if result:
            for name in (result.get("品类") or "", result.get("菜品名") or ""):
                if name:
                    food_icon_src = _asset_data_uri(f"food-icons/{name}.png")
                    if food_icon_src:
                        break
            if not food_icon_src:
                food_icon_src = _asset_data_uri("food-icons/sprite.png") or ""
        gashapon_html = _gashapon_html("animate", result=result, tid=tid, machine_src=machine_src or "", ball_src=ball_src or "", ball_left_src=ball_left_src or "", ball_right_src=ball_right_src or "", food_icon_src=food_icon_src, hide_draw_btn=False, mode_label=mode, bg_diet=bg_diet, color_diet=color_diet, bg_indulge=bg_indulge, color_indulge=color_indulge)
    else:
        gashapon_html = _gashapon_html("idle", machine_src=machine_src or "", ball_src=ball_src or "", ball_left_src=ball_left_src or "", ball_right_src=ball_right_src or "", hide_draw_btn=False, mode_label=mode, bg_diet=bg_diet, color_diet=color_diet, bg_indulge=bg_indulge, color_indulge=color_indulge)

    st.components.v1.html(gashapon_html, height=800, scrolling=False)


if __name__ == "__main__":
    main()
