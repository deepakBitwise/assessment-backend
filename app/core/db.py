from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.core.security import get_password_hash
from app.models import User, UserCreate, UserRole

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def ensure_seed_user(
    session: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
    is_superuser: bool = False,
) -> User:
    user = session.exec(select(User).where(User.email == email)).first()

    if not user:
        return crud.create_user(
            session=session,
            user_create=UserCreate(
                email=email,
                password=password,
                full_name=full_name,
                role=role,
                is_superuser=is_superuser,
            ),
        )

    user.full_name = full_name
    user.role = role
    user.is_superuser = is_superuser
    user.is_active = True
    user.hashed_password = get_password_hash(password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    # Create superuser
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
            role=UserRole.ADMIN,
        )
        user = crud.create_user(session=session, user_create=user_in)
    elif user.role != UserRole.ADMIN:
        user.role = UserRole.ADMIN
        session.add(user)
        session.commit()
        session.refresh(user)

    # Create test users with stable credentials for local UI sign-in.
    ensure_seed_user(
        session,
        email="learner@example.com",
        password="SecurePass123!",
        full_name="Learner User",
        role=UserRole.LEARNER,
    )
    ensure_seed_user(
        session,
        email="reviewer@example.com",
        password="SecurePass123!",
        full_name="Reviewer User",
        role=UserRole.REVIEWER,
    )

    # Keep this separate from FIRST_SUPERUSER so demo
    # credentials are stable even when the default superuser already exists.
    ensure_seed_user(
        session,
        email="admin.user@example.com",
        password="SecurePass123!",
        full_name="Administrator User",
        role=UserRole.ADMIN,
        is_superuser=True,
    )
