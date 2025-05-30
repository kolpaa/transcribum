from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from src.infrastructure.repositories.database import Base
from sqlalchemy import Integer


"""
CREATE TABLE users(
id BIGSERIAL NOT NULL PRIMARY KEY,
telegram_id BIGSERIAL NOT NULL,
paid BOOLEAN NOT NULL,
paid_minutes INTEGER,
created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

"""
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();"""


class UserModel(Base):
    __tablename__ = 'users'
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    paid: Mapped[bool]
    paid_minutes: Mapped[int]