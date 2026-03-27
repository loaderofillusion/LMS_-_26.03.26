import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Quiz(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'quizzes'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    lesson_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('lessons.id'))

    lesson = orm.relationship('Lesson')
    questions = orm.relationship('QuizQuestion', back_populates='quiz')


class QuizQuestion(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'quiz_questions'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    quiz_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('quizzes.id'))
    text = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    options = sqlalchemy.Column(sqlalchemy.Text)  # CSV
    correct_answer = sqlalchemy.Column(sqlalchemy.Integer)
    order = sqlalchemy.Column(sqlalchemy.Integer, default=0)

    quiz = orm.relationship('Quiz')