"""SQLAdmin configuration for CashPilot."""

from markupsafe import Markup
from sqladmin import ModelView
from wtforms import SelectField

from cashpilot.core.db import AsyncSessionLocal
from cashpilot.core.validation import validate_session_dates
from cashpilot.models import Business, CashSession


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


class CashSessionAdmin(ModelView, model=CashSession):
    """Admin view for CashSession (cash register shifts)."""

    name = "Caja"
    name_plural = "Cajas"
    icon = "fa-solid fa-cash-register"

    form_columns = [
        "business",
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
        CashSession.closing_ticket,
        CashSession.notes,
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

    column_list = [
        CashSession.status,
        CashSession.cashier_name,
        "business.name",
        CashSession.opened_at,
        CashSession.closed_at,
        CashSession.initial_cash,
        CashSession.final_cash,
    ]
    column_sortable_list = [
        CashSession.opened_at,
        CashSession.status,
        CashSession.cashier_name,
    ]
    column_filterable_list = [CashSession.status, CashSession.opened_at]
    column_searchable_list = [CashSession.cashier_name]

    column_default_sort = [
        (CashSession.opened_at, True),
        ("business.name", False),
    ]

    column_details_list = [
        CashSession.id,
        CashSession.business_id,
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
        CashSession.notes,
    ]

    column_labels = {
        CashSession.id: "ID",
        CashSession.business_id: "Sucursal",
        "business": "Sucursal",
        CashSession.status: "Estado",
        CashSession.cashier_name: "Cajero",
        CashSession.opened_at: "Abierto",
        CashSession.closed_at: "Cerrado",
        CashSession.initial_cash: "Monto Inicial",
        CashSession.final_cash: "Monto Final",
        CashSession.envelope_amount: "Sobre",
        CashSession.credit_card_total: "Tarjeta Crédito",
        CashSession.debit_card_total: "Tarjeta Débito",
        CashSession.bank_transfer_total: "Transferencia",
        CashSession.notes: "Notas",
        "business.name": "Sucursal",
    }

    async def on_model_change(self, data: dict, model, is_created: bool, request) -> None:
        """Hook called before save - validate dates and detect conflicts."""

        # Validate dates if closed_at is being set or updated
        if data.get("closed_at"):
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
            }
            for key, value in data.items():
                if key in safe_fields and hasattr(model, key):
                    setattr(model, key, value)

            async with AsyncSessionLocal() as db:
                # Now conflicts are checked with NEW dates
                conflicts = await model.get_conflicting_sessions(db)
                model.has_conflict = len(conflicts) > 0
                data["has_conflict"] = model.has_conflict

    column_formatters = {
        CashSession.status: lambda m, a: (
            Markup(
                '<span style="background-color: #fca5a5; color: #991b1b; '
                'padding: 4px 8px; border-radius: 4px; font-weight: 500;">⚠ CONFLICTO</span>'
            )
            if m.has_conflict
            else (
                Markup(
                    '<span style="background-color: #fef3c7; color: #92400e; '
                    'padding: 2px 8px; border-radius: 4px; font-weight: 500;">⏰ ABIERTA</span>'
                )
                if m.status == "OPEN"
                else Markup(
                    '<span style="background-color: #d1fae5; color: #065f46; '
                    'padding: 2px 8px; border-radius: 4px; font-weight: 500;">✓ CERRADA</span>'
                )
            )
        ),
        CashSession.opened_at: lambda m, a: (
            m.opened_at.strftime("%d/%m/%Y %H:%M") if m.opened_at else "-"
        ),
        CashSession.closed_at: lambda m, a: (
            m.closed_at.strftime("%d/%m/%Y %H:%M")
            if m.closed_at
            else Markup(
                '<span style="background-color: #fee2e2; color: #991b1b; '
                'padding: 2px 8px; border-radius: 4px; font-weight: 500;">⚠ Sin cerrar</span>'
            )
        ),
        CashSession.initial_cash: lambda m, a: (
            f"₲ {int(m.initial_cash):,}" if m.initial_cash else "-"
        ),
        CashSession.final_cash: lambda m, a: (f"₲ {int(m.final_cash):,}" if m.final_cash else "-"),
        CashSession.envelope_amount: lambda m, a: (
            f"₲ {int(m.envelope_amount):,}" if m.envelope_amount else "-"
        ),
        CashSession.credit_card_total: lambda m, a: (
            f"₲ {int(m.credit_card_total):,}" if m.credit_card_total else "-"
        ),
        CashSession.debit_card_total: lambda m, a: (
            f"₲ {int(m.debit_card_total):,}" if m.debit_card_total else "-"
        ),
        CashSession.bank_transfer_total: lambda m, a: (
            f"₲ {int(m.bank_transfer_total):,}" if m.bank_transfer_total else "-"
        ),
    }
