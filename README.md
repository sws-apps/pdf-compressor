# PDF Compressor

A web application for merging and compressing multiple PDF files with a clean, user-friendly interface.

## Features

- **Drag & Drop Interface**: Easily upload multiple PDF files
- **PDF Merging**: Combine multiple PDFs into a single document
- **Smart Compression**: Automatically adjusts compression level based on target file size
- **Customizable Size Limit**: Set maximum output file size (0.1 - 50 MB)
- **Real-time Progress**: Visual feedback during processing
- **Error Handling**: Comprehensive validation and error messages

## Requirements

- Python 3.9+
- Ghostscript (for PDF compression)

### Installing Ghostscript

**macOS:**
```bash
brew install ghostscript
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ghostscript
```

**Windows:**
Download and install from [Ghostscript official website](https://www.ghostscript.com/download/gsdnld.html)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pdf-compressor
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running Locally

Start the server:
```bash
uvicorn main:app --reload --port 8000
```

Open your browser and navigate to `http://localhost:8000`

### Deploying to Production

The application includes a `Procfile` for easy deployment to platforms like Heroku or Railway.

For Heroku deployment:
```bash
heroku create your-app-name
heroku buildpacks:add heroku/python
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-apt
git push heroku main
```

Create an `Aptfile` in the root directory with:
```
ghostscript
```

## API Endpoints

### `GET /health`
Health check endpoint

**Response:**
```json
{
  "status": "ok"
}
```

### `POST /process`
Process and compress PDF files

**Parameters:**
- `files`: Multiple PDF files (multipart/form-data)
- `max_size_mb`: Target maximum file size in MB (default: 5.0)

**Response:**
- Success: Returns compressed PDF file as download
- Error: JSON with error message

## Project Structure

```
pdf-compressor/
├── main.py              # FastAPI application
├── static/
│   └── index.html       # Frontend interface
├── requirements.txt     # Python dependencies
├── Procfile            # Deployment configuration
├── .gitignore          # Git ignore rules
└── README.md           # Documentation
```

## Compression Levels

The application uses two compression levels:
- **ebook**: Medium compression, better quality (tried first)
- **screen**: High compression, lower quality (fallback if file exceeds target size)

## Security Features

- File size validation (max 100MB per file)
- PDF file type validation
- Temporary file cleanup after processing
- CORS middleware for secure cross-origin requests

## Error Handling

The application handles various error scenarios:
- Empty or invalid files
- Non-PDF files
- Oversized files
- Ghostscript compression failures
- Server processing errors

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.