"""
Financial Documents Generation API.

Generate acts, invoices, contracts after project acceptance.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum
import html

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field


router = APIRouter(prefix="/financial", tags=["financial"])


# =============================================================================
# Models
# =============================================================================

class Currency(str, Enum):
    EUR = "EUR"
    USD = "USD"
    UAH = "UAH"


class DocumentLanguage(str, Enum):
    EN = "en"
    UK = "uk"
    RU = "ru"


class DocumentFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"


class PartyInfo(BaseModel):
    """Party information for documents."""
    name: str
    legal_name: Optional[str] = None
    address: str
    country: str = "Ukraine"
    tax_id: Optional[str] = None  # ЄДРПОУ / VAT ID
    iban: Optional[str] = None
    bank_name: Optional[str] = None
    swift: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    representative: Optional[str] = None
    representative_title: Optional[str] = None


class WorkItem(BaseModel):
    """Line item for invoice/act."""
    description: str
    quantity: float = 1.0
    unit: str = "hours"
    unit_price: float
    total: Optional[float] = None

    def calculate_total(self) -> float:
        return self.quantity * self.unit_price


class ActOfWorkRequest(BaseModel):
    """Request to generate Act of Work."""
    # Document info
    act_number: str
    act_date: date = Field(default_factory=date.today)
    language: DocumentLanguage = DocumentLanguage.UK
    format: DocumentFormat = DocumentFormat.PDF

    # Parties
    contractor: PartyInfo
    client: PartyInfo

    # Project info
    project_name: str
    contract_number: Optional[str] = None
    contract_date: Optional[date] = None

    # Work details
    work_period_start: date
    work_period_end: date
    work_description: str
    deliverables: List[str] = []
    items: List[WorkItem] = []

    # Totals
    currency: Currency = Currency.USD
    subtotal: Optional[float] = None
    tax_rate: float = 0.0  # e.g., 0.20 for 20% VAT
    tax_amount: Optional[float] = None
    total: Optional[float] = None

    # Analysis reference
    analysis_id: Optional[str] = None


class InvoiceRequest(BaseModel):
    """Request to generate Invoice."""
    # Document info
    invoice_number: str
    invoice_date: date = Field(default_factory=date.today)
    due_date: date
    language: DocumentLanguage = DocumentLanguage.EN
    format: DocumentFormat = DocumentFormat.PDF

    # Parties
    contractor: PartyInfo
    client: PartyInfo

    # Reference
    project_name: Optional[str] = None
    contract_number: Optional[str] = None
    act_number: Optional[str] = None
    po_number: Optional[str] = None

    # Items
    items: List[WorkItem]

    # Payment
    currency: Currency = Currency.USD
    subtotal: Optional[float] = None
    discount_percent: float = 0.0
    discount_amount: Optional[float] = None
    tax_rate: float = 0.0
    tax_amount: Optional[float] = None
    total: Optional[float] = None

    # Payment details
    payment_terms: str = "Net 30"
    payment_instructions: Optional[str] = None

    # Analysis reference
    analysis_id: Optional[str] = None


class ContractRequest(BaseModel):
    """Request to generate Service Contract."""
    # Document info
    contract_number: str
    contract_date: date = Field(default_factory=date.today)
    language: DocumentLanguage = DocumentLanguage.EN
    format: DocumentFormat = DocumentFormat.PDF

    # Parties
    contractor: PartyInfo
    client: PartyInfo

    # Contract details
    project_name: str
    scope_of_work: str
    deliverables: List[str]
    acceptance_criteria: Optional[str] = None

    # Timeline
    start_date: date
    end_date: date
    milestones: List[Dict[str, Any]] = []

    # Pricing
    currency: Currency = Currency.USD
    pricing_model: str = "fixed"  # fixed, hourly, milestone
    total_price: float
    hourly_rate: Optional[float] = None
    payment_schedule: List[Dict[str, Any]] = []

    # Terms
    payment_terms: str = "Net 30"
    warranty_period_days: int = 30
    liability_cap: Optional[float] = None

    # Analysis reference
    analysis_id: Optional[str] = None


# =============================================================================
# Document Generation
# =============================================================================

def calculate_totals(items: List[WorkItem], tax_rate: float = 0.0, discount_percent: float = 0.0):
    """Calculate subtotal, tax, and total from items."""
    subtotal = sum(item.quantity * item.unit_price for item in items)
    discount = subtotal * discount_percent
    taxable = subtotal - discount
    tax = taxable * tax_rate
    total = taxable + tax

    return {
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "taxable": round(taxable, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
    }


def generate_act_html(request: ActOfWorkRequest) -> str:
    """Generate Act of Work as HTML."""
    # Calculate totals if not provided
    if request.items:
        totals = calculate_totals(request.items, request.tax_rate)
        subtotal = request.subtotal or totals["subtotal"]
        tax_amount = request.tax_amount or totals["tax"]
        total = request.total or totals["total"]
    else:
        subtotal = request.subtotal or 0
        tax_amount = request.tax_amount or 0
        total = request.total or subtotal + tax_amount

    # Generate items table
    items_html = ""
    if request.items:
        items_html = """
        <table class="items">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Description</th>
                    <th>Qty</th>
                    <th>Unit</th>
                    <th>Rate</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
        """
        for i, item in enumerate(request.items, 1):
            amount = item.quantity * item.unit_price
            items_html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{html.escape(item.description)}</td>
                    <td>{item.quantity}</td>
                    <td>{html.escape(item.unit)}</td>
                    <td>{item.unit_price:,.2f}</td>
                    <td>{amount:,.2f}</td>
                </tr>
            """
        items_html += "</tbody></table>"

    deliverables_html = ""
    if request.deliverables:
        deliverables_html = "<h4>Deliverables:</h4><ul>"
        for d in request.deliverables:
            deliverables_html += f"<li>{html.escape(d)}</li>"
        deliverables_html += "</ul>"

    # Escape all user-provided strings for XSS prevention
    esc = html.escape
    contractor_name = esc(request.contractor.name)
    contractor_address = esc(request.contractor.address)
    contractor_tax_id = esc(request.contractor.tax_id) if request.contractor.tax_id else None
    contractor_rep = esc(request.contractor.representative) if request.contractor.representative else contractor_name
    client_name = esc(request.client.name)
    client_address = esc(request.client.address)
    client_tax_id = esc(request.client.tax_id) if request.client.tax_id else None
    client_rep = esc(request.client.representative) if request.client.representative else client_name
    project_name = esc(request.project_name)
    work_description = esc(request.work_description)
    contract_number = esc(request.contract_number) if request.contract_number else None

    act_number_esc = esc(request.act_number)
    html_content = f"""
<!DOCTYPE html>
<html lang="{request.language.value}">
<head>
    <meta charset="UTF-8">
    <title>Act of Work #{act_number_esc}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .parties {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
        .party {{ width: 45%; }}
        .party h3 {{ border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
        .details {{ margin-bottom: 30px; }}
        .items {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .items th, .items td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        .items th {{ background: #f5f5f5; }}
        .totals {{ text-align: right; margin-top: 20px; }}
        .totals table {{ margin-left: auto; }}
        .totals td {{ padding: 5px 15px; }}
        .signatures {{ display: flex; justify-content: space-between; margin-top: 50px; }}
        .signature {{ width: 45%; text-align: center; }}
        .signature-line {{ border-top: 1px solid #000; margin-top: 50px; padding-top: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ACT OF WORK / АКТ ВИКОНАНИХ РОБІТ</h1>
        <h2>#{act_number_esc}</h2>
        <p>Date: {request.act_date.strftime('%d.%m.%Y')}</p>
    </div>

    <div class="parties">
        <div class="party">
            <h3>Contractor / Виконавець</h3>
            <p><strong>{contractor_name}</strong></p>
            <p>{contractor_address}</p>
            {f'<p>Tax ID: {contractor_tax_id}</p>' if contractor_tax_id else ''}
        </div>
        <div class="party">
            <h3>Client / Замовник</h3>
            <p><strong>{client_name}</strong></p>
            <p>{client_address}</p>
            {f'<p>Tax ID: {client_tax_id}</p>' if client_tax_id else ''}
        </div>
    </div>

    <div class="details">
        <h3>Project: {project_name}</h3>
        {f'<p>Contract: #{contract_number} dated {request.contract_date.strftime("%d.%m.%Y")}</p>' if contract_number else ''}
        <p>Work Period: {request.work_period_start.strftime('%d.%m.%Y')} — {request.work_period_end.strftime('%d.%m.%Y')}</p>

        <h4>Work Description:</h4>
        <p>{work_description}</p>

        {deliverables_html}
    </div>

    {items_html}

    <div class="totals">
        <table>
            <tr>
                <td>Subtotal:</td>
                <td><strong>{subtotal:,.2f} {request.currency.value}</strong></td>
            </tr>
            {f'<tr><td>Tax ({request.tax_rate*100:.0f}%):</td><td>{tax_amount:,.2f} {request.currency.value}</td></tr>' if request.tax_rate > 0 else ''}
            <tr>
                <td><strong>TOTAL:</strong></td>
                <td><strong>{total:,.2f} {request.currency.value}</strong></td>
            </tr>
        </table>
    </div>

    <p style="margin-top: 30px;">
        The above work has been completed in full and accepted by the Client.
        No claims regarding quality or completeness of work.
    </p>

    <div class="signatures">
        <div class="signature">
            <p><strong>Contractor / Виконавець</strong></p>
            <div class="signature-line">
                {contractor_rep}
            </div>
        </div>
        <div class="signature">
            <p><strong>Client / Замовник</strong></p>
            <div class="signature-line">
                {client_rep}
            </div>
        </div>
    </div>
</body>
</html>
    """
    return html_content


