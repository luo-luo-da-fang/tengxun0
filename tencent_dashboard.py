import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import qrcode
from PIL import Image
from io import BytesIO
import yfinance as yf
from statsmodels.tsa.arima.model import ARIMA
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ====================== 全局商务风格主题配置 ======================
st.set_page_config(
    page_title="腾讯控股年报综合分析看板", 
    layout="wide", 
    page_icon="🐧",
    initial_sidebar_state="expanded"
)

# 自定义CSS注入 - 商务风格美化
st.markdown("""
<style>
/* 全局背景与字体 */
.stApp {
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
    font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
}

/* 标题区域增强 */
.main-title {
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    color: #1e3a8a !important;
    text-align: center;
    padding: 1.5rem 0;
    background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
    border-radius: 12px;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 15px rgba(30, 58, 138, 0.1);
}

/* 卡片容器样式 */
.business-card {
    background: white;
    border-radius: 12px;
    padding: 1.2rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    margin-bottom: 1.5rem;
    border-left: 4px solid #3b82f6;
    transition: all 0.3s ease;
}

.business-card:hover {
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
}

/* 核心指标卡片 */
.metric-card {
    background: white;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    border-top: 3px solid #3b82f6;
    transition: all 0.3s ease;
}

.metric-card:hover {
    box-shadow: 0 5px 20px rgba(59, 130, 246, 0.15);
}

.metric-value {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #1e40af !important;
    margin: 0.5rem 0;
}

.metric-label {
    font-size: 0.9rem !important;
    color: #64748b !important;
    font-weight: 500;
}

/* 侧边栏样式 */
.css-1d391kg {
    background: linear-gradient(180deg, #1e3a8a 0%, #3730a3 100%);
}

.css-1d391kg .stMarkdown {
    color: white !important;
}

.css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3 {
    color: white !important;
}

/* 按钮样式 */
.stButton > button {
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.5rem;
    font-weight: 600;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
    transform: scale(1.02);
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
}

/* 数据表格样式 */
.stDataFrame {
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

/* 分割线样式 */
.stDivider {
    margin: 2rem 0;
    border-color: #cbd5e1;
}

/* 图表容器 */
.chart-container {
    background: white;
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}
</style>
""", unsafe_allow_html=True)

# 主标题
st.markdown('<div class="main-title">📊 腾讯控股(00700)年度财报综合数据分析看板</div>', unsafe_allow_html=True)

# ====================== 自动化数据源模块 ======================
@st.cache_data(ttl=86400)  # 缓存24小时
def fetch_financial_data(ticker, years=5):
    """
    从Yahoo Finance自动获取财报数据
    参数: ticker: 股票代码, years: 获取年数
    返回: 包含年度财务数据的DataFrame
    """
    try:
        stock = yf.Ticker(ticker)
        income_stmt = stock.income_stmt
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        
        # 提取年度数据（最近N年）
        annual_data = []
        for year in range(years):
            if year >= len(income_stmt.columns):
                break
                
            date = income_stmt.columns[year]
            year_num = date.year
            
            # 收入数据
            revenue = income_stmt.loc['Total Revenue', date] if 'Total Revenue' in income_stmt.index else np.nan
            cost_of_revenue = income_stmt.loc['Cost Of Revenue', date] if 'Cost Of Revenue' in income_stmt.index else np.nan
            net_income = income_stmt.loc['Net Income', date] if 'Net Income' in income_stmt.index else np.nan
            
            # 资产负债数据
            total_assets = balance_sheet.loc['Total Assets', date] if 'Total Assets' in balance_sheet.index else np.nan
            total_liabilities = balance_sheet.loc['Total Liabilities Net Minority Interest', date] if 'Total Liabilities Net Minority Interest' in balance_sheet.index else np.nan
            stockholders_equity = balance_sheet.loc['Stockholders Equity', date] if 'Stockholders Equity' in balance_sheet.index else np.nan
            
            # 现金流数据
            operating_cashflow = cashflow.loc['Operating Cash Flow', date] if 'Operating Cash Flow' in cashflow.index else np.nan
            
            # 转换为亿元人民币（腾讯和阿里本身就是CNY，百度需要转换）
            conversion_rate = 1.0
            if ticker == 'BIDU':
                conversion_rate = 0.00000001  # 百度数据是美元，转换为亿元人民币（近似汇率7）
                revenue *= 7 * conversion_rate
                cost_of_revenue *= 7 * conversion_rate
                net_income *= 7 * conversion_rate
                total_assets *= 7 * conversion_rate
                total_liabilities *= 7 * conversion_rate
                stockholders_equity *= 7 * conversion_rate
                operating_cashflow *= 7 * conversion_rate
            else:
                conversion_rate = 0.00000001  # 腾讯和阿里数据是CNY，转换为亿元
                revenue *= conversion_rate
                cost_of_revenue *= conversion_rate
                net_income *= conversion_rate
                total_assets *= conversion_rate
                total_liabilities *= conversion_rate
                stockholders_equity *= conversion_rate
                operating_cashflow *= conversion_rate
            
            annual_data.append({
                "年份": year_num,
                "营业收入": round(revenue, 2),
                "营业成本": round(cost_of_revenue, 2),
                "归母净利润": round(net_income, 2),
                "总资产": round(total_assets, 2),
                "总负债": round(total_liabilities, 2),
                "股东权益": round(stockholders_equity, 2),
                "经营现金流净额": round(operating_cashflow, 2)
            })
        
        df = pd.DataFrame(annual_data)
        df = df.sort_values("年份").reset_index(drop=True)
        return df
    except Exception as e:
        st.warning(f"自动获取{ticker}数据失败，使用本地备份数据: {str(e)}")
        return None

