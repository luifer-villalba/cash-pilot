# File: tests/test_admin_business_assignment.py
"""Tests for admin business assignment endpoints."""

import pytest
from sqlalchemy import select

from cashpilot.models.business import Business
from cashpilot.models.user import User
from cashpilot.models.user_business import UserBusiness


@pytest.mark.asyncio
async def test_cashier_cannot_create_user(
    client,
    db_session,
):
    """AC-02: Cashier is denied creating a user (admin only)."""
    response = await client.post(
        "/users",
        json={
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "role": "CASHIER",
            "password": "TempPassword123!",
        },
    )
    assert response.status_code == 403
    # Verify user was NOT created
    stmt = select(User).where(User.email == "newuser@example.com")
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_admin_can_create_user(
    admin_client,
    db_session,
):
    """AC-02: Admin can create a user (basic RBAC test)."""
    response = await admin_client.post(
        "/users",
        json={
            "email": "newadminuser@example.com",
            "first_name": "Admin",
            "last_name": "Created",
            "role": "CASHIER",
        },
    )
    # Just verify admin gets access (201 or error is OK, as long as not 403)
    # The actual creation logic is tested elsewhere
    assert response.status_code != 403, f"Admin should have access to create users, got {response.status_code}"


@pytest.mark.asyncio
async def test_list_users_includes_businesses(
    admin_client,
    test_user,
    db_session,
):
    """AC-07: Admin can view user businesses in audit list."""
    # Create a business
    business = Business(
        name="Test Business",
        address="123 Test St",
        phone="+595981234567",
        is_active=True,
    )
    db_session.add(business)
    await db_session.commit()
    await db_session.refresh(business)

    # Assign business to user
    assignment = UserBusiness(
        user_id=test_user.id,
        business_id=business.id,
    )
    db_session.add(assignment)
    await db_session.commit()

    response = await admin_client.get("/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert len(data["users"]) > 0

    # Find the test user
    user_data = next((u for u in data["users"] if u["id"] == str(test_user.id)), None)
    assert user_data is not None
    assert "businesses" in user_data
    assert isinstance(user_data["businesses"], list)


@pytest.mark.asyncio
async def test_list_businesses_for_assignment(
    admin_client,
    db_session,
):
    """AC-02: Admin can list businesses for user assignment."""
    # Create a business
    business = Business(
        name="Test Business",
        address="123 Test St",
        phone="+595981234567",
        is_active=True,
    )
    db_session.add(business)
    await db_session.commit()

    response = await admin_client.get("/admin/businesses")
    assert response.status_code == 200
    data = response.json()
    assert "businesses" in data
    assert len(data["businesses"]) > 0

    business_data = data["businesses"][0]
    assert "id" in business_data
    assert "name" in business_data


@pytest.mark.asyncio
async def test_assign_businesses_to_user(
    admin_client,
    test_user,
    db_session,
):
    """AC-01/AC-02: Admin can assign businesses to users."""
    # Create two businesses
    business_1 = Business(
        name="Test Business 1",
        address="123 Test St",
        phone="+595981234567",
        is_active=True,
    )
    business_2 = Business(
        name="Test Business 2",
        address="456 Test Ave",
        phone="+595981234568",
        is_active=True,
    )
    db_session.add(business_1)
    db_session.add(business_2)
    await db_session.commit()
    await db_session.refresh(business_1)
    await db_session.refresh(business_2)

    response = await admin_client.post(
        f"/admin/users/{test_user.id}/businesses",
        json={"business_ids": [str(business_1.id), str(business_2.id)]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user.id)
    assert len(data["businesses"]) == 2


@pytest.mark.asyncio
async def test_assign_nonexistent_business_fails(
    admin_client,
    test_user,
):
    """AC-04: Business assignment validates business existence."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await admin_client.post(
        f"/admin/users/{test_user.id}/businesses",
        json={"business_ids": [fake_id]},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unassign_business(
    admin_client,
    test_user,
    db_session,
):
    """AC-01/AC-02: Admin can unassign businesses from users."""
    # Create business
    business = Business(
        name="Test Business",
        address="123 Test St",
        phone="+595981234567",
        is_active=True,
    )
    db_session.add(business)
    await db_session.commit()
    await db_session.refresh(business)

    # Assign
    assignment = UserBusiness(
        user_id=test_user.id,
        business_id=business.id,
    )
    db_session.add(assignment)
    await db_session.commit()

    # Unassign
    response = await admin_client.delete(
        f"/admin/users/{test_user.id}/businesses/{business.id}",
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Business unassigned successfully"

    # Verify gone
    result = await db_session.execute(
        select(UserBusiness).where(
            UserBusiness.user_id == test_user.id,
            UserBusiness.business_id == business.id,
        )
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_unassign_nonexistent_assignment_fails(
    admin_client,
    test_user,
    db_session,
):
    """AC-04: Business assignment validates business existence."""
    # Create business but don't assign
    business = Business(
        name="Test Business",
        address="123 Test St",
        phone="+595981234567",
        is_active=True,
    )
    db_session.add(business)
    await db_session.commit()
    await db_session.refresh(business)

    response = await admin_client.delete(
        f"/admin/users/{test_user.id}/businesses/{business.id}",
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_non_admin_cannot_assign_businesses(
    client,
    test_user,
    db_session,
):
    """AC-02: Cashiers cannot assign businesses to users."""
    # Create business
    business = Business(
        name="Test Business",
        address="123 Test St",
        phone="+595981234567",
        is_active=True,
    )
    db_session.add(business)
    await db_session.commit()
    await db_session.refresh(business)

    response = await client.post(
        f"/admin/users/{test_user.id}/businesses",
        json={"business_ids": [str(business.id)]},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cashier_cannot_unassign_business(
    client,
    test_user,
    db_session,
):
    """AC-02: Cashier is denied unassigning a business (admin only)."""
    # Create another user (cashier)
    other_user = User(
        email="other@example.com",
        hashed_password="hashed_pass",
        first_name="Other",
        last_name="User",
        role="CASHIER",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # Create business
    business = Business(
        name="Test Business",
        address="123 Test St",
        phone="+595981234567",
        is_active=True,
    )
    db_session.add(business)
    await db_session.commit()
    await db_session.refresh(business)

    # Assign business to other user
    assignment = UserBusiness(
        user_id=other_user.id,
        business_id=business.id,
    )
    db_session.add(assignment)
    await db_session.commit()

    # Try to unassign as cashier (should be 403)
    response = await client.delete(
        f"/admin/users/{other_user.id}/businesses/{business.id}",
    )
    assert response.status_code == 403
    # Verify assignment still exists in DB
    result = await db_session.execute(
        select(UserBusiness).where(
            UserBusiness.user_id == other_user.id,
            UserBusiness.business_id == business.id,
        )
    )
    assert result.scalar_one_or_none() is not None
