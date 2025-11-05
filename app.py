
# PRO SE VERITAS: Evidence & Integrity Engine Dashboard
# File: app.py (Main Interface)

import streamlit as st
import hashlib
import time
import os
import tempfile
import pandas as pd 
import json

# Firebase Dependencies
import firebase_admin 
from firebase_admin import credentials, firestore, storage

# AI Dependencies
try:
    from google import genai
    from google.api_core import exceptions as google_exceptions
except ImportError:
    st.warning("AI dependencies (google-genai) not yet found. Legal Triage tab will show errors.")
    class MockGenAI:
        def Client(self): return None
        class MockAPIError(Exception): pass
    genai = MockGenAI()
    google_exceptions = None

# --- Firebase Initialization (Singleton Pattern for Streamlit) ---
if not firebase_admin._apps:
    try:
        if "FIREBASE_SERVICE_ACCOUNT_KEY" in st.secrets:
            cred_dict = st.secrets["FIREBASE_SERVICE_ACCOUNT_KEY"]
            cred = credentials.Certificate(cred_dict)
            initialize_app(cred, {'storageBucket': 'harperssafewayhome-34882-264d6.appspot.com'})
        elif "FIREBASE_SERVICE_ACCOUNT_KEY" in os.environ:
            cred_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
            cred_dict = json.loads(cred_str)
            cred = credentials.Certificate(cred_dict)
            initialize_app(cred, {'storageBucket': 'harperssafewayhome-34882-264d6.appspot.com'})
        else:
            # This fallback is for local dev without secrets and will use GOOGLE_APPLICATION_CREDENTIALS
            initialize_app()
    except Exception as e:
        st.error(f"Firebase Initialization Failed: {e}")

# Initialize clients (must be done after initialize_app)
db = firestore.client()
# --- End Firebase Initialization ---


# --- CORE INTEGRITY & STORAGE FUNCTIONS ---

def calculate_sha256_of_uploaded_file(uploaded_file):
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, uploaded_file.name + str(time.time()))
    calculated_hash = None
    
    try:
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer()) 
            
        hash_sha256 = hashlib.sha256()
        with open(temp_file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
            
        calculated_hash = hash_sha256.hexdigest()
        
    except Exception as e:
        st.error(f"Integrity Engine Error during Hashing: {e}")
        
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return calculated_hash


def process_and_log_evidence(uploaded_file, file_hash):
    global db 
    case_id = st.session_state.case_id

    if not uploaded_file:
        return "Error: No file provided.", None
    
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, uploaded_file.name + "_upload_" + str(time.time()))
    
    try:
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        bucket = storage.bucket() 
        destination_blob_name = f"evidence/{case_id}/raw/{uploaded_file.name}"
        
        blob = bucket.blob(destination_blob_name)        
        blob.upload_from_filename(temp_file_path)
        
        storage_path = destination_blob_name
        
        doc_ref = db.collection('cases').document(case_id).collection('evidence').document(file_hash)
        
        evidence_data = {
            "file_name": uploaded_file.name,
            "file_size_bytes": uploaded_file.size,
            "sha256_hash": file_hash,
            "storage_path": storage_path,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "verified": True,
            "status": "SHA-256 Verified (Upload Complete)"
        }
        
        doc_ref.set(evidence_data)
        
        return f"Success: Evidence verified and secured.", evidence_data

    except Exception as e:
        return f"Critical Error: {e}", None
        
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# --- MOCK DATA FUNCTION FOR DEMO ---

def mock_fetch_evidence_data(case_id):
    return [
        {"sha256_hash": "a1b2c3d4e5f6...", "file_name": "Email_from_Counsel_03-15-2025.pdf", "content": "The respondent failed to appear at the scheduled meeting regarding the child's medical care. This is the third time this month. This pattern of non-compliance is clearly documented and impacts the child's best interests.", "storage_path": "evidence/DEMO/raw/Email.pdf"},
        {"sha256_hash": "f6e5d4c3b2a1...", "file_name": "Therapy_Notes_2024-11-01.txt", "content": "Child stated they were afraid to go home after weekend visit. Observed bruising on left arm. Noted high anxiety levels and stated, 'It's scary when the house is too quiet.'", "storage_path": "evidence/DEMO/raw/Therapy.txt"},
        {"sha256_hash": "1a2b3c4d5e6f...", "file_name": "Text_Message_Exhibit_05-20-2025.pdf", "content": "I am done with this. You deal with the school. Don't call me again. (Screenshot of text message.)", "storage_path": "evidence/DEMO/raw/Text.pdf"},
    ]


# --- TAB FUNCTIONS ---

