"""
Tests for Team CRUD operations.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team, TeamRole
from tests.crud import (
    create_team,
    create_proxy_team,
    get_team,
    get_team_with_members,
    update_team,
    promote_team,
    delete_team,
    list_teams,
    add_team_member,
    get_team_member,
    get_team_membership,
    update_team_member,
    delete_team_member,
    list_team_members,
    create_person,
    create_division,
)


class TestTeamCreate:
    """Tests for creating teams."""

    async def test_create_team_minimal(self, db: AsyncSession):
        """Test creating a team with minimal required fields."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        await db.flush()

        team = await create_team(
            db,
            name="Test Team",
            responsible_id=responsible.id,
        )
        await db.flush()

        assert team.id is not None
        assert team.name == "Test Team"
        assert team.responsible_id == responsible.id
        assert team.is_proxy is False
        assert team.promoted_at is not None

    async def test_create_team_full(self, db: AsyncSession):
        """Test creating a team with all fields."""
        division = await create_division(db, name="Test Division")
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        await db.flush()

        team = await create_team(
            db,
            name="Full Team",
            description="A team with all fields",
            division_id=division.id,
            responsible_id=responsible.id,
        )
        await db.flush()

        assert team.name == "Full Team"
        assert team.description == "A team with all fields"
        assert team.division_id == division.id
        assert team.responsible_id == responsible.id
        assert team.is_proxy is False
        assert team.is_external is False

    async def test_create_proxy_team(self, db: AsyncSession):
        """Test creating a proxy team."""
        team = await create_proxy_team(
            db,
            name="FC Bayern U11",
            external_org="FC Bayern München",
            description="External team placeholder",
        )
        await db.flush()

        assert team.id is not None
        assert team.name == "FC Bayern U11"
        assert team.external_org == "FC Bayern München"
        assert team.responsible_id is None
        assert team.division_id is None
        assert team.is_proxy is True
        assert team.is_external is True
        assert team.promoted_at is None


class TestTeamRead:
    """Tests for reading teams."""

    async def test_get_team_by_id(self, db: AsyncSession):
        """Test getting a team by ID."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        await db.flush()

        created = await create_team(db, name="Fetch Test", responsible_id=responsible.id)
        await db.flush()

        fetched = await get_team(db, created.id)

        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_team_not_found(self, db: AsyncSession):
        """Test getting a non-existent team."""
        from uuid import uuid4

        team = await get_team(db, uuid4())

        assert team is None

    async def test_get_team_with_members(self, db: AsyncSession):
        """Test getting a team with members loaded."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        player = await create_person(db, firstname="Player", lastname="Test")
        await db.flush()

        team = await create_team(db, name="Test Team", responsible_id=responsible.id)
        await db.flush()

        await add_team_member(db, team_id=team.id, person_id=player.id, role=TeamRole.PLAYER)
        await db.flush()

        loaded = await get_team_with_members(db, team.id)

        assert loaded is not None
        assert loaded.responsible is not None
        assert loaded.responsible.firstname == "Coach"
        assert len(loaded.members) == 1
        assert loaded.members[0].person.firstname == "Player"

    async def test_list_teams_by_division(self, db: AsyncSession):
        """Test listing teams by division."""
        division = await create_division(db, name="Test Division")
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        await db.flush()

        team1 = await create_team(db, name="Team 1", division_id=division.id, responsible_id=responsible.id)
        team2 = await create_team(db, name="Team 2", division_id=division.id, responsible_id=responsible.id)
        other = await create_team(db, name="Other Team", responsible_id=responsible.id)
        await db.flush()

        teams = await list_teams(db, division_id=division.id)

        team_ids = [t.id for t in teams]
        assert team1.id in team_ids
        assert team2.id in team_ids
        assert other.id not in team_ids

    async def test_list_proxy_teams(self, db: AsyncSession):
        """Test listing only proxy teams."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        await db.flush()

        real_team = await create_team(db, name="Real Team", responsible_id=responsible.id)
        proxy1 = await create_proxy_team(db, name="Proxy 1", external_org="Org 1")
        proxy2 = await create_proxy_team(db, name="Proxy 2", external_org="Org 2")
        await db.flush()

        proxies = await list_teams(db, proxy_only=True)

        proxy_ids = [t.id for t in proxies]
        assert proxy1.id in proxy_ids
        assert proxy2.id in proxy_ids
        assert real_team.id not in proxy_ids


class TestTeamUpdate:
    """Tests for updating teams."""

    async def test_update_team_name(self, db: AsyncSession):
        """Test updating a team's name."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        await db.flush()

        team = await create_team(db, name="Original", responsible_id=responsible.id)
        await db.flush()

        updated = await update_team(db, team.id, name="Updated")
        await db.flush()

        assert updated.name == "Updated"

    async def test_update_team_division(self, db: AsyncSession):
        """Test moving a team to a different division."""
        division1 = await create_division(db, name="Division 1")
        division2 = await create_division(db, name="Division 2")
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        await db.flush()

        team = await create_team(db, name="Team", division_id=division1.id, responsible_id=responsible.id)
        await db.flush()

        updated = await update_team(db, team.id, division_id=division2.id)
        await db.flush()

        assert updated.division_id == division2.id


