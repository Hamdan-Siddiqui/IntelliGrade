from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from database import db, User, Classroom, Enrollment, Assignment, Submission
from grading import grade_submission
import secrets
from datetime import datetime
from functools import wraps
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = secrets.token_hex(16)
db.init_app(app)

@app.before_request
def load_user():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.user:
                return redirect(url_for('login'))
            
            if role and g.user.role != role:
                flash('Unauthorized access', 'error')
                if g.user.role == 'teacher':
                    return redirect(url_for('teacher_dashboard'))
                else:
                    return redirect(url_for('student_dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def inject_user():
    return dict(user=g.user)

@app.route('/')
def home():
    if g.user:
        if g.user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

# Auth Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash('Both email and password are required', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            if user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            name = request.form.get('name', '').strip()
            role = request.form.get('role', 'student').strip()
            
            if not all([email, password, name]):
                flash('All fields are required', 'error')
                return render_template('auth/register.html')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return render_template('auth/register.html')
            
            user = User(email=email, password=password, name=name, role=role)
            db.session.add(user)
            db.session.commit()
            
            session['user_id'] = user.id
            flash('Registration successful!', 'success')
            
            if role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
                
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Teacher Routes
@app.route('/teacher/dashboard')
@login_required(role='teacher')
def teacher_dashboard():
    classes = Classroom.query.filter_by(teacher_id=g.user.id).options(
        db.joinedload(Classroom.enrollments).joinedload(Enrollment.student)
    ).all()
    return render_template('teacher/dashboard.html', classes=classes)

@app.route('/teacher/create-class', methods=['GET', 'POST'])
@login_required(role='teacher')
def create_class():
    if request.method == 'POST':
        class_code = secrets.token_hex(3).upper()
        classroom = Classroom(
            name=request.form.get('name', '').strip(),
            code=class_code,
            teacher_id=g.user.id
        )
        db.session.add(classroom)
        db.session.commit()
        flash(f'Class created! Code: {class_code}', 'success')
        return redirect(url_for('teacher_dashboard'))
    return render_template('teacher/create_class.html')

@app.route('/teacher/class/<int:class_id>')
@login_required(role='teacher')
def view_class(class_id):
    classroom = Classroom.query.get_or_404(class_id)
    if classroom.teacher_id != g.user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    assignments = Assignment.query.filter_by(class_id=class_id).all()
    enrollments = Enrollment.query.filter_by(class_id=class_id).join(User).all()
    return render_template('teacher/view_class.html',
                        classroom=classroom,
                        assignments=assignments,
                        enrollments=enrollments)

@app.route('/teacher/class/<int:class_id>/create-assignment', methods=['GET', 'POST'])
@login_required(role='teacher')
def create_assignment(class_id):
    classroom = Classroom.query.get_or_404(class_id)
    if classroom.teacher_id != g.user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        try:
            due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%dT%H:%M')
            assignment = Assignment(
                title=request.form.get('title', '').strip(),
                description=request.form.get('description', '').strip(),
                due_date=due_date,
                class_id=class_id,
                reference_answer=request.form.get('reference_answer', '').strip()
            )
            db.session.add(assignment)
            db.session.commit()
            flash('Assignment created!', 'success')
            return redirect(url_for('view_class', class_id=class_id))
        except ValueError:
            flash('Invalid date format', 'error')
        except Exception as e:
            db.session.rollback()
            flash('Failed to create assignment', 'error')

    return render_template('teacher/create_assignment.html', class_id=class_id)

@app.route('/teacher/assignment/<int:assignment_id>/submissions')
@login_required(role='teacher')
def view_assignment_submissions(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    classroom = Classroom.query.get_or_404(assignment.class_id)
    
    if classroom.teacher_id != g.user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    submissions = Submission.query.filter_by(assignment_id=assignment_id).join(User).all()
    return render_template('teacher/view_submissions.html',
                        assignment=assignment,
                        submissions=submissions,
                        classroom=classroom)

# Student Routes
@app.route('/student/dashboard')
@login_required(role='student')
def student_dashboard():
    enrollments = db.session.query(Enrollment).\
        filter_by(student_id=g.user.id).\
        join(Classroom).\
        join(User, Classroom.teacher_id == User.id).\
        all()
    return render_template('student/dashboard.html', enrollments=enrollments)

@app.route('/student/join-class', methods=['GET', 'POST'])
@login_required(role='student')
def join_class():
    if request.method == 'POST':
        class_code = request.form.get('code', '').strip().upper()
        if not class_code:
            flash('Class code is required', 'error')
            return render_template('student/join_class.html')
        
        classroom = Classroom.query.filter_by(code=class_code).first()
        if not classroom:
            flash('Invalid class code', 'error')
            return render_template('student/join_class.html')
        
        existing = Enrollment.query.filter_by(
            student_id=g.user.id,
            class_id=classroom.id
        ).first()
        
        if existing:
            flash('You are already enrolled in this class', 'info')
            return redirect(url_for('student_dashboard'))
        
        try:
            enrollment = Enrollment(
                student_id=g.user.id,
                class_id=classroom.id
            )
            db.session.add(enrollment)
            db.session.commit()
            flash(f'Successfully joined class: {classroom.name}', 'success')
            return redirect(url_for('student_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Failed to join class. Please try again.', 'error')
    
    return render_template('student/join_class.html')

@app.route('/student/class/<int:class_id>')
@login_required(role='student')
def student_view_class(class_id):
    enrollment = Enrollment.query.filter_by(
        student_id=g.user.id,
        class_id=class_id
    ).first_or_404()
    
    classroom = Classroom.query.get_or_404(class_id)
    assignments = Assignment.query.filter_by(class_id=class_id).all()
    
    return render_template('student/view_class.html',
                         classroom=classroom,
                         assignments=assignments)

@app.route('/student/submit/<int:assignment_id>', methods=['GET', 'POST'])
@login_required(role='student')
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    enrollment = Enrollment.query.filter_by(
        student_id=g.user.id,
        class_id=assignment.class_id
    ).first_or_404()
    
    submission = Submission.query.filter_by(
        student_id=g.user.id,
        assignment_id=assignment_id
    ).first()
    
    if request.method == 'POST':
        answer = request.form.get('answer', '').strip()
        if not answer:
            flash('Answer cannot be empty', 'error')
            return render_template('student/submit.html', assignment=assignment)
        
        try:
            if submission:
                submission.content = answer
            else:
                submission = Submission(
                    content=answer,
                    student_id=g.user.id,
                    assignment_id=assignment_id
                )
                db.session.add(submission)
            
            score, feedback, improvement = grade_submission(
                answer,
                assignment.reference_answer
            )
            
            submission.score = score
            submission.feedback = f"{feedback}\n\nAreas for improvement:\n{improvement}"
            db.session.commit()
            
            flash('Assignment submitted and graded!', 'success')
            return redirect(url_for('student_view_class', class_id=assignment.class_id))
        except Exception as e:
            db.session.rollback()
            flash('Failed to submit assignment. Please try again.', 'error')
    
    return render_template('student/submit.html', 
                         assignment=assignment,
                         submission=submission)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)