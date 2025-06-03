import streamlit as st

st.title("Testing Secrets")

# This should print your key
st.write("Mediastack API Key:", st.secrets["mediastack"]["MEDIASTACK_API_KEY"])