class TestTeamPromotion:
    """Tests for promoting proxy teams."""

    async def test_promote_proxy_team(self, db: AsyncSession):
        """Test promoting a proxy team to a full team."""
        proxy = await create_proxy_team(db, name="Proxy Team", external_org="External")
        responsible = await create_person(db, firstname="New", lastname="Coach")
        division = await create_division(db, name="Our Division")
        await db.flush()

        assert proxy.is_proxy is True

        promoted = await promote_team(
            db,
            proxy.id,
            responsible_id=responsible.id,
            division_id=division.id,
        )
        await db.flush()

        assert promoted is not None
        assert promoted.is_proxy is False
        assert promoted.responsible_id == responsible.id
        assert promoted.division_id == division.id
        assert promoted.promoted_at is not None

    async def test_promote_already_real_team(self, db: AsyncSession):
        """Test promoting a team that's already real."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        await db.flush()

        team = await create_team(db, name="Real Team", responsible_id=responsible.id)
        await db.flush()

        new_responsible = await create_person(db, firstname="New", lastname="Coach")
        await db.flush()

        result = await promote_team(db, team.id, responsible_id=new_responsible.id)

        assert result is None  # Should fail - already promoted


class TestTeamDelete:
    """Tests for deleting teams."""

    async def test_delete_team(self, db: AsyncSession):
        """Test deleting a team."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        await db.flush()

        team = await create_team(db, name="ToDelete", responsible_id=responsible.id)
        await db.flush()
        team_id = team.id

        result = await delete_team(db, team_id)
        await db.flush()

        assert result is True
        assert await get_team(db, team_id) is None

    async def test_delete_team_not_found(self, db: AsyncSession):
        """Test deleting a non-existent team."""
        from uuid import uuid4

        result = await delete_team(db, uuid4())

        assert result is False


class TestTeamMembers:
    """Tests for team membership."""

    async def test_add_player_to_team(self, db: AsyncSession):
        """Test adding a player to a team."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        player = await create_person(db, firstname="Player", lastname="Test")
        await db.flush()

        team = await create_team(db, name="Test Team", responsible_id=responsible.id)
        await db.flush()

        member = await add_team_member(
            db,
            team_id=team.id,
            person_id=player.id,
            role=TeamRole.PLAYER,
        )
        await db.flush()

        assert member.id is not None
        assert member.team_id == team.id
        assert member.person_id == player.id
        assert member.role == TeamRole.PLAYER

    async def test_add_different_roles(self, db: AsyncSession):
        """Test adding members with different roles."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        player = await create_person(db, firstname="Player", lastname="Test")
        medic = await create_person(db, firstname="Medic", lastname="Test")
        await db.flush()

        team = await create_team(db, name="Test Team", responsible_id=responsible.id)
        await db.flush()

        player_member = await add_team_member(db, team_id=team.id, person_id=player.id, role=TeamRole.PLAYER)
        medic_member = await add_team_member(db, team_id=team.id, person_id=medic.id, role=TeamRole.MEDIC)
        await db.flush()

        assert player_member.role == TeamRole.PLAYER
        assert medic_member.role == TeamRole.MEDIC

    async def test_update_team_member_role(self, db: AsyncSession):
        """Test updating a member's role."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        player = await create_person(db, firstname="Player", lastname="Test")
        await db.flush()

        team = await create_team(db, name="Test Team", responsible_id=responsible.id)
        await db.flush()

        member = await add_team_member(db, team_id=team.id, person_id=player.id, role=TeamRole.PLAYER)
        await db.flush()

        # Promote player to coach
        updated = await update_team_member(db, member.id, role=TeamRole.COACH)
        await db.flush()

        assert updated.role == TeamRole.COACH

    async def test_list_team_members(self, db: AsyncSession):
        """Test listing all members of a team."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        player1 = await create_person(db, firstname="Player1", lastname="Test")
        player2 = await create_person(db, firstname="Player2", lastname="Test")
        await db.flush()

        team = await create_team(db, name="Test Team", responsible_id=responsible.id)
        await db.flush()

        await add_team_member(db, team_id=team.id, person_id=player1.id, role=TeamRole.PLAYER)
        await add_team_member(db, team_id=team.id, person_id=player2.id, role=TeamRole.PLAYER)
        await db.flush()

        members = await list_team_members(db, team.id)

        assert len(members) == 2
        person_ids = [m.person_id for m in members]
        assert player1.id in person_ids
        assert player2.id in person_ids

    async def test_delete_team_member(self, db: AsyncSession):
        """Test removing a member from a team."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        player = await create_person(db, firstname="Player", lastname="Test")
        await db.flush()

        team = await create_team(db, name="Test Team", responsible_id=responsible.id)
        await db.flush()

        member = await add_team_member(db, team_id=team.id, person_id=player.id)
        await db.flush()
        member_id = member.id

        result = await delete_team_member(db, member_id)
        await db.flush()

        assert result is True
        assert await get_team_member(db, member_id) is None

    async def test_get_team_membership(self, db: AsyncSession):
        """Test getting a specific team membership."""
        responsible = await create_person(db, firstname="Coach", lastname="Test")
        player = await create_person(db, firstname="Player", lastname="Test")
        await db.flush()

        team = await create_team(db, name="Test Team", responsible_id=responsible.id)
        await db.flush()

        await add_team_member(db, team_id=team.id, person_id=player.id, role=TeamRole.PLAYER)
        await db.flush()

        membership = await get_team_membership(db, team.id, player.id)

        assert membership is not None
        assert membership.role == TeamRole.PLAYER
