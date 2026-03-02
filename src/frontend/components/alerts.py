import streamlit as st
from utils import api_client
import pandas as pd

def render_alerts():
    """
    Renders the alert management table.
    """
    st.subheader("🚨 Active Alerts")
    
    alerts = api_client.get_alerts()
    active_alerts = [a for a in alerts if a.get('status') == 'Active']

    if not active_alerts:
        st.success("No active alerts. All systems nominal.")
        return

    # Prepare data for the editor
    df = pd.DataFrame(active_alerts)
    df['Acknowledge'] = False 

    # Reorder and filter columns for display
    display_cols = ['id', 'asset_id', 'timestamp', 'severity', 'message', 'status', 'Acknowledge']
    df = df[display_cols]

    edited_df = st.data_editor(
        df,
        column_config={
            "id": st.column_config.TextColumn("Alert ID", width="small"),
            "asset_id": st.column_config.TextColumn("Asset ID", width="small"),
            "timestamp": st.column_config.DatetimeColumn("Timestamp", format="YYYY-MM-DD HH:mm:ss"),
            "severity": st.column_config.TextColumn("Severity", width="small"),
            "message": st.column_config.TextColumn("Message", width="large"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "Acknowledge": st.column_config.CheckboxColumn("Ack?", default=False)
        },
        disabled=["id", "asset_id", "timestamp", "severity", "message", "status"],
        hide_index=True,
        use_container_width=True,
        key=f"alert_editor_data"
    )

    # Find which rows were acknowledged
    # Use st.session_state to track acknowledgments to avoid redundant API calls if possible
    # but for simplicity we just check the edited_df
    acknowledged_ids = edited_df[edited_df["Acknowledge"] == True]["id"].tolist()
    
    if acknowledged_ids:
        for alert_id in acknowledged_ids:
            success = api_client.acknowledge_alert(alert_id)
            if success:
                st.toast(f"Acknowledged alert {alert_id}", icon="✅")
            else:
                st.toast(f"Failed to acknowledge alert {alert_id}", icon="❌")
        # Trigger a rerun of the fragment to refresh the alert list
        st.rerun()
