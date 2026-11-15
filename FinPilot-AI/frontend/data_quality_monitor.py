"""FinPilot AI — Data Quality & Market Data Monitor Page.

Audits data provenance, timestamp freshness, missing records, provider connectivity,
and enforces data integrity safeguards prior to simulated trade execution.
"""
import streamlit as st
import pandas as pd
from backend.analytics.data_quality import audit_ticker_data_quality, get_all_providers_health


def render_data_quality_monitor():
    """Render data quality and provider health monitor."""
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 2rem;">📡</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: #f8fafc;">
                        Data Quality & Provenance Monitor
                    </h1>
                    <span style="color: #64748b; font-size: 0.85rem; font-weight: 600;">
                        Provider Health • Timestamp Freshness • OHLCV Completeness • Integrity Auditing
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Section 1: Provider Health Overview
    st.markdown("### 🌐 Global Financial API & Provider Connectivity")
    health = get_all_providers_health()

    prov_cols = st.columns(4)
    providers = health["providers"]

    for idx, (p_id, info) in enumerate(providers.items()):
        with prov_cols[idx % 4]:
            border_color = "#10b981" if "CONNECTED" in info["status"] or "ONLINE" in info["status"] else "#f59e0b"
            st.markdown(f"""
                <div style="background: #1e293b; border-radius: 12px; padding: 14px; border: 1px solid {border_color}; margin-bottom: 12px;">
                    <div style="font-size: 0.75rem; color: #94a3b8; font-weight: 700; text-transform: uppercase;">{info['name']}</div>
                    <div style="font-size: 1.05rem; font-weight: 800; color: #f8fafc; margin: 4px 0;">{info['status']}</div>
                    <div style="font-size: 0.72rem; color: #64748b; line-height: 1.4;">{info['role']}</div>
                </div>
            """, unsafe_allow_html=True)

    # Section 2: Asset-Specific Data Integrity Audit
    st.markdown("### 🔍 Asset Data Integrity & Gap Inspection")
    c_tick, c_btn = st.columns([3, 1])
    with c_tick:
        audit_ticker = st.text_input("Enter Ticker to Inspect", value="NVDA").strip().upper()
    with c_btn:
        st.write("")
        st.write("")
        run_audit = st.button("Run Audit 🔎", use_container_width=True)

    with st.spinner(f"Running integrity scan for {audit_ticker}..."):
        report = audit_ticker_data_quality(audit_ticker)

    # Audit KPI Metrics
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        st.metric("Quality Score", f"{report['quality_score']:.1f} / 100", help="Aggregate data reliability score")
    with q2:
        st.metric("Data Provenance", report["provenance"], help="Source pipeline providing market quotes")
    with q3:
        st.metric("Freshness Classification", report["freshness"], help="Real-time latency tier")
    with q4:
        st.metric("Historical Bars", f"{report.get('total_records', 0)} sessions", help="Valid OHLCV rows available")

    # Metrics Detail Table
    m = report.get("metrics", {})
    st.markdown("### 📋 Anomaly & Completeness Report")
    audit_table = pd.DataFrame([
        {"Data Integrity Factor": "OHLCV Completeness", "Result": f"{m.get('ohlcv_completeness_pct', 100):.2f}%", "Status": "Normal" if m.get("ohlcv_completeness_pct", 100) > 99 else "Warning"},
        {"Data Integrity Factor": "Missing Price Fields", "Result": f"{m.get('missing_ohlc_count', 0)} bars", "Status": "Clean" if m.get("missing_ohlc_count", 0) == 0 else "Action Required"},
        {"Data Integrity Factor": "Zero Volume Days", "Result": f"{m.get('zero_volume_count', 0)} bars", "Status": "Normal"},
        {"Data Integrity Factor": "Duplicate Timestamp Records", "Result": f"{m.get('duplicate_timestamps', 0)} records", "Status": "Clean" if m.get("duplicate_timestamps", 0) == 0 else "De-duplicated"},
        {"Data Integrity Factor": "Extreme Gaps (>15%)", "Result": f"{m.get('extreme_gaps_count', 0)} events", "Status": "Informational"},
        {"Data Integrity Factor": "Active Network Connectivity", "Result": "ONLINE" if report.get("is_online") else "OFFLINE", "Status": "Normal"},
    ])
    st.dataframe(audit_table, use_container_width=True, hide_index=True)

    # Active Warnings Banner
    warnings = report.get("warnings", [])
    if warnings:
        with st.expander("⚠️ Active Data Warnings & Integrity Notes", expanded=True):
            for w in warnings:
                st.markdown(f"- {w}")

    # Trading Execution Safeguard Disclosure
    st.markdown("""
        <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 12px; padding: 14px; margin-top: 14px;">
            <b style="color: #38bdf8;">🛡️ Execution Safeguard Policy:</b>
            <span style="color: #cbd5e1; font-size: 0.85rem;">
                FinPilot AI enforces strict transparency: orders simulated during market closure or on synthetic fallback data are explicitly marked with a <code>SIMULATED_DEMO</code> execution badge. Real quotes are never simulated or labeled as live without active network verification.
            </span>
        </div>
    """, unsafe_allow_html=True)
