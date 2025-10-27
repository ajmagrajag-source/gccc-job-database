import streamlit as st
import sqlite3
import pandas as pd
import random
from datetime import datetime
import time
import toml
import os

# Load configuration from config.toml
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.toml")
    if os.path.exists(config_path):
        return toml.load(config_path)
    else:
        # Default configuration if config.toml doesn't exist
        return {
            "app": {
                "title": "Rockstar Social Club Jobs Database",
                "description": "Browse and search through scraped Rockstar job data",
                "logo": "assets/logo_gccc.png",
                "logo_width": 80,
                "wide_view": True
            },
            "style": {
                "primary_color": "#fcaf17",
                "text_color": "black"
            },
            "assets": {
                "rockstar_logo": "assets/logo_rockstar.png",
                "gtalens_logo": "assets/logo_gtalens.png",
                "logo_size": 30
            }
        }

config = load_config()

# Set page layout from config
layout = "wide" if config["app"].get("wide_view", True) else "centered"
st.set_page_config(
    page_title="Rockstar Jobs Database",
    page_icon="🎮",
    layout=layout,
    initial_sidebar_state="collapsed"
)

# Custom CSS with config values
st.markdown(f"""
<style>
div.stButton > button:first-child {{
    background-color: {config['style']['primary_color']};
    color: {config['style']['text_color']};
}}
div.stButton > button:first-child:hover {{
    background-color: {config['style']['primary_color']};
    opacity: 0.8;
    color: {config['style']['text_color']};
}}
.streamlit-expanderHeader {{
    background-color: #f8f8f8;
}}
.right-align {{
    text-align: right;
}}
.center-align {{
    text-align: center;
}}
.job-type-container {{
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
</style>
""", unsafe_allow_html=True)

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

def format_date(date_str):
    """Format date string to a more user-friendly format"""
    try:
        date_obj = pd.to_datetime(date_str, errors='coerce')
        if pd.notna(date_obj):
            return date_obj.strftime("%B %d, %Y")
        return date_str
    except:
        return date_str

def get_random_jobs(df, n=12, job_type_filters=None, verification_filters=None, year_filters=None, player_filters=None):
    """Get n random jobs with optional filters"""
    filtered_df = df.copy()
    
    if job_type_filters and len(job_type_filters) > 0:
        filtered_df = filtered_df[filtered_df['job_type_edited'].isin(job_type_filters)]
    
    if verification_filters and len(verification_filters) > 0:
        filtered_df = filtered_df[filtered_df['verification_type'].isin(verification_filters)]
    
    if year_filters and len(year_filters) > 0:
        filtered_df = filtered_df[filtered_df['creation_year'].isin(year_filters)]
    
    if player_filters and len(player_filters) > 0:
        if "30 players" in player_filters:
            filtered_df = filtered_df[filtered_df['max_players'] == "30"]
        elif "16-29 players" in player_filters:
            filtered_df = filtered_df[filtered_df['max_players'].astype(int).between(16, 29)]
        elif "8-15 players" in player_filters:
            filtered_df = filtered_df[filtered_df['max_players'].astype(int).between(8, 15)]
    
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

# User-friendly column names for display
COLUMN_DISPLAY_NAMES = {
    "job_name": "Job Name",
    "job_creator": "Creator",
    "job_type_edited": "Job Type",
    "max_players": "Max Players",
    "creation_date": "Creation Date",
    "last_updated": "Last Updated",
    "verification_type": "Verification Type"
}

# Main app with logo
col1, col2 = st.columns([1, 10])
with col1:
    st.image(config['app']['logo'], width=config['app']['logo_width'])
with col2:
    st.title(config['app']['title'])

st.markdown(config['app']['description'])

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
if 'selected_year_range' not in st.session_state:
    st.session_state.selected_year_range = [int(min(df['creation_year'])), int(max(df['creation_year']))]
if 'selected_player_filters' not in st.session_state:
    st.session_state.selected_player_filters = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'filters_expanded' not in st.session_state:
    st.session_state.filters_expanded = True
if 'sort_column' not in st.session_state:
    st.session_state.sort_column = "creation_date"
if 'sort_direction' not in st.session_state:
    st.session_state.sort_direction = "desc"

# Get unique values for filters
job_types = [x for x in JOB_TYPE_ORDER if x in df['job_type_edited'].unique()]
verification_types = sorted([x for x in df['verification_type'].unique() if pd.notna(x)])
min_year = int(min(df['creation_year']))
max_year = int(max(df['creation_year']))

# Search bar
search_term = st.text_input("Search by Job Name or Creator")

