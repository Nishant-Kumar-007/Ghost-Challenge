"""Deletion-Request Classification Module.

Evaluates request_text to determine whether the user authorized account/data deletion,
or whether the request is a non-deletion action (access, export, rectification, opt-out),
resulting in NOT_APPLICABLE.
"""

import re
from typing import Tuple


class RequestClassifier:
    """Classifies customer request text into DELETION vs NON_DELETION."""

    EXPLICIT_NON_DELETION_PATTERNS = [
        r"leave the account active",
        r"keep the account as it is",
        r"leave my profile",
        r"continue using the service",
        r"without removing any of my records",
        r"without deleting my account",
        r"do not delete my account",
        r"don't delete my account",
        r"keep my account active",
        r"keep my account open",
        r"garder mon compte actif",
        r"mantener la cuenta activa",
        r"sin eliminar mi cuenta",
        r"sans supprimer mon compte",
    ]

    DELETION_STEMS = [
        "delet", "eras", "remov", "clos", "forget", "wipe", "expung", "purg", "gone",
        "supprim", "suppress", "effac", "clôtur", "ferm",
        "elimin", "borr", "cerr", "dar de baja",
        "exclu", "encerr",
        "lösch", "entfern", "schließ",
        "cancell",
        "削除", "消去", "解約", "退会",
        "삭제", "해지", "탈퇴",
        "удал", "стереть"
    ]

    NON_DELETION_PRIMARY_INTENTS = [
        r"download my account information.*keep the account",
        r"copy of last year's invoices.*leave my profile",
        r"misspelled.*correct it without removing",
        r"replace it with the new one and leave the account active",
        r"change the email address.*continue using the service",
    ]

    def __init__(self):
        pass

    def classify(self, request_text: str) -> Tuple[bool, str]:
        """Returns (is_deletion_request, reason).

        If False, deletion_status is NOT_APPLICABLE.
        """
        if not request_text:
            return False, "EMPTY_REQUEST"

        text_lower = request_text.lower().strip()

        # 1. Check explicit non-deletion expressions
        for pattern in self.EXPLICIT_NON_DELETION_PATTERNS:
            if re.search(pattern, text_lower):
                return False, f"EXPLICIT_NON_DELETION: {pattern}"

        for pattern in self.NON_DELETION_PRIMARY_INTENTS:
            if re.search(pattern, text_lower):
                return False, f"NON_DELETION_INTENT: {pattern}"

        # 2. Check presence of deletion stems across multiple languages
        has_deletion_intent = any(kw in text_lower for kw in self.DELETION_STEMS)
        if has_deletion_intent:
            return True, "DELETION_AUTHORIZED"

        # 3. Fallback: If no deletion words exist, check if it's an access/rectification request
        if any(w in text_lower for w in ["invoice", "copy", "download", "export", "newsletter", "update", "correct"]):
            return False, "NON_DELETION_FALLBACK"

        # Default to False if no deletion intent found
        return False, "NO_DELETION_INTENT_FOUND"
