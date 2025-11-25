#!/usr/bin/env python3
"""
Database seeding script for UnserEvent.

This script allows you to populate the database with divisions, teams, users, and persons.

Usage:
    python scripts/seed_db.py                    # Run with default sample data
    python scripts/seed_db.py --config seed.yaml # Run with custom YAML config
    python scripts/seed_db.py --interactive      # Interactive mode

Examples:
    # Create a superuser
    python scripts/seed_db.py --superuser admin admin@example.com password123

    # Create sample data
    python scripts/seed_db.py --sample
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.division import DivisionRole
from app.models.team import TeamRole


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

async def get_db_session() -> AsyncSession:
    """Create a database session."""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return session_factory()


# ============================================================================
# CRUD OPERATIONS (imported from tests/crud.py patterns)
# ============================================================================

from app.models.person import Person
from app.models.user import User
from app.models.division import Division, DivisionMember
from app.models.team import Team, TeamMember
from app.models.auth import Role, UserRole
from app.services.auth import hash_password
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def create_person(
    db: AsyncSession,
    *,
    firstname: str,
    lastname: str,
    email: Optional[str] = None,
    mobile: Optional[str] = None,
) -> Person:
    """Create a new person."""
    person = Person(
        firstname=firstname,
        lastname=lastname,
        email=email,
        mobile=mobile,
    )
    db.add(person)
    await db.flush()
    await db.refresh(person)
    return person


async def create_user(
    db: AsyncSession,
    *,
    firstname: str,
    lastname: str,
    username: str,
    password: str,
    email: Optional[str] = None,
    mobile: Optional[str] = None,
    is_active: bool = True,
) -> User:
    """Create a new user with associated person."""
    person = Person(
        firstname=firstname,
        lastname=lastname,
        email=email,
        mobile=mobile,
    )
    db.add(person)
    await db.flush()

    user = User(
        id=person.id,
        username=username,
        password_hash=hash_password(password),
        is_active=is_active,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_division(
    db: AsyncSession,
    *,
    name: str,
    description: Optional[str] = None,
    parent_id: Optional[UUID] = None,
) -> Division:
    """Create a new division."""
    division = Division(
        name=name,
        description=description,
        parent_id=parent_id,
    )
    db.add(division)
    await db.flush()
    await db.refresh(division)
    return division


async def create_team(
    db: AsyncSession,
    *,
    name: str,
    description: Optional[str] = None,
    division_id: Optional[UUID] = None,
    responsible_id: Optional[UUID] = None,
) -> Team:
    """Create a new team."""
    from datetime import datetime, timezone

    team = Team(
        name=name,
        description=description,
        division_id=division_id,
        responsible_id=responsible_id,
    )
    if responsible_id is not None:
        team.promoted_at = datetime.now(timezone.utc)

    db.add(team)
    await db.flush()
    await db.refresh(team)
    return team


async def add_division_member(
    db: AsyncSession,
    *,
    division_id: UUID,
    person_id: UUID,
    role: DivisionRole = DivisionRole.MEMBER,
) -> DivisionMember:
    """Add a member to a division."""
    member = DivisionMember(
        division_id=division_id,
        person_id=person_id,
        role=role,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def add_team_member(
    db: AsyncSession,
    *,
    team_id: UUID,
    person_id: UUID,
    role: TeamRole = TeamRole.PLAYER,
) -> TeamMember:
    """Add a member to a team."""
    member = TeamMember(
        team_id=team_id,
        person_id=person_id,
        role=role,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def get_role_by_name(db: AsyncSession, name: str) -> Optional[Role]:
    """Get a role by name."""
    stmt = select(Role).where(Role.name == name)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def assign_role_to_user(
    db: AsyncSession,
    user_id: UUID,
    role_name: str,
) -> Optional[UserRole]:
    """Assign a global role to a user."""
    role = await get_role_by_name(db, role_name)
    if role is None:
        print(f"  Warning: Role '{role_name}' not found in database")
        return None

    # Check if already assigned
    stmt = select(UserRole).where(
        UserRole.user_id == user_id,
        UserRole.role_id == role.id,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    user_role = UserRole(user_id=user_id, role_id=role.id)
    db.add(user_role)
    await db.flush()
    await db.refresh(user_role)
    return user_role


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get a user by username."""
    stmt = select(User).options(selectinload(User.person)).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ============================================================================
# SEEDING FUNCTIONS
# ============================================================================