# Create collapsible filter section
with st.expander("Filters", expanded=st.session_state.filters_expanded):
    # Job Type Filter
    st.markdown("### Job Type")
    job_type_cols = st.columns(min(5, len(job_types)))
    for i, job_type in enumerate(job_types):
        with job_type_cols[i % len(job_type_cols)]:
            is_selected = job_type in st.session_state.selected_job_types
            # Only use primary color if selected
            button_type = "primary" if is_selected else "secondary"
            if st.button(job_type, key=f"job_type_{job_type}", use_container_width=True, type=button_type):
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
            # Only use primary color if selected
            button_type = "primary" if is_selected else "secondary"
            if st.button(verification_type, key=f"verification_{verification_type}", use_container_width=True, type=button_type):
                if is_selected:
                    st.session_state.selected_verification_types.remove(verification_type)
                else:
                    st.session_state.selected_verification_types.append(verification_type)
                st.rerun()
    
    st.markdown("---")
    
    # Creation Year Filter (Slider with debounce)
    st.markdown("### Creation Year")
    
    # Get current slider value
    current_year_range = st.session_state.selected_year_range
    
    # Create a placeholder for the slider
    year_slider_placeholder = st.empty()
    
    # Create the slider in the placeholder
    with year_slider_placeholder:
        year_range = st.slider(
            "Select Year Range",
            min_value=min_year,
            max_value=max_year,
            value=current_year_range,
            step=1,
            key="year_slider"
        )
    
    # Only update session state if the slider value has changed
    if year_range != current_year_range:
        st.session_state.selected_year_range = year_range
        # Add a small delay to prevent excessive reruns
        time.sleep(0.1)
        st.rerun()
    
    st.markdown("---")
    
    # Max Players Filter
    st.markdown("### Max Players")
    player_options = ["30 players", "16-29 players", "8-15 players"]
    player_cols = st.columns(len(player_options))
    for i, player_option in enumerate(player_options):
        with player_cols[i]:
            is_selected = player_option in st.session_state.selected_player_filters
            # Only use primary color if selected
            button_type = "primary" if is_selected else "secondary"
            if st.button(player_option, key=f"player_{player_option}", use_container_width=True, type=button_type):
                if is_selected:
                    st.session_state.selected_player_filters.remove(player_option)
                else:
                    st.session_state.selected_player_filters = [player_option]  # Only allow one selection
                st.rerun()
    
    st.markdown("---")
    
    # Clear filters button
    if st.button("Clear All Filters", use_container_width=True):
        st.session_state.selected_job_types = []
        st.session_state.selected_verification_types = []
        st.session_state.selected_year_range = [min_year, max_year]
        st.session_state.selected_player_filters = []
        st.session_state.current_page = 1
        st.rerun()

# Main content area
tab1, tab2, tab3 = st.tabs(["Browse All Jobs", "Random Job Discovery", "Table View"])

