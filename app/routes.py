from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Student

bp = Blueprint('students', __name__)
FIELD_LIMITS = {'first_name': 80, 'last_name': 80, 'email': 254, 'group': 40}
FIELD_LABELS = {'first_name': 'Ім’я', 'last_name': 'Прізвище', 'email': 'Email', 'group': 'Група'}


def validated_student():
    payload = request.get_json()
    if not isinstance(payload, dict):
        return None, {'form': 'Очікується JSON-об’єкт.'}
    values, errors = {}, {}
    for field, limit in FIELD_LIMITS.items():
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors[field] = f'{FIELD_LABELS[field]}: заповніть поле.'
        elif len(value.strip()) > limit:
            errors[field] = f'{FIELD_LABELS[field]}: максимум {limit} символів.'
        elif any(ord(char) < 32 for char in value):
            errors[field] = f'{FIELD_LABELS[field]}: недопустимі символи.'
        else:
            values[field] = value.strip()
    if 'email' in values:
        try:
            values['email'] = validate_email(values['email'], check_deliverability=False).normalized.lower()
            if len(values['email']) > FIELD_LIMITS['email']:
                errors['email'] = 'Email: максимум 254 символи.'
        except EmailNotValidError:
            errors['email'] = 'Введіть коректну адресу email.'
    return values, errors


def save_student(student, status):
    try:
        db.session.add(student)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error='Студент із таким email уже існує.',
                       fields={'email': 'Цей email уже використовується.'}), 409
    return jsonify(student.to_dict()), status


@bp.get('/')
def index():
    return render_template('index.html')


@bp.get('/api/students')
def list_students():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        if page < 1 or not 1 <= per_page <= 100:
            raise ValueError
    except ValueError:
        return jsonify(error='Некоректні параметри сторінки.'), 400
    query = db.select(Student)
    search = request.args.get('q', '').strip()[:200]
    group = request.args.get('group', '').strip()
    if search:
        # Escape LIKE metacharacters: search treats user input as literal text.
        escaped = search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        pattern = f'%{escaped}%'
        query = query.where(or_(
            Student.first_name.ilike(pattern, escape='\\'),
            Student.last_name.ilike(pattern, escape='\\'),
            (Student.first_name + ' ' + Student.last_name).ilike(pattern, escape='\\'),
            Student.email.ilike(pattern, escape='\\'),
        ))
    if group:
        query = query.where(Student.group == group)
    total = db.session.scalar(db.select(func.count()).select_from(query.subquery()))
    students = db.session.scalars(query.order_by(Student.last_name, Student.first_name, Student.id)
                                  .offset((page - 1) * per_page).limit(per_page)).all()
    groups = db.session.scalars(db.select(Student.group).distinct().order_by(Student.group)).all()
    all_count = db.session.scalar(db.select(func.count(Student.id)))
    return jsonify(items=[s.to_dict() for s in students], total=total, page=page,
                   per_page=per_page, groups=groups, all_count=all_count)


@bp.post('/api/students')
def create_student():
    values, errors = validated_student()
    if errors:
        return jsonify(error='Перевірте поля форми.', fields=errors), 400
    return save_student(Student(**values), 201)


@bp.put('/api/students/<int:student_id>')
def update_student(student_id):
    student = db.get_or_404(Student, student_id)
    values, errors = validated_student()
    if errors:
        return jsonify(error='Перевірте поля форми.', fields=errors), 400
    for key, value in values.items():
        setattr(student, key, value)
    return save_student(student, 200)


@bp.delete('/api/students/<int:student_id>')
def delete_student(student_id):
    student = db.get_or_404(Student, student_id)
    db.session.delete(student)
    db.session.commit()
    return '', 204
