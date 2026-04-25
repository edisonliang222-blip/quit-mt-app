# type: ignore
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
import json

# ==================== 配置 ====================
DATA_FILE = "milk_tea_record.csv"
SETTINGS_FILE = "settings.json"

st.set_page_config(
    page_title="🍵 戒奶器",
    page_icon="🍵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 常见奶茶品牌
BRANDS = ["喜茶", "奈雪的茶", "茶百道", "蜜雪冰城", "古茗", "霸王茶姬", "书亦烧仙草", "阿嬷手作"]

# ==================== 数据加载与保存 ====================
def load_data():
    if os.path.exists(DATA_FILE):
        data = pd.read_csv(DATA_FILE, parse_dates=['date']) # type: ignore
        data['date'] = pd.to_datetime(data['date']).dt.date
        
        # 兼容旧数据：如果没有 brand 列，添加空值
        if 'brand' not in data.columns:
            data['brand'] = ''
        return data
    else:
        # 初始化示例数据（最近7天）
        today = date.today() # noqa
        sample_data = []
        brands_sample = ["喜茶", "奈雪的茶", "", "茶百道", "", "蜜雪冰城", ""]
        for idx in range(7, 0, -1):
            d = today - timedelta(days=i)
            drank = 1 if i in [2, 5] else 0
            cups = 1 if drank else 0
            brand = brands_sample[7-i] if drank else ""
            sample_data.append({
                'date': d,
                'drank': drank,
                'cups': cups,
                'brand': brand,
                'note': '偶尔解馋' if drank else ''
            })
        data = pd.DataFrame(sample_data)
        save_data(data)
        return data

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        settings = {
            'price_per_cup': 18,
            'calories_per_cup': 350,
            'goal_days': 30,
            'daily_goal_cups': 0
        }
        save_settings(settings)
        return settings

def save_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

# ==================== 核心逻辑 ====================
def calculate_streak(df):
    if df.empty:
        return 0, 0
    df = df.sort_values('date', ascending=False)
    today = date.today()
    today_record = df[df['date'] == today]
    start_date = today if not today_record.empty else today - timedelta(days=1)
    
    current_streak = 0
    max_streak = 0
    temp_streak = 0
    sorted_dates = sorted(df['date'].unique(), reverse=True)
    
    for i, d in enumerate(sorted_dates):
        record = df[df['date'] == d].iloc[0]
        if record['drank'] == 0:
            temp_streak += 1
            if d == start_date or (i > 0 and (sorted_dates[i-1] - d).days == 1):
                current_streak = temp_streak
        else:
            max_streak = max(max_streak, temp_streak)
            temp_streak = 0
            if d == start_date:
                current_streak = 0
    max_streak = max(max_streak, temp_streak, current_streak)
    return current_streak, max_streak

def get_stats(df, settings):
    if df.empty:
        return {'total_days': 0, 'clean_days': 0, 'total_cups': 0,
                'money_saved': 0, 'calories_avoided': 0,
                'current_streak': 0, 'max_streak': 0}
    
    total_days = len(df)
    clean_days = len(df[df['drank'] == 0])
    total_cups = df['cups'].sum()
    money_saved = clean_days * settings['price_per_cup']
    calories_avoided = clean_days * settings['calories_per_cup']
    current_streak, max_streak = calculate_streak(df)
    
    return {
        'total_days': total_days,
        'clean_days': clean_days,
        'total_cups': total_cups,
        'money_saved': money_saved,
        'calories_avoided': calories_avoided,
        'current_streak': current_streak,
        'max_streak': max_streak
    }

# ==================== 主界面 ====================
st.title("🍵 戒奶茶记录器")
st.markdown("**坚持每一天，健康每一天！**")

df = load_data()
settings = load_settings()

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    new_price = st.number_input("每杯奶茶平均价格（元）", 5, 50, settings['price_per_cup'], 1)
    new_calories = st.number_input("每杯奶茶热量（大卡）", 100, 600, settings['calories_per_cup'], 10)
    new_goal = st.number_input("戒除目标天数", 7, 365, settings['goal_days'], 1)
    
    if st.button("💾 保存设置"):
        settings.update({'price_per_cup': new_price, 'calories_per_cup': new_calories, 'goal_days': new_goal})
        save_settings(settings)
        st.success("设置已保存！")
        st.rerun()
    
    st.divider()
    st.metric("目标连续天数", f"{settings['goal_days']} 天")
    stats = get_stats(df, settings)
    progress = min(stats['current_streak'] / settings['goal_days'], 1.0)
    st.progress(progress, text=f"当前进度：{stats['current_streak']}/{settings['goal_days']} 天")

# ==================== 今日打卡区 ====================
st.subheader("📅 今日打卡")

col1, col2 = st.columns([2, 1])

with col1:
    today = date.today()
    today_record = df[df['date'] == today]
    
    if not today_record.empty:
        st.success(f"✅ 今天已经打卡了！品牌：{today_record.iloc[0]['brand'] or '无'}")
        if st.button("🔄 重新打卡"):
            df = df[df['date'] != today]
            save_data(df)
            st.rerun()
    else:
        st.info("今天还没打卡哦～")
        
        drank = st.radio("今天喝奶茶了吗？", 
                        options=["没有喝！💪", "喝了... 😭"], 
                        horizontal=True,
                        index=0)
        
        if "没有" in drank:
            note = st.text_input("今天感觉如何？（可选）", 
                                placeholder="例如：今天超有精神！")
            if st.button("✅ 确认打卡 - 坚持成功！", type="primary"):
                new_row = pd.DataFrame([{
                    'date': today,
                    'drank': 0,
                    'cups': 0,
                    'brand': '',
                    'note': note
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.balloons()
                st.success("🎉 太棒了！又坚持了一天！")
                st.rerun()
        else:
            # 新增品牌选择
            brand = st.selectbox("喝的是哪个品牌？", BRANDS, index=0)
            if brand == "其他":
                brand = st.text_input("请输入品牌名称", placeholder="例如：星巴克")
            
            cups = st.number_input("今天喝了几杯？", min_value=1, max_value=5, value=1)
            note = st.text_input("为什么喝了？（可选）", 
                                placeholder="例如：加班太累了...")
            
            if st.button("📝 记录下来（下次加油！）", type="secondary"):
                new_row = pd.DataFrame([{
                    'date': today,
                    'drank': 1,
                    'cups': cups,
                    'brand': brand,
                    'note': note
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.warning("没关系，明天继续加油！💪")
                st.rerun()

with col2:
    if not today_record.empty:
        if today_record.iloc[0]['drank'] == 0:
            st.metric("今日状态", "✅ 成功戒除", "💪")
        else:
            brand_text = today_record.iloc[0]['brand'] or "未知品牌"
            st.metric("今日状态", "😭 喝了", f"{brand_text} × {today_record.iloc[0]['cups']}")

# ==================== 统计面板 ====================
st.subheader("📈 我的戒除战绩")

stats = get_stats(df, settings)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🔥 当前连续天数", f"{stats['current_streak']} 天", 
              delta=f"最长 {stats['max_streak']} 天" if stats['max_streak'] > stats['current_streak'] else "新纪录！")

with col2:
    st.metric("💰 累计节省", f"¥{stats['money_saved']}")

with col3:
    st.metric("🔥 避免热量", f"{stats['calories_avoided']:,} kcal")

with col4:
    rate = f"{stats['clean_days']/stats['total_days']*100:.0f}%" if stats['total_days'] > 0 else "0%"
    st.metric("📅 总记录天数", f"{stats['total_days']} 天", f"成功率 {rate}")

# ==================== 新增：品牌统计 ====================
if not df.empty and len(df[df['drank'] == 1]) > 0:
    st.subheader("🏷️ 品牌诱惑分析")
    
    drank_df = df[df['drank'] == 1]
    brand_counts = drank_df['brand'].value_counts()
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("**最常喝的品牌 Top 5**")
        st.dataframe(brand_counts.head(5), use_container_width=True)
    
    with col_b:
        st.markdown("**品牌诱惑力排行**")
        if len(brand_counts) > 0:
            most_tempting = brand_counts.index[0]
            st.info(f"你最容易被 **{most_tempting}** 诱惑！\n\n下次看到它的时候要特别警惕哦～")

# ==================== 图表区 ====================
st.subheader("📊 趋势分析")

if not df.empty:
    chart_df = df.sort_values('date').copy()
    chart_df['date_str'] = chart_df['date'].astype(str)
    st.line_chart(chart_df.set_index('date_str')['cups'], color="#FF6B6B")
    
    st.markdown("**最近 7 天状态**")
    recent = chart_df.tail(7)
    cols = st.columns(7)
    for i, (_, row) in enumerate(recent.iterrows()):
        with cols[i]:
            if row['drank'] == 0:
                st.success(f"✅\n{row['date'].strftime('%m/%d')}")
            else:
                st.error(f"❌\n{row['date'].strftime('%m/%d')}")

# ==================== 历史记录 ====================
st.subheader("📋 历史打卡记录")

if not df.empty:
    display_df = df.sort_values('date', ascending=False).copy()
    display_df['日期'] = display_df['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    display_df['状态'] = display_df['drank'].map({0: '✅ 成功', 1: '❌ 失败'})
    display_df['品牌'] = display_df['brand'].fillna('')
    display_df['杯数'] = display_df['cups']
    display_df['备注'] = display_df['note']
    
    st.dataframe(
        display_df[['日期', '状态', '品牌', '杯数', '备注']],
        use_container_width=True,
        hide_index=True
    )
    
    with st.expander("🗑️ 删除某天记录"):
        dates_to_delete = st.multiselect(
            "选择要删除的日期",
            options=display_df['日期'].tolist()
        )
        if st.button("确认删除", type="secondary"):
            df = df[~df['date'].astype(str).isin(dates_to_delete)]
            save_data(df)
            st.success(f"已删除 {len(dates_to_delete)} 条记录")
            st.rerun()
else:
    st.info("暂无历史记录")

# ==================== 激励语录 ====================
st.divider()
st.subheader("💪 加油语录")

motivations = [
    "每一天的坚持，都是在给未来的自己投一票！",
    "奶茶好喝，但健康的身体更香！",
    "你已经比昨天更强了！",
    "小小一杯奶茶，换不来大大的健康。",
    "坚持不是为了别人，而是为了那个更好的自己。"
]
import random
st.info(random.choice(motivations))

st.caption("Made with ❤️ for 戒奶茶小勇士 | 数据仅保存在本地")

st.markdown("---")
st.markdown("""
**使用提示**：
- 每天打开这个页面打卡即可
- 新增了**品牌记录**功能，可以帮你分析自己最容易被哪个品牌诱惑
- 数据自动保存在同文件夹的 `milk_tea_record.csv`
""")
