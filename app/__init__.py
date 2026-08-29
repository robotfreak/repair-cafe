import os

import flask

from app.db import get_request_db, init_db


def create_app(data_dir=None):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = flask.Flask(
        __name__,
        template_folder=os.path.join(project_root, "templates"),
        static_folder=os.path.join(project_root, "static"),
    )
    if data_dir is None:
        data_dir = os.path.join(project_root, "data")
    app.config["DATA_DIR"] = data_dir
    os.makedirs(data_dir, exist_ok=True)

    db_path = os.path.join(data_dir, "repair.db")
    app.config["DB_PATH"] = db_path
    init_db(db_path)

    os.makedirs(os.path.join(data_dir, "documents"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "signatures"), exist_ok=True)

    @app.teardown_appcontext
    def close_db(exception=None):
        conn = getattr(flask.g, "_db", None)
        if conn is not None:
            conn.close()

    from app.devices import bp as devices_bp
    from app.waivers import bp as waivers_bp
    from app.tickets import bp as tickets_bp, board_bp as tickets_board_bp
    from app.journal import bp as journal_bp
    from app.search import bp as search_bp
    from app.documents import bp as documents_bp
    from app.assistant import bp as assistant_bp
    from app.equipment import bp as equipment_bp

    app.register_blueprint(devices_bp)
    app.register_blueprint(waivers_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(tickets_board_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(equipment_bp)

    @app.route("/")
    def index():
        return flask.render_template("index.html")

    @app.route("/api/health")
    def health():
        return {"ok": True}

    return app