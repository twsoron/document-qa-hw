import streamlit as st

hw1= st.Page('HW1.py', title = "HW1")
hw2 = st.Page('HW2.py', title = "HW2")
hw3 = st.Page('HW3.py', title = 'HW3', default=True)

nav = st.navigation([hw1, hw2, hw3])
st.set_page_config(page_title= "Homework", initial_sidebar_state="expanded")
nav.run()