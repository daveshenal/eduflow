import PyPDF2

# Path to the protected PDF and the output PDF
input_pdf_path = "protected.pdf"
output_pdf_path = "unprotected.pdf"
password = "your_password"

# Open the PDF
with open(input_pdf_path, "rb") as file:
    reader = PyPDF2.PdfReader(file)
    
    # Decrypt the PDF
    if reader.is_encrypted:
        reader.decrypt(password)
    
    # Create a writer for the output file
    writer = PyPDF2.PdfWriter()
    
    # Add all pages to the writer
    for page in reader.pages:
        writer.add_page(page)
    
    # Write the unprotected PDF
    with open(output_pdf_path, "wb") as output_file:
        writer.write(output_file)

print(f"Password removed and saved as {output_pdf_path}")
