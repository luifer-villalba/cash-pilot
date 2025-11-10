"""SQLAdmin configuration for CashPilot."""


from sqladmin import ModelView

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
        (CashSession.opened_at, True),  # True = descending
        ("business.name", False),  # False = ascending
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

    column_formatters = {
        CashSession.opened_at: lambda m, a: (
            m.opened_at.strftime("%d/%m/%Y %H:%M") if m.opened_at else "-"
        ),
        CashSession.closed_at: lambda m, a: (
            m.closed_at.strftime("%d/%m/%Y %H:%M") if m.closed_at else "⏰ Abierta"
        ),
        CashSession.initial_cash: lambda m, a: (
            f"₲ {int(m.initial_cash):,}" if m.initial_cash else "-"
        ),
        CashSession.final_cash: lambda m, a: f"₲ {int(m.final_cash):,}" if m.final_cash else "-",
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
