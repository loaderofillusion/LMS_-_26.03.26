import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Task(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'tasks'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    lesson_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('lessons.id'))
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.Text)
    initial_code = sqlalchemy.Column(sqlalchemy.Text, default='')
    test_code = sqlalchemy.Column(sqlalchemy.Text)
    language = sqlalchemy.Column(sqlalchemy.String, default='python')

    lesson = orm.relationship('Lesson')
    solutions = orm.relationship('TaskSolution', back_populates='task')


class TaskSolution(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'task_solutions'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    task_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('tasks.id'))
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    code = sqlalchemy.Column(sqlalchemy.Text)
    solved = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=sqlalchemy.func.now())

    task = orm.relationship('Task', back_populates='solutions')
    user = orm.relationship('User', back_populates='task_solutions')