def generate_invoice_html(request: InvoiceRequest) -> str:
    """Generate Invoice as HTML."""
    totals = calculate_totals(request.items, request.tax_rate, request.discount_percent)
    subtotal = request.subtotal or totals["subtotal"]
    discount = totals["discount"]
    tax_amount = request.tax_amount or totals["tax"]
    total = request.total or totals["total"]

    # Escape helper for XSS prevention
    esc = html.escape

    items_html = """
    <table class="items">
        <thead>
            <tr>
                <th>#</th>
                <th>Description</th>
                <th>Qty</th>
                <th>Rate</th>
                <th>Amount</th>
            </tr>
        </thead>
        <tbody>
    """
    for i, item in enumerate(request.items, 1):
        amount = item.quantity * item.unit_price
        items_html += f"""
            <tr>
                <td>{i}</td>
                <td>{esc(item.description)}</td>
                <td>{item.quantity} {esc(item.unit)}</td>
                <td>{item.unit_price:,.2f}</td>
                <td>{amount:,.2f}</td>
            </tr>
        """
    items_html += "</tbody></table>"

    # Escape all user-provided strings
    invoice_number_esc = esc(request.invoice_number)
    contractor_name = esc(request.contractor.name)
    contractor_address = esc(request.contractor.address)
    contractor_email = esc(request.contractor.email) if request.contractor.email else None
    contractor_bank = esc(request.contractor.bank_name) if request.contractor.bank_name else 'N/A'
    contractor_iban = esc(request.contractor.iban) if request.contractor.iban else 'N/A'
    contractor_swift = esc(request.contractor.swift) if request.contractor.swift else 'N/A'
    client_name = esc(request.client.name)
    client_address = esc(request.client.address)
    po_number = esc(request.po_number) if request.po_number else None
    project_name_esc = esc(request.project_name) if request.project_name else None
    contract_number = esc(request.contract_number) if request.contract_number else None
    payment_terms = esc(request.payment_terms)
    payment_instructions = esc(request.payment_instructions) if request.payment_instructions else None

    html_content = f"""
<!DOCTYPE html>
<html lang="{request.language.value}">
<head>
    <meta charset="UTF-8">
    <title>Invoice #{invoice_number_esc}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .invoice-header {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
        .invoice-title {{ font-size: 32px; color: #333; }}
        .invoice-meta {{ text-align: right; }}
        .parties {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
        .party {{ width: 45%; }}
        .items {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .items th, .items td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        .items th {{ background: #f8f9fa; }}
        .totals {{ text-align: right; margin: 20px 0; }}
        .totals table {{ margin-left: auto; }}
        .totals td {{ padding: 5px 15px; }}
        .total-row {{ font-size: 18px; font-weight: bold; background: #f8f9fa; }}
        .payment-info {{ background: #f8f9fa; padding: 20px; margin-top: 30px; }}
        .due-date {{ color: #dc3545; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="invoice-header">
        <div>
            <div class="invoice-title">INVOICE</div>
            <div>#{invoice_number_esc}</div>
        </div>
        <div class="invoice-meta">
            <p>Date: {request.invoice_date.strftime('%d.%m.%Y')}</p>
            <p class="due-date">Due: {request.due_date.strftime('%d.%m.%Y')}</p>
        </div>
    </div>

    <div class="parties">
        <div class="party">
            <h4>From:</h4>
            <p><strong>{contractor_name}</strong></p>
            <p>{contractor_address}</p>
            {f'<p>{contractor_email}</p>' if contractor_email else ''}
        </div>
        <div class="party">
            <h4>Bill To:</h4>
            <p><strong>{client_name}</strong></p>
            <p>{client_address}</p>
            {f'<p>PO#: {po_number}</p>' if po_number else ''}
        </div>
    </div>

    {f'<p><strong>Project:</strong> {project_name_esc}</p>' if project_name_esc else ''}
    {f'<p><strong>Contract:</strong> #{contract_number}</p>' if contract_number else ''}

    {items_html}

    <div class="totals">
        <table>
            <tr>
                <td>Subtotal:</td>
                <td>{subtotal:,.2f} {request.currency.value}</td>
            </tr>
            {f'<tr><td>Discount ({request.discount_percent*100:.0f}%):</td><td>-{discount:,.2f} {request.currency.value}</td></tr>' if discount > 0 else ''}
            {f'<tr><td>Tax ({request.tax_rate*100:.0f}%):</td><td>{tax_amount:,.2f} {request.currency.value}</td></tr>' if request.tax_rate > 0 else ''}
            <tr class="total-row">
                <td>TOTAL DUE:</td>
                <td>{total:,.2f} {request.currency.value}</td>
            </tr>
        </table>
    </div>

    <div class="payment-info">
        <h4>Payment Information</h4>
        <p><strong>Bank:</strong> {contractor_bank}</p>
        <p><strong>IBAN:</strong> {contractor_iban}</p>
        <p><strong>SWIFT:</strong> {contractor_swift}</p>
        <p><strong>Terms:</strong> {payment_terms}</p>
        {f'<p><strong>Instructions:</strong> {payment_instructions}</p>' if payment_instructions else ''}
    </div>

    <p style="margin-top: 30px; text-align: center; color: #666;">
        Thank you for your business!
    </p>
</body>
</html>
    """
    return html_content


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/act")
async def generate_act_of_work(request: ActOfWorkRequest):
    """
    Generate Act of Work (Акт виконаних робіт).

    Document confirming work completion and acceptance.
    """
    html = generate_act_html(request)

    if request.format == DocumentFormat.HTML:
        return Response(
            content=html,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=act_{request.act_number}.html"}
        )
    elif request.format == DocumentFormat.PDF:
        # Would need weasyprint or reportlab for PDF
        # For now, return HTML with note
        return Response(
            content=html,
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=act_{request.act_number}.html",
                "X-Note": "Install weasyprint for PDF output",
            }
        )
    else:
        return Response(
            content=html,
            media_type="text/html",
        )


