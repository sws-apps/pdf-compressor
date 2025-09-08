from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import tempfile
import os
import subprocess
from pathlib import Path
from PyPDF2 import PdfMerger

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def serve_index():
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/process")
async def process_pdfs(
    files: List[UploadFile] = File(...),
    max_size_mb: float = Form(default=5.0)
):
    if not files:
        return {"error": "No files provided"}
    
    temp_dir = Path(tempfile.mkdtemp())
    pdf_files = []
    
    try:
        # Validate file size and type
        MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB per file
        
        for file in files:
            if not file.filename:
                continue
                
            if not file.filename.lower().endswith('.pdf'):
                return {"error": f"File '{file.filename}' is not a PDF"}
            
            # Read file content
            content = await file.read()
            
            if len(content) > MAX_UPLOAD_SIZE:
                return {"error": f"File '{file.filename}' exceeds maximum size of 100MB"}
            
            if len(content) == 0:
                return {"error": f"File '{file.filename}' is empty"}
            
            # Save file
            file_path = temp_dir / file.filename
            with open(file_path, 'wb') as f:
                f.write(content)
            pdf_files.append(file_path)
        
        if not pdf_files:
            return {"error": "No valid PDF files uploaded"}
        
        # Merge PDFs
        merger = PdfMerger()
        for pdf_file in pdf_files:
            merger.append(str(pdf_file))
        
        # Save merged PDF
        merged_path = temp_dir / "merged.pdf"
        merger.write(str(merged_path))
        merger.close()
        
        # Check if merged file exists and has content
        if not merged_path.exists() or merged_path.stat().st_size == 0:
            return {"error": "Failed to merge PDF files"}
        
        # Compress PDF using Ghostscript
        compressed_path = temp_dir / "compressed.pdf"
        
        # Function to compress with specific quality setting
        def compress_pdf(input_path, output_path, quality):
            # Use full path to gs
            gs_path = "/opt/homebrew/bin/gs"
            cmd = [
                gs_path,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                f"-dPDFSETTINGS=/{quality}",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                f"-sOutputFile={output_path}",
                str(input_path)
            ]
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Ghostscript stderr: {result.stderr}")
                print(f"Ghostscript stdout: {result.stdout}")
                raise Exception(f"Ghostscript error: {result.stderr}")
        
        # Try /ebook first
        compress_pdf(merged_path, compressed_path, "ebook")
        
        # Check file size and fallback to /screen if needed
        file_size_mb = compressed_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            compress_pdf(merged_path, compressed_path, "screen")
        
        # Verify compressed file exists
        if not compressed_path.exists():
            return {"error": "Failed to compress PDF"}
        
        # Return compressed PDF as file response
        return FileResponse(
            path=str(compressed_path),
            media_type="application/pdf",
            filename="compressed.pdf",
            headers={
                "Content-Disposition": "attachment; filename=compressed.pdf"
            }
        )
        
    except subprocess.CalledProcessError as e:
        return {"error": f"PDF compression failed: {str(e)}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
    finally:
        # Clean up temp files after response is sent
        import atexit
        import shutil
        atexit.register(lambda: shutil.rmtree(temp_dir, ignore_errors=True))