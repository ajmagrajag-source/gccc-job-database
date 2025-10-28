import streamlit as st
import sqlite3
import pandas as pd
import random
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Rockstar Jobs Database",
    page_icon="🎮",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
        white-space: nowrap;
    }
    .job-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        margin-bottom: 1rem;
        border: 1px solid #e5e7eb;
    }
    .job-card:hover {
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .job-title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .job-creator {
        color: #6b7280;
        font-size: 0.875rem;
        margin-bottom: 0.5rem;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .badge-blue {
        background-color: #dbeafe;
        color: #1e40af;
    }
    .badge-green {
        background-color: #d1fae5;
        color: #065f46;
    }
    .filter-button {
        margin: 0.25rem;
    }
    div[data-testid="column"] {
        padding: 0.5rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    /* Button styling for filter buttons */
    div[data-testid="stHorizontalBlock"] button {
        border-radius: 9999px;
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
    }
    /* Sidebar width adjustment */
    section[data-testid="stSidebar"] {
        width: 320px !important;
    }
</style>
""", unsafe_allow_html=True)

# Custom job type order
JOB_TYPE_ORDER = [
    "GP", "Street", "Race", "Stunt Race", "Banger Race", "Off Road",
    "Deathmatch", "King of the Hill", "Last Team Standing", "Parkour", "Other"
]

# Database connection
@st.cache_resource
def get_connection():
    return sqlite3.connect('rockstar_jobs.db', check_same_thread=False)

# Load data with caching
@st.cache_data(ttl=300)
def load_jobs():
    conn = get_connection()
    query = """
    SELECT 
        id,
        job_name,
        job_creator,
        job_type_edited,
        max_players,
        verification_type,
        creation_date,
        last_updated,
        scraped_at,
        gta_lens_link,
        original_url,
        job_description,
        job_image
    FROM jobs
    """
    df = pd.read_sql_query(query, conn)
    return df

# Parse date string to datetime
def parse_date(date_str):
    if pd.isna(date_str):
        return None
    try:
        # Parse "August 08, 2015" format
        return datetime.strptime(date_str, "%B %d, %Y")
    except:
        return None

# Format date for display
def format_date(date_str):
    dt = parse_date(date_str)
    if dt:
        return dt.strftime("%b %d, %Y")
    return date_str

# Extract year from date string
def extract_year(date_str):
    if pd.isna(date_str):
        return None
    try:
        parts = date_str.split(',')
        if len(parts) >= 2:
            return int(parts[1].strip())
    except:
        return None
    return None

# Parse scraped_at datetime
def parse_scraped_at(scraped_str):
    if pd.isna(scraped_str):
        return None
    try:
        return datetime.strptime(scraped_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None

# Sort job types by custom order
def sort_job_types(job_types):
    sorted_types = []
    # Add types in custom order if they exist
    for jt in JOB_TYPE_ORDER:
        if jt in job_types:
            sorted_types.append(jt)
    # Add any remaining types not in custom order
    for jt in sorted(job_types):
        if jt not in sorted_types:
            sorted_types.append(jt)
    return sorted_types

# Initialize session state
if 'expanded_cards' not in st.session_state:
    st.session_state.expanded_cards = set()
if 'selected_job_types' not in st.session_state:
    st.session_state.selected_job_types = []
if 'selected_max_players' not in st.session_state:
    st.session_state.selected_max_players = []

# Load data
df = load_jobs()

# Add parsed date columns for sorting
df['creation_date_dt'] = df['creation_date'].apply(parse_date)
df['last_updated_dt'] = df['last_updated'].apply(parse_date)
df['scraped_at_dt'] = df['scraped_at'].apply(parse_scraped_at)
df['creation_year'] = df['creation_date'].apply(extract_year)
df['update_year'] = df['last_updated'].apply(extract_year)

# Add job type order for sorting
job_type_order_map = {jt: idx for idx, jt in enumerate(JOB_TYPE_ORDER)}
df['job_type_order'] = df['job_type_edited'].map(lambda x: job_type_order_map.get(x, 999))

# Get min/max years for sliders from full dataset
min_creation_year_full = int(df['creation_year'].min()) if df['creation_year'].notna().any() else 2013
max_creation_year_full = int(df['creation_year'].max()) if df['creation_year'].notna().any() else 2025
min_update_year_full = int(df['update_year'].min()) if df['update_year'].notna().any() else 2013
max_update_year_full = int(df['update_year'].max()) if df['update_year'].notna().any() else 2025

# Title
st.title("🎮 Rockstar Jobs Database")

# Tabs
tab1, tab2, tab3 = st.tabs(["📇 Card View", "📊 Table View", "🎲 Random Jobs"])

# Sidebar for filters
with st.sidebar:
    st.header("🔍 Search & Filters")
    
    # Search
    search_term = st.text_input("Search", placeholder="Job name, creator...")
    
    st.divider()
    
    # Job Type Filter with buttons in custom order
    st.subheader("Job Types")
    job_types = list(df['job_type_edited'].unique())
    job_types_sorted = sort_job_types(job_types)
    
    # Create columns for job type buttons
    num_cols = 2
    cols = st.columns(num_cols)
    for idx, job_type in enumerate(job_types_sorted):
        with cols[idx % num_cols]:
            is_selected = job_type in st.session_state.selected_job_types
            button_type = "primary" if is_selected else "secondary"
            if st.button(job_type, key=f"jt_{job_type}", type=button_type, use_container_width=True):
                if is_selected:
                    st.session_state.selected_job_types.remove(job_type)
                else:
                    st.session_state.selected_job_types.append(job_type)
                st.rerun()
    
    st.divider()
    
    # Max Players Filter with buttons
    st.subheader("Max Players")
    player_ranges = [("30", "30"), ("16-29", "16-29"), ("8-15", "8-15")]
    
    cols = st.columns(3)
    for idx, (label, value) in enumerate(player_ranges):
        with cols[idx]:
            is_selected = value in st.session_state.selected_max_players
            button_type = "primary" if is_selected else "secondary"
            if st.button(label, key=f"mp_{value}", type=button_type, use_container_width=True):
                if is_selected:
                    st.session_state.selected_max_players.remove(value)
                else:
                    st.session_state.selected_max_players.append(value)
                st.rerun()
    
    st.divider()
    
    # Creation Year Filter
    st.subheader("Creation Year")
    creation_year_range = st.slider(
        "Select range",
        min_value=min_creation_year_full,
        max_value=max_creation_year_full,
        value=(min_creation_year_full, max_creation_year_full),
        key="creation_slider"
    )
    
    st.divider()
    
    # Update Year Filter
    st.subheader("Last Updated Year")
    update_year_range = st.slider(
        "Select range",
        min_value=min_update_year_full,
        max_value=max_update_year_full,
        value=(min_update_year_full, max_update_year_full),
        key="update_slider"
    )
    
    st.divider()
    
    # Clear filters button
    if st.button("Clear All Filters", use_container_width=True):
        st.session_state.selected_job_types = []
        st.session_state.selected_max_players = []
        # Reset sliders by forcing a rerun with default values
        if 'creation_slider' in st.session_state:
            del st.session_state['creation_slider']
        if 'update_slider' in st.session_state:
            del st.session_state['update_slider']
        st.rerun()

# Apply filters
filtered_df = df.copy()

# Search filter
if search_term:
    search_lower = search_term.lower()
    filtered_df = filtered_df[
        filtered_df['job_name'].str.lower().str.contains(search_lower, na=False) |
        filtered_df['job_creator'].str.lower().str.contains(search_lower, na=False) |
        filtered_df['job_description'].str.lower().str.contains(search_lower, na=False)
    ]

# Job type filter
if st.session_state.selected_job_types:
    filtered_df = filtered_df[filtered_df['job_type_edited'].isin(st.session_state.selected_job_types)]

# Max players filter
if st.session_state.selected_max_players:
    def check_max_players(players, filters):
        try:
            p = int(players)
            for f in filters:
                if f == "30" and p == 30:
                    return True
                elif f == "16-29" and 16 <= p <= 29:
                    return True
                elif f == "8-15" and 8 <= p <= 15:
                    return True
            return False
        except:
            return False
    
    filtered_df = filtered_df[
        filtered_df['max_players'].apply(lambda x: check_max_players(x, st.session_state.selected_max_players))
    ]

# Creation year filter
filtered_df = filtered_df[
    (filtered_df['creation_year'] >= creation_year_range[0]) &
    (filtered_df['creation_year'] <= creation_year_range[1])
]

# Update year filter
filtered_df = filtered_df[
    (filtered_df['update_year'] >= update_year_range[0]) &
    (filtered_df['update_year'] <= update_year_range[1])
]

# Card View
with tab1:
    col_sort1, col_sort2, col_count = st.columns([2, 1, 1])
    with col_sort1:
        sort_by = st.selectbox(
            "Sort by",
            ["Job Name", "Job Creator", "Job Type", "Creation Date", "Last Updated", "Scraped At"],
            key="card_sort"
        )
    with col_sort2:
        sort_order = st.selectbox(
            "Order",
            ["Ascending", "Descending"],
            key="card_order"
        )
    with col_count:
        st.markdown(f"**{len(filtered_df)} of {len(df)}**")
    
    # Apply sorting
    sorted_df = filtered_df.copy()
    ascending = (sort_order == "Ascending")
    
    if sort_by == "Job Name":
        sorted_df = sorted_df.sort_values('job_name', ascending=ascending)
    elif sort_by == "Job Creator":
        sorted_df = sorted_df.sort_values('job_creator', ascending=ascending)
    elif sort_by == "Job Type":
        sorted_df = sorted_df.sort_values('job_type_order', ascending=ascending)
    elif sort_by == "Creation Date":
        sorted_df = sorted_df.sort_values('creation_date_dt', ascending=ascending, na_position='last')
    elif sort_by == "Last Updated":
        sorted_df = sorted_df.sort_values('last_updated_dt', ascending=ascending, na_position='last')
    elif sort_by == "Scraped At":
        sorted_df = sorted_df.sort_values('scraped_at_dt', ascending=ascending, na_position='last')
    
    st.divider()
    
    if len(sorted_df) == 0:
        st.info("No jobs found matching your filters.")
    else:
        for _, job in sorted_df.iterrows():
            col1, col2 = st.columns([1, 4])
            
            with col1:
                if pd.notna(job['job_image']):
                    try:
                        st.image(job['job_image'], use_container_width=True)
                    except:
                        st.write("🖼️")
            
            with col2:
                # Job title and creator on one line
                max_players_text = f" ({job['max_players']} players)" if str(job['max_players']) != "30" else ""
                st.markdown(f"### [{job['job_name']}]({job['original_url']}) by {job['job_creator']}{max_players_text}")
                
                # Creation date on second line
                st.markdown(f"*Created: {format_date(job['creation_date'])}*")
                
                # Badges
                badge_html = f"""
                <div style="margin: 0.5rem 0;">
                    <span class="badge badge-blue">{job['job_type_edited']}</span>
                    <span class="badge badge-green">{job['verification_type']}</span>
                </div>
                """
                st.markdown(badge_html, unsafe_allow_html=True)
                
                # GTALens link
                if pd.notna(job['gta_lens_link']):
                    st.markdown(f"🔗 [GTALens Link]({job['gta_lens_link']})")
                
                # Collapsible description
                if pd.notna(job['job_description']) and job['job_description']:
                    card_id = f"card_{job['id']}"
                    if st.button("📝 Description", key=f"btn_{job['id']}", use_container_width=False):
                        if card_id in st.session_state.expanded_cards:
                            st.session_state.expanded_cards.remove(card_id)
                        else:
                            st.session_state.expanded_cards.add(card_id)
                    
                    if card_id in st.session_state.expanded_cards:
                        st.info(job['job_description'])
            
            st.divider()

# Table View
with tab2:
    st.markdown(f"**Showing {len(filtered_df)} of {len(df)} jobs**")
    st.divider()
    
    if len(filtered_df) == 0:
        st.info("No jobs found matching your filters.")
    else:
        # Prepare display dataframe with proper date sorting
        display_df = filtered_df.copy()
        
        # Format dates for display
        display_df['creation_date_display'] = display_df['creation_date'].apply(format_date)
        display_df['last_updated_display'] = display_df['last_updated'].apply(format_date)
        
        # Create display dataframe
        table_df = pd.DataFrame({
            'Job Name': display_df['job_name'],
            'Job Link': display_df['original_url'],
            'Creator': display_df['job_creator'],
            'Type': display_df['job_type_edited'],
            'Max Players': display_df['max_players'].astype(str),
            'Verification': display_df['verification_type'],
            'Created': display_df['creation_date_display'],
            'Updated': display_df['last_updated_display'],
            'GTALens': display_df['gta_lens_link'],
            # Hidden columns for sorting
            'creation_sort': display_df['creation_date_dt'],
            'updated_sort': display_df['last_updated_dt'],
            'type_order': display_df['job_type_order']
        })
        
        st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Job Name": st.column_config.TextColumn("Job Name", width="medium"),
                "Job Link": st.column_config.LinkColumn("Job Link", display_text="View Job"),
                "Creator": st.column_config.TextColumn("Creator", width="small"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Max Players": st.column_config.TextColumn("Max Players", width="small"),
                "Verification": st.column_config.TextColumn("Verification", width="small"),
                "Created": st.column_config.TextColumn("Created", width="small"),
                "Updated": st.column_config.TextColumn("Updated", width="small"),
                "GTALens": st.column_config.LinkColumn("GTALens", display_text="GTALens Link"),
                "creation_sort": None,
                "updated_sort": None,
                "type_order": None
            }
        )

# Random Jobs
with tab3:
    st.subheader("🎲 Random Job Selection")
    st.markdown(f"*Selecting from {len(filtered_df)} filtered jobs*")
    
    random_count = st.slider(
        "Number of random jobs",
        min_value=1,
        max_value=min(20, len(filtered_df)) if len(filtered_df) > 0 else 1,
        value=min(5, len(filtered_df)) if len(filtered_df) > 0 else 1
    )
    
    if st.button("🔀 Generate Random Selection", type="primary"):
        if len(filtered_df) > 0:
            st.session_state.random_jobs = filtered_df.sample(n=min(random_count, len(filtered_df)))
        else:
            st.warning("No jobs available with current filters!")
    
    st.divider()
    
    if 'random_jobs' in st.session_state and len(st.session_state.random_jobs) > 0:
        st.markdown(f"### Random Selection ({len(st.session_state.random_jobs)} jobs)")
        
        for _, job in st.session_state.random_jobs.iterrows():
            col1, col2 = st.columns([1, 4])
            
            with col1:
                if pd.notna(job['job_image']):
                    try:
                        st.image(job['job_image'], use_container_width=True)
                    except:
                        st.write("🖼️")
            
            with col2:
                max_players_text = f" ({job['max_players']} players)" if str(job['max_players']) != "30" else ""
                st.markdown(f"### [{job['job_name']}]({job['original_url']}) by {job['job_creator']}{max_players_text}")
                st.markdown(f"*Created: {format_date(job['creation_date'])}*")
                
                badge_html = f"""
                <div style="margin: 0.5rem 0;">
                    <span class="badge badge-blue">{job['job_type_edited']}</span>
                    <span class="badge badge-green">{job['verification_type']}</span>
                </div>
                """
                st.markdown(badge_html, unsafe_allow_html=True)
                
                if pd.notna(job['gta_lens_link']):
                    st.markdown(f"🔗 [GTALens Link]({job['gta_lens_link']})")
                
                if pd.notna(job['job_description']) and job['job_description']:
                    with st.expander("📝 Description"):
                        st.write(job['job_description'])
            
            st.divider()
    else:
        st.info("Click the button above to generate a random selection of jobs!")

# Footer
st.divider()
st.markdown(
    "<div style='text-align: center; color: #6b7280; padding: 2rem;'>"
    f"Total Jobs in Database: {len(df)}"
    "</div>",
    unsafe_allow_html=True
)