"""
Document Extraction Service.

Extracts structured data from contracts and policies using:
1. Text extraction from PDF/DOCX/TXT
2. Pattern-based extraction (regex)
3. LLM-based extraction (structured JSON output)
4. Hybrid approach with confidence scoring
"""
import re
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID
from dataclasses import dataclass, field

from app.llm.client import get_llm_client
from app.llm.models import LLMRequest, TaskType

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of document extraction."""
    success: bool
    method: str  # "regex", "llm", "hybrid"
    confidence: int  # 0-100

    # Contract metadata
    contract_number: Optional[str] = None
    contract_title: Optional[str] = None
    contract_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Financial
    total_amount: Optional[int] = None  # in cents
    currency: Optional[str] = None

    # Parties
    client_name: Optional[str] = None
    client_address: Optional[str] = None
    contractor_name: Optional[str] = None
    contractor_address: Optional[str] = None

    # Structured data
    work_plan: list = field(default_factory=list)
    budget_breakdown: list = field(default_factory=list)
    milestones: list = field(default_factory=list)
    deliverables: list = field(default_factory=list)
    indicators: list = field(default_factory=list)
    policies: list = field(default_factory=list)

    # Raw sections for reference
    raw_sections: dict = field(default_factory=dict)

    # Errors
    error: Optional[str] = None


# =============================================================================
# TEXT EXTRACTION
# =============================================================================


async def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=content, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("PyMuPDF not installed, trying pdfplumber")
        try:
            import pdfplumber
            import io

            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text_parts.append(page.extract_text() or "")
                return "\n".join(text_parts)
        except ImportError:
            logger.error("No PDF library available")
            return ""


async def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        from docx import Document
        import io

        doc = Document(io.BytesIO(content))
        text_parts = []
        for para in doc.paragraphs:
            text_parts.append(para.text)
        return "\n".join(text_parts)
    except ImportError:
        logger.error("python-docx not installed")
        return ""


async def extract_text(content: bytes, mime_type: str) -> str:
    """Extract text from document based on MIME type."""
    if "pdf" in mime_type:
        return await extract_text_from_pdf(content)
    elif "docx" in mime_type or "word" in mime_type:
        return await extract_text_from_docx(content)
    elif "text" in mime_type:
        return content.decode("utf-8", errors="replace")
    else:
        # Try decoding as text
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            return ""


# =============================================================================
# PATTERN-BASED EXTRACTION
# =============================================================================


# Common patterns for Ukrainian/English contracts
PATTERNS = {
    # Contract number patterns
    "contract_number": [
        r"(?:Договір|Контракт|Contract|Agreement)\s*(?:№|#|No\.?)\s*([\w\-/]+)",
        r"№\s*([\w\-/]+)\s*(?:від|from|dated)",
    ],

    # Date patterns (DD.MM.YYYY, YYYY-MM-DD, etc.)
    "date": [
        r"(\d{2})[./](\d{2})[./](\d{4})",  # DD.MM.YYYY or DD/MM/YYYY
        r"(\d{4})-(\d{2})-(\d{2})",  # YYYY-MM-DD
        r"(\d{1,2})\s+(січня|лютого|березня|квітня|травня|червня|липня|серпня|вересня|жовтня|листопада|грудня)\s+(\d{4})",  # Ukrainian
        r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",  # English
    ],

    # Amount patterns
    "amount": [
        r"(?:на суму|total amount|сума|amount)[\s:]*(\d[\d\s,\.]+)\s*(грн|UAH|USD|EUR|$|€)",
        r"(\d[\d\s,\.]+)\s*(грн|UAH|USD|EUR)\s*(?:\(|включаючи|including)",
        r"(?:вартість|ціна|price|cost)[\s:]*(\d[\d\s,\.]+)\s*(грн|UAH|USD|EUR)",
    ],

    # Party patterns
    "parties": [
        r"(?:Замовник|Client|Customer)[\s:]+([^\n,]+)",
        r"(?:Виконавець|Contractor|Supplier)[\s:]+([^\n,]+)",
    ],

    # Section headers
    "sections": {
        "work_plan": [
            r"(?:Календарний план|Work Plan|План робіт|Schedule)",
            r"(?:Етапи виконання|Stages|Phases)",
        ],
        "budget": [
            r"(?:Кошторис|Budget|Бюджет)",
            r"(?:Фінансування|Funding|Financial)",
        ],
        "deliverables": [
            r"(?:Результати|Deliverables|Outputs)",
            r"(?:Продукти|Products|Очікувані результати)",
        ],
    }
}


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime."""
    # Ukrainian month names
    uk_months = {
        "січня": 1, "лютого": 2, "березня": 3, "квітня": 4,
        "травня": 5, "червня": 6, "липня": 7, "серпня": 8,
        "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12,
    }

    # English month names
    en_months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }

    try:
        # Try DD.MM.YYYY
        if match := re.match(r"(\d{2})[./](\d{2})[./](\d{4})", date_str):
            return datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))

        # Try YYYY-MM-DD
        if match := re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str):
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))

        # Try Ukrainian month
        for month_name, month_num in uk_months.items():
            if month_name in date_str.lower():
                if match := re.search(rf"(\d{{1,2}})\s+{month_name}\s+(\d{{4}})", date_str.lower()):
                    return datetime(int(match.group(2)), month_num, int(match.group(1)))

        # Try English month
        for month_name, month_num in en_months.items():
            if month_name in date_str.lower():
                if match := re.search(rf"(\d{{1,2}})\s+{month_name}\s+(\d{{4}})", date_str.lower()):
                    return datetime(int(match.group(2)), month_num, int(match.group(1)))

    except (ValueError, AttributeError):
        pass

    return None


