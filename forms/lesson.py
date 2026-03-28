from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

class LessonForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    content = TextAreaField("Содержание", validators=[DataRequired()])
    submit = SubmitField('Сохранить')

class TaskForm(FlaskForm):
    code = TextAreaField("Ваш код")
    submit = SubmitField('Проверить')