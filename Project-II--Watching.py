from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from data import Series
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'sarlym17'
app.config['MYSQL_DB'] = 'projeto2'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

Series = Series()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/series')
def series():
    return render_template('series.html', series = Series)

@app.route('/serie/<string:title>/')
def serie(title):

    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM series WHERE title = %s", [title])

    serie = cur.fetchone()

    form = SerieForm(request.form)
    form.title.data = serie['title']
    form.body.data = serie['body']
    form.seasons.data = serie['seasons']
    return render_template('serie.html', form = form)

class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        mysql.connection.commit()

        cur.close()

        flash('You are now registered and can log in', 'success')

        redirect(url_for('home'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized. Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    return render_template('dashboard.html')

@app.route('/myseries')
@is_logged_in
def myseries():

    ser = []
    for serie in Series:
        tit = serie
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM myseries WHERE title = %s", [tit])
        if result > 0:
            ser = ser + [tit]
    return render_template('myseries.html', series = ser)

@app.route('/myserie/<string:title>/')
def myserie(title):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM myseries WHERE title = %s", [title])

    serie = cur.fetchone()

    form = SerieForm(request.form)

    form.title.data = serie['title']
    form.body.data = serie['body']
    form.seasons.data = serie['seasons']
    form.episodes.data = serie['episodes']

    return render_template('myserie.html', form=form)

class SerieForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = StringField('Body', [validators.Length(min=30)])
    seasons = StringField('Seasons', [validators.Length(max=3)])
    episodes = StringField('Episodes', [validators.Length(max=5)])

@app.route('/add_serie/<string:title>', methods=['GET', 'POST'])
@is_logged_in
def add_serie(title):

    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM series WHERE title = %s", [title])

    serie = cur.fetchone()

    lookfor = cur.execute("SELECT * FROM myseries WHERE title = %s", [title])

    if lookfor > 0:
        flash('Already on your list!', 'danger')
        return redirect(url_for('series'))

    else:
        form = SerieForm(request.form)

        form.title.data = serie['title']
        form.body.data = serie['body']
        form.seasons.data = serie['seasons']
        form.episodes.data = serie['episodes']

        cur.execute("INSERT INTO myseries(title, body, seasons, episodes) VALUES (%s, %s, %s, %s)", (form.title.data, form.body.data, '1', '1'))
        mysql.connection.commit()

        cur.close()

        flash('Serie added to your list!', 'success')


    return render_template('add_serie.html', form=form)

@app.route('/remove_serie/<string:title>', methods=['GET', 'POST'])
@is_logged_in
def remove_serie(title):

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM myseries WHERE title = %s", [title])

    mysql.connection.commit()

    cur.close()

    flash('Serie removed from your list!', 'danger')


    return render_template('remove_serie.html')

@app.route('/edit_serie/<string:title>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(title):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article by id
    result = cur.execute("SELECT * FROM myseries WHERE title=%s", [title])

    serie = cur.fetchone()
    cur.close()
    # Get form
    form = SerieForm(request.form)

    # Populate article form fields
    form.seasons.data = serie['seasons']
    form.episodes.data = serie['episodes']
    form.title.data = serie['title']

    if request.method == 'POST':
        seasons = request.form['seasons']
        episodes = request.form['episodes']

        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(title)
        # Execute
        cur.execute ("UPDATE myseries SET seasons=%s, episodes=%s WHERE title=%s",[seasons, episodes, title])
        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Serie Updated', 'success')

        return redirect(url_for('myseries'))

    return render_template('edit_serie.html', form=form)

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)