async def create_superuser(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
) -> User:
    """Create a superuser account."""
    # Check if user already exists
    existing = await get_user_by_username(db, username)
    if existing:
        print(f"User '{username}' already exists, assigning superuser role...")
        await assign_role_to_user(db, existing.id, "superuser")
        await db.commit()
        return existing

    user = await create_user(
        db,
        firstname="Super",
        lastname="User",
        username=username,
        password=password,
        email=email,
    )
    await assign_role_to_user(db, user.id, "superuser")
    await db.commit()
    print(f"Created superuser: {username}")
    return user


async def seed_sample_data(db: AsyncSession) -> dict:
    """Seed the database with sample data."""
    created = {
        "divisions": [],
        "teams": [],
        "users": [],
        "persons": [],
    }

    print("\n=== Creating Sample Data ===\n")

    # Create main division (club)
    print("Creating divisions...")
    main_division = await create_division(
        db,
        name="FC Hersbruck",
        description="Main club division",
    )
    created["divisions"].append(main_division)
    print(f"  + Division: {main_division.name}")

    # Create sub-divisions
    youth_division = await create_division(
        db,
        name="Jugendabteilung",
        description="Youth department",
        parent_id=main_division.id,
    )
    created["divisions"].append(youth_division)
    print(f"  + Division: {youth_division.name} (under {main_division.name})")

    seniors_division = await create_division(
        db,
        name="Seniorenabteilung",
        description="Senior teams department",
        parent_id=main_division.id,
    )
    created["divisions"].append(seniors_division)
    print(f"  + Division: {seniors_division.name} (under {main_division.name})")

    # Create users
    print("\nCreating users...")

    # Admin user
    admin_user = await create_user(
        db,
        firstname="Admin",
        lastname="User",
        username="admin",
        password="admin123",
        email="admin@fchersbruck.de",
    )
    await assign_role_to_user(db, admin_user.id, "admin")
    created["users"].append(admin_user)
    print(f"  + User: {admin_user.username} (admin)")

    # Superuser
    super_user = await create_user(
        db,
        firstname="Super",
        lastname="Admin",
        username="superadmin",
        password="super123",
        email="superadmin@fchersbruck.de",
    )
    await assign_role_to_user(db, super_user.id, "superuser")
    created["users"].append(super_user)
    print(f"  + User: {super_user.username} (superuser)")

    # Regular user (youth manager)
    youth_manager = await create_user(
        db,
        firstname="Thomas",
        lastname="Mueller",
        username="tmueller",
        password="password123",
        email="t.mueller@fchersbruck.de",
    )
    await assign_role_to_user(db, youth_manager.id, "user")
    created["users"].append(youth_manager)
    print(f"  + User: {youth_manager.username} (user)")

    # Add youth manager to youth division as admin
    await add_division_member(
        db,
        division_id=youth_division.id,
        person_id=youth_manager.id,
        role=DivisionRole.ADMIN,
    )
    print(f"    -> Added as admin of {youth_division.name}")

    # Coach user
    coach_user = await create_user(
        db,
        firstname="Hans",
        lastname="Schmidt",
        username="hschmidt",
        password="password123",
        email="h.schmidt@fchersbruck.de",
    )
    await assign_role_to_user(db, coach_user.id, "user")
    created["users"].append(coach_user)
    print(f"  + User: {coach_user.username} (user)")

    # Create persons (non-users)
    print("\nCreating persons...")
    persons_data = [
        ("Max", "Mustermann", "max@example.com", "+49 123 456789"),
        ("Anna", "Schmidt", "anna@example.com", "+49 234 567890"),
        ("Peter", "Weber", "peter@example.com", "+49 345 678901"),
        ("Lisa", "Fischer", "lisa@example.com", "+49 456 789012"),
        ("Tim", "Becker", "tim@example.com", "+49 567 890123"),
        ("Sarah", "Wagner", "sarah@example.com", "+49 678 901234"),
        ("Felix", "Hoffmann", "felix@example.com", "+49 789 012345"),
        ("Laura", "Schulz", "laura@example.com", "+49 890 123456"),
    ]

    for firstname, lastname, email, mobile in persons_data:
        person = await create_person(
            db,
            firstname=firstname,
            lastname=lastname,
            email=email,
            mobile=mobile,
        )
        created["persons"].append(person)
        print(f"  + Person: {firstname} {lastname}")

    # Create teams
    print("\nCreating teams...")

    # U11 team
    u11_team = await create_team(
        db,
        name="U11",
        description="Under 11 youth team",
        division_id=youth_division.id,
        responsible_id=coach_user.id,
    )
    created["teams"].append(u11_team)
    print(f"  + Team: {u11_team.name} (in {youth_division.name})")

    # Add coach to team
    await add_team_member(
        db,
        team_id=u11_team.id,
        person_id=coach_user.id,
        role=TeamRole.COACH,
    )
    print(f"    -> Added {coach_user.person.firstname} as coach")

    # Add some players
    for person in created["persons"][:4]:
        await add_team_member(
            db,
            team_id=u11_team.id,
            person_id=person.id,
            role=TeamRole.PLAYER,
        )
        print(f"    -> Added {person.firstname} as player")

    # U15 team
    u15_team = await create_team(
        db,
        name="U15",
        description="Under 15 youth team",
        division_id=youth_division.id,
        responsible_id=youth_manager.id,
    )
    created["teams"].append(u15_team)
    print(f"  + Team: {u15_team.name} (in {youth_division.name})")

    # Add remaining persons as players
    for person in created["persons"][4:]:
        await add_team_member(
            db,
            team_id=u15_team.id,
            person_id=person.id,
            role=TeamRole.PLAYER,
        )
        print(f"    -> Added {person.firstname} as player")

    # First team (seniors)
    first_team = await create_team(
        db,
        name="1. Mannschaft",
        description="First senior team",
        division_id=seniors_division.id,
        responsible_id=admin_user.id,
    )
    created["teams"].append(first_team)
    print(f"  + Team: {first_team.name} (in {seniors_division.name})")

    await db.commit()

    print("\n=== Sample Data Created Successfully ===")
    print(f"\nSummary:")
    print(f"  Divisions: {len(created['divisions'])}")
    print(f"  Teams: {len(created['teams'])}")
    print(f"  Users: {len(created['users'])}")
    print(f"  Persons: {len(created['persons'])}")

    print(f"\nDefault credentials:")
    print(f"  superadmin / super123  (superuser)")
    print(f"  admin / admin123       (admin)")
    print(f"  tmueller / password123 (youth division admin)")
    print(f"  hschmidt / password123 (coach)")

    return created


