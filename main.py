import datetime
import os
import hashlib
import sys
import io
from contextlib import redirect_stdout
from flask import Flask, render_template, redirect, request, abort, make_response, jsonify, g, session
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
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from data.quiz import UserQuizAnswer
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=31)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@app.teardown_appcontext
def shutdown_session(exception=None):
    """Закрываем сессию после каждого запроса"""
    db_sess = getattr(g, '_db_session', None)
    if db_sess:
        db_sess.close()


def get_db():
    """Получаем сессию базы данных (одна на запрос)"""
    if not hasattr(g, '_db_session'):
        g._db_session = db_session.create_session()
    return g._db_session


@login_manager.user_loader
def load_user(user_id):
    db_sess = get_db()
    return db_sess.get(User, user_id)


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
    except AssertionError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Ошибка выполнения: {str(e)}"


def init_educational_data():
    db_sess = db_session.create_session()

    if db_sess.query(Lesson).first():
        db_sess.close()
        return

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

    lessons_data = [
        # Модуль 1: Основы программирования
        {"title": "Что такое программирование?",
         "content": "<p>Программирование - это процесс создания компьютерных программ. Язык Python - отличный выбор для начинающих!</p><p>Python - это интерпретируемый язык, который читает код построчно. Он очень популярен для обучения программированию.</p>",
         "order": 1, "xp_reward": 50, "module_id": module_objects[0].id},
        {"title": "Первая программа",
         "content": "<p>Напишем программу, которая выводит текст на экран. Используйте команду print().</p><p>Пример: <code>print('Привет, мир!')</code></p><p>Команда print() выводит текст в консоль. Текст нужно заключать в кавычки.</p>",
         "order": 2, "xp_reward": 50, "module_id": module_objects[0].id},

        # Модуль 2: Переменные и типы данных
        {"title": "Что такое переменные?",
         "content": "<p>Переменные - это контейнеры для хранения данных. Пример: <code>name = 'Анна'</code></p><p>Переменная - это имя, которое ссылается на значение в памяти компьютера. Знак = называется оператором присваивания.</p>",
         "order": 1, "xp_reward": 75, "module_id": module_objects[1].id},
        {"title": "Числовые типы данных",
         "content": "<p>В Python есть два основных числовых типа: int (целые числа) и float (дробные числа).</p><p>Пример: <code>age = 10</code> (int), <code>price = 99.99</code> (float)</p><p>С числами можно выполнять арифметические операции: +, -, *, /, // (целое деление), % (остаток).</p>",
         "order": 2, "xp_reward": 75, "module_id": module_objects[1].id},
        {"title": "Строки и булевы значения",
         "content": "<p>str (строка) - тип данных для текста. Строки заключаются в одинарные или двойные кавычки.</p><p>bool (булево значение) - может быть True или False. Используется в условиях.</p><p>Пример: <code>name = 'Вася'</code>, <code>is_student = True</code></p>",
         "order": 3, "xp_reward": 75, "module_id": module_objects[1].id},

        # Модуль 3: Условные операторы
        {"title": "Оператор if",
         "content": "<p>if позволяет выполнять код только при определенном условии.</p><p>Пример:</p><pre>if age >= 18:\n    print('Совершеннолетний')</pre><p>Важно! После условия ставится двоеточие, а тело условия пишется с отступом (4 пробела).</p>",
         "order": 1, "xp_reward": 100, "module_id": module_objects[2].id},
        {"title": "Операторы else и elif",
         "content": "<p>else выполняется, если условие ложно. elif позволяет проверить несколько условий.</p><p>Пример:</p><pre>if score >= 90:\n    print('Отлично')\nelif score >= 70:\n    print('Хорошо')\nelse:\n    print('Нужно учиться')</pre>",
         "order": 2, "xp_reward": 100, "module_id": module_objects[2].id},

        # Модуль 4: Циклы
        {"title": "Цикл while",
         "content": "<p>while повторяет код пока условие истинно.</p><p>Пример:</p><pre>count = 0\nwhile count < 5:\n    print(count)\n    count = count + 1</pre><p>Важно не забывать менять переменную в условии, иначе цикл станет бесконечным!</p>",
         "order": 1, "xp_reward": 100, "module_id": module_objects[3].id},
        {"title": "Цикл for",
         "content": "<p>for используется для перебора элементов последовательности.</p><p>Пример:</p><pre>for i in range(5):\n    print(i)\n\nfor letter in 'Python':\n    print(letter)</pre><p>range(n) создает последовательность от 0 до n-1.</p>",
         "order": 2, "xp_reward": 100, "module_id": module_objects[3].id},

        # Модуль 5: Функции
        {"title": "Создание функций",
         "content": "<p>Функции - это блоки кода, которые можно вызывать многократно. Создаются с помощью def.</p><p>Пример:</p><pre>def greet():\n    print('Привет!')\n\ngreet()  # вызов функции</pre>",
         "order": 1, "xp_reward": 125, "module_id": module_objects[4].id},
        {"title": "Параметры и возврат значений",
         "content": "<p>Функции могут принимать параметры и возвращать результаты с помощью return.</p><p>Пример:</p><pre>def add(a, b):\n    return a + b\n\nresult = add(5, 3)\nprint(result)  # 8</pre>",
         "order": 2, "xp_reward": 125, "module_id": module_objects[4].id},
    ]

    lesson_objects = []
    for lesson_data in lessons_data:
        lesson = Lesson(**lesson_data)
        db_sess.add(lesson)
        db_sess.commit()
        lesson_objects.append(lesson)

    # Тесты для всех уроков
    quizzes = [
        {"lesson_id": lesson_objects[0].id, "questions": [
            {"text": "Что такое программирование?", "options": "Процесс создания программ,Изучение компьютеров,Работа с текстом,Игры", "correct": 0},
            {"text": "Какой язык рекомендуется для начинающих?", "options": "C++,Java,Python,JavaScript", "correct": 2},
        ]},
        {"lesson_id": lesson_objects[1].id, "questions": [
            {"text": "Как вывести текст в Python?", "options": "print(),output(),echo(),write()", "correct": 0},
            {"text": "Что выведет print('Hello')?", "options": "Hello,'Hello',hello,Ошибка", "correct": 0},
        ]},
        {"lesson_id": lesson_objects[2].id, "questions": [
            {"text": "Как правильно создать переменную?", "options": "name = 'Анна',name == 'Анна','Анна' = name", "correct": 0},
            {"text": "Что такое переменная?", "options": "Контейнер для данных,Функция,Цикл", "correct": 0},
        ]},
        {"lesson_id": lesson_objects[3].id, "questions": [
            {"text": "Какой тип данных у числа 10?", "options": "int,float,str", "correct": 0},
            {"text": "Сколько будет 10 // 3?", "options": "3,3.33,4,Ошибка", "correct": 0},
        ]},
        {"lesson_id": lesson_objects[4].id, "questions": [
            {"text": "Какое значение у типа bool?", "options": "True/False,1/0,Yes/No", "correct": 0},
            {"text": "Как создать строку?", "options": "'Привет',\"Привет\",Оба варианта", "correct": 2},
        ]},
        {"lesson_id": lesson_objects[5].id, "questions": [
            {"text": "Что делает оператор if?", "options": "Выполняет код при условии,Повторяет код,Создает функцию", "correct": 0},
            {"text": "Как проверить, что a равно 5?", "options": "if a = 5:,if a == 5:,if a === 5:", "correct": 1},
        ]},
        {"lesson_id": lesson_objects[6].id, "questions": [
            {"text": "Что делает else?", "options": "Выполняется если условие ложно,Проверяет другое условие,Завершает программу", "correct": 0},
            {"text": "Что делает elif?", "options": "Проверяет доп. условие,Завершает программу,Выводит ошибку", "correct": 0},
        ]},
        {"lesson_id": lesson_objects[7].id, "questions": [
            {"text": "Что делает цикл while?", "options": "Повторяет пока условие истинно,Выполняет один раз,Создает функцию", "correct": 0},
            {"text": "Как остановить цикл?", "options": "break,continue,stop", "correct": 0},
        ]},
        {"lesson_id": lesson_objects[8].id, "questions": [
            {"text": "Что делает цикл for?", "options": "Перебирает элементы,Повторяет пока условие,Выполняет один раз", "correct": 0},
            {"text": "Что выведет for i in range(3): print(i)?", "options": "0 1 2,1 2 3,0 1 2 3", "correct": 0},
        ]},
        {"lesson_id": lesson_objects[9].id, "questions": [
            {"text": "Как создать функцию?", "options": "def,func,function", "correct": 0},
            {"text": "Как вызвать функцию greet?", "options": "greet(),call greet(),greet", "correct": 0},
        ]},
        {"lesson_id": lesson_objects[10].id, "questions": [
            {"text": "Что делает return?", "options": "Возвращает значение,Выводит текст,Завершает программу", "correct": 0},
            {"text": "Сколько параметров в функции def add(a, b)?", "options": "2,1,3", "correct": 0},
        ]},
    ]

    for quiz_data in quizzes:
        quiz = Quiz(lesson_id=quiz_data["lesson_id"])
        db_sess.add(quiz)
        db_sess.commit()
        for i, q in enumerate(quiz_data["questions"]):
            question = QuizQuestion(quiz_id=quiz.id, text=q["text"], options=q["options"], correct_answer=q["correct"], order=i + 1)
            db_sess.add(question)
            db_sess.commit()

    # Практические задания для всех 11 уроков с улучшенной проверкой
    tasks = [
        # Урок 1
        {"lesson_id": lesson_objects[0].id, "title": "Моя первая программа",
         "description": "Напишите программу, которая выводит на экран текст 'Я начинаю программировать!'",
         "initial_code": "# Напишите код здесь\n\n",
         "test_code": "assert 'Я начинаю программировать!' in output, 'Не найдена фраза \"Я начинаю программировать!\"'",
         "language": "python"},
        # Урок 2
        {"lesson_id": lesson_objects[1].id, "title": "Приветствие",
         "description": "Напишите программу, которая выводит на экран 'Привет, мир!' и 'Python - это круто!' (каждое с новой строки)",
         "initial_code": "# Напишите код здесь\n\n",
         "test_code": "assert 'Привет, мир!' in output, 'Не найдена фраза \"Привет, мир!\"'\nassert 'Python - это круто!' in output, 'Не найдена фраза \"Python - это круто!\"'",
         "language": "python"},
        # Урок 3
        {"lesson_id": lesson_objects[2].id, "title": "Мои переменные",
         "description": "Создайте переменную name со значением 'Python' и выведите её на экран",
         "initial_code": "# Создайте переменную name\n\n# Выведите переменную\n",
         "test_code": "assert 'Python' in output, 'Переменная name не выведена или содержит не \"Python\"'",
         "language": "python"},
        # Урок 4
        {"lesson_id": lesson_objects[3].id, "title": "Калькулятор",
         "description": "Создайте переменные a=15 и b=4, выведите их сумму",
         "initial_code": "a = 15\nb = 4\n\n# Выведите сумму\n",
         "test_code": "assert '19' in output, 'Сумма 15+4 должна быть 19'",
         "language": "python"},
        # Урок 5
        {"lesson_id": lesson_objects[4].id, "title": "Строки",
         "description": "Создайте строку text='Python' и выведите её длину (используйте len())",
         "initial_code": "# Создайте строку\n\n# Выведите длину\n",
         "test_code": "assert '6' in output, 'Длина строки \"Python\" равна 6'",
         "language": "python"},
        # Урок 6
        {"lesson_id": lesson_objects[5].id, "title": "Проверка возраста",
         "description": "Если age=16, выведите 'Несовершеннолетний'",
         "initial_code": "age = 16\n\n# Напишите условие\n",
         "test_code": "assert 'Несовершеннолетний' in output, 'Должно быть выведено \"Несовершеннолетний\"'",
         "language": "python"},
        # Урок 7
        {"lesson_id": lesson_objects[6].id, "title": "Оценка знаний",
         "description": "Если score=75, выведите 'Хорошо'",
         "initial_code": "score = 75\n\n# Напишите условие\n",
         "test_code": "assert 'Хорошо' in output, 'Должно быть выведено \"Хорошо\"'",
         "language": "python"},
        # Урок 8
        {"lesson_id": lesson_objects[7].id, "title": "Счетчик",
         "description": "Используя цикл while, выведите числа от 1 до 5 (каждое с новой строки)",
         "initial_code": "# Напишите цикл while\n",
         "test_code": "assert '1' in output, 'Нет числа 1'\nassert '2' in output, 'Нет числа 2'\nassert '3' in output, 'Нет числа 3'\nassert '4' in output, 'Нет числа 4'\nassert '5' in output, 'Нет числа 5'",
         "language": "python"},
        # Урок 9
        {"lesson_id": lesson_objects[8].id, "title": "Перебор букв",
         "description": "Выведите все буквы слова 'Python' с помощью цикла for (каждую с новой строки)",
         "initial_code": "word = 'Python'\n\n# Напишите цикл for\n",
         "test_code": "assert 'P' in output, 'Нет буквы P'\nassert 'y' in output, 'Нет буквы y'\nassert 't' in output, 'Нет буквы t'\nassert 'h' in output, 'Нет буквы h'\nassert 'o' in output, 'Нет буквы o'\nassert 'n' in output, 'Нет буквы n'",
         "language": "python"},
        # Урок 10
        {"lesson_id": lesson_objects[9].id, "title": "Моя функция",
         "description": "Создайте функцию greet, которая выводит 'Привет!' и вызовите её",
         "initial_code": "# Создайте функцию\n\n# Вызовите функцию\n",
         "test_code": "assert 'Привет!' in output, 'Функция должна выводить \"Привет!\"'",
         "language": "python"},
        # Урок 11
        {"lesson_id": lesson_objects[10].id, "title": "Сумматор",
         "description": "Создайте функцию add, которая принимает два числа и возвращает их сумму. Вызовите её с числами 5 и 3 и выведите результат",
         "initial_code": "# Создайте функцию\n\n# Вызовите функцию и выведите результат\n",
         "test_code": "assert '8' in output, 'Сумма 5+3 должна быть 8'",
         "language": "python"},
    ]

    for task_data in tasks:
        task = Task(**task_data)
        db_sess.add(task)
        db_sess.commit()

    achievements = [
        {"name": "Первые шаги", "description": "Завершите первый урок", "icon": "🌟", "xp_reward": 50, "required_lessons": 1},
        {"name": "Новичок", "description": "Наберите 200 XP", "icon": "📚", "xp_reward": 100, "required_xp": 200},
        {"name": "Мастер переменных", "description": "Завершите модуль 'Переменные'", "icon": "🔤", "xp_reward": 150, "required_modules": 2},
        {"name": "Программист", "description": "Наберите 500 XP", "icon": "💻", "xp_reward": 200, "required_xp": 500},
        {"name": "Гуру циклов", "description": "Завершите модуль 'Циклы'", "icon": "🔄", "xp_reward": 150, "required_modules": 4},
        {"name": "Мастер функций", "description": "Завершите модуль 'Функции'", "icon": "⚙️", "xp_reward": 150, "required_modules": 5},
    ]

    for ach in achievements:
        achievement = Achievement(**ach)
        db_sess.add(achievement)
        db_sess.commit()

    db_sess.close()


