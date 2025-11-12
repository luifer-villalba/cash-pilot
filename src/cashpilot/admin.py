# File: src/cashpilot/admin.py
# SQLAdmin configuration for CashPilot - Operational Dashboard

from markupsafe import Markup
from sqladmin import ModelView
from wtforms import SelectField

from cashpilot.core.db import AsyncSessionLocal
from cashpilot.models import Business, CashSession

# ==================== HELPER FUNCTIONS ====================


def _format_schedule(session) -> str:
    """Format schedule as: DD/MM/YYYY HH:MM - HH:MM (or pending close)."""
    if not session.opened_at:
        return "-"

    opened = session.opened_at.strftime("%d/%m/%Y %H:%M")

    if session.closed_at:
        closed_time = session.closed_at.strftime("%H:%M")
        return f"{opened} - {closed_time}"
    else:
        return Markup(
            f'{opened} - <span style="color: #d97706; font-weight: 500;">(sin cerrar)</span>'
        )


def _format_currency(amount) -> str:
    """Format amount as: ₲ 1,234,567."""
    if amount is None or amount == 0:
        return "₲ 0"
    return f"₲ {int(amount):,}"


def _format_status_badge(session) -> Markup:
    """Status indicator with visual styling."""
    if session.has_conflict:
        return Markup(
            '<span style="background-color: #fca5a5; color: #991b1b; '
            'padding: 4px 8px; border-radius: 4px; font-weight: 500;">⚠ CONFLICTO</span>'
        )
    elif session.status == "OPEN":
        return Markup(
            '<span style="background-color: #fef3c7; color: #92400e; '
            'padding: 2px 8px; border-radius: 4px; font-weight: 500;">⏰ ABIERTA</span>'
        )
    else:
        return Markup(
            '<span style="background-color: #d1fae5; color: #065f46; '
            'padding: 2px 8px; border-radius: 4px; font-weight: 500;">✓ CERRADA</span>'
        )


# ==================== BUSINESS ADMIN ====================


class BusinessAdmin(ModelView, model=Business):
    """Admin view for Business (pharmacy locations)."""

    name = "Sucursal"
    name_plural = "Sucursales"
    icon = "fa-solid fa-hospital"

    column_list = [
        Business.name,
        Business.address,
        Business.phone,
        Business.is_active,
        Business.created_at,
    ]

    column_sortable_list = [Business.name, Business.created_at, Business.is_active]
    column_filterable_list = [Business.is_active, Business.created_at]
    column_searchable_list = [Business.name]

    column_details_list = [
        Business.id,
        Business.name,
        Business.address,
        Business.phone,
        Business.is_active,
        Business.created_at,
        Business.updated_at,
    ]

    column_labels = {
        Business.id: "ID",
        Business.name: "Nombre",
        Business.address: "Dirección",
        Business.phone: "Teléfono",
        Business.is_active: "Activo",
        Business.created_at: "Creado",
        Business.updated_at: "Actualizado",
    }

    column_formatters = {
        Business.created_at: lambda m, a: (
            m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "-"
        ),
        Business.updated_at: lambda m, a: (
            m.updated_at.strftime("%d/%m/%Y %H:%M") if m.updated_at else "-"
        ),
    }


# ==================== CASH SESSION ADMIN ====================


