from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.core.security import get_password_hash
from app.models import Assessment, DEFAULT_ASSESSMENT_ID, User, UserCreate, UserRole

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def ensure_seed_user(
    session: Session,
    *,
    username: str,
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
                username=username,
                email=email,
                password=password,
                full_name=full_name,
                role=role,
                is_superuser=is_superuser,
            ),
        )

    user.username = username
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
            username="admin",
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
        username="learner",
        email="learner@example.com",
        password="SecurePass123!",
        full_name="Learner User",
        role=UserRole.LEARNER,
    )
    ensure_seed_user(
        session,
        username="reviewer",
        email="reviewer@example.com",
        password="SecurePass123!",
        full_name="Reviewer User",
        role=UserRole.REVIEWER,
    )

    # Keep this separate from FIRST_SUPERUSER so demo
    # credentials are stable even when the default superuser already exists.
    ensure_seed_user(
        session,
        username="admin.user",
        email="admin.user@example.com",
        password="SecurePass123!",
        full_name="Administrator User",
        role=UserRole.ADMIN,
        is_superuser=True,
    )

    assessment = session.get(Assessment, DEFAULT_ASSESSMENT_ID)
    if not assessment:
        assessment = Assessment(
            id=DEFAULT_ASSESSMENT_ID,
            problem_statement=(
                "Create a small project directory for a basic LLM agent. The agent "
                "implementation should live in agent.py, configuration should be "
                "stored in .env, a sample run should produce output.txt, and "
                "README.md should explain exactly how to run the program."
            ),
            deliverables=[
                "A ZIP file containing agent.py",
                "The same ZIP must include output.txt from a successful sample run",
                "The same ZIP must include .env with the expected environment variable structure",
                "The same ZIP must include README.md with steps to install dependencies and run the agent",
            ],
        )
        session.add(assessment)
        session.commit()