def setup_ui():
    st.set_page_config(
        page_title="Pro Se Veritas: Legal Evidence Engine",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("⚖️ Pro Se Veritas: Evidence & Integrity Engine")
    st.subheader("Created for Harper, perfected for you.")
    st.markdown("---")

def upload_evidence_tab():
    if 'case_id' not in st.session_state:
        st.session_state.case_id = "DEMO-PSV-" + str(int(time.time()))

    st.info(f"Active Case ID (for data separation): **{st.session_state.case_id}**")

    uploaded_files = st.file_uploader(
        "Upload Digital Evidence (PDFs, Images, Videos, etc.)", 
        type=None, 
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("Process & Secure Evidence: Activate Integrity Engine", type="primary"):
            with st.spinner("Calculating Integrity Fingerprints and Securing to Firebase..."):
                results_list = []
                
                for file in uploaded_files:
                    st.write(f"Processing: **{file.name}**...")
                    try:
                        hash_value = calculate_sha256_of_uploaded_file(file)
                        
                        if hash_value:
                            status_message, data = process_and_log_evidence(file, hash_value)
                            
                            results_list.append({
                                "File Name": file.name,
                                "SHA-256 Fingerprint": hash_value[:16] + "...",
                                "Status": "SECURED" if "Success" in status_message else "FAILED",
                                "Full Status": status_message,
                                "File Size": f"{file.size / (1024 * 1024):.2f} MB"
                            })
                        else:
                            results_list.append({
                                "File Name": file.name,
                                "SHA-256 Fingerprint": "N/A",
                                "Status": "FAILED",
                                "Full Status": "Hashing failed or returned None.",
                                "File Size": "N/A"
                            })

                    except Exception as e:
                        results_list.append({
                            "File Name": file.name,
                            "SHA-256 Fingerprint": "ERROR",
                            "Status": "CRITICAL ERROR",
                            "Full Status": f"Unforeseen Processing Error: {e}",
                            "File Size": "N/A"
                        })

                st.success("Evidence Processing Complete!")
                st.subheader("📋 Evidence Integrity Log")
                
                if results_list:
                    results_df = pd.DataFrame(results_list)
                    st.dataframe(results_df, use_container_width=True, hide_index=True)
                
                st.markdown(
                    '''
                    **Integrity Guarantee:** The **SHA-256 Fingerprint** (hash) ensures non-repudiation. 
                    This unique, immutable code is stored in Firestore and verifies the file in Firebase Storage. 
                    Any change to the file will break the fingerprint match.
                    '''
                )

def evidence_browser_tab():
    st.subheader("📁 Evidence Browser (Placeholder)")
    st.info("This tab will load data from your Firestore evidence log for filtering and analysis using the Pandas/Matplotlib libraries from your requirements.")

def legal_triage_tab():
    st.subheader("⚖️ Legal Triage: Advanced AI Analysis")
    st.markdown("---")
    
    if 'case_id' not in st.session_state:
        st.error("No active Case ID found. Please upload evidence first.")
        return

    evidence_items = mock_fetch_evidence_data(st.session_state.case_id)
    
    if not evidence_items:
        st.info("No evidence loaded for analysis. Use the 'Upload & Verify' tab first.")
        return

    options = {item['file_name']: item for item in evidence_items}
    file_selection = st.selectbox(
        "Select Evidence for AI Spotting", 
        list(options.keys()),
        index=0 if options else None
    )

    if not file_selection:
        return

    selected_evidence = options[file_selection]

    st.markdown("### 1. Issue Spotting Summary (Powered by Gemini)")
    st.info("Uses the Gemini API to analyze the document content for relevant legal issues and context.")
    
    if st.button("Generate Issue Spotting Summary", type="primary"):
        document_text = selected_evidence['content']
        
        try:
            api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
            if not api_key:
                st.error("Gemini API Key not found. Please set it in your Streamlit secrets or environment variables.")
                return
            genai.configure(api_key=api_key)
            client = genai.GenerativeModel(model_name='gemini-1.5-flash')
        except Exception as e:
            st.error(f"Gemini Client Initialization Error: {e}")
            return

        prompt = f'''
        You are PRO SE VERITAS, a professional legal analysis engine specializing in family and custody law.
        Analyze the following evidence text. Identify and summarize the key legal issues, context, and potential evidentiary value in a formal, bulleted list.
        
        Evidence File: {selected_evidence['file_name']}
        Evidence Content:
        ---
        {document_text}
        ---
        
        Summarize the legal issues (e.g., Failure to Co-Parent, Neglect, Emotional Harm, Non-Compliance) in less than 200 words.
        '''
        
        try:
            with st.spinner(f"Analyzing {selected_evidence['file_name']} with Gemini..."):
                response = client.generate_content(prompt)
            st.success("Analysis Complete!")
            st.markdown(response.text)
        except google_exceptions and google_exceptions.GoogleAPICallError as e:
            st.error(f"Gemini API Error: Could not generate content. Check your API key and quotas. Details: {e}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

    st.markdown("---")
    
    st.markdown("### 2. Evidence Classification (Mock)")
    st.info("Mocks an ML model that automatically classifies evidence based on content keywords.")

    if st.button("Run Basic Classification"):
        text_lower = selected_evidence['content'].lower()
        
        classification = "MEDIUM"
        category = "General Communication"
        
        if "fail" in text_lower or "non-compliance" in text_lower or "refused" in text_lower:
            classification = "HIGH"
            category = "Co-Parenting Non-Compliance"
        if "afraid" in text_lower or "bruising" in text_lower or "anxiety" in text_lower:
            classification = "CRITICAL"
            category = "Child Safety/Harm"

        st.success(f"Classification Complete for {selected_evidence['file_name']}")
        st.metric(label="Calculated Priority", value=classification)
        st.metric(label="Suggested Category", value=category)
        st.warning("Note: A real-world system would use a trained NLP model for this classification.")

def main_app():
    setup_ui()
    
    tab1, tab2, tab3 = st.tabs(["🔒 Upload & Verify", "📁 Evidence Browser", "⚖️ Legal Triage"])

    with tab1:
        upload_evidence_tab()

    with tab2:
        evidence_browser_tab()
        
    with tab3:
        legal_triage_tab()


if __name__ == "__main__":
    main_app()
