import platform
from typing import Optional
from PIL import Image
from ..models.label import LabelSession
from ..config.settings import PRINTER_NAME
import win32print
import win32ui
import ImageWin
import os

class PrinterService:
    @staticmethod
    def is_printing_available() -> bool:
        """Check if printing functionality is available on this platform."""
        return platform.system() == 'Windows'

    @staticmethod
    def print_label(image_path: str, copies: int, session: Optional[LabelSession] = None) -> None:
        """Prints the given image `copies` times on Windows using win32print."""
        if copies <= 0:
            return

        if not os.path.exists(image_path):
            raise RuntimeError(f"Image file not found: {image_path}")

        try:
            # Get the default printer if PRINTER_NAME is not found
            try:
                hprinter = win32print.OpenPrinter(PRINTER_NAME)
            except Exception:
                default_printer = win32print.GetDefaultPrinter()
                hprinter = win32print.OpenPrinter(default_printer)

            printer_dc = win32ui.CreateDC()
            printer_dc.CreatePrinterDC(PRINTER_NAME)

            # Get printer DPI
            dpi_x = printer_dc.GetDeviceCaps(88)  # HORZRES
            dpi_y = printer_dc.GetDeviceCaps(90)  # VERTRES

            # Open and resize image
            image = Image.open(image_path)
            # Example dimension: 5" x 1" label
            target_width = int(5 * dpi_x)
            target_height = int(1 * dpi_y)
            image = image.resize((target_width, target_height))

            # Start print job
            printer_dc.StartDoc(image_path)
            for _ in range(copies):
                printer_dc.StartPage()
                dib = ImageWin.Dib(image)
                dib.draw(printer_dc.GetHandleOutput(), (0, 0, target_width, target_height))
                printer_dc.EndPage()

            printer_dc.EndDoc()
            printer_dc.DeleteDC()
            win32print.ClosePrinter(hprinter)

            # Log the print job if session data is available
            if session:
                from .storage_service import StorageService
                StorageService.log_print_job(session, copies)

        except Exception as e:
            raise RuntimeError(f"Failed to print: {str(e)}")