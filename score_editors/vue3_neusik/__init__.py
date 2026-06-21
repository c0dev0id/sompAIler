from flask import Blueprint, render_template, request

blueprint = Blueprint(
    'vue3_neusik',
    __name__,
    static_folder='static',
    static_url_path='/static',
    template_folder='templates',
)

@blueprint.route('/', methods=['GET'])
def index():
    return render_template(
        'vue3_neusik/index.html',
        import_on_load='true' if request.args.get('import') == '1' else 'false',
    )
