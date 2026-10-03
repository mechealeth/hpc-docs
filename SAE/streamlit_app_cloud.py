"""
Cloud-deployable four-domain view -- reads ONLY the precomputed JSON
bundle built by export_precomputed_fourdomain.py. No torch, no
checkpoint, no HPC filesystem access needed. Safe to deploy on Streamlit
Community Cloud.

Local test:
    streamlit run streamlit_app_fourdomain_cloud.py

Deploy: push this file + precomputed_fourdomain.json to a GitHub repo,
connect that repo at https://share.streamlit.io
"""

import json, os
import streamlit as st
import py3Dmol
from stmol import showmol

st.set_page_config(page_title="Four-Domain Feature Explorer", layout="wide")

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "precomputed_fourdomain.json")


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


st.title("Four-Domain Feature Explorer")
st.caption("Precomputed, self-contained -- no live HPC connection needed. Shared fixed scale across all 4 panels.")

if not os.path.exists(DATA_PATH):
    st.error(f"precomputed_fourdomain.json not found at {DATA_PATH} -- "
            f"make sure it's uploaded in the SAME folder as this script.")
    st.stop()
bundle = load_bundle(DATA_PATH)

st.write(f"Feature **{bundle['feature']}**, shown across all 4 domains")

max_scale = st.sidebar.number_input(
    "Fixed activation scale (SAME for all 4 panels)", value=1.0, step=0.1, min_value=0.01,
    help="Not auto-computed -- check each panel's real max (shown underneath) and set this to a sensible "
         "value so color intensity is genuinely comparable across domains, not independently stretched.")

max_timesteps = max(len(d["designs"][0]["timesteps"]) for d in bundle["domains"].values() if d["designs"])
t_idx_shared = st.slider("Shared timestep index (applies to all 4 panels)", 0, max_timesteps - 1, max_timesteps - 1)

cols = st.columns(4)
for col, (domain, ddata) in zip(cols, bundle["domains"].items()):
    with col:
        st.subheader(domain)
        if not ddata["designs"]:
            st.error("No designs in bundle for this domain")
            continue
        design_names = [d["design"] for d in ddata["designs"]]
        design_name = st.selectbox(f"Design ({len(design_names)} available)", design_names, key=f"design_{domain}")
        design = next(d for d in ddata["designs"] if d["design"] == design_name)
        target_len = ddata["target_len"]

        t_idx = min(t_idx_shared, len(design["timesteps"]) - 1)
        t = str(design["timesteps"][t_idx])
        activation = design["trajectory"].get(t, {})
        real_max_here = max(activation.values()) if activation else 0

        view = py3Dmol.view(width=280, height=260)
        view.addModel(design["pdb_text"], "pdb")
        view.setStyle({"chain": "A"}, {"cartoon": {"color": "grey"}})
        view.setStyle({"chain": "B"}, {"cartoon": {"color": "lightblue"}})
        view.addStyle({"chain": "B"}, {"stick": {"color": "lightblue", "radius": 0.15}})

        for resi_str, val in activation.items():
            resi = int(resi_str)
            norm = min(val / max_scale, 1.0) if max_scale > 0 else 0
            if norm > 0.02:
                is_target = resi < target_len
                chain = "A" if is_target else "B"
                local_resi = resi if is_target else resi - target_len
                color = activation_to_color(norm, "teal" if is_target else "coral")
                view.setStyle({"chain": chain, "resi": local_resi + 1}, {"cartoon": {"color": color}})
        view.zoomTo()
        showmol(view, height=260, width=280)

        st.caption(f"step {t} -- real max: {real_max_here:.2f} "
                  f"({'clipped' if real_max_here > max_scale else 'within range'} at scale {max_scale:.2f})")

st.caption("Teal = target-side, coral = binder-side. All 4 panels share the SAME fixed scale -- "
          "a brighter panel genuinely means higher real activation.")
