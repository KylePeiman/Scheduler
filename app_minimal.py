import streamlit as st

st.set_page_config(page_title="Test", layout="wide")

st.title("✅ If you see this, Streamlit is working!")
st.write("Frontend is fully developed.")

if st.button("Click me"):
    st.success("Button clicked!")

st.info("The full app has 6 tabs with provider management, shift management, schedule generation, editing, provider view, and analytics.")