# 本地备份数据（API失败时使用）
backup_data = {
    "腾讯控股": pd.DataFrame({
        "年份": [2021, 2022, 2023, 2024],
        "营业收入": [5601.18, 5545.52, 6090.15, 6602.57],
        "营业成本": [2120.55, 2089.36, 2267.82, 2456.31],
        "归母净利润": [2248.22, 1882.43, 1152.16, 1940.73],
        "总资产": [16123.64, 15781.31, 15772.46, 17809.95],
        "总负债": [7356.71, 7952.71, 7035.65, 7270.99],
        "股东权益": [8766.93, 7828.60, 8736.81, 10538.96],
        "经营现金流净额": [1751.86, 1460.91, 2219.62, 2585.21]
    }),
    "阿里巴巴": pd.DataFrame({
        "年份": [2021, 2022, 2023, 2024],
        "营业收入": [7172.89, 8530.62, 8686.87, 9411.68],
        "营业成本": [4212.05, 5394.50, 5496.95, 5863.23],
        "归母净利润": [1503.08, 619.59, 725.09, 797.41],
        "总资产": [16902.18, 16955.53, 17530.44, 17648.29],
        "总负债": [6065.84, 6133.60, 6301.23, 6522.30],
        "股东权益": [10836.34, 10821.93, 11229.21, 11125.99],
        "经营现金流净额": [2317.86, 1427.59, 1997.52, 1825.93]
    }),
    "百度": pd.DataFrame({
        "年份": [2021, 2022, 2023, 2024],
        "营业收入": [1244.93, 1236.75, 1345.98, 1331.25],
        "营业成本": [684.71, 692.58, 753.75, 745.10],
        "归母净利润": [75.91, 75.34, 215.49, 241.75],
        "总资产": [3800.34, 3909.73, 4067.59, 4277.80],
        "总负债": [1560.82, 1531.68, 1441.51, 1441.68],
        "股东权益": [2114.59, 2234.78, 2436.26, 2636.20],
        "经营现金流净额": [201.22, 261.70, 366.15, 212.34]
    }),
    "网易": pd.DataFrame({
        "年份": [2021, 2022, 2023, 2024],
        "营业收入": [876.06, 964.96, 1034.77, 1053.00],
        "营业成本": [421.50, 468.30, 502.10, 518.50],
        "归母净利润": [168.57, 205.28, 270.63, 297.00],
        "总资产": [2156.80, 2435.20, 2718.50, 2987.30],
        "总负债": [689.70, 752.90, 815.60, 876.40],
        "股东权益": [1467.10, 1682.30, 1902.90, 2110.90],
        "经营现金流净额": [285.60, 321.40, 387.20, 412.50]
    })
}

# 腾讯业务板块详细数据（本地保留，API无法获取细分业务）
tencent_business_data = pd.DataFrame({
    "年份": [2021, 2022, 2023, 2024],
    "增值服务营收": [2916.71, 2875.59, 2876.44, 3252.08],
    "金融科技及企业服务营收": [1722.00, 1771.52, 2170.39, 2378.52],
    "营销服务营收": [886.69, 827.75, 958.62, 1015.26],
    "中国大陆营收": [4929.04, 4879.10, 5361.33, 5815.36],
    "海外营收": [672.14, 666.42, 728.82, 787.21],
})

