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
    df = pd.read_sql_query("SELECT * FROM jobs ORDER BY scraped_at DESC", conn)
    conn.close()
    return df

def get_random_jobs(df, n=12, job_type_filter=None, verification_filter=None):
    """Get n random jobs with optional filters"""
    filtered_df = df.copy()
    
    if job_type_filter and job_type_filter != "All":
        filtered_df = filtered_df[filtered_df['job_type_edited'] == job_type_filter]
    
    if verification_filter and verification_filter != "All":
        filtered_df = filtered_df[filtered_df['verification_type'] == verification_filter]
    
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

# Sidebar for filters
st.sidebar.header("Filters")

# Get unique values for filters
job_types = ['All'] + sorted([x for x in df['job_type_edited'].unique() if pd.notna(x)])
verification_types = ['All'] + sorted([x for x in df['verification_type'].unique() if pd.notna(x)])
years = ['All'] + sorted([str(x) for x in df['scraped_at'].str[:4].unique() if pd.notna(x)])

# Filter widgets
selected_job_type = st.sidebar.selectbox("Job Type", job_types)
selected_verification = st.sidebar.selectbox("Verification Type", verification_types)
selected_year = st.sidebar.selectbox("Year", years)

# Search bar
search_term = st.sidebar.text_input("Search by job name or creator")

# Main content area
tab1, tab2 = st.tabs(["Browse All Jobs", "Random Job Discovery"])

with tab1:
    st.subheader("Browse Jobs")
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_job_type != 'All':
        filtered_df = filtered_df[filtered_df['job_type_edited'] == selected_job_type]
    
    if selected_verification != 'All':
        filtered_df = filtered_df[filtered_df['verification_type'] == selected_verification]
    
    if selected_year != 'All':
        filtered_df = filtered_df[filtered_df['scraped_at'].str.startswith(selected_year)]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['job_name'].str.contains(search_term, case=False) |
            filtered_df['job_creator'].str.contains(search_term, case=False)
        ]
    
    # Display results
    st.info(f"Found {len(filtered_df)} jobs matching your filters")
    
    if not filtered_df.empty:
        # Pagination
        page_size = 20
        page = st.number_input("Page", min_value=1, max_value=(len(filtered_df) // page_size) + 1, value=1)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_df = filtered_df.iloc[start_idx:end_idx]
        
        # Display jobs in cards
        for _, row in page_df.iterrows():
            with st.container():
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if pd.notna(row['job_image']) and row['job_image']:
                        st.image(row['job_image'], width=200)
                
                with col2:
                    st.markdown(f"### {row['job_name']}")
                    st.markdown(f"**Creator:** {row['job_creator']}")
                    st.markdown(f"**Type:** {row['job_type_edited'] or row['job_type']}")
                    st.markdown(f"**Players:** {row['max_players']}")
                    st.markdown(f"**Verification:** {row['verification_type']}")
                    
                    # Links
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"[🔗 View on Rockstar]({row['original_url']})")
                    with col_b:
                        if pd.notna(row['gta_lens_link']) and row['gta_lens_link']:
                            st.markdown(f"[🔗 View on GTALens]({row['gta_lens_link']})")
                    
                    # Description (truncated)
                    if pd.notna(row['job_description']) and row['job_description']:
                        desc = row['job_description'][:200] + "..." if len(row['job_description']) > 200 else row['job_description']
                        with st.expander("Description"):
                            st.write(desc)
                
                st.divider()
    else:
        st.warning("No jobs match your filters. Try adjusting your search criteria.")

with tab2:
    st.subheader("Random Job Discovery")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        discovery_job_type = st.selectbox("Filter by Job Type", job_types, key="discovery_job")
    
    with col2:
        discovery_verification = st.selectbox("Filter by Verification", verification_types, key="discovery_ver")
    
    num_jobs = st.slider("Number of random jobs to show", min_value=1, max_value=30, value=12)
    
    if st.button("🎲 Get Random Jobs"):
        random_jobs = get_random_jobs(df, num_jobs, discovery_job_type, discovery_verification)
        
        if not random_jobs.empty:
            st.success(f"Found {len(random_jobs)} random jobs!")
            
            # Display in a grid
            cols = st.columns(3)
            for i, (_, row) in enumerate(random_jobs.iterrows()):
                with cols[i % 3]:
                    st.markdown(f"**{row['job_name']}**")
                    st.markdown(f"by {row['job_creator']}")
                    st.markdown(f"Type: {row['job_type_edited'] or row['job_type']}")
                    
                    if pd.notna(row['job_image']) and row['job_image']:
                        st.image(row['job_image'], width=150)
                    
                    st.markdown(f"[View Job]({row['original_url']})")
                    st.divider()
        else:
            st.warning("No jobs found with the selected filters.")

# Footer
st.markdown("---")
st.markdown("*Data scraped from Rockstar Social Club*")