"""Render a booking's invoice as a PDF.

Daftra's own invoice links all redirect to a Daftra sign-in, and a guest has no
Daftra account, so the copy the customer actually receives is rendered here.
Daftra remains the book of record; this is the same document in a form we can
hand to someone who is not a Daftra user.

Set in Jost, the typeface the website itself uses. ReportLab can only embed
TrueType outlines, so the three weights in ``assets/`` were cut from the
upstream variable font once, offline -- there is no runtime dependency on
fontTools. If those files ever go missing the invoice still renders, in
Helvetica, rather than failing.

Carries the ZATCA QR. It is Daftra's own QR image, stored on the invoice record
when the invoice is raised, so scanning our copy and scanning Daftra's give the
same result. Storing the image rather than the link keeps rendering offline. A
locally generated QR is only a fallback for a booking with no Daftra invoice --
it can differ, because Daftra encodes its own company profile and timestamp.
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4  # 595.28 x 841.89 pt

ASSETS = os.path.join(os.path.dirname(__file__), "assets")
LOGO_PATH = os.path.join(ASSETS, "ken_logo.png")

MARGIN = 48
RIGHT = PAGE_W - MARGIN

INK = (0.09, 0.09, 0.09)      # body text
MUTED = (0.45, 0.45, 0.45)    # labels and secondary lines
HAIRLINE = (0.85, 0.85, 0.85)  # table rules

# Column anchors, mirroring the reference layout: item on the left, then
# quantity and unit price, with the money column flushed to the right margin.
COL_QTY = 320
COL_UNIT = 396
COL_TOTAL = RIGHT

_FONT_FILES = (
    ("Jost", "Jost-Regular.ttf"),
    ("Jost-Medium", "Jost-Medium.ttf"),
    ("Jost-Bold", "Jost-Bold.ttf"),
)


def _register_fonts():
    """Register the site's typeface, falling back to Helvetica.

    A missing or unreadable font file must never cost the customer their
    invoice, so every failure path here returns the built-in faces.
    """
    try:
        registered = pdfmetrics.getRegisteredFontNames()
        for name, filename in _FONT_FILES:
            path = os.path.join(ASSETS, filename)
            if not os.path.exists(path):
                logger.warning("Invoice font %s missing; using Helvetica", filename)
                return "Helvetica", "Helvetica", "Helvetica-Bold"
            if name not in registered:
                pdfmetrics.registerFont(TTFont(name, path))
        return "Jost", "Jost-Medium", "Jost-Bold"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not register invoice fonts (%s); using Helvetica", exc)
        return "Helvetica", "Helvetica", "Helvetica-Bold"


REGULAR, MEDIUM, BOLD = _register_fonts()


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


def _sar(value):
    # "- SAR 1740.00" rather than "SAR -1740.00": the sign belongs to the row,
    # not to the currency.
    amount = Decimal(str(value or 0))
    if amount < 0:
        return f"- SAR {_money(-amount)}"
    return f"SAR {_money(amount)}"


def _text(pdf, x, y, value, font=None, size=9, colour=INK, right=False):
    pdf.setFont(font or REGULAR, size)
    pdf.setFillColorRGB(*colour)
    if right:
        pdf.drawRightString(x, y, str(value))
    else:
        pdf.drawString(x, y, str(value))


def _rule(pdf, y, colour=HAIRLINE, width=0.6, x0=MARGIN, x1=RIGHT):
    pdf.setStrokeColorRGB(*colour)
    pdf.setLineWidth(width)
    pdf.line(x0, y, x1, y)


def _draw_masthead(pdf):
    """Logo left, the word Invoice right -- the reference layout's header."""
    if os.path.exists(LOGO_PATH):
        try:
            pdf.drawImage(
                LOGO_PATH, MARGIN, PAGE_H - 108, width=104, height=46,
                mask="auto", preserveAspectRatio=True, anchor="sw",
            )
        except Exception as exc:  # noqa: BLE001 - a missing logo must not stop the invoice
            logger.warning("Could not draw invoice logo: %s", exc)

    _text(pdf, RIGHT, PAGE_H - 100, "Invoice", font=BOLD, size=30, right=True)