class CashSessionAdmin(ModelView, model=CashSession):
    """Admin view for CashSession (operational dashboard for reconciliation)."""

    name = "Caja"
    name_plural = "Cajas"
    icon = "fa-solid fa-cash-register"

    # ==================== FORM (for create/edit) ====================
    form_columns = [
        "business",  # 1. Sucursal
        CashSession.status,  # 2. Estado
        CashSession.cashier_name,  # 3. Responsable
        CashSession.opened_at,  # 4. Horario
        CashSession.closed_at,  # 5. Horario Cierre
        CashSession.initial_cash,  # 6. Monto Inicial
        CashSession.final_cash,  # 7. Caja Final
        CashSession.envelope_amount,  # 8. Depósito Bancario
        CashSession.credit_card_total,  # 9. TC
        CashSession.debit_card_total,  # 10. TD
        CashSession.bank_transfer_total,  # 11. Transferencias
        CashSession.expenses,  # 12. Gastos
        CashSession.closing_ticket,  # 13. Ticket
        CashSession.notes,  # 14. Notas
    ]

    form_overrides = {
        "status": SelectField,
    }

    form_args = {
        "status": {
            "choices": [("OPEN", "Abierta"), ("CLOSED", "Cerrada")],
            "default": "OPEN",
        }
    }

    # ==================== LIST VIEW (Operational Dashboard) ====================
    # Same order as form_columns (first 11 fields for list view)
    column_list = [
        "business.name",  # 1. Sucursal
        CashSession.status,  # 2. Estado
        CashSession.cashier_name,  # 3. Responsable
        CashSession.opened_at,  # 4. Horario
        CashSession.initial_cash,  # 5. Monto Inicial
        CashSession.final_cash,  # 6. Caja Final
        CashSession.envelope_amount,  # 7. Depósito Bancario
        CashSession.credit_card_total,  # 8. TC
        CashSession.debit_card_total,  # 9. TD
        CashSession.bank_transfer_total,  # 10. Transferencias
        CashSession.expenses,  # 11. Gastos
    ]

    column_sortable_list = [
        CashSession.opened_at,
        CashSession.status,
        CashSession.cashier_name,
        "business.name",
    ]

    column_filterable_list = [
        CashSession.status,
        CashSession.opened_at,
        "business.name",
    ]

    column_searchable_list = [
        CashSession.cashier_name,
        "business.name",
    ]

    column_default_sort = [
        (CashSession.opened_at, True),
        ("business.name", False),
    ]

    # ==================== DETAILS VIEW ====================
    column_details_list = [
        CashSession.id,
        "business.name",
        CashSession.status,
        CashSession.cashier_name,
        CashSession.opened_at,
        CashSession.closed_at,
        CashSession.initial_cash,
        CashSession.final_cash,
        CashSession.envelope_amount,
        CashSession.credit_card_total,
        CashSession.debit_card_total,
        CashSession.bank_transfer_total,
        CashSession.expenses,
        CashSession.closing_ticket,
        CashSession.notes,
    ]

    # ==================== LABELS (Spanish) ====================
    column_labels = {
        CashSession.id: "ID",
        CashSession.business_id: "Sucursal",
        "business": "Sucursal",
        "business.name": "Sucursal",
        CashSession.status: "Estado",
        CashSession.cashier_name: "Responsable",
        CashSession.opened_at: "Horario",
        CashSession.closed_at: "Cerrado",
        CashSession.initial_cash: "Monto Inicial",
        CashSession.final_cash: "Caja Final",
        CashSession.envelope_amount: "Depósito Bancario",
        CashSession.credit_card_total: "TC",
        CashSession.debit_card_total: "TD",
        CashSession.bank_transfer_total: "Transferencias",
        CashSession.expenses: "Gastos",
        CashSession.closing_ticket: "Ticket",
        CashSession.notes: "Notas",
    }

    # ==================== FORMATTERS (Display Logic) ====================
    column_formatters = {
        # Status with visual badge
        CashSession.status: lambda m, a: _format_status_badge(m),
        # Schedule: "15/11/2025 08:00 - 15:00" or "15/11/2025 08:00 - (sin cerrar)"
        CashSession.opened_at: lambda m, a: _format_schedule(m),
        # Currency formatting with Guaraní symbol
        CashSession.initial_cash: lambda m, a: _format_currency(m.initial_cash),
        CashSession.final_cash: lambda m, a: _format_currency(m.final_cash if m.final_cash else 0),
        CashSession.envelope_amount: lambda m, a: _format_currency(m.envelope_amount),
        CashSession.credit_card_total: lambda m, a: _format_currency(m.credit_card_total),
        CashSession.debit_card_total: lambda m, a: _format_currency(m.debit_card_total),
        CashSession.bank_transfer_total: lambda m, a: _format_currency(m.bank_transfer_total),
        CashSession.expenses: lambda m, a: _format_currency(m.expenses if m.expenses else 0),
    }

    async def on_model_change(self, data: dict, model, is_created: bool, request) -> None:
        """Hook called before save - validate dates and detect conflicts."""

        # Validate dates if closed_at is being set or updated
        if data.get("closed_at"):
            from cashpilot.core.validation import validate_session_dates

            opened_at = data.get("opened_at") or model.opened_at
            closed_at = data.get("closed_at")

            date_error = await validate_session_dates(opened_at, closed_at)
            if date_error:
                raise ValueError(date_error["message"])

        # Detect conflicts with NEW dates (not old ones)
        if not is_created and (data.get("opened_at") or data.get("closed_at")):
            # Apply only scalar fields (skip relationships like 'business')
            safe_fields = {
                "opened_at",
                "closed_at",
                "status",
                "initial_cash",
                "final_cash",
                "envelope_amount",
                "credit_card_total",
                "debit_card_total",
                "bank_transfer_total",
                "closing_ticket",
                "notes",
                "cashier_name",
                "expenses",
            }
            for key, value in data.items():
                if key in safe_fields and hasattr(model, key):
                    setattr(model, key, value)

            async with AsyncSessionLocal() as db:
                # Now conflicts are checked with NEW dates
                conflicts = await model.get_conflicting_sessions(db)
                model.has_conflict = len(conflicts) > 0
                data["has_conflict"] = model.has_conflict
