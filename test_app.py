import streamlit as st

st.set_page_config(page_title="Test App", layout="wide")

st.title("🏥 Test App - Database Connection")

st.write("If you see this, Streamlit is working!")

try:
    from db_manager import DatabaseManager
    st.success("✅ DatabaseManager imported successfully")
    
    dm = DatabaseManager()
    st.success("✅ DatabaseManager initialized")
    
    providers = dm.get_all_providers()
    st.success(f"✅ Database connected - {len(providers)} providers found")
    
    if len(providers) == 0:
        st.info("Loading sample data...")
        dm.load_sample_data()
        providers = dm.get_all_providers()
        st.success(f"✅ Sample data loaded - {len(providers)} providers")
    
    st.subheader("Providers:")
    for p in providers:
        st.write(f"- {p['name']}")
        
except Exception as e:
    st.error(f"❌ Error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