with tab1:
    # Header with page controls
    header_col1, header_col2 = st.columns([3, 1])
    
    with header_col1:
        st.subheader("Browse Jobs")
    
    with header_col2:
        # Clear filters button
        if st.button("Reset Page", use_container_width=True):
            st.session_state.current_page = 1
            st.rerun()
    
    # Apply filters
    filtered_df = df.copy()
    
    if st.session_state.selected_job_types:
        filtered_df = filtered_df[filtered_df['job_type_edited'].isin(st.session_state.selected_job_types)]
    
    if st.session_state.selected_verification_types:
        filtered_df = filtered_df[filtered_df['verification_type'].isin(st.session_state.selected_verification_types)]
    
    # Apply year range filter
    year_min, year_max = st.session_state.selected_year_range
    filtered_df = filtered_df[filtered_df['creation_year'].astype(int).between(year_min, year_max)]
    
    # Apply player count filter
    if st.session_state.selected_player_filters:
        if "30 players" in st.session_state.selected_player_filters:
            filtered_df = filtered_df[filtered_df['max_players'] == "30"]
        elif "16-29 players" in st.session_state.selected_player_filters:
            filtered_df = filtered_df[filtered_df['max_players'].astype(int).between(16, 29)]
        elif "8-15 players" in st.session_state.selected_player_filters:
            filtered_df = filtered_df[filtered_df['max_players'].astype(int).between(8, 15)]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['job_name'].str.contains(search_term, case=False) |
            filtered_df['job_creator'].str.contains(search_term, case=False)
        ]
    
    # Display results
    st.info(f"Found {len(filtered_df)} jobs matching your filters")
    
    if not filtered_df.empty:
        # Sort controls
        sort_col1, sort_col2, sort_col3 = st.columns([1, 1, 1])
        with sort_col1:
            # Use display names for sort options
            sort_options = [COLUMN_DISPLAY_NAMES.get(col, col) for col in ["job_name", "job_creator", "job_type_edited", "creation_date", "last_updated", "verification_type"]]
            current_index = sort_options.index(COLUMN_DISPLAY_NAMES.get(st.session_state.sort_column, st.session_state.sort_column)) if st.session_state.sort_column in COLUMN_DISPLAY_NAMES else 0
            sort_column_display = st.selectbox("Sort by", sort_options, index=current_index)
            
            # Convert display name back to column name
            sort_column = {v: k for k, v in COLUMN_DISPLAY_NAMES.items()}.get(sort_column_display, sort_column_display)
        
        with sort_col2:
            sort_direction = st.selectbox(
                "Direction",
                ["Ascending", "Descending"],
                index=0 if st.session_state.sort_direction == "asc" else 1
            )
        
        with sort_col3:
            if st.button("Apply Sort", use_container_width=True):
                st.session_state.sort_column = sort_column
                st.session_state.sort_direction = "asc" if sort_direction == "Ascending" else "desc"
                st.rerun()
        
        # Apply sorting with case-insensitive and date-aware sorting
        if st.session_state.sort_column in filtered_df.columns:
            ascending = st.session_state.sort_direction == "asc"
            
            if st.session_state.sort_column in ["job_name", "job_creator"]:
                # Case-insensitive sorting for text columns
                filtered_df = filtered_df.sort_values(
                    by=st.session_state.sort_column, 
                    ascending=ascending, 
                    key=lambda x: x.str.lower()
                )
            elif st.session_state.sort_column in ["creation_date", "last_updated"]:
                # Date-aware sorting for date columns
                filtered_df[st.session_state.sort_column] = pd.to_datetime(
                    filtered_df[st.session_state.sort_column], 
                    errors='coerce'
                )
                filtered_df = filtered_df.sort_values(
                    by=st.session_state.sort_column, 
                    ascending=ascending
                )
            else:
                # Default sorting for other columns
                filtered_df = filtered_df.sort_values(
                    by=st.session_state.sort_column, 
                    ascending=ascending
                )
        
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
                    # Job name and creator with job type on same line
                    job_name = row['job_name']
                    job_creator = row['job_creator']
                    job_type = row['job_type_edited'] or row['job_type']
                    
                    # Create columns for job info
                    info_col1, info_col2 = st.columns([3, 1])
                    with info_col1:
                        st.markdown(f"### {job_name} by {job_creator}")
                    with info_col2:
                        st.markdown(f"<p style='font-style: italic; text-align: right;'>{job_type}</p>", unsafe_allow_html=True)
                    
                    # Creation date, update date, and verification type
                    creation_date = format_date(row['creation_date'])
                    last_updated = format_date(row['last_updated'])
                    verification = row['verification_type']
                    st.markdown(f"**Created:** {creation_date} | **Updated:** {last_updated} | **{verification}**")
                    
                    # Links with icons
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"[![Rockstar]({config['assets']['rockstar_logo']}|width={config['assets']['logo_size']})]({row['original_url']})")
                    with col_b:
                        if pd.notna(row['gta_lens_link']) and row['gta_lens_link']:
                            st.markdown(f"[![GTALens]({config['assets']['gtalens_logo']}|width={config['assets']['logo_size']})]({row['gta_lens_link']})")
                    
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
            [str(year) for year in range(st.session_state.selected_year_range[0], st.session_state.selected_year_range[1] + 1)],
            st.session_state.selected_player_filters
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
                    
                    st.markdown(f"[![Rockstar]({config['assets']['rockstar_logo']}|width={config['assets']['logo_size']})]({row['original_url']})")
                    st.divider()
        else:
            st.warning("No jobs found with the selected filters.")

