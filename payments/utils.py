# payments/utils.py
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# Register a Unicode font that supports the Rupee symbol (₹) and Unicode text
font_path = os.path.join(settings.BASE_DIR, 'fonts', 'DejaVuSans.ttf')  # Put DejaVuSans.ttf in a "fonts" folder under your project root
if not pdfmetrics.getFont('DejaVuSans'):
    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))


def send_order_confirmation_email(order):
    """
    Send order confirmation email to the customer with PDF invoice attachment (if available).
    """
    subject = f'Order Confirmation - {order.order_number}'
    
    # Render HTML email content
    html_content = render_to_string('emails/order_confirmation.html', {
        'order': order,
        'user': order.user,
    })
    
    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[order.user.email],
    )
    email.content_subtype = 'html'  # Set content type to HTML
    
    # Attach PDF invoice if it exists
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
    Generate PDF invoice using ReportLab (lightweight and minimal dependencies).
    Returns the absolute path of the generated PDF.
    """
    # Create invoice directory if it doesn't exist
    invoice_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
    os.makedirs(invoice_dir, exist_ok=True)
    
    # PDF file path
    pdf_filename = f'invoice_{order.order_number}.pdf'
    pdf_path = os.path.join(invoice_dir, pdf_filename)
    
    # Create PDF document template
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    
    # Get default stylesheet and override with custom font for all styles
    styles = getSampleStyleSheet()
    
    # Override all styles to use DejaVuSans font which supports Rupee symbol
    for style_name in styles.byName:
        styles[style_name].fontName = 'DejaVuSans'
    
    story = []
    
    # Title style and content
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName='DejaVuSans',
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        alignment=1,  # Center alignment
    )
    story.append(Paragraph("CAKE SHOP INVOICE", title_style))
    story.append(Spacer(1, 20))
    
    # Order details table data (string without HTML tags)
    order_data = [
        ['Invoice Number:', order.order_number],
        ['Order Date:', order.created_at.strftime('%B %d, %Y')],
        ['Payment Method:', order.get_payment_method_display()],
        ['Status:', order.get_status_display()],
    ]
    order_table = Table(order_data, colWidths=[2 * inch, 3 * inch])
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(order_table)
    story.append(Spacer(1, 20))
    
    # Customer billing address using multiple Paragraphs instead of raw <br/>
    story.append(Paragraph("<b>Billing Address:</b>", styles['Heading3']))
    address = order.shipping_address
    # Use separate Paragraphs for each line:
    address_lines = [
        address.name,
        address.address_line_1,
    ]
    if address.address_line_2:
        address_lines.append(address.address_line_2)
    address_lines.append(f"{address.city}, {address.state} - {address.pincode}")
    address_lines.append(f"Phone: {address.phone}")
    for line in address_lines:
        story.append(Paragraph(line, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Order items heading
    story.append(Paragraph("<b>Order Items:</b>", styles['Heading3']))
    
    # Items table header + data
    items_data = [['Item', 'Weight', 'Quantity', 'Price', 'Total']]
    for item in order.items.all():
        items_data.append([
            item.variant.cake.title,
            f"{item.variant.weight} kg",
            str(item.quantity),
            f"₹{item.price:.2f}",
            f"₹{item.get_total_price():.2f}",
        ])
    items_table = Table(items_data, colWidths=[2.5 * inch, inch, inch, inch, inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 20))
    
    # Totals table data with Rupee symbol using DejaVuSans font
    totals_data = [
        ['Subtotal:', f"₹{order.subtotal:.2f}"],
        ['Delivery Charge:', f"₹{order.delivery_charge:.2f}"],
    ]
    if order.coupon_discount > 0:
        totals_data.append(['Coupon Discount:', f"- ₹{order.coupon_discount:.2f}"])
    totals_data.append(['Total Amount:', f"₹{order.total_amount:.2f}"])
    
    totals_table = Table(totals_data, colWidths=[4 * inch, 2 * inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -2), 'DejaVuSans'),
        ('FONTNAME', (0, -1), (-1, -1), 'DejaVuSans-Bold'),  # You can register bold variant if needed; else normal font
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 30))
    
    # Footer message
    footer_text = "Thank you for shopping with us!"
    story.append(Paragraph(footer_text, styles['Normal']))
    
    # Build the PDF file
    doc.build(story)
    
    return pdf_path
