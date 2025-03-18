import platform
from typing import Optional
from PIL import Image
from ..models.label import LabelSession
from ..config.settings import PRINTER_NAME

class PrinterService:
    @staticmethod
    def is_printing_available() -> bool:
        """Check if printing functionality is available on this platform."""
        return platform.system() == 'Windows'

    @staticmethod
    def print_label(image_path: str, copies: int, session: Optional[LabelSession] = None) -> None:
        """Prints the given image `copies` times."""
        if not PrinterService.is_printing_available():
            raise RuntimeError("Printing is not available on this platform")

        if copies <= 0:
            return

        if platform.system() == 'Windows':
            try:
                import win32print
                import win32ui
                import ImageWin
            except ImportError:
                raise RuntimeError("Windows printing modules not available. Please install pywin32.")

            hprinter = win32print.OpenPrinter(PRINTER_NAME)
            printer_dc = win32ui.CreateDC()
            printer_dc.CreatePrinterDC(PRINTER_NAME)

            dpi_x = printer_dc.GetDeviceCaps(88)  # HORZRES
            dpi_y = printer_dc.GetDeviceCaps(90)  # VERTRES

            image = Image.open(image_path)
            # Example dimension: 5" x 1" label
            target_width = int(5 * dpi_x)
            target_height = int(1 * dpi_y)
            image = image.resize((target_width, target_height))

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
        else:
            raise RuntimeError("Printing is not supported on this platform")