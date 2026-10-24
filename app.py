import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime
import pytz

# --- NASTAVITEV STRANI ---
st.set_page_config(
    page_title="The Value Ledger 2.0 · Terminal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

