import datetime
import os
import hashlib
import sys
import io
from contextlib import redirect_stdout
from flask import Flask, render_template, redirect, request, abort, make_response, jsonify, session
from waitress import serve
from data import db_session
from data.users import User
from data.lesson import Lesson
from data.module import Module
from data.user_progress import UserProgress
from data.achievement import Achievement
from data.user_achievement import UserAchievement
from data.quiz import Quiz, QuizQuestion, UserQuizAnswer
from data.task import Task, TaskSolution
from forms.login_form import LoginForm
from forms.user import RegisterForm
from forms.lesson import LessonForm, TaskForm
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import json

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


def read_lesson_content(filename):
    """Читает содержимое урока из файла"""
    # Пробуем разные пути к файлу
    possible_paths = [
        f"lesson_content/{filename}",
        f"lesson_content/{filename}",
        filename,
        f"data/lesson_content/{filename}"
    ]

    for path in possible_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            continue

    # Если файл не найден, возвращаем заглушку
    return f"""
    <h2>Содержимое урока временно недоступно</h2>
    <p>Файл {filename} не найден. Пожалуйста, проверьте наличие файла в папке lesson_content/</p>
    """


# Инициализация данных для образовательной платформы
def init_educational_data():
    db_sess = db_session.create_session()

    # Проверяем, есть ли уже уроки
    if db_sess.query(Lesson).first():
        print("Уроки уже существуют, пропускаем инициализацию")
        return

    # Создаем модули и уроки по программированию
    modules = [
        {"name": "Основы программирования", "order": 1,
         "description": "Введение в мир программирования. Узнаем, что такое программирование и напишем первую программу."},
        {"name": "Переменные и типы данных", "order": 2,
         "description": "Изучаем переменные и их типы. Числа, строки и логические значения."},
        {"name": "Условные операторы", "order": 3,
         "description": "Как заставить программу принимать решения. if, else, elif."},
        {"name": "Циклы", "order": 4, "description": "Повторяем действия с помощью циклов while и for."},
        {"name": "Функции", "order": 5, "description": "Создаем собственные функции и используем их повторно."},
    ]

    module_objects = []
    for mod in modules:
        module = Module(
            name=mod["name"],
            description=mod["description"],
            order=mod["order"]
        )
        db_sess.add(module)
        db_sess.flush()  # Получаем ID без коммита
        module_objects.append(module)

    db_sess.commit()

    # Уроки для каждого модуля (с указанием файлов с содержимым)
    lessons_data = [
        # Модуль 1: Основы программирования
        {"title": "Что такое программирование?",
         "content_file": "module1_basics.html",
         "order": 1, "xp_reward": 50, "module_id": module_objects[0].id},
        {"title": "Первая программа",
         "content_file": "module1_basics.html",
         "order": 2, "xp_reward": 50, "module_id": module_objects[0].id},

        # Модуль 2: Переменные и типы данных
        {"title": "Что такое переменные?",
         "content_file": "module2_variables.html",
         "order": 1, "xp_reward": 75, "module_id": module_objects[1].id},
        {"title": "Числовые типы данных",
         "content_file": "module2_variables.html",
         "order": 2, "xp_reward": 75, "module_id": module_objects[1].id},
        {"title": "Строки и булевы значения",
         "content_file": "module2_variables.html",
         "order": 3, "xp_reward": 75, "module_id": module_objects[1].id},

        # Модуль 3: Условные операторы
        {"title": "Оператор if",
         "content_file": "module3_conditions.html",
         "order": 1, "xp_reward": 100, "module_id": module_objects[2].id},
        {"title": "Операторы else и elif",
         "content_file": "module3_conditions.html",
         "order": 2, "xp_reward": 100, "module_id": module_objects[2].id},

        # Модуль 4: Циклы
        {"title": "Цикл while",
         "content_file": "module4_loops.html",
         "order": 1, "xp_reward": 100, "module_id": module_objects[3].id},
        {"title": "Цикл for",
         "content_file": "module4_loops.html",
         "order": 2, "xp_reward": 100, "module_id": module_objects[3].id},

        # Модуль 5: Функции
        {"title": "Создание функций",
         "content_file": "module5_functions.html",
         "order": 1, "xp_reward": 125, "module_id": module_objects[4].id},
        {"title": "Параметры и возврат значений",
         "content_file": "module5_functions.html",
         "order": 2, "xp_reward": 125, "module_id": module_objects[4].id},
    ]

    lesson_objects = []
    for lesson_data in lessons_data:
        # Извлекаем имя файла и удаляем его из словаря
        content_file = lesson_data.pop("content_file")

        # Читаем содержимое из файла
        content = read_lesson_content(content_file)

        # Создаем урок
        lesson = Lesson(content=content, **lesson_data)
        db_sess.add(lesson)
        db_sess.flush()
        lesson_objects.append(lesson)

    db_sess.commit()
    print(f"Создано {len(lesson_objects)} уроков")

    # Создаем вопросы для тестов
    quizzes = [
        {"lesson_id": lesson_objects[0].id, "questions": [
            {"text": "Что такое программирование?",
             "options": "Процесс создания программ,Изучение компьютеров,Работа с текстом,Игры", "correct": 0},
            {"text": "Какой язык рекомендуется для начинающих?",
             "options": "C++,Java,Python,JavaScript", "correct": 2},
        ]},
        {"lesson_id": lesson_objects[1].id, "questions": [
            {"text": "Как вывести текст в Python?",
             "options": "print(),output(),echo(),write()", "correct": 0},
            {"text": "Что выведет print('Hello')?",
             "options": "Hello,'Hello',hello,Ошибка", "correct": 0},
        ]},
        {"lesson_id": lesson_objects[2].id, "questions": [
            {"text": "Как создать переменную в Python?",
             "options": "var x = 5,x = 5,let x = 5,int x = 5", "correct": 1},
            {"text": "Какой тип данных у числа 3.14?",
             "options": "int,float,str,bool", "correct": 1},
        ]},
        {"lesson_id": lesson_objects[3].id, "questions": [
            {"text": "Что выведет print(10 // 3)?",
             "options": "3.333,3,4,Ошибка", "correct": 1},
            {"text": "Как объединить две строки?",
             "options": "str1 + str2,str1 & str2,str1.append(str2),str1.join(str2)", "correct": 0},
        ]},
        {"lesson_id": lesson_objects[4].id, "questions": [
            {"text": "Какой оператор проверяет равенство?",
             "options": "=,==,!=,===", "correct": 1},
            {"text": "Что делает оператор and?",
             "options": "Сложение,Истина если оба истинны,Истина если хотя бы один истинен,Отрицание", "correct": 1},
        ]},
        {"lesson_id": lesson_objects[5].id, "questions": [
            {"text": "Что выведет if 5 > 3: print('Да')?",
             "options": "Да,Ничего,Ошибка,False", "correct": 0},
            {"text": "Как проверить, что число x от 10 до 20?",
             "options": "10 < x < 20,x > 10 and x < 20,оба варианта,ни один", "correct": 2},
        ]},
        {"lesson_id": lesson_objects[6].id, "questions": [
            {"text": "Какой цикл используется когда известно количество повторений?",
             "options": "while,for,do-while,repeat", "correct": 1},
            {"text": "Что делает break в цикле?",
             "options": "Пропускает итерацию,Завершает цикл,Начинает цикл заново,Ничего", "correct": 1},
        ]},
        {"lesson_id": lesson_objects[7].id, "questions": [
            {"text": "Что выведет range(5)?",
             "options": "0,1,2,3,4,1,2,3,4,5,0,1,2,3,4,5,1,2,3,4", "correct": 0},
            {"text": "Как перебрать элементы списка с индексами?",
             "options": "for i in list,for i in range(list),for i,item in enumerate(list),for item in list",
             "correct": 2},
        ]},
        {"lesson_id": lesson_objects[8].id, "questions": [
            {"text": "Какое ключевое слово используется для создания функции?",
             "options": "function,def,func,define", "correct": 1},
            {"text": "Что делает return?",
             "options": "Выводит значение,Возвращает значение из функции,Завершает программу,Создает переменную",
             "correct": 1},
        ]},
        {"lesson_id": lesson_objects[9].id, "questions": [
            {"text": "Что такое параметры функции?",
             "options": "Данные которые функция возвращает,Данные которые функция получает,Имя функции,Тип функции",
             "correct": 1},
            {"text": "Что выведет print(greet()) если greet(name='Гость')?",
             "options": "Привет, ,Привет, Гость,Ошибка,None", "correct": 1},
        ]},
    ]

    for quiz_data in quizzes:
        quiz = Quiz(lesson_id=quiz_data["lesson_id"])
        db_sess.add(quiz)
        db_sess.flush()

        for i, q in enumerate(quiz_data["questions"]):
            question = QuizQuestion(
                quiz_id=quiz.id,
                text=q["text"],
                options=q["options"],
                correct_answer=q["correct"],
                order=i + 1
            )
            db_sess.add(question)

        db_sess.flush()

    db_sess.commit()
    print(f"Создано {len(quizzes)} тестов")

    # Создаем задания
    tasks = [
        {"lesson_id": lesson_objects[1].id, "title": "Напиши приветствие",
         "description": "Напишите программу, которая выводит 'Привет, мир!'",
         "initial_code": "# Напишите код здесь\n",
         "test_code": "assert 'Привет, мир!' in output",
         "language": "python"},
        {"lesson_id": lesson_objects[3].id, "title": "Калькулятор",
         "description": "Создайте переменные a=10 и b=5, выведите их сумму",
         "initial_code": "a = 10\nb = 5\n# Вычислите сумму\n",
         "test_code": "assert '15' in output",
         "language": "python"},
        {"lesson_id": lesson_objects[5].id, "title": "Проверка возраста",
         "description": "Дан возраст, выведите 'Совершеннолетний', если он больше либо равен 18 и 'Несовершеннолетний' если меньше 18'",
         "initial_code": "age = 15\n\n# Напишите условие\n",
         "test_code": "assert 'Несовершеннолетний' in output or 'Совершеннолетний' in output",
         "language": "python"},
        {"lesson_id": lesson_objects[7].id, "title": "Сумма чисел",
         "description": "Напишите программу, которая считает сумму чисел от 1 до 10",
         "initial_code": "# Напишите цикл для подсчета суммы",
         "test_code": "assert '55' in output",
         "language": "python"},
        {"lesson_id": lesson_objects[9].id, "title": "Функция приветствия",
         "description": "Создайте функцию greet(name), которая выводит 'Привет, [имя]!'",
         "initial_code": "def greet(name):\n    # Напишите код здесь\n",
         "test_code": "assert 'Привет, Анна' in output",
         "language": "python"},
    ]

    for task_data in tasks:
        task = Task(**task_data)
        db_sess.add(task)

    db_sess.commit()
    print(f"Создано {len(tasks)} заданий")

    # Создаем достижения
    achievements = [
        {"name": "Первые шаги", "description": "Завершите первый урок", "icon": "🌟", "xp_reward": 50,
         "required_lessons": 1},
        {"name": "Новичок", "description": "Наберите 200 XP", "icon": "📚", "xp_reward": 100, "required_xp": 200},
        {"name": "Мастер переменных", "description": "Завершите модуль 'Переменные и типы данных'", "icon": "🔤",
         "xp_reward": 150, "required_modules": 2},
        {"name": "Программист", "description": "Наберите 500 XP", "icon": "💻", "xp_reward": 200, "required_xp": 500},
        {"name": "Мастер условий", "description": "Завершите модуль 'Условные операторы'", "icon": "🤔",
         "xp_reward": 150, "required_modules": 3},
        {"name": "Король циклов", "description": "Завершите модуль 'Циклы'", "icon": "🔄",
         "xp_reward": 150, "required_modules": 4},
        {"name": "Гуру функций", "description": "Завершите модуль 'Функции'", "icon": "🎯",
         "xp_reward": 150, "required_modules": 5},
        {"name": "Эксперт", "description": "Наберите 1000 XP", "icon": "🏆", "xp_reward": 300, "required_xp": 1000},
    ]

    for ach in achievements:
        achievement = Achievement(**ach)
        db_sess.add(achievement)

    db_sess.commit()
    print(f"Создано {len(achievements)} достижений")
    print("🎉 Инициализация данных завершена!")


