import datetime
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Lesson(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'lessons'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    content = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    order = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    xp_reward = sqlalchemy.Column(sqlalchemy.Integer, default=50)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    module_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('modules.id'))
    module = orm.relationship('Module')

    quizzes = orm.relationship('Quiz', back_populates='lesson')
    tasks = orm.relationship('Task', back_populates='lesson')