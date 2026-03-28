import datetime
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class UserAchievement(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'user_achievements'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    achievement_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('achievements.id'))
    earned_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    user = orm.relationship('User', back_populates='achievements')
    achievement = orm.relationship('Achievement', back_populates='user_achievements')