def check_python_code(code, task_obj):
    """Безопасная проверка Python кода"""
    try:
        # Захватываем вывод
        f = io.StringIO()
        with redirect_stdout(f):
            # Создаем безопасную среду
            exec_globals = {}
            exec(code, exec_globals)

        output = f.getvalue()

        # Выполняем тестовый код
        test_globals = {'output': output}
        exec(task_obj.test_code, test_globals)
        return True, output
    except Exception as e:
        return False, str(e)


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


@app.route('/lesson/<int:lesson_id>/complete', methods=['POST', 'GET'])
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

    # Проверяем, проходил ли пользователь этот тест
    user_answers_record = db_sess.query(UserQuizAnswer).filter(
        UserQuizAnswer.user_id == current_user.id,
        UserQuizAnswer.quiz_id == quiz_obj.id
    ).first()

    # Проверяем, пройден ли урок
    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
    lesson_completed_from_progress = False
    if progress and progress.completed_lessons:
        lesson_completed_from_progress = str(lesson_id) in progress.completed_lessons.split(',')

    lesson_completed = lesson_completed_from_progress
    user_answers = {}

    if user_answers_record:
        if user_answers_record.answers:
            user_answers = json.loads(user_answers_record.answers)
        lesson_completed = lesson_completed or user_answers_record.completed

    if request.method == 'POST':
        score = 0
        answers = {}
        for i, question in enumerate(questions):
            answer = request.form.get(f'q_{i}')
            if answer:
                answers[str(i)] = answer
                if int(answer) == question.correct_answer:
                    score += 1

        test_passed = (score >= len(questions) / 2)

        # Сохраняем ответы пользователя
        if user_answers_record:
            user_answers_record.answers = json.dumps(answers)
            user_answers_record.completed = test_passed
            db_sess.commit()
        else:
            user_answers_record = UserQuizAnswer(
                user_id=current_user.id,
                quiz_id=quiz_obj.id,
                answers=json.dumps(answers),
                completed=test_passed
            )
            db_sess.add(user_answers_record)
            db_sess.commit()

        return render_template("quiz_result.html", quiz=quiz_obj, questions=questions,
                               score=score, total=len(questions), test_passed=test_passed,
                               lesson_id=lesson_id, lesson_completed=lesson_completed,
                               user_answers=answers)

    return render_template("quiz.html", quiz=quiz_obj, questions=questions,
                           lesson_id=lesson_id, lesson_completed=lesson_completed,
                           user_answers=user_answers)


