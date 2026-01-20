"""
EPUB to PDF Converter - Core conversion logic
"""
import os
import re
import base64
import tempfile
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import unquote

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from weasyprint import HTML, CSS
from PIL import Image
import io


class EPUBConverter:
    """Handles conversion of EPUB files to PDF"""
    
    def __init__(self, progress_callback: Optional[Callable[[float, str], None]] = None):
        self.progress_callback = progress_callback
        
    def _report_progress(self, progress: float, message: str):
        """Report progress to callback if available"""
        if self.progress_callback:
            self.progress_callback(progress, message)
    
    def _extract_images(self, book: epub.EpubBook) -> dict:
        """Extract all images from EPUB and return as base64 encoded dict"""
        images = {}
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                img_name = item.get_name()
                img_data = item.get_content()
                
                # Convert image to base64 for embedding
                img_ext = Path(img_name).suffix.lower()
                mime_types = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.svg': 'image/svg+xml',
                    '.webp': 'image/webp'
                }
                mime_type = mime_types.get(img_ext, 'image/png')
                
                # Try to optimize large images
                if img_ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    try:
                        img = Image.open(io.BytesIO(img_data))
                        # Resize if too large (max 1200px width for PDF)
                        if img.width > 1200:
                            ratio = 1200 / img.width
                            new_size = (1200, int(img.height * ratio))
                            img = img.resize(new_size, Image.LANCZOS)
                        
                        # Convert to RGB if necessary
                        if img.mode in ('RGBA', 'P'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                            img = background
                        
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=85)
                        img_data = buffer.getvalue()
                        mime_type = 'image/jpeg'
                    except Exception:
                        pass  # Use original image if optimization fails
                
                b64_data = base64.b64encode(img_data).decode('utf-8')
                data_uri = f"data:{mime_type};base64,{b64_data}"
                
                # Store with various path formats for matching
                images[img_name] = data_uri
                images[os.path.basename(img_name)] = data_uri
                # Handle URL-encoded paths
                images[unquote(img_name)] = data_uri
                images[unquote(os.path.basename(img_name))] = data_uri
                
        return images
    
    def _process_html_content(self, html_content: str, images: dict, base_path: str = "") -> str:
        """Process HTML content - fix image references and clean up"""
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Process all images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if not src:
                continue
                
            # Try various path combinations to find the image
            src_variants = [
                src,
                unquote(src),
                os.path.basename(src),
                os.path.basename(unquote(src)),
            ]
            
            if base_path:
                src_variants.extend([
                    os.path.normpath(os.path.join(os.path.dirname(base_path), src)),
                    os.path.normpath(os.path.join(os.path.dirname(base_path), unquote(src))),
                ])
            
            for variant in src_variants:
                # Clean up path
                variant = variant.lstrip('./')
                if variant in images:
                    img['src'] = images[variant]
                    break
        
        # Remove scripts
        for script in soup.find_all('script'):
            script.decompose()
            
        return str(soup)
    
    def _get_base_css(self) -> str:
        """Return base CSS for PDF styling"""
        return """
        @page {
            size: A4;
            margin: 2cm 2.5cm;
            @top-center {
                content: none;
            }
            @bottom-center {
                content: counter(page);
                font-family: 'Georgia', serif;
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Georgia', 'Times New Roman', serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #1a1a1a;
            text-align: justify;
            hyphens: auto;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Helvetica Neue', 'Arial', sans-serif;
            color: #222;
            page-break-after: avoid;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        
        h1 {
            font-size: 24pt;
            text-align: center;
            margin-top: 2em;
            page-break-before: always;
        }
        
        h1:first-of-type {
            page-break-before: avoid;
        }
        
        h2 {
            font-size: 18pt;
            border-bottom: 1px solid #ddd;
            padding-bottom: 0.3em;
        }
        
        h3 {
            font-size: 14pt;
        }
        
        p {
            margin: 0.8em 0;
            orphans: 3;
            widows: 3;
        }
        
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1em auto;
            page-break-inside: avoid;
        }
        
        figure {
            margin: 1.5em 0;
            page-break-inside: avoid;
        }
        
        figcaption {
            font-size: 9pt;
            font-style: italic;
            text-align: center;
            color: #666;
            margin-top: 0.5em;
        }
        
        blockquote {
            margin: 1em 2em;
            padding-left: 1em;
            border-left: 3px solid #ccc;
            font-style: italic;
            color: #444;
        }
        
        pre, code {
            font-family: 'Menlo', 'Monaco', monospace;
            font-size: 9pt;
            background-color: #f5f5f5;
            border-radius: 3px;
        }
        
        pre {
            padding: 1em;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            page-break-inside: avoid;
        }
        
        code {
            padding: 0.2em 0.4em;
        }
        
        a {
            color: #2563eb;
            text-decoration: none;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
            page-break-inside: avoid;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 0.5em;
            text-align: left;
        }
        
        th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        
        ul, ol {
            margin: 0.8em 0;
            padding-left: 2em;
        }
        
        li {
            margin: 0.3em 0;
        }
        
        hr {
            border: none;
            border-top: 1px solid #ddd;
            margin: 2em 0;
        }
        
        .chapter {
            page-break-before: always;
        }
        
        .title-page {
            text-align: center;
            padding-top: 30%;
        }
        
        .title-page h1 {
            font-size: 32pt;
            border: none;
            page-break-before: avoid;
        }
        
        .title-page .author {
            font-size: 16pt;
            margin-top: 2em;
            color: #666;
        }
        """
    
    def convert(self, epub_path: str, output_path: str) -> bool:
        """
        Convert an EPUB file to PDF
        
        Args:
            epub_path: Path to the input EPUB file
            output_path: Path for the output PDF file
            
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            self._report_progress(0.0, "Opening EPUB file...")
            
            # Read the EPUB file
            book = epub.read_epub(epub_path)
            
            self._report_progress(0.1, "Extracting images...")
            
            # Extract images
            images = self._extract_images(book)
            
            self._report_progress(0.2, "Processing chapters...")
            
            # Get book metadata
            title = book.get_metadata('DC', 'title')
            title = title[0][0] if title else Path(epub_path).stem
            
            creator = book.get_metadata('DC', 'creator')
            author = creator[0][0] if creator else ""
            
            # Build combined HTML
            html_parts = []
            
            # Title page
            html_parts.append(f'''
            <div class="title-page">
                <h1>{title}</h1>
                {f'<p class="author">{author}</p>' if author else ''}
            </div>
            ''')
            
            # Get spine items (reading order)
            spine_items = []
            for item_id, linear in book.spine:
                item = book.get_item_with_id(item_id)
                if item:
                    spine_items.append(item)
            
            # Process each chapter/document
            total_items = len(spine_items)
            for idx, item in enumerate(spine_items):
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    progress = 0.2 + (0.5 * (idx / max(total_items, 1)))
                    self._report_progress(progress, f"Processing chapter {idx + 1} of {total_items}...")
                    
                    content = item.get_content().decode('utf-8', errors='ignore')
                    processed = self._process_html_content(content, images, item.get_name())
                    
                    # Extract body content
                    soup = BeautifulSoup(processed, 'lxml')
                    body = soup.find('body')
                    if body:
                        html_parts.append(f'<div class="chapter">{body.decode_contents()}</div>')
                    else:
                        html_parts.append(f'<div class="chapter">{processed}</div>')
            
            self._report_progress(0.7, "Generating PDF...")
            
            # Combine into full HTML document
            full_html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{title}</title>
            </head>
            <body>
                {''.join(html_parts)}
            </body>
            </html>
            '''
            
            # Generate PDF
            html_doc = HTML(string=full_html)
            css = CSS(string=self._get_base_css())
            
            self._report_progress(0.85, "Writing PDF file...")
            
            html_doc.write_pdf(output_path, stylesheets=[css])
            
            self._report_progress(1.0, "Complete!")
            
            return True
            
        except Exception as e:
            self._report_progress(0.0, f"Error: {str(e)}")
            raise


def convert_epub_to_pdf(epub_path: str, output_path: str, 
                        progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
    """
    Convenience function to convert EPUB to PDF
    
    Args:
        epub_path: Path to input EPUB
        output_path: Path for output PDF
        progress_callback: Optional callback for progress updates (progress: 0-1, message: str)
        
    Returns:
        True if successful
    """
    converter = EPUBConverter(progress_callback)
    return converter.convert(epub_path, output_path)

