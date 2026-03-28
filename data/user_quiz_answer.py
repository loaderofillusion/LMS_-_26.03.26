import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class UserQuizAnswer(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'user_quiz_answers'
    __table_args__ = {'extend_existing': True}  # Добавь эту строку

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    quiz_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('quizzes.id'))
    answers = sqlalchemy.Column(sqlalchemy.Text, default='')  # JSON
    completed = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=sqlalchemy.func.now())

    user = orm.relationship('User')
    quiz = orm.relationship('Quiz')