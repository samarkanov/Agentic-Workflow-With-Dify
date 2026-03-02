import streamlit as st
import time
from components.dashboard import render_dashboard
from components.alerts import render_alerts
from utils import api_client

st.set_page_config(
    page_title="Predictive Maintenance Dashboard",
    page_icon="🏭",
    layout="wide"
)

def main():
    st.title("🏭 Predictive Maintenance Dashboard")

    if not api_client.is_backend_available():
        st.warning("Warning: Backend API is unreachable. Please ensure the backend server is running.", icon="⚠️")
        st.stop()

    assets = api_client.get_assets()
    if not assets:
        st.error("Could not fetch assets from the backend. Cannot proceed.")
        st.stop()
    
    asset_options = {asset['name']: asset['id'] for asset in assets}
    
    # Use query params to maintain selected asset across full-page reloads
    if 'asset' not in st.query_params:
        st.query_params['asset'] = list(asset_options.keys())[0]
    
    # Find the index of the asset from query params for the selectbox default
    try:
        default_index = list(asset_options.keys()).index(st.query_params.asset)
    except ValueError:
        default_index = 0
        st.query_params.asset = list(asset_options.keys())[0]

    selected_asset_name = st.sidebar.selectbox(
        "Select Asset to Monitor",
        options=asset_options.keys(),
        index=default_index,
        key="asset_selector"
    )
    st.query_params.asset = selected_asset_name
    selected_asset_id = asset_options[selected_asset_name]

    # Main update logic using st.fragment for 1s refresh
    @st.fragment(run_every=1)
    def live_view(asset_id):
        render_dashboard(asset_id)
        st.divider()
        render_alerts()

    live_view(selected_asset_id)

if __name__ == "__main__":
    main()
