import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class UserProgress(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'user_progress'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), unique=True)
    total_xp = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    completed_lessons = sqlalchemy.Column(sqlalchemy.Text, default='')  # CSV ids
    level = sqlalchemy.Column(sqlalchemy.Integer, default=1)

    user = orm.relationship('User')