with tab3:
    st.subheader("Table View")
    
    # Apply the same filters as in the card view
    filtered_df = df.copy()
    
    if st.session_state.selected_job_types:
        filtered_df = filtered_df[filtered_df['job_type_edited'].isin(st.session_state.selected_job_types)]
    
    if st.session_state.selected_verification_types:
        filtered_df = filtered_df[filtered_df['verification_type'].isin(st.session_state.selected_verification_types)]
    
    # Apply year range filter
    year_min, year_max = st.session_state.selected_year_range
    filtered_df = filtered_df[filtered_df['creation_year'].astype(int).between(year_min, year_max)]
    
    # Apply player count filter
    if st.session_state.selected_player_filters:
        if "30 players" in st.session_state.selected_player_filters:
            filtered_df = filtered_df[filtered_df['max_players'] == "30"]
        elif "16-29 players" in st.session_state.selected_player_filters:
            filtered_df = filtered_df[filtered_df['max_players'].astype(int).between(16, 29)]
        elif "8-15 players" in st.session_state.selected_player_filters:
            filtered_df = filtered_df[filtered_df['max_players'].astype(int).between(8, 15)]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['job_name'].str.contains(search_term, case=False) |
            filtered_df['job_creator'].str.contains(search_term, case=False)
        ]
    
    # Display results
    st.info(f"Found {len(filtered_df)} jobs matching your filters")
    
    if not filtered_df.empty:
        # Sort controls
        sort_col1, sort_col2, sort_col3 = st.columns([1, 1, 1])
        with sort_col1:
            # Use display names for sort options
            sort_options = [COLUMN_DISPLAY_NAMES.get(col, col) for col in ["job_name", "job_creator", "job_type_edited", "creation_date", "last_updated", "verification_type"]]
            current_index = sort_options.index(COLUMN_DISPLAY_NAMES.get(st.session_state.sort_column, st.session_state.sort_column)) if st.session_state.sort_column in COLUMN_DISPLAY_NAMES else 0
            sort_column_display = st.selectbox("Sort by", sort_options, index=current_index, key="table_sort_column")
            
            # Convert display name back to column name
            sort_column = {v: k for k, v in COLUMN_DISPLAY_NAMES.items()}.get(sort_column_display, sort_column_display)
        
        with sort_col2:
            sort_direction = st.selectbox(
                "Direction",
                ["Ascending", "Descending"],
                index=0 if st.session_state.sort_direction == "asc" else 1,
                key="table_sort_direction"
            )
        
        with sort_col3:
            if st.button("Apply Sort", use_container_width=True, key="table_apply_sort"):
                st.session_state.sort_column = sort_column
                st.session_state.sort_direction = "asc" if sort_direction == "Ascending" else "desc"
                st.rerun()
        
        # Apply sorting with case-insensitive and date-aware sorting
        if st.session_state.sort_column in filtered_df.columns:
            ascending = st.session_state.sort_direction == "asc"
            
            if st.session_state.sort_column in ["job_name", "job_creator"]:
                # Case-insensitive sorting for text columns
                filtered_df = filtered_df.sort_values(
                    by=st.session_state.sort_column, 
                    ascending=ascending, 
                    key=lambda x: x.str.lower()
                )
            elif st.session_state.sort_column in ["creation_date", "last_updated"]:
                # Date-aware sorting for date columns
                filtered_df[st.session_state.sort_column] = pd.to_datetime(
                    filtered_df[st.session_state.sort_column], 
                    errors='coerce'
                )
                filtered_df = filtered_df.sort_values(
                    by=st.session_state.sort_column, 
                    ascending=ascending
                )
            else:
                # Default sorting for other columns
                filtered_df = filtered_df.sort_values(
                    by=st.session_state.sort_column, 
                    ascending=ascending
                )
        
        # Create a simplified dataframe for display
        display_df = filtered_df[[
            'job_name', 'job_creator', 'job_type_edited', 'max_players', 
            'creation_date', 'last_updated', 'verification_type', 'original_url', 'gta_lens_link'
        ]].copy()
        
        # Format dates for display
        display_df['creation_date'] = display_df['creation_date'].apply(format_date)
        display_df['last_updated'] = display_df['last_updated'].apply(format_date)
        
        # Rename columns for better display
        display_df.columns = [
            'Job Name', 'Creator', 'Type', 'Max Players', 
            'Created', 'Updated', 'Verification', 'Rockstar', 'Lens'
        ]
        
        # Convert URLs to clickable links
        display_df['Job Name'] = display_df.apply(
            lambda row: f"<a href='{row['Rockstar']}' target='_blank'>{row['Job Name']}</a>", 
            axis=1
        )
        
        display_df['Lens'] = display_df.apply(
            lambda row: f"<a href='{row['Lens']}' target='_blank'>View</a>" if pd.notna(row['Lens']) else "", 
            axis=1
        )
        
        # Drop the original URL columns
        display_df = display_df.drop(columns=['Rockstar'])
        
        # Create HTML table with custom styling
        html_table = display_df.to_html(
            escape=False,
            index=False,
            classes="dataframe",
            formatters={
                'Created': lambda x: f"<div class='right-align'>{x}</div>",
                'Updated': lambda x: f"<div class='right-align'>{x}</div>",
                'Max Players': lambda x: f"<div class='center-align'>{x}</div>",
                'Lens': lambda x: f"<div class='center-align'>{x}</div>"
            }
        )
        
        # Display the table
        st.write(html_table, unsafe_allow_html=True)
    else:
        st.warning("No jobs match your filters. Try adjusting your search criteria.")

# Footer
st.markdown("---")
st.markdown("*Data scraped from Rockstar Social Club*")