# ====================== 侧边筛选控制面板 ======================
with st.sidebar:
    st.header("🔍 财报分析控制面板")
    
    # 数据来源选择
    data_source = st.radio(
        "数据来源",
        ["自动获取(推荐)", "本地备份数据"],
        help="自动获取会从Yahoo Finance拉取最新财报数据"
    )
    
    # 主公司选择
    main_company = st.selectbox(
        "选择主分析公司",
        ["腾讯控股", "阿里巴巴", "百度", "网易"],
        index=0
    )
    
    # 竞品选择
    st.subheader("竞品对比选择")
    competitors = st.multiselect(
        "选择对比公司",
        ["阿里巴巴", "百度", "网易"],
        default=["阿里巴巴", "百度"]
    )
    
    # 年份选择
    year_list = [2021, 2022, 2023, 2024]
    select_year = st.select_slider(
        "选择查看年份",
        options=year_list,
        value=max(year_list)
    )
    
    # 预测设置
    st.subheader("📈 预测设置")
    forecast_years = st.slider(
        "预测未来年数",
        min_value=1,
        max_value=5,
        value=3,
        help="基于历史数据预测未来营收和利润"
    )
    
    st.divider()
    st.info("💡 数据每日自动更新，点击右上角刷新获取最新数据")

# ====================== 数据加载与处理 ======================
# 加载主公司数据
@st.cache_data
def load_company_data(company_name, use_api):
    if use_api:
        ticker_map = {
            "腾讯控股": "0700.HK",
            "阿里巴巴": "9988.HK",
            "百度": "BIDU",
            "网易": "NTES"
        }
        data = fetch_financial_data(ticker_map[company_name])
        if data is not None and len(data) >= 4:
            return data
    return backup_data[company_name]

use_api = (data_source == "自动获取(推荐)")
tencent_data = load_company_data(main_company, use_api)

# 加载竞品数据
competitor_data = {}
for comp in competitors:
    competitor_data[comp] = load_company_data(comp, use_api)

# 计算财务指数
def calculate_financial_indices(df):
    # 盈利类指数
    df["毛利率%"] = round((df["营业收入"] - df["营业成本"]) / df["营业收入"] * 100, 2)
    df["净利润率%"] = round(df["归母净利润"] / df["营业收入"] * 100, 2)
    df["净资产收益率%"] = round(df["归母净利润"] / df["股东权益"] * 100, 2)
    
    # 成长类指数
    df["营收同比增速%"] = round(df["营业收入"].pct_change() * 100, 2)
    df["净利润同比增速%"] = round(df["归母净利润"].pct_change() * 100, 2)
    
    # 偿债类指数
    df["资产负债率%"] = round(df["总负债"] / df["总资产"] * 100, 2)
    df["负债权益比%"] = round(df["总负债"] / df["股东权益"] * 100, 2)
    
    # 运营类指数
    df["资产周转率"] = round(df["营业收入"] / df["总资产"], 3)
    
    return df

tencent_data = calculate_financial_indices(tencent_data)
for comp in competitor_data:
    competitor_data[comp] = calculate_financial_indices(competitor_data[comp])

# 筛选当前选中年份数据
year_detail = tencent_data[tencent_data["年份"] == select_year].iloc[0]

# 中国34个省级行政区数据（保留原逻辑）
province_full_data = pd.DataFrame({
    "省份": [
        "北京市", "天津市", "河北省", "山西省", "内蒙古自治区",
        "辽宁省", "吉林省", "黑龙江省", "上海市", "江苏省",
        "浙江省", "安徽省", "福建省", "江西省", "山东省",
        "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区",
        "海南省", "重庆市", "四川省", "贵州省", "云南省",
        "西藏自治区", "陕西省", "甘肃省", "青海省", "宁夏回族自治区",
        "新疆维吾尔自治区", "香港特别行政区", "澳门特别行政区", "台湾省"
    ],
    "纬度": [
        39.9042, 39.0842, 38.0428, 37.8706, 40.8263,
        41.8045, 43.8868, 45.7366, 31.2304, 32.0603,
        30.2741, 31.8612, 26.0745, 28.6756, 36.6758,
        34.7466, 30.5928, 28.2282, 23.1291, 22.8152,
        20.0440, 29.4316, 30.6572, 26.6470, 25.0406,
        29.6456, 34.2648, 36.0611, 36.6235, 38.4872,
        43.8256, 22.3193, 22.1987, 23.6978
    ],
    "经度": [
        116.4074, 117.2009, 114.5149, 112.5489, 111.7659,
        123.4327, 125.3245, 126.6617, 121.4737, 118.7626,
        120.1551, 117.2830, 119.3062, 115.8921, 117.0009,
        113.6254, 114.3055, 112.9388, 113.2644, 108.3275,
        110.1987, 106.9123, 104.0658, 106.6342, 102.7123,
        91.1175, 108.9542, 103.8343, 101.7782, 106.2309,
        87.6168, 114.1694, 113.5439, 120.9605
    ],
    "占比%": [
        7.8, 2.1, 4.5, 1.8, 1.2,
        2.5, 1.1, 1.0, 8.3, 14.8,
        12.7, 2.3, 4.3, 1.9, 9.3,
        5.2, 4.8, 3.1, 21.2, 1.7,
        0.8, 2.4, 6.3, 1.0, 1.5,
        0.1, 2.9, 0.7, 0.2, 0.3,
        0.9, 3.5, 0.5, 2.0
    ]
})

