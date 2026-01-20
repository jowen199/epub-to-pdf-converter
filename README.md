# EPUB to PDF Converter

A portable Mac app for bulk converting EPUB files to PDF with a modern queue-based interface.

![macOS](https://img.shields.io/badge/macOS-10.15+-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)

## Features

- 📚 **Bulk Conversion** - Convert multiple EPUB files at once
- 📊 **Progress Tracking** - See real-time progress for each file
- 📋 **Queue Management** - Add, remove, and track files in the queue
- 🎨 **Modern Dark UI** - Beautiful Catppuccin-inspired interface
- 📁 **Flexible Output** - Save to source directory or custom location
- 🚀 **Portable App** - Runs as a standalone Mac application

## Quick Start

### Option 1: Run Directly with Python

1. **Install dependencies:**
   ```bash
   cd epub-to-pdf-converter
   pip3 install -r requirements.txt
   ```

2. **Run the app:**
   ```bash
   python3 app.py
   ```

### Option 2: Create Portable App Bundle

1. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Create the app:**
   ```bash
   python3 setup_app.py
   ```

3. **Run the app:**
   ```bash
   open "dist/EPUB to PDF Converter.app"
   ```
   
   Or double-click the app in Finder.

## Usage

1. **Add Files** - Click "Add EPUB Files" button or drag & drop EPUB files
2. **Set Output** (Optional) - Click "Change" to select a custom output directory
3. **Monitor Progress** - Watch the queue as files are converted
4. **Clear Completed** - Use "Clear All" to remove finished conversions

## File Structure

```
epub-to-pdf-converter/
├── app.py              # Main GUI application
├── converter.py        # EPUB to PDF conversion logic
├── setup_app.py        # Script to create Mac .app bundle
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Requirements

- macOS 10.15 (Catalina) or later
- Python 3.8+
- Dependencies (installed automatically):
  - customtkinter - Modern UI toolkit
  - ebooklib - EPUB parsing
  - weasyprint - PDF generation
  - beautifulsoup4 - HTML processing
  - lxml - XML/HTML parsing
  - Pillow - Image processing

## Troubleshooting

### WeasyPrint Installation Issues

WeasyPrint requires some system libraries. Install via Homebrew:

```bash
brew install pango cairo gdk-pixbuf libffi
```

### App Won't Open

If macOS blocks the app:
1. Right-click the app → Open
2. Or: System Preferences → Security & Privacy → Allow

### Conversion Fails

- Ensure the EPUB file is not corrupted
- Check that you have write permissions to the output directory
- Some DRM-protected EPUBs cannot be converted

## License

MIT License - Feel free to modify and distribute.

