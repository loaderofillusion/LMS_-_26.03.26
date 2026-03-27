import datetime
import os
import hashlib
from flask import Flask, render_template, redirect, request, abort, make_response, jsonify, session
from waitress import serve
from data import db_session
from data.users import User
from data.lesson import Lesson
from data.module import Module
from data.user_progress import UserProgress
from data.achievement import Achievement
from data.user_achievement import UserAchievement
from data.quiz import Quiz, QuizQuestion
from data.task import Task, TaskSolution
from forms.login_form import LoginForm
from forms.user import RegisterForm
from forms.lesson import LessonForm, TaskForm
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=31)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.get(User, user_id)


# Инициализация данных для образовательной платформы
def init_educational_data():
    db_sess = db_session.create_session()

    # Проверяем, есть ли уже уроки
    if db_sess.query(Lesson).first():
        return

    # Создаем модули и уроки по программированию
    modules = [
        {"name": "Основы программирования", "order": 1, "description": "Введение в мир программирования"},
        {"name": "Переменные и типы данных", "order": 2, "description": "Изучаем переменные и их типы"},
        {"name": "Условные операторы", "order": 3, "description": "Как заставить программу принимать решения"},
        {"name": "Циклы", "order": 4, "description": "Повторяем действия с помощью циклов"},
        {"name": "Функции", "order": 5, "description": "Создаем собственные функции"},
    ]

    module_objects = []
    for mod in modules:
        module = Module(
            name=mod["name"],
            description=mod["description"],
            order=mod["order"]
        )
        db_sess.add(module)
        db_sess.commit()
        module_objects.append(module)

    # Уроки для каждого модуля
    lessons_data = [
        # Модуль 1: Основы программирования
        {"title": "Что такое программирование?",
         "content": "Программирование - это процесс создания компьютерных программ. Язык Python - отличный выбор для начинающих!",
         "order": 1, "xp_reward": 50, "module_id": module_objects[0].id},
        {"title": "Первая программа",
         "content": "Напишем программу, которая выводит 'Hello, World!'. Используйте команду print()", "order": 2,
         "xp_reward": 50, "module_id": module_objects[0].id},

        # Модуль 2: Переменные и типы данных
        {"title": "Что такое переменные?",
         "content": "Переменные - это контейнеры для хранения данных. Пример: name = 'Анна'", "order": 1,
         "xp_reward": 75, "module_id": module_objects[1].id},
        {"title": "Числовые типы данных",
         "content": "int (целые числа) и float (дробные числа). Пример: age = 10, price = 99.99", "order": 2,
         "xp_reward": 75, "module_id": module_objects[1].id},
        {"title": "Строки и булевы значения",
         "content": "str (текст) и bool (True/False). Пример: name = 'Вася', is_student = True", "order": 3,
         "xp_reward": 75, "module_id": module_objects[1].id},

        # Модуль 3: Условные операторы
        {"title": "Оператор if", "content": "if позволяет выполнять код только при определенном условии", "order": 1,
         "xp_reward": 100, "module_id": module_objects[2].id},
        {"title": "Операторы else и elif",
         "content": "else выполняется, если условие ложно. elif позволяет проверить несколько условий", "order": 2,
         "xp_reward": 100, "module_id": module_objects[2].id},

        # Модуль 4: Циклы
        {"title": "Цикл while", "content": "while повторяет код пока условие истинно", "order": 1, "xp_reward": 100,
         "module_id": module_objects[3].id},
        {"title": "Цикл for", "content": "for используется для перебора элементов", "order": 2, "xp_reward": 100,
         "module_id": module_objects[3].id},

        # Модуль 5: Функции
        {"title": "Создание функций", "content": "Функции - это блоки кода, которые можно вызывать многократно",
         "order": 1, "xp_reward": 125, "module_id": module_objects[4].id},
        {"title": "Параметры и возврат значений",
         "content": "Функции могут принимать параметры и возвращать результаты", "order": 2, "xp_reward": 125,
         "module_id": module_objects[4].id},
    ]

    for lesson_data in lessons_data:
        lesson = Lesson(**lesson_data)
        db_sess.add(lesson)
        db_sess.commit()

    # Создаем вопросы для тестов
    quizzes = [
        {"lesson_id": 1, "questions": [
            {"text": "Что такое программирование?",
             "options": "Процесс создания программ,Изучение компьютеров,Работа с текстом,Игры", "correct": 0},
            {"text": "Какой язык рекомендуется для начинающих?", "options": "C++,Java,Python,JavaScript", "correct": 2},
        ]},
        {"lesson_id": 2, "questions": [
            {"text": "Как вывести текст в Python?", "options": "print(),output(),echo(),write()", "correct": 0},
            {"text": "Что выведет print('Hello')?", "options": "Hello,'Hello',hello,Ошибка", "correct": 0},
        ]},
    ]

    for quiz_data in quizzes:
        quiz = Quiz(lesson_id=quiz_data["lesson_id"])
        db_sess.add(quiz)
        db_sess.commit()

        for i, q in enumerate(quiz_data["questions"]):
            question = QuizQuestion(
                quiz_id=quiz.id,
                text=q["text"],
                options=q["options"],
                correct_answer=q["correct"],
                order=i + 1
            )
            db_sess.add(question)
            db_sess.commit()

    # Создаем задания
    tasks = [
        {"lesson_id": 2, "title": "Напиши приветствие",
         "description": "Напишите программу, которая выводит 'Привет, мир!'",
         "initial_code": "# Напишите код здесь\n\n", "test_code": "assert 'Привет, мир!' in output",
         "language": "python"},
        {"lesson_id": 4, "title": "Калькулятор", "description": "Создайте переменные a=10 и b=5, выведите их сумму",
         "initial_code": "a = 10\nb = 5\n\n# Вычислите сумму\n", "test_code": "assert '15' in output",
         "language": "python"},
        {"lesson_id": 6, "title": "Проверка возраста",
         "description": "Напишите программу, которая проверяет, является ли возраст >= 18",
         "initial_code": "age = 15\n\n# Напишите условие\n",
         "test_code": "assert 'Несовершеннолетний' in output or 'Совершеннолетний' in output", "language": "python"},
    ]

    for task_data in tasks:
        task = Task(**task_data)
        db_sess.add(task)
        db_sess.commit()

    # Создаем достижения
    achievements = [
        {"name": "Первые шаги", "description": "Завершите первый урок", "icon": "🌟", "xp_reward": 50,
         "required_lessons": 1},
        {"name": "Новичок", "description": "Наберите 200 XP", "icon": "📚", "xp_reward": 100, "required_xp": 200},
        {"name": "Мастер переменных", "description": "Завершите модуль 'Переменные и типы данных'", "icon": "🔤",
         "xp_reward": 150, "required_modules": 2},
        {"name": "Программист", "description": "Наберите 500 XP", "icon": "💻", "xp_reward": 200, "required_xp": 500},
    ]

    for ach in achievements:
        achievement = Achievement(**ach)
        db_sess.add(achievement)
        db_sess.commit()


