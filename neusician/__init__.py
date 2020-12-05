import os
from .arbitextonotes import tones
from flask import Flask, render_template, request, jsonify

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'neusician.db'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    @app.route('/randomelody', methods=("GET", "POST"))
    def randomelody_stage1():
        if request.method == 'POST':
            return jsonify(tones(
                request.form["seedphrase"],
                request.form["markovspec"],
                (int(request.form["melody-share"]),
                 int(request.form["pause-share"]))
                ))
        else:
            markov = request.args.get("markov")
            if not markov:
                markov = open("neusician/markov_default.txt").read()
            return render_template("random.tmpl",
                seed_phrase="test",
                markov_spec=markov,
                correction="(Not implemented, yet)",
                melody_pause_ratio=(
                    request.args.get("melody-share", 1),
                    request.args.get("pause-share", 1)
                )
            )

    @app.route('/sompyle', methods=('GET',))
    def yaml_textarea():
        return render_template("yaml_input.tmpl",
                yamlcode=request.args.get("yamlcode")
            )


    return app

app = create_app()