async def seed_from_yaml(db: AsyncSession, config_path: str) -> dict:
    """Seed the database from a YAML configuration file."""
    try:
        import yaml
    except ImportError:
        print("Error: PyYAML is required for YAML config. Install with: pip install pyyaml")
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    created = {
        "divisions": [],
        "teams": [],
        "users": [],
        "persons": [],
    }

    print(f"\n=== Seeding from {config_path} ===\n")

    # Create divisions
    division_map = {}  # name -> Division for parent references
    if "divisions" in config:
        print("Creating divisions...")
        for div_data in config["divisions"]:
            parent_id = None
            if "parent" in div_data and div_data["parent"] in division_map:
                parent_id = division_map[div_data["parent"]].id

            division = await create_division(
                db,
                name=div_data["name"],
                description=div_data.get("description"),
                parent_id=parent_id,
            )
            division_map[div_data["name"]] = division
            created["divisions"].append(division)
            print(f"  + Division: {division.name}")

    # Create users
    user_map = {}  # username -> User
    if "users" in config:
        print("\nCreating users...")
        for user_data in config["users"]:
            user = await create_user(
                db,
                firstname=user_data["firstname"],
                lastname=user_data["lastname"],
                username=user_data["username"],
                password=user_data.get("password", "password123"),
                email=user_data.get("email"),
                mobile=user_data.get("mobile"),
            )
            user_map[user_data["username"]] = user
            created["users"].append(user)

            # Assign roles
            for role_name in user_data.get("roles", ["user"]):
                await assign_role_to_user(db, user.id, role_name)

            print(f"  + User: {user.username} ({', '.join(user_data.get('roles', ['user']))})")

            # Add to divisions
            for div_membership in user_data.get("divisions", []):
                if div_membership["name"] in division_map:
                    role = DivisionRole(div_membership.get("role", "member"))
                    await add_division_member(
                        db,
                        division_id=division_map[div_membership["name"]].id,
                        person_id=user.id,
                        role=role,
                    )
                    print(f"    -> Added to {div_membership['name']} as {role.value}")

    # Create persons
    person_map = {}  # email -> Person
    if "persons" in config:
        print("\nCreating persons...")
        for person_data in config["persons"]:
            person = await create_person(
                db,
                firstname=person_data["firstname"],
                lastname=person_data["lastname"],
                email=person_data.get("email"),
                mobile=person_data.get("mobile"),
            )
            if person_data.get("email"):
                person_map[person_data["email"]] = person
            created["persons"].append(person)
            print(f"  + Person: {person.firstname} {person.lastname}")

    # Create teams
    if "teams" in config:
        print("\nCreating teams...")
        for team_data in config["teams"]:
            division_id = None
            if "division" in team_data and team_data["division"] in division_map:
                division_id = division_map[team_data["division"]].id

            responsible_id = None
            if "responsible" in team_data and team_data["responsible"] in user_map:
                responsible_id = user_map[team_data["responsible"]].id

            team = await create_team(
                db,
                name=team_data["name"],
                description=team_data.get("description"),
                division_id=division_id,
                responsible_id=responsible_id,
            )
            created["teams"].append(team)
            print(f"  + Team: {team.name}")

            # Add members
            for member_data in team_data.get("members", []):
                person_id = None
                if "username" in member_data and member_data["username"] in user_map:
                    person_id = user_map[member_data["username"]].id
                elif "email" in member_data and member_data["email"] in person_map:
                    person_id = person_map[member_data["email"]].id

                if person_id:
                    role = TeamRole(member_data.get("role", "player"))
                    await add_team_member(
                        db,
                        team_id=team.id,
                        person_id=person_id,
                        role=role,
                    )
                    print(f"    -> Added member as {role.value}")

    await db.commit()

    print("\n=== Seeding Complete ===")
    print(f"\nSummary:")
    print(f"  Divisions: {len(created['divisions'])}")
    print(f"  Teams: {len(created['teams'])}")
    print(f"  Users: {len(created['users'])}")
    print(f"  Persons: {len(created['persons'])}")

    return created