@app.route('/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task(task_id):
    db_sess = db_session.create_session()
    task_obj = db_sess.get(Task, task_id)
    if not task_obj:
        abort(404)

    # Проверяем, решена ли задача
    solved_record = db_sess.query(TaskSolution).filter(
        TaskSolution.task_id == task_id,
        TaskSolution.user_id == current_user.id
    ).first()

    solved = solved_record is not None and solved_record.solved

    if request.method == 'POST':
        code = request.form.get('code')

        if code and task_obj.language == 'python':
            # Проверяем код
            is_correct, message = check_python_code(code, task_obj)

            if is_correct:
                # Сохраняем решение, если еще не решено
                if not solved:
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
                    solved = True

                return render_template("task.html", task=task_obj,
                                       solved=True, message="✅ Задание выполнено! +50 XP")
            else:
                return render_template("task.html", task=task_obj,
                                       solved=False, message=f"❌ Код не прошел проверку: {message}")

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
        achieved = False

        if achievement.required_xp and progress.total_xp >= achievement.required_xp:
            achieved = True

        elif achievement.required_lessons and progress.completed_lessons:
            completed = len(progress.completed_lessons.split(',')) if progress.completed_lessons else 0
            if completed >= achievement.required_lessons:
                achieved = True

        elif achievement.required_modules:
            # Подсчет пройденных модулей
            if progress.completed_lessons:
                completed_lessons = progress.completed_lessons.split(',')
                # Получаем все уроки
                all_lessons = db_sess.query(Lesson).all()
                lesson_to_module = {lesson.id: lesson.module_id for lesson in all_lessons}

                # Считаем пройденные модули
                completed_modules = set()
                for lesson_id_str in completed_lessons:
                    lesson_id = int(lesson_id_str)
                    if lesson_id in lesson_to_module:
                        completed_modules.add(lesson_to_module[lesson_id])

                if len(completed_modules) >= achievement.required_modules:
                    achieved = True

        if achieved:
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
    data = db_sess.query(User.name, UserProgress.completed_lessons, UserProgress.total_xp).join(User,
                                                                                                User.id == UserProgress.user_id).order_by(
        UserProgress.total_xp.desc()).all()
    return render_template("leaderboard.html", data=data)


if __name__ == '__main__':
    # Создаем папку lesson_content если её нет
    if not os.path.exists("lesson_content"):
        os.makedirs("lesson_content")
        print("📁 Создана папка lesson_content/")
        print("⚠️ Не забудьте поместить файлы с содержимым уроков в эту папку!")
        print("   - module1_basics.html")
        print("   - module2_variables.html")
        print("   - module3_conditions.html")
        print("   - module4_loops.html")
        print("   - module5_functions.html")

    db_session.global_init("db/educational.db")
    init_educational_data()

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)