@app.route("/")
def index():
    if current_user.is_authenticated:
        db_sess = db_session.create_session()
        progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
        if progress:
            total_xp = progress.total_xp
        else:
            total_xp = 0

        achievements = db_sess.query(UserAchievement).filter(
            UserAchievement.user_id == current_user.id
        ).join(Achievement).all()

        return render_template("index.html", total_xp=total_xp,
                               achievements=achievements,
                               user=current_user)
    return render_template("index.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        password = hashlib.sha256(form.password.data.encode('utf-8')).hexdigest()
        password_again = hashlib.sha256(form.password_again.data.encode('utf-8')).hexdigest()
        if password != password_again:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")

        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data,
            age=form.age.data if hasattr(form, 'age') else 12
        )
        user.set_password(password)
        db_sess.add(user)
        db_sess.commit()

        # Создаем прогресс для нового пользователя
        progress = UserProgress(user_id=user.id)
        db_sess.add(progress)
        db_sess.commit()

        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(hashlib.sha256(form.password.data.encode('utf-8')).hexdigest()):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/lessons')
@login_required
def lessons():
    db_sess = db_session.create_session()
    modules = db_sess.query(Module).order_by(Module.order).all()

    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
    completed_lessons = set()
    if progress and progress.completed_lessons:
        completed_lessons = set(progress.completed_lessons.split(',')) if progress.completed_lessons else set()

    return render_template("lessons.html", modules=modules,
                           completed_lessons=completed_lessons)


@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    db_sess = db_session.create_session()
    lesson = db_sess.get(Lesson, lesson_id)
    if not lesson:
        abort(404)

    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
    completed = False
    if progress and progress.completed_lessons:
        completed = str(lesson_id) in progress.completed_lessons.split(',')

    return render_template("lesson_detail.html", lesson=lesson, completed=completed)


@app.route('/lesson/<int:lesson_id>/complete', methods=['POST'])
@login_required
def complete_lesson(lesson_id):
    db_sess = db_session.create_session()
    lesson = db_sess.get(Lesson, lesson_id)
    if not lesson:
        abort(404)

    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
    if not progress:
        progress = UserProgress(user_id=current_user.id)
        db_sess.add(progress)

    completed_lessons = set()
    if progress.completed_lessons:
        completed_lessons = set(progress.completed_lessons.split(','))

    if str(lesson_id) not in completed_lessons:
        completed_lessons.add(str(lesson_id))
        progress.completed_lessons = ','.join(completed_lessons)
        progress.total_xp += lesson.xp_reward
        db_sess.commit()

        # Проверяем достижения
        check_achievements(current_user.id)

    return jsonify({"success": True, "xp": lesson.xp_reward})