async def interactive_mode(db: AsyncSession):
    """Run in interactive mode."""
    print("\n=== Interactive Database Seeding ===\n")

    while True:
        print("\nOptions:")
        print("  1. Create a user")
        print("  2. Create a person")
        print("  3. Create a division")
        print("  4. Create a team")
        print("  5. Load sample data")
        print("  6. Quit")

        choice = input("\nChoice (1-6): ").strip()

        if choice == "1":
            print("\n--- Create User ---")
            firstname = input("First name: ").strip()
            lastname = input("Last name: ").strip()
            username = input("Username: ").strip()
            password = input("Password: ").strip() or "password123"
            email = input("Email (optional): ").strip() or None
            role = input("Role (user/admin/superuser) [user]: ").strip() or "user"

            user = await create_user(
                db,
                firstname=firstname,
                lastname=lastname,
                username=username,
                password=password,
                email=email,
            )
            await assign_role_to_user(db, user.id, role)
            await db.commit()
            print(f"\nCreated user: {username} with role {role}")

        elif choice == "2":
            print("\n--- Create Person ---")
            firstname = input("First name: ").strip()
            lastname = input("Last name: ").strip()
            email = input("Email (optional): ").strip() or None
            mobile = input("Mobile (optional): ").strip() or None

            person = await create_person(
                db,
                firstname=firstname,
                lastname=lastname,
                email=email,
                mobile=mobile,
            )
            await db.commit()
            print(f"\nCreated person: {firstname} {lastname}")

        elif choice == "3":
            print("\n--- Create Division ---")
            name = input("Name: ").strip()
            description = input("Description (optional): ").strip() or None

            division = await create_division(
                db,
                name=name,
                description=description,
            )
            await db.commit()
            print(f"\nCreated division: {name}")

        elif choice == "4":
            print("\n--- Create Team ---")
            name = input("Name: ").strip()
            description = input("Description (optional): ").strip() or None

            team = await create_team(
                db,
                name=name,
                description=description,
            )
            await db.commit()
            print(f"\nCreated team: {name}")

        elif choice == "5":
            await seed_sample_data(db)

        elif choice == "6":
            print("\nGoodbye!")
            break
        else:
            print("Invalid choice, please try again.")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Seed the UnserEvent database with data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/seed_db.py --sample
  python scripts/seed_db.py --superuser admin admin@example.com password123
  python scripts/seed_db.py --config seed.yaml
  python scripts/seed_db.py --interactive
        """
    )

    parser.add_argument(
        "--sample",
        action="store_true",
        help="Load sample data (divisions, teams, users, persons)",
    )

    parser.add_argument(
        "--superuser",
        nargs=3,
        metavar=("USERNAME", "EMAIL", "PASSWORD"),
        help="Create a superuser with the given credentials",
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to YAML configuration file",
    )

    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode",
    )

    args = parser.parse_args()

    # If no arguments, show help
    if not any([args.sample, args.superuser, args.config, args.interactive]):
        parser.print_help()
        print("\n\nTip: Use --sample to quickly populate with test data")
        return

    db = await get_db_session()

    try:
        if args.superuser:
            username, email, password = args.superuser
            await create_superuser(db, username, email, password)

        if args.config:
            await seed_from_yaml(db, args.config)

        if args.sample:
            await seed_sample_data(db)

        if args.interactive:
            await interactive_mode(db)

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
