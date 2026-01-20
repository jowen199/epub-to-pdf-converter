#!/usr/bin/env python3
"""
EPUB to PDF Converter
A portable Mac app for bulk EPUB to PDF conversion with queue management
"""

import os
import sys
import threading
import queue
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum
import uuid

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from converter import convert_epub_to_pdf


class ConversionStatus(Enum):
    PENDING = "pending"
    CONVERTING = "converting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueueItem:
    id: str
    epub_path: str
    output_path: str
    status: ConversionStatus = ConversionStatus.PENDING
    progress: float = 0.0
    message: str = "Waiting..."
    error: Optional[str] = None
    
    @property
    def filename(self) -> str:
        return Path(self.epub_path).name


class ConversionWorker(threading.Thread):
    """Background worker for processing the conversion queue"""
    
    def __init__(self, task_queue: queue.Queue, result_callback):
        super().__init__(daemon=True)
        self.task_queue = task_queue
        self.result_callback = result_callback
        self.running = True
        
    def stop(self):
        self.running = False
        
    def run(self):
        while self.running:
            try:
                item = self.task_queue.get(timeout=0.5)
            except queue.Empty:
                continue
                
            if item is None:
                break
                
            try:
                self.result_callback(item.id, ConversionStatus.CONVERTING, 0.0, "Starting conversion...")
                
                def progress_callback(progress: float, message: str):
                    self.result_callback(item.id, ConversionStatus.CONVERTING, progress, message)
                
                convert_epub_to_pdf(item.epub_path, item.output_path, progress_callback)
                self.result_callback(item.id, ConversionStatus.COMPLETED, 1.0, "Complete!")
                
            except Exception as e:
                self.result_callback(item.id, ConversionStatus.FAILED, 0.0, f"Error: {str(e)}")
                
            finally:
                self.task_queue.task_done()


