"""Render a booking's invoice as a PDF, laid out like the Daftra document.

Daftra's own invoice links all redirect to a Daftra sign-in, and a guest has no
Daftra account, so the copy the customer actually receives is rendered here.
Daftra remains the book of record; this is the same document in a form we can
hand to someone who is not a Daftra user.

Carries the ZATCA QR. It is generated locally from the same TLV fields Daftra
encodes, so rendering needs no network call and cannot fail because Daftra is
slow or down.
"""
import base64
import io
import logging
import os
from decimal import Decimal

import qrcode
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4  # 595.28 x 841.89 pt

# The source document is laid out in 96dpi pixels; PDF works in 72dpi points.
PX = 0.75

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "ken_logo.png")

BROWN = (0.404, 0.243, 0.157)
GREY = (0.45, 0.45, 0.45)
LINE = (0.85, 0.85, 0.85)


def _y(top_px):
    """Page coordinate from a top-down pixel offset in the source layout."""
    return PAGE_H - (top_px * PX)


def zatca_tlv(*, seller, vat, timestamp, total, vat_amount):
    """ZATCA phase-1 QR payload: base64 of tag-length-value triples."""
    def field(tag, value):
        raw = str(value).encode("utf-8")
        return bytes([tag, len(raw)]) + raw

    payload = (
        field(1, seller)
        + field(2, vat)
        + field(3, timestamp)
        + field(4, total)
        + field(5, vat_amount)
    )
    return base64.b64encode(payload).decode("ascii")


def _qr_image(data):
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def _money(value):
    return f"{Decimal(str(value or 0)):.2f}"


