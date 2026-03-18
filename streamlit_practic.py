import streamlit as st
import os
from datetime import datetime, timedelta

st.title("News Summarizer")
st.write("Enter keywords and date range to fetch and summarize news articles.")
keywords = st.text_input("Keywords (comma-separated)", "climate change")
start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=1))
end_date = st.date_input("End Date", value=datetime.now())