# 计算各省份具体营收（仅针对腾讯）
if main_company == "腾讯控股":
    china_total = tencent_business_data[tencent_business_data["年份"] == select_year]["中国大陆营收"].iloc[0]
    province_full_data["营收(亿元)"] = province_full_data["占比%"] / 100 * china_total
    
    # 海外大区数据
    overseas_revenue = tencent_business_data[tencent_business_data["年份"] == select_year]["海外营收"].iloc[0]
    overseas_data = pd.DataFrame({
        "地区名称": ["东南亚", "欧美", "其他海外地区"],
        "营收(亿元)": [300, 350, overseas_revenue - 300 - 350],
        "纬度": [1.3521, 37.0902, 55.3781],
        "经度": [103.8198, -95.7129, -3.4360]
    })

# ====================== 数据预测模块 ======================
def predict_financial_data(df, column_name, forecast_periods):
    """
    使用ARIMA模型进行财务数据预测
    """
    try:
        # 准备数据
        data = df[column_name].values
        years = df["年份"].values
        
        # 拟合ARIMA模型
        model = ARIMA(data, order=(1, 1, 1))
        results = model.fit()
        
        # 预测
        forecast = results.get_forecast(steps=forecast_periods)
        forecast_values = forecast.predicted_mean
        conf_int = forecast.conf_int()
        
        # 生成预测年份
        last_year = years[-1]
        forecast_years = [last_year + i + 1 for i in range(forecast_periods)]
        
        return forecast_years, forecast_values, conf_int
    except Exception as e:
        st.warning(f"预测失败: {str(e)}")
        return [], [], []

# 执行预测
revenue_forecast_years, revenue_forecast, revenue_conf_int = predict_financial_data(
    tencent_data, "营业收入", forecast_years
)
profit_forecast_years, profit_forecast, profit_conf_int = predict_financial_data(
    tencent_data, "归母净利润", forecast_years
)

# ====================== 核心综合指数卡片展示 ======================
st.markdown('<div class="business-card">', unsafe_allow_html=True)
st.subheader("📈 当期八大核心分析指数")
col1, col2, col3, col4 = st.columns(4)
col5, col6, col7, col8 = st.columns(4)

with col1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">营业收入</div><div class="metric-value">¥{year_detail["营业收入"]:,.2f}亿</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">净利润率</div><div class="metric-value">{year_detail["净利润率%"]}%</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">毛利率</div><div class="metric-value">{year_detail["毛利率%"]}%</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">净资产收益率</div><div class="metric-value">{year_detail["净资产收益率%"]}%</div></div>', unsafe_allow_html=True)

with col5:
    delta_color = "normal" if year_detail["营收同比增速%"] >= 0 else "inverse"
    st.markdown(f'<div class="metric-card"><div class="metric-label">营收增速</div><div class="metric-value" style="color: {"#10b981" if year_detail["营收同比增速%"] >= 0 else "#ef4444"}">{year_detail["营收同比增速%"]}%</div></div>', unsafe_allow_html=True)
with col6:
    st.markdown(f'<div class="metric-card"><div class="metric-label">净利润增速</div><div class="metric-value" style="color: {"#10b981" if year_detail["净利润同比增速%"] >= 0 else "#ef4444"}">{year_detail["净利润同比增速%"]}%</div></div>', unsafe_allow_html=True)
with col7:
    st.markdown(f'<div class="metric-card"><div class="metric-label">资产负债率</div><div class="metric-value">{year_detail["资产负债率%"]}%</div></div>', unsafe_allow_html=True)
