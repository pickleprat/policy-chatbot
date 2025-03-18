import streamlit as st
import os
import tempfile
from PyPDF2 import PdfReader
import anthropic
import openai

def get_client(org: str): 
    openai.OpenAI()

# Configure page
st.set_page_config(page_title="Policy Assistant", layout="wide")

# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = []
if "policy_text" not in st.session_state:
    st.session_state.policy_text = ""
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

# Title and description
st.title("Policy Compliance Assistant")
st.markdown("""
Upload a PDF containing your organization's policies, then ask questions about whether 
specific actions comply with these policies. The AI will analyze your request against the policies.
""")

# Sidebar for PDF upload
with st.sidebar:
    st.header("Upload Policy Document")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None and not st.session_state.file_uploaded:
        with st.spinner("Processing policy document..."):
            # Save the uploaded file to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            # Extract text from the PDF
            policy_text = extract_text_from_pdf(tmp_path)
            
            # Clean up the temporary file
            os.unlink(tmp_path)
            
            # Store the extracted text in session state
            st.session_state.policy_text = policy_text
            st.session_state.file_uploaded = True
            
            # Display confirmation
            st.success("Policy document uploaded and processed successfully!")
            
            # Display a preview of the extracted text
            with st.expander("View extracted policy text"):
                st.text_area("Policy Content", policy_text, height=300, disabled=True)
    
    if st.session_state.file_uploaded:
        if st.button("Clear uploaded document"):
            st.session_state.policy_text = ""
            st.session_state.file_uploaded = False
            st.session_state.messages = []
            st.experimental_rerun()

# Main chat interface
if st.session_state.file_uploaded:
    st.header("Chat with the Policy Assistant")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Get user input
    if prompt := st.chat_input("Ask if your action complies with the policies..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message in chat message container
        with st.chat_message("user"):
            st.write(prompt)
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            with st.spinner("Analyzing policies..."):
                # Load environment variables
                api_key = os.environ.get("ANTHROPIC_API_KEY", st.secrets.get("ANTHROPIC_API_KEY", None))
                
                if not api_key:
                    st.error("API key not found. Please set the ANTHROPIC_API_KEY environment variable or in Streamlit secrets.")
                    st.stop()
                
                client = anthropic.Anthropic(api_key=api_key)
                
                system_prompt = f"""
                You are a helpful policy compliance assistant. Your role is to analyze user requests and determine 
                if they comply with the organization's policies. Here are the policies you should reference:
                
                {st.session_state.policy_text}
                
                When a user asks if a certain action is allowed, you should:
                1. Carefully analyze if the action complies with or violates the policies
                2. Provide a clear YES or NO determination at the beginning of your response
                3. Cite specific relevant sections from the policy document
                4. Explain your reasoning
                
                If the policy document doesn't address the specific situation, clearly state that the policies
                are silent on this matter and provide your best recommendation based on similar policies.
                """
                
                # Prepare the messages
                messages = [
                    {"role": "system", "content": system_prompt},
                ]
                
                # Add previous conversation for context (limiting to last 10 messages)
                for msg in st.session_state.messages[-10:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                
                # Get response from Claude
                response = client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1024,
                    temperature=0,
                    system=system_prompt,
                    messages=[
                        {"role": msg["role"], "content": msg["content"]} 
                        for msg in st.session_state.messages[-10:]
                    ]
                )
                
                assistant_response = response.content[0].text
                st.write(assistant_response)
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
else:
    st.info("Please upload a policy document to start the conversation.")

# Display instructions at the bottom
st.markdown("---")
st.markdown("""
### How to use this application:
1. Upload your organization's policy document (PDF format) using the sidebar
2. Ask questions like: "Can I use company equipment for personal projects?" or "Is it allowed to share customer data with third parties?"
3. The AI will analyze your request against the policies and provide a determination with explanation
""")

# Add setup instructions in the expander
with st.expander("Setup Instructions"):
    st.markdown("""
    #### Environment Setup
    
    To run this application, you need an Anthropic API key for Claude. You can set it up in two ways:
    
    1. **Environment Variable**: Set `ANTHROPIC_API_KEY` as an environment variable.
    2. **Streamlit Secrets**: Add the following to your `.streamlit/secrets.toml` file:
       ```toml
       ANTHROPIC_API_KEY = "your-api-key"
       ```
    
    #### Required Packages
    
    Install the required packages with:
    ```
    pip install streamlit anthropic PyPDF2
    ```
    
    #### Running the Application
    
    Run the application with:
    ```
    streamlit run app.py
    ```
    """)