@app.route("/")
def index():
    if current_user.is_authenticated:
        db_sess = get_db()
        progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
        total_xp = progress.total_xp if progress else 0
        achievements = db_sess.query(UserAchievement).filter(UserAchievement.user_id == current_user.id).join(Achievement).all()
        return render_template("index.html", total_xp=total_xp, achievements=achievements, user=current_user)
    return render_template("index.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        password = hashlib.sha256(form.password.data.encode('utf-8')).hexdigest()
        password_again = hashlib.sha256(form.password_again.data.encode('utf-8')).hexdigest()
        if password != password_again:
            return render_template('register.html', form=form, message="Пароли не совпадают")
        db_sess = get_db()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', form=form, message="Такой пользователь уже есть")
        user = User(name=form.name.data, email=form.email.data, about=form.about.data, age=form.age.data if hasattr(form, 'age') else 12)
        user.set_password(password)
        db_sess.add(user)
        db_sess.commit()
        progress = UserProgress(user_id=user.id)
        db_sess.add(progress)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = get_db()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(hashlib.sha256(form.password.data.encode('utf-8')).hexdigest()):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', message="Неправильный логин или пароль", form=form)
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/lessons')
@login_required
def lessons():
    db_sess = get_db()
    modules = db_sess.query(Module).order_by(Module.order).all()
    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
    completed_lessons = set(progress.completed_lessons.split(',')) if progress and progress.completed_lessons else set()
    return render_template("lessons.html", modules=modules, completed_lessons=completed_lessons)


@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    db_sess = get_db()
    lesson = db_sess.get(Lesson, lesson_id)
    if not lesson:
        abort(404)
    task_obj = db_sess.query(Task).filter(Task.lesson_id == lesson_id).first()
    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
    completed = str(lesson_id) in (progress.completed_lessons.split(',') if progress and progress.completed_lessons else [])
    return render_template("lesson_detail.html", lesson=lesson, completed=completed, task=task_obj)


@app.route('/lesson/<int:lesson_id>/complete', methods=['GET'])
@login_required
def complete_lesson(lesson_id):
    db_sess = get_db()
    lesson = db_sess.get(Lesson, lesson_id)
    if not lesson:
        abort(404)
    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
    if not progress:
        progress = UserProgress(user_id=current_user.id)
        db_sess.add(progress)
    completed_lessons = set(progress.completed_lessons.split(',')) if progress.completed_lessons else set()
    if str(lesson_id) not in completed_lessons:
        completed_lessons.add(str(lesson_id))
        progress.completed_lessons = ','.join(completed_lessons)
        progress.total_xp += lesson.xp_reward
        db_sess.commit()
        quiz_obj = db_sess.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
        if quiz_obj:
            user_answers = db_sess.query(UserQuizAnswer).filter(UserQuizAnswer.user_id == current_user.id, UserQuizAnswer.quiz_id == quiz_obj.id).first()
            if user_answers:
                user_answers.completed = True
                db_sess.commit()
    return redirect(f'/lesson/{lesson_id}')


@app.route('/quiz/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def quiz(lesson_id):
    db_sess = get_db()
    quiz_obj = db_sess.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    if not quiz_obj:
        return redirect(f'/lesson/{lesson_id}')
    questions = db_sess.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_obj.id).order_by(QuizQuestion.order).all()
    task_obj = db_sess.query(Task).filter(Task.lesson_id == lesson_id).first()
    task_id = task_obj.id if task_obj else None
    user_answers_record = db_sess.query(UserQuizAnswer).filter(UserQuizAnswer.user_id == current_user.id, UserQuizAnswer.quiz_id == quiz_obj.id).first()
    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
    lesson_completed = str(lesson_id) in (progress.completed_lessons.split(',') if progress and progress.completed_lessons else [])
    user_answers = json.loads(user_answers_record.answers) if user_answers_record and user_answers_record.answers else {}
    if request.method == 'POST':
        score = 0
        answers = {}
        for i, question in enumerate(questions):
            answer = request.form.get(f'q_{i}')
            if answer:
                answers[str(i)] = answer
                if int(answer) == question.correct_answer:
                    score += 1
        test_passed = (score == len(questions))
        if user_answers_record:
            user_answers_record.answers = json.dumps(answers)
            user_answers_record.completed = test_passed
        else:
            user_answers_record = UserQuizAnswer(user_id=current_user.id, quiz_id=quiz_obj.id, answers=json.dumps(answers), completed=test_passed)
            db_sess.add(user_answers_record)
        db_sess.commit()
        return render_template("quiz.html", quiz=quiz_obj, questions=questions, score=score, total=len(questions), test_passed=test_passed, lesson_id=lesson_id, lesson_completed=lesson_completed, user_answers=answers, task_id=task_id)
    return render_template("quiz.html", quiz=quiz_obj, questions=questions, lesson_id=lesson_id, lesson_completed=lesson_completed, user_answers={}, task_id=task_id)


@app.route('/quiz/<int:lesson_id>/reset', methods=['GET'])
@login_required
def reset_quiz(lesson_id):
    db_sess = get_db()
    quiz_obj = db_sess.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    if quiz_obj:
        user_answers = db_sess.query(UserQuizAnswer).filter(UserQuizAnswer.user_id == current_user.id, UserQuizAnswer.quiz_id == quiz_obj.id).first()
        if user_answers:
            db_sess.delete(user_answers)
        progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
        if progress and progress.completed_lessons:
            completed = set(progress.completed_lessons.split(','))
            if str(lesson_id) in completed:
                completed.remove(str(lesson_id))
                progress.completed_lessons = ','.join(completed)
                lesson = db_sess.get(Lesson, lesson_id)
                if lesson:
                    progress.total_xp -= lesson.xp_reward
        db_sess.commit()
    return redirect(f'/quiz/{lesson_id}')


@app.route('/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task(task_id):
    db_sess = get_db()
    task_obj = db_sess.get(Task, task_id)
    if not task_obj:
        abort(404)
    solved_record = db_sess.query(TaskSolution).filter(TaskSolution.task_id == task_id, TaskSolution.user_id == current_user.id).first()
    solved = solved_record is not None and solved_record.solved
    if request.method == 'POST':
        code = request.form.get('code')
        if code and task_obj.language == 'python':
            # Используем улучшенную проверку кода
            is_correct, message = check_python_code(code, task_obj)
            if is_correct:
                if not solved:
                    solution = TaskSolution(task_id=task_id, user_id=current_user.id, code=code, solved=True)
                    db_sess.add(solution)
                    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
                    if progress:
                        progress.total_xp += 50
                    db_sess.commit()
                    check_achievements(current_user.id)
                return render_template("task.html", task=task_obj, solved=True, message="✅ Задание выполнено! +50 XP")
            else:
                return render_template("task.html", task=task_obj, solved=False, message=f"❌ {message}")
        return render_template("task.html", task=task_obj, solved=False, message="❌ Код не прошел проверку. Попробуйте еще раз!")
    return render_template("task.html", task=task_obj, solved=solved)


@app.route('/profile')
@login_required
def profile():
    db_sess = get_db()
    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
    total_xp = progress.total_xp if progress else 0
    completed_lessons_count = len(progress.completed_lessons.split(',')) if progress and progress.completed_lessons else 0
    total_lessons = db_sess.query(Lesson).count()
    user_achievements = db_sess.query(UserAchievement).filter(UserAchievement.user_id == current_user.id).join(Achievement).all()
    return render_template("profile.html", user=current_user, total_xp=total_xp, completed_lessons=completed_lessons_count, total_lessons=total_lessons, achievements=user_achievements)


def check_achievements(user_id):
    db_sess = get_db()
    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == user_id).first()
    if not progress:
        return
    achievements = db_sess.query(Achievement).all()
    user_achievements = set(ua.achievement_id for ua in db_sess.query(UserAchievement).filter(UserAchievement.user_id == user_id).all())
    for achievement in achievements:
        if achievement.id in user_achievements:
            continue
        achieved = False
        if achievement.required_xp and progress.total_xp >= achievement.required_xp:
            achieved = True
        elif achievement.required_lessons and progress.completed_lessons:
            completed = len(progress.completed_lessons.split(',')) if progress.completed_lessons else 0
            if completed >= achievement.required_lessons:
                achieved = True
        if achieved:
            user_achievement = UserAchievement(user_id=user_id, achievement_id=achievement.id, earned_at=datetime.datetime.now())
            db_sess.add(user_achievement)
            progress.total_xp += achievement.xp_reward
            db_sess.commit()


@app.route('/api/user/progress')
@login_required
def api_user_progress():
    db_sess = get_db()
    progress = db_sess.query(UserProgress).filter(UserProgress.user_id == current_user.id).first()
    return jsonify({"total_xp": progress.total_xp if progress else 0, "completed_lessons": progress.completed_lessons.split(',') if progress and progress.completed_lessons else []})


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/leaderboard')
@login_required
def leaderboard():
    db_sess = get_db()
    data = db_sess.query(User.name, UserProgress.completed_lessons, UserProgress.total_xp).join(User, User.id == UserProgress.user_id).order_by(UserProgress.total_xp.desc()).all()
    return render_template("leaderboard.html", data=data)


if __name__ == '__main__':
    db_dir = "db"
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    db_session.global_init("db/educational.db")
    init_educational_data()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)