@router.post("/invoice")
async def generate_invoice(request: InvoiceRequest):
    """
    Generate Invoice (Рахунок-фактура).

    Payment invoice for services rendered.
    """
    html = generate_invoice_html(request)

    if request.format == DocumentFormat.HTML:
        return Response(
            content=html,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=invoice_{request.invoice_number}.html"}
        )
    elif request.format == DocumentFormat.PDF:
        return Response(
            content=html,
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=invoice_{request.invoice_number}.html",
                "X-Note": "Install weasyprint for PDF output",
            }
        )
    else:
        return Response(content=html, media_type="text/html")


@router.post("/contract")
async def generate_contract(request: ContractRequest):
    """
    Generate Service Contract.

    Basic service agreement template.
    """
    # For contracts, we'd use a more sophisticated template system
    # For now, return a basic structure
    return {
        "message": "Contract generation",
        "contract_number": request.contract_number,
        "parties": {
            "contractor": request.contractor.name,
            "client": request.client.name,
        },
        "project": request.project_name,
        "total": request.total_price,
        "currency": request.currency.value,
        "note": "Full contract template generation coming soon",
    }


@router.post("/from-analysis/{analysis_id}")
async def generate_from_analysis(
    analysis_id: str,
    document_type: str,  # act, invoice, contract
    contractor: PartyInfo,
    client: PartyInfo,
    currency: Currency = Currency.USD,
    hourly_rate: float = 50.0,
):
    """
    Generate financial document from analysis results.

    Automatically fills in work description, hours, and costs from analysis.
    """
    from app.metrics.storage import metrics_store

    # Get analysis data
    metrics = await metrics_store.get(analysis_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Analysis not found")

    data = metrics.to_flat_dict()

    # Extract relevant info
    total_hours = data.get("cost.hours_typical_total", 100)
    repo_name = data.get("repo.name", "Repository")

    if document_type == "invoice":
        request = InvoiceRequest(
            invoice_number=f"INV-{analysis_id[:8].upper()}",
            invoice_date=date.today(),
            due_date=date.today(),
            contractor=contractor,
            client=client,
            project_name=f"Repository Audit: {repo_name}",
            items=[
                WorkItem(
                    description=f"Repository analysis and audit services for {repo_name}",
                    quantity=total_hours,
                    unit="hours",
                    unit_price=hourly_rate,
                )
            ],
            currency=currency,
            analysis_id=analysis_id,
        )
        return await generate_invoice(request)

    elif document_type == "act":
        request = ActOfWorkRequest(
            act_number=f"ACT-{analysis_id[:8].upper()}",
            act_date=date.today(),
            contractor=contractor,
            client=client,
            project_name=f"Repository Audit: {repo_name}",
            work_period_start=date.today(),
            work_period_end=date.today(),
            work_description=f"Comprehensive repository analysis and technical audit for {repo_name}",
            deliverables=[
                "Technical audit report",
                "Repository health assessment",
                "Technical debt analysis",
                "Cost estimation",
                "Improvement recommendations",
            ],
            items=[
                WorkItem(
                    description="Repository analysis services",
                    quantity=total_hours,
                    unit="hours",
                    unit_price=hourly_rate,
                )
            ],
            currency=currency,
            analysis_id=analysis_id,
        )
        return await generate_act_of_work(request)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown document type: {document_type}")
