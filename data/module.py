import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Module(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'modules'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.Text)
    order = sqlalchemy.Column(sqlalchemy.Integer, default=0)

    lessons = orm.relationship('Lesson', back_populates='module')