def _draw_table_header(pdf, y):
    _text(pdf, MARGIN, y, "Item", font=BOLD, size=9)
    _text(pdf, COL_QTY, y, "Quantity", font=BOLD, size=9)
    _text(pdf, COL_UNIT, y, "Unit Price", font=BOLD, size=9)
    _text(pdf, COL_TOTAL, y, "Total", font=BOLD, size=9, right=True)
    _rule(pdf, y - 10, colour=INK, width=0.9)
    return y - 30


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

    _draw_masthead(pdf)

    # ------------------------------------------------------- billed to / meta
    y = PAGE_H - 168
    _text(pdf, MARGIN, y, "Billed to:", font=BOLD, size=9.5)
    line = y - 18
    for value in (
        booking.contact_name or booking.contact_email or "-",
        booking.contact_phone,
        booking.contact_email,
    ):
        if value:
            _text(pdf, MARGIN, line, value, size=9)
            line -= 14

    _text(pdf, RIGHT, y, f"Invoice No. {number}", size=9, right=True)
    _text(pdf, RIGHT, y - 18, issued.strftime("%d %B %Y"), size=9,
          colour=MUTED, right=True)
    meta = y - 32
    if main_date:
        _text(pdf, RIGHT, meta,
              f"Stay {main_date.date_from:%d %b %Y} - {main_date.date_to:%d %b %Y}",
              size=9, colour=MUTED, right=True)
        meta -= 14
    if settings.INVOICE_SELLER_VAT:
        _text(pdf, RIGHT, meta, f"VAT {settings.INVOICE_SELLER_VAT}",
              size=9, colour=MUTED, right=True)

    # -------------------------------------------------------------- the table
    y = min(line, meta) - 34
    y = _draw_table_header(pdf, y)

    for item in items:
        # Start a fresh page rather than let a long booking run off the bottom.
        if y < 250:
            pdf.showPage()
            _draw_masthead(pdf)
            y = _draw_table_header(pdf, PAGE_H - 168)

        line_total = Decimal(str(item["unit_price"])) * Decimal(str(item["quantity"]))
        _text(pdf, MARGIN, y, str(item["item"])[:46], size=9)
        description = str(item.get("description") or "").strip()
        if description:
            _text(pdf, MARGIN, y - 12, description[:56], size=7.5, colour=MUTED)
        _text(pdf, COL_QTY, y, item["quantity"], size=9)
        _text(pdf, COL_UNIT, y, _money(item["unit_price"]), size=9)
        _text(pdf, COL_TOTAL, y, _money(line_total), size=9, right=True)

        y -= 34 if description else 24
        _rule(pdf, y + 10)

    # ------------------------------------------------------------- the totals
    y -= 16
    outstanding = balance > 0

    rows = [("Subtotal", items_total)]
    if discount:
        rows.append(("Discount", -Decimal(str(discount))))
    if outstanding and paid:
        # Only while something is still owed. On a settled invoice the bar
        # carries the total, and a "Paid" deduction above it would read as
        # arithmetic that does not come out.
        rows.append(("Paid", -paid))

    for label, value in rows:
        _text(pdf, COL_UNIT, y, label, font=BOLD, size=9)
        _text(pdf, COL_TOTAL, y, _sar(value), size=9, right=True)
        y -= 20

    # The headline figure sits in a solid bar, as in the reference layout. What
    # is owed matters more than what was billed, so a part-paid invoice puts the
    # outstanding balance here and says so.
    bar_label = "Balance Due" if outstanding else "Total"
    bar_value = balance if outstanding else total

    bar_h, bar_y = 34, y - 26
    pdf.setFillColorRGB(0, 0, 0)
    pdf.rect(COL_UNIT - 24, bar_y, RIGHT - COL_UNIT + 24, bar_h, stroke=0, fill=1)
    _text(pdf, COL_UNIT - 10, bar_y + 12, bar_label, font=BOLD, size=11,
          colour=(1, 1, 1))
    _text(pdf, RIGHT - 12, bar_y + 11, _sar(bar_value), font=BOLD, size=13,
          colour=(1, 1, 1), right=True)

    _text(pdf, MARGIN, bar_y + 12,
          "Partially paid" if outstanding else "Paid in full",
          font=MEDIUM, size=10, colour=MUTED)

    # ------------------------------------------------------------- thank you
    # Sits just above the footer rather than trailing the totals, so a short
    # invoice does not leave a void down the middle of the page. On a long one
    # it follows the totals instead, and is dropped if there is no room.
    thank_y = min(bar_y - 56, 250)
    if thank_y > 215:
        _text(pdf, MARGIN, thank_y, "Thank you", font=MEDIUM, size=22, colour=INK)

    # ---------------------------------------------------------------- footer
    foot = 152
    _rule(pdf, foot + 32, colour=HAIRLINE)

    _text(pdf, MARGIN, foot + 12, "Payment Information", font=BOLD, size=9)
    detail = foot - 4
    for label in (
        f"Booking reference: #{booking.pk}",
        f"Invoice total: {_sar(total)}",
        (f"Outstanding: {_sar(balance)}" if outstanding else "Settled in full"),
    ):
        _text(pdf, MARGIN, detail, label, size=8.5, colour=MUTED)
        detail -= 13

    _text(pdf, RIGHT, foot + 12, settings.INVOICE_SELLER_NAME, font=BOLD, size=9,
          right=True)
    seller_line = foot - 4
    for value in str(settings.INVOICE_SELLER_ADDRESS).splitlines():
        _text(pdf, RIGHT, seller_line, value.strip(), size=8.5, colour=MUTED,
              right=True)
        seller_line -= 13

    # ------------------------------------------------------------- zatca qr
    # Daftra's own QR, byte for byte, so scanning our invoice and scanning
    # theirs give the same result. Only if it is missing do we fall back to
    # generating one, which can differ: Daftra encodes its own company profile
    # and its own invoice timestamp, not ours.
    try:
        if record and record.qr_code_png:
            image = ImageReader(io.BytesIO(base64.b64decode(record.qr_code_png)))
        else:
            logger.info(
                "No Daftra QR stored for booking %s; generating one locally",
                booking.pk,
            )
            image = _qr_image(
                zatca_tlv(
                    seller=settings.INVOICE_SELLER_NAME,
                    vat=settings.INVOICE_SELLER_VAT,
                    timestamp=issued.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    total=_money(total),
                    vat_amount="0",
                )
            )
        pdf.drawImage(image, MARGIN, 40, width=58, height=58, mask="auto")
        _text(pdf, MARGIN + 66, 74, "ZATCA e-invoice QR", size=7.5, colour=MUTED)
        _text(pdf, MARGIN + 66, 62, "Scan to verify this invoice", size=7.5,
              colour=MUTED)
    except Exception as exc:  # noqa: BLE001 - the invoice is still valid without it
        logger.warning("Could not draw ZATCA QR for booking %s: %s", booking.pk, exc)

    _text(pdf, RIGHT, 50, f"Invoice {number}", size=7.5, colour=MUTED, right=True)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
