"""
API tests for teams endpoints.
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestListTeams:
    """Tests for list teams endpoint."""

    async def test_list_teams_requires_auth(self, client: AsyncClient):
        """Test listing teams requires authentication."""
        response = await client.get("/teams")
        assert response.status_code in (401, 403)

    async def test_list_teams_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing teams when empty returns empty list."""
        response = await client.get(
            "/teams",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_teams_with_data(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test listing teams returns created teams."""
        from tests.crud import create_division, create_person, create_team

        division = await create_division(api_db, name=f"TeamDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="Responsible",
            lastname="Person",
            email=f"resp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"Team1_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person.id,
        )
        await api_db.commit()

        response = await client.get(
            "/teams",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        team_ids = [t["id"] for t in data]
        assert str(team.id) in team_ids

    async def test_list_teams_by_division(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test listing teams filtered by division."""
        from tests.crud import create_division, create_person, create_team

        division1 = await create_division(api_db, name=f"Div1_{uuid4().hex[:6]}")
        division2 = await create_division(api_db, name=f"Div2_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="Resp",
            lastname="Person",
            email=f"resp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team1 = await create_team(
            api_db,
            name=f"TeamD1_{uuid4().hex[:6]}",
            division_id=division1.id,
            responsible_id=person.id,
        )
        team2 = await create_team(
            api_db,
            name=f"TeamD2_{uuid4().hex[:6]}",
            division_id=division2.id,
            responsible_id=person.id,
        )
        await api_db.commit()

        response = await client.get(
            f"/teams?division_id={division1.id}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()

        team_ids = [t["id"] for t in data]
        assert str(team1.id) in team_ids
        assert str(team2.id) not in team_ids

    async def test_list_teams_proxy_only(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test listing only proxy teams."""
        from tests.crud import create_division, create_person, create_team, create_proxy_team

        division = await create_division(api_db, name=f"ProxyDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="Resp",
            lastname="Person",
            email=f"proxyresp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        full_team = await create_team(
            api_db,
            name=f"FullTeam_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person.id,
        )
        proxy_team = await create_proxy_team(
            api_db,
            name=f"ProxyTeam_{uuid4().hex[:6]}",
            external_org="External Org",
        )
        await api_db.commit()

        response = await client.get(
            "/teams?proxy_only=true",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()

        team_ids = [t["id"] for t in data]
        assert str(proxy_team.id) in team_ids
        assert str(full_team.id) not in team_ids

    async def test_list_teams_pagination(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test listing teams with pagination."""
        from tests.crud import create_proxy_team

        for i in range(5):
            await create_proxy_team(
                api_db,
                name=f"PageTeam{i}_{uuid4().hex[:6]}",
                external_org=f"Org{i}",
            )
        await api_db.commit()

        response = await client.get(
            "/teams?limit=2",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestCreateTeam:
    """Tests for create team endpoint."""

    async def test_create_team_requires_auth(self, client: AsyncClient):
        """Test creating team requires authentication."""
        response = await client.post(
            "/teams",
            json={"name": "Test Team"},
        )
        assert response.status_code in (401, 403)

    async def test_create_team_success(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test creating a full team."""
        from tests.crud import create_division, create_person

        division = await create_division(api_db, name=f"CreateDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="TeamResp",
            lastname="Person",
            email=f"teamresp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        unique_name = f"NewTeam_{uuid4().hex[:6]}"
        response = await client.post(
            "/teams",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "name": unique_name,
                "description": "A new team",
                "division_id": str(division.id),
                "responsible_id": str(person.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == unique_name
        assert data["description"] == "A new team"
        assert data["division_id"] == str(division.id)
        assert data["responsible_id"] == str(person.id)
        assert data["is_proxy"] is False
        assert data["promoted_at"] is not None

    async def test_create_team_without_division_permission(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test creating team in division without permission fails."""
        from tests.crud import create_division, create_person

        division = await create_division(api_db, name=f"NoPermDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="NoPermResp",
            lastname="Person",
            email=f"nopermresp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.post(
            "/teams",
            headers={"Authorization": auth_headers["Authorization"]},
            json={
                "name": "No Permission Team",
                "division_id": str(division.id),
                "responsible_id": str(person.id),
            },
        )
        assert response.status_code == 403

    async def test_create_team_minimal(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test creating team with minimal fields (no division)."""
        from tests.crud import create_person

        person = await create_person(
            api_db,
            firstname="MinResp",
            lastname="Person",
            email=f"minresp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        unique_name = f"MinTeam_{uuid4().hex[:6]}"
        response = await client.post(
            "/teams",
            headers={"Authorization": auth_headers["Authorization"]},
            json={
                "name": unique_name,
                "responsible_id": str(person.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == unique_name
        assert data["division_id"] is None


class TestCreateProxyTeam:
    """Tests for create proxy team endpoint."""

    async def test_create_proxy_requires_auth(self, client: AsyncClient):
        """Test creating proxy team requires authentication."""
        response = await client.post(
            "/teams/proxy",
            json={"name": "Proxy Team", "external_org": "External"},
        )
        assert response.status_code in (401, 403)

    async def test_create_proxy_success(self, client: AsyncClient, auth_headers: dict):
        """Test creating a proxy team."""
        unique_name = f"ProxyTeam_{uuid4().hex[:6]}"
        response = await client.post(
            "/teams/proxy",
            headers={"Authorization": auth_headers["Authorization"]},
            json={
                "name": unique_name,
                "external_org": "External Organization",
                "description": "A proxy team",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == unique_name
        assert data["external_org"] == "External Organization"
        assert data["is_proxy"] is True
        assert data["is_external"] is True
        assert data["division_id"] is None
        assert data["responsible_id"] is None
        assert data["promoted_at"] is None

    async def test_create_proxy_missing_external_org(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating proxy without external_org fails."""
        response = await client.post(
            "/teams/proxy",
            headers={"Authorization": auth_headers["Authorization"]},
            json={"name": "No External Org"},
        )
        assert response.status_code == 422


class TestGetTeam:
    """Tests for get team endpoint."""

    async def test_get_team_requires_auth(self, client: AsyncClient):
        """Test getting team requires authentication."""
        response = await client.get(f"/teams/{uuid4()}")
        assert response.status_code in (401, 403)

    async def test_get_team_success(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test getting a team by ID."""
        from tests.crud import create_division, create_person, create_team

        division = await create_division(api_db, name=f"GetDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="GetResp",
            lastname="Person",
            email=f"getresp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"GetTeam_{uuid4().hex[:6]}",
            description="Test team",
            division_id=division.id,
            responsible_id=person.id,
        )
        await api_db.commit()

        response = await client.get(
            f"/teams/{team.id}",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(team.id)
        assert data["name"] == team.name
        assert data["description"] == "Test team"
        assert data["division_name"] == division.name
        assert data["responsible_name"] is not None
        assert "member_count" in data

    async def test_get_team_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting non-existent team returns 404."""
        response = await client.get(
            f"/teams/{uuid4()}",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]


class TestUpdateTeam:
    """Tests for update team endpoint."""

    async def test_update_team_requires_auth(self, client: AsyncClient):
        """Test updating team requires authentication."""
        response = await client.patch(
            f"/teams/{uuid4()}",
            json={"name": "Updated"},
        )
        assert response.status_code in (401, 403)

    async def test_update_team_as_admin(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test updating team as admin."""
        from tests.crud import create_division, create_person, create_team

        division = await create_division(api_db, name=f"UpdateDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="UpdateResp",
            lastname="Person",
            email=f"updateresp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"UpdateTeam_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person.id,
        )
        await api_db.commit()

        response = await client.patch(
            f"/teams/{team.id}",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "name": "Updated Team Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Team Name"
        assert data["description"] == "Updated description"

    async def test_update_team_partial(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test partial team update."""
        from tests.crud import create_division, create_person, create_team

        division = await create_division(api_db, name=f"PartialDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="PartialResp",
            lastname="Person",
            email=f"partialresp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"PartialTeam_{uuid4().hex[:6]}",
            description="Original",
            division_id=division.id,
            responsible_id=person.id,
        )
        await api_db.commit()

        response = await client.patch(
            f"/teams/{team.id}",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"description": "New description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == team.name  # Unchanged
        assert data["description"] == "New description"

    async def test_update_team_not_found(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test updating non-existent team returns 404."""
        response = await client.patch(
            f"/teams/{uuid4()}",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"name": "Updated"},
        )
        assert response.status_code == 404


class TestPromoteTeam:
    """Tests for promote team endpoint."""

    async def test_promote_team_requires_auth(self, client: AsyncClient):
        """Test promoting team requires authentication."""
        response = await client.post(
            f"/teams/{uuid4()}/promote",
            json={"responsible_id": str(uuid4())},
        )
        assert response.status_code in (401, 403)

    async def test_promote_team_success(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test promoting a proxy team to full team."""
        from tests.crud import create_person, create_proxy_team

        person = await create_person(
            api_db,
            firstname="PromoteResp",
            lastname="Person",
            email=f"promoteresp_{uuid4().hex[:8]}@example.com",
        )
        proxy = await create_proxy_team(
            api_db,
            name=f"PromoteProxy_{uuid4().hex[:6]}",
            external_org="External Org",
        )
        await api_db.commit()

        assert proxy.is_proxy is True

        response = await client.post(
            f"/teams/{proxy.id}/promote",
            headers={"Authorization": auth_headers["Authorization"]},
            json={"responsible_id": str(person.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_proxy"] is False
        assert data["responsible_id"] == str(person.id)
        assert data["promoted_at"] is not None

    async def test_promote_team_with_division(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test promoting proxy team and assigning to division."""
        from tests.crud import create_division, create_person, create_proxy_team

        division = await create_division(api_db, name=f"PromoteDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="PromoteDivResp",
            lastname="Person",
            email=f"promotedivresp_{uuid4().hex[:8]}@example.com",
        )
        proxy = await create_proxy_team(
            api_db,
            name=f"PromoteDivProxy_{uuid4().hex[:6]}",
            external_org="External Org",
        )
        await api_db.commit()

        response = await client.post(
            f"/teams/{proxy.id}/promote",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "responsible_id": str(person.id),
                "division_id": str(division.id),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["division_id"] == str(division.id)
        assert data["is_proxy"] is False

    async def test_promote_already_full_team(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test promoting an already full team fails."""
        from tests.crud import create_division, create_person, create_team

        division = await create_division(api_db, name=f"AlreadyDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="AlreadyResp",
            lastname="Person",
            email=f"alreadyresp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"AlreadyFull_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person.id,
        )
        await api_db.commit()

        response = await client.post(
            f"/teams/{team.id}/promote",
            headers={"Authorization": auth_headers["Authorization"]},
            json={"responsible_id": str(person.id)},
        )
        assert response.status_code == 400
        assert "already a full team" in response.json()["detail"]

    async def test_promote_team_not_found(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test promoting non-existent team fails."""
        from tests.crud import create_person

        person = await create_person(
            api_db,
            firstname="NotFound",
            lastname="Person",
            email=f"notfound_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.post(
            f"/teams/{uuid4()}/promote",
            headers={"Authorization": auth_headers["Authorization"]},
            json={"responsible_id": str(person.id)},
        )
        assert response.status_code == 404


class TestDeleteTeam:
    """Tests for delete team endpoint."""

    async def test_delete_team_requires_auth(self, client: AsyncClient):
        """Test deleting team requires authentication."""
        response = await client.delete(f"/teams/{uuid4()}")
        assert response.status_code in (401, 403)

    async def test_delete_team_as_admin(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test deleting team as admin."""
        from tests.crud import create_proxy_team

        team = await create_proxy_team(
            api_db,
            name=f"DeleteTeam_{uuid4().hex[:6]}",
            external_org="External",
        )
        await api_db.commit()

        response = await client.delete(
            f"/teams/{team.id}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 204

        # Verify deletion
        get_response = await client.get(
            f"/teams/{team.id}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert get_response.status_code == 404

    async def test_delete_team_not_found(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test deleting non-existent team returns 404."""
        response = await client.delete(
            f"/teams/{uuid4()}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 404


class TestTeamMembers:
    """Tests for team member endpoints."""

    async def test_list_members_requires_auth(self, client: AsyncClient):
        """Test listing team members requires authentication."""
        response = await client.get(f"/teams/{uuid4()}/members")
        assert response.status_code in (401, 403)

    async def test_list_members_empty(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test listing members of team with no members."""
        from tests.crud import create_division, create_person, create_team

        division = await create_division(api_db, name=f"EmptyMemDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="EmptyMemResp",
            lastname="Person",
            email=f"emptymemresp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"EmptyMemTeam_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person.id,
        )
        await api_db.commit()

        response = await client.get(
            f"/teams/{team.id}/members",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_list_members_with_data(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test listing team members."""
        from tests.crud import (
            create_division, create_person, create_team, add_team_member
        )

        division = await create_division(api_db, name=f"MemDiv_{uuid4().hex[:6]}")
        person1 = await create_person(
            api_db,
            firstname="MemResp",
            lastname="Person",
            email=f"memresp_{uuid4().hex[:8]}@example.com",
        )
        person2 = await create_person(
            api_db,
            firstname="Player",
            lastname="Person",
            email=f"player_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"MemTeam_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person1.id,
        )
        await api_db.commit()

        member = await add_team_member(
            api_db, team_id=team.id, person_id=person2.id
        )
        await api_db.commit()

        response = await client.get(
            f"/teams/{team.id}/members",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["person_id"] == str(person2.id)

    async def test_add_member_requires_auth(self, client: AsyncClient):
        """Test adding team member requires authentication."""
        response = await client.post(
            f"/teams/{uuid4()}/members",
            json={"person_id": str(uuid4()), "role": "PLAYER"},
        )
        assert response.status_code in (401, 403)

    async def test_add_member_as_admin(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test adding member to team as admin."""
        from tests.crud import create_division, create_person, create_team

        division = await create_division(api_db, name=f"AddMemDiv_{uuid4().hex[:6]}")
        person1 = await create_person(
            api_db,
            firstname="AddMemResp",
            lastname="Person",
            email=f"addmemresp_{uuid4().hex[:8]}@example.com",
        )
        person2 = await create_person(
            api_db,
            firstname="NewPlayer",
            lastname="Person",
            email=f"newplayer_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"AddMemTeam_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person1.id,
        )
        await api_db.commit()

        response = await client.post(
            f"/teams/{team.id}/members",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "person_id": str(person2.id),
                "role": "PLAYER",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["person_id"] == str(person2.id)
        assert data["team_id"] == str(team.id)
        assert data["role"] == "PLAYER"

    async def test_add_member_with_coach_role(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test adding member with COACH role."""
        from tests.crud import create_division, create_person, create_team

        division = await create_division(api_db, name=f"CoachDiv_{uuid4().hex[:6]}")
        person1 = await create_person(
            api_db,
            firstname="CoachResp",
            lastname="Person",
            email=f"coachresp_{uuid4().hex[:8]}@example.com",
        )
        person2 = await create_person(
            api_db,
            firstname="Coach",
            lastname="Person",
            email=f"coach_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"CoachTeam_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person1.id,
        )
        await api_db.commit()

        response = await client.post(
            f"/teams/{team.id}/members",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "person_id": str(person2.id),
                "role": "COACH",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "COACH"

    async def test_add_member_to_proxy_team_fails(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test adding member to proxy team fails."""
        from tests.crud import create_person, create_proxy_team

        person = await create_person(
            api_db,
            firstname="ProxyMember",
            lastname="Person",
            email=f"proxymem_{uuid4().hex[:8]}@example.com",
        )
        proxy = await create_proxy_team(
            api_db,
            name=f"ProxyNoMem_{uuid4().hex[:6]}",
            external_org="External",
        )
        await api_db.commit()

        response = await client.post(
            f"/teams/{proxy.id}/members",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "person_id": str(person.id),
                "role": "PLAYER",
            },
        )
        assert response.status_code == 400
        assert "Cannot add members to a proxy team" in response.json()["detail"]

    async def test_update_member_role(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test updating team member role."""
        from tests.crud import (
            create_division, create_person, create_team, add_team_member
        )

        division = await create_division(api_db, name=f"UpdateMemDiv_{uuid4().hex[:6]}")
        person1 = await create_person(
            api_db,
            firstname="UpdateMemResp",
            lastname="Person",
            email=f"updatememresp_{uuid4().hex[:8]}@example.com",
        )
        person2 = await create_person(
            api_db,
            firstname="UpdateMember",
            lastname="Person",
            email=f"updatemem_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"UpdateMemTeam_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person1.id,
        )
        await api_db.commit()

        member = await add_team_member(
            api_db, team_id=team.id, person_id=person2.id
        )
        await api_db.commit()

        response = await client.patch(
            f"/teams/{team.id}/members/{member.id}",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"role": "COACH"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "COACH"

    async def test_update_member_not_found(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test updating non-existent team member returns 404."""
        from tests.crud import create_division, create_person, create_team

        division = await create_division(api_db, name=f"NoMemDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="NoMemResp",
            lastname="Person",
            email=f"nomemresp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"NoMemTeam_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person.id,
        )
        await api_db.commit()

        response = await client.patch(
            f"/teams/{team.id}/members/{uuid4()}",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"role": "COACH"},
        )
        assert response.status_code == 404

    async def test_remove_member_requires_auth(self, client: AsyncClient):
        """Test removing team member requires authentication."""
        response = await client.delete(f"/teams/{uuid4()}/members/{uuid4()}")
        assert response.status_code in (401, 403)

    async def test_remove_member_as_admin(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test removing member from team as admin."""
        from tests.crud import (
            create_division, create_person, create_team, add_team_member
        )

        division = await create_division(api_db, name=f"RemMemDiv_{uuid4().hex[:6]}")
        person1 = await create_person(
            api_db,
            firstname="RemMemResp",
            lastname="Person",
            email=f"remmemresp_{uuid4().hex[:8]}@example.com",
        )
        person2 = await create_person(
            api_db,
            firstname="RemMember",
            lastname="Person",
            email=f"remmem_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"RemMemTeam_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person1.id,
        )
        await api_db.commit()

        member = await add_team_member(
            api_db, team_id=team.id, person_id=person2.id
        )
        await api_db.commit()

        response = await client.delete(
            f"/teams/{team.id}/members/{member.id}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 204

        # Verify removal
        list_response = await client.get(
            f"/teams/{team.id}/members",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) == 0

    async def test_remove_member_not_found(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test removing non-existent member returns 404."""
        from tests.crud import create_division, create_person, create_team

        division = await create_division(api_db, name=f"NoRemDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="NoRemResp",
            lastname="Person",
            email=f"noremresp_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        team = await create_team(
            api_db,
            name=f"NoRemTeam_{uuid4().hex[:6]}",
            division_id=division.id,
            responsible_id=person.id,
        )
        await api_db.commit()

        response = await client.delete(
            f"/teams/{team.id}/members/{uuid4()}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 404
