import json
from pathlib import Path
import pandas as pd
import streamlit as st

APP_TITLE = "IP 角色库（中英对照）"
DATA_PATH = Path(__file__).parent / "data.json"

@st.cache_data(show_spinner=False)
def load_data(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"找不到 data.json：{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def to_rows(db: dict) -> list[dict]:
    rows = []
    for w in db.get("works", []):
        w_id = w.get("id")
        cn = w.get("title_cn", "")
        en = w.get("title_en", "")
        for c in w.get("characters", []):
            rows.append({
                "work_id": w_id,
                "作品": f"{cn} — {en}".strip(" —"),
                "角色中文": c.get("cn", ""),
                "角色英文": c.get("en", ""),
            })
    return rows

def normalize(s: str) -> str:
    return (s or "").strip().lower()

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

db = load_data(DATA_PATH)
rows = to_rows(db)
df = pd.DataFrame(rows)

# Sidebar controls
st.sidebar.header("筛选")
work_options = ["全部作品"] + sorted(df["作品"].unique().tolist())
work_selected = st.sidebar.selectbox("选择作品", work_options, index=0)

query = st.sidebar.text_input("关键词搜索（中/英都支持）", value="")
only_cn = st.sidebar.checkbox("只搜中文字段", value=False)
only_en = st.sidebar.checkbox("只搜英文字段", value=False)
if only_cn and only_en:
    st.sidebar.info("已同时勾选“只搜中文/只搜英文”，等同于全字段搜索。")

# Apply filters
view = df.copy()

if work_selected != "全部作品":
    view = view[view["作品"] == work_selected]

q = normalize(query)
if q:
    if only_cn and not only_en:
        mask = view["角色中文"].astype(str).str.lower().str.contains(q, na=False)
    elif only_en and not only_cn:
        mask = view["角色英文"].astype(str).str.lower().str.contains(q, na=False)
    else:
        mask = (
            view["角色中文"].astype(str).str.lower().str.contains(q, na=False)
            | view["角色英文"].astype(str).str.lower().str.contains(q, na=False)
            | view["作品"].astype(str).str.lower().str.contains(q, na=False)
        )
    view = view[mask]

# Main display
col1, col2, col3 = st.columns([2, 1, 1])
col1.metric("作品数", int(df["作品"].nunique()))
col2.metric("角色条目总数", int(len(df)))
col3.metric("当前结果数", int(len(view)))

st.dataframe(
    view[["作品", "角色中文", "角色英文"]],
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("导出")
csv_bytes = view[["作品", "角色中文", "角色英文"]].to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "下载当前结果（CSV）",
    data=csv_bytes,
    file_name="ip_characters_filtered.csv",
    mime="text/csv",
)

# Quick add instructions (read-only)
with st.expander("如何扩充 data.json（保持格式即可）", expanded=False):
    st.markdown(
        """
- 在项目目录下编辑 `data.json`。
- 每个作品是一个对象：`{id, title_cn, title_en, characters:[{cn,en}, ...]}`。
- 你可以新增角色或新增作品；保存后刷新页面即可生效。
        """.strip()
    )
