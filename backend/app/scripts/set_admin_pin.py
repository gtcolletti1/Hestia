"""Recovery: set or reset an admin profile's PIN from the backend container.

Usage (inside the backend container)::

    python -m app.scripts.set_admin_pin                    # interactive
    python -m app.scripts.set_admin_pin --list             # list admins
    python -m app.scripts.set_admin_pin --profile <uuid> --pin 1234
    python -m app.scripts.set_admin_pin --household <uuid> --name "Alice" --pin 1234

This bypasses the API auth checks because admin login requires a PIN; if every
admin in a household has somehow ended up PIN-less the system would otherwise
be locked out. Treat this script as break-glass: it requires shell access to
the backend container.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import pwd_context
from app.database import async_session
from app.models.user import Household, Profile, ProfileRole


def _looks_like_pin(pin: str) -> bool:
    return pin.isdigit() and 4 <= len(pin) <= 12


async def _list_admins(db: AsyncSession) -> list[tuple[Profile, Household]]:
    result = await db.execute(
        select(Profile, Household)
        .join(Household, Profile.household_id == Household.id)
        .where(Profile.role == ProfileRole.admin)
        .order_by(Household.name, Profile.name)
    )
    return list(result.all())


async def _resolve_profile(
    db: AsyncSession,
    *,
    profile_id: str | None,
    household_id: str | None,
    name: str | None,
) -> Profile:
    if profile_id:
        try:
            pid = uuid.UUID(profile_id)
        except ValueError as exc:
            raise SystemExit(f"Invalid profile id: {profile_id}") from exc
        profile = await db.get(Profile, pid)
        if profile is None:
            raise SystemExit(f"No profile with id {profile_id}")
        return profile

    if not (household_id and name):
        raise SystemExit(
            "Provide either --profile <uuid>, or both --household <uuid> and --name <name>."
        )
    try:
        hid = uuid.UUID(household_id)
    except ValueError as exc:
        raise SystemExit(f"Invalid household id: {household_id}") from exc
    result = await db.execute(
        select(Profile).where(
            Profile.household_id == hid,
            Profile.name == name,
        )
    )
    matches = result.scalars().all()
    if not matches:
        raise SystemExit(f"No profile named {name!r} in household {household_id}")
    if len(matches) > 1:
        raise SystemExit(
            f"Multiple profiles named {name!r} in household {household_id}; "
            "use --profile <uuid> instead."
        )
    return matches[0]


def _prompt_pin() -> str:
    pin1 = getpass.getpass("New PIN (4-12 digits): ").strip()
    if not _looks_like_pin(pin1):
        raise SystemExit("PIN must be 4-12 digits.")
    pin2 = getpass.getpass("Confirm PIN: ").strip()
    if pin1 != pin2:
        raise SystemExit("PINs do not match.")
    return pin1


async def _run(args: argparse.Namespace) -> int:
    async with async_session() as db:
        if args.list:
            rows = await _list_admins(db)
            if not rows:
                print("(no admin profiles found)")
                return 0
            for profile, household in rows:
                pin_state = "pin-set" if profile.pin_hash else "NO PIN"
                active = "active" if profile.is_active else "inactive"
                print(
                    f"{profile.id}  household={household.name!r} ({household.id})  "
                    f"name={profile.name!r}  [{active}, {pin_state}]"
                )
            return 0

        profile = await _resolve_profile(
            db,
            profile_id=args.profile,
            household_id=args.household,
            name=args.name,
        )

        if profile.role != ProfileRole.admin:
            raise SystemExit(
                f"Profile {profile.name!r} is not an admin (role={profile.role.value}); "
                "this script only sets PINs for admin profiles."
            )

        pin = args.pin if args.pin is not None else _prompt_pin()
        if not _looks_like_pin(pin):
            raise SystemExit("PIN must be 4-12 digits.")

        profile.pin_hash = pwd_context.hash(pin)
        if not profile.is_active:
            profile.is_active = True
        await db.commit()

        print(
            f"OK: PIN updated for admin {profile.name!r} "
            f"(profile_id={profile.id}, household_id={profile.household_id})."
        )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m app.scripts.set_admin_pin",
        description="Set or reset an admin profile's PIN (recovery tool).",
    )
    p.add_argument("--list", action="store_true", help="List all admin profiles and exit.")
    p.add_argument("--profile", help="Target profile UUID.")
    p.add_argument("--household", help="Household UUID (use with --name).")
    p.add_argument("--name", help="Profile name within the household (use with --household).")
    p.add_argument(
        "--pin",
        help="New PIN (4-12 digits). If omitted, you will be prompted interactively.",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
