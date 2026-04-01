"""Async PDF exporter using Playwright for HTML to PDF conversion"""
import asyncio
import tempfile
import os
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright
from .pdf_exporter import PDFExporter


class AsyncPDFExporter:
    """Async wrapper for PDF generation using Playwright"""
    
    def __init__(self):
        self.exporter = PDFExporter()
        self._playwright = None
        self._browser = None
    
    async def initialize(self):
        """Initialize Playwright browser"""
        if self._playwright is None:
            try:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
            except Exception as e:
                print(f"❌ Failed to initialize Playwright: {e}")
                print("💡 Make sure Playwright browsers are installed. Run: playwright install chromium")
                raise
    
    async def cleanup(self):
        """Clean up browser resources"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            self._browser = None
    
    async def wait_for_mathjax(self, page, max_wait: int = 10) -> bool:
        """Wait for MathJax to complete rendering"""
        wait_time = 0
        while wait_time < max_wait:
            try:
                mathjax_ready = await page.evaluate("""
                    () => {
                        if (typeof MathJax === 'undefined') return false;
                        if (!MathJax.startup) return false;
                        return MathJax.startup.document.state >= 8;
                    }
                """)
                
                data_ready = await page.get_attribute('body', 'data-ready')
                
                if mathjax_ready and data_ready == 'true':
                    print("✓ MathJax rendering completed!")
                    await asyncio.sleep(2)  # Extra wait for stability
                    return True
            except Exception as e:
                print(f"Error checking MathJax: {e}")
            
            await asyncio.sleep(1)
            wait_time += 1
            if wait_time % 5 == 0:
                print(f"⏳ Waiting for MathJax... {wait_time}s")
        
        print("⚠ MathJax wait timeout - proceeding anyway")
        return False
    
    async def html_to_pdf(self, html_content: str, output_path: str) -> bool:
        """Convert HTML to PDF using Playwright"""
        if self._browser is None:
            await self.initialize()
        
        temp_html_path = None
        try:
            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(html_content)
                temp_html_path = temp_file.name
            
            # Create a new page
            page = await self._browser.new_page()
            
            # Load HTML in browser
            file_url = f"file://{os.path.abspath(temp_html_path)}"
            print(f"🌐 Loading HTML: {file_url}")
            await page.goto(file_url, wait_until='networkidle')
            
            # Wait for fonts to load (especially Bengali fonts from Google Fonts)
            print("⏳ Waiting for fonts to load...")
            await page.evaluate("""
                async () => {
                    // Wait for all fonts to be loaded
                    if (document.fonts && document.fonts.ready) {
                        await document.fonts.ready;
                    }
                    // Wait for Google Fonts to load
                    await new Promise(resolve => setTimeout(resolve, 3000));
                    // Verify Noto Sans Bengali font is loaded
                    try {
                        await document.fonts.load('1em "Noto Sans Bengali"');
                    } catch (e) {
                        console.log('Font loading warning:', e);
                    }
                    // Additional wait to ensure all fonts are rendered
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            """)
            
            # Wait for MathJax to render
            print("⏳ Waiting for MathJax...")
            await self.wait_for_mathjax(page)
            
            # Generate PDF with A4 settings
            print("🖨️ Generating PDF...")
            await page.pdf(
                path=output_path,
                format='A4',
                margin={
                    'top': '10mm',
                    'bottom': '10mm',
                    'left': '10mm',
                    'right': '10mm'
                },
                print_background=True
            )
            
            await page.close()
            print(f"✅ PDF generated: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error converting HTML to PDF: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return False
            
        finally:
            # Clean up temp HTML file
            if temp_html_path and os.path.exists(temp_html_path):
                try:
                    os.unlink(temp_html_path)
                    print("🧹 Temp HTML file cleaned up")
                except Exception as e:
                    print(f"Failed to clean up temp HTML: {e}")
    
    async def export_quiz_batch_to_pdf(
        self, 
        quiz_data: List[Dict[str, Any]], 
        exam_name: str, 
        format_type: int = 1,
        display_title: str = None
    ) -> Optional[bytes]:
        """
        Export quiz batch to PDF and return as bytes
        
        Args:
            quiz_data: List of quiz dictionaries
            exam_name: Name for the exam header
            format_type: 1 for Format 1 (with answers), 2 for Format 2 (separate answer sheet), 3 for Format 3 (exam style, answer key only)
        
        Returns:
            PDF bytes or None if generation failed
        """
        try:
            # Generate HTML
            html_content = self.exporter.process_json_to_html(quiz_data, exam_name, format_type, display_title)
            
            if not html_content:
                print("❌ Failed to generate HTML content")
                return None
            
            # Create temporary PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            # Convert HTML to PDF
            success = await self.html_to_pdf(html_content, temp_pdf_path)
            
            if not success:
                return None
            
            # Read PDF bytes
            with open(temp_pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            # Clean up temp file
            try:
                os.unlink(temp_pdf_path)
            except Exception:
                pass
            
            return pdf_bytes
            
        except Exception as e:
            print(f"❌ Error in export_quiz_batch_to_pdf: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return None


# Global async exporter instance
_async_pdf_exporter = None


def get_async_pdf_exporter() -> AsyncPDFExporter:
    """Get or create the async PDF exporter instance"""
    global _async_pdf_exporter
    if _async_pdf_exporter is None:
        _async_pdf_exporter = AsyncPDFExporter()
    return _async_pdf_exporter
