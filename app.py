
import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import math

# ---------------- CONFIGURATION ----------------

st.set_page_config(
    page_title="MemoryMesh",
    page_icon="🧠",
    layout="wide"
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "memorymesh.db"


# ---------------- DATABASE ----------------

def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


def add_memory(content, category, importance):
    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO memories
            (content, category, importance, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (content, category, importance, now, now))


def get_memories():
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM memories ORDER BY id DESC",
            conn
        )


def update_memory(memory_id, content, category, importance):
    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute("""
            UPDATE memories
            SET content = ?, category = ?,
                importance = ?, updated_at = ?
            WHERE id = ?
        """, (content, category, importance, now, memory_id))


def delete_memory(memory_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM memories WHERE id = ?",
            (memory_id,)
        )


initialize_database()


# ---------------- MEMORY SCORING ----------------

def calculate_score(created_at, importance):
    created = datetime.fromisoformat(created_at)
    age_days = max(
        0,
        (datetime.now() - created).total_seconds() / 86400
    )

    # Importance ranges from 1 to 5.
    # Higher importance means slower decay.
    decay_rate = 0.02 / importance

    score = importance * math.exp(-decay_rate * age_days)

    return round(score, 3)


# ---------------- USER INTERFACE ----------------

st.title("🧠 MemoryMesh")
st.caption("Long-Term Memory and Forgetting Mechanism for AI Agents")


# ---------------- DASHBOARD ----------------

memories = get_memories()

if not memories.empty:
    memories["memory_score"] = memories.apply(
        lambda row: calculate_score(
            row["created_at"],
            int(row["importance"])
        ),
        axis=1
    )

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Memories", len(memories))

with col2:
    st.metric(
        "High-Importance Memories",
        int((memories["importance"] >= 4).sum())
        if not memories.empty else 0
    )

with col3:
    st.metric(
        "Average Memory Score",
        round(memories["memory_score"].mean(), 2)
        if not memories.empty else 0
    )

with col4:
    st.metric(
        "Memory Categories",
        memories["category"].nunique()
        if not memories.empty else 0
    )

st.divider()

st.subheader("Memory Priority Distribution")

if not memories.empty:
    st.bar_chart(
        memories.set_index("id")[["memory_score"]]
    )
else:
    st.info("Add your first memory to display the chart.")

st.divider()
# ---------------- APPLICATION TABS ----------------

tab1, tab2, tab3, tab4 = st.tabs([
    "➕ Add Memory",
    "🔍 Search Memory",
    "🗂️ Manage Memories",
    "⏳ Forgetting Analysis"
])

# ---------------- ADD MEMORY ----------------

with tab1:
    st.subheader("Save a New Memory")

    with st.form("add_memory_form"):
        content = st.text_area(
            "Memory content",
            placeholder="Example: I prefer Python over Java."
        )

        category = st.selectbox(
            "Category",
            [
                "Preference",
                "Personal Information",
                "Learning",
                "Task",
                "Project",
                "Other"
            ]
        )

        importance = st.slider(
            "Importance",
            min_value=1,
            max_value=5,
            value=3,
            help="1 = Low importance, 5 = High importance"
        )

        submitted = st.form_submit_button("Save Memory")

        if submitted:
            if content.strip():
                add_memory(
                    content.strip(),
                    category,
                    importance
                )
                st.success("Memory saved successfully!")
                st.rerun()
            else:
                st.error("Please enter memory content.")


# ---------------- SEARCH MEMORY ----------------


# ---------------- SEARCH MEMORY ----------------

with tab2:
    st.subheader("Search Stored Memories")

    query = st.text_input(
        "Enter keywords",
        placeholder="Example: Python"
    )

    if query.strip():
        current_memories = get_memories()

        results = current_memories[
            current_memories["content"].str.contains(
                query.strip(),
                case=False,
                na=False,
                regex=False
            )
        ].copy()

        if results.empty:
            st.info("No matching memories found.")

        else:
            results["memory_score"] = results.apply(
                lambda row: calculate_score(
                    row["created_at"],
                    int(row["importance"])
                ),
                axis=1
            )

            results = results.sort_values(
                by="memory_score",
                ascending=False
            )

            for _, memory in results.iterrows():
                st.markdown(
                    f"**Memory #{memory['id']}**"
                )

                st.write(memory["content"])

                st.caption(
                    f"Category: {memory['category']} | "
                    f"Importance: {memory['importance']}/5 | "
                    f"Memory score: {memory['memory_score']}"
                )

                st.divider()

    else:
        st.info(
            "Enter a keyword to search your memories."
        )


# ---------------- MANAGE MEMORIES ----------------

with tab3:
    st.subheader("View, Update, or Delete Memories")

    current_memories = get_memories()

    if current_memories.empty:
        st.info("No memories stored yet.")
    else:
        st.dataframe(
            current_memories,
            use_container_width=True,
            hide_index=True
        )

        selected_id = st.selectbox(
            "Select memory ID",
            current_memories["id"].tolist()
        )

        selected = current_memories[
            current_memories["id"] == selected_id
        ].iloc[0]

        with st.form("edit_memory_form"):
            edited_content = st.text_area(
                "Content",
                value=selected["content"]
            )

            categories = [
                "Preference",
                "Personal Information",
                "Learning",
                "Task",
                "Project",
                "Other"
            ]

            category_index = (
                categories.index(selected["category"])
                if selected["category"] in categories else 5
            )

            edited_category = st.selectbox(
                "Category",
                categories,
                index=category_index
            )

            edited_importance = st.slider(
                "Importance",
                min_value=1,
                max_value=5,
                value=int(selected["importance"])
            )

            save_changes = st.form_submit_button(
                "Update Memory"
            )

            if save_changes:
                if edited_content.strip():
                    update_memory(
                        int(selected_id),
                        edited_content.strip(),
                        edited_category,
                        edited_importance
                    )
                    st.success("Memory updated!")
                    st.rerun()
                else:
                    st.error("Content cannot be empty.")

        if st.button(
            "Delete Selected Memory",
            type="secondary"
        ):
            delete_memory(int(selected_id))
            st.success("Memory deleted.")
            st.rerun()


# ---------------- FORGETTING ANALYSIS ----------------

with tab4:
    st.subheader("Memory Decay and Forgetting")

    st.write(
        "This prototype calculates a memory priority score "
        "using importance and the age of a memory."
    )

    current_memories = get_memories()

    if current_memories.empty:
        st.info("Add some memories to see the analysis.")
    else:
        current_memories["age_days"] = current_memories[
            "created_at"
        ].apply(
            lambda value: max(
                0,
                (datetime.now() -
                 datetime.fromisoformat(value)
                ).total_seconds() / 86400
            )
        )

        current_memories["memory_score"] = current_memories.apply(
            lambda row: calculate_score(
                row["created_at"],
                int(row["importance"])
            ),
            axis=1
        )

        st.dataframe(
            current_memories[
                [
                    "id",
                    "content",
                    "importance",
                    "age_days",
                    "memory_score"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.bar_chart(
            current_memories.set_index("id")["memory_score"]
        )

        st.caption(
            "Higher scores indicate higher current priority. "
            "This initial model uses a simple exponential decay rule."
        )

        st.warning(
            "Decay currently lowers priority only. "
            "Automatic deletion based on a retention threshold "
            "has not yet been implemented."
        )

st.divider()

st.caption(
    "MemoryMesh Prototype | Persistent storage with SQLite | "
    "Basic rule-based memory scoring"
)
