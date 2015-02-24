#!/usr/bin/env python
"""
Main server file.
@author ianaval

"""
import os
import os.path
import re

from jinja2 import evalcontextfilter, Markup, escape
from flask import Flask, render_template, request, redirect, url_for, g
from flask_login import LoginManager, login_required, current_user, \
    login_user, logout_user
from werkzeug import secure_filename

from users import User
from challenges import Challenge
from hackerrank import hackerrank


################
# SERVER SETUP #
################
app = Flask(__name__)
app.secret_key = '&\x96J\xb3\x8d\x1c\x8c\x81|\x0c\xde\xb0D\xbfk!\xf7\xb8\xbd\x833\x92N\xa5'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')
print "Getting users"
User.initialize()
print "Getting challenges"
Challenge.initialize()

if not app.debug:
    import logging
    file_handler = logging.FileHandler('/tmp/test')
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)

@app.before_request
def before_request():
    """Exposes users, shadows and hackerrank languages to global template 
    context."""
    g.users = User._users
    g.shadows = User._shadows
    g.Challenge = Challenge
    g.langs = sorted(
        hackerrank.langs['languages']['names'].iteritems(),
        key=lambda v: v[1])
    g.lang_names = hackerrank.langs['languages']['names']


@app.template_filter()
@evalcontextfilter
def nl2br(eval_ctx, value):
    """Converts newlines to <br /> in templates."""
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                          for p in _paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result


@login_manager.user_loader
def load_user(userid):
    """Loads users."""
    return User.get(userid, None)


#########
# VIEWS #
#########
@app.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_anonymous():
        username = request.environ.get('REMOTE_USER')
        User.authenticate(username, '')
        login_user(g.users.get(username))
        return redirect(url_for('index'))
    else:
        langs = ', '.join(
            sorted(hackerrank.langs['languages']['names'].values()))
        return render_template('index.html', langs=langs)



@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('https://cas.wpi.edu/cas/logout')


@app.route('/challenges.aspx')
@app.route('/challenges/<challenge_id>', methods=['GET', 'POST'])
@login_required
def challenges(challenge_id=None):
    if challenge_id is not None:
        challenge = Challenge.get(challenge_id)
        if request.method == 'GET':
            return render_template('challenge.html', challenge=challenge)
        elif request.method == 'POST':
            points = 0
            file_ = request.files['file']
            file_content = file_.read()
            lang = request.form['lang']
            test = request.form['submit'] == 'Test'

            raw_results = None
            if file_ and lang:
                raw_results = hackerrank.submit(file_content, lang, challenge, test)

            if raw_results is None:
                return render_template('challenge.html', challenge=challenge,
                    error="Connection timed out after 10s. Write faster code!")
            check = challenge.check(raw_results, test)
            results = []
            if check and not test:
                challenge.register_solution(current_user.username, raw_results,
                                            lang)
                challenge.recalculate_leaderboards()
                points = challenge.overall_points[current_user.username]

                SOLUTIONS_DIR = '/tmp/solutions'
                if not os.path.exists(SOLUTIONS_DIR):
                    os.makedirs(SOLUTIONS_DIR)
                user_dir = SOLUTIONS_DIR + '/' + current_user.username
                if not os.path.exists(user_dir):
                    os.makedirs(user_dir)
                filename = user_dir + '/{0}_{1}'.format(lang, file_.filename)
                with open(filename, 'w') as save_file:
                    save_file.write(file_content)

            if test and raw_results['stdout']:
                keys = ['stdout', 'stderr', 'time', 'memory', 'signal']
                for i in range(len(raw_results['stdout'])):
                    results.append({
                        key: raw_results[key][i] or ''
                        for key in keys
                    })
            return render_template(
                'challenge.html', challenge=challenge, raw_results=raw_results,
                results=enumerate(results), check=check, test=test, 
                points=points)
    else:
        return render_template(
            'challenges.html', challenges=enumerate(Challenge.all(), start=1))


@app.route('/leaderboards.drracket')
@login_required
def leaderboards():
    Challenge.recalculate_all()
    leaders = enumerate(sorted(
        g.users.values(), 
        key=lambda user: (Challenge.get_user_points(user.username), user.username),
        reverse=True), start=1)
    return render_template(
        'leaderboards.html', leaders=leaders, challenges=Challenge.all())



@app.route('/sample')
def sample():
    return "Sample page!"


@app.route('/flag')
def flag():
    return "OK"


def main():
    app.run('0.0.0.0', debug=True)


if __name__ == '__main__':
    main()