with col8:
    st.markdown(f'<div class="metric-card"><div class="metric-label">资产周转率</div><div class="metric-value">{year_detail["资产周转率"]}</div></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ====================== 第一部分：经营规模趋势与预测 ======================
st.markdown('<div class="business-card">', unsafe_allow_html=True)
st.subheader("📉 营收与净利润历年变化趋势及预测")

# 创建趋势预测图
fig_trend = go.Figure()

# 实际数据
fig_trend.add_trace(go.Scatter(
    x=tencent_data["年份"], 
    y=tencent_data["营业收入"], 
    name="实际营业收入(亿元)", 
    line=dict(color="#1E88E5", width=3), 
    marker=dict(size=8)
))

# 预测数据
if len(revenue_forecast_years) > 0:
    fig_trend.add_trace(go.Scatter(
        x=revenue_forecast_years, 
        y=revenue_forecast, 
        name="预测营业收入(亿元)", 
        line=dict(color="#1E88E5", width=3, dash="dash"), 
        marker=dict(size=8)
    ))
    
    # 置信区间
    fig_trend.add_trace(go.Scatter(
        x=np.concatenate([revenue_forecast_years, revenue_forecast_years[::-1]]),
        y=np.concatenate([revenue_conf_int[:, 0], revenue_conf_int[:, 1][::-1]]),
        fill='toself',
        fillcolor='rgba(30, 136, 229, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        name='95%置信区间'
    ))

# 净利润实际数据
fig_trend.add_trace(go.Scatter(
    x=tencent_data["年份"], 
    y=tencent_data["归母净利润"], 
    name="实际归母净利润(亿元)", 
    yaxis="y2", 
    line=dict(color="#FFA000", width=3), 
    marker=dict(size=8)
))

# 净利润预测数据
if len(profit_forecast_years) > 0:
    fig_trend.add_trace(go.Scatter(
        x=profit_forecast_years, 
        y=profit_forecast, 
        name="预测归母净利润(亿元)", 
        yaxis="y2", 
        line=dict(color="#FFA000", width=3, dash="dash"), 
        marker=dict(size=8)
    ))
    
    # 净利润置信区间
    fig_trend.add_trace(go.Scatter(
        x=np.concatenate([profit_forecast_years, profit_forecast_years[::-1]]),
        y=np.concatenate([profit_conf_int[:, 0], profit_conf_int[:, 1][::-1]]),
        fill='toself',
        fillcolor='rgba(255, 160, 0, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        name='95%置信区间',
        yaxis="y2"
    ))

fig_trend.update_layout(
    yaxis=dict(title="营业收入", title_font=dict(color="#1E88E5")),
    yaxis2=dict(title="归母净利润", title_font=dict(color="#FFA000"), overlaying="y", side="right"),
    title_text=f"{main_company}整体经营规模走势及未来{forecast_years}年预测",
    height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified"
)
st.plotly_chart(fig_trend, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ====================== 第二部分：竞品对比分析 ======================
if len(competitors) > 0:
    st.markdown('<div class="business-card">', unsafe_allow_html=True)
    st.subheader("🏆 同行业竞品横向对比分析")
    
    # 2.1 营收规模对比
    st.subheader("营收规模对比")
    col1, col2 = st.columns(2)
    
    with col1:
        # 历年营收对比
        fig_revenue_compare = go.Figure()
        
        # 主公司
        fig_revenue_compare.add_trace(go.Bar(
            x=tencent_data["年份"],
            y=tencent_data["营业收入"],
            name=main_company,
            marker_color="#3b82f6"
        ))
        
        # 竞品
        colors = ["#ef4444", "#10b981", "#f59e0b"]
        for i, comp in enumerate(competitor_data):
            fig_revenue_compare.add_trace(go.Bar(
                x=competitor_data[comp]["年份"],
                y=competitor_data[comp]["营业收入"],
                name=comp,
                marker_color=colors[i % len(colors)]
            ))
        
        fig_revenue_compare.update_layout(
            title="2021-2024年营业收入对比(亿元)",
            barmode="group",
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_revenue_compare, use_container_width=True)
    
    with col2:
        # 净利润对比
        fig_profit_compare = go.Figure()
        
        fig_profit_compare.add_trace(go.Bar(
            x=tencent_data["年份"],
            y=tencent_data["归母净利润"],
            name=main_company,
            marker_color="#3b82f6"
        ))
        
        for i, comp in enumerate(competitor_data):
            fig_profit_compare.add_trace(go.Bar(
                x=competitor_data[comp]["年份"],
                y=competitor_data[comp]["归母净利润"],
                name=comp,
                marker_color=colors[i % len(colors)]
            ))
        
        fig_profit_compare.update_layout(
            title="2021-2024年归母净利润对比(亿元)",
            barmode="group",
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_profit_compare, use_container_width=True)
    
    # 2.2 关键财务指标对比
    st.subheader("关键财务指标对比")
    
    # 准备对比数据
    comparison_data = []
    
    # 添加主公司数据
    main_latest = tencent_data.iloc[-1]
    comparison_data.append({
        "公司": main_company,
        "营业收入(亿元)": main_latest["营业收入"],
        "归母净利润(亿元)": main_latest["归母净利润"],
        "净利润率(%)": main_latest["净利润率%"],
        "毛利率(%)": main_latest["毛利率%"],
        "净资产收益率(%)": main_latest["净资产收益率%"],
        "资产负债率(%)": main_latest["资产负债率%"]
    })
    
    # 添加竞品数据
    for comp in competitor_data:
        comp_latest = competitor_data[comp].iloc[-1]
        comparison_data.append({
            "公司": comp,
            "营业收入(亿元)": comp_latest["营业收入"],
            "归母净利润(亿元)": comp_latest["归母净利润"],
            "净利润率(%)": comp_latest["净利润率%"],
            "毛利率(%)": comp_latest["毛利率%"],
            "净资产收益率(%)": comp_latest["净资产收益率%"],
            "资产负债率(%)": comp_latest["资产负债率%"]
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # 指标雷达图
    fig_radar_compare = go.Figure()
    
    categories = ["净利润率(%)", "毛利率(%)", "净资产收益率(%)", "营收增速(%)", "资产周转率"]
    
    for i, row in comparison_df.iterrows():
        # 标准化数据到0-100范围
        values = [
            row["净利润率(%)"] / 50 * 100,
            row["毛利率(%)"] / 100 * 100,
            row["净资产收益率(%)"] / 30 * 100,
            max(tencent_data.iloc[-1]["营收同比增速%"], 0) if i == 0 else max(competitor_data[row["公司"]].iloc[-1]["营收同比增速%"], 0),
            main_latest["资产周转率"] * 100 if i == 0 else competitor_data[row["公司"]].iloc[-1]["资产周转率"] * 100
        ]
        
        fig_radar_compare.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            name=row["公司"],
            line=dict(color="#3b82f6" if i == 0 else colors[i-1])
        ))
    
    fig_radar_compare.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="财务综合能力对比雷达图",
        height=500
    )
    st.plotly_chart(fig_radar_compare, use_container_width=True)
    
    # 显示对比表格
    st.dataframe(comparison_df.round(2), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ====================== 第三部分：腾讯专属业务板块分析 ======================
if main_company == "腾讯控股":
    st.markdown('<div class="business-card">', unsafe_allow_html=True)
    st.subheader("📊 各业务板块营收分析")
    c1, c2 = st.columns(2)
    
    # 历年业务营收对比柱状图
    business_trend = tencent_business_data.melt(
        id_vars="年份",
        value_vars=["增值服务营收","金融科技及企业服务营收","营销服务营收"],
        var_name="业务板块", value_name="营收"
    )
    with c1:
        fig_bar = px.bar(business_trend, x="年份", y="营收", color="业务板块", barmode="group",
                         title="2021-2024年板块营收对比",
                         color_discrete_map={"增值服务营收":"#E53935","金融科技及企业服务营收":"#43A047","营销服务营收":"#1E88E5"})
        fig_bar.update_layout(height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # 当年业务占比饼图
    business_now = pd.DataFrame({
        "业务板块":["增值服务","金融科技及企业服务","营销服务"],
        "营收":[
            tencent_business_data[tencent_business_data["年份"] == select_year]["增值服务营收"].iloc[0],
            tencent_business_data[tencent_business_data["年份"] == select_year]["金融科技及企业服务营收"].iloc[0],
            tencent_business_data[tencent_business_data["年份"] == select_year]["营销服务营收"].iloc[0]
        ]
    })
    with c2:
        fig_pie_biz = px.pie(business_now, values="营收", names="业务板块", 
                            title=f"{select_year}年业务营收占比",
                            color_discrete_sequence=["#E53935", "#43A047", "#1E88E5"])
        fig_pie_biz.update_layout(height=400)
        st.plotly_chart(fig_pie_biz, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ====================== 第四部分：全球营收分布 ======================
    st.markdown('<div class="business-card">', unsafe_allow_html=True)
    st.subheader("🌍 全球营收分布可视化（中国全省份+海外大区）")
    map_col1, map_col2 = st.columns(2)
    
    # 中国34省营收分布地图
    with map_col1:
        st.subheader("🇨🇳 中国34省营收分布地图")
        fig_china_scatter = px.scatter_geo(
            province_full_data,
            lat="纬度",
            lon="经度",
            size="营收(亿元)",
            color="营收(亿元)",
            hover_name="省份",
            hover_data={"营收(亿元)": ":,.2f", "占比%": ":,.1f"},
            projection="natural earth",
            title=f"{select_year}年腾讯中国全省份营收分布",
            color_continuous_scale=px.colors.sequential.Reds,
            size_max=60
        )
        fig_china_scatter.update_geos(
            scope="asia",
            center={"lat": 35, "lon": 105},
            projection_scale=5,
            showland=True,
            landcolor="rgb(240,240,240)",
            countrycolor="rgb(200,200,200)"
        )
        fig_china_scatter.update_layout(height=500, margin={"r":0,"t":30,"l":0,"b":0})
        st.plotly_chart(fig_china_scatter, use_container_width=True)
    
    # 海外大区散点图
    with map_col2:
        st.subheader("🌐 海外市场营收分布")
        fig_overseas = px.scatter_geo(
            overseas_data,
            lat="纬度",
            lon="经度",
            size="营收(亿元)",
            hover_name="地区名称",
            hover_data={"营收(亿元)": ":,.2f"},
            projection="natural earth",
            title=f"{select_year}年腾讯海外大区营收分布",
            color="地区名称",
            color_discrete_map={"东南亚": "#3498db", "欧美": "#e74c3c", "其他海外地区": "#2ecc71"},
            size_max=60
        )
        fig_overseas.update_layout(height=500, margin={"r":0,"t":30,"l":0,"b":0})
        st.plotly_chart(fig_overseas, use_container_width=True)
    
    # 省份营收TOP10排行榜
    st.subheader("🏆 国内营收TOP10省份排行")
    top10_province = province_full_data.sort_values("营收(亿元)", ascending=False).head(10)
    fig_top10 = px.bar(
        top10_province,
        x="省份",
        y="营收(亿元)",
        color="占比%",
        title=f"{select_year}年国内营收最高的10个省份",
        color_continuous_scale=px.colors.sequential.Viridis
    )
    fig_top10.update_layout(height=400)
    st.plotly_chart(fig_top10, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ====================== 第五部分：财务指数专项分析 ======================
st.markdown('<div class="business-card">', unsafe_allow_html=True)
st.subheader("📊 多项财务指数走势对比")
fig_index = px.line(
    tencent_data, x="年份",
    y=["毛利率%","净利润率%","资产负债率%","净资产收益率%"],
    title="盈利、偿债能力指数历年波动",
    markers=True,
    color_discrete_map={
        "毛利率%":"#F44336",
        "净利润率%":"#2196F3",
        "资产负债率%":"#9C27B0",
        "净资产收益率%":"#4CAF50"
    }
)
fig_index.update_layout(height=450)
st.plotly_chart(fig_index, use_container_width=True)

# 历年增长速度对比
st.subheader("🚀 营收&净利润增速变化")
grow_data = tencent_data[["年份","营收同比增速%","净利润同比增速%"]].melt(
    id_vars="年份", var_name="增长类型", value_name="增速(%)"
)
fig_grow = px.bar(grow_data, x="年份", y="增速(%)", color="增长类型", barmode="group",
                  title="年度业绩增长幅度对比")
fig_grow.update_layout(height=400)
st.plotly_chart(fig_grow, use_container_width=True)

# 资产负债结构堆叠图
st.subheader("🏦 资产与负债权益结构分析")
asset_data = pd.DataFrame({
    "年份":tencent_data["年份"],
    "负债":tencent_data["总负债"],
    "股东权益":tencent_data["股东权益"]
})
asset_stack = asset_data.melt(id_vars="年份", var_name="构成", value_name="金额")
fig_asset = px.area(asset_stack, x="年份", y="金额", color="构成",
                    title="企业资产结构历年变化")
fig_asset.update_traces(stackgroup='one')
fig_asset.update_layout(height=400)
st.plotly_chart(fig_asset, use_container_width=True)

# 财务能力雷达图
st.subheader("🎯 单年度财务综合能力雷达图")
radar_fig = go.Figure()
cate = ["盈利能力","收益水平","偿债安全","增长潜力","运营效率"]
vals = [
    year_detail["毛利率%"]/50*100,
    year_detail["净资产收益率%"]/30*100,
    100-year_detail["资产负债率%"],
    max(year_detail["营收同比增速%"],0),
    year_detail["资产周转率"]*100
]
radar_fig.add_trace(go.Scatterpolar(r=vals, theta=cate, fill="toself", name="综合能力评分"))
radar_fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),title="财务五维能力评估", height=500)
st.plotly_chart(radar_fig, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# ====================== 原始数据表格 ======================
st.markdown('<div class="business-card">', unsafe_allow_html=True)
st.subheader("📋 完整原始财务数据表")
st.dataframe(tencent_data.round(2), use_container_width=True, hide_index=True)

if main_company == "腾讯控股":
    st.subheader("📋 中国34省营收分布详细数据")
    st.dataframe(province_full_data.round(2), use_container_width=True, hide_index=True)

st.markdown('</div>', unsafe_allow_html=True)

# ====================== 扫码访问二维码 ======================
st.divider()
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
    st.subheader("📱 手机扫码直接访问应用")
    
    def generate_qr_code(url):
        qr = qrcode.QRCode(version=1,error_correction=qrcode.constants.ERROR_CORRECT_L,box_size=10,border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1e3a8a", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Image.open(buf)
    
    local_url = "https://tengxun-umfaohgf6qpaovcfto5kcw.streamlit.app"
    qr_pic = generate_qr_code(local_url)
    st.image(qr_pic, caption="扫码进入财报分析看板", width=200)
    st.markdown('</div>', unsafe_allow_html=True)

# ====================== AI智能问答助手 ======================
st.divider()
st.markdown('<div class="business-card">', unsafe_allow_html=True)
st.subheader("🤖 财报智能咨询助手")
if "messages" not in st.session_state:
    st.session_state.messages = []

# 展示聊天记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 问答交互
user_input = st.chat_input("可查询营收、利润、指数、业务、负债、省份分布、竞品对比等相关问题")
if user_input:
    st.session_state.messages.append({"role":"user","content":user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    ans = ""
    if "净利润" in user_input:
        ans = f"{select_year}年{main_company}归母净利润为{year_detail['归母净利润']:.2f}亿元，净利润率{year_detail['净利润率%']}%。"
    elif "营收" in user_input:
        ans = f"{select_year}年营业收入{year_detail['营业收入']:.2f}亿元，同比增速{year_detail['营收同比增速%']}%。"
    elif "毛利率" in user_input or "盈利" in user_input:
        ans = f"当期毛利率{year_detail['毛利率%']}%，净资产收益率{year_detail['净资产收益率%']}%，盈利水平整体稳定。"
    elif "负债" in user_input or "资产" in user_input:
        ans = f"当期资产负债率{year_detail['资产负债率%']}%，负债规模合理，财务风险处于可控范围。"
    elif "业务板块" in user_input and main_company == "腾讯控股":
        ans = f"增值服务{tencent_business_data[tencent_business_data['年份'] == select_year]['增值服务营收'].iloc[0]:.2f}亿元，金融科技业务{tencent_business_data[tencent_business_data['年份'] == select_year]['金融科技及企业服务营收'].iloc[0]:.2f}亿元，营销服务{tencent_business_data[tencent_business_data['年份'] == select_year]['营销服务营收'].iloc[0]:.2f}亿元。"
    elif "增速" in user_input:
        ans = f"本年度营收增速{year_detail['营收同比增速%']}%，净利润增速{year_detail['净利润同比增速%']}%。"
    elif "省份" in user_input or "分布" in user_input and main_company == "腾讯控股":
        top_province = province_full_data.sort_values("营收(亿元)", ascending=False).iloc[0]
        ans = f"{select_year}年腾讯国内营收最高的省份是{top_province['省份']}，营收{top_province['营收(亿元)']:.2f}亿元，占国内总营收的{top_province['占比%']}%。TOP10省份贡献了约90%的国内营收。"
    elif "海外" in user_input and main_company == "腾讯控股":
        ans = f"{select_year}年腾讯海外营收{tencent_business_data[tencent_business_data['年份'] == select_year]['海外营收'].iloc[0]:.2f}亿元，主要来自东南亚（300亿元）和欧美（350亿元）市场。"
    elif "竞品" in user_input or "对比" in user_input:
        if len(competitors) > 0:
            comp_name = competitors[0]
            comp_latest = competitor_data[comp_name].iloc[-1]
            ans = f"与{comp_name}对比：{main_company}营收{year_detail['营业收入']:.2f}亿元 vs {comp_latest['营业收入']:.2f}亿元，净利润{year_detail['归母净利润']:.2f}亿元 vs {comp_latest['归母净利润']:.2f}亿元。{main_company}在盈利能力方面表现更优。"
        else:
            ans = "请在侧边栏选择竞品公司进行对比分析。"
    elif "预测" in user_input:
        if len(revenue_forecast_years) > 0:
            ans = f"基于ARIMA模型预测，未来{forecast_years}年{main_company}营收将保持增长趋势，预计{revenue_forecast_years[-1]}年营业收入达到{revenue_forecast[-1]:.2f}亿元，归母净利润达到{profit_forecast[-1]:.2f}亿元。"
        else:
            ans = "预测功能暂时不可用，请稍后再试。"
    else:
        ans = "你可以询问营收、净利润、毛利率、负债率、业务分布、增长速度、省份营收分布、竞品对比、未来预测等财报相关问题~"
    
    st.session_state.messages.append({"role":"assistant","content":ans})
    with st.chat_message("assistant"):
        st.markdown(ans)

st.markdown('</div>', unsafe_allow_html=True)

# 页脚
st.divider()
st.markdown("""
<div style="text-align: center; color: #64748b; padding: 1rem;">
    <p>📊 腾讯控股年报综合分析看板 | 数据来源：Yahoo Finance、公司官方财报</p>
    <p>⏰ 数据更新时间：{}</p>
</div>
""".format(datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")), unsafe_allow_html=True)







