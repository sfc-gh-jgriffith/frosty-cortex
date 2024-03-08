import streamlit as st 

import re

from snowflake.snowpark.session import Session 
from snowflake.ml.utils import connection_params
from snowflake.cortex import Complete

from prompts import get_system_prompt, get_summary_prompt

params = connection_params.SnowflakeLoginOptions("demo_jgriffith3")

@st.cache_resource
def get_snowflake_connection():
    session = Session.builder.configs(params).create()
    return session

session = get_snowflake_connection()
st.title("☃️ Frosty")

# Initialize the chat messages history

with st.sidebar:
    if st.button("Start Over"):
        del st.session_state["messages"]
    
    show_sql = st.checkbox("Show SQL", value=True)


if "messages" not in st.session_state:
    # system prompt includes table information, rules, and prompts the LLM to produce
    # a welcome message to the user.
    st.session_state.messages = [{"role": "system", "content": get_system_prompt(session)}]

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

# display the existing chat messages
message_counter = 0
for message in st.session_state.messages:
    if message["role"] == "system":
        continue

    with st.chat_message(message["role"]):
        if show_sql or (message["role"] == "user") or (message_counter == 0):
            st.write(message["content"])
        
        # give option to get data summary from LLM
        if "results" in message:
            st.dataframe(message["results"])
            if st.button("Summarize", key=f"summarize_message_{message_counter}"):
                
                summary = Complete("mistral-large", 
                                   get_summary_prompt(session, 
                                                      data=message["results"], 
                                                      context=message["content"]
                                                     )
                                 )
                st.write(summary)
    message_counter += 1

# If last message is not from assistant, we need to generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        resp_container = st.empty()
        messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        
        response = Complete('mistral-large', str(messages))

        resp_container.markdown(response)

        message = {"role": "assistant", "content": response}
        
        # Parse the response for a SQL query and execute if available
        if st.session_state.messages[-1]["role"] != "system":
            sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
            
            if sql_match:
                sql = sql_match.group(1)
                
                if sql[-1] == ';':
                    sql = sql[:-1]

                message["results"] = session.sql(sql)
                st.dataframe(message["results"])
        
        st.session_state.messages.append(message)
       

        