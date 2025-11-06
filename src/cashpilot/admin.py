"""SQLAdmin configuration for CashPilot."""

from sqladmin import ModelView
from cashpilot.models import Business, CashSession


class BusinessAdmin(ModelView, model=Business):  # ← Back to this syntax for 0.21.0
    """Admin view for Business (pharmacy locations)."""

    name = "Sucursal"
    name_plural = "Sucursales"
    icon = "fa-solid fa-hospital"

    column_list = [
        Business.id,
        Business.name,
        Business.address,
        Business.phone,
        Business.is_active,
        Business.created_at,
    ]
    column_sortable_list = [Business.name, Business.created_at, Business.is_active]
    column_filterable_list = [Business.is_active, Business.created_at]
    column_searchable_list = [Business.name]

    column_labels = {
        Business.id: "ID",
        Business.name: "Nombre",
        Business.address: "Dirección",
        Business.phone: "Teléfono",
        Business.is_active: "Activo",
        Business.created_at: "Creado",
        Business.updated_at: "Actualizado",
    }

    form_columns = [Business.name, Business.address, Business.phone, Business.is_active]


class CashSessionAdmin(ModelView, model=CashSession):  # ← And this
    """Admin view for CashSession (cash register shifts)."""

    name = "Caja"
    name_plural = "Cajas"
    icon = "fa-solid fa-cash-register"

    column_list = [
        CashSession.id,
        CashSession.business_id,
        CashSession.status,
        CashSession.cashier_name,
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

    column_labels = {
        CashSession.id: "ID",
        CashSession.business_id: "Sucursal ID",
        CashSession.status: "Estado",
        CashSession.cashier_name: "Cajero",
        CashSession.shift_hours: "Horario",
        CashSession.opened_at: "Abierto",
        CashSession.closed_at: "Cerrado",
        CashSession.initial_cash: "Monto Inicial",
        CashSession.final_cash: "Monto Final",
        CashSession.envelope_amount: "Sobre",
        CashSession.credit_card_total: "Tarjeta Crédito",
        CashSession.debit_card_total: "Tarjeta Débito",
        CashSession.bank_transfer_total: "Transferencia",
    }

    form_columns = [
        CashSession.business_id,
        CashSession.cashier_name,
        CashSession.shift_hours,
        CashSession.initial_cash,
        CashSession.final_cash,
        CashSession.envelope_amount,
        CashSession.status,
    ]
