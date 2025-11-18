"""Tests for Business cashier management API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from .factories import BusinessFactory


class TestGetCashiers:
    """Test cashier retrieval endpoint."""

    async def test_get_cashiers_empty_list(self, client: AsyncClient, db_session: AsyncSession):
        """Test getting cashiers for new business with empty list."""
        business = await BusinessFactory.create(db_session, name="Farmacia Nueva", cashiers=[])
        await db_session.commit()

        response = await client.get(f"/businesses/{business.id}/cashiers")

        assert response.status_code == 200
        data = response.json()
        assert data["cashiers"] == []

    async def test_get_cashiers_not_found(self, client: AsyncClient):
        """Test getting cashiers for non-existent business."""
        response = await client.get(
            "/businesses/00000000-0000-0000-0000-000000000000/cashiers"
        )
        assert response.status_code == 404


class TestUpdateBusinessCashiers:
    """Test updating cashier list via PUT endpoint."""

    async def test_update_business_cashiers_via_put(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test updating business cashier list via PUT."""
        business = await BusinessFactory.create(db_session, name="Farmacia Update", cashiers=[])
        await db_session.commit()

        update_data = {"cashiers": ["María", "Juan", "Carlos"]}
        response = await client.put(
            f"/businesses/{business.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cashiers"] == ["María", "Juan", "Carlos"]
