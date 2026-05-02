from flask import render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Organization, UserOrganization
from app.auth import bp
import secrets
from app.models import Invite
from app.utils import admin_required
from flask_mail import Message
from app import mail


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        org_name = request.form['org_name']

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already taken.')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('auth.register'))

        # Create user with hashed password
        hashed_pw = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_pw)
        db.session.add(user)

        # Create organization
        org = Organization(name=org_name)
        db.session.add(org)
        db.session.flush()  # gets the org.id before final commit

        # Link user to org as admin
        membership = UserOrganization(user_id=user.id, org_id=org.id, role='admin')
        db.session.add(membership)

        db.session.commit()
        flash('Account created! Please log in.')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash('Invalid username or password.')
            return redirect(url_for('auth.login'))

        login_user(user)

        # Save the user's org and role in session
        membership = UserOrganization.query.filter_by(user_id=user.id).first()
        session['org_id'] = membership.org_id
        session['role'] = membership.role

        flash(f'Welcome, {user.username}!')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))

@bp.route('/invite', methods=['GET', 'POST'])
@login_required
@admin_required
def invite():
    org_id = session.get('org_id')

    if request.method == 'POST':
        email = request.form['email']

        # Check if already invited
        existing = Invite.query.filter_by(email=email, org_id=org_id, used=False).first()
        if existing:
            flash('An invite has already been sent to this email.')
            return redirect(url_for('auth.invite'))

        # Generate a unique token
        token = secrets.token_urlsafe(32)
        invite = Invite(email=email, org_id=org_id, token=token)
        db.session.add(invite)
        db.session.commit()

        # Generate the invite link
        invite_link = url_for('auth.accept_invite', token=token, _external=True)
        # Send email
        msg = Message(
            subject='You have been invited to join IMS',
            recipients=[email]
        )
        msg.body = f'''Hello!

        You have been invited to join as a staff member on the Inventory Management System.

        Click the link below to create your account:

        {invite_link}

        This link can only be used once.

        If you did not expect this invite, you can ignore this email.
        '''
        mail.send(msg)

        flash(f'Invite email sent to {email}!')
        return redirect(url_for('auth.invite'))

    # Show existing pending invites
    org_id = session.get('org_id')
    pending = Invite.query.filter_by(org_id=org_id, used=False).all()
    return render_template('auth/invite.html', pending=pending)


@bp.route('/accept/<token>', methods=['GET', 'POST'])
def accept_invite(token):
    invite = Invite.query.filter_by(token=token, used=False).first()

    if not invite:
        flash('Invalid or expired invite link.')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check username not taken
        if User.query.filter_by(username=username).first():
            flash('Username already taken. Try another.')
            return redirect(url_for('auth.accept_invite', token=token))

        # Create the staff user
        hashed_pw = generate_password_hash(password)
        user = User(username=username, email=invite.email, password=hashed_pw)
        db.session.add(user)
        db.session.flush()

        # Link to org as staff
        membership = UserOrganization(
            user_id=user.id,
            org_id=invite.org_id,
            role='staff'
        )
        db.session.add(membership)

        # Mark invite as used
        invite.used = True
        db.session.commit()

        flash('Account created! You can now log in.')
        return redirect(url_for('auth.login'))

    return render_template('auth/accept_invite.html', invite=invite)