def render_invoice_pdf(booking):
    """The booking's invoice as PDF bytes."""
    from .daftra import build_invoice_items

    record = getattr(booking, "daftra_invoice", None)
    number = record.invoice_number if record else f"B{booking.pk:06d}"

    main_date = booking.dates.filter(is_extra=False).first() or booking.dates.first()
    issued = booking.created_at
    items, discount = build_invoice_items(booking)

    total = Decimal(str(booking.total_price or 0))
    paid = Decimal(str(booking.paid or 0))
    balance = Decimal(str(booking.not_paid or 0))
    items_total = sum(
        Decimal(str(i["unit_price"])) * Decimal(str(i["quantity"])) for i in items
    )

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f"Invoice {number}")

    # ---------------------------------------------------------------- header
    if os.path.exists(LOGO_PATH):
        try:
            pdf.drawImage(
                LOGO_PATH, 394, _y(15) - 43, width=121, height=43,
                mask="auto", preserveAspectRatio=True, anchor="ne",
            )
        except Exception as exc:  # noqa: BLE001 - a missing logo must not stop the invoice
            logger.warning("Could not draw invoice logo: %s", exc)

    pdf.setFillColorRGB(*BROWN)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(22.5, _y(45), "Invoice")

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawRightString(565, _y(80), settings.INVOICE_SELLER_NAME)
    pdf.setFont("Helvetica", 9)
    line_y = 94
    for line in str(settings.INVOICE_SELLER_ADDRESS).splitlines():
        pdf.drawRightString(565, _y(line_y), line.strip())
        line_y += 14
    if settings.INVOICE_SELLER_VAT:
        pdf.drawRightString(565, _y(line_y), f"VAT {settings.INVOICE_SELLER_VAT}")

    # ------------------------------------------------------- bill to / meta
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(22.5, _y(228), "Bill To:")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(22.5, _y(256), booking.contact_name or booking.contact_email or "-")
    if booking.contact_email:
        pdf.drawString(22.5, _y(270), booking.contact_email)

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(397, _y(228), "Invoice No")
    pdf.drawString(397, _y(242), "Invoice Date")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(462, _y(228), str(number))
    pdf.drawString(462, _y(242), issued.strftime("%d/%m/%Y"))
    if main_date:
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(397, _y(256), "Stay")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(
            462, _y(256),
            f"{main_date.date_from:%d/%m/%Y} - {main_date.date_to:%d/%m/%Y}",
        )

    # ------------------------------------------------------------ item table
    cols = [25.5, 170, 307, 373, 470]
    head_top = 330
    pdf.setFillColorRGB(*LINE)
    pdf.rect(22.5, _y(head_top + 6) - 4, 550, 20, stroke=0, fill=1)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 9)
    for x, label in zip(cols, ["Item name", "Description", "Unit Price", "Quantity", "Subtotal"]):
        if label == "Subtotal":
            pdf.drawRightString(x + 100, _y(head_top), label)
        else:
            pdf.drawString(x, _y(head_top), label)

    pdf.setFont("Helvetica", 9)
    row_top = head_top + 26
    for item in items:
        pdf.drawString(cols[0], _y(row_top), str(item["item"])[:34])
        pdf.drawString(cols[1], _y(row_top), str(item.get("description") or "")[:32])
        pdf.drawRightString(cols[2] + 45, _y(row_top), _money(item["unit_price"]))
        pdf.drawRightString(cols[3] + 40, _y(row_top), str(item["quantity"]))
        line_total = Decimal(str(item["unit_price"])) * Decimal(str(item["quantity"]))
        pdf.drawRightString(cols[4] + 100, _y(row_top), _money(line_total))
        pdf.setStrokeColorRGB(*LINE)
        pdf.line(22.5, _y(row_top + 8), 572.5, _y(row_top + 8))
        row_top += 26

    # ---------------------------------------------------------------- totals
    totals_top = row_top + 12
    rows = [("Items Total", items_total)]
    if discount:
        rows.append(("Discount", -Decimal(str(discount))))
    rows += [("Total", total), ("Paid", -paid), ("Balance Due", balance)]

    for label, value in rows:
        strong = label in ("Total", "Balance Due")
        pdf.setFont("Helvetica-Bold" if strong else "Helvetica", 9)
        pdf.drawString(397, _y(totals_top), label)
        pdf.drawRightString(572.5, _y(totals_top), f"SAR {_money(value)}")
        totals_top += 20

    # A part-paid invoice must say so on its face, not only in the numbers.
    pdf.setFont("Helvetica-Bold", 9)
    if balance > 0:
        pdf.setFillColorRGB(0.7, 0.35, 0.0)
        pdf.drawString(22.5, _y(totals_top - 20), f"PARTIALLY PAID - SAR {_money(balance)} outstanding")
    else:
        pdf.setFillColorRGB(0.1, 0.5, 0.2)
        pdf.drawString(22.5, _y(totals_top - 20), "PAID IN FULL")
    pdf.setFillColorRGB(0, 0, 0)

    pdf.setFont("Helvetica", 9)
    pdf.drawString(22.5, _y(totals_top + 20), f"Booking #{booking.pk}")

    # ------------------------------------------------------------- zatca qr
    try:
        payload = zatca_tlv(
            seller=settings.INVOICE_SELLER_NAME,
            vat=settings.INVOICE_SELLER_VAT,
            timestamp=issued.strftime("%Y-%m-%dT%H:%M:%SZ"),
            total=_money(total),
            vat_amount="0",
        )
        pdf.drawImage(_qr_image(payload), 23, 59, width=68, height=68, mask="auto")
        pdf.setFont("Helvetica", 7)
        pdf.setFillColorRGB(*GREY)
        pdf.drawString(23, 48, "ZATCA e-invoice QR")
    except Exception as exc:  # noqa: BLE001 - the invoice is still valid without it
        logger.warning("Could not draw ZATCA QR for booking %s: %s", booking.pk, exc)

    pdf.setFillColorRGB(*GREY)
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(PAGE_W / 2, 40, settings.INVOICE_SELLER_NAME)
    pdf.drawRightString(572.5, 40, "1/1")

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