@app.route('/quiz/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def quiz(lesson_id):
    db_sess = db_session.create_session()
    quiz_obj = db_sess.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    if not quiz_obj:
        return redirect(f'/lesson/{lesson_id}')

    questions = db_sess.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_obj.id).order_by(
        QuizQuestion.order).all()

    if request.method == 'POST':
        score = 0
        for i, question in enumerate(questions):
            answer = request.form.get(f'q_{i}')
            if answer and int(answer) == question.correct_answer:
                score += 1

        if score >= len(questions) / 2:  # Проходной балл 50%
            return redirect(f'/lesson/{lesson_id}/complete')

        return render_template("quiz.html", quiz=quiz_obj, questions=questions,
                               score=score, total=len(questions), passed=False)

    return render_template("quiz.html", quiz=quiz_obj, questions=questions, passed=True)


@app.route('/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task(task_id):
    db_sess = db_session.create_session()
    task_obj = db_sess.get(Task, task_id)
    if not task_obj:
        abort(404)

    # Проверяем, решена ли задача
    solved = db_sess.query(TaskSolution).filter(
        TaskSolution.task_id == task_id,
        TaskSolution.user_id == current_user.id
    ).first()

    if request.method == 'POST':
        code = request.form.get('code')
        # Простая проверка кода (в реальном проекте нужен безопасный executor)
        if code and task_obj.language == 'python':
            # Простая валидация
            if 'print' in code or '=' in code:
                # Сохраняем решение
                solution = TaskSolution(
                    task_id=task_id,
                    user_id=current_user.id,
                    code=code,
                    solved=True
                )
                db_sess.add(solution)

                # Начисляем XP
                progress = db_sess.query(UserProgress).filter(
                    UserProgress.user_id == current_user.id
                ).first()
                if progress:
                    progress.total_xp += 50  # XP за решение задачи
                    db_sess.commit()

                check_achievements(current_user.id)

                return render_template("task.html", task=task_obj,
                                       solved=True, message="✅ Задание выполнено! +50 XP")

        return render_template("task.html", task=task_obj,
                               solved=False, message="❌ Код не прошел проверку. Попробуйте еще раз!")

    return render_template("task.html", task=task_obj, solved=solved)


@app.route('/profile')
@login_required
def profile():
    db_sess = db_session.create_session()
    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()

    if progress:
        total_xp = progress.total_xp
        completed_lessons_count = len(progress.completed_lessons.split(',')) if progress.completed_lessons else 0
    else:
        total_xp = 0
        completed_lessons_count = 0

    total_lessons = db_sess.query(Lesson).count()

    user_achievements = db_sess.query(UserAchievement).filter(
        UserAchievement.user_id == current_user.id
    ).join(Achievement).all()

    return render_template("profile.html", user=current_user, total_xp=total_xp,
                           completed_lessons=completed_lessons_count,
                           total_lessons=total_lessons,
                           achievements=user_achievements)


def check_achievements(user_id):
    db_sess = db_session.create_session()
    user = db_sess.get(User, user_id)
    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == user_id).first()

    if not progress:
        return

    achievements = db_sess.query(Achievement).all()
    user_achievements = set(ua.achievement_id for ua in
                            db_sess.query(UserAchievement).filter(UserAchievement.user_id == user_id).all())

    for achievement in achievements:
        if achievement.id in user_achievements:
            continue

        # Проверяем условия
        if achievement.required_xp and progress.total_xp >= achievement.required_xp:
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                earned_at=datetime.datetime.now()
            )
            db_sess.add(user_achievement)
            progress.total_xp += achievement.xp_reward
            db_sess.commit()

        elif achievement.required_lessons and progress.completed_lessons:
            completed = len(progress.completed_lessons.split(',')) if progress.completed_lessons else 0
            if completed >= achievement.required_lessons:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    earned_at=datetime.datetime.now()
                )
                db_sess.add(user_achievement)
                progress.total_xp += achievement.xp_reward
                db_sess.commit()


@app.route('/api/user/progress')
@login_required
def api_user_progress():
    db_sess = db_session.create_session()
    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
    return jsonify({
        "total_xp": progress.total_xp if progress else 0,
        "completed_lessons": progress.completed_lessons.split(',') if progress and progress.completed_lessons else []
    })


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/leaderboard')
@login_required
def leaderboard():
    db_sess = db_session.create_session()
    data = db_sess.query(User.name, UserProgress.completed_lessons, UserProgress.total_xp).join(User, User.id == UserProgress.user_id).order_by(UserProgress.total_xp.desc()).all()


    print(data)

    return render_template("leaderboard.html", data=data)

if __name__ == '__main__':
    db_session.global_init("db/educational.db")
    init_educational_data()

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)