def parse_amount(amount_str: str) -> tuple[Optional[int], Optional[str]]:
    """Parse amount string to cents and currency."""
    # Clean the amount string
    amount_str = amount_str.strip()

    # Find currency
    currency = None
    if "грн" in amount_str.lower() or "uah" in amount_str.lower():
        currency = "UAH"
    elif "$" in amount_str or "usd" in amount_str.lower():
        currency = "USD"
    elif "€" in amount_str or "eur" in amount_str.lower():
        currency = "EUR"

    # Extract number
    number_str = re.sub(r"[^\d,.]", "", amount_str)
    if not number_str:
        return None, currency

    # Handle different decimal separators
    # If last separator is comma and followed by 2 digits, treat as decimal
    if re.match(r".*,\d{2}$", number_str):
        number_str = number_str.replace(".", "").replace(",", ".")
    else:
        number_str = number_str.replace(",", "")

    try:
        amount_float = float(number_str)
        amount_cents = int(amount_float * 100)
        return amount_cents, currency
    except ValueError:
        return None, currency


async def extract_with_patterns(text: str) -> ExtractionResult:
    """Extract data using regex patterns."""
    result = ExtractionResult(
        success=True,
        method="regex",
        confidence=50,  # Start with medium confidence
    )

    # Extract contract number
    for pattern in PATTERNS["contract_number"]:
        if match := re.search(pattern, text, re.IGNORECASE):
            result.contract_number = match.group(1).strip()
            result.confidence += 5
            break

    # Extract dates
    dates_found = []
    for pattern in PATTERNS["date"]:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            date_str = match.group(0)
            if parsed := parse_date(date_str):
                dates_found.append(parsed)

    if dates_found:
        dates_found.sort()
        result.contract_date = dates_found[0]
        result.confidence += 5
        if len(dates_found) >= 2:
            result.start_date = dates_found[0]
            result.end_date = dates_found[-1]
            result.confidence += 5

    # Extract amounts
    for pattern in PATTERNS["amount"]:
        if match := re.search(pattern, text, re.IGNORECASE):
            amount_str = match.group(1) + " " + match.group(2)
            cents, currency = parse_amount(amount_str)
            if cents:
                result.total_amount = cents
                result.currency = currency
                result.confidence += 10
                break

    # Extract parties
    for pattern in PATTERNS["parties"]:
        if match := re.search(pattern, text, re.IGNORECASE):
            party_name = match.group(1).strip()
            if "замовник" in pattern.lower() or "client" in pattern.lower():
                result.client_name = party_name
            else:
                result.contractor_name = party_name
            result.confidence += 5

    # Cap confidence at 70 for regex-only
    result.confidence = min(result.confidence, 70)

    return result


# =============================================================================
# LLM-BASED EXTRACTION
# =============================================================================


