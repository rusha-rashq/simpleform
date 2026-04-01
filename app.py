import os
import subprocess

import streamlit as st
import yaml
from dotenv import load_dotenv

# Load AWS/GCP credentials
load_dotenv()

st.set_page_config(page_title="Simpleform Cloud Portal", page_icon="🚀")

st.title("🚀 Simpleform v1.2")
st.subheader("Multi-Cloud Infrastructure Orchestrator")

# --- SIDEBAR: ACTION SELECTION ---
with st.sidebar:
    st.header("Control Plane")
    action = st.radio("Select Action", ["Deploy", "Destroy"])

    if action == "Deploy":
        cloud = st.selectbox("Cloud Provider", ["aws", "gcp"])
        resource = st.selectbox("Resource Type", ["server", "bucket"])
        name = st.text_input("Resource Name", value="my-resource")
        region = st.selectbox("Region", ["us-east", "us-west", "europe"])

        settings = {"region": region}

        if resource == "bucket":
            settings["public_access"] = st.checkbox("Public Access")
            settings["versioning"] = st.checkbox("Versioning")
        elif resource == "server":
            settings["size"] = st.select_slider(
                "Server Size", options=["small", "medium"]
            )

        if st.button("Generate Config & Deploy"):
            config = {
                "cloud": cloud,
                "resource": resource,
                "name": name,
                "settings": settings,
            }
            with open("simpleform.yaml", "w") as f:
                yaml.dump(config, f)
            st.success("simpleform.yaml updated!")

            # Trigger Pulumi Up
            st.info("Starting Deployment... check logs below.")
            process = subprocess.Popen(
                ["pulumi", "up", "--yes"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            log_area = st.empty()
            full_log = ""
            for line in process.stdout:
                full_log += line
                log_area.code(full_log)

    # --- DESTROY LOGIC ---
    if action == "Destroy":
        st.warning("⚠️ This will delete ALL managed infrastructure.")
        if st.button("🔥 Confirm Destruction"):
            st.info("Destroying infrastructure...")
            process = subprocess.Popen(
                ["pulumi", "destroy", "--yes"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            log_area = st.empty()
            full_log = ""
            for line in process.stdout:
                full_log += line
                log_area.code(full_log)
            st.success("Infrastructure cleanup complete.")

# --- MAIN AREA: DOCUMENTATION ---
st.write("### How it works")
st.markdown(
    """
1. **Define Intent**: Use the sidebar to specify what you want to build.
2. **Abstract**: Simpleform translates your choices into a provider-agnostic YAML.
3. **Orchestrate**: Pulumi handles the heavy lifting of VPCs, Subnets, and Instances.
"""
)

if os.path.exists("simpleform.yaml"):
    st.write("#### Current Configuration (`simpleform.yaml`) ")
    with open("simpleform.yaml", "r") as f:
        st.code(f.read(), language="yaml")
