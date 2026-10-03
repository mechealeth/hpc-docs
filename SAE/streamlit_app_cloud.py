"""
Cloud-deployable version -- reads ONLY the precomputed JSON bundle built
by export_precomputed_dataset.py. No torch, no checkpoint, no HPC
filesystem access needed. Safe to deploy on Streamlit Community Cloud.

Local test:
    streamlit run streamlit_app_cloud.py

Deploy: push this file + precomputed_dataset.json to a GitHub repo, then
connect that repo at https://share.streamlit.io (free tier).
"""

import json, os
import streamlit as st
import py3Dmol
from stmol import showmol

# Resolve relative to THIS SCRIPT'S folder, not the process's current
# working directory -- Streamlit Cloud's cwd doesn't necessarily match
# where the script file lives, which is what caused the FileNotFoundError.
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "precomputed_dataset.json")

st.set_page_config(page_title="SAE Feature Activation Explorer", layout="wide")


def activation_to_color(norm, base="teal"):
    if base == "teal":
        r = int(46 + norm * (15 - 46)); g = int(58 + norm * (102 - 58)); b = int(82 + norm * (87 - 82))
    else:
        r = int(46 + norm * (224 - 46)); g = int(58 + norm * (99 - 58)); b = int(82 + norm * (79 - 82))
    return f"0x{r:02x}{g:02x}{b:02x}"


@st.cache_data
def load_bundle(path):
    with open(path) as f:
        return json.load(f)


st.title("SAE Feature Activation Explorer")
st.caption("Precomputed, self-contained -- no live HPC connection needed.")

if not os.path.exists(DATA_PATH):
    st.error(f"precomputed_dataset.json not found at {DATA_PATH} -- "
            f"make sure it's uploaded in the SAME folder as this script in your repo.")
    st.stop()
bundle = load_bundle(DATA_PATH)
st.write(f"Domain: **{bundle['domain']}** -- target feature **{bundle['target_feature']}**, "
        f"binder feature **{bundle['binder_feature']}**")

design_names = [d["design"] for d in bundle["designs"]]
col1, col2 = st.columns(2)
with col1:
    design_name = st.selectbox("Design", design_names)
design = next(d for d in bundle["designs"] if d["design"] == design_name)

with col2:
    t_idx = st.select_slider("Timestep", options=list(range(len(design["timesteps"]))),
                             format_func=lambda i: f"step {design['timesteps'][i]}",
                             value=len(design["timesteps"]) - 1)
t = str(design["timesteps"][t_idx])

target_activation = design["trajectory_target"].get(t, {})
binder_activation = design["trajectory_binder"].get(t, {})
max_t = max(target_activation.values()) if target_activation else 0
max_b = max(binder_activation.values()) if binder_activation else 0
st.write(f"timestep {t} -- max target activation: {max_t:.3f}, max binder activation: {max_b:.3f}")

view = py3Dmol.view(width=700, height=500)
view.addModel(design["pdb_text"], "pdb")
view.setStyle({"chain": "A"}, {"cartoon": {"color": "grey"}})
view.setStyle({"chain": "B"}, {"cartoon": {"color": "lightblue"}})
view.addStyle({"chain": "B"}, {"stick": {"color": "lightblue", "radius": 0.15}})

for resi, val in target_activation.items():
    norm = val / max_t if max_t > 0 else 0
    if norm > 0.02:
        view.setStyle({"chain": "A", "resi": int(resi) + 1}, {"cartoon": {"color": activation_to_color(norm, "teal")}})
for resi, val in binder_activation.items():
    norm = val / max_b if max_b > 0 else 0
    if norm > 0.02:
        view.setStyle({"chain": "B", "resi": int(resi) + 1}, {"cartoon": {"color": activation_to_color(norm, "coral")}})
view.zoomTo()

showmol(view, height=500, width=700)
st.caption("Teal = target feature, coral = binder feature. Grey/light blue = baseline.")
