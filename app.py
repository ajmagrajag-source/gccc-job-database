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

# Custom order for job types
JOB_TYPE_ORDER = [
    "GP and Street",
    "Off Road", 
    "Race",
    "Stunt Race",
    "Banger Race",
    "Deathmatch",
    "Last Team Standing",
    "King of the Hill",
    "Other",
    "Parkour"
]

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

# Initialize session state for filters
if 'selected_job_types' not in st.session_state:
    st.session_state.selected_job_types = []
if 'selected_verification_types' not in st.session_state:
    st.session_state.selected_verification_types = []
if 'selected_years' not in st.session_state:
    st.session_state.selected_years = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# Get unique values for filters
job_types = [x for x in JOB_TYPE_ORDER if x in df['job_type_edited'].unique()]
verification_types = sorted([x for x in df['verification_type'].unique() if pd.notna(x)])
years = sorted([str(x) for x in df['creation_year'].unique() if pd.notna(x)], reverse=True)

# Create filter section
st.markdown("## Filters")

# Search bar
search_term = st.text_input("Search by job name or creator")

# Job Type Filter
st.markdown("### Job Type")
job_type_cols = st.columns(min(5, len(job_types)))
for i, job_type in enumerate(job_types):
    with job_type_cols[i % len(job_type_cols)]:
        is_selected = job_type in st.session_state.selected_job_types
        if st.button(job_type, key=f"job_type_{job_type}", use_container_width=True, type="primary" if is_selected else "secondary"):
            if is_selected:
                st.session_state.selected_job_types.remove(job_type)
            else:
                st.session_state.selected_job_types.append(job_type)
            st.rerun()

st.markdown("---")

# Verification Type Filter
st.markdown("### Verification Types")
verification_cols = st.columns(min(3, len(verification_types)))
for i, verification_type in enumerate(verification_types):
    with verification_cols[i % len(verification_cols)]:
        is_selected = verification_type in st.session_state.selected_verification_types
        if st.button(verification_type, key=f"verification_{verification_type}", use_container_width=True, type="primary" if is_selected else "secondary"):
            if is_selected:
                st.session_state.selected_verification_types.remove(verification_type)
            else:
                st.session_state.selected_verification_types.append(verification_type)
            st.rerun()

st.markdown("---")

# Year Filter
st.markdown("### Years")
year_cols = st.columns(min(5, len(years)))
for i, year in enumerate(years):
    with year_cols[i % len(year_cols)]:
        is_selected = year in st.session_state.selected_years
        if st.button(year, key=f"year_{year}", use_container_width=True, type="primary" if is_selected else "secondary"):
            if is_selected:
                st.session_state.selected_years.remove(year)
            else:
                st.session_state.selected_years.append(year)
            st.rerun()

st.markdown("---")

# Main content area
tab1, tab2 = st.tabs(["Browse All Jobs", "Random Job Discovery"])

with tab1:
    # Header with page controls
    header_col1, header_col2 = st.columns([3, 1])
    
    with header_col1:
        st.subheader("Browse Jobs")
    
    with header_col2:
        # Clear filters button
        if st.button("Clear Filters", use_container_width=True):
            st.session_state.selected_job_types = []
            st.session_state.selected_verification_types = []
            st.session_state.selected_years = []
            st.session_state.current_page = 1
            st.rerun()
    
    # Apply filters
    filtered_df = df.copy()
    
    if st.session_state.selected_job_types:
        filtered_df = filtered_df[filtered_df['job_type_edited'].isin(st.session_state.selected_job_types)]
    
    if st.session_state.selected_verification_types:
        filtered_df = filtered_df[filtered_df['verification_type'].isin(st.session_state.selected_verification_types)]
    
    if st.session_state.selected_years:
        filtered_df = filtered_df[filtered_df['creation_year'].isin(st.session_state.selected_years)]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['job_name'].str.contains(search_term, case=False) |
            filtered_df['job_creator'].str.contains(search_term, case=False)
        ]
    
    # Display results
    st.info(f"Found {len(filtered_df)} jobs matching your filters")
    
    if not filtered_df.empty:
        # Pagination controls in a single line
        page_size = 30
        total_pages = (len(filtered_df) // page_size) + 1
        
        # Create columns for pagination
        page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
        
        with page_col1:
            if st.button("← Previous", disabled=st.session_state.current_page <= 1):
                st.session_state.current_page = max(1, st.session_state.current_page - 1)
                st.rerun()
        
        with page_col2:
            current_page = st.number_input(
                "Page", 
                min_value=1, 
                max_value=total_pages, 
                value=st.session_state.current_page,
                key="page_input"
            )
            # Update session state if page number changes
            if current_page != st.session_state.current_page:
                st.session_state.current_page = current_page
                st.rerun()
        
        with page_col3:
            if st.button("Next →", disabled=st.session_state.current_page >= total_pages):
                st.session_state.current_page = min(total_pages, st.session_state.current_page + 1)
                st.rerun()
        
        # Get current page data
        start_idx = (current_page - 1) * page_size
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
                            st.image(row['job_image'], width=300, use_container_width=True)
                
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
    
    # Use the same filters as the main page
    num_jobs = st.slider("Number of random jobs to show", min_value=1, max_value=30, value=12)
    
    if st.button("🎲 Get Random Jobs"):
        random_jobs = get_random_jobs(
            df, 
            num_jobs, 
            st.session_state.selected_job_types,
            st.session_state.selected_verification_types,
            st.session_state.selected_years
        )
        
        if not random_jobs.empty:
            st.success(f"Found {len(random_jobs)} random jobs!")
            
            # Display in a grid
            cols = st.columns(3)
            for i, (_, row) in enumerate(random_jobs.iterrows()):
                with cols[i % 3]:
                    # Responsive image
                    if pd.notna(row['job_image']) and row['job_image']:
                        st.image(row['job_image'], width=200, use_container_width=True)
                    
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