import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Achievement(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'achievements'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.String)
    icon = sqlalchemy.Column(sqlalchemy.String, default='🏆')
    xp_reward = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    required_xp = sqlalchemy.Column(sqlalchemy.Integer)
    required_lessons = sqlalchemy.Column(sqlalchemy.Integer)
    required_modules = sqlalchemy.Column(sqlalchemy.Integer)