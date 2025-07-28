import os
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors


def send_order_confirmation_email(order):
    """
    Send order confirmation email with PDF invoice attachment if exists.
    """
    subject = f'Order Confirmation - {order.order_number}'
    html_content = render_to_string('emails/order_confirmation.html', {
        'order': order,
        'user': order.user,
    })

    email = EmailMessage(
        subject,
        html_content,
        settings.EMAIL_HOST_USER,
        [order.user.email],
    )
    email.content_subtype = "html"

    pdf_path = os.path.join(settings.MEDIA_ROOT, 'invoices', f'invoice_{order.order_number}.pdf')
    if os.path.exists(pdf_path):
        email.attach_file(pdf_path)

    try:
        email.send()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def generate_invoice_pdf(order):
    """
    Generate simple PDF invoice using ReportLab.
    Uses default system fonts, and uses 'Rs' instead of ₹ symbol in text.
    Returns absolute path of the created PDF.
    """
    invoice_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
    os.makedirs(invoice_dir, exist_ok=True)

    pdf_filename = f'invoice_{order.order_number}.pdf'
    pdf_path = os.path.join(invoice_dir, pdf_filename)

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#2c3e50"),
        alignment=1,  # center
    )

    story = [Paragraph("CAKE SHOP INVOICE", title_style), Spacer(1, 20)]

    order_data = [
        ['Invoice Number:', order.order_number],
        ['Order Date:', order.created_at.strftime('%B %d, %Y')],
        ['Payment Method:', order.get_payment_method_display()],
        ['Status:', order.get_status_display()],
    ]

    order_table = Table(order_data, colWidths=[2 * inch, 3 * inch])
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(order_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Billing Address:</b>", styles['Heading3']))
    address = order.shipping_address
    if address:
        addr_lines = [
            address.name or '',
            address.address_line_1 or '',
        ]
        if address.address_line_2:
            addr_lines.append(address.address_line_2)
        addr_lines.append(f"{address.city or ''}, {address.state or ''} - {address.pincode or ''}")
        addr_lines.append(f"Phone: {address.phone or ''}")
        for line in addr_lines:
            if line.strip():
                story.append(Paragraph(line, styles['Normal']))
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Ordered Items:</b>", styles['Heading3']))

    items_data = [['Item', 'Weight', 'Quantity', 'Price', 'Total']]
    for item in order.items.all():
        items_data.append([
            item.variant.cake.title,
            f"{item.variant.weight} kg",
            str(item.quantity),
            f"Rs {item.price:.2f}",
            f"Rs {item.get_total_price():.2f}",
        ])

    items_table = Table(items_data, colWidths=[2.5 * inch, inch, inch, inch, inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3498db")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 30))

    totals_data = [
        ['Subtotal:', f"Rs {order.subtotal:.2f}"],
        ['Delivery Charge:', f"Rs {order.delivery_charge:.2f}"],
    ]
    if order.coupon_discount > 0:
        totals_data.append(['Coupon Discount:', f"- Rs {order.coupon_discount:.2f}"])
    totals_data.append(['Total:', f"Rs {order.total_amount:.2f}"])

    totals_table = Table(totals_data, colWidths=[4 * inch, 2 * inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
    ]))

    story.append(totals_table)

    footer_text = "Thank you for shopping with Cake Shop!"
    story.append(Paragraph(footer_text, styles['Normal']))

    doc.build(story)

    return pdf_path
