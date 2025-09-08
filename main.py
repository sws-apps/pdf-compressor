from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import tempfile
import os
import subprocess
from pathlib import Path
from PyPDF2 import PdfMerger
import shutil
import io

app = FastAPI()

# Mount static files if directory exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def serve_index():
    try:
        with open("static/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>PDF Compressor API is running</h1><p>Static files not found. Please check deployment.</p>")

@app.get("/health")
async def health_check():
    # Check if Ghostscript is available
    gs_path = shutil.which("gs") or shutil.which("ghostscript")
    gs_available = gs_path is not None
    return {
        "status": "ok",
        "ghostscript_available": gs_available,
        "ghostscript_path": gs_path
    }

def cleanup_temp_dir(temp_dir: Path):
    """Background task to clean up temporary directory"""
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except:
        pass

@app.post("/process")
async def process_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    max_size_mb: float = Form(default=2.0)
):
    # Enforce maximum size limit of 5MB
    if max_size_mb > 5.0:
        max_size_mb = 5.0
    elif max_size_mb < 0.1:
        max_size_mb = 0.1
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
        
        # Merge PDFs if multiple, or just use single file
        if len(pdf_files) == 1:
            # Single file, just copy it
            merged_path = temp_dir / "merged.pdf"
            shutil.copy2(pdf_files[0], merged_path)
        else:
            # Multiple files, merge them
            merger = PdfMerger()
            for pdf_file in pdf_files:
                try:
                    merger.append(str(pdf_file))
                except Exception as e:
                    print(f"Error merging {pdf_file}: {e}")
                    continue
            
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
            # Try to find gs in different locations
            gs_path = shutil.which("gs") or shutil.which("ghostscript") or "/usr/bin/gs"
            
            # Verify Ghostscript exists
            if not gs_path or not os.path.exists(gs_path):
                print(f"Ghostscript not found at {gs_path}")
                # If no Ghostscript, just copy the file
                shutil.copy2(input_path, output_path)
                return
            
            cmd = [
                gs_path,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                f"-dPDFSETTINGS=/{quality}",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                "-dPrinted=false",
                "-dSAFER",
                f"-sOutputFile={output_path}",
                str(input_path)
            ]
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Ghostscript stderr: {result.stderr}")
                print(f"Ghostscript stdout: {result.stdout}")
                # If compression fails, copy original
                shutil.copy2(input_path, output_path)
        
        # Try /ebook first
        compress_pdf(merged_path, compressed_path, "ebook")
        
        # Check file size and fallback to /screen if needed
        file_size_mb = compressed_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            compress_pdf(merged_path, compressed_path, "screen")
        
        # Verify compressed file exists
        if not compressed_path.exists():
            print("Compressed file doesn't exist, using merged file")
            compressed_path = merged_path
        
        # Verify file has content
        file_size = compressed_path.stat().st_size
        if file_size == 0:
            return {"error": "Compressed PDF is empty"}
        
        print(f"Sending PDF file: {compressed_path}, size: {file_size} bytes")
        
        # Read the compressed PDF into memory
        with open(compressed_path, 'rb') as f:
            pdf_content = f.read()
        
        # Verify content was read
        if not pdf_content:
            return {"error": "Failed to read PDF content"}
        
        # Schedule cleanup for after response is sent
        background_tasks.add_task(cleanup_temp_dir, temp_dir)
        
        # Return the PDF as a streaming response
        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=compressed.pdf",
                "Content-Length": str(len(pdf_content)),
                "Cache-Control": "no-cache"
            }
        )
        
    except subprocess.CalledProcessError as e:
        # Clean up on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"error": f"PDF compression failed: {str(e)}"}
    except Exception as e:
        # Clean up on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"error": f"An error occurred: {str(e)}"}