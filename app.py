import streamlit as st
import pandas as pd
from pubmed_searcher import PubMedSearcher
from fpdf import FPDF
import io
import zipfile
import math

# Initialize PubMedSearcher instance
searcher = PubMedSearcher()

# App title
st.title("PubMed Article Search")

# Initialize df in session state if it doesn't exist
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

# Step 1: Choose Search Mode
st.subheader("Choose Search Mode")
search_mode = st.radio("Would you like to enter a single query or build a complex query?", 
                       ("Single Query", "Build Complex Query"))

# If Single Query is selected
if search_mode == "Single Query":
    term = st.text_input("Enter your search term (e.g., 'Kawasaki[Title/Abstract] AND Adalimumab[Text]'):")
    if st.button("Search"):
        if term:
            try:
                pubmed_ids = searcher.fetch_all_pubmed_ids(term)
                if pubmed_ids:
                    articles = searcher.fetch_article_details(pubmed_ids)
                    if articles:
                        st.session_state.df = pd.DataFrame(articles)
                        st.write("### Articles Found:")
                        st.dataframe(st.session_state.df)
                    else:
                        st.write("No article details available.")
                else:
                    st.write("No articles found.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

# If Build Complex Query is selected
elif search_mode == "Build Complex Query":
    # Initialize session state for query building
    if 'query_parts' not in st.session_state:
        st.session_state['query_parts'] = []

    st.subheader("Build Your Search Query")

    # Input for query field
    field = st.selectbox("Select Field", ["Title", "Title/Abstract", "Text"])
    term = st.text_input("Enter Search Term")

    # Button to add the term with field
    if st.button("Add Term"):
        if term:
            # Append the field and term to the query list
            st.session_state['query_parts'].append(f"{term}[{field}]")
            st.write(f"Current Query: {' '.join(st.session_state['query_parts'])}")
        else:
            st.warning("Please enter a search term before adding.")

    # Input for adding conditions (AND/OR) between terms
    if st.session_state['query_parts']:
        condition = st.radio("Add Condition", ["AND", "OR"])
        if st.button("Add Condition"):
            # Append the condition to the query list
            st.session_state['query_parts'].append(condition)
            st.write(f"Current Query: {' '.join(st.session_state['query_parts'])}")

    # Button to execute the search
    if st.button("Search PubMed"):
        query = " ".join(st.session_state['query_parts'])
        st.write(f"Executing search for query: {query}")
        
        try:
            pubmed_ids = searcher.fetch_all_pubmed_ids(query)
            if pubmed_ids:
                articles = searcher.fetch_article_details(pubmed_ids)
                if articles:
                    st.session_state.df = pd.DataFrame(articles)
                    st.write("### Articles Found:")
                    st.dataframe(st.session_state.df)
                else:
                    st.write("No article details available.")
            else:
                st.write("No articles found.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

# Function to sanitize text for FPDF
def sanitize_text(text):
    """Sanitize text by removing unsupported characters."""
    return text.encode("latin1", "ignore").decode("latin1")

# Function to create a PDF for a batch of articles
def create_pdf(df, start_index, end_index):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Add content for each article
    for i, row in df.iloc[start_index:end_index].iterrows():
        pdf.cell(200, 10, txt=sanitize_text(f"Article {i + 1}"), ln=True, align="L")
        pdf.multi_cell(0, 10, sanitize_text(f"Title: {row['Title']}"))
        pdf.multi_cell(0, 10, sanitize_text(f"Abstract: {row['Abstract']}"))
        pdf.cell(0, 10, sanitize_text(f"Keywords: {row['Keywords']}"), ln=True)
        pdf.cell(0, 10, sanitize_text(f"Year: {row['Year']}"), ln=True)
        pdf.cell(0, 10, sanitize_text(f"First Author: {row['First Author']}"), ln=True)
        pdf.cell(0, 10, sanitize_text(f"Link: {row['Link']}"), ln=True)
        pdf.cell(0, 10, sanitize_text(f"Access Type: {row['Access Type']}"), ln=True)
        pdf.cell(0, 10, ln=True)  # Blank line between articles
    
    # Save PDF to a bytes buffer
    pdf_buffer = io.BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin1')  # Output as string, encode to bytes
    pdf_buffer.write(pdf_output)
    pdf_buffer.seek(0)
    return pdf_buffer

# Generate and download all PDFs and CSV in a zip file
if not st.session_state.df.empty:
    if st.button("Download All as Zip"):
        with io.BytesIO() as zip_buffer:
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                # Add CSV to the zip file
                csv_data = st.session_state.df.to_csv(index=False, sep=';')
                zip_file.writestr("pubmed_articles.csv", csv_data)

                # Generate and add PDFs in batches of 20 rows
                total_rows = len(st.session_state.df)
                batch_size = 20
                total_batches = math.ceil(total_rows / batch_size)
                
                for batch in range(total_batches):
                    start_index = batch * batch_size
                    end_index = min(start_index + batch_size, total_rows)
                    pdf_buffer = create_pdf(st.session_state.df, start_index, end_index)

                    # Add each PDF batch to the zip file
                    pdf_filename = f"pubmed_articles_batch_{batch + 1}.pdf"
                    zip_file.writestr(pdf_filename, pdf_buffer.getvalue())

            # Prepare zip for download
            zip_buffer.seek(0)
            st.download_button(
                label="Download ZIP",
                data=zip_buffer,
                file_name="pubmed_articles.zip",
                mime="application/zip"
            )
else:
    st.write("No data available to generate PDFs.")