CONTRACT_EXTRACTION_PROMPT = """You are a document analysis expert. Extract structured data from the following contract/document text.

Return ONLY a valid JSON object with the following structure:
{
  "contract_number": "string or null",
  "contract_title": "string or null",
  "contract_date": "YYYY-MM-DD or null",
  "start_date": "YYYY-MM-DD or null",
  "end_date": "YYYY-MM-DD or null",
  "total_amount": number_in_cents_or_null,
  "currency": "UAH|USD|EUR or null",
  "client_name": "string or null",
  "client_address": "string or null",
  "contractor_name": "string or null",
  "contractor_address": "string or null",
  "work_plan": [
    {"phase": "string", "description": "string", "duration_days": number, "deliverables": ["string"]}
  ],
  "budget_breakdown": [
    {"category": "string", "amount_cents": number, "description": "string"}
  ],
  "milestones": [
    {"name": "string", "date": "YYYY-MM-DD", "deliverable": "string", "payment_cents": number}
  ],
  "deliverables": [
    {"name": "string", "description": "string", "due_date": "YYYY-MM-DD or null"}
  ],
  "indicators": [
    {"name": "string", "target": "string", "measurement": "string"}
  ],
  "policies": [
    {"type": "string", "requirement": "string", "source_text": "string"}
  ]
}

Important rules:
1. Return ONLY the JSON object, no explanations
2. Use null for missing values, don't guess
3. All amounts should be in cents (multiply by 100)
4. Dates must be in YYYY-MM-DD format
5. Extract as much structured data as possible
6. For policies, extract any compliance requirements, data protection clauses, etc.

Document text:
{text}"""


POLICY_EXTRACTION_PROMPT = """You are a compliance document analyst. Extract policies and requirements from the following document.

Return ONLY a valid JSON object with:
{
  "document_title": "string or null",
  "document_type": "policy|standard|guideline|procedure",
  "effective_date": "YYYY-MM-DD or null",
  "version": "string or null",
  "policies": [
    {
      "id": "string",
      "type": "data_protection|security|financial|operational|compliance|other",
      "title": "string",
      "requirement": "string (the actual requirement)",
      "mandatory": true/false,
      "source_text": "exact text from document",
      "applicable_to": ["string"]
    }
  ],
  "definitions": [
    {"term": "string", "definition": "string"}
  ],
  "references": [
    {"type": "law|standard|internal", "name": "string", "id": "string or null"}
  ]
}

Return only JSON, no explanations.

Document text:
{text}"""


async def extract_with_llm(
    text: str,
    task_type: TaskType = TaskType.CONTRACT_EXTRACTION,
) -> ExtractionResult:
    """Extract data using LLM."""
    result = ExtractionResult(
        success=False,
        method="llm",
        confidence=0,
    )

    # Truncate text if too long (keep first ~15000 chars)
    max_chars = 15000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... document truncated ...]"

    # Select prompt based on task type
    if task_type == TaskType.POLICY_EXTRACTION:
        prompt = POLICY_EXTRACTION_PROMPT.format(text=text)
    else:
        prompt = CONTRACT_EXTRACTION_PROMPT.format(text=text)

    # Query LLM
    client = get_llm_client()
    request = LLMRequest(
        system_prompt="You are a document extraction assistant. Return only valid JSON.",
        user_prompt=prompt,
        task_type=task_type,
        max_tokens=4000,
        temperature=0.1,  # Low temperature for consistent extraction
    )

    try:
        response = await client.query(request)

        if not response.success:
            result.error = response.error
            return result

        # Parse JSON from response
        response_text = response.text.strip()

        # Try to extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if not json_match:
            result.error = "No JSON found in response"
            return result

        data = json.loads(json_match.group())

        # Map to result
        result.success = True
        result.confidence = 85  # High confidence for successful LLM extraction

        result.contract_number = data.get("contract_number")
        result.contract_title = data.get("contract_title")

        # Parse dates
        for date_field in ["contract_date", "start_date", "end_date"]:
            if date_str := data.get(date_field):
                try:
                    setattr(result, date_field, datetime.fromisoformat(date_str))
                except ValueError:
                    pass

        result.total_amount = data.get("total_amount")
        result.currency = data.get("currency")
        result.client_name = data.get("client_name")
        result.client_address = data.get("client_address")
        result.contractor_name = data.get("contractor_name")
        result.contractor_address = data.get("contractor_address")

        # Structured data
        result.work_plan = data.get("work_plan", [])
        result.budget_breakdown = data.get("budget_breakdown", [])
        result.milestones = data.get("milestones", [])
        result.deliverables = data.get("deliverables", [])
        result.indicators = data.get("indicators", [])
        result.policies = data.get("policies", [])

    except json.JSONDecodeError as e:
        result.error = f"JSON parse error: {e}"
    except Exception as e:
        result.error = f"LLM extraction error: {e}"
        logger.error(f"LLM extraction failed: {e}")

    return result


# =============================================================================
# HYBRID EXTRACTION
# =============================================================================


