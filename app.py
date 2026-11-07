# -*- coding: utf-8 -*-
"""
1号模块：app.py —— Streamlit 主界面与集成
职责：页面导航、表单输入、调用其他 9 个业务模块
规范：本文件不直接读写 JSON，所有数据操作经由 storage / models 等模块
启动：streamlit run app.py
"""
import streamlit as st
from datetime import date as _date

# ========== 页面基础配置 ==========
st.set_page_config(
    page_title="个人记账本",
    page_icon="💰",
    layout="centered",
)

# ========== 常量（从 models 导入，未就绪时使用规范默认值）==========
try:
    from models import EXPENSE_CATEGORIES, INCOME_CATEGORIES
except ImportError:
    EXPENSE_CATEGORIES = ["饮食", "交通", "购物", "娱乐", "住房", "医疗", "学习", "其他"]
    INCOME_CATEGORIES = ["工资", "兼职", "奖学金", "奖金", "其他"]


# ========== 业务模块懒加载（未就绪时友好提示）==========
def _safe_import():
    """统一加载业务模块，返回 (records, modules_dict)"""
    mods = {}
    try:
        from storage import load_records, save_records
        mods["load_records"] = load_records
        mods["save_records"] = save_records
    except ImportError:
        st.error("⚠️ storage.py 模块未就绪，数据读写不可用")
        return [], mods

    for name, mod_name, func in [
        ("add_record", "add_record", "add_record"),
        ("get_recent_records", "view_records", "get_recent_records"),
        ("filter_records", "filter_records", "filter_records"),
        ("calculate_summary", "statistics", "calculate_summary"),
        ("category_totals", "statistics", "category_totals"),
        ("render_charts", "charts", "render_charts"),
        ("export_csv", "export_data", "export_csv"),
    ]:
        try:
            m = __import__(mod_name)
            mods[name] = getattr(m, func)
        except ImportError:
            mods[name] = None
        except AttributeError:
            mods[name] = None

    try:
        records = mods["load_records"]()
    except Exception as e:
        st.error(f"数据加载失败：{e}")
        records = []
    return records, mods


# ========== 各页面 ==========
def page_add(records, mods):
    """新增记账页"""
    st.subheader("📝 新增一笔记录")
    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            rec_type = st.radio("类型", ["expense", "income"],
                                format_func=lambda x: "支出" if x == "expense" else "收入")
            amount = st.number_input("金额（元）", min_value=0.0, step=0.5, format="%.2f")
        with c2:
            d = st.date_input("日期", value=_date.today())
            cats = EXPENSE_CATEGORIES if rec_type == "expense" else INCOME_CATEGORIES
            category = st.selectbox("类别", cats)
        note = st.text_input("备注（可选）", max_chars=200)
        submitted = st.form_submit_button("✅ 保存记录", use_container_width=True)

    if submitted:
        if amount <= 0:
            st.error("金额必须大于 0")
            return
        if mods.get("add_record") is None:
            st.warning("add_record.py 模块未就绪，无法保存")
            return
        try:
            rec = mods["add_record"](
                date=d.isoformat(),
                record_type=rec_type,
                amount=round(float(amount), 2),
                category=category,
                note=note.strip(),
            )
            st.success(f"已保存：{rec_type} {amount:.2f} 元 / {category}")
            st.rerun()
        except ValueError as e:
            st.error(f"校验失败：{e}")
        except Exception as e:
            st.error(f"保存失败：{e}")


def page_recent(records, mods):
    """最近记录页"""
    st.subheader("📋 最近记录")
    if not records:
        st.info("暂无记录，去新增一笔吧")
        return
    if mods.get("get_recent_records"):
        try:
            recent = mods["get_recent_records"](records, limit=10)
        except Exception:
            recent = list(reversed(records[-10:]))
    else:
        recent = list(reversed(records[-10:]))
    st.dataframe(recent, use_container_width=True, hide_index=True)


def page_filter_stat(records, mods):
    """筛选 + 统计页"""
    st.subheader("🔍 筛选条件")
    c1, c2 = st.columns(2)
    with c1:
        f_type = st.selectbox("类型", ["全部", "expense", "income"],
                               format_func=lambda x: {"全部": "全部", "expense": "支出", "income": "收入"}[x])
        f_min = st.number_input("最小金额", min_value=0.0, step=10.0)
    with c2:
        f_cat = st.selectbox("类别", ["全部"] + EXPENSE_CATEGORIES + INCOME_CATEGORIES)
        f_max = st.number_input("最大金额", min_value=0.0, step=10.0, value=100000.0)

    f_type_arg = None if f_type == "全部" else f_type
    f_cat_arg = None if f_cat == "全部" else f_cat
    min_arg = None if f_min == 0 else float(f_min)
    max_arg = None if f_max == 100000 else float(f_max)

    try:
        if mods.get("filter_records"):
            selected = mods["filter_records"](
                records, category=f_cat_arg, record_type=f_type_arg,
                min_amount=min_arg, max_amount=max_arg,
            )
        else:
            selected = records
    except ValueError as e:
        st.error(f"筛选条件有误：{e}")
        selected = []

    st.subheader("📊 统计结果")
    if mods.get("calculate_summary"):
        try:
            summary = mods["calculate_summary"](selected)
        except Exception:
            summary = None
    else:
        summary = None

    if summary:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("总收入", f"¥{summary['income']:.2f}")
        m2.metric("总支出", f"¥{summary['expense']:.2f}")
        m3.metric("结余", f"¥{summary['balance']:.2f}")
        m4.metric("笔数", summary["count"])
    else:
        total_in = sum(r["amount"] for r in selected if r.get("type") == "income")
        total_out = sum(r["amount"] for r in selected if r.get("type") == "expense")
        c1, c2, c3 = st.columns(3)
        c1.metric("总收入", f"¥{total_in:.2f}")
        c2.metric("总支出", f"¥{total_out:.2f}")
        c3.metric("结余", f"¥{total_in - total_out:.2f}")

    st.write(f"匹配记录 {len(selected)} 条")
    if selected:
        st.dataframe(selected, use_container_width=True, hide_index=True)


def page_charts(records, mods):
    """图表页"""
    st.subheader("📈 数据图表")
    if mods.get("render_charts") is None:
        st.info("charts.py 模块开发中")
        return
    try:
        mods["render_charts"](records)
    except Exception as e:
        st.error(f"图表渲染失败：{e}")


def page_export(records, mods):
    """CSV 导出页"""
    st.subheader("💾 导出 CSV")
    if mods.get("export_csv") is None:
        st.info("export_data.py 模块开发中")
        return
    try:
        data = mods["export_csv"](records)
        st.download_button(
            "下载 CSV",
            data=data,
            file_name="records.csv",
            mime="text/csv",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"导出失败：{e}")


# ========== 主入口 ==========
def main():
    st.title("💰 个人记账本")
    records, mods = _safe_import()

    page = st.sidebar.radio(
        "导航",
        ["📝 新增记账", "📋 最近记录", "🔍 筛选统计", "📈 数据图表", "💾 导出 CSV"],
    )
    st.sidebar.caption(f"当前共 {len(records)} 条记录")

    if page.startswith("📝"):
        page_add(records, mods)
    elif page.startswith("📋"):
        page_recent(records, mods)
    elif page.startswith("🔍"):
        page_filter_stat(records, mods)
    elif page.startswith("📈"):
        page_charts(records, mods)
    elif page.startswith("💾"):
        page_export(records, mods)


if __name__ == "__main__":
    main()