class QueueItemWidget(ttk.Frame):
    """Widget displaying a single queue item"""
    
    def __init__(self, parent, item: QueueItem, on_remove=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.item = item
        self.on_remove = on_remove
        
        # Configure grid
        self.columnconfigure(1, weight=1)
        
        # Status indicator (colored label)
        self.status_label = ttk.Label(self, text="●", width=2)
        self.status_label.grid(row=0, column=0, rowspan=2, padx=(10, 5), pady=10)
        
        # Filename
        self.filename_label = ttk.Label(
            self, 
            text=item.filename,
            font=('Helvetica', 13, 'bold')
        )
        self.filename_label.grid(row=0, column=1, padx=5, pady=(10, 2), sticky="w")
        
        # Progress frame
        progress_frame = ttk.Frame(self)
        progress_frame.grid(row=1, column=1, padx=5, pady=(2, 10), sticky="ew")
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var,
            maximum=1.0,
            length=300
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        
        # Status message
        self.message_label = ttk.Label(
            progress_frame,
            text=item.message,
            font=('Helvetica', 11)
        )
        self.message_label.grid(row=1, column=0, sticky="w")
        
        # Remove button
        self.remove_btn = ttk.Button(
            self,
            text="✕",
            width=3,
            command=self._on_remove
        )
        self.remove_btn.grid(row=0, column=2, rowspan=2, padx=10, pady=10)
        
        self.update_status(item.status, item.progress, item.message)
        
    def _on_remove(self):
        if self.on_remove:
            self.on_remove(self.item.id)
            
    def update_status(self, status: ConversionStatus, progress: float, message: str):
        """Update the visual state based on status"""
        self.item.status = status
        self.item.progress = progress
        self.item.message = message
        
        self.progress_var.set(progress)
        self.message_label.configure(text=message)
        
        # Update status indicator
        status_symbols = {
            ConversionStatus.PENDING: ("●", "gray"),
            ConversionStatus.CONVERTING: ("●", "blue"),
            ConversionStatus.COMPLETED: ("✓", "green"),
            ConversionStatus.FAILED: ("✗", "red")
        }
        symbol, color = status_symbols.get(status, ("●", "gray"))
        self.status_label.configure(text=symbol, foreground=color)
        
        # Enable/disable remove button
        if status == ConversionStatus.CONVERTING:
            self.remove_btn.configure(state="disabled")
        else:
            self.remove_btn.configure(state="normal")


class EPUBtoPDFApp(tk.Tk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.title("EPUB → PDF Converter")
        self.geometry("750x700")
        self.minsize(600, 500)
        
        # Queue management
        self.queue_items: dict[str, QueueItem] = {}
        self.item_widgets: dict[str, QueueItemWidget] = {}
        self.task_queue = queue.Queue()
        self.output_directory: Optional[str] = None
        
        # Start worker thread
        self.worker = ConversionWorker(self.task_queue, self._on_conversion_update)
        self.worker.start()
        
        self._setup_styles()
        self._create_ui()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        
    def _setup_styles(self):
        """Setup ttk styles"""
        style = ttk.Style()
        style.theme_use('aqua')  # Use macOS native theme
        
    def _create_ui(self):
        """Create the user interface"""
        
        # Main container
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header_frame.columnconfigure(0, weight=1)
        
        title_label = ttk.Label(
            header_frame,
            text="EPUB → PDF Converter",
            font=('Helvetica', 28, 'bold')
        )
        title_label.grid(row=0, column=0, sticky="w")
        
        subtitle_label = ttk.Label(
            header_frame,
            text="Bulk convert your ebooks with ease",
            font=('Helvetica', 14)
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(5, 0))
        
        # Controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        controls_frame.columnconfigure(1, weight=1)
        
        # Add files button
        add_btn = ttk.Button(
            controls_frame,
            text="+ Add EPUB Files",
            command=self._add_files
        )
        add_btn.grid(row=0, column=0, padx=(0, 15))
        
        # Output directory label
        self.output_label = ttk.Label(
            controls_frame,
            text="Output: Same as source"
        )
        self.output_label.grid(row=0, column=1, sticky="e", padx=(0, 10))
        
        # Change output button
        output_btn = ttk.Button(
            controls_frame,
            text="Change Output...",
            command=self._select_output_dir
        )
        output_btn.grid(row=0, column=2)
        
        # Queue section header
        queue_header = ttk.Frame(main_frame)
        queue_header.grid(row=2, column=0, sticky="new", pady=(0, 10))
        queue_header.columnconfigure(0, weight=1)
        
        queue_title = ttk.Label(
            queue_header,
            text="Conversion Queue",
            font=('Helvetica', 16, 'bold')
        )
        queue_title.grid(row=0, column=0, sticky="w")
        
        self.queue_count_label = ttk.Label(
            queue_header,
            text="0 files"
        )
        self.queue_count_label.grid(row=0, column=1, padx=(0, 15))
        
        # Clear button
        self.clear_btn = ttk.Button(
            queue_header,
            text="Clear Completed",
            command=self._clear_completed
        )
        self.clear_btn.grid(row=0, column=2)
        
        # Scrollable queue container
        queue_container = ttk.Frame(main_frame)
        queue_container.grid(row=2, column=0, sticky="nsew", pady=(40, 0))
        queue_container.columnconfigure(0, weight=1)
        queue_container.rowconfigure(0, weight=1)
        
        # Canvas for scrolling
        self.queue_canvas = tk.Canvas(queue_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(queue_container, orient="vertical", command=self.queue_canvas.yview)
        
        self.queue_scroll = ttk.Frame(self.queue_canvas)
        self.queue_scroll.columnconfigure(0, weight=1)
        
        self.queue_scroll.bind(
            "<Configure>",
            lambda e: self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))
        )
        
        self.canvas_window = self.queue_canvas.create_window((0, 0), window=self.queue_scroll, anchor="nw")
        self.queue_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Make canvas resize with window
        self.queue_canvas.bind('<Configure>', self._on_canvas_configure)
        
        self.queue_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Mousewheel scrolling
        self.queue_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Empty state
        self.empty_label = ttk.Label(
            self.queue_scroll,
            text="No files in queue\n\nClick '+ Add EPUB Files' to get started",
            font=('Helvetica', 14),
            justify="center"
        )
        self.empty_label.grid(row=0, column=0, pady=80)
        
        # Footer with stats
        footer_frame = ttk.Frame(main_frame)
        footer_frame.grid(row=3, column=0, sticky="ew", pady=(20, 0))
        footer_frame.columnconfigure(0, weight=1)
        
        self.stats_label = ttk.Label(
            footer_frame,
            text="Ready",
            font=('Helvetica', 12)
        )
        self.stats_label.grid(row=0, column=0)
        
    def _on_canvas_configure(self, event):
        """Resize canvas window when canvas size changes"""
        self.queue_canvas.itemconfig(self.canvas_window, width=event.width)
        
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling"""
        self.queue_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
    def _add_files(self):
        """Open file dialog to add EPUB files"""
        files = filedialog.askopenfilenames(
            title="Select EPUB Files",
            filetypes=[("EPUB Files", "*.epub"), ("All Files", "*.*")]
        )
        if files:
            self._add_files_to_queue(list(files))
            
    def _add_files_to_queue(self, epub_paths: List[str]):
        """Add files to the conversion queue"""
        for epub_path in epub_paths:
            if not os.path.exists(epub_path):
                continue
                
            # Determine output path
            if self.output_directory:
                output_path = os.path.join(
                    self.output_directory,
                    Path(epub_path).stem + ".pdf"
                )
            else:
                output_path = str(Path(epub_path).with_suffix('.pdf'))
                
            # Create queue item
            item_id = str(uuid.uuid4())
            item = QueueItem(
                id=item_id,
                epub_path=epub_path,
                output_path=output_path
            )
            
            self.queue_items[item_id] = item
            self._create_item_widget(item)
            self.task_queue.put(item)
            
        self._update_ui()
        
    def _create_item_widget(self, item: QueueItem):
        """Create a widget for a queue item"""
        # Hide empty state
        self.empty_label.grid_remove()
        
        widget = QueueItemWidget(
            self.queue_scroll,
            item,
            on_remove=self._remove_item
        )
        widget.grid(row=len(self.item_widgets), column=0, sticky="ew", pady=(0, 5))
        self.item_widgets[item.id] = widget
        
        # Update scroll region
        self.queue_scroll.update_idletasks()
        self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))
        
    def _remove_item(self, item_id: str):
        """Remove an item from the queue"""
        if item_id in self.item_widgets:
            self.item_widgets[item_id].destroy()
            del self.item_widgets[item_id]
            
        if item_id in self.queue_items:
            del self.queue_items[item_id]
            
        self._reorder_widgets()
        self._update_ui()
        
    def _reorder_widgets(self):
        """Reorder widget grid positions after removal"""
        for idx, widget in enumerate(self.item_widgets.values()):
            widget.grid(row=idx, column=0, sticky="ew", pady=(0, 5))
            
    def _clear_completed(self):
        """Clear completed and failed items from queue"""
        to_remove = [
            item_id for item_id, item in self.queue_items.items()
            if item.status in [ConversionStatus.COMPLETED, ConversionStatus.FAILED]
        ]
        for item_id in to_remove:
            self._remove_item(item_id)
            
    def _select_output_dir(self):
        """Select output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_directory = directory
            display_path = directory
            if len(display_path) > 35:
                display_path = "..." + display_path[-32:]
            self.output_label.configure(text=f"Output: {display_path}")
            
    def _on_conversion_update(self, item_id: str, status: ConversionStatus, 
                              progress: float, message: str):
        """Handle conversion progress updates from worker thread"""
        self.after(0, lambda: self._update_item(item_id, status, progress, message))
        
    def _update_item(self, item_id: str, status: ConversionStatus, 
                     progress: float, message: str):
        """Update item state on main thread"""
        if item_id in self.item_widgets:
            self.item_widgets[item_id].update_status(status, progress, message)
            
        if item_id in self.queue_items:
            self.queue_items[item_id].status = status
            self.queue_items[item_id].progress = progress
            self.queue_items[item_id].message = message
            
        self._update_ui()
        
    def _update_ui(self):
        """Update UI state"""
        total = len(self.queue_items)
        completed = sum(1 for item in self.queue_items.values() 
                       if item.status == ConversionStatus.COMPLETED)
        failed = sum(1 for item in self.queue_items.values() 
                    if item.status == ConversionStatus.FAILED)
        converting = sum(1 for item in self.queue_items.values() 
                        if item.status == ConversionStatus.CONVERTING)
        pending = sum(1 for item in self.queue_items.values() 
                     if item.status == ConversionStatus.PENDING)
        
        self.queue_count_label.configure(text=f"{total} file{'s' if total != 1 else ''}")
        
        if converting > 0:
            self.stats_label.configure(text=f"Converting... {completed}/{total} complete")
        elif pending > 0:
            self.stats_label.configure(text=f"Processing queue... {pending} remaining")
        elif total > 0:
            parts = []
            if completed > 0:
                parts.append(f"{completed} completed")
            if failed > 0:
                parts.append(f"{failed} failed")
            self.stats_label.configure(text=" • ".join(parts) if parts else "Ready")
        else:
            self.stats_label.configure(text="Ready")
            
        if not self.queue_items:
            self.empty_label.grid()
            
    def _on_close(self):
        """Handle window close"""
        self.worker.stop()
        self.task_queue.put(None)
        self.destroy()


def main():
    app = EPUBtoPDFApp()
    app.mainloop()


if __name__ == "__main__":
    main()