async def extract_hybrid(
    text: str,
    task_type: TaskType = TaskType.CONTRACT_EXTRACTION,
) -> ExtractionResult:
    """
    Hybrid extraction combining patterns and LLM.

    1. First try pattern-based for quick results
    2. Then use LLM to fill gaps and extract complex structures
    3. Merge results with conflict resolution
    """
    # Pattern-based extraction
    pattern_result = await extract_with_patterns(text)

    # LLM extraction
    llm_result = await extract_with_llm(text, task_type)

    # Merge results
    final = ExtractionResult(
        success=pattern_result.success or llm_result.success,
        method="hybrid",
        confidence=0,
    )

    # Helper to pick best value
    def pick_best(pattern_val, llm_val):
        if llm_val is not None:
            return llm_val
        return pattern_val

    # Merge scalar fields
    final.contract_number = pick_best(pattern_result.contract_number, llm_result.contract_number)
    final.contract_title = pick_best(pattern_result.contract_title, llm_result.contract_title)
    final.contract_date = pick_best(pattern_result.contract_date, llm_result.contract_date)
    final.start_date = pick_best(pattern_result.start_date, llm_result.start_date)
    final.end_date = pick_best(pattern_result.end_date, llm_result.end_date)
    final.total_amount = pick_best(pattern_result.total_amount, llm_result.total_amount)
    final.currency = pick_best(pattern_result.currency, llm_result.currency)
    final.client_name = pick_best(pattern_result.client_name, llm_result.client_name)
    final.client_address = pick_best(pattern_result.client_address, llm_result.client_address)
    final.contractor_name = pick_best(pattern_result.contractor_name, llm_result.contractor_name)
    final.contractor_address = pick_best(pattern_result.contractor_address, llm_result.contractor_address)

    # For lists, prefer LLM results (more structured)
    final.work_plan = llm_result.work_plan or pattern_result.work_plan
    final.budget_breakdown = llm_result.budget_breakdown or pattern_result.budget_breakdown
    final.milestones = llm_result.milestones or pattern_result.milestones
    final.deliverables = llm_result.deliverables or pattern_result.deliverables
    final.indicators = llm_result.indicators or pattern_result.indicators
    final.policies = llm_result.policies or pattern_result.policies

    # Calculate confidence
    fields_extracted = sum([
        1 for f in [
            final.contract_number, final.contract_title, final.contract_date,
            final.total_amount, final.client_name, final.contractor_name
        ] if f is not None
    ])

    lists_extracted = sum([
        1 for lst in [
            final.work_plan, final.budget_breakdown, final.milestones,
            final.deliverables, final.indicators, final.policies
        ] if lst
    ])

    # Base confidence on extraction success
    if llm_result.success:
        final.confidence = 75 + (fields_extracted * 2) + (lists_extracted * 3)
    else:
        final.confidence = 40 + (fields_extracted * 3)

    final.confidence = min(final.confidence, 98)  # Cap at 98

    return final


# =============================================================================
# MAIN EXTRACTION SERVICE
# =============================================================================


class DocumentExtractionService:
    """Service for extracting data from documents."""

    async def extract(
        self,
        content: bytes,
        mime_type: str,
        method: str = "hybrid",  # "regex", "llm", "hybrid"
        task_type: TaskType = TaskType.CONTRACT_EXTRACTION,
    ) -> ExtractionResult:
        """
        Extract structured data from document.

        Args:
            content: Document bytes
            mime_type: MIME type of document
            method: Extraction method ("regex", "llm", "hybrid")
            task_type: Type of extraction task

        Returns:
            ExtractionResult with extracted data
        """
        # Extract text first
        text = await extract_text(content, mime_type)

        if not text.strip():
            return ExtractionResult(
                success=False,
                method=method,
                confidence=0,
                error="Could not extract text from document",
            )

        # Store raw text in sections
        raw_sections = {"full_text": text[:5000]}  # Store first 5000 chars

        # Run extraction based on method
        if method == "regex":
            result = await extract_with_patterns(text)
        elif method == "llm":
            result = await extract_with_llm(text, task_type)
        else:  # hybrid
            result = await extract_hybrid(text, task_type)

        result.raw_sections = raw_sections
        return result

    async def extract_from_text(
        self,
        text: str,
        method: str = "hybrid",
        task_type: TaskType = TaskType.CONTRACT_EXTRACTION,
    ) -> ExtractionResult:
        """Extract from raw text (for already extracted content)."""
        if method == "regex":
            return await extract_with_patterns(text)
        elif method == "llm":
            return await extract_with_llm(text, task_type)
        else:
            return await extract_hybrid(text, task_type)


# Singleton instance
extraction_service = DocumentExtractionService()
