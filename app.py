import streamlit as st
import sqlite3
import pandas as pd
import random
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Rockstar Jobs Database",
    page_icon="🎮",
    layout="wide"
)

# Database connection
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('rockstar_jobs.db')
    return conn

@st.cache_data
def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM jobs ORDER BY creation_date DESC", conn)
    conn.close()
    return df

def get_random_jobs(df, n=12, job_type_filters=None, verification_filters=None, year_filters=None):
    """Get n random jobs with optional filters"""
    filtered_df = df.copy()
    
    if job_type_filters and len(job_type_filters) > 0:
        filtered_df = filtered_df[filtered_df['job_type_edited'].isin(job_type_filters)]
    
    if verification_filters and len(verification_filters) > 0:
        filtered_df = filtered_df[filtered_df['verification_type'].isin(verification_filters)]
    
    if year_filters and len(year_filters) > 0:
        filtered_df = filtered_df[filtered_df['creation_year'].isin(year_filters)]
    
    if len(filtered_df) == 0:
        return pd.DataFrame()
    
    # Get random sample
    sample_size = min(n, len(filtered_df))
    return filtered_df.sample(n=sample_size)

# Main app
st.title("🎮 Rockstar Social Club Jobs Database")
st.markdown("Browse and search through scraped Rockstar job data")

# Load data
df = load_data()

if df.empty:
    st.warning("No jobs found in the database. Please run the scraper first.")
    st.stop()

# Extract year from creation_date for filtering
df['creation_year'] = pd.to_datetime(df['creation_date'], errors='coerce').dt.year.astype('Int64').astype(str)

# Sidebar for filters
st.sidebar.header("Filters")

# Get unique values for filters
job_types = sorted([x for x in df['job_type_edited'].unique() if pd.notna(x)])
verification_types = sorted([x for x in df['verification_type'].unique() if pd.notna(x)])
years = sorted([str(x) for x in df['creation_year'].unique() if pd.notna(x)], reverse=True)

# Multi-select filters
selected_job_types = st.sidebar.multiselect("Job Types", job_types)
selected_verification_types = st.sidebar.multiselect("Verification Types", verification_types)
selected_years = st.sidebar.multiselect("Years", years)

# Search bar
search_term = st.sidebar.text_input("Search by job name or creator")

# Main content area
tab1, tab2 = st.tabs(["Browse All Jobs", "Random Job Discovery"])

with tab1:
    st.subheader("Browse Jobs")
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_job_types:
        filtered_df = filtered_df[filtered_df['job_type_edited'].isin(selected_job_types)]
    
    if selected_verification_types:
        filtered_df = filtered_df[filtered_df['verification_type'].isin(selected_verification_types)]
    
    if selected_years:
        filtered_df = filtered_df[filtered_df['creation_year'].isin(selected_years)]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['job_name'].str.contains(search_term, case=False) |
            filtered_df['job_creator'].str.contains(search_term, case=False)
        ]
    
    # Display results
    st.info(f"Found {len(filtered_df)} jobs matching your filters")
    
    if not filtered_df.empty:
        # Pagination
        page_size = 30  # Increased for condensed view
        page = st.number_input("Page", min_value=1, max_value=(len(filtered_df) // page_size) + 1, value=1)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_df = filtered_df.iloc[start_idx:end_idx]
        
        # Display jobs in condensed format
        for _, row in page_df.iterrows():
            with st.container():
                # Create columns for layout
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    # Responsive image sizing
                    if pd.notna(row['job_image']) and row['job_image']:
                        # Use columns to control image size on different screens
                        img_col1, img_col2, img_col3 = st.columns([1, 6, 1])
                        with img_col2:
                            st.image(row['job_image'], width=300, use_column_width=True)
                
                with col2:
                    # Job name and creator on same line
                    job_name = row['job_name']
                    job_creator = row['job_creator']
                    st.markdown(f"### {job_name} by {job_creator}")
                    
                    # Job type and player count on same line
                    job_type = row['job_type_edited'] or row['job_type']
                    max_players = row['max_players']
                    
                    # Only show player count if it's not 30
                    if max_players and max_players != "30":
                        st.markdown(f"**{job_type}** | **{max_players} players**")
                    else:
                        st.markdown(f"**{job_type}**")
                    
                    # Verification type and creation date
                    verification = row['verification_type']
                    creation_date = row['creation_date']
                    st.markdown(f"**Verification:** {verification} | **Created:** {creation_date}")
                    
                    # Links
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"[🔗 View on Rockstar]({row['original_url']})")
                    with col_b:
                        if pd.notna(row['gta_lens_link']) and row['gta_lens_link']:
                            st.markdown(f"[🔗 View on GTALens]({row['gta_lens_link']})")
                    
                    # Full description in expander (no character limit)
                    if pd.notna(row['job_description']) and row['job_description']:
                        with st.expander("Description"):
                            st.write(row['job_description'])
                
                st.divider()
    else:
        st.warning("No jobs match your filters. Try adjusting your search criteria.")

with tab2:
    st.subheader("Random Job Discovery")
    
    # Create columns for filter controls
    filter_col1, filter_col2 = st.columns([1, 1])
    
    with filter_col1:
        discovery_job_types = st.multiselect("Filter by Job Types", job_types, key="discovery_job")
    
    with filter_col2:
        discovery_verification = st.multiselect("Filter by Verification", verification_types, key="discovery_ver")
    
    discovery_years = st.multiselect("Filter by Years", years, key="discovery_year")
    
    num_jobs = st.slider("Number of random jobs to show", min_value=1, max_value=30, value=12)
    
    if st.button("🎲 Get Random Jobs"):
        random_jobs = get_random_jobs(df, num_jobs, discovery_job_types, discovery_verification, discovery_years)
        
        if not random_jobs.empty:
            st.success(f"Found {len(random_jobs)} random jobs!")
            
            # Display in a grid
            cols = st.columns(3)
            for i, (_, row) in enumerate(random_jobs.iterrows()):
                with cols[i % 3]:
                    # Responsive image
                    if pd.notna(row['job_image']) and row['job_image']:
                        st.image(row['job_image'], width=200, use_column_width=True)
                    
                    # Job name and creator
                    st.markdown(f"**{row['job_name']}** by {row['job_creator']}")
                    
                    # Job type and player count
                    job_type = row['job_type_edited'] or row['job_type']
                    max_players = row['max_players']
                    
                    if max_players and max_players != "30":
                        st.markdown(f"Type: {job_type} | {max_players} players")
                    else:
                        st.markdown(f"Type: {job_type}")
                    
                    st.markdown(f"[View Job]({row['original_url']})")
                    st.divider()
        else:
            st.warning("No jobs found with the selected filters.")

# Footer
st.markdown("---")
st.markdown("*Data scraped from Rockstar Social Club*")