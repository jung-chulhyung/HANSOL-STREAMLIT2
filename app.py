import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(
    page_title="국내 주식 대시보드",
    page_icon="📈",
    layout="wide"
)

STOCKS = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "LG에너지솔루션": "373220.KS",
    "삼성바이오로직스": "207940.KS",
    "현대자동차": "005380.KS",
    "기아": "000270.KS",
    "NAVER": "035420.KS",
    "카카오": "035720.KS",
    "POSCO홀딩스": "005490.KS",
    "셀트리온": "068270.KS",
}

st.title("📈 국내 주식 대시보드")
st.markdown("KOSPI 주요 종목 10개의 실시간 데이터를 확인하세요.")

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    period_options = {"1개월": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y", "2년": "2y"}
    selected_period_label = st.selectbox("조회 기간", list(period_options.keys()), index=2)
    selected_period = period_options[selected_period_label]

    selected_stocks = st.multiselect(
        "종목 선택",
        list(STOCKS.keys()),
        default=list(STOCKS.keys())[:5]
    )

    interval_options = {"일봉": "1d", "주봉": "1wk", "월봉": "1mo"}
    selected_interval_label = st.selectbox("차트 단위", list(interval_options.keys()))
    selected_interval = interval_options[selected_interval_label]

    if st.button("🔄 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()

@st.cache_data(ttl=300)
def load_stock_data(ticker, period, interval):
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period, interval=interval)
    return hist

@st.cache_data(ttl=300)
def load_all_summary():
    rows = []
    for name, ticker in STOCKS.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d", interval="1d")
            if hist.empty:
                continue
            current = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2] if len(hist) >= 2 else current
            change = current - prev
            change_pct = (change / prev) * 100
            volume = hist["Volume"].iloc[-1]
            rows.append({
                "종목명": name,
                "현재가": f"{current:,.0f}",
                "전일대비": f"{change:+,.0f}",
                "등락률": f"{change_pct:+.2f}%",
                "거래량": f"{volume:,.0f}",
                "_change_pct": change_pct,
            })
        except Exception:
            continue
    return pd.DataFrame(rows)

# 현황 요약 테이블
st.subheader("📊 전체 종목 현황")

with st.spinner("데이터 불러오는 중..."):
    summary_df = load_all_summary()

if not summary_df.empty:
    def color_change(val):
        if "+" in str(val):
            return "color: red; font-weight: bold"
        elif "-" in str(val):
            return "color: blue; font-weight: bold"
        return ""

    display_df = summary_df.drop(columns=["_change_pct"])
    styled = display_df.style.map(color_change, subset=["전일대비", "등락률"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # 등락률 바 차트
    col1, col2 = st.columns(2)
    with col1:
        fig_bar = px.bar(
            summary_df,
            x="종목명",
            y="_change_pct",
            color="_change_pct",
            color_continuous_scale=["#1f77b4", "#aec7e8", "#ffbb78", "#ff7f0e", "#d62728"],
            labels={"_change_pct": "등락률 (%)"},
            title="종목별 등락률"
        )
        fig_bar.update_layout(coloraxis_showscale=False, xaxis_tickangle=-30)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        top5 = summary_df.nlargest(5, "_change_pct")
        bot5 = summary_df.nsmallest(5, "_change_pct")
        combined = pd.concat([top5, bot5]).drop_duplicates()
        colors = ["red" if v > 0 else "blue" for v in combined["_change_pct"]]
        fig_top = go.Figure(go.Bar(
            x=combined["종목명"],
            y=combined["_change_pct"],
            marker_color=colors,
            text=[f"{v:+.2f}%" for v in combined["_change_pct"]],
            textposition="outside"
        ))
        fig_top.update_layout(title="상승/하락 TOP 종목", xaxis_tickangle=-30)
        st.plotly_chart(fig_top, use_container_width=True)

st.divider()

# 개별 종목 차트
st.subheader("📉 개별 종목 차트")

if not selected_stocks:
    st.warning("사이드바에서 종목을 하나 이상 선택하세요.")
else:
    tabs = st.tabs(selected_stocks)
    for tab, name in zip(tabs, selected_stocks):
        ticker = STOCKS[name]
        with tab:
            with st.spinner(f"{name} 데이터 로딩 중..."):
                hist = load_stock_data(ticker, selected_period, selected_interval)

            if hist.empty:
                st.error("데이터를 불러올 수 없습니다.")
                continue

            # 지표 카드
            current_price = hist["Close"].iloc[-1]
            prev_price = hist["Close"].iloc[-2] if len(hist) >= 2 else current_price
            change = current_price - prev_price
            change_pct = (change / prev_price) * 100
            high_52w = hist["High"].max()
            low_52w = hist["Low"].min()
            avg_vol = hist["Volume"].mean()

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("현재가", f"{current_price:,.0f}원", f"{change:+,.0f} ({change_pct:+.2f}%)")
            m2.metric("기간 최고가", f"{high_52w:,.0f}원")
            m3.metric("기간 최저가", f"{low_52w:,.0f}원")
            m4.metric("평균 거래량", f"{avg_vol:,.0f}")
            m5.metric("조회 봉 수", f"{len(hist)}개")

            # 캔들스틱 차트
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=hist.index,
                open=hist["Open"],
                high=hist["High"],
                low=hist["Low"],
                close=hist["Close"],
                name="가격",
                increasing_line_color="red",
                decreasing_line_color="blue"
            ))

            # 이동평균선
            if len(hist) >= 20:
                hist["MA20"] = hist["Close"].rolling(20).mean()
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist["MA20"],
                    mode="lines", name="MA20",
                    line=dict(color="orange", width=1.5)
                ))
            if len(hist) >= 60:
                hist["MA60"] = hist["Close"].rolling(60).mean()
                fig.add_trace(go.Scatter(
                    x=hist.index, y=hist["MA60"],
                    mode="lines", name="MA60",
                    line=dict(color="purple", width=1.5)
                ))

            fig.update_layout(
                title=f"{name} ({ticker}) 주가 차트",
                xaxis_rangeslider_visible=False,
                height=450,
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig, use_container_width=True)

            # 거래량 차트
            vol_colors = ["red" if c >= o else "blue"
                          for c, o in zip(hist["Close"], hist["Open"])]
            fig_vol = go.Figure(go.Bar(
                x=hist.index, y=hist["Volume"],
                marker_color=vol_colors,
                name="거래량"
            ))
            fig_vol.update_layout(title="거래량", height=200, margin=dict(t=30, b=20))
            st.plotly_chart(fig_vol, use_container_width=True)

            # 원본 데이터
            with st.expander("📋 원본 데이터 보기"):
                show_df = hist[["Open", "High", "Low", "Close", "Volume"]].copy()
                show_df.columns = ["시가", "고가", "저가", "종가", "거래량"]
                show_df.index = show_df.index.strftime("%Y-%m-%d")
                st.dataframe(show_df.sort_index(ascending=False), use_container_width=True)

st.divider()
st.caption(f"데이터 출처: Yahoo Finance (yfinance) | 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
