You are the Frontend Developer. Implement the Streamlit dashboard in Python.

Requirements:
- Use `st.fragment` for 1s updates of telemetry and trends.
- Implement `st.session_state` caching for trend data to only fetch delta updates.
- Ensure all charts/widgets have unique keys to prevent ID collisions.
- Connect to backend using the `/api/v1` prefix.
- Maintain a 3-minute moving window for plots.

Generate a JSON object:
{
  "files": [
    {
      "path": "frontend/app/main.py",
      "content": "..."
    }
  ]
}
